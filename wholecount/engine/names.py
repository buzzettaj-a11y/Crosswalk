"""Name comparison for copies and identity (P-DUP-6, P-ID-2). Every comparison folds first, so José equals Jose."""
import re
import tomllib
import unicodedata
from functools import lru_cache
from importlib import resources

from wholecount.engine.fold import fold
from wholecount.settings.loader import load

SUFFIXES = ("jr", "sr", "ii", "iii", "iv", "v", "2nd", "3rd")
# The old build's surname particles, beside the P-PREP-4 list in settings/names.toml.
EXTRA_PARTICLES = ("de", "del", "la", "las", "los", "van", "von", "der", "den", "di", "da", "do", "dos", "du", "el", "al", "bin",
                   "ibn", "san", "santa", "st", "mc", "mac", "o")
# Identity compares each name many times, so these pure string functions keep their recent answers in memory (M15 profile:
# words ran 646,000 times for one decision on 19,000 rows). Nothing is written anywhere, and the size is bounded.
_CACHE = 65536


@lru_cache(maxsize=_CACHE)
def words(text):
    """The fold, keeping single spaces between words. Apostrophes join (O'Brien is obrien); other punctuation splits."""
    s = unicodedata.normalize("NFKD", text or "")
    s = "".join(ch for ch in s if not unicodedata.combining(ch)).casefold()
    s = re.sub(r"['’]", "", s)
    s = "".join(ch if ch.isalnum() else " " for ch in s)
    return " ".join(s.split())


@lru_cache(maxsize=1)
def _particles():
    out = set(EXTRA_PARTICLES)
    for p in load("names")["particles"]:
        out.update(p.split())
    return frozenset(out)


@lru_cache(maxsize=1)
def _groups():
    text = resources.files("wholecount.engine.data").joinpath("nicknames.toml").read_text(encoding="utf-8")
    return tuple(tuple(g) for g in tomllib.loads(text)["groups"])


@lru_cache(maxsize=1)
def _group_ids():
    ids = {}
    for i, g in enumerate(_groups()):
        for name in g:
            ids.setdefault(name, set()).add(i)
    return {k: frozenset(v) for k, v in ids.items()}


def nickname_groups():
    return _groups()


@lru_cache(maxsize=_CACHE)
def head(first):
    """The first word of a given name, folded."""
    w = words(first).split()
    return w[0] if w else ""


@lru_cache(maxsize=_CACHE)
def given_keys(first):
    """The first word plus g<id> for each nickname group it belongs to."""
    h = head(first)
    if not h:
        return frozenset()
    return frozenset({h} | {f"g{i}" for i in _group_ids().get(h, ())})


def nickname_match(a, b):
    """True when the two given names share a nickname group."""
    ga = {k for k in given_keys(a) if k.startswith("g") and k[1:].isdigit()}
    gb = {k for k in given_keys(b) if k.startswith("g") and k[1:].isdigit()}
    return bool(ga & gb)


def same_given(a, b):
    """Equal after folding, or forms of one name (P-DUP-2, P-ID-3)."""
    return bool(fold(a)) and (fold(a) == fold(b) or nickname_match(a, b))


@lru_cache(maxsize=_CACHE)
def surname_tokens(last):
    """The distinguishing parts of a surname: no suffix words, particles or one-letter tokens. Every token of a double surname
    stays. If nothing is left, the particles stay."""
    parts = [p for p in words(last).split() if p not in SUFFIXES]
    keep = [p for p in parts if p not in _particles() and len(p) > 1]
    return frozenset(keep or parts)


def suffix_of(last, suffix_column=None):
    """The generational suffix at the end of the surname, else ''. A tidy-up <name>_suffix column wins when given."""
    if suffix_column is not None and words(suffix_column):
        return words(suffix_column)
    w = words(last).split()
    return w[-1] if len(w) > 1 and w[-1] in SUFFIXES else ""


def surname_core(last):
    """The folded surname without its suffix, for exact comparison (P-ID-3)."""
    w = words(last).split()
    if len(w) > 1 and w[-1] in SUFFIXES:
        w = w[:-1]
    return "".join(w)
