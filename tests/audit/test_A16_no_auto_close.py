"""A-16: the old tool closed itself after 45 seconds without a heartbeat. Wholecount closes only when the operator closes
it or the operating system ends it. There's no timer, heartbeat or idle limit, and both close paths run the same code."""
import ast
import re

import pytest
from PySide6.QtCore import QTimer

from tests.conftest import ROOT
from tests.ui.conftest import Confirm, make_window, settle, themed  # noqa: F401  fixtures
from tools import screen_fixtures as F
from wholecount import copy

UI = ROOT / "wholecount" / "ui"


def test_window_stays_open_through_ten_minutes(make_window, qapp, monkeypatch):
    """A fake clock moves 10 minutes while the event loop runs every timer the window has."""
    import datetime as dt

    w = make_window(F.after_run())
    t = {"now": F.NOW}
    w.clock = lambda: t["now"]
    for minute in range(10):
        t["now"] = F.NOW + dt.timedelta(minutes=minute + 1)
        for timer in w.findChildren(QTimer):
            if timer.isActive():
                timer.timeout.emit()
        settle(qapp, 2)
        assert w.isVisible()
    assert w.close_requests == 0


def _calls_close(node):
    for n in ast.walk(node):
        if isinstance(n, ast.Call):
            f = n.func
            name = f.attr if isinstance(f, ast.Attribute) else getattr(f, "id", "")
            if name in ("close", "quit", "exit", "request_close", "closeAllWindows"):
                return True
    return False


CLOSERS = ("close", "quit", "exit", "request_close", "closeAllWindows")
TIMED = ("timeout", "started", "finished", "singleShot")


def timed_closers(tree):
    """Timer, thread and single-shot callbacks that would close the window."""
    bad = []
    for n in ast.walk(tree):
        if not isinstance(n, ast.Call):
            continue
        f = n.func
        timed = (isinstance(f, ast.Attribute) and f.attr == "connect" and isinstance(f.value, ast.Attribute)
                 and f.value.attr in TIMED) or (isinstance(f, ast.Attribute) and f.attr == "singleShot")
        if not timed:
            continue
        for arg in n.args:
            target = getattr(arg, "attr", getattr(arg, "id", ""))
            if target in CLOSERS or (isinstance(arg, ast.Lambda) and _calls_close(arg)):
                bad.append(n.lineno)
    return bad


def test_no_timer_or_thread_closes_and_no_idle_constant():
    for p in UI.rglob("*.py"):
        src = p.read_text(encoding="utf-8")
        assert timed_closers(ast.parse(src)) == [], p
        names = {n.id for n in ast.walk(ast.parse(src)) if isinstance(n, ast.Name)}
        assert not {n for n in names if re.fullmatch(r"(IDLE|GRACE|IDLE_LIMIT|GRACE_AFTER_CLOSE|CLOSE_AFTER)\w*", n)}, p


def test_scan_negative_controls():
    bad = ast.parse("t.timeout.connect(self.close)\nQTimer.singleShot(45000, lambda: app.quit())\n"
                    "b.clicked.connect(self.close)\n")
    assert timed_closers(bad) == [1, 2]


@pytest.mark.claim("CL-CLOSE-CLEARS-01")
@pytest.mark.claim("CL-CLOSE-KEEPS-01")
def test_button_and_title_bar_run_the_same_path(make_window):
    c = Confirm(False)
    w = make_window(F.after_run(), confirm=c)
    w.ledger.close_button.click()
    assert w.isVisible() and len(c.asked) == 1
    w.close()                              # the title bar sends the same close event
    assert w.isVisible() and len(c.asked) == 2
    assert c.asked[0] == c.asked[1]
    title, lines, yes, no = c.asked[0]
    assert title == "Close Wholecount?" and yes == "Close Wholecount" and no == "Keep working"
    assert lines == (copy.get("close.confirm"), copy.get("close.saved_on"))
    c.answer = True
    w.close()
    assert not w.isVisible()


def test_no_batch_closes_at_once_and_off_says_nothing_is_kept(make_window):
    c = Confirm(True)
    w = make_window(F.idle(), confirm=c)
    w.close()
    assert c.asked == [] and not w.isVisible()
    c2 = Confirm(False)
    w2 = make_window(F.after_run(saved_progress=False), confirm=c2)
    w2.close()
    assert c2.asked[0][1] == (copy.get("close.confirm"), copy.get("close.saved_off"))


def test_running_job_is_cancelled_with_the_extra_line(make_window, qtbot):
    import threading

    c = Confirm(True)
    w = make_window(F.after_run(), confirm=c)
    gate = threading.Event()
    w.start_job(F.DemoJob(seconds=1.0, sleep=lambda s: gate.wait(0.01)))
    w.close()
    assert c.asked[0][1][-1] == copy.get("close.running")
    assert not w.bridge.runner.running


@pytest.mark.claim("CL-CLOSE-CLEARS-01")
def test_closing_lets_go_of_the_batch_and_writes_nothing(tmp_path, qtbot, qapp, monkeypatch):
    """With saved progress off, closing writes nothing, the window lets go of the session, and the app quits when its
    last window closes, so the operating system takes the memory back."""
    from tests.support.session import base
    from tests.support.write_spy import WriteSpy
    from wholecount.ui.frame.bridge import SessionBridge
    from wholecount.ui.frame.window import MainWindow

    s = base(tmp_path)
    b = SessionBridge(s, {"saved_progress": False})
    w = MainWindow(b, clock=lambda: F.NOW, confirm=lambda *a: True)
    qtbot.addWidget(w)
    w.show()
    with WriteSpy(monkeypatch) as spy:
        w.close()
        settle(qapp)
    assert spy.writes == []
    assert b.session is None
    assert qapp.quitOnLastWindowClosed()


@pytest.mark.claim("CL-CLOSE-KEEPS-01")
def test_saved_progress_keeps_decisions_for_seven_days(tmp_path):
    import datetime as dt

    from tests.support.fake_dpapi import FakeDpapi
    from tests.support.session import base, rk
    from wholecount.session import commands as C
    from wholecount.session.store import Store

    s = base(tmp_path / "w")
    fd = FakeDpapi()
    s.store = Store(tmp_path / "store", fd.protect, fd.unprotect)
    s.history.execute(C.SetAsideRows([rk(s, "R14")], "out_of_scope"))
    saved = list(s.store.sessions.glob("*.wcs"))
    assert saved
    data = s.store.load(saved[0])
    assert data["decisions"] and data["setup"]
    now = dt.datetime.now(dt.timezone.utc)
    s.store.purge_expired(now + dt.timedelta(days=6))
    assert list(s.store.sessions.glob("*.wcs"))
    s.store.purge_expired(now + dt.timedelta(days=8))
    assert not list(s.store.sessions.glob("*.wcs"))
