"""P-PREP-5: a calculated ZIP column. Exact lookups only, and a value that isn't a valid NYC ZIP is never written (B-06)."""
import re
from typing import Protocol

from wholecount.engine.geo.zips import is_nyc_zip

_FIVE = re.compile(r"\d{5}")
_PLUS4 = re.compile(r"(\d{5})-?\d{4}")


class ZipResolver(Protocol):
    def zip_for(self, street, borough_or_city):
        """The ZIP an address points to, from an exact match only, or None. M05 supplies Geosupport and the reference."""


def valid_existing(value):
    """The five-digit NYC ZIP a cell already holds, or None. ZIP+4 is reduced to five. Nothing else is kept."""
    v = value.strip()
    if not v.isascii():
        return None
    m = _FIVE.fullmatch(v) or _PLUS4.fullmatch(v)
    if not m:
        return None
    z = m.group(1) if m.re is _PLUS4 else m.group(0)
    return z if is_nyc_zip(z) else None


def calculate(street, city, existing, mode, resolver):
    """(zip or "", note reason ID) for one row."""
    if mode == "blanks" and existing is not None:
        kept = valid_existing(existing)
        if kept:
            return kept, "zip_kept"
    if not street.strip():
        return "", "no_street"
    if resolver is None:
        return "", "no_lookup_available"
    z = resolver.zip_for(street.strip(), city.strip())
    if z and _FIVE.fullmatch(z) and is_nyc_zip(z):
        return z, "zip_found"
    return "", "zip_not_worked_out"
