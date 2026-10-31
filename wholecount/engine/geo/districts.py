"""Districts from the true point (P-GEO-5, B-19, C-10). One loader, one shape, no third-party geometry.

Ring 0 of a polygon is its outer boundary and later rings are holes. Coordinates are GeoJSON order, longitude then latitude.
"""
import json
from dataclasses import dataclass

from wholecount.engine.geo.types import Districts

KINDS = {"senate_district": "senate", "assembly_district": "assembly", "council_district": "council"}


def _on_segment(x, y, x1, y1, x2, y2, eps=1e-12):
    if min(x1, x2) - eps <= x <= max(x1, x2) + eps and min(y1, y2) - eps <= y <= max(y1, y2) + eps:
        return abs((x2 - x1) * (y - y1) - (y2 - y1) * (x - x1)) <= eps * max(1.0, abs(x2 - x1) + abs(y2 - y1))
    return False


def ring_contains(ring, x, y):
    """'boundary', True or False. Ray casting after a boundary check."""
    inside = False
    n = len(ring)
    for i in range(n):
        x1, y1 = ring[i][0], ring[i][1]
        x2, y2 = ring[(i + 1) % n][0], ring[(i + 1) % n][1]
        if _on_segment(x, y, x1, y1, x2, y2):
            return "boundary"
        if (y1 > y) != (y2 > y):
            xi = x1 + (y - y1) * (x2 - x1) / (y2 - y1)
            if x < xi:
                inside = not inside
    return inside


def polygon_contains(rings, x, y):
    """DIST-1, DIST-2: inside ring 0 (its edge counts) and inside no hole (a hole's edge counts as inside the polygon)."""
    if not rings or not ring_contains(rings[0], x, y):
        return False
    for hole in rings[1:]:
        r = ring_contains(hole, x, y)
        if r is True:
            return False
    return True


@dataclass(frozen=True)
class _Feature:
    kind: str
    number: str
    polygons: tuple       # each a tuple of rings
    bbox: tuple           # min_x, min_y, max_x, max_y

    def contains(self, x, y):
        bx0, by0, bx1, by1 = self.bbox
        if not (bx0 <= x <= bx1 and by0 <= y <= by1):
            return False
        return any(polygon_contains(p, x, y) for p in self.polygons)


def _polygons(geometry):
    t = (geometry or {}).get("type")
    if t == "Polygon":
        return (tuple(geometry["coordinates"]),)
    if t == "MultiPolygon":
        return tuple(tuple(p) for p in geometry["coordinates"])
    return ()


def _number_key(n):
    try:
        return (0, int(n), n)
    except ValueError:
        return (1, 0, n)


def _as_number(v):
    if isinstance(v, float) and v.is_integer():
        v = int(v)
    return str(v).strip()


class DistrictIndex:
    def __init__(self, features=(), sources=()):
        self.features = tuple(features)
        self.sources = tuple(sources)

    @classmethod
    def from_files(cls, paths):
        """Any number of GeoJSON files, merged. Properties are any subset of senate_district, assembly_district, council_district."""
        feats, sources = [], []
        for p in paths:
            with open(p, encoding="utf-8") as f:
                data = json.load(f)
            sources.append(str(p))
            for feat in data.get("features", []):
                polys = _polygons(feat.get("geometry"))
                if not polys:
                    continue
                xs = [pt[0] for poly in polys for pt in poly[0]]
                ys = [pt[1] for poly in polys for pt in poly[0]]
                bbox = (min(xs), min(ys), max(xs), max(ys))
                for prop, kind in KINDS.items():
                    v = (feat.get("properties") or {}).get(prop)
                    if v is None or str(v).strip() == "":
                        continue
                    feats.append(_Feature(kind, _as_number(v), polys, bbox))
        return cls(feats, sources)

    @property
    def empty(self):
        return not self.features

    def assign(self, lat, lon):
        """Districts for the TRUE point (DIST-5). The smallest number wins when several of one kind hold it (DIST-2)."""
        found = {}
        for f in self.features:
            if f.contains(lon, lat):
                found.setdefault(f.kind, []).append(f.number)
        pick = {k: min(v, key=_number_key) for k, v in found.items()}
        return Districts(pick.get("senate"), pick.get("assembly"), pick.get("council"))
