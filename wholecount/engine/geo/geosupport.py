"""NYC Geosupport Desktop Edition through python-geosupport (P-GEO-1). Imported lazily, only inside discover().

Lookup is Function 1B. GRC 00 is High, GRC 01 is Low, anything else or a GeosupportError is Not placed. Districts come from the
result and never fall back to polygons for a Geosupport row. place_rows drops the census tract unless the run asks for it.
"""
import ntpath
import re
import sys

from wholecount.engine.geo.types import BOROUGH_CODES, Districts, GeoResult, not_placed
from wholecount.guard.config import discover_geosupport_dirs

_RELEASE = re.compile(r"(?<![0-9A-Za-z])(\d{2})([A-Da-d])(?![0-9A-Za-z])")
SMOKE_TEST = {"house_number": "125", "street_name": "Worth St", "borough_code": "MN"}
_BOROUGH_NAMES = {"manhattan": "New York", "new york": "New York", "bronx": "Bronx", "brooklyn": "Brooklyn", "queens": "Queens",
                  "staten island": "Staten Island"}


def release_from_path(path):
    """'25C' from an install folder named like 'Geosupport Desktop Edition 25C', else 'unknown'."""
    for part in reversed(re.split(r"[\\/]", path or "")):
        m = _RELEASE.search(part.replace("_", " "))
        if m:
            return f"{m.group(1)}{m.group(2).upper()}"
    return "unknown"


def release_quarter(release):
    """(year, quarter) for '25C', or None for 'unknown' or ''."""
    m = re.fullmatch(r"(\d{2})([A-D])", release or "")
    if not m:
        return None
    return 2000 + int(m.group(1)), "ABCD".index(m.group(2)) + 1


def extract_fields(result):
    """Tolerant key matching across Geosupport releases (ported from the old adapter's rule, written fresh)."""
    out = {"lat": "", "lon": "", "borough": "", "zip": "", "grc": "", "senate": "", "assembly": "", "council": "", "tract": "",
           "message": ""}
    for k, v in result.items():
        if not isinstance(k, str):
            continue
        kl = k.lower()
        val = "" if v is None else str(v).strip()
        if not val:
            continue
        if not out["lat"] and "latitude" in kl:
            out["lat"] = val
        elif not out["lon"] and "longitude" in kl:
            out["lon"] = val
        elif not out["borough"] and "borough name" in kl and "code" not in kl:
            out["borough"] = val
        elif not out["zip"] and "zip code" in kl:
            out["zip"] = val
        elif not out["grc"] and ("return code" in kl or kl in ("grc", "grc 1")):
            out["grc"] = val
        elif not out["senate"] and "senat" in kl:
            out["senate"] = val
        elif not out["assembly"] and "assembly" in kl:
            out["assembly"] = val
        elif not out["council"] and "council" in kl:
            out["council"] = val
        elif not out["tract"] and "census tract" in kl and "2020" in kl:
            out["tract"] = val
        elif not out["message"] and kl == "message":
            out["message"] = val
    m = re.match(r"(\d{5})", out["zip"])
    out["zip"] = m.group(1) if m else ""
    out["borough"] = _BOROUGH_NAMES.get(out["borough"].lower(), "")
    return out


def _district(v):
    v = (v or "").strip().lstrip("0")
    return v or None


class GeosupportBackend:
    name = "geosupport"

    def __init__(self, g, error_type, release):
        self._g = g
        self._error = error_type
        self.release = release

    @classmethod
    def discover(cls, environ, exists=None, platform=None):
        """(backend or None, reason). Reasons: ok, not_installed, wrapper_missing, not_usable, smoke_test_failed."""
        import os

        exists = exists or os.path.isdir
        platform = platform or sys.platform
        dirs = discover_geosupport_dirs(environ, exists)
        if not dirs:
            return None, "not_installed"
        install = dirs[0]
        try:
            from geosupport import Geosupport, GeosupportError
        except ImportError:
            return None, "wrapper_missing"
        try:
            g = Geosupport(geosupport_path=install) if platform == "win32" else Geosupport()
        except Exception:
            return None, "not_usable"
        try:
            g.address(**SMOKE_TEST)
        except Exception:
            return None, "smoke_test_failed"
        return cls(g, GeosupportError, release_from_path(install)), "ok"

    def lookup(self, house_number, street, borough_or_zip):
        kwargs = {"house_number": house_number, "street_name": street}
        v = (borough_or_zip or "").strip()
        if re.fullmatch(r"\d{5}", v):
            kwargs["zip_code"] = v
        elif v in BOROUGH_CODES:
            kwargs["borough_code"] = BOROUGH_CODES[v]
        else:
            return not_placed("not_found", self.name)
        try:
            res = self._g.address(**kwargs)
        except self._error:
            return not_placed("not_found", self.name)
        f = extract_fields(res)
        try:
            lat, lon = float(f["lat"]), float(f["lon"])
        except ValueError:
            return not_placed("not_found", self.name)
        grc = f["grc"].zfill(2) if f["grc"] else "00"
        if grc == "00":
            conf, reason = "high", "matched_building"
        elif grc == "01":
            conf = "low"
            reason = "house_out_of_range" if "out of range" in f["message"].lower() else "matched_with_warning"
        else:
            return not_placed("not_found", self.name)
        districts = Districts(_district(f["senate"]), _district(f["assembly"]), _district(f["council"]))
        return GeoResult(conf, reason, lat, lon, f["borough"] or None, f["zip"] or None,
                         districts if districts.any() else None, f["tract"] or None, self.name, grc)
