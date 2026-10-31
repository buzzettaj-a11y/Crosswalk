"""P-STD-3: ZIP forms (proof sheet 04), numeric padding and the NYC list."""
import pytest

from tests.support.std import ids, std
from wholecount.engine.standardize.zipcode import standardize_zip


@pytest.mark.parametrize("text,value,reason,notes", [
    ("11201-1234", "11201", None, ("zip_plus4_reduced",)), ("11201", "11201", None, ()), ("112011234", "11201", None, ("zip_plus4_reduced",)),
    ("7030", "7030", "zip_not_valid", ()), ("ABCDE", "ABCDE", "zip_not_valid", ()), ("", "", None, ()),
])
def test_sheet_04_forms(text, value, reason, notes):
    z = standardize_zip(text)
    assert (z.value, z.reason, z.notes) == (value, reason, notes)


def test_numeric_padding():
    assert standardize_zip("501", "number").value == "00501"
    assert standardize_zip("112011234", "number").reason == "zip_not_valid"
    assert standardize_zip("7030", None).reason == "zip_not_valid"


def test_outside_nyc_is_a_status_not_a_problem():
    z = standardize_zip("07030")
    assert z.outside_nyc and z.reason is None and z.notes == ("zip_outside_nyc",)


def test_blank_zip_is_missing():
    assert "address_part_missing" in ids(std(Zip=""))
