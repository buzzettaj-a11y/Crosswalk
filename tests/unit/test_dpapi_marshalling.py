"""DPAPI's DATA_BLOB handling, driven through a fake crypt32 so it runs on Linux."""
import pytest

from tests.support.fake_dpapi import FakeDpapi
from wholecount.session.dpapi import DpapiError


def test_round_trip_and_blobs_seen():
    d = FakeDpapi()
    secret = bytes(range(32))
    blob = d.protect(secret)
    assert blob != secret and len(blob) > len(secret)
    assert d.unprotect(blob) == secret
    kinds = [c[0] for c in d.crypt32.calls]
    assert kinds == ["protect", "unprotect"]
    assert d.crypt32.calls[0][1] == secret and d.crypt32.calls[0][2] == blob
    assert d.kernel32.freed == 2


def test_flipped_byte_raises_and_frees_nothing_partial():
    d = FakeDpapi()
    blob = bytearray(d.protect(b"x" * 32))
    blob[3] ^= 1
    with pytest.raises(DpapiError):
        d.unprotect(bytes(blob))
    assert d.kernel32.freed == 1


def test_another_users_blob_raises():
    blob = FakeDpapi().protect(b"x" * 32)
    with pytest.raises(DpapiError):
        FakeDpapi().unprotect(blob)


def test_empty_data():
    d = FakeDpapi()
    assert d.unprotect(d.protect(b"")) == b""
