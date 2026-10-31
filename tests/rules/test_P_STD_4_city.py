"""P-STD-4: every row of the city table in the M04 milestone."""
import pytest

from tests.support.std import ids, std


@pytest.mark.parametrize("city,state,zip_,value,reasons,note", [
    ("", "NY", "11201", "Brooklyn", [], "city_filled_from_zip"),
    ("", "NY", "07030", "", ["address_part_missing"], None),
    ("", "NY", "", "", ["address_part_missing"], None),
    ("Bklyn", "NY", "11201", "Brooklyn", [], "city_standardized"),
    ("Park Slope", "NY", "11201", "Brooklyn", [], "city_standardized"),
    ("Brooklyn", "NY", "11201", "Brooklyn", [], None),
    ("Queens", "NY", "11201", "Queens", ["city_zip_disagree"], None),
    ("Brooklyn", "NY", "07030", "Brooklyn", ["city_zip_disagree"], None),
    ("Chelsea", "NY", "07030", "Chelsea", [], None),
    ("Bklyn", "NY", "", "Brooklyn", [], "city_standardized"),
    ("Bklyn", "NJ", "", "Bklyn", [], None),
    ("Springfield", "NY", "11201", "Springfield", ["city_not_recognized"], None),
    ("Springfield", "NY", "", "Springfield", ["city_not_recognized"], None),
    ("Springfield", "NY", "07030", "Springfield", [], None),
    ("Springfield", "MA", "", "Springfield", [], None),
])
def test_city_table(city, state, zip_, value, reasons, note):
    r = std(City=city, State=state, Zip=zip_)
    got = [x for x in ids(r) if x in ("address_part_missing", "city_zip_disagree", "city_not_recognized")]
    city_reasons = [x.reason_id for x in r.reasons if x.field == "City"]
    assert r.value("City") == value and sorted(city_reasons) == reasons
    assert [n.reason_id for n in r.notes if n.field == "City"] == ([note] if note else [])


def test_a_city_is_never_changed_except_to_its_own_borough():
    r = std(City="Queens", Zip="11201")
    assert r.value("City") == "Queens" and r.values["City"].suggestions == ("Brooklyn",)


def test_blank_city_fill_is_recorded():
    r = std(City="")
    assert [(f.field, f.kind) for f in r.fills] == [("City", "zip")] and r.location.filled
