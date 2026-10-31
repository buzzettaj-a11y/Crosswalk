"""Results (M12 section 3): final only when nothing is left, the settled sentence, people without a program, rows without an
address, no weak match called verified, and no number at all while the results are out of date."""
import re

import pytest
from PySide6.QtWidgets import QLabel

from tests.support.example_session import decide, example_session
from tests.support.m11 import window_for
from tests.ui.conftest import settle
from wholecount import copy
from wholecount.session import commands as C

UI = {"reviewer_asked": True}


def labels(w):
    return [x.text() for x in w.stage_widget.findChildren(QLabel)]


def finish_rows(s):
    open_ = [k for k, o in s.results.outcomes.items() if o.reasons and o.set_aside_reason is None and not o.counted]
    if open_:
        s.history.execute(C.SetAsideRows(open_, "test_record"))
    if s.results.confidence.level == "low":
        s.history.execute(C.AcknowledgeLowConfidence())


@pytest.mark.claim("CL-FINAL-05")
def test_pairs_closed_with_rows_not_counted_shows_the_settled_sentence(qtbot, qapp, tmp_path):
    s = decide(example_session(tmp_path))
    c = s.results.counts
    assert c.open_pairs == 0 and c.not_counted_yet > 0 and not c.final
    w = window_for(qtbot, qapp, s, stage="summary", ui=UI)
    text = w.stage_widget.findChild(QLabel, "statusPartial").text()
    assert text == f"Settled for the rows counted so far. {c.not_counted_yet} rows aren't counted yet."
    assert w.stage_widget.findChild(QLabel, "statusFinal") is None


@pytest.mark.claim("CL-FINAL-04")
def test_final_shows_only_when_nothing_is_left(qtbot, qapp, tmp_path):
    s = example_session(tmp_path)
    w = window_for(qtbot, qapp, s, stage="summary", ui=UI)
    assert not s.results.counts.final and w.stage_widget.findChild(QLabel, "statusFinal") is None
    decide(s)
    finish_rows(s)
    w.refresh()
    settle(qapp)
    assert s.results.counts.final
    assert w.stage_widget.findChild(QLabel, "statusFinal").text() == "Final. Nothing is left to decide."
    assert w.stage_widget.findChild(QLabel, "goal1Until") is None
    s.history.undo()
    w.refresh()
    settle(qapp)
    assert not s.results.counts.final and w.stage_widget.findChild(QLabel, "statusFinal") is None


@pytest.mark.claim("CL-NOPROGRAM-PEOPLE-01")
def test_people_without_a_program_are_named_and_counted_in_goal_1_only(qtbot, qapp, tmp_path):
    s = decide(example_session(tmp_path))
    counts = s.results.counts
    n = counts.people_without_program.high
    w = window_for(qtbot, qapp, s, stage="summary", ui=UI)
    if n:
        assert w.stage_widget.findChild(QLabel, "noProgram").text() == copy.get("results.noprogram", n=n)
    # Counted in Goal 1 and not in Goal 2: each of them adds one to Goal 1 and nothing to any program.
    r = s.results
    masters = {}
    for k, o in r.outcomes.items():
        if o.counted:
            masters.setdefault(r.identity.master_of_record[k], []).append(r.rows[k].value("Program"))
    without = [m for m, progs in masters.items() if not any(progs)]
    assert len(without) == n
    assert counts.goal1.high == len(masters)


@pytest.mark.claim("CL-NOADDR-COUNTED-01")
@pytest.mark.claim("CL-VERIFIED-01")
def test_rows_without_an_address_count_and_no_weak_match_is_called_verified(qtbot, qapp, tmp_path):
    s = decide(example_session(tmp_path))
    w = window_for(qtbot, qapp, s, stage="summary", ui=UI)
    assert w.stage_widget.findChild(QLabel, "noAddrCounted").text() == copy.get("results.noaddr")
    r = s.results
    not_mapped = [k for k, o in r.outcomes.items() if o.counted and o.location is not None and o.location.kind != "mapped"]
    assert not_mapped and all(r.identity.master_of_record.get(k) for k in not_mapped)
    assert copy.get("results.verified") in labels(w)
    # The only place "verified" appears is that sentence, and a low placement is never shown as high.
    assert [t for t in labels(w) if "verified" in t.lower()] == [copy.get("results.verified")]
    loc = r.counts.locations
    assert loc.low == sum(1 for o in r.outcomes.values() if o.counted and o.location and o.location.kind == "mapped"
                          and o.location.confidence == "low")


@pytest.mark.claim("CL-STALE-HIDDEN-01")
def test_a_stale_result_draws_no_count_anywhere(qtbot, qapp, tmp_path):
    s = decide(example_session(tmp_path))
    w = window_for(qtbot, qapp, s, stage="summary", ui=UI)
    assert w.stage_widget.findChild(QLabel, "goal1Number") is not None
    s.history.execute(C.SetupChange("run_settings", "extra_fields", frozenset({"census_tract"})))
    w.refresh()
    settle(qapp)
    shown = labels(w)
    assert copy.get("results.held") in shown
    assert w.stage_widget.findChild(QLabel, "goal1Number") is None
    # Digit groups only: the stage head's "STAGE 08 OF 09" is a position, not a count.
    head = w.stage_widget.head
    numbers = [x.text() for x in w.stage_widget.findChildren(QLabel) if not head.isAncestorOf(x) and re.search(r"\d", x.text())]
    assert numbers == []
    assert w.stage_widget.cont.held and w.stage_widget.page_button.held
    # A download setting alone changes no result, so the numbers stay.
    s.history.undo()
    s.history.execute(C.SetupChange("export_settings", "map_points", True))
    w.refresh()
    settle(qapp)
    assert w.stage_widget.findChild(QLabel, "goal1Number") is not None
