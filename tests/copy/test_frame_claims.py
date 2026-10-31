"""The window's claims about data, disk, the network and saved progress (SPEC 11.3, 11.8, H1, H2, H8, H9). Each test proves
the behavior, not the wording."""
import datetime as dt
import json

import pytest

from tests.conftest import ROOT
from tests.fixtures.session import r_fixture
from tests.support.fake_dpapi import FakeDpapi
from tests.support.files_run import ack
from tests.support.geo import fake
from tests.support.guarded import run_guarded
from tests.support.outputs import write
from tests.support.session import decide_all, rk
from tests.support.write_spy import WriteSpy
from wholecount.session import commands as C
from wholecount.session.runner import process
from wholecount.session.store import Store


def _values(s):
    return {v.entered for r in s.results.rows.values() for _, v in r.values.items() if v.entered and len(v.entered) >= 4}


def full_run(tmp_path, monkeypatch, saved):
    """A whole session under the write spy: process, every decision, download. Returns (session, spy, folders)."""
    src, data, down = tmp_path / "src", tmp_path / "data", tmp_path / "down"
    paths = r_fixture.files(src)
    fd = FakeDpapi()
    store = Store(data, fd.protect, fd.unprotect)
    s = r_fixture.session(tmp_path / "w", backend=fake(), paths=paths)
    with WriteSpy(monkeypatch) as spy:
        store.set_saved_progress(saved)
        s.store = store
        process(s)
        decide_all(s)
        ack(s)
        write(s, down)
    return s, spy, {"data": data, "down": down, "store": store, "fd": fd}


@pytest.mark.claim("CL-TRUST-DISK-01")
@pytest.mark.claim("CL-DATA-NEVER-KEPT-01")
@pytest.mark.parametrize("saved", [False, True])
def test_client_data_is_written_only_to_downloads(tmp_path, monkeypatch, saved):
    s, spy, f = full_run(tmp_path, monkeypatch, saved)
    values = _values(s)
    for path, data in spy.writes:
        if path.startswith(str(f["down"])):
            continue
        assert path.startswith(str(f["data"])), path
        assert path.endswith(("prefs.json", ".wcs", ".part", ".tmp")) or "sessions" in path, path
        if data:
            for v in values:
                assert v.encode("utf-8") not in data, (path, v)
    if not saved:
        assert not list((f["data"] / "sessions").glob("*")) if (f["data"] / "sessions").exists() else True


@pytest.mark.claim("CL-TRUST-SAVED-01")
@pytest.mark.claim("CL-DATA-SAVED-01")
def test_saved_progress_holds_decisions_and_setup_never_values(tmp_path, monkeypatch):
    s, spy, f = full_run(tmp_path, monkeypatch, True)
    saved = list((f["data"] / "sessions").glob("*.wcs"))
    assert len(saved) == 1
    raw = saved[0].read_bytes()
    for v in _values(s):
        assert v.encode("utf-8") not in raw
    data = f["store"].load(saved[0])
    assert data["decisions"] and data["setup"]
    text = json.dumps(data)
    for v in _values(s):
        assert v not in text, v
    assert f["fd"].protect(b"x") != b"x"
    now = dt.datetime.now(dt.timezone.utc)
    f["store"].purge_expired(now + dt.timedelta(days=8))
    assert not list((f["data"] / "sessions").glob("*.wcs"))


@pytest.mark.claim("CL-SAVED-OFF-01")
def test_saved_progress_off_saves_nothing(tmp_path, monkeypatch):
    s, spy, f = full_run(tmp_path, monkeypatch, False)
    assert not any(p.endswith(".wcs") for p in spy.paths())


@pytest.mark.claim("CL-SAVED-TIME-01")
def test_saved_time_comes_from_the_save(tmp_path, qtbot, qapp):
    from tests.ui.conftest import settle
    from tools import screen_fixtures as F
    from wholecount.ui.frame.bridge import SessionBridge
    from wholecount.ui.frame.window import MainWindow

    s = r_fixture.session(tmp_path / "w", backend=fake(), paths=r_fixture.files(tmp_path / "src"))
    process(s)
    fd = FakeDpapi()
    s.store = Store(tmp_path / "data", fd.protect, fd.unprotect)
    b = SessionBridge(s, {"saved_progress": True}, clock=s.clock)
    w = MainWindow(b, clock=lambda: s.clock.t, confirm=lambda *a: True)
    qtbot.addWidget(w)
    assert w.topbar.saved.text() == "nothing to save yet"
    b.dispatch(C.SetAsideRows([rk(s, "R14")], "out_of_scope"))
    settle(qapp)
    assert list((tmp_path / "data" / "sessions").glob("*.wcs"))
    assert w.topbar.saved.text() == "progress saved just now"
    s.clock.t += dt.timedelta(minutes=5)
    w._refresh_saved()
    assert w.topbar.saved.text() == "progress saved 5 min ago"
    w.closing_confirmed = True


