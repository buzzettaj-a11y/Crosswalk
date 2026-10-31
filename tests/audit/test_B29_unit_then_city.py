"""B-29 (Medium): a unit swallowed the city ("Apt 3 Brooklyn" landed in Address_2)."""
from wholecount.engine.prepare.address import parse_address


def test_B29_unit_then_city():
    a = parse_address("123 Main St, Apt 3 Brooklyn NY 11201")
    assert (a.street, a.unit, a.city, a.state, a.zip) == ("123 Main St", "Apt 3", "Brooklyn", "NY", "11201")
