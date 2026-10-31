"""Proof workbook sheets 01 to 08 (legacy/tools/make_proof_workbook.py lines 92 to 218). CLEAN means no decision reason; REVIEW
means at least one, and the test names the flag. Changed answers are in tests/golden/CHANGES.md."""
import pytest

from tests.support.std import ids, std
from wholecount.engine import reasons

PEOPLE = [("Ada", "Sample"), ("Ben", "Fixture"), ("Cara", "Example"), ("Devi", "Mock"), ("Evan", "Draft"), ("Fay", "Proxy"), ("Gus", "Stub")]

# (sheet, row, overrides, want, expect): expect is "clean" or the flag the row's reasons carry.
ROWS = [
    ("01", 1, {"First_Name": "NULL"}, {}, "holds_count"),
    ("01", 2, {"Address_2": "#N/A"}, {"Address_2": ""}, "clean"),
    ("01", 3, {"Address_1": "209 Joralemon St"}, {"Address_1": "209 Joralemon St"}, "clean"),
    ("01", 4, {"First_Name": "Mary Beth"}, {"First_Name": "Mary Beth"}, "clean"),
    ("01", 5, {"First_Name": "Lena"}, {"First_Name": "Lena"}, "clean"),
    ("01", 6, {"Last_Name": "O'Brien"}, {"Last_Name": "O'Brien"}, "clean"),
    ("01", 7, {"Last_Name": "Smith-Jones"}, {"Last_Name": "Smith-Jones"}, "clean"),
    ("02", 1, {"First_Name": "JOHN"}, {"First_Name": "John"}, "clean"),
    ("02", 2, {"Last_Name": "smith"}, {"Last_Name": "Smith"}, "clean"),
    ("02", 3, {"Last_Name": "MCMAHON"}, {"Last_Name": "McMahon"}, "clean"),
    ("02", 4, {"Last_Name": "O'BRIEN"}, {"Last_Name": "O'Brien"}, "clean"),
    ("02", 5, {"Last_Name": "DiNapoli"}, {"Last_Name": "DiNapoli"}, "clean"),
    ("02", 6, {"Last_Name": "LaGuardia"}, {"Last_Name": "LaGuardia"}, "clean"),
    ("02", 7, {"First_Name": "mELINDA"}, {"First_Name": "mELINDA"}, "clean"),
    ("03", 1, {"Middle_Initial": "James"}, {"Middle_Initial": "J"}, "clean"),
    ("03", 2, {"Middle_Initial": "j."}, {"Middle_Initial": "J"}, "clean"),
    ("03", 3, {"Middle_Initial": "a"}, {"Middle_Initial": "A"}, "clean"),
    ("03", 4, {"Middle_Initial": "J"}, {"Middle_Initial": "J"}, "clean"),
    ("03", 5, {"Middle_Initial": ""}, {"Middle_Initial": ""}, "clean"),
    ("04", 1, {"Zip": "11201-1234"}, {"Zip": "11201"}, "clean"),
    ("04", 2, {"Zip": "11201"}, {"Zip": "11201"}, "clean"),
    ("04", 3, {"Zip": "11201"}, {"Zip": "11201"}, "clean"),
    ("04", 4, {"Zip": "7030"}, {}, "location"),
    ("04", 5, {"Zip": "ABCDE"}, {}, "location"),
    ("04", 6, {"Zip": ""}, {}, "location"),
    ("04", 7, {"Zip": "112011234"}, {"Zip": "11201"}, "clean"),
    ("05", 1, {"City": "", "Zip": "11201"}, {"City": "Brooklyn"}, "clean"),
    ("05", 2, {"City": "", "Zip": "10007"}, {"City": "New York"}, "clean"),
    ("05", 3, {"City": "", "Zip": "10306"}, {"City": "Staten Island"}, "clean"),
    ("05", 4, {"City": "", "Zip": "11377"}, {"City": "Queens"}, "clean"),
    ("05", 5, {"City": "Brooklyn"}, {"City": "Brooklyn"}, "clean"),
    ("05", 6, {"City": "", "Zip": "07030"}, {}, "location"),
    ("06", 1, {"City": "Brooklyn", "Zip": "10007"}, {}, "location"),
    ("06", 2, {"City": "Queens", "Zip": "11201"}, {}, "location"),
    ("06", 3, {"City": "Bronx", "Zip": "10306"}, {}, "location"),
    ("06", 4, {"City": "Brooklyn", "Zip": "11201"}, {}, "clean"),
    ("06", 5, {"City": "New York", "Zip": "10007"}, {}, "clean"),
    ("06", 6, {"City": "Manhattan", "Zip": "10007"}, {"City": "New York"}, "clean"),
    ("06", 7, {"City": "Springfield", "Zip": "11201"}, {"City": "Springfield"}, "location"),
    ("07", 1, {"City": "Bklyn"}, {"City": "Brooklyn"}, "clean"),
    ("07", 2, {"City": "BK"}, {"City": "Brooklyn"}, "clean"),
    ("07", 3, {"City": "Woodside", "Zip": "11377"}, {"City": "Queens"}, "clean"),
    ("07", 4, {"City": "Bay Ridge", "Zip": "11209"}, {"City": "Brooklyn"}, "clean"),
    ("07", 5, {"City": "Harlem", "Zip": "10027"}, {"City": "New York"}, "clean"),
    ("07", 6, {"City": "Brooklyn"}, {"City": "Brooklyn"}, "clean"),
    ("08", 1, {"State": ""}, {"State": "NY"}, "clean"),
    ("08", 2, {"State": "New York"}, {"State": "NY"}, "clean"),
    ("08", 3, {"State": "ny"}, {"State": "NY"}, "clean"),
    ("08", 4, {"State": "NY"}, {"State": "NY"}, "clean"),
    ("08", 5, {"State": "NJ"}, {}, "location"),
    ("08", 6, {"State": "CT"}, {}, "location"),
]


@pytest.mark.parametrize("sheet,n,over,want,expect", ROWS, ids=[f"{s}-{n}" for s, n, *_ in ROWS])
def test_sheet(sheet, n, over, want, expect):
    first, last = PEOPLE[(n - 1) % len(PEOPLE)]
    values = {"First_Name": first, "Last_Name": last, "Client_ID": f"P{n:03d}", **over}
    r = std(**values)
    for f, v in want.items():
        assert r.value(f) == v, (sheet, n, f)
    flags = {reasons.get(x).flag for x in ids(r)}
    if expect == "clean":
        assert flags == set(), (sheet, n, ids(r))
    else:
        assert expect in flags, (sheet, n, ids(r))
    assert r.count_status.counted == (expect != "holds_count")
