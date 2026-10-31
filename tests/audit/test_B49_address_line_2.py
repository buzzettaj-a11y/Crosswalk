"""B-49 (Medium): "Address Line 2" before "Address Line 1" was mapped to Address_1."""
from tests.support.mapping import mapped


def test_B49_address_line_2_before_line_1():
    m = mapped(["Address Line 2", "Address Line 1"]).as_names()
    assert m == {"Address_1": "Address Line 1", "Address_2": "Address Line 2"}


def test_B49_street_address_2_before_street_address():
    m = mapped(["Street Address 2", "Street Address"]).as_names()
    assert m == {"Address_1": "Street Address", "Address_2": "Street Address 2"}
