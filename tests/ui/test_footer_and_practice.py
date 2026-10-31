"""The ledger footer and PRACTICE (SPEC 8.7, 11.3, P-GEO-4)."""
import pytest
from PySide6.QtWidgets import QLabel

from tests.ui.conftest import settle
from tools import screen_fixtures as F
from wholecount import copy
from wholecount.session.commands import SetReviewer
from wholecount.ui.frame.stages import IDS


def test_reviewer_not_asked_yet_before_a_name(make_window):
    w = make_window(F.idle(reviewer="jdoe", reviewer_asked=False))
    assert w.ledger.reviewer.text() == "Reviewer: not asked yet"
    w2 = make_window(F.after_run())
    assert w2.ledger.reviewer.text() == "Reviewer: J. Rivera"


def test_change_fires_set_reviewer_once_with_the_typed_name(make_window):
    w = make_window(F.after_run())
    assert w.change_reviewer("Ana Lee") is None
    cmds = [c for c in w.bridge.dispatched if isinstance(c, SetReviewer)]
    assert len(cmds) == 1 and cmds[0].name == "Ana Lee"


def test_empty_name_shows_the_refusal_and_fires_nothing(make_window):
    w = make_window(F.after_run())
    assert w.change_reviewer("   ") == copy.get("reviewer.refused.empty")
    assert w.change_reviewer("x" * 200) == copy.get("reviewer.refused.too_long", max=60)
    assert not [c for c in w.bridge.dispatched if isinstance(c, SetReviewer)]


def test_set_reviewer_through_the_session_shows_in_the_footer(tmp_path, qtbot, qapp):
    from tests.support.session import base
    from wholecount.ui.frame.bridge import SessionBridge
    from wholecount.ui.frame.window import MainWindow

    s = base(tmp_path)
    b = SessionBridge(s, {"reviewer_asked": False})
    w = MainWindow(b, clock=lambda: F.NOW, confirm=lambda *a: True)
    qtbot.addWidget(w)
    assert w.ledger.reviewer.text() == "Reviewer: not asked yet"
    w.change_reviewer("Ana Lee")
    settle(qapp)
    assert w.ledger.reviewer.text() == "Reviewer: Ana Lee"
    assert s.reviewer == "Ana Lee"
    assert any(e.code == "REVIEWER" for e in s.audit)
    w.closing_confirmed = True


@pytest.mark.claim("CL-PRACTICE-01")
@pytest.mark.claim("CL-PRACTICE-02")
@pytest.mark.parametrize("stage", IDS)
def test_practice_tag_and_line_exactly_when_practice(make_window, stage):
    w = make_window(F.after_run(practice=True), stage=stage)
    assert w.topbar.practice.isVisible() and w.topbar.practice.text() == "PRACTICE"
    assert w.ledger.findChild(QLabel, "practiceLine").text() == copy.get("ledger.batch.practice")
    w2 = make_window(F.after_run(practice=False), stage=stage)
    assert not w2.topbar.practice.isVisible()
    assert w2.ledger.findChild(QLabel, "practiceLine") is None


@pytest.mark.claim("CL-PRACTICE-01")
def test_practice_comes_from_the_sample_run_and_never_a_real_batch(tmp_path):
    """P-GEO-4: the sample reference makes the run practice; a real batch with the fake or no backend never is."""
    from tests.support.session import base
    from wholecount.ui.frame.view import build_view

    s = base(tmp_path)
    assert build_view(s).practice is False
    s.results.practice = True
    assert build_view(s).practice is True


@pytest.mark.claim("CL-CHECK-READY-01")
@pytest.mark.claim("CL-CHECK-READY-02")
def test_check_line_follows_the_preflight(make_window, tmp_path):
    from tests.support.session import base
    from wholecount.ui.frame.view import build_view

    w = make_window(F.after_run(backend="geosupport"))
    assert w.ledger.check_line.text() == copy.get("ledger.foot.check_ok")
    w2 = make_window(F.after_run(backend="none"))
    assert w2.ledger.check_line.text() == copy.get("ledger.foot.check_warn")
    assert w2.ledger.check_line.property("tone") == "amber"
    s = base(tmp_path)
    pre = s.preflight(environ={}, data_dir=tmp_path / "empty")
    assert pre.can_place is False and build_view(s, preflight=pre).can_place is False


def test_saved_text_forms(make_window):
    import datetime as dt

    from wholecount.ui.frame.topbar import saved_text

    v = F.after_run()
    assert saved_text(v.with_(saved_at=F.NOW - dt.timedelta(seconds=20)), F.NOW) == "progress saved just now"
    assert saved_text(v.with_(saved_at=F.NOW - dt.timedelta(minutes=2)), F.NOW) == "progress saved 2 min ago"
    assert saved_text(v.with_(saved_at=F.NOW - dt.timedelta(hours=3)), F.NOW) == "progress saved 3 h ago"
    assert saved_text(v.with_(saved_progress=False), F.NOW) == "saved progress is off"
    assert saved_text(v.with_(saved_at=None), F.NOW) == "nothing to save yet"


def test_backend_text_forms(make_window):
    from wholecount.ui.frame.topbar import backend_text

    assert backend_text(F.idle(backend="geosupport", release="24B")) == ("Geosupport Desktop Edition 24B on this computer", "")
    assert backend_text(F.idle(backend="reference"))[0] == "Address reference file, exact matches only"
    assert backend_text(F.idle(backend="none"))[0] == "Addresses will not be placed"
