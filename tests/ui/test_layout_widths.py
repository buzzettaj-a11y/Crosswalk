"""The frame at 1280, 1366, 1440 and 1920 wide, on all nine stages, with a maximal view (SPEC 11.1, 11.4)."""
import pytest
from PySide6.QtWidgets import QAbstractScrollArea, QWidget

from tests.ui.conftest import settle
from tools import screen_fixtures as F
from wholecount.ui.frame.stages import IDS

WIDTHS = (1280, 1366, 1440, 1920)


def _visible_children(w):
    return [c for c in w.findChildren(QWidget) if c.isVisible() and c.window() is w and not c.isWindow()]


@pytest.mark.parametrize("width", WIDTHS)
@pytest.mark.parametrize("stage", IDS)
def test_no_sideways_scroll_and_everything_inside(make_window, width, stage):
    w = make_window(F.maximal(), width=width, height=900, stage=stage)
    assert w.width() == width
    assert not w.stage_area.horizontalScrollBar().isVisible()
    assert w.minimumSizeHint().width() <= width
    for c in _visible_children(w):
        if c.parentWidget() is None or c.objectName() == "liveRegion":
            continue
        right = c.mapTo(w, c.rect().topRight()).x()
        assert right <= width, (c.metaObject().className(), c.objectName(), right)
    assert not w.strip.findChildren(QAbstractScrollArea)
    for it in w.strip.items.values():
        assert it.name.height() >= it.name.heightForWidth(it.name.width()) or it.name.heightForWidth(it.name.width()) < 0


def test_1280_hides_the_column_and_shows_band_and_close(make_window):
    w = make_window(F.after_run(), width=1280)
    assert w.compact and not w.ledger_column.isVisible()
    assert w.band.isVisible() and w.band.height() == 44
    assert w.topbar.close_button.isVisible()


def test_1366_shows_the_280_column(make_window):
    w = make_window(F.after_run(), width=1366)
    assert not w.compact and w.ledger_column.isVisible() and w.ledger_column.width() == 280
    assert not w.band.isVisible()
    assert not w.topbar.close_button.isVisible()


def test_minimum_size_and_opening_size(make_window):
    w = make_window(F.idle())
    assert w.minimumWidth() == 1280 and w.minimumHeight() == 720


@pytest.mark.parametrize("start,end", [(1440, 1280), (1280, 1440)])
def test_crossing_the_breakpoint_keeps_drawer_scroll_and_holds(make_window, qapp, start, end):
    from wholecount.ui.widgets.held import HoldReason

    w = make_window(F.after_run(data_notes=()), width=start, height=720, stage="review")
    tall = QWidget()
    tall.setFixedHeight(3000)
    w.stage_area.widget().layout().addWidget(tall)
    settle(qapp)
    w.stage_area.verticalScrollBar().setValue(400)
    w.your_data.open_()
    w.run_hold.hold()
    w.resize(end, 720)
    settle(qapp)
    assert w.stage_area.verticalScrollBar().value() == 400
    assert w.your_data.isVisible()
    assert w.strip.undo.run_held and w.run_hold.active
    w.run_hold.release()
    assert HoldReason("hold.run").text


def test_one_ledger_panel_moves_into_details(make_window, qapp):
    from wholecount.ui.frame.ledger import LedgerPanel

    w = make_window(F.after_run(), width=1280)
    assert len(w.findChildren(LedgerPanel)) == 1
    w.band.details_button.click()
    settle(qapp)
    assert w.details.isVisible() and w.ledger.isVisible()
    assert w.details.isAncestorOf(w.ledger)
    w.details.close_()
    settle(qapp)
    assert len(w.findChildren(LedgerPanel)) == 1 and w.ledger.parentWidget() is w.ledger_column


def test_band_is_elided_and_never_grows(make_window):
    w = make_window(F.maximal(), width=1280)
    assert w.band.height() == 44
    for g in w.band.groups:
        assert not g.line.wordWrap()
        assert g.line.toolTip() == g.full
