"""P-READ-5: a block with the shape of the records table above it joins as a continuation (A-09)."""
from tests.support.grids import accounting_of, tables_of

HEAD = ["Client_ID", "First_Name", "Last_Name", "Zip"]


def test_joins():
    t, _, _ = tables_of([HEAD, ["1", "a", "b", "11201"], [""], ["2", "c", "d", "11201"], ["3", "e", "f", "11201"]])
    assert len(t) == 1 and len(t[0].rows) == 3
    assert [(b.rows, b.continuation, b.included) for b in t[0].blocks] == [(1, False, True), (2, True, True)]
    assert t[0].row_numbers == [2, 4, 5]


def test_a_one_row_block_can_continue():
    t, nt, _ = tables_of([HEAD, ["1", "a", "b", "11201"], [""], ["2", "c", "d", "11201"]])
    assert len(t) == 1 and len(t[0].rows) == 2 and not nt


def test_repeated_header_does_not_join():
    t, _, _ = tables_of([HEAD, ["1", "a", "b", "11201"], [""], HEAD, ["2", "c", "d", "11201"]])
    assert len(t) == 2


def test_different_width_does_not_join():
    t, nt, _ = tables_of([HEAD, ["1", "a", "b", "11201"], [""], ["2", "c", "d", "11201", "x"], ["3", "e", "f", "11201", "y"]])
    assert len(t) == 2 and len(t[0].rows) == 1


def test_different_first_column_does_not_join():
    t, nt, _ = tables_of([HEAD + [""], ["1", "a", "b", "11201", ""], ["", "", "", "", ""], ["", "2", "c", "d", "11201"]])
    assert len(t) == 1 and len(t[0].rows) == 1 and len(nt) == 1


def test_unticking_a_continuation_keeps_the_balance():
    rows = [HEAD, ["1", "a", "b", "11201"], [""], ["2", "c", "d", "11201"], ["3", "e", "f", "11201"]]
    t, _, _ = tables_of(rows)
    t[0].blocks[1].included = False
    a = accounting_of(rows, t)
    assert (a.included, a.excluded, a.rows_left_out) == (1, 2, 2) and a.balanced()
