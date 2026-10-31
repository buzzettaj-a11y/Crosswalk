"""The placing step (P-GEO-1 to P-GEO-8, P-VAL-1). A pure function of each row: one row never changes another (B-45, H13).

Only rows M04 marks to_place are looked up, counted or not yet counted, so a later decision needs no new lookup. Coordinates
in the result are the TRUE point, in memory only.
"""
import dataclasses
from dataclasses import dataclass

from wholecount.engine.addresskey import address_key, split_house_street
from wholecount.engine.geo import places, zips
from wholecount.engine.geo.types import AddressQuery, LocationOutcome, not_placed
from wholecount.engine.progress import ProgressMessage, Step, Unit
from wholecount.engine.standardize.model import location_for
from wholecount.settings import loader


def to_query(row):
    """The one adapter from M04's StdRow: house number and street from Address_1 (its unit already moved out), then the
    ZIP, or the borough when the ZIP is blank."""
    house, street = split_house_street(row.value("Address_1"))
    z = row.value("Zip")
    where = z if len(z) == 5 and z.isdigit() else (places.borough_of(row.value("City")) or "")
    return AddressQuery(house, street, where)


def building_key(query, result, typed_zip=""):
    """OFF-1: the address key of the building, with the ZIP the backend returned, else the typed ZIP, else '-'."""
    z = result.zip5 or (typed_zip if len(typed_zip) == 5 and typed_zip.isdigit() else "")
    return address_key(query.house_number, query.street, z)


@dataclass(frozen=True)
class GeoAuditEntry:
    """IDs and counts only (H8, A-14). Never the secret, an offset or a point."""
    rule_id: str
    event: str
    backend: str
    release: str
    practice: bool
    looked_up: int
    placed: int


@dataclass(frozen=True)
class PlacementResult:
    results: dict             # record key -> GeoResult
    building_keys: dict       # record key -> address key of the building, for placed rows (OFF-1)
    practice: bool            # the backend is a sample reference: no Map_Counts, Map_Points or district columns (M09)
    backend: str
    release: str
    audit: tuple


def _lookup(backend, query):
    if not query.house_number or not query.street or not query.borough_or_zip:
        return not_placed("not_found", backend.name)
    try:
        return backend.lookup(query.house_number, query.street, query.borough_or_zip)
    except Exception:
        # A failing lookup is that row's Not placed. It never stops the run or touches another row (B-45).
        return not_placed("not_found", backend.name)


def place_rows(rows, backend, districts, options, sink=None):
    every = int(loader.load("geo")["progress_every_rows"])
    todo = [r for r in rows if not r.set_aside_reason and location_for(r).kind == "to_place"]
    results, keys = {}, {}
    if sink is not None:
        sink.begin(Step.PLACING_ADDRESSES, len(todo), Unit.ADDRESSES)
    for i, row in enumerate(todo, start=1):
        q = to_query(row)
        res = _lookup(backend, q)
        if res.placed:
            if res.source in ("reference", "reference_sample") and districts is not None and not districts.empty:
                res = dataclasses.replace(res, districts=districts.assign(res.latitude, res.longitude))
            if "census_tract" not in options.extra_fields:
                res = dataclasses.replace(res, census_tract=None)
            keys[row.record_key] = building_key(q, res, row.value("Zip"))
        results[row.record_key] = res
        if sink is not None and (i % every == 0 or i == len(todo)):
            sink.advance(i, ProgressMessage("progress.addresses_looked_up", {"done": i, "total": len(todo)}))
    placed = sum(1 for r in results.values() if r.placed)
    if sink is not None:
        sink.end(ProgressMessage("progress.found.placing_addresses", {"placed": placed, "looked_up": len(todo)}))
    practice = backend.name == "reference_sample"
    audit = (
        GeoAuditEntry("P-GEO-1", "addresses_placed", backend.name, backend.release, practice, len(todo), placed),
        GeoAuditEntry("P-GEO-7", "privacy_offset_applied", backend.name, backend.release, practice, len(todo), placed),
    )
    return PlacementResult(results, keys, practice, backend.name, backend.release, audit)


def outcome_for(location, result, filled=False):
    """M04's LocationStatus and a GeoResult -> the P-VAL-1 location status. LOC-1 to LOC-4."""
    filled = bool(filled or location.filled)
    if location.kind == "not_mapped":
        return LocationOutcome("not_mapped", None, location.reason, filled)                    # LOC-1
    if result is None or result.reason == "no_backend":
        return LocationOutcome("not_mapped", None, "no_geocoder", filled)                      # LOC-2
    if not result.placed:
        return LocationOutcome("not_mapped", None, "not_found", filled)                        # LOC-3
    return LocationOutcome("mapped", result.confidence, None, filled)                          # LOC-4
