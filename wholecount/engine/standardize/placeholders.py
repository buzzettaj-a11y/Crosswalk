"""Placeholders by field class (P-STD-2, B-01, B-25). A marker matches the whole cell only."""
from dataclasses import dataclass
from functools import lru_cache

from wholecount.settings.loader import load

NAME_FIELDS = ("First_Name", "Middle_Initial", "Last_Name")
IDENTIFIER_FIELDS = ("Client_ID",)
ADDRESS_FIELDS = ("Address_1", "Address_2", "City", "State", "Zip")
# In the name fields only these blank a value. The name_kept words are kept and flagged (the name rule wins over none and nil).
NAME_BLANKING = frozenset({"null", "n/a", "#n/a", "(null)"})


@lru_cache(maxsize=1)
def _lists():
    p = load("placeholders")
    return {"every": frozenset(p["every_field"]["words"]) | frozenset(p["every_field"]["marks"]),
            "marks": frozenset(p["every_field"]["marks"]),
            "id_address": frozenset(p["identifier_and_address"]["words"]),
            "name_kept": frozenset(p["name_kept"]["words"]),
            "housing": frozenset(p["housing"]["words"])}


def _forms(text):
    t = " ".join(text.lower().split())
    out = {t}
    if t and not t[-1].isalnum() and len(t) > 1:
        out.add(t[:-1].rstrip())
    return out


@dataclass(frozen=True)
class Marker:
    kind: str     # every_field, identifier_and_address, name_kept or housing


def marker(field, text):
    """The kind of placeholder the whole cell is, for this field, or None."""
    if not text.strip():
        return None
    lists, forms = _lists(), _forms(text)
    if field in ("First_Name", "Last_Name"):
        if forms & (NAME_BLANKING | lists["marks"]):
            return Marker("every_field")
        if forms & lists["name_kept"]:
            return Marker("name_kept")
        return None
    if field in ADDRESS_FIELDS and forms & lists["housing"]:
        return Marker("housing")
    if forms & lists["every"]:
        return Marker("every_field")
    if (field in IDENTIFIER_FIELDS or field in ADDRESS_FIELDS) and forms & lists["id_address"]:
        return Marker("identifier_and_address")
    return None


def is_blank(field, text):
    """True for an empty cell or a marker that blanks this field. What fill_default receives, bound with functools.partial."""
    if not text.strip():
        return True
    m = marker(field, text)
    return m is not None and m.kind != "name_kept"
