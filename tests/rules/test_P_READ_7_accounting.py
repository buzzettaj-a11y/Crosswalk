"""P-READ-7 and H4: every non-empty row is placed, and side-by-side tables count shared rows."""
import pytest

from tests.support.grids import accounting_of
from wholecount.engine.read.tables import rebuild_with_header

pytestmark = pytest.mark.claim("CL-READ-ACCOUNTING-01")


def test_header_included_and_non_table():
    a = accounting_of([["Notes"], [""], ["ID", "First", "Last"], ["1", "a", "b"], ["2", "c", "d"]])
    assert (a.non_empty_rows, a.header, a.included, a.non_table, a.shared_rows) == (4, 1, 2, 1, 0) and a.balanced()


@pytest.mark.claim("CL-READ-ACCOUNTING-02")
def test_side_by_side_tables_share_rows():
    a = accounting_of([["Program", "Total", "", "ID", "First", "Last"], ["Housing", "5", "", "1", "a", "b"],
                       ["Youth", "9", "", "2", "c", "d"]])
    assert (a.non_empty_rows, a.shared_rows, a.header, a.included, a.excluded) == (3, 3, 2, 2, 2) and a.balanced()
    assert a.cells_in_blocks == a.non_empty_cells


def test_above_header_counted_after_a_header_choice():
    from tests.support.grids import tables_of
    rows = [["Roster", "", ""], ["client_id", "first", "last"], ["1", "a", "b"]]
    t, _, _ = tables_of(rows)
    a = accounting_of(rows, [rebuild_with_header(t[0], 2)])
    assert (a.above_header, a.header, a.included) == (1, 1, 1) and a.balanced()


def test_rows_left_out():
    a = accounting_of([["Program", "Total"], ["Housing", "5"], ["Youth", "9"]])
    assert a.excluded == 2 and a.rows_left_out == 2 and a.balanced()


def test_accounting_line_copy_renders():
    from wholecount import copy
    text = copy.get("read.accounting_line", included=1234, excluded=0, non_table=1, header=1, above_header=2, non_empty=1238)
    assert "1,234 rows in included tables" in text and "1,238 rows" in text
    text = copy.get("read.accounting_line_shared", included=2, excluded=2, non_table=0, header=2, above_header=0, non_empty=3, shared=3)
    assert "plus 3 rows" in text
