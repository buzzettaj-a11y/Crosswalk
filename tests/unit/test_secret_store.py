"""The install secret (SPEC 5.1, H9). Tests never touch the real store."""
import pytest

from tests.support.fake_dpapi import FakeDpapi
from wholecount.session.secret_store import (
    DpapiSecretStore, FileSecretStore, InstallSecret, SecretUnreadable, default_store, get_or_create_secret,
)


def test_first_call_creates_32_bytes_and_second_returns_the_same(tmp_path):
    store = FileSecretStore(tmp_path)
    s1, created1 = get_or_create_secret(store)
    s2, created2 = get_or_create_secret(store)
    assert created1 is True and created2 is False
    assert len(s1._value) == 32 and s1._value == s2._value


def test_unreadable_store_raises_and_makes_nothing(tmp_path):
    (tmp_path / "key.bin").write_bytes(b"short")
    with pytest.raises(SecretUnreadable):
        get_or_create_secret(FileSecretStore(tmp_path))
    assert (tmp_path / "key.bin").read_bytes() == b"short"


def test_damaged_dpapi_blob_raises_and_makes_nothing(tmp_path):
    d = FakeDpapi()
    store = DpapiSecretStore(tmp_path, d.protect, d.unprotect)
    get_or_create_secret(store)
    blob = bytearray((tmp_path / "key.bin").read_bytes())
    blob[0] ^= 0xFF
    (tmp_path / "key.bin").write_bytes(bytes(blob))
    with pytest.raises(SecretUnreadable):
        get_or_create_secret(store)
    assert (tmp_path / "key.bin").read_bytes() == bytes(blob)


def test_dpapi_store_round_trip_never_writes_the_plain_secret(tmp_path):
    d = FakeDpapi()
    store = DpapiSecretStore(tmp_path, d.protect, d.unprotect)
    s, created = get_or_create_secret(store)
    on_disk = (tmp_path / "key.bin").read_bytes()
    assert created and s._value not in on_disk and len(on_disk) > 32
    assert get_or_create_secret(store)[0]._value == s._value


def test_secret_is_not_in_repr_str_or_pickle():
    s = InstallSecret(bytes(range(32)))
    assert bytes(range(32)).hex() not in repr(s) and "hidden" in repr(s) and str(s) == repr(s)
    import pickle
    with pytest.raises(TypeError):
        pickle.dumps(s)


def test_install_secret_needs_32_bytes():
    with pytest.raises(ValueError):
        InstallSecret(b"x" * 31)


def test_store_choice_by_platform(tmp_path):
    linux = default_store(platform="linux", env={"WHOLECOUNT_DATA_DIR": str(tmp_path)})
    assert isinstance(linux, FileSecretStore) and linux.INSECURE and linux.path == tmp_path / "key.bin"
    win = default_store(platform="win32", env={"LOCALAPPDATA": str(tmp_path)})
    assert isinstance(win, DpapiSecretStore) and not win.INSECURE
    assert win.path.parent.name == "Wholecount" and win.path.name == "key.bin"
