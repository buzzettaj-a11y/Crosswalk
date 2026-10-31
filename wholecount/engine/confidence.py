"""Confidence (SPEC 7.4, H15): batch, match and location. Thresholds live in settings/confidence.toml.

Percentages are compared by cross-multiplying integers, so 95 is exact. There are no percentages in the headline.
"""
from dataclasses import dataclass

from wholecount.settings.loader import load

LEVELS = ("low", "medium", "high")


@dataclass(frozen=True)
class BatchConfidence:
    level: str | None                     # low, medium, high, or None when nothing was received
    parts: tuple                          # (code, params) for each reason the level isn't High
    measures: tuple                       # (name, numerator, denominator); placed may be (name, None, None)
    calibration: object = None            # M13


def _at_least(num, den, pct):
    return num * 100 >= pct * den


def batch_confidence(counts, settings=None):
    """CONF-1 to CONF-3."""
    s = (settings or load("confidence"))["batch"]
    if counts.received == 0:
        return BatchConfidence(None, (), ())
    locs = counts.locations
    looked = locs.looked_up
    measures = (("counted", counts.counted, counts.received), ("open_pairs", counts.open_pairs, None),
                ("placed", locs.high, looked) if looked else ("placed", None, None))
    low_parts, other_parts = [], []

    def add(part, under_low):
        (low_parts if under_low else other_parts).append(part)

    counted_low = not _at_least(counts.counted, counts.received, s["low_pct"])
    if not _at_least(counts.counted, counts.received, s["high_counted_pct"]):
        add(("counted_short", {"counted": counts.counted, "received": counts.received}), counted_low)
    if counts.open_pairs > s["high_open_pairs"]:
        add(("pairs_open", {"count": counts.open_pairs}), False)
    placed_low = False
    if not looked:
        code = "placed_unavailable_no_geocoder" if locs.no_geocoder else "placed_unavailable_none_looked_up"
        add((code, {}), False)
    else:
        placed_low = not _at_least(locs.high, looked, s["low_pct"])
        if not _at_least(locs.high, looked, s["high_placed_pct"]):
            add(("placed_short", {"high": locs.high, "looked_up": looked}), placed_low)
    parts = tuple(low_parts + other_parts)
    if counted_low or placed_low:
        level = "low"
    elif parts:
        level = "medium"
    else:
        level = "high"
    return BatchConfidence(level, parts, measures)


def master_match_confidence(master_id, identity):
    """CONF-5: certain, likely, possible (the stronger open band) or single."""
    keys = set(identity.groups.get(master_id, ()))
    bands = {p.band for p in identity.proposals if keys & set(p.pair)}
    if "likely" in bands:
        return "likely"
    if "possible" in bands:
        return "possible"
    rows = sum(1 for m in identity.master_of_record.values() if m == master_id)
    return "certain" if len(keys) > 1 or rows > 1 else "single"


def master_match_confidences(identity):
    """CONF-5 for every master ID in one pass: {master ID: certain, likely, possible or single}. Equal to calling
    master_match_confidence for each, without scanning every proposal and record once per person."""
    master_of_key = {k: m for m, ks in identity.groups.items() for k in ks}
    bands = {}
    for p in identity.proposals:
        for k in p.pair:
            m = master_of_key.get(k)
            if m is not None:
                bands.setdefault(m, set()).add(p.band)
    rows = {}
    for m in identity.master_of_record.values():
        rows[m] = rows.get(m, 0) + 1
    out = {}
    for m in set(identity.groups) | set(rows):
        b = bands.get(m, ())
        if "likely" in b:
            out[m] = "likely"
        elif "possible" in b:
            out[m] = "possible"
        else:
            out[m] = "certain" if len(set(identity.groups.get(m, ()))) > 1 or rows.get(m, 0) > 1 else "single"
    return out


def location_confidence(outcome):
    """CONF-6: (High, Low or Not placed, reason code) for a counted row."""
    loc = outcome.location
    if loc is None:
        return None
    if loc.kind == "mapped":
        return (loc.confidence, None)
    return ("not_placed", loc.reason)
