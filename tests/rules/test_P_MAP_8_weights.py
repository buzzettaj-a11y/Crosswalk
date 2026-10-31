"""P-MAP-8: the two weights the spec names. Mailing loses to Home by a penalty, and a calculated ZIP wins over a real one."""
import pytest

from tests.support.mapping import derived_ref, mapped

V = ["11201", "10027", "10458"]
COLS = ["Home Address", "Mailing Address", "Home Zip", "Mailing Zip"]


@pytest.mark.parametrize("order", [COLS, list(reversed(COLS)), COLS[1::2] + COLS[::2]])
def test_mailing_loses_to_home_in_every_order(order):
    m = mapped(order).as_names()
    assert m["Address_1"] == "Home Address" and m["Zip"] == "Home Zip"


def test_mailing_is_offered_when_it_is_the_only_address():
    m = mapped(["Mailing Address", "Mailing City", "Mailing Zip"]).as_names()
    assert m == {"Address_1": "Mailing Address", "City": "Mailing City", "Zip": "Mailing Zip"}


def test_a_calculated_zip_wins_over_a_real_zipcode():
    d = [(derived_ref("Address_zip", "Address", kind="calculated"), V)]
    assert mapped(["ZipCode", "Address"], {"ZipCode": V}, derived=d).as_names()["Zip"] == "Address_zip"


def test_a_split_zip_from_another_column_does_not():
    d = [(derived_ref("Notes_zip", "Notes", kind="split"), V)]
    assert mapped(["ZipCode", "Notes"], {"ZipCode": V}, derived=d).as_names()["Zip"] == "ZipCode"
