"""Placing addresses (SPEC 6.6 P-GEO-1 to P-GEO-9) and M05's DIST, OFF, MAP and FILL rules."""
import dataclasses
import datetime as dt
import json
import math

import pytest

from tests.support.geo import MAC, NO_EXTRAS, OTHER_MAC, SAMPLE, TRACT, donut, fake, ref_b17, reference_of, row
from wholecount.engine.addresskey import address_key
from wholecount.engine.geo.backend import NoBackend, select_backend
from wholecount.engine.geo.districts import DistrictIndex
from wholecount.engine.geo.fill import propose_fills
from wholecount.engine.geo.mapdata import MapEntry, MapPointEntry, build_map_counts, build_map_points
from wholecount.engine.geo.offset import PrivacyOffset, haversine_ft, move_point, stable_offset
from wholecount.engine.geo.place import building_key, place_rows, to_query
from wholecount.engine.geo.reference import ReferenceBackend
from wholecount.engine.geo.types import Districts, GeoResult


# P-GEO

def test_P_GEO_1_backend_interface_is_lookup_house_street_where():
    for backend in (fake(), ref_b17(), NoBackend()):
        r = backend.lookup("100", "W 10 St", "10011")
        assert isinstance(r, GeoResult)
    assert fake().lookup("100", "W 10 St", "10011").source == "fake"


def test_P_GEO_2_confidence_levels_and_verified_only_for_high():
    high = fake().lookup("100", "W 10 St", "10011")
    low = fake().lookup("77", "Warning Pl", "11201")
    none = fake().lookup("111", "Main St", "11201")
    assert (high.confidence, low.confidence, none.confidence) == ("high", "low", "not_placed")
    assert high.verified and not low.verified and not none.verified
    with pytest.raises(ValueError):
        GeoResult("high", "matched_with_warning")


def test_P_GEO_3_reference_is_exact_only_and_suggestions_never_place():
    ref = ref_b17()
    assert ref.lookup("123", "Fultin St", "11201").confidence == "not_placed"
    s = ref.suggest("123", "Fultin St", "11201")
    assert [(x.house_number, x.street) for x in s] == [("123", "Fulton St")]
    assert not any(hasattr(x, "latitude") for x in s)
    assert ref.lookup("100", "West 10 Street", "10011").confidence == "high"
    assert ref.lookup("100", "W 10 St", "New York").confidence == "high"


def test_P_GEO_4_sample_reference_only_with_allow_sample():
    sample = ReferenceBackend.from_path(SAMPLE)
    assert sample.is_sample and sample.name == "reference_sample"
    assert select_backend(None, sample).name == "none"
    assert select_backend(None, sample, allow_sample=True) is sample
    assert NoBackend().lookup("1", "Main St", "11201").reason == "no_backend"


def test_P_GEO_4a_example_addresses_are_in_the_sample():
    sample = ReferenceBackend.from_path(SAMPLE)
    plan = json.loads((SAMPLE.parent / "EXPECTED.json").read_text(encoding="utf-8"))["locations"]
    assert sample.rows == plan["reference_rows"] > 0


def test_P_GEO_5_districts_from_the_true_point_with_holes():
    ref = reference_of([("1", "Hole St", "11201", "Brooklyn", 40.70, -73.95)])
    res = place_rows([row("r1", "1 Hole St", "11201")], ref, donut(), NO_EXTRAS).results["r1"]
    assert res.districts == Districts("2", "2", "2")


def test_P_GEO_6_map_counts_hold_no_person_fields():
    names = {f.name for f in dataclasses.fields(build_map_counts([MapEntry("u", "P", Districts("1", "2", "3"))], 10)[0])}
    assert names == {"program", "district_type", "district", "count"}


def test_P_GEO_7_offset_is_keyed_by_secret_and_address_key():
    a = PrivacyOffset(MAC).apply("1|main street|11201", 40.7, -73.99)
    assert a == PrivacyOffset(MAC).apply("1|main street|11201", 40.7, -73.99)
    assert a != PrivacyOffset(OTHER_MAC).apply("1|main street|11201", 40.7, -73.99)
    assert 149.5 <= haversine_ft(40.7, -73.99, *a) <= 250.5


@pytest.mark.parametrize("make", [fake, ref_b17, NoBackend])
def test_P_GEO_8_each_source_runs_end_to_end(make):
    pr = place_rows([row("r1", "1 Main St", "11201"), row("r2", "999 Nowhere Ave", "11201")], make(), donut(), NO_EXTRAS)
    assert set(pr.results) == {"r1", "r2"}


def test_P_GEO_9_fill_needs_the_house_number():
    ref = ref_b17()
    assert propose_fills(row("r", "Montague St", "", city="Brooklyn"), ref) == []
    assert [p.value for p in propose_fills(row("r", "85 Montague St", "", city="Brooklyn"), ref) if p.field == "Zip"] == ["11201"]


# DIST

