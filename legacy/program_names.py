"""
Program names: the same program, spelled differently in every system.

The second count the project asks for is people per program. That count is only
correct if a program means the same thing everywhere. In practice one system
writes "Workforce", another "Workforce Development", a third "WFD", and a fourth
"Workforce Dev.". Counted literally these look like four programs, and a person
enrolled in one of them appears to be in four.

This module proposes which names describe the same program and lets a person
confirm. As everywhere else in the tool, nothing is merged on a guess: a
grouping is a suggestion until it is accepted, and any variant can be pulled
back out.
"""
from __future__ import annotations

import re
import unicodedata
from collections import defaultdict

try:
    from thefuzz import fuzz as _fuzz

    def _ratio(a, b):
        return int(_fuzz.token_sort_ratio(a, b))
except Exception:                                  # pragma: no cover
    import difflib

    def _ratio(a, b):
        return int(difflib.SequenceMatcher(None, a, b).ratio() * 100)


# Words that carry no distinguishing meaning in a program name. Removing them
# lets "Workforce" and "Workforce Development Program" meet in the middle.
NOISE = {"program", "programs", "prog", "service", "services", "svc", "svcs",
         "department", "dept", "division", "div", "unit", "team", "office",
         "initiative", "project", "the", "of", "and", "for", "a", "an",
         "client", "clients", "participant", "participants", "general"}

# Endings that are abbreviations of a longer word, so "dev" meets "development".
STEM = [("development", "dev"), ("administration", "admin"),
        ("management", "mgmt"), ("services", "svcs"), ("resident", "res"),
        ("community", "comm"), ("education", "educ"), ("employment", "empl"),
        ("training", "trng"), ("assistance", "asst"), ("housing", "hsg"),
        ("workforce", "wf")]

SIMILAR_ENOUGH = 86      # below this, two names are not proposed as one


def _fold(text) -> str:
    """A name folded to lower case with punctuation and spacing normalized."""
    s = unicodedata.normalize("NFKD", str(text or ""))
    s = "".join(c for c in s if not unicodedata.combining(c))
    s = s.lower().replace("&", " and ")
    s = re.sub(r"[^a-z0-9 ]", " ", s)
    # collapse repeated spaces so "workforce  development" matches
    return re.sub(r"\s+", " ", s).strip()


def _tokens(name):
    """The words of a name after folding."""
    return [t for t in _fold(name).split() if t]


def _key(name) -> str:
    """
    A name reduced to what distinguishes it. Noise words are dropped and common
    abbreviations are expanded, so several spellings land on one key.
    """
    out = []
    for tok in _tokens(name):
        for full, short in STEM:
            if tok == short:
                tok = full
                break
        if tok in NOISE:
            continue
        out.append(tok)
    return " ".join(sorted(out)) or _fold(name)


def _initial_forms(name):
    """
    The ways people build an acronym from a name.

    An acronym is taken from the words as written, including ones this module
    treats as noise, because a person writing RS for Resident Services counted
    the S. Some acronyms also take two letters from a word, as WFD does from
    Workforce, so those forms are offered too.
    """
    all_toks = _tokens(name)
    meaning = [t for t in all_toks if t not in NOISE]
    forms = set()
    for toks in (all_toks, meaning):
        if len(toks) > 1:
            forms.add("".join(t[0] for t in toks))
        if toks:
            rest = "".join(t[0] for t in toks[1:])
            # first word contributes two letters, the rest one
            forms.add(toks[0][:2] + rest)
            # or its first two consonants, which is how WFD comes from Workforce
            cons = [ch for ch in toks[0] if ch not in "aeiou"]
            if len(cons) >= 2:
                forms.add(cons[0] + cons[1] + rest)
    return {f for f in forms if len(f) >= 2}


