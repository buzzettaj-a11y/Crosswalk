"""Reviewers and bulk accepts (SPEC 8.7, the engine side). Every decision carries the reviewer's name."""
import getpass
import hashlib
import unicodedata
from dataclasses import dataclass

from wholecount.settings.loader import load

ACCEPT_REASONS = ("checked_sample", "matches_source", "expected_in_this_file", "other")
SET_ASIDE_REASONS = ("not_a_client", "test_record", "duplicate_other_system", "out_of_scope", "other")


class BadReviewerName(ValueError):
    def __init__(self, code):
        super().__init__(code)
        self.code = code


class BulkAcceptRefused(Exception):
    def __init__(self, code):
        super().__init__(code)
        self.code = code


@dataclass(frozen=True)
class AcceptProof:
    """A bulk accept takes no free text, so there is no note."""
    typed_count: int
    reason_code: str


@dataclass(frozen=True)
class ReviewerCount:
    reviewer: str
    kind: str
    count: int


def settings():
    return load("review")


def current_reviewer(getuser=getpass.getuser):
    try:
        return clean_name(getuser())
    except (BadReviewerName, Exception):
        return ""


def clean_name(name):
    n = (name or "").strip()
    if not n:
        raise BadReviewerName("empty")
    if any(unicodedata.category(ch).startswith("C") for ch in n):
        raise BadReviewerName("control_character")
    if len(n) > settings()["reviewer_name_max"]:
        raise BadReviewerName("too_long")
    return n


def sample_rows(decision_id, record_keys, n=None):
    """The rows to show before a bulk accept: ranked by sha256(decision ID + record key), no random. Sorted."""
    n = settings()["sample_rows"] if n is None else n
    ranked = sorted(record_keys, key=lambda k: hashlib.sha256((decision_id + k).encode("utf-8")).hexdigest())
    return tuple(sorted(ranked[:n]))


def _same_person(a, b):
    return (a or "").strip().casefold() == (b or "").strip().casefold()


def needs_second(rows):
    return rows > settings()["second_signoff_rows"]


def check_second(rows, second, reviewer, limit=None):
    limit = settings()["second_signoff_rows"] if limit is None else limit
    if rows > limit:
        if not (second or "").strip():
            raise BulkAcceptRefused("second_signoff_needed")
        if _same_person(second, reviewer):
            raise BulkAcceptRefused("second_same_person")


def check_accept(group_rows, proof, second, reviewer):
    """Raises BulkAcceptRefused(count_mismatch, reason_missing, second_signoff_needed or second_same_person)."""
    if proof is None or proof.typed_count != group_rows:
        raise BulkAcceptRefused("count_mismatch")
    if proof.reason_code not in ACCEPT_REASONS:
        raise BulkAcceptRefused("reason_missing")
    check_second(group_rows, second, reviewer)


def decisions_by_reviewer(decisions):
    tally = {}
    for d in decisions:
        tally[(d.reviewer, d.kind)] = tally.get((d.reviewer, d.kind), 0) + 1
    return tuple(ReviewerCount(r, k, n) for (r, k), n in sorted(tally.items()))
