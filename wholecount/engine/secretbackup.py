"""Install secret backup (SPEC 5.1, M13 BAK-1 to BAK-3). Standard library only.

The file is 84 bytes: b"WCB1", a 16-byte salt, the 32-byte secret XOR a SHAKE-256 keystream, and an HMAC-SHA256 tag over the
magic, salt and ciphertext. scrypt turns the passphrase into one key for the keystream and one for the tag. The tag is checked
before anything is decrypted, so a wrong passphrase and a damaged file look the same, and nothing partial comes back.
"""
import hashlib
import hmac
import secrets
import unicodedata

MAGIC = b"WCB1"
SALT_BYTES = 16
SECRET_BYTES = 32
TAG_BYTES = 32
BLOB_BYTES = len(MAGIC) + SALT_BYTES + SECRET_BYTES + TAG_BYTES
CONTEXT = b"wholecount-secret-backup-v1"


class BackupError(Exception):
    """code: not_a_backup or wrong_passphrase_or_damaged. It never carries the passphrase or any secret byte."""

    def __init__(self, code):
        super().__init__(code)
        self.code = code


def _keys(passphrase, salt):
    dk = hashlib.scrypt(unicodedata.normalize("NFKC", passphrase).encode("utf-8"), salt=salt, n=2 ** 15, r=8, p=1,
                        maxmem=2 ** 26, dklen=64)
    return dk[:32], dk[32:]


def _xor(data, enc_key):
    stream = hashlib.shake_256(CONTEXT + enc_key).digest(len(data))
    return bytes(a ^ b for a, b in zip(data, stream))


def make_backup(secret, passphrase, salt=None):
    if not isinstance(secret, bytes) or len(secret) != SECRET_BYTES:
        raise ValueError("an install secret is 32 bytes")
    salt = secrets.token_bytes(SALT_BYTES) if salt is None else salt
    if len(salt) != SALT_BYTES:
        raise ValueError("the salt is 16 bytes")
    enc_key, mac_key = _keys(passphrase, salt)
    body = MAGIC + salt + _xor(secret, enc_key)
    return body + hmac.new(mac_key, body, hashlib.sha256).digest()


def read_backup(blob, passphrase):
    if not isinstance(blob, (bytes, bytearray)) or len(blob) != BLOB_BYTES or bytes(blob[:4]) != MAGIC:
        raise BackupError("not_a_backup")
    blob = bytes(blob)
    salt = blob[4:4 + SALT_BYTES]
    body, tag = blob[:-TAG_BYTES], blob[-TAG_BYTES:]
    enc_key, mac_key = _keys(passphrase, salt)
    if not hmac.compare_digest(hmac.new(mac_key, body, hashlib.sha256).digest(), tag):
        raise BackupError("wrong_passphrase_or_damaged")
    return _xor(body[4 + SALT_BYTES:], enc_key)
