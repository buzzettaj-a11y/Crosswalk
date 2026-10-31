"""P-STD-5: states, every US state and territory, and the outside-NYC rule."""
import pytest

from tests.support.std import ids, std
from wholecount.engine.geo import places
from wholecount.settings.loader import load

STATES = load("places")["states"]


@pytest.mark.parametrize("text", ["NY", "N.Y.", "ny.", "New York", "New York State", "ny"])
def test_ny_forms(text):
    r = std(State=text)
    assert r.value("State") == "NY" and ids(r) == []


@pytest.mark.parametrize("name,code", list(STATES.items()))
def test_every_state_by_name_and_code(name, code):
    assert places.state_code(name) == code and places.state_code(code) == code and places.state_code(code.lower()) == code


def test_another_state_with_an_nyc_zip_disagrees_and_is_not_outside():
    r = std(City="Brooklyn", State="NJ", Zip="11201")
    assert ids(r) == ["state_zip_disagree"] and not r.outside_nyc and r.value("State") == "NJ"
    assert r.count_status.counted and r.location.reason == "address_problem"


def test_newark_nj_is_outside():
    r = std(City="Newark", State="NJ", Zip="07102")
    assert ids(r) == [] and r.outside_nyc and r.location.reason == "outside_nyc" and r.count_status.counted


def test_state_name_becomes_its_code():
    r = std(City="Newark", State="New Jersey", Zip="07102")
    assert r.value("State") == "NJ" and "state_standardized" in [n.reason_id for n in r.notes]


def test_blanks():
    r = std(State="")
    assert r.value("State") == "NY" and [(f.field, f.kind) for f in r.fills] == [("State", "zip")]
    assert ids(std(State="", Zip="")) == ["address_incomplete", "address_part_missing"]
    assert ids(std(State="", Zip="07030", City="Hoboken")) == ["state_not_recognized"]
    assert ids(std(State="Narnia")) == ["state_not_recognized"]


def test_another_state_with_no_zip_is_outside():
    r = std(State="CT", Zip="", City="Hartford")
    assert r.outside_nyc and "state_not_recognized" not in ids(r)
