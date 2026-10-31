"""P-READ-4: tables inside sheets, split on fully blank rows and columns, classified as records, summary or unknown."""
from tests.support.grids import a1, tables_of


def ranges(tables):
    return [a1(t.blocks[0].block) for t in tables]


def test_single_table_stays_one():
    t, nt, _ = tables_of([["ID", "First", "Last", "address1", "city", "state", "zip"],
                          ["1", "a", "b", "1 Main St", "Brooklyn", "NY", "11201"], ["2", "c", "d", "2 Oak St", "Queens", "NY", "11375"]])
    assert len(t) == 1 and not nt
    assert t[0].kind == "records" and t[0].included and t[0].header_row == 1


def test_side_by_side():
    t, _, _ = tables_of([["Program", "Total", "", "ID", "First", "city", "zip"],
                         ["Housing", "5", "", "1", "a", "Brooklyn", "11201"], ["Youth", "9", "", "2", "b", "Queens", "11375"]])
    assert ranges(t) == ["A1:B3", "D1:G3"]
    assert [(x.kind, x.included) for x in t] == [("summary", False), ("records", True)]


def test_stacked():
    t, _, _ = tables_of([["ID", "First"], ["1", "a"], ["", ""], ["Program", "Total"], ["Housing", "5"]])
    assert ranges(t) == ["A1:B2", "A4:B5"]


def test_offset_from_a1():
    t, _, _ = tables_of([["", "", "", ""], ["", "ID", "First", "city"], ["", "1", "a", "Brooklyn"]])
    assert ranges(t) == ["B2:D3"]


def test_headerless_numeric():
    t, _, _ = tables_of([["1", "2", "3"], ["4", "5", "6"]])
    assert t[0].header_row == 0 and t[0].headers == ["Column_1", "Column_2", "Column_3"] and len(t[0].rows) == 2
    assert t[0].kind == "unknown" and not t[0].included


def test_duplicate_headers_made_unique():
    t, _, _ = tables_of([["ID", "ID", "name"], ["1", "2", "x"]])
    assert t[0].headers == ["ID", "ID_2", "name"]


def test_a_column_headed_null_does_not_split():
    t, _, _ = tables_of([["ID", "First", "NULL", "Program", "Total"], ["1", "a", "", "Housing", "5"]])
    assert len(t) == 1 and t[0].headers[2] == "NULL"


def test_a_row_of_dashes_is_data():
    t, _, _ = tables_of([["ID", "First", "Last"], ["1", "a", "b"], ["-", "-", "-"], ["2", "c", "d"]])
    assert len(t) == 1 and len(t[0].rows) == 3


def test_one_cell_notes_are_non_table_blocks():
    t, nt, _ = tables_of([["Client list"], [""], ["ID", "First", "Last"], ["1", "a", "b"], [""], ["Exported by staff"]])
    assert len(t) == 1 and len(nt) == 2


def test_empty_columns_are_listed():
    t, _, _ = tables_of([["ID", "first", "address2", "city"], ["1", "a", "", "Brooklyn"], ["2", "b", "", "Queens"]])
    assert t[0].empty_columns == ["address2"]
