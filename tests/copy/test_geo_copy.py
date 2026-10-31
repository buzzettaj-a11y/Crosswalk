"""H11: each placing sentence states what the code does. One claim test per GEO_REASONS code, plus the fill note."""
import pytest

from tests.support.geo import NO_EXTRAS, fake, reference_of, ref_b17, row
from wholecount import copy
from wholecount.engine.geo.backend import NoBackend
from wholecount.engine.geo.fill import propose_fills
from wholecount.engine.geo.geosupport import GeosupportBackend
from wholecount.engine.geo.place import place_rows
from wholecount.engine.geo.types import GEO_REASONS


class _G:
    def __init__(self, grc, message=""):
        self.grc, self.message = grc, message

    def address(self, **kw):
        return {"Latitude": "40.7", "Longitude": "-73.99", "Geosupport Return Code (GRC)": self.grc, "Message": self.message}


def test_every_reason_code_has_a_sentence():
    for code in GEO_REASONS:
        assert copy.get(f"geo.reason.{code}")


@pytest.mark.claim("CL-GEO-REASON-01")
def test_matched_building_is_an_exact_match():
    assert fake().lookup("100", "W 10 St", "10011").reason == "matched_building"
    assert ref_b17().lookup("100", "West 10 Street", "10011").reason == "matched_building"
    assert "exactly" in copy.get("geo.reason.matched_building")


@pytest.mark.claim("CL-GEO-REASON-02")
def test_matched_with_warning_is_grc_01_and_low():
    r = GeosupportBackend(_G("01"), KeyError, "25C").lookup("1", "Main St", "11201")
    assert (r.reason, r.confidence) == ("matched_with_warning", "low")
    assert "low confidence" in copy.get("geo.reason.matched_with_warning")


@pytest.mark.claim("CL-GEO-REASON-03")
def test_house_out_of_range_is_low():
    r = GeosupportBackend(_G("01", "ADDRESS NUMBER OUT OF RANGE"), KeyError, "25C").lookup("1", "Main St", "11201")
    assert (r.reason, r.confidence) == ("house_out_of_range", "low")
    assert "house number" in copy.get("geo.reason.house_out_of_range")


@pytest.mark.claim("CL-GEO-REASON-04")
def test_street_only_is_low():
    assert GEO_REASONS["matched_street_only"] == "low"
    assert "low confidence" in copy.get("geo.reason.matched_street_only")


@pytest.mark.claim("CL-GEO-REASON-05")
def test_not_found_places_nothing():
    r = ref_b17().lookup("111", "Main St", "11201")
    assert r.reason == "not_found" and r.latitude is None
    assert GeosupportBackend(_G("42"), KeyError, "25C").lookup("1", "Main St", "11201").reason == "not_found"
    assert "wasn't placed" in copy.get("geo.reason.not_found")


@pytest.mark.claim("CL-GEO-REASON-06")
def test_two_points_far_apart_are_ambiguous():
    far = reference_of([("1", "Oak St", "11201", "Brooklyn", 40.70, -73.99), ("1", "Oak St", "11201", "Brooklyn", 40.71, -73.99)])
    near = reference_of([("1", "Oak St", "11201", "Brooklyn", 40.70, -73.99), ("1", "Oak St", "11201", "Brooklyn", 40.7001, -73.99)])
    assert far.lookup("1", "Oak St", "11201").reason == "reference_ambiguous"
    r = near.lookup("1", "Oak St", "11201")
    assert (r.confidence, r.latitude) == ("high", 40.70)
    assert "two different points" in copy.get("geo.reason.reference_ambiguous")


@pytest.mark.claim("CL-GEO-REASON-07")
def test_no_backend_looks_nothing_up():
    pr = place_rows([row("r", "1 Main St", "11201")], NoBackend(), None, NO_EXTRAS)
    assert pr.results["r"].reason == "no_backend"
    assert "No geocoder" in copy.get("geo.reason.no_backend")


@pytest.mark.claim("CL-GEO-FILL-03")
def test_a_proposal_changes_nothing():
    r = row("r", "85 Montague St", "", city="Brooklyn")
    before = {k: (v.value, v.entered) for k, v in r.values.items()}
    assert propose_fills(r, ref_b17())
    assert {k: (v.value, v.entered) for k, v in r.values.items()} == before
    assert copy.get("geo.fill.nothing_changes") == "Nothing changes until you accept it."
