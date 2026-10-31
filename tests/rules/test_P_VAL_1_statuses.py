"""P-VAL-1: the full precedence of both statuses."""
from tests.support.std import std
from wholecount.engine.standardize.model import count_status_for


def test_count_status_precedence():
    held = std(First_Name="")
    assert count_status_for(held).value == "not_counted_yet"
    assert count_status_for(held, approved=True).value == "counted_approved"
    assert count_status_for(held, corrected=True).value == "counted_corrected"
    assert count_status_for(held, approved=True, corrected=True).value == "counted_corrected"
    clean = std()
    assert count_status_for(clean).value == "counted_passed" and count_status_for(clean, approved=True).value == "counted_approved"
    total = std(First_Name="", Last_Name="Total", Client_ID="", Address_1="", City="", Zip="", Program="", State="")
    assert count_status_for(total, approved=True).value == "set_aside"


def test_location_precedence():
    assert std(Address_1="Homeless", Zip="07030").location.reason == "no_fixed_address"
    assert std(Zip="07030", City="Queens").location.reason == "outside_nyc"
    assert std(City="Queens").location.reason == "address_problem"
    loc = std().location
    assert loc.kind == "to_place" and loc.problems == ()


def test_soft_and_location_reasons_never_change_the_count_status():
    for kw in ({"First_Name": "Na"}, {"City": "Queens"}, {"Zip": "ABCDE"}, {"Date_of_Birth": "soon"}):
        assert std(**kw).count_status.value == "counted_passed", kw