def _square(n, x0, y0, x1, y1, kind="council_district"):
    return {"type": "Feature", "properties": {kind: n},
            "geometry": {"type": "Polygon", "coordinates": [[[x0, y0], [x1, y0], [x1, y1], [x0, y1], [x0, y0]]]}}


def _index(tmp_path, *features):
    p = tmp_path / "d.geojson"
    p.write_text(json.dumps({"type": "FeatureCollection", "features": list(features)}), encoding="utf-8")
    return DistrictIndex.from_files([p])


def test_DIST_1_ring_zero_outer_later_rings_holes_multipolygon_any_member(tmp_path):
    d = donut()
    assert d.assign(40.70, -73.95).council == "2"
    assert d.assign(40.62, -73.99).council == "1"
    multi = {"type": "Feature", "properties": {"council_district": 9}, "geometry": {"type": "MultiPolygon", "coordinates": [
        [[[0, 0], [1, 0], [1, 1], [0, 1], [0, 0]], [[0.4, 0.4], [0.6, 0.4], [0.6, 0.6], [0.4, 0.6], [0.4, 0.4]]],
        [[[2, 0], [3, 0], [3, 1], [2, 1], [2, 0]]]]}}
    idx = _index(tmp_path, multi)
    assert idx.assign(0.2, 0.2).council == "9" and idx.assign(0.5, 2.5).council == "9"
    assert idx.assign(0.5, 0.5).council is None and idx.assign(0.5, 1.5).council is None


def test_DIST_2_boundary_counts_and_smallest_number_wins(tmp_path):
    idx = _index(tmp_path, _square(12, 0, 0, 1, 1), _square(3, 1, 0, 2, 1))
    assert idx.assign(0.5, 1.0).council == "3"
    assert idx.assign(0.5, 0.0).council == "12"
    assert _index(tmp_path, _square(10, 0, 0, 1, 1), _square(9, 0, 0, 1, 1)).assign(0.5, 0.5).council == "9"


def test_DIST_3_bounding_box_first(tmp_path):
    idx = _index(tmp_path, _square(1, 0, 0, 1, 1))
    f = idx.features[0]
    assert f.bbox == (0, 0, 1, 1) and not f.contains(5, 5)


def test_DIST_4_geojson_order_is_longitude_then_latitude(tmp_path):
    idx = _index(tmp_path, _square(1, -74.0, 40.6, -73.9, 40.8))
    assert idx.assign(40.7, -73.95).council == "1"
    assert idx.assign(-73.95, 40.7).council is None


def test_DIST_5_districts_never_from_the_moved_point():
    ref = reference_of([("1", "Hole St", "11201", "Brooklyn", 40.70, -73.95)])
    res = place_rows([row("r1", "1 Hole St", "11201")], ref, donut(), NO_EXTRAS).results["r1"]
    assert res.districts == donut().assign(res.latitude, res.longitude)
    assert (res.latitude, res.longitude) == (40.70, -73.95)


def test_DIST_any_subset_of_properties_and_several_files(tmp_path):
    a = tmp_path / "a.geojson"
    a.write_text(json.dumps({"type": "FeatureCollection", "features": [_square(4, 0, 0, 1, 1, "senate_district")]}))
    b = tmp_path / "b.geojson"
    b.write_text(json.dumps({"type": "FeatureCollection", "features": [_square(7, 0, 0, 1, 1, "assembly_district")]}))
    assert DistrictIndex.from_files([a, b]).assign(0.5, 0.5) == Districts("4", "7", None)


# OFF

def test_OFF_1_building_key_uses_the_returned_zip():
    q = to_query(row("r", "100 W 10 St", ""))
    res = fake().lookup("100", "W 10 St", "10011")
    assert building_key(q, res) == "100|west 10 street|10011"
    assert building_key(q, dataclasses.replace(res, zip5=None), "10011") == "100|west 10 street|10011"
    assert building_key(q, dataclasses.replace(res, zip5=None), "") == "100|west 10 street|-"
    blank = place_rows([row("a", "1 Main St", "11201")], fake(), None, NO_EXTRAS).building_keys["a"]
    assert blank == address_key("1", "Main St", "11201")


def test_OFF_2_one_point_per_building():
    entries = [MapPointEntry("P", "1|main street|11201", 40.70, -73.99) for _ in range(50)]
    pts = build_map_points(entries, MAC)
    assert len({(p.latitude, p.longitude) for p in pts}) == 1


def test_OFF_3_no_random_and_no_seed_in_the_geo_package():
    from tests.conftest import ROOT
    for p in (ROOT / "wholecount" / "engine" / "geo").rglob("*.py"):
        text = p.read_text(encoding="utf-8")
        assert "import random" not in text and "from random" not in text, p
        assert "1337" not in text and "seed" not in text.lower(), p


def test_OFF_4_one_installation_one_point_another_differs():
    d1, b1 = stable_offset(MAC, "1|main street|11201")
    assert (d1, b1) == stable_offset(MAC, "1|main street|11201")
    assert (d1, b1) != stable_offset(OTHER_MAC, "1|main street|11201")