@pytest.mark.claim("CL-START-DELETES-01")
def test_start_over_deletes_saved_progress_and_clears_memory(tmp_path, qtbot, qapp):
    from tests.ui.conftest import Confirm
    from tools import screen_fixtures as F
    from wholecount.ui.frame.bridge import SessionBridge
    from wholecount.ui.frame.window import MainWindow

    paths = r_fixture.files(tmp_path / "src")
    s = r_fixture.session(tmp_path / "w", backend=fake(), paths=paths)
    process(s)
    fd = FakeDpapi()
    s.store = Store(tmp_path / "data", fd.protect, fd.unprotect)
    s.history.execute(C.SetAsideRows([rk(s, "R14")], "out_of_scope"))
    down = tmp_path / "down"
    ack(s)
    write(s, down)
    downloaded = sorted(p.name for p in down.iterdir())
    assert list((tmp_path / "data" / "sessions").glob("*.wcs"))
    b = SessionBridge(s, {"saved_progress": True})
    c = Confirm(True)
    w = MainWindow(b, clock=lambda: F.NOW, confirm=c)
    qtbot.addWidget(w)
    assert w.request_start_over()
    assert c.asked[0][1] == ("This clears the batch from memory and deletes its saved progress.",)
    assert not list((tmp_path / "data" / "sessions").glob("*.wcs"))
    assert b.session is not s and b.session.results is None and not list(b.session.decisions)
    assert sorted(p.name for p in down.iterdir()) == downloaded
    assert w.current == "sources"
    w.closing_confirmed = True


def test_start_over_declined_keeps_everything(tmp_path, qtbot):
    from tests.ui.conftest import Confirm
    from tools import screen_fixtures as F
    from wholecount.ui.frame.bridge import StaticBridge
    from wholecount.ui.frame.window import MainWindow

    b = StaticBridge(F.after_run())
    w = MainWindow(b, clock=lambda: F.NOW, confirm=Confirm(False))
    qtbot.addWidget(w)
    assert w.request_start_over() is False
    assert getattr(b, "start_over_calls", 0) == 0
    w.closing_confirmed = True


@pytest.mark.claim("CL-AUDIT-NOCELLS-01")
def test_neither_audit_log_holds_a_cell_value(tmp_path, monkeypatch):
    s, spy, f = full_run(tmp_path, monkeypatch, False)
    logs = [p for p in f["down"].iterdir() if "Audit" in p.name or "audit" in p.name]
    assert len(logs) == 2
    for p in logs:
        text = p.read_bytes()
        for v in _values(s):
            assert v.encode("utf-8") not in text, (p.name, v)


GUARDED_RUN = """
import pathlib, tempfile
from tests.fixtures.session import r_fixture
from tests.support.geo import fake
from tests.support.session import decide_all
from wholecount.session.runner import process
t = pathlib.Path(tempfile.mkdtemp())
s = r_fixture.session(t / "w", backend=fake(), paths=r_fixture.files(t / "src"))
process(s)
decide_all(s)
out["counted"] = 'ok' if s.results.counts.counted else 'none'
attempt("socket", lambda: __import__("socket").create_connection(("127.0.0.1", 9), 1))
"""


@pytest.mark.claim("CL-TRUST-OFFLINE-01")
@pytest.mark.claim("CL-DATA-NEVER-NET-01")
@pytest.mark.claim("CL-DATA-MEMORY-01")
def test_a_whole_session_runs_with_the_network_blocked(tmp_path):
    out = run_guarded(GUARDED_RUN)
    assert out["counted"] == "ok"
    assert out["socket"] == "blocked"


@pytest.mark.claim("CL-TRUST-OFFLINE-01")
@pytest.mark.claim("CL-DATA-NEVER-NET-01")
def test_no_network_module_in_the_ui():
    from tools.offline_scan import scan_imports, scan_url_literals

    paths = sorted((ROOT / "wholecount").rglob("*.py"))
    assert scan_imports(paths, ROOT) == []
    assert scan_url_literals(paths, ROOT) == []


@pytest.mark.claim("CL-DATA-NEVER-AI-01")
def test_there_is_no_ai_in_the_app():
    from tools.offline_rules import FORBIDDEN_DISTS, MODEL_FILE_SUFFIXES
    from tools.offline_scan import check_lock_clean, scan_imports

    ai = {"openai", "anthropic", "transformers", "torch", "tensorflow", "onnxruntime", "llama_cpp", "sklearn"}
    paths = sorted((ROOT / "wholecount").rglob("*.py"))
    assert scan_imports(paths, ROOT, frozenset(ai)) == []
    assert check_lock_clean((ROOT / "requirements.lock").read_text(encoding="utf-8")) == []
    assert {"openai", "anthropic"} <= {d.lower() for d in FORBIDDEN_DISTS}
    assert not [p for p in (ROOT / "wholecount").rglob("*") if p.suffix in MODEL_FILE_SUFFIXES]


@pytest.mark.claim("CL-DATA-MEMORY-01")
def test_every_step_works_in_memory(tmp_path, monkeypatch):
    """Tidying, checking, placing, matching and counting write nothing; only downloads do."""
    s, spy, f = full_run(tmp_path, monkeypatch, False)
    assert {p for p in spy.paths() if not p.startswith(str(f["down"]))} <= {str(f["data"] / "prefs.json"),
                                                                          str(f["data"] / ".prefs.json.part")} | {
        p for p in spy.paths() if p.startswith(str(f["data"])) and "prefs" in p}
