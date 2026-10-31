"""Rows for Map_Counts and Map_Points (P-GEO-6, P-GEO-7, 9.1). M09 writes the files; this builds rows and writes nothing.

No row holds a unit, name, address, ID or point from a person. Map_Points holds only program and a moved point.
"""
from dataclasses import dataclass
from typing import Literal

from wholecount.engine.geo.offset import PrivacyOffset
from wholecount.engine.geo.types import Districts
from wholecount.settings import loader

DISTRICT_TYPES = ("council", "assembly", "senate", "census_tract")


@dataclass(frozen=True)
class MapEntry:
    unit: str                 # the master ID, passed by M09. Counted, never written.
    program: str
    districts: Districts
    tract: str | None = None


@dataclass(frozen=True)
class MapCountRow:
    program: str
    district_type: Literal["council", "assembly", "senate", "census_tract"]
    district: str
    count: int | None         # None means 1 to small_cell_max, shown as "fewer than 11"


@dataclass(frozen=True)
class MapPointEntry:
    program: str
    address_key: str
    latitude: float           # the TRUE point
    longitude: float


@dataclass(frozen=True)
class MapPoint:
    program: str
    latitude: float           # the moved point
    longitude: float


def small_cell_max():
    return int(loader.load("privacy")["small_cell_max"])


def _district_sort(d):
    try:
        return (0, int(d), d)
    except ValueError:
        return (1, 0, d)


def build_map_counts(entries, small_cell_max):
    """MAP-1, MAP-2. Distinct units per (program, district type, district), with counts 1 to small_cell_max blanked."""
    cells = {}
    for e in entries:
        values = {"council": e.districts.council if e.districts else None,
                  "assembly": e.districts.assembly if e.districts else None,
                  "senate": e.districts.senate if e.districts else None,
                  "census_tract": e.tract}
        for kind, d in values.items():
            if d is None or str(d).strip() == "":
                continue
            cells.setdefault((e.program, kind, str(d)), set()).add(e.unit)
    rows = []
    for (program, kind, d), units in cells.items():
        n = len(units)
        rows.append(MapCountRow(program, kind, d, None if 1 <= n <= small_cell_max else n))
    rows.sort(key=lambda r: (r.program, DISTRICT_TYPES.index(r.district_type), _district_sort(r.district)))
    return rows


def build_map_points(entries, mac, offset=None):
    """MAP-3. One moved point per entry, from its building's address key. Sorted by program and point, never by person."""
    offset = offset or PrivacyOffset.from_settings(mac)
    out = []
    for e in entries:
        lat, lon = offset.apply(e.address_key, e.latitude, e.longitude)
        out.append(MapPoint(e.program, lat, lon))
    out.sort(key=lambda p: (p.program, p.latitude, p.longitude))
    return out
