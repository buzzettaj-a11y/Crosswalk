"""P-STD-2: placeholders by field class, whole cell only."""
import pytest

from tests.support.std import ids, std
from wholecount.engine.standardize.placeholders import is_blank, marker


@pytest.mark.parametrize("text", ["NULL", "n/a", "#N/A", "(null)", "none", "nil", "#REF!", "#VALUE!", "#DIV/0!", "<NA>", "undefined", "-", "--", "?"])
def test_every_field_words_blank_program(text):
    r = std(Program=text)
    assert r.value("Program") == "" and [n.reason_id for n in r.notes if n.field == "Program"] == ["blank_marker"]


@pytest.mark.parametrize("text", ["0", "00", "000", "unknown", "UNK", "refused", "declined", "TBD", "same", "see above", "NA", "N.A.", "xxx"])
def test_identifier_and_address_words(text):
    r = std(Client_ID=text, Date_of_Birth="1990-04-03")
    assert r.value("Client_ID") == "" and ids(r) == ["placeholder_in_value"]
    assert marker("Program", text) is None or marker("Program", text).kind == "every_field"


def test_address_2_gets_a_note_not_a_reason():
    r = std(Address_2="Unknown")
    assert r.value("Address_2") == "" and ids(r) == [] and [n.reason_id for n in r.notes] == ["blank_marker"]


def test_name_rule():
    assert ids(std(First_Name="None")) == ["name_may_be_placeholder"]
    assert ids(std(First_Name="nil")) == ["name_may_be_placeholder"]
    assert "name_missing" in ids(std(First_Name="?"))


@pytest.mark.parametrize("field", ["Address_1", "Address_2", "City", "State", "Zip"])
@pytest.mark.parametrize("word", ["Homeless", "shelter", "STREET", "no fixed address", "NFA", "undomiciled"])
def test_housing_words_in_every_address_field(field, word):
    r = std(**{field: word})
    assert r.no_fixed_address and r.value(field) == "" and r.location.reason == "no_fixed_address" and r.count_status.counted
    assert "address_part_missing" not in ids(r)


def test_whole_cell_only():
    assert std(Address_1="10 Street Rd").value("Address_1") == "10 Street Rd"
    assert not std(Address_1="10 Street Rd").no_fixed_address


def test_is_blank():
    assert is_blank("Client_ID", "TBD") and is_blank("Program", "") and not is_blank("First_Name", "Na") and not is_blank("Program", "0")
