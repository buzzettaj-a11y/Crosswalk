"""B-35: the old app called a GRC 01 match "Medium" and could read Verified for it. Only High reads Verified (P-GEO-2)."""
import pytest

from tests.support.geo import fake, ref_b17
from wholecount import copy
from wholecount.engine.geo.backend import NoBackend
from wholecount.engine.geo.geosupport import GeosupportBackend
from wholecount.engine.geo.types import GEO_REASONS, GeoResult

pytestmark = [pytest.mark.claim("CL-GEO-HIGH-01"), pytest.mark.claim("CL-GEO-HIGH-02"), pytest.mark.claim("CL-GEO-HIGH-03")]


def label(result):
    if result.confidence == "high":
        return copy.get("location.mapped_high")
    if result.confidence == "low":
        return copy.get("location.mapped_low")
    return None


class _G:
    def __init__(self, grc, message=""):
        self.grc, self.message = grc, message

    def address(self, **kw):
        return {"Latitude": "40.7", "Longitude": "-73.99", "Geosupport Return Code (GRC)": self.grc, "Message": self.message,
                "ZIP Code": "11201", "First Borough Name": "BROOKLYN"}


def test_only_high_is_verified_and_reads_high():
    results = [fake().lookup("100", "W 10 St", "10011"), fake().lookup("77", "Warning Pl", "11201"),
               fake().lookup("111", "Main St", "11201"), ref_b17().lookup("1", "Main St", "11201"),
               NoBackend().lookup("1", "Main St", "11201"),
               GeosupportBackend(_G("01"), KeyError, "25C").lookup("1", "Main St", "11201"),
               GeosupportBackend(_G("01", "HOUSE NUMBER OUT OF RANGE"), KeyError, "25C").lookup("1", "Main St", "11201")]
    for r in results:
        assert r.confidence and r.reason in GEO_REASONS
        assert r.verified == (r.confidence == "high")
        assert (label(r) == copy.get("location.mapped_high")) == (r.confidence == "high")
    assert [r.reason for r in results[-2:]] == ["matched_with_warning", "house_out_of_range"]
    assert results[-1].confidence == "low"


def test_no_low_reason_can_be_built_as_high():
    for reason, conf in GEO_REASONS.items():
        for other in {"high", "low", "not_placed"} - {conf}:
            with pytest.raises(ValueError):
                GeoResult(other, reason)


def test_labels_say_what_they_mean():
    assert copy.get("location.mapped_high") == "Mapped, high confidence"
    assert copy.get("location.mapped_low") == "Mapped, low confidence"
    assert copy.get("location.verified") == "Verified"
