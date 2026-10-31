"""P-READ-6: the header row, warnings as reason IDs, never a silent switch, and rebuild_with_header."""
import pytest

from tests.support.grids import accounting_of, grid, tables_of
from wholecount.engine.read.accounting import account_grid
from wholecount.engine.read.tables import header_looks_wrong, rebuild_with_header

TITLE = [["Client roster", "", "", "", ""], ["client_id", "first_name", "last_name", "city", "zip"],
         ["H1", "Ada", "Sample", "Brooklyn", "11201"], ["H2", "Ben", "Fixture", "New York", "10007"]]


@pytest.mark.parametrize("rows,header_row,warning", [
    ([["", "", ""], ["a", "b", "c"]], 1, "header_row_empty"),
    ([["Title", "", "", "", "", ""], ["a", "b", "c", "d", "e", "f"]], 1, "header_mostly_blank"),
    ([["11201", "2024-01-01", "x"], ["a", "b", "c"]], 1, "header_looks_like_data"),
    ([["ID", "id", "name"], ["1", "2", "x"]], 1, "header_duplicate_name"),
    ([["1", "Ada", "Sample", "Brooklyn"], ["2", "Ben", "Fixture", "Queens"]], 1, "header_same_shape_as_row_below"),
    ([["Roster", "x", "", "", ""], ["client_id", "first", "last", "city", "zip"], ["1", "a", "b", "c", "11201"]], 1,
     "header_row_below_is_better"),
    ([["Roster", "", ""], ["client_id", "first", "last"], ["1", "a", "b"]], 0, "no_header_but_row_looks_like_names"),
])
def test_each_warning(rows, header_row, warning):
    assert header_looks_wrong(rows, header_row)[0] == warning


def test_a_good_header_has_no_warning():
    assert header_looks_wrong([["client_id", "first", "last"], ["1", "a", "b"]], 1) == (None, None)


def test_no_silent_switch_and_a_suggestion():
    t, _, _ = tables_of(TITLE)
    assert t[0].header_row == 0 and t[0].header_warning == "no_header_but_row_looks_like_names"
    assert t[0].suggested_header_row == 2 and t[0].kind == "unknown" and not t[0].included


def test_rebuild_with_header():
    t, _, g = tables_of(TITLE)
    r = rebuild_with_header(t[0], 2)
    assert r.header_row == 2 and r.headers == ["client_id", "first_name", "last_name", "city", "zip"]
    assert len(r.rows) == 2 and r.above_header_rows == 1 and r.row_numbers == [3, 4]
    assert r.kind == "records" and r.included and r.header_warning is None
    assert account_grid(g, [r], []).balanced()
    assert t[0].header_row == 0, "rebuild is pure"