def test_OFF_5_audit_records_only_that_the_offset_was_applied():
    pr = place_rows([row("r1", "1 Main St", "11201")], fake(), None, NO_EXTRAS)
    entry = [a for a in pr.audit if a.event == "privacy_offset_applied"]
    assert entry and entry[0].rule_id == "P-GEO-7"
    assert {f.name for f in dataclasses.fields(entry[0])} == {"rule_id", "event", "backend", "release", "practice", "looked_up",
                                                             "placed"}


def test_OFF_golden_vectors():
    d, b = stable_offset(MAC, "100|west 10 street|10011")
    assert round(d, 4) == 172.6566 and round(b, 6) == 0.400361
    lat, lon = move_point(40.7350, -73.9990, d, b)
    assert (round(lat, 7), round(lon, 7)) == (40.7354354, -73.9987568)
    assert math.isclose(haversine_ft(40.7350, -73.9990, lat, lon), d, rel_tol=2e-3)


# MAP

def test_MAP_1_rows_blanking_and_sorting():
    entries = [MapEntry(f"u{i}", "B", Districts("2", "10", "33")) for i in range(11)]
    entries += [MapEntry("v1", "A", Districts(None, None, "7")), MapEntry("v1", "A", Districts(None, None, "7"))]
    rows = build_map_counts(entries, 10)
    assert [(r.program, r.district_type, r.district, r.count) for r in rows] == [
        ("A", "council", "7", None), ("B", "council", "33", 11), ("B", "assembly", "10", 11), ("B", "senate", "2", 11)]


def test_MAP_2_none_districts_add_nothing():
    assert build_map_counts([MapEntry("u", "P", Districts(None, None, None))], 10) == []


def test_MAP_3_points_sorted_by_program_and_point_never_by_person():
    entries = [MapPointEntry("B", "2|main street|11201", 40.71, -73.98), MapPointEntry("A", "1|main street|11201", 40.70, -73.99),
               MapPointEntry("A", "11|main street|11201", 40.704, -73.98)]
    pts = build_map_points(entries, MAC)
    assert [p.program for p in pts] == ["A", "A", "B"]
    assert pts == sorted(pts, key=lambda p: (p.program, p.latitude, p.longitude))
    assert build_map_points(list(reversed(entries)), MAC) == pts


# FILL

def test_FILL_ZIP_1_blank_zip_from_an_exact_borough_hit():
    (p,) = [p for p in propose_fills(row("r", "85 Montague St", "", city="Brooklyn"), ref_b17()) if p.field == "Zip"]
    assert (p.value, p.rule_id, p.source, p.source_detail) == ("11201", "FILL-ZIP-1", "reference", "18")
    assert p.basis.startswith("FILL-ZIP-1|reference|") and "11201" not in p.basis


def test_FILL_CITY_1_unrecognized_city_with_an_nyc_zip():
    (p,) = propose_fills(row("r", "85 Montague St", "11201", city="Brooklin"), ref_b17())
    assert (p.field, p.value, p.rule_id) == ("City", "Brooklyn", "FILL-CITY-1")
    assert propose_fills(row("r", "85 Montague St", "11201", city="Brooklyn"), ref_b17()) == []


def test_FILL_CITY_2_blank_city_and_zip_one_borough_only():
    ps = propose_fills(row("r", "85 Montague St", "", city=""), ref_b17())
    assert [(p.field, p.value, p.rule_id) for p in ps] == [("City", "Brooklyn", "FILL-CITY-2")]
    two = reference_of([("5", "Main St", "11201", "Brooklyn", 40.70, -73.99), ("5", "Main St", "10003", "New York", 40.73, -73.99)])
    assert propose_fills(row("r", "5 Main St", "", city=""), two) == []


def test_FILL_STATE_1_blank_state_with_a_high_lookup():
    ps = propose_fills(row("r", "85 Montague St", "", city="Brooklyn", State=""), ref_b17())
    assert ("State", "NY", "FILL-STATE-1") in [(p.field, p.value, p.rule_id) for p in ps]
    assert not [p for p in propose_fills(row("r", "85 Montague St", "", city="Brooklyn", State="NJ"), ref_b17())
                if p.field == "State"]
    assert propose_fills(row("r", "85 Montague St", "07030", city="Brooklyn", State=""), ref_b17()) == []


def test_FILL_no_proposal_without_a_source():
    assert propose_fills(row("r", "85 Montague St", "", city="Brooklyn"), NoBackend()) == []
    assert propose_fills(row("r", "85 Montague St", "", city="Brooklyn"), fake()) == []


def test_census_tract_only_when_asked():
    rows = [row("r1", "1 Main St", "11201")]
    assert place_rows(rows, fake(), None, NO_EXTRAS).results["r1"].census_tract is None
    assert place_rows(rows, fake(), None, TRACT).results["r1"].census_tract == "0001"


def test_units_moved_out_before_the_query():
    q = to_query(row("r", "123 Fulton St Apt 2A", "11201"))
    assert (q.house_number, q.street, q.borough_or_zip) == ("123", "Fulton St", "11201")
