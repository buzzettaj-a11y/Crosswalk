"""Fix problems (M12 section 2): the reviewer prompt, the finish hold, previews that change nothing, keep one, fills,
corrections files, unmatched columns on screen only, and opening a source file."""
import sys

import pytest
from PySide6.QtWidgets import QLabel

from tests.support.example_session import example_session
from tests.support.files_run import fixture, run
from tests.support.m11 import run_job, window_for
from tests.support.outputs import write
from tests.support.review import cell, review_grid, save_grid
from tests.support.session import base, rk, snapshot
from tests.ui.conftest import Confirm, settle
from wholecount import copy
from wholecount.session import commands as C
from wholecount.session.export import build_view
from wholecount.session.pages import cause_views, gate, keep_one_plan

UI = {"reviewer_asked": True}


def texts(w):
    return [x.text() for x in w.findChildren(QLabel) if x.isVisible()]


def cause(s, cause_id):
    return next(v.cause for v in cause_views(s) if v.cause.cause_id == cause_id)


@pytest.mark.claim("CL-REVIEWER-LOGGED-01")
def test_the_reviewer_is_asked_once_and_their_name_goes_on_both_logs(qtbot, qapp, tmp_path):
    from wholecount.engine.outputs.audit_text import render_internal, render_shareable

    s = example_session(tmp_path)
    w = window_for(qtbot, qapp, s, stage="review")
    d = w.stage_widget.dialog
    assert d is not None and d.isVisible()
    assert copy.get("review.reviewer.line") in [x.text() for x in d.findChildren(QLabel)]
    d.name.setText("Avery Reviewer")
    d.start.click()
    settle(qapp)
    assert s.reviewer == "Avery Reviewer" and not d.isVisible()
    w.go_to("summary")
    w.go_to("review")
    settle(qapp)
    assert w.stage_widget.dialog is None or not w.stage_widget.dialog.isVisible()
    keys = cause(s, "name_missing").record_keys
    s.history.execute(C.SetAsideRows(keys, "test_record"))
    assert all(d.reviewer == "Avery Reviewer" for d in s.decisions if d.kind == "set_aside")
    view = build_view(s)
    assert "Avery Reviewer" in render_internal(view) and "Avery Reviewer" in render_shareable(view)


@pytest.mark.claim("CL-REV-HOLD-01")
@pytest.mark.claim("CL-LOC-COUNTS-01")
def test_finish_is_held_by_counts_causes_only_and_location_rows_already_count(qtbot, qapp, tmp_path):
    s = example_session(tmp_path)
    w = window_for(qtbot, qapp, s, stage="review", ui=UI)
    body = w.stage_widget
    g = gate(s)
    assert body.finish.hold.copy_id == "review.hold.causes"
    assert body.finish.caption.text() == copy.get("review.hold.causes", n=len(g.left)) == "Held until 5 causes are decided."
    # Location causes are open and hold nothing; their rows are in the counted total.
    loc = [v.cause for v in cause_views(s) if v.cause.tab == "location" and v.state == "open"]
    assert loc and not {c.cause_id for c in loc} & {cid for cid, _ in g.left}
    assert all(s.results.outcomes[k].counted for c in loc for k in c.record_keys)
    body._set_tab("location")
    settle(qapp)
    assert copy.get("review.loc.intro") in texts(w)


@pytest.mark.claim("CL-PREVIEW-ARITH-01")
def test_preview_is_arithmetic_and_changes_nothing(qtbot, qapp, tmp_path):
    s = example_session(tmp_path)
    w = window_for(qtbot, qapp, s, stage="review", ui=UI)
    before = (snapshot(s), len(s.history.stack))
    c = cause(s, "name_missing")
    w.stage_widget.open_preview(c)
    settle(qapp)
    counted = s.results.counts.counted
    line = w.stage_widget.preview.findChild(QLabel, "previewAccept").text()
    assert line == copy.get("review.preview.accept", a=counted, b=counted + len(c.record_keys))
    assert w.stage_widget.preview.findChild(QLabel, "previewNote").text() == "This is a preview. Nothing changes."
    assert (snapshot(s), len(s.history.stack)) == before
    s.history.execute(C.ApproveRows(list(c.record_keys), "*"))
    assert s.results.counts.counted == counted + len(c.record_keys)


