"""B-05 (High): non-NYC place names were folded into a borough and State defaulted to NY."""
import pytest

from tests.support.std import ids, std


@pytest.mark.parametrize("city,zip_", [("Chelsea", "02150"), ("Riverdale", "20737"), ("Flushing", "48433"), ("Jamaica", "05343"),
                                       ("Brookline", "02446")])
def test_B05_blank_state_is_not_set_to_ny(city, zip_):
    r = std(City=city, State="", Zip=zip_)
    assert r.value("City") == city and r.value("State") == "" and ids(r) == ["state_not_recognized"]
    assert r.count_status.counted and r.location.reason == "outside_nyc"


@pytest.mark.parametrize("city,state,zip_", [("Chelsea", "MA", "02150"), ("Flushing", "MI", "48433")])
def test_B05_typed_other_state_is_kept_and_not_folded(city, state, zip_):
    r = std(City=city, State=state, Zip=zip_)
    assert (r.value("City"), r.value("State")) == (city, state) and ids(r) == []
