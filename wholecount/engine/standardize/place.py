"""City and state (P-STD-4, P-STD-5), the street line's own city, state and ZIP (B-27), and a place left in the street (B-28).

A typed city is never overwritten by the ZIP's borough. A blank city or state is filled only from an NYC ZIP, and the fill is
recorded. Nothing here is fuzzy.
"""
import re
from dataclasses import dataclass, field

from wholecount.engine.geo import places
from wholecount.engine.geo.zips import borough_for_zip
from wholecount.engine.prepare.address import address_words


@dataclass
class PlaceResult:
    city: str = ""
    state: str = ""
    reasons: list = field(default_factory=list)      # (reason ID, field)
    notes: list = field(default_factory=list)
    fills: list = field(default_factory=list)        # (field, kind)
    suggestions: dict = field(default_factory=dict)  # field -> tuple
    outside_nyc: bool = False


def standardize_city_state(city, state, zip_result):
    """zip_result is a ZipResult. Returns a PlaceResult with the city and state values to write."""
    r = PlaceResult(city=city, state=state)
    z = borough_for_zip(zip_result.value) if zip_result.nyc else None
    outside_zip = zip_result.valid and zip_result.outside_nyc
    code = places.state_code(state) if state.strip() else None
    other_state = code is not None and code != "NY"

    # State first, because the city rules ask whether another state was typed.
    if not state.strip():
        if z:
            r.state = "NY"
            r.notes.append(("state_filled_from_zip", "State"))
            r.fills.append(("State", "zip"))
        elif outside_zip:
            r.reasons.append(("state_not_recognized", "State"))
        else:
            r.reasons.append(("address_incomplete", "State"))
    elif code == "NY":
        r.state = "NY"
        if state != "NY":
            r.notes.append(("state_standardized", "State"))
    elif other_state:
        if z:
            r.reasons.append(("state_zip_disagree", "State"))
            r.suggestions["State"] = ("NY",)
        else:
            r.state = code
            if state != code:
                r.notes.append(("state_standardized", "State"))
            r.outside_nyc = True
            r.notes.append(("state_outside_nyc", "State"))
    else:
        r.reasons.append(("state_not_recognized", "State"))

    kind, borough = places.city_kind(city) if city.strip() else (None, None)
    if not city.strip():
        if z:
            r.city = z
            r.notes.append(("city_filled_from_zip", "City"))
            r.fills.append(("City", "zip"))
        else:
            r.reasons.append(("address_part_missing", "City"))
    elif kind is not None:
        if z:
            if borough == z or places.allowed_pair(borough, zip_result.value):
                _fold(r, city, borough)
            else:
                r.reasons.append(("city_zip_disagree", "City"))
                r.suggestions["City"] = (z,)
        elif outside_zip:
            if kind == "alias":
                r.reasons.append(("city_zip_disagree", "City"))
        elif not other_state:
            _fold(r, city, borough)
    else:
        if z:
            r.reasons.append(("city_not_recognized", "City"))
            r.suggestions["City"] = (z,)
        elif not (outside_zip or other_state):
            r.reasons.append(("city_not_recognized", "City"))
    return r


def _fold(r, city, borough):
    r.city = borough
    if city != borough:
        r.notes.append(("city_standardized", "City"))


def text_disagreements(text, std_city, std_state, std_zip):
    """[(field, the text's value)] where the street line's own city, state or ZIP differs from its column after standardizing (B-27)."""
    out = []
    if text.city.strip() and std_city.strip():
        a = places.borough_of(text.city) or text.city.strip()
        b = places.borough_of(std_city) or std_city.strip()
        if a.lower() != b.lower():
            out.append(("City", text.city))
    if text.state.strip() and std_state.strip():
        a = places.state_code(text.state) or text.state.strip().upper()
        b = places.state_code(std_state) or std_state.strip().upper()
        if a != b:
            out.append(("State", text.state))
    if text.zip.strip() and std_zip.strip() and text.zip.strip()[:5] != std_zip.strip()[:5]:
        out.append(("Zip", text.zip))
    return out


def move_place(address_1):
    """(street, place) when Address_1 ends in 1 to 3 words that are a listed neighborhood or alias, and what's left starts with a
    house number and ends in a street-type word. Otherwise (address_1, "") (B-28). The place never sets City."""
    words = address_words()
    tokens = address_1.strip().split()
    for n in (3, 2, 1):
        if len(tokens) <= n:
            continue
        tail = " ".join(tokens[-n:]).strip(",")
        if places.city_kind(tail)[0] is None:
            continue
        head = [t for t in tokens[:-n]]
        if head:
            head[-1] = head[-1].rstrip(",")
        last = head[-1].lower().rstrip(".") if head else ""
        if head and re.match(r"\d", head[0]) and (last in words["street_types"] or " ".join(head).lower() in
                                                  {" ".join(f) for f in words["fixed_streets"]}):
            return " ".join(head), tail
    return address_1, ""
