"""Choosing how to place addresses (P-GEO-1 to P-GEO-4): Geosupport, then a real reference, then nothing.

The fake backend is never chosen here. A sample reference is refused for the operator's own files and allowed only for
"Try example data".
"""
import pathlib
from dataclasses import dataclass, field
from importlib import resources

from wholecount.engine.geo.geosupport import GeosupportBackend, release_quarter
from wholecount.engine.geo.reference import load_folder
from wholecount.engine.geo.types import not_placed
from wholecount.settings import loader


class NoBackend:
    name = "none"
    release = ""

    def lookup(self, house_number, street, borough_or_zip):
        return not_placed("no_backend", "none")


@dataclass(frozen=True)
class GeoOptions:
    """The run's optional Geosupport fields. "census_tract" is the only one used now."""
    extra_fields: frozenset = field(default_factory=frozenset)

    @classmethod
    def from_settings(cls):
        return cls(frozenset(loader.load("geo")["extra_fields"]))


def select_backend(geosupport, reference, allow_sample=False):
    """Geosupport, then a real reference (or a sample one when allow_sample), then NoBackend. Never the fake."""
    if geosupport is not None and getattr(geosupport, "name", "") == "geosupport":
        return geosupport
    if reference is not None and getattr(reference, "name", "") in ("reference", "reference_sample"):
        if not reference.is_sample or allow_sample:
            return reference
    return NoBackend()


def release_stale(release, today, quarters=None):
    """True when the release is more than `quarters` quarters behind today. 'unknown' and '' are never stale."""
    rq = release_quarter(release)
    if rq is None:
        return False
    if quarters is None:
        quarters = int(loader.load("geo")["release_stale_quarters"])
    ry, rqn = rq
    behind = (today.year * 4 + (today.month - 1) // 3) - (ry * 4 + rqn - 1)
    return behind > quarters


def district_paths(directory=None):
    if directory is None:
        directory = resources.files("wholecount.engine.geo").joinpath("data/districts")
    d = pathlib.Path(str(directory))
    if not d.is_dir():
        return ()
    return tuple(sorted(p for p in d.iterdir() if p.suffix.lower() in (".geojson", ".json")))


@dataclass(frozen=True)
class GeoPreflight:
    backend: object
    release: str
    release_stale: bool
    reference_kind: str          # real, sample, none, several_reference_files or reference_unreadable
    reference_rows: int
    district_files: int
    can_place: bool
    geosupport_reason: str = ""

    @property
    def backend_name(self):
        return self.backend.name


def preflight(environ, data_dir, today, discover=None, district_dir=None):
    """What a batch of the operator's own files would use. M08 wraps it and M10 shows it. today is always passed in (H3)."""
    discover = discover or GeosupportBackend.discover
    geo, geo_reason = discover(environ)
    reference, kind = load_folder(pathlib.Path(data_dir) / "reference")
    backend = select_backend(geo, reference, allow_sample=False)
    release = backend.release if backend.name == "geosupport" else ""
    return GeoPreflight(
        backend=backend,
        release=release,
        release_stale=release_stale(release, today) if release else False,
        reference_kind=kind,
        reference_rows=reference.rows if reference is not None else 0,
        district_files=len(district_paths(district_dir)),
        can_place=backend.name != "none",
        geosupport_reason=geo_reason,
    )
