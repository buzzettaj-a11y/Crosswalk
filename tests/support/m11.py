"""Helpers for M11 stage tests: a real session over the example files (or literal CSVs) in a real window."""
import csv
import json

from tests.conftest import ROOT
from tests.ui.conftest import Confirm, settle
from tools import screen_fixtures as F

DATA = ROOT / "wholecount" / "sample_data"
EXPECTED = json.loads((DATA / "EXPECTED.json").read_text(encoding="utf-8"))


def write_csv(path, header, rows):
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(header)
        w.writerows(rows)
    return path


def window_for(qtbot, qapp, session, stage="sources", width=1440, height=900, confirm=None, ui=None):
    from wholecount.ui.frame.bridge import SessionBridge
    from wholecount.ui.frame.window import MainWindow

    b = SessionBridge(session, {"saved_progress": False, **(ui or {})})
    w = MainWindow(b, clock=lambda: F.NOW, confirm=confirm or Confirm(True))
    qtbot.addWidget(w)
    w.resize(width, height)
    w.show()
    w.go_to(stage)
    settle(qapp)
    return w


def example_window(qtbot, qapp, tmp_path, stage="sources", **kw):
    from tests.support.example_session import example_session

    s = example_session(tmp_path)
    return window_for(qtbot, qapp, s, stage, **kw), s


def empty_session(tmp_path, backend=None):
    from tests.fixtures.session import r_fixture
    from wholecount.engine.geo.backend import NoBackend

    s = r_fixture.session(tmp_path, backend=backend or NoBackend(), paths=[])
    s.setup.sections["sources"].clear()
    return s


def run_job(qtbot, qapp, w, start):
    with qtbot.waitSignal(w.bridge.runner.finished, timeout=60000):
        assert start()
    settle(qapp)


def last(session, cls=None):
    stack = session.history.stack
    if cls is None:
        return stack[-1]
    return [c for c in stack if isinstance(c, cls)][-1]


def find(w, cls, name):
    return w.findChild(cls, name)
