"""Proof workbook sheet 11 (lines 290 to 320), through the whole row. Rows 9 and 10 are now counted, with a location reason."""
import pytest

from tests.support.std import ids, std

ROWS = [
    ("123 Main St Apt 2A", "Apt 2A", "123 Main St", "Apt 2A", []),
    ("123 Main St Apt 2A", "#2A", "123 Main St", "#2A", []),
    ("123 Main St Apt 2A", "", "123 Main St", "Apt 2A", []),
    ("123 Main St", "Apt 2A", "123 Main St", "Apt 2A", []),
    ("67 Franklin Avenue Apt. 10 R", "", "67 Franklin Avenue", "Apt. 10 R", []),
    ("25 Tom Street APT18L", "", "25 Tom Street", "APT18L", []),
    ("67 Jill Ave Apt#: 11T", "", "67 Jill Ave", "Apt#: 11T", []),
    ("10 Apartment Way", "", "10 Apartment Way", "", []),
    ("123 Main St Apt 2A", "Apt 3B", "123 Main St Apt 2A", "Apt 3B", ["units_differ"]),
    ("123 Main St Apt 2A", "c/o Jane Doe", "123 Main St Apt 2A", "c/o Jane Doe", ["address_extra_text"]),
]


@pytest.mark.parametrize("a1,a2,out1,out2,reasons", ROWS)
def test_sheet_11(a1, a2, out1, out2, reasons):
    r = std(Address_1=a1, Address_2=a2)
    assert (r.value("Address_1"), r.value("Address_2"), ids(r)) == (out1, out2, reasons)
    assert r.count_status.counted
