"""settings/places.toml: 24 aliases, at least 114 neighborhoods, only the five boroughs, 56 states. Floral Park left out."""
from wholecount.engine.geo.places import BOROUGHS, counts
from wholecount.settings.loader import load

P = load("places")


def test_counts():
    c = counts()
    assert c["aliases"] == 24 and c["neighborhoods"] >= 114 and c["states"] == 56


def test_only_the_five_boroughs():
    assert set(P["aliases"].values()) | set(P["neighborhoods"].values()) <= set(BOROUGHS)


def test_b28_names_and_marble_hill_are_listed_and_floral_park_is_not():
    for name in ("woodhaven", "brooklyn heights", "kew gardens hills", "rockaway park", "douglaston", "bellerose", "kensington",
                 "gravesend", "cobble hill", "kips bay", "hamilton heights"):
        assert name in P["neighborhoods"], name
    assert P["neighborhoods"]["marble hill"] == "New York"
    assert "floral park" not in P["neighborhoods"]
    assert P["allowed_pairs"] == {"New York": ["10463"]}
