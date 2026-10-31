"""P-PREP-3: splitting a jammed address into street, unit, city, state, ZIP and extra text. Every input word ends up in one part.

The rules run in the milestone's order: separators and the country, the ZIP tail, the NY state tail, the street end, the units after
it, a unit followed by city text, and what is left. The city is read only from after the street end (B-08), so a street named for a
borough stays whole. Only NY is read as a state (P-STD-5).
"""
import re
from dataclasses import dataclass, field

from wholecount.settings.loader import load

_DESIGNATOR = r"(?:[0-9]{1,5}(?:[\s\-]{0,2}[A-Za-z]{1,2})?|[A-Za-z]{1,2}[\s\-]{0,2}[0-9]{1,5}|[0-9A-Za-z\-]*[0-9][0-9A-Za-z\-]*)"
_END = r"(?=[\s,]|$)"
_ZIP_TAIL = re.compile(r"(?:^|(?<=[^\d\-]))(\d{5})(?:-?(\d{4}))?\s*$")
_STATE_TAIL = re.compile(r"(?:^|(?<=[\s,]))(N\.?\s?Y\.?|New\s+York(?:\s+State)?)\s*$", re.I)
_HOUSE_RANGE = re.compile(r"^\s*(\d+)\s+-\s+(\d+)(?=\s)")
_SPACED_SEPARATOR = re.compile(r"\s+[\-/;:|]{1,3}\s+")
_ORDINAL_FLOOR = re.compile(r"^\d{1,3}(?:st|nd|rd|th)\s+(?:fl|floor)\.?" + _END, re.I)
# A bare designator such as 14A or 5C. An ordinal such as 45th is a street name, never a unit.
_BARE_DESIGNATOR = re.compile(r"^(?!\d+(?:st|nd|rd|th)\b)(?:\d{1,4}[A-Za-z]{1,2}|[A-Za-z]\d{1,4}|\d{1,4}-[A-Za-z])" + _END, re.I)
# A whole comma segment that is only a designator: B, 4, 14A, B2. Two letters alone (NJ, CT) are not a unit.
_LONE_SEGMENT_UNIT = re.compile(r"^(?!\d+(?:st|nd|rd|th)$)(?:[A-Za-z]|\d{1,4}[A-Za-z]{0,2}|[A-Za-z]\d{1,4}|\d{1,4}-[A-Za-z])$", re.I)


@dataclass
class AddressParts:
    street: str = ""
    unit: str = ""
    city: str = ""
    state: str = ""
    zip: str = ""
    extra: str = ""
    notes: list = field(default_factory=list)     # reason IDs: address_extra_text (decision), zip_had_9_digits (note)


_WORDS = None


def address_words():
    global _WORDS
    if _WORDS is None:
        w = load("address_words")
        _WORDS = {k: (set(v) if isinstance(v, list) else v) for k, v in w.items()}
        _WORDS["fixed_streets"] = [s.split() for s in w["fixed_streets"]]
        _WORDS["countries"] = sorted(w["countries"], key=len, reverse=True)
    return _WORDS


def _norm(token):
    return token.lower().rstrip(".,")


def _unit_word_re(words):
    unit = "|".join(sorted(words["unit_words"], key=len, reverse=True))
    return re.compile(r"^(?:(?:" + unit + r")\.?\s*#?\s*:?\s*(?:" + _DESIGNATOR + r"|[A-Za-z]{1,2})" + _END +
                      r"|#\s*:?\s*(?:" + _DESIGNATOR + r"|[A-Za-z]{1,2})" + _END + r")", re.I)


def _match_unit(text, words, after_street):
    """The unit at the start of text, as a string, or None. after_street allows a bare designator like 14A."""
    m = _unit_word_re(words).match(text)
    if m:
        return m.group(0).strip()
    m = _ORDINAL_FLOOR.match(text)
    if m:
        return m.group(0).strip()
    first = text.split(" ", 1)[0]
    if _norm(first) in words["standalone_units"]:
        rest = text[len(first):].lstrip()
        nxt = rest.split(" ", 1)[0] if rest else ""
        if _norm(nxt) in ("fl", "floor"):
            return f"{first} {nxt}"
        return first
    if after_street:
        m = _BARE_DESIGNATOR.match(text)
        if m:
            return m.group(0)
    return None


def _take_units(text, words, after_street):
    """(units found, rest). Reads units from the start of text, one after another."""
    units, rest = [], text.strip()
    while rest:
        u = _match_unit(rest, words, after_street and not units)
        if not u:
            break
        units.append(u)
        rest = rest[len(u):].lstrip(" ,")
    return units, rest