@pytest.mark.claim("CL-NOTE-INTERNAL-01")
def test_the_other_note_goes_to_the_internal_log_only(qtbot, qapp, tmp_path):
    from wholecount.engine.outputs.audit_text import render_internal, render_shareable

    s = example_session(tmp_path)
    w = window_for(qtbot, qapp, s, stage="review", ui=UI)
    d = w.stage_widget.set_aside(cause(s, "name_missing"))
    settle(qapp)
    assert not d.note.isVisible()
    d.reason.setCurrentIndex(d.reason.findData("other"))
    settle(qapp)
    assert d.note.isVisible() and d.note.maxLength() == 120
    assert d.note_warning.text() == copy.get("review.aside.note")
    d.note.setText("Checked with the intake desk")
    d.ok.button.click()
    settle(qapp)
    view = build_view(s)
    assert "Checked with the intake desk" in render_internal(view)
    assert "Checked with the intake desk" not in render_shareable(view)


@pytest.mark.claim("CL-KEEP-ONE-PLAN-01")
def test_keep_one_states_the_exact_plan_before_it_acts(qtbot, qapp, tmp_path):
    from wholecount.session.pages import QueueFilter

    s = example_session(tmp_path)
    ask = Confirm(True)
    w = window_for(qtbot, qapp, s, stage="review", ui=UI, confirm=ask)
    body = w.stage_widget
    c = cause(s, "copies_identical")
    body.set_step(2, QueueFilter(cause_id=c.cause_id))
    settle(qapp)
    q = body.queue
    for k in c.record_keys:
        q._tick(k, True)
    kept, aside = keep_one_plan(s, q.selection_keys())
    before = s.results.counts.set_aside
    q.keep_one()
    settle(qapp)
    assert ask.asked[-1][1] == (copy.get("review.keep_one.plan", k=kept, j=aside),)
    assert s.results.counts.set_aside - before == aside and kept >= 1


@pytest.mark.claim("CL-FILL-NOCHANGE-01")
def test_the_fill_preview_changes_nothing_until_apply(qtbot, qapp, tmp_path):
    s = base(tmp_path)
    w = window_for(qtbot, qapp, s, stage="review", ui=UI)
    c = next(v.cause for v in cause_views(s) if v.cause.kind == "fill_from_street")
    before = (snapshot(s), len(s.history.stack))
    run_job(qtbot, qapp, w, lambda: w.stage_widget.look_up(c))
    fill = w.stage_widget.fill
    assert fill.findChild(QLabel, "fillTitle").text() == copy.get("review.fill.title")
    assert fill.boxes and (snapshot(s), len(s.history.stack)) == before
    fill.close_()
    assert (snapshot(s), len(s.history.stack)) == before
    run_job(qtbot, qapp, w, lambda: w.stage_widget.look_up(c))
    keys = list(w.stage_widget.fill.boxes)
    w.stage_widget.fill.apply.click()
    settle(qapp)
    assert isinstance(s.history.stack[-1], C.AcceptFills) and sorted(s.history.stack[-1].record_keys) == sorted(keys)


def corrections_window(qtbot, qapp, tmp_path):
    s = run(tmp_path, fixture(tmp_path, "household.csv"))
    zed = next(k for k, r in s.results.rows.items() if r.value("Client_ID") == "H300")
    return s, zed, review_grid(s, tmp_path / "out"), window_for(qtbot, qapp, s, stage="review", ui=UI)


def apply_file(qtbot, qapp, w, grid, path):
    # The body of the file is reversed: rows match by Record_Key, never by position.
    save_grid([grid[0]] + grid[1:][::-1], path)
    run_job(qtbot, qapp, w, lambda: w.stage_widget.start_corrections(path))
    return [x.text() for x in w.stage_widget.corrections_result.findChildren(QLabel)]


@pytest.mark.claim("CL-CORRECTIONS-REFUSE-01")
def test_a_changed_original_is_refused_with_its_reason(qtbot, qapp, tmp_path):
    s, zed, grid, w = corrections_window(qtbot, qapp, tmp_path)
    cell(grid, zed, "Corrected_Zip", "11201")
    cell(grid, zed, "Original_Zip", "10001")
    line = next(i for i, r in enumerate(grid) if zed in r) + 1
    shown = apply_file(qtbot, qapp, w, grid, tmp_path / "c.csv")
    assert copy.get("review.corrections.result", a=0, b=1, c=0) in shown
    assert any(t.endswith("This row has changed since the review file was made.") for t in shown)
    assert all("11201" not in t and "10001" not in t for t in shown)
    assert line > 1


