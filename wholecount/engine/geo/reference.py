"""The fallback reference (P-GEO-3, P-GEO-4, B-17, C-24): a CSV of real NYC address points the operator installs.

Lookup is a dict hit on the address key and nothing else. Near matches are suggestions for a person and never place a row.
"""
import csv
import difflib
import hashlib
import io
import pathlib
import re
from dataclasses import dataclass

from wholecount.engine.addresskey import TYPES, address_key, normalize_house, normalize_street
from wholecount.engine.geo import places, zips
from wholecount.engine.geo.offset import haversine_ft
from wholecount.engine.geo.types import GeoResult, not_placed
from wholecount.settings import loader

SAMPLE_MARKER = "#wholecount-sample"
# SHA-256 of wholecount/sample_data/sample_reference.csv. tools/make_example_data.py prints it, and --check fails while they differ.
SAMPLE_REFERENCE_HASHES = frozenset({
    "288d4a88e54128b586191625da07fc4af2a46fedfcec02a1e5acfef8478931e7",
})
HEADERS = {
    "house_number": ("house_number", "hnum", "housenum"),
    "street": ("street", "street_name", "stname"),
    "zip": ("zip", "zipcode"),
    "borough": ("borough", "boro"),
    "latitude": ("latitude",),
    "longitude": ("longitude",),
}
_FULL_TYPES = frozenset(TYPES.values())


class ReferenceError(Exception):
    """The file isn't a reference: a column is missing. The message names the column, never a value."""


@dataclass(frozen=True)
class _Point:
    house_number: str
    street: str
    zip5: str
    borough: str
    latitude: float
    longitude: float


@dataclass(frozen=True)
class Suggestion:
    """A near match for Fix problems. Data for a person, never coordinates or districts (P-GEO-3)."""
    house_number: str
    street: str
    zip5: str
    borough: str
    ratio: float


def _borough(text):
    if not text:
        return ""
    return places.borough_of(text) or ""


def _location_part(borough_or_zip):
    v = (borough_or_zip or "").strip()
    if re.fullmatch(r"\d{5}", v):
        return "zip", v
    return "borough", _borough(v)


def _house_street_key(house, street):
    return f"{normalize_house(house)}|{normalize_street(street)}"


def _alpha(street):
    return " ".join(t for t in normalize_street(street).split() if t.isalpha() and t not in _FULL_TYPES)


def _numbers(street):
    return re.findall(r"\d+", normalize_street(street))


def _type(street):
    toks = normalize_street(street).split()
    return toks[-1] if toks and toks[-1] in _FULL_TYPES else ""


