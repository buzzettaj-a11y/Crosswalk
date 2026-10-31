"""B-34: the old fill proposed a ZIP or city from a street name alone and said the street "is only in" one place (P-GEO-9)."""
import pytest

from tests.support.geo import ref_b17, row
from wholecount import copy
from wholecount.engine.geo.fill import propose_fills

pytestmark = [pytest.mark.claim("CL-GEO-FILL-01"), pytest.mark.claim("CL-GEO-FILL-02")]


def test_valid_zip_outside_nyc_gives_nothing():
    assert propose_fills(row("r", "85 Montague St", "07030", city="Hoboken"), ref_b17()) == []


def test_house_number_not_in_the_reference_gives_nothing():
    assert propose_fills(row("r", "999 Montague St", "", city="Brooklyn"), ref_b17()) == []


def test_unknown_city_and_blank_zip_gives_nothing():
    assert propose_fills(row("r", "1 Avenue U", "", city="Brookline"), ref_b17()) == []


def test_exact_row_gives_zip_with_evidence():
    (p,) = [p for p in propose_fills(row("r", "85 Montague St", "", city="Brooklyn"), ref_b17()) if p.field == "Zip"]
    assert (p.rule_id, p.value, p.source) == ("FILL-ZIP-1", "11201", "reference")
    assert (p.evidence.house_number, p.evidence.street, p.evidence.came_from_kind, p.evidence.came_from) == (
        "85", "Montague St", "borough", "Brooklyn")
    text = copy.get("geo.fill.evidence.reference", rows=int(p.source_detail), house=p.evidence.house_number,
                    street=p.evidence.street, came_from=p.evidence.came_from, value=f"ZIP {p.value}")
    assert "in the reference i have" in text.lower() and "85 Montague St" in text and "11201" in text


def test_blank_state_with_exact_high_lookup_gives_ny():
    ps = propose_fills(row("r", "85 Montague St", "", city="Brooklyn", State=""), ref_b17())
    assert [(p.rule_id, p.value) for p in ps if p.field == "State"] == [("FILL-STATE-1", "NY")]


def test_no_registry_text_says_is_only_in():
    assert not [e.key for e in copy.all_entries() if "is only in" in e.text.lower() or "only in" in e.text.lower()]
    assert "Geosupport" in copy.get("geo.fill.evidence.geosupport", release="25C", house="85", street="Montague St",
                                    came_from="Brooklyn", value="ZIP 11201")
