"""Saved progress and set-ups (SPEC 10.1 to 10.3): STORE-1 to STORE-8."""
import datetime as dt
import json
import os

import pytest

from tests.fixtures.outputs.fixture import VALUES, rows, session
from tests.fixtures.session import r_fixture
from tests.support.fake_dpapi import FakeDpapi
from tests.support.session import rk
from wholecount.session import commands as C
from wholecount.session.resume import resume
from wholecount.session.store import Store, StoreError, export_setup, import_setup, snapshot
from wholecount.session.state import Setup


@pytest.fixture()
def store(tmp_path):
    fd = FakeDpapi()
    return Store(tmp_path / "data", fd.protect, fd.unprotect)


def test_STORE_1_folders(store):
    assert store.sessions.name == "sessions" and store.setups.name == "setups"


def test_STORE_2_contents_hold_no_values(tmp_path, store):
    s = session(tmp_path, "decided")
    path = store.save("x", snapshot(s))
    raw = path.read_bytes()
    assert raw.startswith(b"WCS1")
    text = json.dumps(store.load(path))
    for v in VALUES + ["00123"]:
        assert v not in text and v.encode() not in raw, v
    assert set(store.load(path)) == {"format", "app_version", "saved_at", "setup", "decisions", "sources"}


def test_STORE_3_autosave_and_switch_off(tmp_path, store):
    s = session(tmp_path)
    s.store = store
    s.history.execute(C.SetAsideRows([rk(s, "00123")], "test_record"))
    assert len(list(store.sessions.glob("*.wcs"))) == 1
    store.set_saved_progress(False)
    assert list(store.sessions.glob("*.wcs")) == []
    s.history.execute(C.SetAsideRows([rk(s, "R02")], "test_record"))
    assert list(store.sessions.glob("*.wcs")) == []
    assert json.loads((store.base / "prefs.json").read_text()) == {"saved_progress": False}


def test_STORE_4_purge(tmp_path, store):
    s = session(tmp_path)
    old = store.save("old", snapshot(s))
    new = store.save("new", snapshot(s))
    now = dt.datetime(2026, 10, 31, tzinfo=dt.timezone.utc)
    os.utime(old, (now.timestamp() - 8 * 86400,) * 2)
    os.utime(new, (now.timestamp() - 6 * 86400,) * 2)
    assert store.purge_expired(now) == 1 and not old.exists() and new.exists()


def test_STORE_5_errors(tmp_path, store):
    s = session(tmp_path)
    path = store.save("x", snapshot(s))
    other = Store(store.base, *(lambda fd: (fd.protect, fd.unprotect))(FakeDpapi()))
    with pytest.raises(StoreError, match="other_user"):
        other.load(path)
    raw = bytearray(path.read_bytes())
    raw[-5] ^= 1
    path.write_bytes(bytes(raw))
    with pytest.raises(StoreError, match="damaged"):
        store.load(path)
    p2 = store.save("y", {"format": 99})
    with pytest.raises(StoreError, match="unknown_version"):
        store.load(p2)


@pytest.mark.claim("CL-OUT-13")
def test_STORE_6_setups(tmp_path, store):
    from wholecount import copy

    s = session(tmp_path)
    s.setup.set("mappings", ("R.csv", 0, "Program"), "Program")
    export_setup(s.setup, tmp_path / "setup.json")
    fresh = import_setup(tmp_path / "setup.json", Setup())
    assert fresh.get("mappings", ("R.csv", 0, "Program")) == "Program"
    assert store.load_setup(store.save_setup("mine", s.setup))["name"] == "mine"
    assert "no client data" in copy.get("setups.export_note")


def test_STORE_7_resume(tmp_path, store):
    s = session(tmp_path, "decided")
    saved = store.load(store.save("x", snapshot(s)))
    s2 = r_fixture.session(tmp_path / "in2", paths=r_fixture.files(tmp_path / "in2", r=rows()), districts=s.districts)
    plan = resume(s2, saved, [tmp_path / "in2" / "R.csv", tmp_path / "in2" / "S.csv"])
    assert plan.restored == ("R.csv", "S.csv") and plan.changed == () and plan.lapsed == 0 and plan.kept == len(s.decisions)
    assert s2.results.digest() == s.results.digest()


@pytest.mark.claim("CL-OUT-11")
@pytest.mark.claim("CL-OUT-12")
def test_STORE_8_what_is_written(tmp_path, store):
    from wholecount import copy

    s = session(tmp_path)
    s.store = store
    store.set_saved_progress(False)
    s.history.execute(C.SetAsideRows([rk(s, "00123")], "test_record"))
    assert sorted(p.name for p in store.base.rglob("*") if p.is_file()) == ["prefs.json"]
    store.set_saved_progress(True)
    s.history.execute(C.SetAsideRows([rk(s, "R02")], "test_record"))
    assert {p.name for p in store.base.rglob("*") if p.is_file()} == {"prefs.json", f"{s.session_id}.wcs"}
    assert copy.get("outputs.writes.saved_progress_off") and "7 days" in copy.get("outputs.writes.saved_progress_on")
