"""The address key (SPEC 5.1, P-GEO-3, P-ID-5, C-24): house number, normalized street with its type, and ZIP. M06 uses it.

The street type stays in the key, so 45 Park Ave and 45 Park Pl differ. Units are never in it: the caller passes Address_1 after
the unit was moved out. Spelled-out ordinals (Fifth Avenue) are not converted; Geosupport handles those.
"""
import re
import unicodedata

DIRECTIONS = {"n": "north", "s": "south", "e": "east", "w": "west"}
TYPES = {"st": "street", "ave": "avenue", "av": "avenue", "rd": "road", "blvd": "boulevard", "dr": "drive", "ln": "lane", "ct": "court",
         "pl": "place", "ter": "terrace", "pkwy": "parkway", "hwy": "highway", "sq": "square", "cir": "circle", "expy": "expressway",
         "plz": "plaza"}
_ORDINAL = re.compile(r"^(\d+)(?:st|nd|rd|th)$")


def _fold(text):
    return "".join(ch for ch in unicodedata.normalize("NFKD", text) if not unicodedata.combining(ch))


def normalize_street(text):
    """ADDR-1 to ADDR-5."""
    s = _fold(text).lower()
    s = re.sub(r"[.,']", "", s)
    s = re.sub(r"(?<=[a-z])-(?=[a-z])", " ", s)
    tokens = s.split()
    out = []
    for i, t in enumerate(tokens):
        m = _ORDINAL.match(t)
        if m:
            out.append(m.group(1))
        elif t == "st" and i != len(tokens) - 1:
            out.append("saint")
        elif t in TYPES and i == len(tokens) - 1:
            out.append(TYPES[t])
        elif t in DIRECTIONS and len(tokens) > 1:
            out.append(DIRECTIONS[t])
        else:
            out.append(t)
    return " ".join(out)


def normalize_house(text):
    """A house number keeps its hyphen (42-09); spaces and case go."""
    return re.sub(r"\s+", "", _fold(text).lower())


def address_key(house_number, street, zip5):
    return f"{normalize_house(house_number)}|{normalize_street(street)}|{zip5.strip() or '-'}"


def split_house_street(address_1):
    """(house number, street) from an Address_1 value with no unit. ('', '') when there's no house number."""
    m = re.match(r"^\s*(\d+[A-Za-z]?(?:\s*-\s*\d+[A-Za-z]?)?)\s+(.+?)\s*$", address_1)
    if not m:
        return "", ""
    return re.sub(r"\s+", "", m.group(1)), m.group(2)