@pytest.mark.claim("CL-CORRECTIONS-REFUSE-02")
def test_another_changed_column_is_named_and_the_rest_applies(qtbot, qapp, tmp_path):
    s, zed, grid, w = corrections_window(qtbot, qapp, tmp_path)
    cell(grid, zed, "Corrected_Zip", "11201")
    cell(grid, zed, "Last_Name", "Somebodyelse")
    shown = apply_file(qtbot, qapp, w, grid, tmp_path / "c.csv")
    assert copy.get("review.corrections.result", a=1, b=1, c=1) in shown
    assert any(t.endswith("Last_Name did not fail, so it can't be corrected here.") for t in shown)
    assert all("Somebodyelse" not in t and "11201" not in t for t in shown)
    assert s.results.outcomes[zed].count_status.value == "counted_corrected"


@pytest.mark.claim("CL-NOLONGER-01")
def test_no_longer_apply_lists_the_dropped_decision_and_reopens_it(qtbot, qapp, tmp_path):
    from wholecount.engine.corrections import VerifiedCorrection
    from wholecount.session.runner import process

    s = base(tmp_path)
    s.history.execute(C.ApplyCorrections([VerifiedCorrection(rk(s, "R13"), (("Zip", "11201"),))], "f" * 64))
    s.correction_texts.clear()
    process(s)
    assert s.results.no_longer_apply
    w = window_for(qtbot, qapp, s, stage="review", ui=UI)
    assert copy.get("review.nolonger.line") in texts(w)
    w.stage_widget._toggle_nolonger()
    settle(qapp)
    assert any(copy.get("review.nolonger.why.file_removed") in t for t in texts(w))


@pytest.mark.claim("CL-UNMATCHED-SCREEN-01")
def test_unmatched_columns_show_on_screen_and_nowhere_else(qtbot, qapp, tmp_path):
    from wholecount.session.pages import QueueFilter, unmatched_columns

    s = example_session(tmp_path / "s" if (tmp_path / "s").mkdir() is None else tmp_path)
    k = next(k for k in s.results.outcomes if s.results.file_of_record[k] == "example_clinic.csv"
             and s.results.outcomes[k].reasons and any(v for _, v in unmatched_columns(s, k)))
    values = [v for _, v in unmatched_columns(s, k) if v]
    w = window_for(qtbot, qapp, s, stage="review", ui=UI)
    w.stage_widget.set_step(2, QueueFilter())
    settle(qapp)
    q = w.stage_widget.queue
    q._open_key(k)
    q._toggle_unmatched()
    settle(qapp)
    assert q.record.findChild(QLabel, "unmatchedNote").text() == copy.get("review.record.unmatched")
    on_screen = [x.text() for x in q.record.findChildren(QLabel)]
    assert all(v in on_screen for v in values)
    if s.results.confidence.level == "low":
        s.history.execute(C.AcknowledgeLowConfidence())
    out = tmp_path / "out"
    write(s, out, map_points=True, exact_coordinates=True)
    blobs = [p.read_bytes() for p in out.iterdir()] + [repr(e).encode() for e in s.audit]
    for v in values:
        assert all(v.encode() not in b for b in blobs), v


@pytest.mark.claim("CL-SHELL-OPEN-01")
def test_open_the_source_file_asks_first_and_only_opens_batch_files(qtbot, qapp, tmp_path, monkeypatch):
    from wholecount.session.pages import QueueFilter
    from wholecount.ui import shell

    ask = Confirm(False)
    s = example_session(tmp_path)
    w = window_for(qtbot, qapp, s, stage="review", ui=UI, confirm=ask)
    w.stage_widget.set_step(2, QueueFilter())
    settle(qapp)
    q = w.stage_widget.queue
    q._open_key(q.data.rows[0].record_key)
    assert q.record.open_source() is False
    assert ask.asked[-1][1][1] == copy.get("review.open.confirm")
    assert "sends nothing" in ask.asked[-1][1][1]
    opened = []
    monkeypatch.setattr(shell, "open_source_file", lambda p, batch: opened.append(p) or True)
    ask.answer = True
    q.record.open_source()
    if sys.platform != "win32":
        assert opened == [] and q.record.message.text() == copy.get("review.open.windows_only")


def test_only_a_file_in_this_batch_can_be_opened(tmp_path):
    from wholecount.ui import shell

    s = example_session(tmp_path)
    with pytest.raises(shell.NotInBatch):
        shell.open_source_file(tmp_path / "elsewhere.csv", s.setup.paths())


def test_every_lapse_reason_has_a_sentence():
    from wholecount.session.decisions import KINDS, LAPSE_REASONS

    for r in LAPSE_REASONS:
        assert copy.get(f"review.nolonger.why.{r}")
    for k in KINDS:
        assert copy.get(f"review.kind.{k}")
