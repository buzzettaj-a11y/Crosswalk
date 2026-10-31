"""P-MAP-5: date order per table, from the evidence, until the operator answers (the evidence half of B-13)."""
import pytest

from wholecount import copy
from wholecount.engine.dateorder import DateOrder, collect_evidence, decide
from wholecount.engine.read.model import CellMeta


def orders(values):
    return [values, list(reversed(values)), values[1:] + values[:1]]


@pytest.mark.parametrize("i", range(3))
def test_resolved_day_first(i):
    d = decide(collect_evidence(orders(["13/04/1990", "03/04/1990"])[i]))
    assert (d.state, d.order) == ("resolved", DateOrder.DAY_FIRST)


def test_alone_asks_with_no_evidence():
    d = decide(collect_evidence(["03/04/1990"]))
    assert (d.state, d.order) == ("ask_no_evidence", None)


@pytest.mark.parametrize("i", range(3))
def test_both_ways(i):
    ev = collect_evidence(orders(["04/13/1990", "13/04/1990", "05/06/1991"])[i])
    d = decide(ev)
    assert d.state == "ask_both_ways" and (ev.month_first_only, ev.day_first_only, ev.either) == (1, 1, 1)
    assert copy.get("map.date_both_ways") == "Dates in this column are written both ways."
    text = copy.get("map.date_order_question", month_first=ev.month_first_only, day_first=ev.day_first_only, either=ev.either)
    assert text.startswith("This table writes dates as month/day or day/month?")


def test_all_iso_not_needed_and_xlsx_date_cells_skipped():
    assert decide(collect_evidence(["1990-04-03", "2001-12-30"])).state == "not_needed"
    ev = collect_evidence(["03/04/1990"], {0: CellMeta("date", "mm/dd/yyyy")})
    assert decide(ev).state == "not_needed"


def test_equal_parts_are_either_and_both_over_12_are_other():
    ev = collect_evidence(["03/03/1990", "13/14/1990", "1.2.90", "3-4-1990"])
    assert (ev.either, ev.other) == (3, 1)


def test_mixed_separators_are_not_dates():
    assert collect_evidence(["03/04-1990"]) == collect_evidence([])


@pytest.mark.parametrize("state_values", [["03/04/1990"], ["04/13/1990", "13/04/1990"]])
def test_an_answer_settles_it(state_values):
    d = decide(collect_evidence(state_values), answer="month_first")
    assert d.answered and d.order == DateOrder.MONTH_FIRST
