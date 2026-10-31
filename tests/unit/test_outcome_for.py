"""outcome_for (M05 LOC-1 to LOC-4, P-VAL-1): M04's location status and a GeoResult give the row's location status."""
import pytest

from wholecount import copy
from wholecount.engine.geo.place import outcome_for
from wholecount.engine.geo.types import GeoResult, not_placed
from wholecount.engine.standardize.model import LocationStatus

TO_PLACE = LocationStatus("to_place")
HIGH = GeoResult("high", "matched_building", 40.7, -73.99, source="fake")
LOW = GeoResult("low", "matched_with_warning", 40.7, -73.99, source="fake")


@pytest.mark.parametrize("reason", ["no_fixed_address", "outside_nyc", "address_problem"])
def test_LOC_1_not_mapped_keeps_its_reason(reason):
    o = outcome_for(LocationStatus("not_mapped", reason), HIGH)
    assert (o.kind, o.confidence, o.reason) == ("not_mapped", None, reason)


@pytest.mark.claim("CL-GEO-LOC-02")
def test_LOC_2_no_backend_is_no_geocoder():
    o = outcome_for(TO_PLACE, not_placed("no_backend", "none"))
    assert (o.kind, o.reason) == ("not_mapped", "no_geocoder")
    assert copy.get("location.not_mapped.no_geocoder") == "Counted, not mapped: no geocoder."


@pytest.mark.claim("CL-GEO-LOC-01")
@pytest.mark.parametrize("reason", ["not_found", "reference_ambiguous"])
def test_LOC_3_other_not_placed_is_not_found(reason):
    o = outcome_for(TO_PLACE, not_placed(reason, "reference"))
    assert (o.kind, o.reason) == ("not_mapped", "not_found")
    assert "wasn't found" in copy.get("location.not_mapped.not_found")


def test_LOC_4_high_and_low_are_mapped():
    assert (outcome_for(TO_PLACE, HIGH).kind, outcome_for(TO_PLACE, HIGH).confidence) == ("mapped", "high")
    assert (outcome_for(TO_PLACE, LOW).kind, outcome_for(TO_PLACE, LOW).confidence) == ("mapped", "low")


def test_filled_carries_through():
    assert outcome_for(LocationStatus("to_place", filled=True), HIGH).filled
    assert outcome_for(TO_PLACE, HIGH, filled=True).filled
    assert not outcome_for(TO_PLACE, HIGH).filled
