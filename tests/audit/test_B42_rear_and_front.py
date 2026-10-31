"""B-42 (Low): "Rear" and "Front" split with a comma but not without."""
import pytest

from wholecount.engine.prepare.address import parse_address


@pytest.mark.parametrize("raw,unit", [("123 Main St Rear", "Rear"), ("123 Main St Front", "Front"), ("123 Main St, Front", "Front")])
def test_B42_all_forms_give_the_same_street(raw, unit):
    a = parse_address(raw)
    assert (a.street, a.unit) == ("123 Main St", unit)


def test_B42_front_street_stays_whole():
    a = parse_address("88 Front St")
    assert (a.street, a.unit) == ("88 Front St", "")
