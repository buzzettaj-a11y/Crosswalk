"""P-MAP-6: the two-digit-year rule, stored per table and date field."""
import datetime as dt

import pytest

from wholecount import copy
from wholecount.engine.dateorder import DateFieldSetting, DateOrder, TwoDigitRule, rule_needed, suggest_pivot


def test_suggested_pivot():
    assert suggest_pivot("Date_of_Birth", dt.date(2026, 10, 30)) == 26
    assert suggest_pivot("Enrolled_On", dt.date(2026, 10, 30)) is None


def test_stored_per_table_and_field():
    settings = {("t1", "Date_of_Birth"): DateFieldSetting(DateOrder.MONTH_FIRST, TwoDigitRule(26)),
                ("t2", "Date_of_Birth"): DateFieldSetting(DateOrder.DAY_FIRST, TwoDigitRule(10))}
    assert settings[("t1", "Date_of_Birth")].pivot != settings[("t2", "Date_of_Birth")].pivot
    assert TwoDigitRule(26).century(26) == 2026 and TwoDigitRule(26).century(27) == 1927


@pytest.mark.parametrize("bad", [-1, 100, True, "26"])
def test_bad_pivot_refused(bad):
    with pytest.raises(ValueError):
        TwoDigitRule(bad)


def test_rule_needed_only_for_two_digit_years():
    assert rule_needed(["1/2/26", "03/04/1990"])
    assert not rule_needed(["03/04/1990", "1990-04-03"])
    assert not rule_needed([])


def test_question_copy_takes_an_int():
    assert copy.get("map.two_digit_rule_question", pivot=26) == "Two-digit years up to 26 mean the 2000s, otherwise the 1900s."
