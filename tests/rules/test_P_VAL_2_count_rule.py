"""P-VAL-2: the count rule, each condition alone, and no address damage changing the count status."""
import pytest

from tests.support.std import ids, std
from wholecount.engine.schema import FieldType, default_schema


def test_each_condition():
    assert std(First_Name="").count_status.value == "not_counted_yet"
    assert std(Last_Name="").count_status.value == "not_counted_yet"
    assert std(Client_ID="").count_status.value == "not_counted_yet"
    s = default_schema().add_custom("Score", type=FieldType.WHOLE_NUMBER, needed_to_count=True)
    assert std(schema=s, Score="x").count_status.value == "not_counted_yet"
    assert std(schema=s, Score="3").count_status.counted


def test_a_valid_dob_rescues_a_missing_id():
    assert std(Client_ID="", Date_of_Birth="1990-04-03").count_status.counted
    assert not std(Client_ID="", Date_of_Birth="soon").count_status.counted


@pytest.mark.parametrize("damage", [{"Address_1": ""}, {"City": "Narnia"}, {"State": "ZZ"}, {"Zip": "x"}, {"Zip": "07030"},
                                    {"Address_1": "Unknown", "City": "", "State": "", "Zip": ""}])
def test_address_damage_never_changes_the_count_status(damage):
    assert std(**damage).count_status.value == "counted_passed"