class ReferenceBackend:
    def __init__(self, points, is_sample=False, ambiguous_ft=None, suggest_ratio=None):
        s = loader.load("geo")
        self.ambiguous_ft = float(s["reference_ambiguous_ft"] if ambiguous_ft is None else ambiguous_ft)
        self.suggest_ratio = float(s["suggest_ratio"] if suggest_ratio is None else suggest_ratio)
        self.is_sample = is_sample
        self.name = "reference_sample" if is_sample else "reference"
        self.rows = len(points)
        self.release = str(self.rows)
        self._by_zip, self._by_borough, self._by_house = {}, {}, {}
        for p in points:
            self._by_zip.setdefault(address_key(p.house_number, p.street, p.zip5), []).append(p)
            if p.borough:
                self._by_borough.setdefault((_house_street_key(p.house_number, p.street), p.borough), []).append(p)
            self._by_house.setdefault(normalize_house(p.house_number), []).append(p)

    @classmethod
    def from_text(cls, text, is_sample=None):
        lines = text.splitlines()
        marked = bool(lines) and lines[0].strip() == SAMPLE_MARKER
        body = "\n".join(l for l in lines if not l.startswith("#"))
        reader = csv.reader(io.StringIO(body))
        header = [h.strip().lower() for h in next(reader, [])]
        cols = {}
        for name, aliases in HEADERS.items():
            idx = next((header.index(a) for a in aliases if a in header), None)
            if idx is not None:
                cols[name] = idx
        for need in ("house_number", "street", "latitude", "longitude"):
            if need not in cols:
                raise ReferenceError(f"missing column {need}")
        if "zip" not in cols and "borough" not in cols:
            raise ReferenceError("missing column zip or borough")
        points = []
        for row in reader:
            if not any(c.strip() for c in row):
                continue

            def cell(name):
                i = cols.get(name)
                return row[i].strip() if i is not None and i < len(row) else ""
            try:
                lat, lon = float(cell("latitude")), float(cell("longitude"))
            except ValueError:
                continue
            zip5 = cell("zip")[:5]
            borough = _borough(cell("borough")) or (zips.borough_for_zip(zip5) or "")
            points.append(_Point(cell("house_number"), cell("street"), zip5, borough, lat, lon))
        if is_sample is None:
            is_sample = marked
        return cls(points, is_sample=is_sample)

    @classmethod
    def from_path(cls, path):
        data = pathlib.Path(path).read_bytes()
        text = data.decode("utf-8-sig")
        sample = text.splitlines()[:1] == [SAMPLE_MARKER] or hashlib.sha256(data).hexdigest() in SAMPLE_REFERENCE_HASHES
        return cls.from_text(text, is_sample=sample)

    def _candidates(self, house_number, street, borough_or_zip):
        kind, value = _location_part(borough_or_zip)
        if kind == "zip":
            return self._by_zip.get(address_key(house_number, street, value), [])
        if not value:
            return []
        return self._by_borough.get((_house_street_key(house_number, street), value), [])

    def lookup(self, house_number, street, borough_or_zip):
        hits = self._candidates(house_number, street, borough_or_zip)
        if not hits:
            return not_placed("not_found", self.name)
        first = hits[0]
        if any(haversine_ft(first.latitude, first.longitude, h.latitude, h.longitude) > self.ambiguous_ft for h in hits[1:]):
            return not_placed("reference_ambiguous", self.name)
        return GeoResult("high", "matched_building", first.latitude, first.longitude, first.borough or None,
                         first.zip5 or None, None, None, self.name, None)

    def suggest(self, house_number, street, borough_or_zip, limit=3):
        """Up to three near matches. The house number, every number in the street and the street type must be equal."""
        kind, value = _location_part(borough_or_zip)
        want_alpha, want_nums, want_type = _alpha(street), _numbers(street), _type(street)
        exact = {id(p) for p in self._candidates(house_number, street, borough_or_zip)}
        scored = []
        for p in self._by_house.get(normalize_house(house_number), []):
            if id(p) in exact or (kind == "zip" and p.zip5 != value) or (kind == "borough" and value and p.borough != value):
                continue
            if _numbers(p.street) != want_nums or _type(p.street) != want_type:
                continue
            ratio = difflib.SequenceMatcher(None, want_alpha, _alpha(p.street)).ratio()
            if ratio >= self.suggest_ratio and normalize_street(p.street) != normalize_street(street):
                scored.append(Suggestion(p.house_number, p.street, p.zip5, p.borough, round(ratio, 3)))
        scored.sort(key=lambda s: (-s.ratio, s.street, s.zip5))
        out, seen = [], set()
        for s in scored:
            k = (normalize_street(s.street), s.zip5)
            if k not in seen:
                seen.add(k)
                out.append(s)
        return tuple(out[:limit])


def load_folder(directory):
    """(backend or None, reason). The one .csv in the reference folder. Two or more is several_reference_files and no backend."""
    d = pathlib.Path(directory)
    if not d.is_dir():
        return None, "none"
    files = sorted(p for p in d.iterdir() if p.is_file() and p.suffix.lower() == ".csv")
    if not files:
        return None, "none"
    if len(files) > 1:
        return None, "several_reference_files"
    try:
        backend = ReferenceBackend.from_path(files[0])
    except (ReferenceError, UnicodeDecodeError, OSError):
        return None, "reference_unreadable"
    return backend, "sample" if backend.is_sample else "real"
