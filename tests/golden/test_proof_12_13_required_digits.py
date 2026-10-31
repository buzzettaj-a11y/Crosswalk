"""Proof workbook sheets 12 and 13 (lines 322 to 349). A missing street or ZIP is now counted and not mapped (P-VAL-2)."""
import pytest

from tests.support.std import ids, std
from wholecount.engine import reasons

ROWS = [
    ("12", {"First_Name": ""}, "holds_count"), ("12", {"Last_Name": ""}, "holds_count"), ("12", {"Address_1": ""}, "location"),
    ("12", {"Zip": ""}, "location"), ("12", {"Middle_Initial": ""}, "clean"), ("12", {"Address_2": ""}, "clean"), ("12", {"Program": ""}, "clean"),
    ("13", {"First_Name": "J0hn"}, "soft"), ("13", {"Last_Name": "209 Joralemon"}, "soft"), ("13", {"First_Name": "3rd"}, "soft"),
    ("13", {"First_Name": "Mary-Kate"}, "clean"), ("13", {"Last_Name": "St. John"}, "clean"), ("13", {"Last_Name": "Smith III"}, "clean"),
]


@pytest.mark.parametrize("sheet,over,expect", ROWS)
def test_sheets_12_13(sheet, over, expect):
    r = std(**over)
    flags = {reasons.get(x).flag for x in ids(r)}
    assert flags == set() if expect == "clean" else expect in flags
    assert r.count_status.counted == (expect != "holds_count")
