"""Proof workbook sheet 10, all 6 rows (legacy/tools/make_proof_workbook.py line 270). Row 3 follows the spec: the suffix goes to
its own column (P-PREP-4), as tests/golden/CHANGES.md records."""
import pytest

from wholecount.engine.prepare.names import parse_name

ROWS = [
    ("Smith, John A", {"First_Name": "John", "Middle_Initial": "A", "Last_Name": "Smith"}),
    ("John A Smith", {"First_Name": "John", "Middle_Initial": "A", "Last_Name": "Smith"}),
    ("Smith Jr, John", {"First_Name": "John", "Last_Name": "Smith", "suffix": "Jr"}),
    ("DiNapoli, Anthony", {"Last_Name": "DiNapoli"}),
    ("MARIA GARCIA", {"First_Name": "MARIA", "Last_Name": "GARCIA"}),
    ("Ana Lopez", {"First_Name": "Ana", "Middle_Initial": "", "Last_Name": "Lopez"}),
]
FIELD = {"First_Name": "first", "Middle_Initial": "middle", "Last_Name": "last", "suffix": "suffix"}


@pytest.mark.parametrize("raw,want", ROWS)
def test_sheet_10(raw, want):
    n = parse_name(raw)
    assert {f: getattr(n, FIELD[f]) for f in want} == want
