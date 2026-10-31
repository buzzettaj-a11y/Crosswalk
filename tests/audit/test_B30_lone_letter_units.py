"""B-30 (Medium): lone-letter units stayed in the street."""
import pytest

from wholecount.engine.prepare.address import parse_address


@pytest.mark.parametrize("raw,street,unit", [
    ("123 Main St Apt B", "123 Main St", "Apt B"), ("123 Main St Unit B", "123 Main St", "Unit B"),
    ("123 Main St, B, Brooklyn NY 11201", "123 Main St", "B"), ("1010 Grand Concourse 5C", "1010 Grand Concourse", "5C"),
    ("100 Avenue U", "100 Avenue U", ""),
])
def test_B30_lone_letter_units(raw, street, unit):
    a = parse_address(raw)
    assert (a.street, a.unit) == (street, unit)
