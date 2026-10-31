"""Borough names, aliases, neighborhoods and US states (P-STD-4, P-STD-5), from settings/places.toml. Exact matching only."""
import re
from functools import lru_cache

from wholecount.settings.loader import load

BOROUGHS = ("New York", "Brooklyn", "Queens", "Bronx", "Staten Island")


def norm(text):
    return re.sub(r"\s+", " ", text.strip().lower())


@lru_cache(maxsize=1)
def _places():
    p = load("places")
    states = {}
    for name, code in p["states"].items():
        states[norm(name)] = code
        states[code.lower()] = code
    return {
        "aliases": {norm(k): v for k, v in p["aliases"].items()},
        "neighborhoods": {norm(k): v for k, v in p["neighborhoods"].items()},
        "allowed_pairs": {k: set(v) for k, v in p["allowed_pairs"].items()},
        "states": states,
    }


def city_kind(text):
    """("alias", borough) for a borough name or alias, ("neighborhood", borough) for a listed neighborhood, else (None, None)."""
    n = norm(text)
    pl = _places()
    if n in pl["aliases"]:
        return "alias", pl["aliases"][n]
    if n in pl["neighborhoods"]:
        return "neighborhood", pl["neighborhoods"][n]
    return None, None


def borough_of(text):
    return city_kind(text)[1]


def allowed_pair(borough, zip_code):
    return zip_code in _places()["allowed_pairs"].get(borough, set())


NY_FORMS = {"ny", "n.y.", "ny.", "new york", "new york state"}


def state_code(text):
    """NY for its forms, another state's or territory's code for its name or code, else None."""
    n = norm(text)
    if n in NY_FORMS:
        return "NY"
    return _places()["states"].get(n)


def counts():
    pl = _places()
    return {"aliases": len(pl["aliases"]), "neighborhoods": len(pl["neighborhoods"]),
            "states": len({v for v in pl["states"].values()})}
