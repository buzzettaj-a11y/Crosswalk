"""Name and address casing (P-STD-1, P-PREP-1). A value is re-cased only when its letters are all upper case or all lower case;
mixed case is kept exactly as typed."""
import re

from wholecount.settings.loader import load

ROMAN = {"ii", "iii", "iv", "vi", "vii", "viii", "ix", "xi", "xii", "xiii"}
APOSTROPHES = "'’"
DIRECTIONALS = {"n", "s", "e", "w", "ne", "nw", "se", "sw"}

_NAMES = None


def _names():
    global _NAMES
    if _NAMES is None:
        n = load("names")
        _NAMES = {
            "mac": set(n["mac_names"]),
            "particles": {w for p in n["particles"] for w in p.split()},
            "exceptions": dict(n["casing_exceptions"]),
        }
    return _NAMES


def recasable(value):
    letters = [c for c in value if c.isalpha()]
    return bool(letters) and (all(c.isupper() for c in letters) or all(c.islower() for c in letters))


def _cap(s):
    return s[:1].upper() + s[1:].lower()


def _name_part(part, all_caps):
    n = _names()
    if not part:
        return part
    if part.upper() in n["exceptions"]:
        return n["exceptions"][part.upper()]
    low = part.lower()
    if low in ROMAN:
        return part.upper()
    for ap in APOSTROPHES:
        if ap in part:
            head, _, tail = part.partition(ap)
            if head.lower() in ("o", "d") and tail:
                return head.upper() + ap + _name_part(tail, all_caps)
            return _cap(head) + ap + tail.lower()
    letters = sum(1 for c in part if c.isalpha())
    if low.startswith("mc") and all_caps and letters >= 4 and low[2:].isalpha():
        return "Mc" + low[2].upper() + low[3:]
    if low in n["mac"]:
        return "Mac" + low[3].upper() + low[4:]
    return _cap(part)


def title_name(value):
    if not recasable(value):
        return value
    all_caps = value.upper() == value
    particles = _names()["particles"]
    out = []
    for i, word in enumerate(value.split(" ")):
        if i > 0 and word.lower() in particles:
            out.append(word.lower())
        else:
            out.append("-".join(_name_part(p, all_caps) for p in word.split("-")))
    return " ".join(out)


def _address_word(w):
    if not w:
        return w
    if w.lower().strip(".") in DIRECTIONALS:
        return w.upper()
    m = re.fullmatch(r"(\d+)(st|nd|rd|th)", w.lower())
    if m:
        return m.group(1) + m.group(2)
    if any(c.isdigit() for c in w):
        return w
    if "-" in w:
        return "-".join(_address_word(p) for p in w.split("-"))
    return _cap(w)


def title_address(value):
    if not recasable(value):
        return value
    return " ".join(_address_word(w) for w in value.split(" "))
