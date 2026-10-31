"""B-44 (Low): surnames Sum, Mean and Count with no street were set aside as summary rows."""
import pytest

from tests.support.std import ids, std
from wholecount.engine.standardize.model import UnmappedHint

NO_ADDRESS = dict(Address_1="", City="", State="", Zip="")


@pytest.mark.parametrize("first,last", [("Sokha", "Sum"), ("Sokha", "Mean"), ("Count", "Basie")])
def test_B44_real_names_with_an_id_are_counted(first, last):
    r = std(First_Name=first, Last_Name=last, **NO_ADDRESS)
    assert r.count_status.counted and r.set_aside_reason is None
    assert ids(r) == ["address_incomplete", "address_part_missing"]
    assert {(x.reason_id, x.field) for x in r.reasons} == {("address_part_missing", "Address_1"), ("address_part_missing", "City"),
                                                           ("address_part_missing", "Zip"), ("address_incomplete", "State")}
    assert r.location.reason == "address_problem"


def test_B44_total_rows_are_set_aside():
    blank = dict(First_Name="", Last_Name="", Client_ID="", Program="", Middle_Initial="", Address_2="", **NO_ADDRESS)
    for r in (std(**{**blank, "Last_Name": "Total"}), std(**{**blank, "Program": "Grand Total"}),
              std(**blank, unmapped=UnmappedHint(numbers_only=True))):
        assert r.count_status.value == "set_aside" and r.set_aside_reason == "summary_row" and r.reasons == ()
