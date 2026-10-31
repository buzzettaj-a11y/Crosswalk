"""The Your data, System check, Settings and Details drawers (SPEC 11.3, 11.8)."""
import json

import pytest
from PySide6.QtCore import Qt
from PySide6.QtWidgets import QLabel

from tests.ui.conftest import Confirm, settle
from tools import screen_fixtures as F
from wholecount import copy
from wholecount.ui.frame.drawers import NEVER_LINES, support_report
from wholecount.ui.frame.view import check_rows


def test_your_data_boxes_and_never_lines_in_order(make_window, qapp):
    w = make_window(F.after_run())
    w.ledger.your_data.click()
    settle(qapp)
    d = w.your_data
    assert d.isVisible()
    t = d.texts()
    order = [copy.get(k) for k in ("data.box.files.title", "data.box.memory.title", "data.box.out.title")]
    assert [t.index(x) for x in order] == sorted(t.index(x) for x in order)
    never = [copy.get(k) for k in NEVER_LINES]
    assert [x.text() for x in d.never_lines] == never
    assert d.boxes[2].objectName() == "flowBoxMemory"


@pytest.mark.claim("CL-DATA-SAVED-OFF-01")
def test_switch_off_asks_then_calls_the_store(make_window, qapp):
    c = Confirm(True)
    w = make_window(F.after_run(), confirm=c)
    w.your_data.open_()
    w.your_data.switch.check.setChecked(False)
    settle(qapp)
    assert c.asked and c.asked[-1][1] == (copy.get("data.saved.confirm_off"),)
    assert w.bridge.saved_progress_calls == [False]
    assert w.your_data.switch.state.text() == copy.get("data.saved.off")
    w.your_data.switch.check.setChecked(True)
    settle(qapp)
    assert w.bridge.saved_progress_calls == [False, True]


def test_switch_off_declined_changes_nothing(make_window, qapp):
    w = make_window(F.after_run(), confirm=Confirm(False))
    w.your_data.switch.check.setChecked(False)
    settle(qapp)
    assert w.bridge.saved_progress_calls == []
    assert w.your_data.switch.check.isChecked()


@pytest.mark.claim("CL-DATA-SAVED-OFF-01")
def test_turning_off_deletes_what_is_saved_and_saves_nothing_new(tmp_path):
    from tests.support.fake_dpapi import FakeDpapi
    from tests.support.session import base, rk
    from wholecount.session import commands as C
    from wholecount.session.store import Store
    from wholecount.ui.frame.bridge import SessionBridge

    s = base(tmp_path / "w")
    fd = FakeDpapi()
    s.store = Store(tmp_path / "store", fd.protect, fd.unprotect)
    s.history.execute(C.SetAsideRows([rk(s, "R14")], "out_of_scope"))
    assert list(s.store.sessions.glob("*.wcs"))
    b = SessionBridge(s, {"saved_progress": True})
    b.set_saved_progress(False)
    s.store = None if not b.ui["saved_progress"] else s.store
    assert not list((tmp_path / "store" / "sessions").glob("*.wcs"))
    assert json.loads((tmp_path / "store" / "prefs.json").read_text())["saved_progress"] is False


def test_data_notes_draw_in_the_drawer_and_the_writes_part(make_window, qapp):
    from wholecount.ui.widgets.dataline import part_text

    w = make_window(F.after_run(data_notes=("stage.placeholder",)), stage="review")
    notes = w.your_data.findChildren(QLabel, "dataNote")
    assert [n.text() for n in notes] == [copy.get("stage.placeholder")]
    w2 = make_window(F.after_run())
    assert w2.your_data.findChildren(QLabel, "dataNote") == []
    assert part_text("review", "writes", False, ()) == "nothing to disk"


def test_dataline_note_key_draws_at_the_end_of_writes(monkeypatch):
    from wholecount.copy import registry
    from wholecount.ui.widgets.dataline import part_text

    entries = dict(registry._entries())
    entries["dataline.note.review.extra"] = registry.Entry("dataline.note.review.extra", "and the saved crosswalk.")
    monkeypatch.setattr(registry, "_ENTRIES", entries)
    assert part_text("review", "writes", False, ("dataline.note.review.extra",)).endswith(" and the saved crosswalk.")
    assert part_text("sources", "writes", False, ("dataline.note.review.extra",)) == "nothing to disk"


class _Pre:
    def __init__(self, kind, rows=0, release="", stale=False):
        self.reference_kind, self.reference_rows, self.release, self.release_stale = kind, rows, release, stale
        self.district_files = 2
        self.backend = type("B", (), {"file_name": "nyc_addresses.csv", "name": "reference"})()


def _detail(rows, cid):
    r = next(x for x in rows if x.check_id == cid)
    k, p = r.detail
    return r.status, copy.get(k, **p)


def test_reference_row_shows_file_and_count_or_sample_wording():
    assert _detail(check_rows(_Pre("real", 1234)), "reference") == ("ok", "nyc_addresses.csv, 1,234 rows")
    assert _detail(check_rows(_Pre("sample")), "reference") == ("warn", "sample file, practice only")
    assert _detail(check_rows(_Pre("several_reference_files")), "reference")[1] == "two files in the folder, none used"
    assert _detail(check_rows(_Pre("none")), "reference")[1] == "none"


def test_stale_release_is_amber(make_window, qapp):
    rows = check_rows(_Pre("none", release="21A", stale=True))
    assert _detail(rows, "geosupport") == ("warn", "Release 21A, more than a year old")
    w = make_window(F.after_run(checks=rows, release="21A", release_stale=True))
    w.ledger.check_line.click()
    settle(qapp)
    assert w.check.isVisible()
    geo = [r for r in w.check.table.rows if r[0] == "geosupport"][0]
    assert geo[3] == "warn"
    assert w.topbar.backend_old.text() == copy.get("top.backend.geosupport_old")
    assert w.topbar.backend_old.property("tone") == "amber"


@pytest.mark.claim("CL-SUPPORT-REPORT-01")
def test_support_report_holds_no_value_from_the_data(tmp_path):
    from tests.support.session import base
    from wholecount.ui.frame.view import build_view

    s = base(tmp_path)
    v = build_view(s, preflight=None)
    text = support_report(v)
    values = {val.entered for r in s.results.rows.values() for _, val in r.values.items() if val.entered}
    for val in values:
        if len(val) >= 3:
            assert val not in text, val
    assert text.splitlines()[0].startswith("Wholecount ")


def test_copy_report_puts_the_report_on_the_clipboard(make_window, qapp):
    from PySide6.QtGui import QGuiApplication

    w = make_window(F.after_run())
    w.check.update_view(w.view)
    text = w.check.copy_report()
    assert QGuiApplication.clipboard().text() == text


def test_drawers_close_with_escape_scrim_and_close(make_window, qtbot, qapp):
    w = make_window(F.after_run())
    for d in (w.your_data, w.check, w.settings):
        d.open_()
        settle(qapp)
        qtbot.keyClick(d, Qt.Key_Escape)
        assert not d.isVisible()
        d.open_()
        qtbot.mouseClick(d, Qt.LeftButton, pos=d.rect().topLeft() + d.rect().topLeft().__class__(5, 5))
        assert not d.isVisible()
        d.open_()
        d.close_button.click()
        assert not d.isVisible()
    assert w.your_data.close_button.text() == "Close"
