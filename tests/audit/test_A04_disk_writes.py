"""A-04: the old app wrote session files with client values to disk. Only key.bin, prefs.json, downloads and, when on, one
encrypted saved-progress file are written, and that file holds no value (H9)."""
import json


from tests.fixtures.outputs.fixture import VALUES, rows
from tests.fixtures.session import r_fixture
from tests.support.fake_dpapi import FakeDpapi
from tests.support.files_run import ack
from tests.support.outputs import write
from tests.support.session import decide_all
from wholecount.session.runner import process
from wholecount.session.secret_store import default_store, get_or_create_secret
from wholecount.session.store import Store


def run(tmp_path, monkeypatch, saved):
    data, work, down, src = tmp_path / "data", tmp_path / "work", tmp_path / "down", tmp_path / "src"
    for d in (work, down):
        d.mkdir()
    paths = r_fixture.files(src, r=rows())
    before = {p for p in tmp_path.rglob("*")}
    monkeypatch.chdir(work)
    secret, _ = get_or_create_secret(default_store(platform="linux", env={"WHOLECOUNT_DATA_DIR": str(data)}))
    fd = FakeDpapi()
    store = Store(data, fd.protect, fd.unprotect)
    store.set_saved_progress(saved)
    s = r_fixture.session(tmp_path / "unused", paths=paths)
    s.secret, s.store = secret, store
    process(s)
    decide_all(s)
    ack(s)
    write(s, down)
    created = {p for p in tmp_path.rglob("*") if p.is_file()} - before
    return s, store, {p.relative_to(tmp_path).as_posix() for p in created}


def test_saved_progress_off(tmp_path, monkeypatch):
    s, store, created = run(tmp_path, monkeypatch, False)
    downloads = {c for c in created if c.startswith("down/")}
    assert created - downloads == {"data/key.bin", "data/prefs.json"}


def test_saved_progress_on_and_switched_off(tmp_path, monkeypatch):
    s, store, created = run(tmp_path, monkeypatch, True)
    downloads = {c for c in created if c.startswith("down/")}
    wcs = [c for c in created - downloads if c.endswith(".wcs")]
    assert created - downloads - set(wcs) == {"data/key.bin", "data/prefs.json"} and len(wcs) == 1
    text = json.dumps(store.load(tmp_path / wcs[0]))
    for v in VALUES + ["00123"]:
        assert v not in text, v
    store.set_saved_progress(False)
    assert not (tmp_path / wcs[0]).exists()
