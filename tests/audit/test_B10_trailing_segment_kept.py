"""B-10 (High): a trailing comma segment was read as the city and silently dropped."""
from wholecount.engine import reasons
from wholecount.engine.prepare.address import parse_address


def test_B10_unit_hints_become_the_unit():
    assert parse_address("123 Main St, Lower").unit == "Lower"
    assert parse_address("123 Main St, Top Floor").unit == "Top Floor"


def test_B10_care_of_is_kept_as_extra_with_a_location_reason():
    a = parse_address("123 Main St, c/o Jane Doe")
    assert (a.street, a.extra) == ("123 Main St", "c/o Jane Doe")
    assert a.notes == ["address_extra_text"]
    assert reasons.get("address_extra_text").flag == "location"


def test_B10_no_trailing_segment_vanishes():
    for raw in ("123 Main St, Lower", "123 Main St, Top Floor", "123 Main St, c/o Jane Doe", "123 Main St, Rear building"):
        a = parse_address(raw)
        assert a.unit or a.extra or a.city, raw
