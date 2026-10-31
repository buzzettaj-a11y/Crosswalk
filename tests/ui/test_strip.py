"""The stage strip (SPEC 11.3): four states and stale, tooltips, accessible names, and the Undo item."""
import pytest

from tests.ui.conftest import settle
from tools import screen_fixtures as F
from wholecount.ui.frame.captions import stage_caption
from wholecount.ui.frame.stages import STAGES
from wholecount.ui.frame.view import RESULT_STAGES


def test_items_follow_states(make_window):
    w = make_window(F.after_run(), stage="review")
    items = w.strip.items
    assert items["review"].state == "current"
    assert items["sources"].state == "done"
    assert items["schema"].state == "nothing"
    assert items["summary"].state == "later"
    assert items["review"].accessibleName().endswith(", current stage")
    assert items["review"].accessibleName().startswith("Stage 07, Fix problems, 1,232 rows open")


def test_tooltip_and_description_are_the_full_caption(make_window):
    v = F.maximal()
    w = make_window(v, width=1280, stage="sources")
    for s in STAGES:
        it = w.strip.items[s.id]
        full = stage_caption(s.id, v).text
        assert it.toolTip() == full and it.accessibleDescription() == full


@pytest.mark.claim("CL-STALE-CAPTION-01")
def test_stale_items_say_out_of_date(make_window):
    w = make_window(F.after_run(stale=frozenset(RESULT_STAGES), counts=None), stage="run")
    for sid in RESULT_STAGES:
        it = w.strip.items[sid]
        assert it.stale and it.full_caption == "out of date"
        assert it.accessibleName().endswith(", out of date")


def test_no_scroll_area_in_the_strip(make_window):
    from PySide6.QtWidgets import QAbstractScrollArea

    w = make_window(F.after_run())
    assert not w.strip.findChildren(QAbstractScrollArea)


@pytest.mark.claim("CL-UNDO-ONE-01")
def test_undo_shows_the_top_label_and_calls_the_bridge_once(make_window, qtbot):
    from PySide6.QtCore import Qt

    w = make_window(F.after_run())
    u = w.strip.undo
    assert u.full_label == "Set aside 96 rows"
    qtbot.mouseClick(u, Qt.LeftButton)
    assert w.bridge.undo_calls == 1


@pytest.mark.claim("CL-UNDO-ONE-01")
def test_empty_stack_reads_nothing_to_undo_and_is_held(make_window, qtbot):
    from PySide6.QtCore import Qt

    w = make_window(F.idle())
    u = w.strip.undo
    assert u.full_label == "Nothing to undo" and u.held
    qtbot.mouseClick(u, Qt.LeftButton)
    assert w.bridge.undo_calls == 0


@pytest.mark.claim("CL-UNDO-ONE-01")
def test_one_undo_takes_back_one_command(tmp_path):
    """Behavior behind the claim: the label is the top command, and one undo pops exactly that one."""
    from tests.support.session import base, group, rk
    from wholecount.session import commands as C
    from wholecount.ui.frame.view import build_view

    s = base(tmp_path)
    s.history.execute(C.SetAsideRows([rk(s, "R14")], "out_of_scope"))
    s.history.execute(C.KeepOneInCopyGroup(group(s, "identical").group_id, group(s, "identical").members[0]))
    assert build_view(s).undo_label == ("commands.keep_one", {})
    s.history.undo()
    assert build_view(s).undo_label == ("commands.set_aside_rows", {"count": 1})
    assert len(s.history.stack) == 1


def test_clicking_an_item_goes_to_that_stage(make_window, qtbot, qapp):
    from PySide6.QtCore import Qt

    w = make_window(F.after_run(), stage="sources")
    qtbot.mouseClick(w.strip.items["summary"], Qt.LeftButton)
    settle(qapp)
    assert w.current == "summary"
    assert w.stage_widget.head.title.text() == "Results"


def test_run_underline_fills_for_owners(make_window):
    w = make_window(F.after_run())
    w.strip.set_run_fractions({"run": 0.5, "summary": 0.0})
    assert w.strip.items["run"].run_fraction == 0.5
    assert w.strip.items["review"].run_fraction is None
    w.strip.set_run_fractions(None)
    assert w.strip.items["run"].run_fraction is None
