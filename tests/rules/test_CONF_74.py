"""Batch confidence (SPEC 7.4): boundaries, the no-geocoder sentence, the spec example and the parts order."""
import pytest

from wholecount import copy
from wholecount.engine.confidence import batch_confidence
from wholecount.engine.counts import Counts, Locations, Range

R = Range(0, 0)


def counts(counted, received, pairs=0, high=0, looked=0, no_geocoder=0):
    locs = Locations(high=high, not_found=looked - high, no_geocoder=no_geocoder)
    return Counts(R, R, {}, R, pairs, 0, received, counted, received - counted, 0, locs, False)


@pytest.mark.claim("CL-CONF-03")
def test_high_at_exactly_95():
    assert batch_confidence(counts(95, 100, 0, 95, 100)).level == "high"
    assert batch_confidence(counts(94, 100, 0, 95, 100)).level == "medium"
    assert copy.get("confidence.high_reason", counted=95, received=100, high=95, looked_up=100)


def test_low_under_80_and_not_at_80():
    assert batch_confidence(counts(80, 100, 0, 95, 100)).level == "medium"
    assert batch_confidence(counts(79, 100, 0, 95, 100)).level == "low"
    assert batch_confidence(counts(95, 100, 0, 79, 100)).level == "low"


@pytest.mark.claim("CL-CONF-02")
def test_nothing_looked_up_cannot_be_high():
    c = batch_confidence(counts(100, 100, 0, 0, 0, no_geocoder=100))
    assert c.level == "medium" and c.parts == (("placed_unavailable_no_geocoder", {}),)
    assert copy.get("confidence.part.placed_unavailable_no_geocoder") == "Addresses weren't placed, so confidence can't be High."


@pytest.mark.claim("CL-CONF-07")
def test_geocoder_present_but_nothing_looked_up():
    c = batch_confidence(counts(100, 100))
    assert c.parts == (("placed_unavailable_none_looked_up", {}),)
    assert copy.get("confidence.part.placed_unavailable_none_looked_up")


@pytest.mark.claim("CL-CONF-01")
@pytest.mark.claim("CL-CONF-05")
def test_spec_example():
    c = batch_confidence(counts(6084, 7412, 14, 96, 100))
    assert c.level == "medium"
    a, b = c.parts
    text = copy.get("confidence.level.medium") + ". " + copy.get(f"confidence.part.{a[0]}", **a[1]) + ", and " + \
        copy.get(f"confidence.part.{b[0]}", **b[1]) + "."
    assert text == "Medium. 6,084 of 7,412 rows are counted, and 14 possible same-person pairs are still open."


@pytest.mark.claim("CL-CONF-06")
def test_parts_order_puts_a_low_measure_first():
    c = batch_confidence(counts(90, 100, 3, 70, 100))
    assert [p[0] for p in c.parts] == ["placed_short", "counted_short", "pairs_open"]
    assert copy.get("confidence.part.placed_short", high=70, looked_up=100)


def test_nothing_received_has_no_confidence():
    assert batch_confidence(counts(0, 0)).level is None


@pytest.mark.claim("CL-CONF-04")
def test_acknowledgment_text():
    assert "Low" in copy.get("confidence.acknowledge")
