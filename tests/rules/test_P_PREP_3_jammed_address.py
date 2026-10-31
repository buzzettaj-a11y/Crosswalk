"""P-PREP-3: the jammed-address table in the milestone, and split_trailing_unit for P-STD-8."""
import pytest

from wholecount.engine.prepare.address import parse_address, split_trailing_unit


@pytest.mark.parametrize("raw,street,unit,city,state,zip_,extra", [
    ("117 - 19 45th Ave, Flushing, NY 11355", "117-19 45th Ave", "", "Flushing", "NY", "11355", ""),
    ("1010 Grand Concourse NY 10452", "1010 Grand Concourse", "", "", "NY", "10452", ""),
    ("123 Main St, Brooklyn, NY 112011234", "123 Main St", "", "Brooklyn", "NY", "11201", ""),
    ("123 Main St, Apt 3 Brooklyn NY 11201", "123 Main St", "Apt 3", "Brooklyn", "NY", "11201", ""),
    ("123 Main St, c/o Jane Doe", "123 Main St", "", "", "", "", "c/o Jane Doe"),
    ("85-10 Forest Pkwy Woodhaven NY 11421", "85-10 Forest Pkwy", "", "Woodhaven", "NY", "11421", ""),
    ("100 Avenue U", "100 Avenue U", "", "", "", "", ""),
    ("9 Elm St, Newark, NJ 07102", "9 Elm St", "", "Newark, NJ", "", "07102", ""),
])
def test_table(raw, street, unit, city, state, zip_, extra):
    a = parse_address(raw)
    assert (a.street, a.unit, a.city, a.state, a.zip, a.extra) == (street, unit, city, state, zip_, extra)


def test_other_state_codes_stay_in_the_text():
    a = parse_address("5 Oak Pl Hartford CT 06103")
    assert a.state == "" and "CT" in a.city


def test_country_and_end_punctuation():
    a = parse_address("100 Grand St Apt 4 Brooklyn NY 11211 USA,")
    assert (a.street, a.unit, a.city, a.zip) == ("100 Grand St", "Apt 4", "Brooklyn", "11211")


@pytest.mark.parametrize("text,street,unit", [
    ("67 Franklin Avenue Apt. 10 R", "67 Franklin Avenue", "Apt. 10 R"), ("25 Tom Street APT18L", "25 Tom Street", "APT18L"),
    ("67 Jill Ave Apt#: 11T", "67 Jill Ave", "Apt#: 11T"), ("123 Main St Apt 2A", "123 Main St", "Apt 2A"),
    ("10 Apartment Way", "10 Apartment Way", None), ("88 Front St", "88 Front St", None), ("100 Avenue U", "100 Avenue U", None),
])
def test_split_trailing_unit(text, street, unit):
    assert split_trailing_unit(text) == (street, unit)


def test_everything_a_unit_keeps_the_original_in_street():
    a = parse_address("Apt 4B")
    assert a.street == "Apt 4B" and a.unit == ""