def _is_acronym_of(short, long_name) -> bool:
    """True when a short all-letters name is an acronym of a longer one."""
    s = _fold(short).replace(" ", "")
    if not (2 <= len(s) <= 6) or not s.isalpha():
        return False
    toks = _tokens(long_name)
    if len(toks) < 2:
        return False
    if s in _initial_forms(long_name):
        return True
    # A person abbreviating picks letters in order, at least one from each word,
    # starting from the first letter of the name. WFD comes from WorkForce
    # Development that way, and it will not match an unrelated name.
    if s[0] != toks[0][0]:
        return False
    pos, used = 0, 0
    joined = "".join(toks)
    for ch in s:
        found = joined.find(ch, pos)
        if found < 0:
            return False
        pos = found + 1
        used += 1
    return used == len(s) and len(s) >= len(toks)


def _starts_the_same(a, b) -> bool:
    """
    True when one name is the other with extra words on the end, for example
    Workforce and Workforce Development. The shorter name must be a real word
    rather than an initial, and must carry meaning on its own.
    """
    ta = [t for t in _tokens(a) if t not in NOISE]
    tb = [t for t in _tokens(b) if t not in NOISE]
    if not ta or not tb or ta == tb:
        return False
    short, long_ = (ta, tb) if len(ta) < len(tb) else (tb, ta)
    if len(short[0]) < 4:          # too short to mean anything by itself
        return False
    return long_[:len(short)] == short


def suggest_groups(values):
    """
    Propose which of these program names describe the same program.

    values: {name: count of rows using it}
    Returns a list of groups, each with a suggested canonical name, its
    variants, and why they were put together.
    """
    names = [n for n in values if str(n).strip()]
    if not names:
        return []

    # 1) names reducing to the same key are the same program
    by_key = defaultdict(list)
    for n in names:
        by_key[_key(n)].append(n)

    groups = []
    for key, members in by_key.items():
        groups.append({"members": list(members),
                       "why": "the same name once wording is set aside"
                       if len(members) > 1 else ""})

    # 2) fold an acronym into the long form it stands for
    merged = True
    while merged:
        merged = False
        for i in range(len(groups)):
            for j in range(len(groups)):
                if i == j or not groups[i] or not groups[j]:
                    continue
                a, b = groups[i], groups[j]
                if not a["members"] or not b["members"]:
                    continue
                hit = None
                for x in a["members"]:
                    for y in b["members"]:
                        if _is_acronym_of(x, y) or _is_acronym_of(y, x):
                            hit = "one is the initials of the other"
                        elif _ratio(_key(x), _key(y)) >= SIMILAR_ENOUGH:
                            hit = "the names are nearly the same"
                        elif _starts_the_same(x, y):
                            hit = ("one name is the other with more words on "
                                   "the end")
                        if hit:
                            break
                    if hit:
                        break
                if hit:
                    a["members"].extend(b["members"])
                    a["why"] = a["why"] or hit
                    b["members"] = []
                    merged = True
        groups = [g for g in groups if g["members"]]

    out = []
    for g in groups:
        members = sorted(set(g["members"]),
                         key=lambda n: (-values.get(n, 0), n))
        # the most used spelling reads as the natural canonical name
        canonical = members[0]
        out.append({
            "canonical": canonical,
            "variants": [{"name": n, "rows": values.get(n, 0)} for n in members],
            "rows": sum(values.get(n, 0) for n in members),
            "why": g["why"],
            "needs_confirming": len(members) > 1,
        })
    out.sort(key=lambda g: (-g["rows"], g["canonical"]))
    return out


def build_alias_map(groups):
    """{original name: canonical name} for every grouped variant."""
    out = {}
    for g in groups:
        for v in g["variants"]:
            out[v["name"]] = g["canonical"]
    return out


def apply_aliases(value, aliases):
    """The canonical name for one recorded value, or the value unchanged."""
    if not value:
        return value
    if value in aliases:
        return aliases[value]
    # fall back to a case and spacing insensitive match
    folded = {_fold(k): v for k, v in aliases.items()}
    return folded.get(_fold(value), value)
