"""Every problem ID in wholecount/copy/problems.toml mapped to an open row that triggers it (C-09). Standardizing raises all
but one; the open same-ID conflict comes from the copy step."""
from tests.fixtures.std_problem_rows import PROBLEM_ROWS
from tests.support.std import MONTH_FIRST, TODAY
from wholecount.engine.dateorder import DateOrder  # noqa: F401
from wholecount.engine.review import base_outcome
from wholecount.engine.schema import default_schema
from wholecount.engine.standardize.dates import DateContext
from wholecount.engine.standardize.rows import TableOptions, standardize_row

CONTEXTS = {None: MONTH_FIRST, "unclear": DateContext(None, "ask_no_evidence", False, None),
            "both_ways": DateContext(None, "ask_both_ways", False, None)}


def std_row(reason_id):
    row, extra = PROBLEM_ROWS[reason_id]
    schema = extra if extra is not None and not isinstance(extra, str) else default_schema()
    ctx = CONTEXTS[extra if isinstance(extra, str) else None]
    return standardize_row(row, schema, TableOptions({"Date_of_Birth": ctx}), TODAY)


def open_row(reason_id):
    """The RowOutcome of a row that has this problem open."""
    if reason_id == "same_id_conflict":
        return base_outcome(std_row("name_order_unclear"), same_id_rows={"rk"})
    return base_outcome(std_row(reason_id))


PROBLEM_IDS = sorted(set(PROBLEM_ROWS) | {"same_id_conflict"})
