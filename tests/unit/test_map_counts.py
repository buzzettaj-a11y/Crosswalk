"""build_map_counts (P-GEO-6, MAP-1, MAP-2): small cells blanked, sorted, census tract rows only when present."""
import dataclasses

import pytest

from wholecount import copy
from wholecount.engine.geo.mapdata import MapCountRow, MapEntry, build_map_counts, small_cell_max
from wholecount.engine.geo.types import Districts


def _entries(n, program="P", council="1", tract=None):
    return [MapEntry(f"{program}{council}-{i}", program, Districts(None, None, council), tract) for i in range(n)]


def _count(rows, kind="council"):
    (r,) = [r for r in rows if r.district_type == kind]
    return r.count


@pytest.mark.claim("CL-GEO-MAP-01")
def test_cells_of_1_10_11_and_0():
    assert _count(build_map_counts(_entries(1), 10)) is None
    assert _count(build_map_counts(_entries(10), 10)) is None
    assert _count(build_map_counts(_entries(11), 10)) == 11
    assert build_map_counts([], 10) == []
    assert small_cell_max() == 10
    assert copy.get("map.fewer_than", limit=small_cell_max() + 1) == "fewer than 11"


def test_one_unit_counted_once_per_cell():
    e = _entries(1) * 20
    assert build_map_counts(e, 0)[0].count == 1


def test_sorting_by_program_type_then_number():
    entries = _entries(1, "B", "10") + _entries(1, "B", "9") + _entries(1, "A", "2")
    entries += [MapEntry("x", "A", Districts("30", "40", None))]
    rows = build_map_counts(entries, 0)
    assert [(r.program, r.district_type, r.district) for r in rows] == [
        ("A", "council", "2"), ("A", "assembly", "40"), ("A", "senate", "30"), ("B", "council", "9"), ("B", "council", "10")]


def test_tract_rows_only_when_present():
    assert all(r.district_type != "census_tract" for r in build_map_counts(_entries(12), 10))
    rows = build_map_counts(_entries(12, tract="0077"), 10)
    assert [r.district_type for r in rows] == ["council", "census_tract"]


def test_no_field_named_like_a_name_id_or_point():
    names = {f.name for f in dataclasses.fields(MapCountRow)}
    for bad in ("name", "unit", "id", "client", "master", "address", "lat", "lon", "point"):
        assert not any(bad in n for n in names)


def test_threshold_change_changes_blanking():
    assert _count(build_map_counts(_entries(11), 10)) == 11
    assert _count(build_map_counts(_entries(11), 11)) is None
    assert _count(build_map_counts(_entries(5), 4)) == 5
