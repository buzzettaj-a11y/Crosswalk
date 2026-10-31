"""B-43 (Low): name-aware title case got a few names wrong. Standardizing re-cases names with no tidy-up step."""
import pytest

from tests.support.std import std


@pytest.mark.parametrize("raw,out", [("MCE", "Mce"), ("MACKENZIE", "MacKenzie"), ("DEJESUS", "DeJesus"), ("LEBRON", "LeBron"),
                                     ("DINAPOLI", "DiNapoli"), ("O’BRIEN", "O’Brien"), ("mELINDA", "mELINDA"), ("DiNapoli", "DiNapoli")])
def test_B43_name_case(raw, out):
    r = std(Last_Name=raw)
    assert r.value("Last_Name") == out and r.values["Last_Name"].entered == raw
