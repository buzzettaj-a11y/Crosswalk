"""The install secret (SPEC 5.1, H9): 32 random bytes made at first launch, stored DPAPI-encrypted on Windows.

The secret is never shown, logged or exported. InstallSecret hides its bytes from repr, and only session/keys.py reads them.
"""
import os
import pathlib
import secrets
import sys

from wholecount.brand import PRODUCT_NAME

SECRET_BYTES = 32
KEY_FILE = "key.bin"


class SecretUnreadable(Exception):
    """The store holds something that isn't a readable secret. A new secret is never made over it, because that would change every key."""


class InstallSecret:
    __slots__ = ("_value",)

    def __init__(self, value):
        if not isinstance(value, bytes) or len(value) != SECRET_BYTES:
            raise ValueError("an install secret is 32 bytes")
        self._value = value

    def __repr__(self):
        return "InstallSecret(hidden)"

    __str__ = __repr__

    def __reduce__(self):
        raise TypeError("an install secret is never pickled")


class SecretStore:
    """load() -> bytes or None, save(secret bytes)."""

    def load(self):
        raise NotImplementedError

    def save(self, secret):
        raise NotImplementedError


class DpapiSecretStore(SecretStore):
    """<dir>\\key.bin holds DPAPI's protected blob, never the plain secret."""

    INSECURE = False

    def __init__(self, directory, protect=None, unprotect=None):
        from wholecount.session import dpapi

        self.path = pathlib.Path(directory) / KEY_FILE
        self._protect = protect or dpapi.protect
        self._unprotect = unprotect or dpapi.unprotect

    def load(self):
        from wholecount.session.dpapi import DpapiError

        if not self.path.exists():
            return None
        try:
            value = self._unprotect(self.path.read_bytes())
        except (DpapiError, OSError):
            raise SecretUnreadable() from None
        if len(value) != SECRET_BYTES:
            raise SecretUnreadable()
        return value

    def save(self, secret):
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.path.write_bytes(self._protect(secret))


class FileSecretStore(SecretStore):
    """The Linux test double. It keeps the bytes as they are, so it is never the Windows choice."""

    INSECURE = True

    def __init__(self, directory):
        self.path = pathlib.Path(directory) / KEY_FILE

    def load(self):
        if not self.path.exists():
            return None
        value = self.path.read_bytes()
        if len(value) != SECRET_BYTES:
            raise SecretUnreadable()
        return value

    def save(self, secret):
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.path.write_bytes(secret)


def default_store(platform=None, env=None):
    platform = sys.platform if platform is None else platform
    env = os.environ if env is None else env
    if platform == "win32":
        base = env.get("LOCALAPPDATA") or str(pathlib.Path.home() / "AppData" / "Local")
        return DpapiSecretStore(pathlib.Path(base) / PRODUCT_NAME)
    base = env.get("WHOLECOUNT_DATA_DIR") or str(pathlib.Path.home() / f".{PRODUCT_NAME.lower()}")
    return FileSecretStore(base)


def get_or_create_secret(store):
    """(InstallSecret, created). Makes the secret only when the store is empty."""
    value = store.load()
    if value is not None:
        return InstallSecret(value), False
    value = secrets.token_bytes(SECRET_BYTES)
    store.save(value)
    return InstallSecret(value), True
