"""ZIP (P-STD-3, B-03, B-26). Five ASCII digits only. The borough comes from the explicit NYC list, never from ranges."""
import re
import unicodedata
from dataclasses import dataclass, field

from wholecount.engine.geo.zips import is_nyc_zip

_FIVE = re.compile(r"[0-9]{5}")
_PLUS4 = re.compile(r"([0-9]{5})(?:-[0-9]{4}|[0-9]{4})")


@dataclass(frozen=True)
class ZipResult:
    value: str
    reason: str | None = None
    notes: tuple = ()
    suggestions: tuple = ()
    outside_nyc: bool = False

    @property
    def valid(self):
        return self.reason is None and bool(self.value)

    @property
    def nyc(self):
        return self.valid and not self.outside_nyc


def standardize_zip(text, kind=None):
    t = text.strip()
    if not t:
        return ZipResult("")
    if kind == "number" and re.fullmatch(r"[0-9]+", t):
        if len(t) in (3, 4):
            return _finish(t.zfill(5), ("zip_zero_restored",))
        if len(t) != 5:
            return ZipResult(t, "zip_not_valid")
    if any(ch.isdigit() and ch not in "0123456789" for ch in t):
        nfkc = unicodedata.normalize("NFKC", t)
        sugg = (nfkc,) if _FIVE.fullmatch(nfkc) else ()
        return ZipResult(t, "zip_unicode_digits", suggestions=sugg)
    if _FIVE.fullmatch(t):
        return _finish(t, ())
    m = _PLUS4.fullmatch(t)
    if m and kind != "number":
        return _finish(m.group(1), ("zip_plus4_reduced",))
    return ZipResult(t, "zip_not_valid")


def _finish(z, notes):
    if is_nyc_zip(z):
        return ZipResult(z, None, notes)
    return ZipResult(z, None, notes + ("zip_outside_nyc",), outside_nyc=True)
