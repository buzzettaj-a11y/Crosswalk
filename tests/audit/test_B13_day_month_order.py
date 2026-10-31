"""B-13 (High): day and month were swapped silently. The table's evidence decides the order, and nothing is swapped silently."""
from wholecount.engine.dateorder import DateOrder, collect_evidence, decide
from wholecount.engine.standardize.dates import date_context, parse_date
from tests.support.std import TODAY


def read(values, answer=None):
    ctx = date_context(decide(collect_evidence(values), answer))
    return [(p.iso, p.reason) for p in (parse_date(v, None, ctx, TODAY) for v in values)]


def test_B13_one_day_first_value_settles_the_table():
    assert read(["13/04/1990", "03/04/1990"]) == [("1990-04-13", None), ("1990-04-03", None)]


def test_B13_no_evidence_asks_then_reads_once_answered():
    assert read(["03/04/1990"]) == [(None, "date_order_unclear")]
    assert read(["03/04/1990"], "day_first") == [("1990-04-03", None)]
    assert read(["03/04/1990"], "month_first") == [("1990-03-04", None)]


def test_B13_both_ways_then_a_month_first_answer():
    assert read(["04/13/1990", "13/04/1990"]) == [(None, "date_both_ways"), (None, "date_both_ways")]
    assert read(["04/13/1990", "13/04/1990"], "month_first") == [("1990-04-13", None), (None, "date_both_ways")]


def test_B13_equal_parts_read_with_no_answer_except_in_a_both_ways_column():
    assert read(["03/03/1990"]) == [("1990-03-03", None)]
    assert read(["03/03/1990", "04/13/1990", "13/04/1990"])[0] == (None, "date_both_ways")
