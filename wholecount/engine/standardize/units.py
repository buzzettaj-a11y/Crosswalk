"""A unit in both address lines (P-STD-8, proof sheet 11)."""
import re
from dataclasses import dataclass

from wholecount.engine.prepare.address import _LONE_SEGMENT_UNIT, _take_units, address_words, split_trailing_unit


@dataclass(frozen=True)
class UnitResult:
    address_1: str
    address_2: str
    reason: str | None = None
    note: str | None = None


def unit_key(text, words=None):
    """A unit's comparable core: unit words, #, punctuation and spaces dropped. Apt 2A, #2A and 2A all give 2a."""
    words = words or address_words()
    v = text.lower()
    names = "|".join(sorted(words["unit_words"] | words["standalone_units"], key=len, reverse=True))
    v = re.sub(r"\b(?:" + names + r")\b\.?", " ", v)
    return re.sub(r"[^a-z0-9]", "", v)


def is_unit(text, words=None):
    words = words or address_words()
    t = text.strip()
    if not t:
        return False
    if _LONE_SEGMENT_UNIT.fullmatch(t):
        return True
    units, rest = _take_units(t, words, True)
    return bool(units) and not rest.strip(" ,")


def reconcile_units(address_1, address_2, words=None):
    words = words or address_words()
    street, unit = split_trailing_unit(address_1, words)
    if unit is None:
        return UnitResult(address_1, address_2)
    if not address_2.strip():
        return UnitResult(street, unit, note="unit_moved")
    if is_unit(address_2, words):
        if unit_key(unit, words) == unit_key(address_2, words):
            return UnitResult(street, address_2, note="unit_deduplicated")
        return UnitResult(address_1, address_2, reason="units_differ")
    return UnitResult(address_1, address_2, reason="address_extra_text")
