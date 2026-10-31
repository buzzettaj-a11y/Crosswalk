"""B-14 (High): the two-digit year pivot was fixed at 25. Now a two-digit year is never guessed. The audit wanted a plausibility
guess; the spec forbids guessing and wins."""
import pytest

from tests.support.std import TODAY
from wholecount.engine.dateorder import DateOrder, suggest_pivot
from wholecount.engine.standardize.dates import DateContext, parse_date


def ctx(pivot=None):
    return DateContext(DateOrder.MONTH_FIRST, "ask_no_evidence", True, pivot)


@pytest.mark.parametrize("text", ["1/2/26", "5/5/26", "12/25/26", "1/2/24", "1/2/25", "1/2/45", "1/2/70", "1/2/15"])
def test_B14_no_pivot_gives_two_readings(text):
    p = parse_date(text, None, ctx(), TODAY, dob=True)
    assert p.reason == "date_two_digit_year" and len(p.readings) == 2 and p.iso is None


@pytest.mark.parametrize("text,iso,reason", [("1/2/26", "2026-01-02", None), ("1/2/27", "1927-01-02", None),
                                             ("1/2/45", "1945-01-02", None), ("12/25/26", "2026-12-25", "dob_out_of_range")])
def test_B14_the_suggested_pivot(text, iso, reason):
    pivot = suggest_pivot("Date_of_Birth", TODAY)
    assert pivot == 26
    p = parse_date(text, None, ctx(pivot), TODAY, dob=True)
    assert (p.iso, p.reason) == (iso, reason)


def test_B14_other_pivots():
    p = parse_date("1/2/45", None, ctx(99), TODAY, dob=True)
    assert (p.iso, p.reason) == ("2045-01-02", "dob_out_of_range")
    assert parse_date("1/2/00", None, ctx(0), TODAY).iso == "2000-01-02"
    assert parse_date("1/2/01", None, ctx(0), TODAY).iso == "1901-01-02"
