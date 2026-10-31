"""Reviewers (SPEC 8.7): the name on every decision, and the checks a bulk accept passes."""
import pytest

from tests.support.session import base, rk
from wholecount import copy
from wholecount.session import commands as C
from wholecount.session.reviewer import (AcceptProof, BadReviewerName, BulkAcceptRefused, check_accept, clean_name,
                                         current_reviewer, decisions_by_reviewer)

pytestmark = pytest.mark.claim("CL-REV-08")


def test_default_name_and_refusals():
    assert current_reviewer(lambda: "  Joe ") == "Joe"
    for bad, code in (("", "empty"), ("  ", "empty"), ("Jo\x07e", "control_character"), ("x" * 61, "too_long")):
        with pytest.raises(BadReviewerName) as e:
            clean_name(bad)
        assert e.value.code == code
    assert "every decision" in copy.get("review.reviewer_prompt")


def test_set_reviewer_goes_on_later_decisions(tmp_path):
    s = base(tmp_path)
    s.history.execute(C.SetReviewer("Sam"))
    s.history.execute(C.ApproveRows([rk(s, "R14")], "name_missing"))
    assert [d.reviewer for d in s.decisions] == ["Sam"]
    assert decisions_by_reviewer(s.decisions)[0].reviewer == "Sam"


def test_check_accept_codes():
    with pytest.raises(BulkAcceptRefused, match="count_mismatch"):
        check_accept(10, AcceptProof(9, "checked_sample"), None, "Joe")
    with pytest.raises(BulkAcceptRefused, match="reason_missing"):
        check_accept(10, AcceptProof(10, ""), None, "Joe")
    check_accept(200, AcceptProof(200, "other"), None, "Joe")
    with pytest.raises(BulkAcceptRefused, match="second_signoff_needed"):
        check_accept(201, AcceptProof(201, "other"), None, "Joe")
    with pytest.raises(BulkAcceptRefused, match="second_same_person"):
        check_accept(201, AcceptProof(201, "other"), " joe ", "Joe")
    check_accept(201, AcceptProof(201, "other"), "Sam", "Joe")
