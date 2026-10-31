"""A Linux double for crypt32 and kernel32 (M01, reused by M05 and M09).

Reversible and keyed per instance: protect XORs with a keystream and appends an HMAC tag, so a flipped byte or another
instance's blob fails the way DPAPI fails for a damaged blob or another Windows user. It records every blob it sees.
"""
import ctypes
import hashlib
import hmac
import secrets

from wholecount.session import dpapi


class FakeCrypt32:
    def __init__(self, kernel32):
        self._key = secrets.token_bytes(32)
        self._kernel32 = kernel32
        self.calls = []

    def _stream(self, n):
        out, i = b"", 0
        while len(out) < n:
            out += hashlib.sha256(self._key + i.to_bytes(4, "big")).digest()
            i += 1
        return out[:n]

    def _write(self, out_ref, data):
        buf = ctypes.create_string_buffer(data, len(data))
        out = out_ref._obj
        out.cbData = len(data)
        out.pbData = ctypes.cast(buf, ctypes.POINTER(ctypes.c_char))
        self._kernel32.allocated.append(buf)

    def CryptProtectData(self, in_ref, desc, entropy, reserved, prompt, flags, out_ref):
        data = dpapi.blob_bytes(in_ref._obj)
        body = bytes(a ^ b for a, b in zip(data, self._stream(len(data))))
        blob = body + hmac.new(self._key, body, hashlib.sha256).digest()
        self.calls.append(("protect", data, blob))
        self._write(out_ref, blob)
        return 1

    def CryptUnprotectData(self, in_ref, desc, entropy, reserved, prompt, flags, out_ref):
        blob = dpapi.blob_bytes(in_ref._obj)
        body, tag = blob[:-32], blob[-32:]
        if len(blob) < 32 or not hmac.compare_digest(tag, hmac.new(self._key, body, hashlib.sha256).digest()):
            self.calls.append(("unprotect failed", blob, None))
            return 0
        data = bytes(a ^ b for a, b in zip(body, self._stream(len(body))))
        self.calls.append(("unprotect", blob, data))
        self._write(out_ref, data)
        return 1


class FakeKernel32:
    def __init__(self):
        self.allocated = []
        self.freed = 0

    def LocalFree(self, ptr):
        self.freed += 1
        return None


class FakeDpapi:
    """protect and unprotect functions bound to one fake crypt32, for DpapiSecretStore."""

    def __init__(self):
        self.kernel32 = FakeKernel32()
        self.crypt32 = FakeCrypt32(self.kernel32)

    def protect(self, data):
        return dpapi.protect_with(self.crypt32, self.kernel32, data)

    def unprotect(self, blob):
        return dpapi.unprotect_with(self.crypt32, self.kernel32, blob)
