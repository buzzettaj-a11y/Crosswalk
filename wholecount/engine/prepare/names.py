"""P-PREP-4: splitting a jammed name into first, middle, last, title, credential, suffix and extra. Every word lands in one part.

Titles, credentials and generational suffixes never become a first, middle or last name (B-12). Particles stay with the surname
(B-11). A name of three or more words with no comma can't be split with certainty, so every word is kept, the row gets the soft
reason name_order_unclear, and nothing is dropped (B-32).
"""
import re
from dataclasses import dataclass, field

from wholecount.settings.loader import load

_NICKNAME = re.compile(r"\(([^)]*)\)|\"([^\"]*)\"|(?<![\w'])'([^']+)'(?![\w'])")


@dataclass
class NameParts:
    first: str = ""
    middle: str = ""
    last: str = ""
    title: str = ""
    credential: str = ""
    suffix: str = ""
    extra: str = ""
    notes: list = field(default_factory=list)     # reason IDs: name_order_unclear, name_extra_tokens


_WORDS = None


def name_words():
    global _WORDS
    if _WORDS is None:
        n = load("names")
        _WORDS = {
            "titles": set(n["titles"]), "credentials": set(n["credentials"]), "suffixes": set(n["suffixes"]),
            "particles": [p.split() for p in sorted(n["particles"], key=lambda p: -len(p.split()))],
            "particle_words": {w for p in n["particles"] for w in p.split()},
            "compound_given": {tuple(c.split()) for c in n["compound_given"]},
            "middle_stop": set(n["middle_stop"]),
        }
    return _WORDS


def _n(token):
    return token.lower().strip(".,")


def _single_letter(token):
    return bool(re.fullmatch(r"[A-Za-z]\.?", token))


def _join(*parts):
    return " ".join(p for p in parts if p)


def _add(parts, attr, text):
    setattr(parts, attr, _join(getattr(parts, attr), text))


def _flag(parts, reason):
    if reason not in parts.notes:
        parts.notes.append(reason)


def _strip_titles(tokens, parts, w):
    while tokens:
        t = _n(tokens[0])
        if t == "sr" and len(tokens) < 3:
            break
        if t in w["titles"] and len(tokens) > 1:
            _add(parts, "title", tokens.pop(0))
            continue
        break
    return tokens


def _strip_tail(tokens, parts, w, comma_less):
    """Credentials and suffixes at the end. DO and NP need two words before them; a lone I is a suffix only at the end of a
    comma-less name of three or more words."""
    changed = True
    while changed and len(tokens) > 1:
        changed = False
        t = _n(tokens[-1])
        before = len(tokens) - 1
        if t in w["credentials"] and (t not in ("do", "np") or before >= 2):
            parts.credential = _join(tokens.pop(), parts.credential)
            changed = True
        elif t in w["suffixes"] and before >= 1:
            if t == "i" and not (comma_less and len(tokens) >= 3):
                break
            parts.suffix = _join(tokens.pop(), parts.suffix)
            changed = True
    return tokens


def _surname_split(tokens, w):
    """(head, surname tokens). A particle chain directly before the final word joins the surname."""
    if len(tokens) < 2:
        return [], tokens
    i = len(tokens) - 1
    while i > 1:
        for p in w["particles"]:
            k = len(p)
            if i - k >= 1 and [_n(t) for t in tokens[i - k:i]] == p:
                i -= k
                break
        else:
            break
    return tokens[:i], tokens[i:]


def _given(tokens, parts, w, comma_form):
    """First name, then a middle initial, from the given-name words."""
    if not tokens:
        return
    if len(tokens) >= 2 and tuple(_n(t) for t in tokens[:2]) in w["compound_given"]:
        parts.first = _join(tokens[0], tokens[1])
        rest = tokens[2:]
    else:
        parts.first = tokens[0]
        rest = tokens[1:]
    if rest and _single_letter(rest[0]):
        parts.middle = rest[0]
        rest = rest[1:]
    if rest:
        if comma_form:
            _add(parts, "extra", " ".join(rest))
            _flag(parts, "name_extra_tokens")
        else:
            parts.middle = _join(parts.middle, " ".join(rest))
            _flag(parts, "name_order_unclear")


def _segment_kind(seg, w):
    toks = [_n(t) for t in seg.split()]
    if toks and all(t in w["suffixes"] for t in toks):
        return "suffix"
    if toks and all(t in w["credentials"] for t in toks):
        return "credential"
    return None


def parse_name(raw, words=None, form="auto"):
    """form is auto (a comma means Last, First), last_first (no comma: the first word is the surname) or first_last."""
    w = words or name_words()
    parts = NameParts()
    s = re.sub(r"\s+", " ", raw).strip()
    for m in list(_NICKNAME.finditer(s)):
        _add(parts, "extra", m.group(0))
        _flag(parts, "name_extra_tokens")
    s = re.sub(r"\s+", " ", _NICKNAME.sub(" ", s)).strip()
    had_comma = "," in s and form != "first_last"
    s = s.strip(" ,")
    if not s:
        return parts

    segments = [x.strip() for x in s.split(",")]
    segments = [x for x in segments if x]
    kept = []
    for i, seg in enumerate(segments):
        kind = _segment_kind(seg, w) if i > 0 else None
        if kind:
            _add(parts, kind, seg)
        else:
            kept.append(seg)
    if form == "last_first" and len(kept) == 1 and " " in kept[0]:
        first_word, rest = kept[0].split(" ", 1)
        kept = [first_word, rest]
    if form == "first_last" and len(kept) > 1:
        kept = [" ".join(kept)]

    if len(kept) == 1 and had_comma and not any(_segment_kind(x, w) for x in segments[1:]):
        kept = [kept[0], ""]
    if len(kept) == 1:
        tokens = _strip_titles(kept[0].split(), parts, w)
        tokens = _strip_tail(tokens, parts, w, comma_less=True)
        if len(tokens) == 1:
            parts.first = tokens[0]
            return parts
        head, surname = _surname_split(tokens, w)
        parts.last = " ".join(surname)
        _given(head, parts, w, comma_form=False)
        return parts

    surname_tokens = kept[0].split()
    surname_tokens = _strip_titles(surname_tokens, parts, w)
    surname_tokens = _strip_tail(surname_tokens, parts, w, comma_less=False)
    parts.last = " ".join(surname_tokens)
    given = kept[1].split()
    while given and _n(given[0]) in w["suffixes"] and _n(given[0]) != "i" and len(given) > 1:
        _add(parts, "suffix", given.pop(0))
    given = _strip_titles(given, parts, w)
    given = _strip_tail(given, parts, w, comma_less=False) if len(given) > 1 else given
    _given(given, parts, w, comma_form=True)
    if len(kept) > 2:
        _add(parts, "extra", ", ".join(kept[2:]))
        _flag(parts, "name_extra_tokens")
    return parts


def middle_initial(value, words=None):
    """(initial, note). A real middle name or letter gives its first letter in upper case. The stop list, suffixes and anything
    that doesn't start with a letter give blank (B-33)."""
    w = words or name_words()
    v = value.strip()
    if not v:
        return "", None
    low = v.lower()
    if low in w["middle_stop"] or low.strip(".") in w["middle_stop"] or low.strip(".,") in w["suffixes"] or not v[0].isalpha():
        return "", "middle_initial_dropped"
    initial = v[0].upper()
    return initial, (None if v == initial else "middle_initial_reduced")
