"""Properties of standardizing (H3, H4, H6): independent of other rows, stable on its own output, entered kept, ASCII ZIPs,
a city only ever folded to its own borough, and address text never changing the count."""
import datetime as dt
import random

from hypothesis import given, settings
from hypothesis import strategies as st

from tests.support.std import BASE, MONTH_FIRST, TODAY, row_input
from wholecount.engine.geo.places import borough_of
from wholecount.engine.schema import default_schema
from wholecount.engine.standardize.rows import TableOptions, standardize_row, standardize_table

S = default_schema()
OPT = TableOptions({"Date_of_Birth": MONTH_FIRST})
TEXT = st.sampled_from(["", "Ada", "LEE", "Unknown", "-", "0", "Homeless", "Brooklyn", "Bklyn", "Queens", "Narnia", "NY", "NJ", "11201",
                        "07030", "1120", "１１２０１", "209 Joralemon St", "123 Main St Apt 2A", "Apt 3B",
                        "1990-04-03", "03/04/1990", "32874", "Total", "Na", "c/o Jane Doe"])
ROWS = st.fixed_dictionaries({k: TEXT for k in BASE})


def run(values, key="rk"):
    return standardize_row(row_input(key, **values), S, OPT, TODAY)


@settings(max_examples=150, deadline=None)
@given(st.lists(ROWS, min_size=1, max_size=6), st.randoms())
def test_alone_or_among_others_in_any_order(rows, rnd):
    alone = [run(v, str(i)) for i, v in enumerate(rows)]
    inputs = [row_input(str(i), **v) for i, v in enumerate(rows)]
    rnd.shuffle(inputs)
    together = {r.record_key: r for r in standardize_table(inputs, S, OPT, TODAY)}
    assert all(together[r.record_key] == r for r in alone)


@settings(max_examples=200, deadline=None)
@given(ROWS)
def test_entered_kept_ascii_zip_and_city_rule(values):
    r = run(values)
    for k, v in values.items():
        assert r.values[k].entered == v
    z = r.value("Zip")
    if z and not any(x.reason_id in ("zip_unicode_digits",) for x in r.reasons):
        assert z.isascii()
    city, entered = r.value("City"), values["City"]
    if entered and city != entered:
        blanked = city == "" and any(n.field == "City" for n in r.notes + r.reasons if n.reason_id in (
            "blank_marker", "placeholder_in_value", "no_fixed_address"))
        filled = any(n.reason_id == "city_filled_from_zip" for n in r.notes)
        assert blanked or filled or city == borough_of(entered)


@settings(max_examples=150, deadline=None)
@given(ROWS)
def test_restandardizing_accepted_values_changes_nothing(values):
    first = run(values)
    if first.count_status.value != "counted_passed" or first.set_aside_reason:
        return
    again = run({k: v.value for k, v in first.values.items()})
    assert {k: v.value for k, v in again.values.items()} == {k: v.value for k, v in first.values.items()}


@settings(max_examples=150, deadline=None)
@given(ROWS, st.fixed_dictionaries({k: TEXT for k in ("Address_1", "Address_2", "City", "State", "Zip")}))
def test_address_values_never_change_the_count_status(values, address):
    if run(values).set_aside_reason or run({**values, **address}).set_aside_reason:
        return
    assert run(values).count_status == run({**values, **address}).count_status


@settings(max_examples=100, deadline=None)
@given(st.lists(ROWS, min_size=1, max_size=10))
def test_table_balance(rows):
    out = standardize_table([row_input(str(i), **v) for i, v in enumerate(rows)], S, OPT, TODAY)
    statuses = [r.count_status.value for r in out]
    counted = [r for r in out if r.count_status.counted]
    assert len(counted) + statuses.count("not_counted_yet") + statuses.count("set_aside") == len(out)
    kinds = [r.location for r in counted]
    reasons = sum(1 for k in kinds if k.kind == "not_mapped")
    assert reasons + sum(1 for k in kinds if k.kind == "to_place") == len(counted)
