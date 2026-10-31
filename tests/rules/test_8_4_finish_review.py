"""Finish review (SPEC 8.4): held by open Affects the counts causes, released by routing, and confirmed with the open count."""
import pytest

from tests.support.session import decided
from wholecount import copy
from wholecount.session import commands as C
from tests.support.session import base


@pytest.mark.claim("CL-REV-02")
def test_held_then_routed(tmp_path):
    s = base(tmp_path)
    with pytest.raises(C.Refused, match="finish_held"):
        s.history.execute(C.FinishReview(0))
    assert copy.get("review.finish_held")


@pytest.mark.claim("CL-REV-01")
def test_finish_with_the_open_count(tmp_path):
    s = decided(tmp_path)
    s.history.execute(C.FinishReview(0))
    assert s.finished[1] == 0 and s.audit[-1].code == "FINISH_REVIEW" and s.audit[-1].get("count") == [0]
    assert copy.get("review.finish_confirm", count=3).startswith("3 rows are still open")


def test_routing_releases_the_hold(tmp_path):
    s = base(tmp_path)
    for cause in ("name_missing", "same_id_conflict"):
        s.history.execute(C.SendToRowByRow(cause))
    from wholecount.engine.review import finish_gate
    gate = finish_gate(list(s.results.outcomes.values()), s.results.open_groups, s.results.replay.routed)
    assert gate.held and {c for c, _ in gate.left} == {"copies_identical", "copies_possible"}
