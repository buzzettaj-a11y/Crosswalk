"""Windows DPAPI for the current user (SPEC 3.1, H9), through ctypes.

The DATA_BLOB handling sits in small functions that take the library objects as arguments, so Linux tests pass a fake crypt32
and kernel32 (tests/support/fake_dpapi.py). Output bytes are read by slicing the blob pointer, never with ctypes.string_at,
which the offline guard denies.
"""
import ctypes

from wholecount.guard.config import DPAPI_DLL_NAMES

CRYPTPROTECT_UI_FORBIDDEN = 0x1


class DpapiError(Exception):
    """A blob that can't be unprotected: damaged, or protected by another Windows user. Never carries partial data."""


class DATA_BLOB(ctypes.Structure):
    _fields_ = [("cbData", ctypes.c_uint32), ("pbData", ctypes.POINTER(ctypes.c_char))]


def blob_in(data):
    """(DATA_BLOB, buffer). Keep the buffer alive while the blob is in use."""
    buf = ctypes.create_string_buffer(bytes(data), len(data))
    return DATA_BLOB(len(data), ctypes.cast(buf, ctypes.POINTER(ctypes.c_char))), buf


def blob_bytes(blob):
    if not blob.cbData:
        return b""
    return bytes(blob.pbData[:blob.cbData])


def protect_with(crypt32, kernel32, data):
    in_blob, _keep = blob_in(data)
    out = DATA_BLOB()
    ok = crypt32.CryptProtectData(ctypes.byref(in_blob), None, None, None, None, CRYPTPROTECT_UI_FORBIDDEN, ctypes.byref(out))
    if not ok:
        raise DpapiError("protect failed")
    try:
        return blob_bytes(out)
    finally:
        kernel32.LocalFree(out.pbData)


def unprotect_with(crypt32, kernel32, blob):
    in_blob, _keep = blob_in(blob)
    out = DATA_BLOB()
    ok = crypt32.CryptUnprotectData(ctypes.byref(in_blob), None, None, None, None, CRYPTPROTECT_UI_FORBIDDEN, ctypes.byref(out))
    if not ok:
        raise DpapiError("unprotect failed")
    try:
        return blob_bytes(out)
    finally:
        kernel32.LocalFree(out.pbData)


def _libraries():
    crypt32_name, kernel32_name = DPAPI_DLL_NAMES
    return ctypes.WinDLL(crypt32_name), ctypes.WinDLL(kernel32_name)


def protect(data):
    return protect_with(*_libraries(), data)


def unprotect(blob):
    return unprotect_with(*_libraries(), blob)
