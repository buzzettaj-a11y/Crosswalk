"""Bulk accepts (SPEC 8.7): the sample, the typed count, the reason, the second reviewer and the audit entry."""
import ast
import dataclasses
import inspect

import pytest

from tests.support.session import base, rk
from wholecount import copy
from wholecount.session import commands as C
from wholecount.session import reviewer
from wholecount.session.reviewer import AcceptProof, BulkAcceptRefused, decisions_by_reviewer, sample_rows

KEYS = [f"{i:020x}" for i in range(40)]


@pytest.mark.claim("CL-REV-07")
def test_sample_rows_are_stable_and_seeded_by_the_decision():
    a = sample_rows("D-0000000001", KEYS)
    assert len(a) == 5 and set(a) <= set(KEYS) and a == tuple(sorted(a))
    assert sample_rows("D-0000000001", KEYS) == a and sample_rows("D-0000000002", KEYS) != a
    tree = ast.parse(inspect.getsource(reviewer))
    imported = {a.name for n in ast.walk(tree) if isinstance(n, (ast.Import, ast.ImportFrom)) for a in n.names}
    imported |= {n.module for n in ast.walk(tree) if isinstance(n, ast.ImportFrom)}
    assert "random" not in imported
    assert copy.get("review.bulk.sample", count=5)


@pytest.mark.claim("CL-REV-05")
def test_typed_count_and_reason(tmp_path):
    s = base(tmp_path)
    with pytest.raises(BulkAcceptRefused, match="count_mismatch"):
        s.history.execute(C.AcceptGroup("name_missing", [rk(s, "R14")], AcceptProof(2, "checked_sample")))
    with pytest.raises(BulkAcceptRefused, match="reason_missing"):
        s.history.execute(C.AcceptGroup("name_missing", [rk(s, "R14")], AcceptProof(1, "because")))
    assert "note" not in {f.name for f in dataclasses.fields(AcceptProof)}
    s.history.execute(C.AcceptGroup("name_missing", [rk(s, "R14")], AcceptProof(1, "other")))
    e = s.audit[-1]
    assert e.code == "ACCEPT_GROUP" and e.get("typed_count") == [1] and e.get("reason_code") == ["other"]
    assert e.get("reviewer") == ["Joe"] and e.get("note") == []
    assert copy.get("review.bulk.type_count", count=1)


@pytest.mark.claim("CL-REV-06")
def test_second_reviewer_over_200_rows_and_for_big_joins(tmp_path):
    with pytest.raises(BulkAcceptRefused, match="second_signoff_needed"):
        C.ApproveRows([f"{i:020x}" for i in range(201)]).build(type("S", (), {"reviewer": "Joe", "now_iso": lambda self: "x"})())
    s = base(tmp_path)
    p = s.results.identity.proposals[0]
    s.history.execute(C.DecidePair(*p.pair, "same"))
    assert reviewer.settings()["second_signoff_join_records"] == 5
    assert copy.get("review.bulk.second_reviewer", limit=200)


def test_a_join_of_six_records_needs_a_second_reviewer():
    with pytest.raises(BulkAcceptRefused, match="second_signoff_needed"):
        reviewer.check_second(6, None, "Joe", 5)
    reviewer.check_second(5, None, "Joe", 5)
    reviewer.check_second(6, "Sam", "Joe", 5)


def test_decisions_by_reviewer(tmp_path):
    s = base(tmp_path)
    s.history.execute(C.SetAsideRows([rk(s, "R01"), rk(s, "R02")], "test_record"))
    s.history.execute(C.SetReviewer("Sam"))
    s.history.execute(C.ApproveRows([rk(s, "R14")], "name_missing"))
    assert [(c.reviewer, c.kind, c.count) for c in decisions_by_reviewer(s.decisions)] == [("Joe", "set_aside", 2),
                                                                                          ("Sam", "approve", 1)]
