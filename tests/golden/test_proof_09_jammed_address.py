"""Proof workbook sheet 09, all 14 rows (legacy/tools/make_proof_workbook.py line 220). City is compared only as parsed, because
M04 fills a blank city from the ZIP."""
import pytest

from wholecount.engine.prepare.address import parse_address

ROWS = [
    ("123 Main St Apt 3L Brooklyn NY 11201", {"Address_1": "123 Main St", "Address_2": "Apt 3L", "City": "Brooklyn", "Zip": "11201"}),
    ("45 Oak St, Queens, NY 11375", {"Address_1": "45 Oak St", "City": "Queens", "Zip": "11375"}),
    ("60 Centre St - Apt 2 - New York NY 10007", {"Address_1": "60 Centre St", "Address_2": "Apt 2", "Zip": "10007"}),
    ("100 Grand St Apt 4 Brooklyn NY 11211 USA", {"Address_1": "100 Grand St", "Zip": "11211"}),
    ("88 Front St Brooklyn NY 11201", {"Address_1": "88 Front St", "Address_2": ""}),
    ("2488 Grand Concourse Bronx NY 10458", {"Address_1": "2488 Grand Concourse", "Address_2": ""}),
    ("40-22 24th St Apt 5 Queens NY 11101", {"Address_1": "40-22 24th St", "Address_2": "Apt 5"}),
    ("111 Test St, Apt. 4, NY, 11201", {"Address_1": "111 Test St", "Address_2": "Apt. 4", "City": "Brooklyn"}),
    ("111 Test St, Brooklyn, Apt. 4, NY, 11201", {"Address_1": "111 Test St", "Address_2": "Apt. 4", "City": "Brooklyn"}),
    ("111 Test St, 4th Fl, Brooklyn, NY, 11201", {"Address_2": "4th Fl", "City": "Brooklyn"}),
    ("111 Test St, Apt. 4, Brooklyn, New York, 11201", {"Address_2": "Apt. 4", "City": "Brooklyn", "State": "NY"}),
    ("117-19 45TH AVE, 14A, QUEENS, NY 11355", {"Address_1": "117-19 45TH AVE", "Address_2": "14A", "City": "Queens", "Zip": "11355"}),
    ("117-19 45TH AVE 14A QUEENS NY 11355", {"Address_1": "117-19 45TH AVE", "Address_2": "14A", "City": "Queens"}),
    ("2300 Avenue U, Brooklyn, NY 11229", {"Address_1": "2300 Avenue U", "Address_2": ""}),
]
FIELD = {"Address_1": "street", "Address_2": "unit", "City": "city", "State": "state", "Zip": "zip"}


@pytest.mark.parametrize("raw,want", ROWS)
def test_sheet_09(raw, want):
    a = parse_address(raw)
    for field, value in want.items():
        got = getattr(a, FIELD[field])
        if field == "City":
            if got:
                assert got.lower() == value.lower(), raw
            continue
        assert got == value, (raw, field)
