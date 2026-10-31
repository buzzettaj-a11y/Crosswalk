"""Captions and states for all nine stages (SPEC 11.3, 10.4). They read only FrameView."""
import pytest

from tools import screen_fixtures as F
from wholecount.ui.frame.captions import CURRENT, DONE, LATER, NOTHING, stage_caption, stage_state
from wholecount.ui.frame.stages import IDS
from wholecount.ui.frame.view import ConfidenceView, RESULT_STAGES

CASES = [
    ("sources", F.idle(), "no files yet", LATER),
    ("sources", F.after_run(), "5 files, 6 tables", DONE),
    ("schema", F.idle(), "nothing to decide", NOTHING),
    ("schema", F.idle(schema_custom=3), "3 custom fields", DONE),
    ("prepare", F.idle(), "no steps yet", NOTHING),
    ("prepare", F.idle(steps_proposed=4), "4 steps proposed", DONE),
    ("prepare", F.idle(steps_proposed=4, steps_kept=4, steps_continued=True, steps_noop=1), "4 steps kept, 1 do nothing",
     DONE),
    ("map", F.idle(map_tables=5, map_confirmed=2), "2 of 5 tables confirmed", LATER),
    ("map", F.idle(map_tables=5, map_confirmed=2, map_wrong=3), "2 of 5 tables confirmed, 3 look wrong", LATER),
    ("map", F.idle(map_tables=5, map_confirmed=5), "5 of 5 tables confirmed", DONE),
    ("programs", F.idle(), "not run yet", LATER),
    ("programs", F.after_run(program_groups_open=4), "4 programs to confirm", LATER),
    ("programs", F.after_run(), "7 programs, confirmed", DONE),
    ("programs", F.after_run(program_files=0, program_names=0, programs_counted=0), "no program column", NOTHING),
    ("run", F.idle(), "ready to run", LATER),
    ("run", F.idle(running=True), "running", LATER),
    ("run", F.after_run(), "done in 30.5 s", DONE),
    ("review", F.idle(), "not run yet", LATER),
    ("review", F.after_run(), "1,232 rows open", LATER),
    ("review", F.after_run(rows_open=0), "all decided", DONE),
    ("review", F.after_run(review_finished=True), "1,232 rows open", DONE),
    ("summary", F.idle(), "not run yet", LATER),
    ("summary", F.after_run(), "14 pairs open", LATER),
    ("summary", F.after_run(counts=F.counts(open_groups=3)), "14 pairs open, 3 copy groups", LATER),
    ("summary", F.after_run(counts=F.counts(open_pairs=0)), "1,232 not counted yet", LATER),
    ("summary", F.after_run(counts=F.counts(final=True, open_pairs=0, not_counted_yet=0)), "final", DONE),
    ("export", F.idle(), "not run yet", LATER),
    ("export", F.after_run(confidence=F.confidence("low")), "held, confidence is Low", LATER),
    ("export", F.after_run(confidence=F.confidence("low", acknowledged=True)), "9 files ready", LATER),
    ("export", F.after_run(downloaded=True), "9 files ready", DONE),
]


@pytest.mark.parametrize("stage,view,text,state", CASES)
def test_caption_and_state(stage, view, text, state):
    assert stage_caption(stage, view).text == text
    assert stage_state(stage, view) == state


def test_every_stage_has_cases():
    assert {c[0] for c in CASES} == set(IDS)


@pytest.mark.parametrize("stage", IDS)
def test_current_wins(stage):
    assert stage_state(stage, F.after_run(), current=stage) == CURRENT


@pytest.mark.claim("CL-STALE-CAPTION-01")
@pytest.mark.parametrize("stage", sorted(RESULT_STAGES))
def test_stale_says_out_of_date_and_no_count(stage):
    v = F.after_run(stale=frozenset(RESULT_STAGES), counts=None)
    cap = stage_caption(stage, v)
    assert cap.text == "out of date" and cap.stale and cap.tone == "amber"
    assert not any(ch.isdigit() for ch in cap.text)
    # the state is kept
    assert stage_state(stage, v) == stage_state(stage, F.after_run(stale=frozenset(RESULT_STAGES), counts=None))


def test_thousands_separators():
    assert stage_caption("review", F.after_run(rows_open=12345)).text == "12,345 rows open"


def test_tones():
    assert stage_caption("prepare", F.idle(steps_proposed=2, steps_noop=1)).parts[-1][2] == "amber"
    assert stage_caption("map", F.idle(map_tables=2, map_wrong=1)).parts[-1][2] == "blue"
    assert ConfidenceView().level is None
