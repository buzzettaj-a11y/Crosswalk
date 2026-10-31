"""Every decision reason has a row that triggers it (M04). M08 reuses the fixture."""
from tests.fixtures.std_problem_rows import PROBLEM_ROWS
from tests.support.std import MONTH_FIRST, TODAY
from wholecount.engine import reasons
from wholecount.engine.dateorder import DateOrder
from wholecount.engine.schema import default_schema
from wholecount.engine.standardize.dates import DateContext
from wholecount.engine.standardize.rows import TableOptions, standardize_row

CONTEXTS = {None: MONTH_FIRST, "unclear": DateContext(None, "ask_no_evidence", False, None),
            "both_ways": DateContext(None, "ask_both_ways", False, None)}


def run(row, extra):
    schema = extra if extra is not None and not isinstance(extra, str) else default_schema()
    ctx = CONTEXTS[extra if isinstance(extra, str) else None]
    return standardize_row(row, schema, TableOptions({"Date_of_Birth": ctx}), TODAY)


def test_every_decision_reason_has_a_triggering_row():
    # same_id_conflict comes from the copy step (M08), not from standardizing, so tests/fixtures/session/problem_rows.py covers it.
    decision = {r.id for r in reasons.all_reasons().values() if r.severity == "decision"} - {"same_id_conflict"}
    assert decision == set(PROBLEM_ROWS)
    for rid, (row, extra) in PROBLEM_ROWS.items():
        assert rid in run(row, extra).reason_ids(), rid
