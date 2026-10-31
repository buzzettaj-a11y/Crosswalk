"""The old proof workbook's sheets 19 and 20 (legacy/tools/make_proof_workbook.py lines 486 to 515), typed as literals."""
from tests.support.grids import tables_of
from wholecount.engine.read.accounting import account_grid
from wholecount.engine.read.tables import rebuild_with_header

SHEET_19 = [
    ["Program", "Total", "", "client_id", "first_name", "last_name", "address_1", "city", "state", "zip"],
    ["Youth", "124", "", "G1", "Ada", "Sample", "209 Joralemon St", "Brooklyn", "NY", "11201"],
    ["Workforce", "87", "", "G2", "Ben", "Fixture", "60 Centre St", "New York", "NY", "10007"],
    ["Housing", "206", "", "G3", "Cara", "Example", "87 Bay Terrace", "Staten Island", "NY", "10306"],
]
SHEET_20 = [
    ["Client roster, spring 2026", "", "", "", "", "", ""],
    ["Prepared by the data team", "", "", "", "", "", ""],
    ["client_id", "first_name", "last_name", "address_1", "city", "state", "zip"],
    ["H1", "Ada", "Sample", "209 Joralemon St", "Brooklyn", "NY", "11201"],
    ["H2", "Ben", "Fixture", "60 Centre St", "New York", "NY", "10007"],
    ["H3", "Cara", "Example", "87 Bay Terrace", "Staten Island", "NY", "10306"],
]


def test_sheet_19_two_tables_only_the_client_list_included():
    t, _, _ = tables_of(SHEET_19)
    assert len(t) == 2
    assert [x.kind for x in t] == ["summary", "records"] and [x.included for x in t] == [False, True]


def test_sheet_20_suggests_row_3_and_balances_after_the_choice():
    t, nt, g = tables_of(SHEET_20)
    assert len(t) == 1 and not nt
    assert t[0].suggested_header_row == 3 and t[0].header_warning is not None
    r = rebuild_with_header(t[0], 3)
    assert len(r.rows) == 3 and r.above_header_rows == 2
    assert account_grid(g, [r], []).balanced()
