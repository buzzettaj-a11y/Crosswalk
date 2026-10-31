"""B-03 (High): Nassau County ZIPs were treated as Queens and overwrote the typed city."""
import pytest

from tests.support.std import ids, std


@pytest.mark.parametrize("city,zip_", [("Hempstead", "11550"), ("Garden City", "11530"), ("Valley Stream", "11580"), ("Mineola", "11501")])
def test_B03_nassau_rows_are_outside_nyc_with_the_city_kept(city, zip_):
    r = std(City=city, Zip=zip_, State="")
    assert r.count_status.counted and r.location.reason == "outside_nyc"
    assert r.value("City") == city and r.value("State") == "" and "state_not_recognized" in ids(r)


def test_B03_blank_city_stays_blank():
    r = std(City="", Zip="11550")
    assert r.value("City") == "" and "address_part_missing" in ids(r) and r.location.reason == "outside_nyc"


def test_B03_brooklyn_with_a_nassau_zip_disagrees():
    r = std(City="Brooklyn", Zip="11550")
    assert "city_zip_disagree" in ids(r) and r.value("City") == "Brooklyn"
    assert "Queens" not in r.values["City"].suggestions


def test_B03_far_rockaway_is_queens_and_placed():
    r = std(City="Far Rockaway", Zip="11691")
    assert ids(r) == [] and r.location.kind == "to_place" and r.value("City") == "Queens"
