"""B-19: the old point-in-polygon treated every ring as solid, so a point in a hole got the outer district (P-GEO-5)."""
import json

from tests.support.geo import donut
from wholecount.engine.geo.districts import DistrictIndex


def test_point_in_the_hole_gets_the_plug():
    assert donut().assign(40.70, -73.95).council == "2"


def test_point_in_the_donut_body():
    assert donut().assign(40.62, -73.99).council == "1"


def test_shared_edge_goes_to_the_smaller_district(tmp_path):
    def sq(n, x0, x1):
        return {"type": "Feature", "properties": {"assembly_district": n},
                "geometry": {"type": "Polygon", "coordinates": [[[x0, 40.6], [x1, 40.6], [x1, 40.7], [x0, 40.7], [x0, 40.6]]]}}
    p = tmp_path / "d.geojson"
    p.write_text(json.dumps({"type": "FeatureCollection", "features": [sq(52, -74.0, -73.9), sq(51, -73.9, -73.8)]}))
    assert DistrictIndex.from_files([p]).assign(40.65, -73.9).assembly == "51"


def test_multipolygon_with_two_parts_and_one_hole(tmp_path):
    ring = lambda x0, y0, x1, y1: [[x0, y0], [x1, y0], [x1, y1], [x0, y1], [x0, y0]]
    geom = {"type": "MultiPolygon", "coordinates": [[ring(-74.0, 40.6, -73.9, 40.7), ring(-73.96, 40.64, -73.94, 40.66)],
                                                     [ring(-73.8, 40.6, -73.7, 40.7)]]}
    p = tmp_path / "m.geojson"
    p.write_text(json.dumps({"type": "FeatureCollection", "features": [
        {"type": "Feature", "properties": {"senate_district": 22}, "geometry": geom}]}))
    idx = DistrictIndex.from_files([p])
    assert idx.assign(40.61, -73.99).senate == "22"
    assert idx.assign(40.65, -73.75).senate == "22"
    assert idx.assign(40.65, -73.95).senate is None
