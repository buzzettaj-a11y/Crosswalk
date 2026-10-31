"""B-01 (High): placeholders outside the sentinel list passed as real names, IDs and addresses."""
import pytest

from tests.support.std import ids, std


def status(r):
    return r.count_status.value


@pytest.mark.parametrize("field", ["First_Name", "Last_Name"])
def test_B01_dash_names_are_missing(field):
    r = std(**{field: "-"})
    assert "name_missing" in ids(r) and status(r) == "not_counted_yet"


@pytest.mark.parametrize("value", ["-", "0"])
def test_B01_placeholder_id_without_dob_is_not_counted(value):
    r = std(Client_ID=value)
    assert "no_identifier" in ids(r) and status(r) == "not_counted_yet"


def test_B01_placeholder_id_with_a_valid_dob_is_counted():
    r = std(Client_ID="0", Date_of_Birth="1990-04-03")
    assert ids(r) == ["placeholder_in_value"] and status(r) == "counted_passed"


@pytest.mark.parametrize("value", ["Unknown", "0"])
def test_B01_placeholder_street_is_counted_with_an_address_problem(value):
    r = std(Address_1=value)
    assert {"placeholder_in_value", "address_part_missing"} <= set(ids(r))
    assert status(r) == "counted_passed" and r.location.reason == "address_problem"


@pytest.mark.parametrize("value", ["-", "0"])
def test_B01_address_2_blanks_with_no_review(value):
    r = std(Address_2=value)
    assert r.value("Address_2") == "" and ids(r) == []


@pytest.mark.parametrize("value", ["TBD", "n.a.", "?", "XXX", "TBD."])
def test_B01_more_placeholders_blank_ids_and_addresses(value):
    assert std(Client_ID=value, Date_of_Birth="1990-04-03").value("Client_ID") == ""
    assert std(Address_1=value).value("Address_1") == ""


def test_B01_text_inside_a_value_stays():
    r = std(Address_1="123 Unknown Ave")
    assert r.value("Address_1") == "123 Unknown Ave" and ids(r) == []


def test_B01_homeless_is_no_fixed_address_and_counted():
    r = std(Address_1="Homeless", City="", State="", Zip="")
    assert ids(r) == [] and r.no_fixed_address and status(r) == "counted_passed"
    assert r.location.reason == "no_fixed_address"