def _street_end(tokens, words, zip_peeled=False):
    """The index just past the street's end in tokens, or None when no street end is found. With a ZIP peeled, a two-letter
    uppercase state code as the final word is a state, never a street type (CT before a ZIP is Connecticut)."""
    low = [_norm(t) for t in tokens]
    if zip_peeled and len(tokens) > 1 and re.fullmatch(r"[A-Z]{2}", tokens[-1]) and low[-1] in words["state_codes"]:
        low = low[:-1]
    best = None
    for fixed in words["fixed_streets"]:
        for i in range(len(low) - len(fixed) + 1):
            if low[i:i + len(fixed)] == fixed:
                best = max(best or 0, i + len(fixed))
    for i, t in enumerate(low):
        if i == 0 and t[:1].isdigit():
            continue
        if t in words["lettered_avenue"] and i + 1 < len(low) and re.fullmatch(r"[a-z]|\d{1,3}", low[i + 1]):
            best = max(best or 0, i + 2)
        elif t in words["street_types"]:
            end = i + 1
            if end < len(low) and low[end] in words["directionals"]:
                end += 1
            best = max(best or 0, end)
    return best


def _is_borough(text, words):
    return _norm(text.strip(" ,")) in words["boroughs"]


def _strip_country(s, words):
    for c in words["countries"]:
        m = re.search(r"[\s,]+" + re.escape(c) + r"\.?\s*$", s, re.I)
        if m:
            return s[:m.start()]
    return s


def _prepare(raw, words):
    s = re.sub(r"\s+", " ", raw).strip()
    s = re.sub(r"[\s,;:\-|]+$", "", s)
    s = _strip_country(s, words)
    s = re.sub(r"[\s,;:\-|]+$", "", s)
    s = _HOUSE_RANGE.sub(r"\1-\2", s)
    s = _SPACED_SEPARATOR.sub(", ", s)
    s = re.sub(r"\s*,\s*(?:,\s*)*", ", ", s)
    return s.strip(" ,")


def parse_address(raw, words=None):
    words = words or address_words()
    parts = AddressParts()
    s = _prepare(raw, words)
    if not s:
        return parts

    m = _ZIP_TAIL.search(s)
    if m:
        parts.zip = m.group(1)
        if m.group(2):
            parts.notes.append("zip_had_9_digits")
        s = s[:m.start()].rstrip(" ,")
    m = _STATE_TAIL.search(s)
    if m:
        parts.state = "NY"
        s = s[:m.start()].rstrip(" ,")
    peeled = bool(parts.zip or parts.state)

    segments = [x.strip() for x in s.split(",") if x.strip()]
    if not segments:
        return parts
    head_tokens = segments[0].split(" ")
    end = _street_end(head_tokens, words, zip_peeled=bool(parts.zip) and len(segments) == 1)
    if end is None and len(segments) == 1:
        if peeled:
            for n in (3, 2, 1):
                if len(head_tokens) > n and _is_borough(" ".join(head_tokens[-n:]), words):
                    parts.street = " ".join(head_tokens[:-n])
                    parts.city = " ".join(head_tokens[-n:])
                    return parts
        parts.street = segments[0]
        return parts
    if end is None:
        end = len(head_tokens)
    parts.street = " ".join(head_tokens[:end])
    tail = " ".join(head_tokens[end:])
    pieces = ([tail] if tail else []) + segments[1:]

    units, leftovers = [], []
    for i, piece in enumerate(pieces):
        whole_segment = not (i == 0 and tail)
        if whole_segment and _LONE_SEGMENT_UNIT.fullmatch(piece):
            units.append(piece)
            continue
        found, rest = _take_units(piece, words, True)
        units.extend(found)
        if rest:
            leftovers.append(rest)

    if units:
        parts.unit = " ".join(units)
    if not parts.street and units:
        parts.street, parts.unit = s, ""

    if leftovers:
        city, extra = _split_city(leftovers, peeled, words)
        parts.city = city
        if extra:
            parts.extra = extra
            parts.notes.append("address_extra_text")
    return parts


def _split_city(leftovers, peeled, words):
    """(city text, extra text). With a ZIP or state peeled, the trailing pieces up to three words are city text. Without one,
    only a borough name is a city. Everything else is extra."""
    if not peeled:
        if len(leftovers) == 1 and _is_borough(leftovers[0], words):
            return leftovers[0], ""
        if _is_borough(leftovers[-1], words):
            return leftovers[-1], ", ".join(leftovers[:-1])
        return "", ", ".join(leftovers)
    city, n_words = [], 0
    for piece in reversed(leftovers):
        w = len(piece.split())
        if n_words + w > 3:
            break
        city.insert(0, piece)
        n_words += w
    extra = leftovers[:len(leftovers) - len(city)]
    return ", ".join(city), ", ".join(extra)


def split_trailing_unit(text, words=None):
    """(street, unit or None) for an Address_1 value with no city, state or ZIP: rules 4 and 5 only (M04 uses it for P-STD-8)."""
    words = words or address_words()
    s = re.sub(r"\s+", " ", text).strip()
    tokens = s.split(" ")
    end = _street_end(tokens, words)
    if end is None or end >= len(tokens):
        return s, None
    tail = " ".join(tokens[end:])
    units, rest = _take_units(tail, words, True)
    if units and not rest.strip(" ,"):
        return " ".join(tokens[:end]).rstrip(","), " ".join(units)
    return s, None
