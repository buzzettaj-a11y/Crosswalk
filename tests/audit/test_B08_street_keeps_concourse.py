"""B-08 (High): "1010 Grand Concourse NY 10452" lost "Concourse" from the street. A city is read only after the street end."""
import pytest

from wholecount.engine.prepare.address import parse_address


@pytest.mark.parametrize("raw,street,city", [
    ("1010 Grand Concourse NY 10452", "1010 Grand Concourse", ""),
    ("1 Brooklyn Ave Brooklyn NY 11203", "1 Brooklyn Ave", "Brooklyn"),
    ("100 Jamaica Ave Queens NY 11418", "100 Jamaica Ave", "Queens"),
    ("5 Queens Blvd Queens NY 11375", "5 Queens Blvd", "Queens"),
    ("100 New York Ave Brooklyn NY 11216", "100 New York Ave", "Brooklyn"),
    ("9 Bronx River Ave Bronx NY 10472", "9 Bronx River Ave", "Bronx"),
    ("7 Staten Island Expy Staten Island NY 10314", "7 Staten Island Expy", "Staten Island"),
    ("3 Flushing Ave Brooklyn NY 11205", "3 Flushing Ave", "Brooklyn"),
])
def test_B08_street_whole_and_city_after_it(raw, street, city):
    a = parse_address(raw)
    assert (a.street, a.city, a.state) == (street, city, "NY")
