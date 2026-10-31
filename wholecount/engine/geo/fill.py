"""Fill proposals for "Look up all N" (P-GEO-9, B-34, B-31). Exact lookups on the row's own house number and street only.

Nothing changes until a person accepts. Evidence is for the screen only and never reaches a log or saved progress; basis holds
a short hash of the value instead (H9).
"""
import hashlib
import re
from dataclasses import dataclass

from wholecount.engine.addresskey import split_house_street
from wholecount.engine.geo import places, zips
from wholecount.engine.geo.places import BOROUGHS


@dataclass(frozen=True)
class FillEvidence:
    house_number: str
    street: str
    came_from_kind: str       # borough or zip
    came_from: str


@dataclass(frozen=True)
class FillProposal:
    field: str
    value: str
    rule_id: str
    source: str               # geosupport or reference
    source_detail: str        # the Geosupport release, or the reference row count
    evidence: FillEvidence
    basis: str


def _valid_zip(z):
    return bool(re.fullmatch(r"\d{5}", z or ""))


def _source(backend, reference):
    """The exact source to ask: Geosupport when it is in use, else a reference."""
    for b in (backend, reference):
        if b is not None and getattr(b, "name", "") in ("geosupport", "reference", "reference_sample"):
            return b
    return None


def _proposal(fld, value, rule_id, src, house, street, kind, came_from):
    source = "geosupport" if src.name == "geosupport" else "reference"
    basis = f"{rule_id}|{source}|{hashlib.sha256(value.encode('utf-8')).hexdigest()[:8]}"
    return FillProposal(fld, value, rule_id, source, src.release, FillEvidence(house, street, kind, came_from), basis)


def _high(src, house, street, where):
    try:
        r = src.lookup(house, street, where)
    except Exception:
        return None
    return r if r.confidence == "high" else None


def propose_fills(row, backend, reference=None):
    """FILL-ZIP-1, FILL-CITY-1, FILL-CITY-2, FILL-STATE-1. Only exact High answers, only with a house number, and nothing
    when two answers come back."""
    src = _source(backend, reference)
    if src is None:
        return []
    house, street = split_house_street(row.value("Address_1"))
    if not house or not street:
        return []
    city, z, state = row.value("City"), row.value("Zip"), row.value("State")
    borough = places.borough_of(city) if city else None
    zip_ok = _valid_zip(z)
    if zip_ok and not zips.is_nyc_zip(z):
        return []
    typed_state = places.state_code(state) if state else None
    out = []

    if not z and borough:                                                        # FILL-ZIP-1
        r = _high(src, house, street, borough)
        if r is not None and r.zip5:
            out.append(_proposal("Zip", r.zip5, "FILL-ZIP-1", src, house, street, "borough", borough))

    if city and borough is None and zip_ok:                                      # FILL-CITY-1
        r = _high(src, house, street, z)
        b = zips.borough_for_zip(z)
        if r is not None and b and (r.borough in (None, b)):
            out.append(_proposal("City", b, "FILL-CITY-1", src, house, street, "zip", z))

    if not city and not z:                                                       # FILL-CITY-2
        hits = [b for b in BOROUGHS if _high(src, house, street, b) is not None]
        if len(hits) == 1:
            out.append(_proposal("City", hits[0], "FILL-CITY-2", src, house, street, "borough", hits[0]))

    if (not state or typed_state is None) and not zip_ok and borough:            # FILL-STATE-1
        if _high(src, house, street, borough) is not None:
            out.append(_proposal("State", "NY", "FILL-STATE-1", src, house, street, "borough", borough))
    return out
