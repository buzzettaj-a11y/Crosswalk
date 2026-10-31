"""settings/programs.toml loads, and no word is both noise and a meaning word."""
from wholecount.settings.loader import load


def test_loads_and_lists_are_disjoint():
    s = load("programs")
    assert s["similarity"] == 0.86 and (s["caps_min_letters"], s["caps_max_letters"]) == (2, 6)
    assert not set(s["noise"]) & set(s["meaning_words"])
    assert s["ending_ok"] == ["development"] and s["stems"]["dev"] == "development"
