"""Programs (SPEC 6.9, P-PROG): which program each table feeds, which spellings may be one program, and the program map.

A proposal is inert. Only confirm and merge decisions put names in a group, and build_program_map is the only code that
builds the map, so the staged route, the fast path and the preview agree (B-20, C-05).
"""
import difflib
import hashlib
import re
import unicodedata
from dataclasses import dataclass, field
from typing import Literal

from wholecount.settings.loader import load

REASONS = ("same_name", "initials", "nearly_same", "more_words")
SEP = "\x1f"


@dataclass(frozen=True)
class TableProgram:
    table_key: str
    source: Literal["column", "default", "none"]
    column: str | None
    default: str | None
    rows: int
    values: tuple = ()        # column source: ((name as entered, rows), ...); "" counts the blank cells


@dataclass(frozen=True)
class ProgramName:
    name: str
    rows: int
    tables: tuple = ()


@dataclass(frozen=True)
class Proposal:
    proposal_id: str
    members: tuple
    label: str
    reasons: tuple            # (name_a, name_b, reason code)


@dataclass(frozen=True)
class ProgramDecision:
    kind: Literal["confirm", "split", "merge", "rename"]
    members: tuple
    label: str | None = None
    inherited: bool = False


@dataclass(frozen=True)
class Group:
    label: str
    members: tuple
    from_earlier_batch: bool = False


@dataclass(frozen=True)
class ProgramMap:
    groups: tuple = ()
    alias: dict = field(default_factory=dict)
    unconfirmed: tuple = ()
    not_in_goal2: tuple = ()
    not_applied: tuple = ()


@dataclass(frozen=True)
class Proceed:
    pass


@dataclass(frozen=True)
class StopAtPrograms:
    unconfirmed: int


def _settings(overrides=None):
    s = dict(load("programs"))
    s.update(overrides or {})
    return s


# Names

def program_sources(tables):
    """PROG-1: (names, not_in_goal2). A column wins over a default. A table with neither is listed with its row count. Blank
    cells in a column are rows without a program, never a program."""
    counts, where, missing = {}, {}, []
    for t in tables:
        if t.source == "column":
            pairs = t.values
        elif t.source == "default" and (t.default or "").strip():
            pairs = ((t.default, t.rows),)
        else:
            missing.append((t.table_key, t.rows))
            continue
        for name, n in pairs:
            name = (name or "").strip()
            if not name:
                continue
            counts[name] = counts.get(name, 0) + n
            where.setdefault(name, set()).add(t.table_key)
    names = [ProgramName(n, counts[n], tuple(sorted(where[n]))) for n in sorted(counts)]
    return names, sorted(missing)


def _tokens(name):
    s = unicodedata.normalize("NFKD", name)
    s = "".join(ch for ch in s if not unicodedata.combining(ch)).lower().replace("&", " and ")
    return "".join(ch if ch.isalnum() else " " for ch in s).split()


def _content(tokens, s):
    """Tokens minus noise, with short forms expanded. A trailing single "a" stays (Class A)."""
    noise = set(s["noise"])
    out = []
    for i, t in enumerate(tokens):
        if t in noise and not (t == "a" and i == len(tokens) - 1 and i > 0):
            continue
        out.append(s["stems"].get(t, t))
    return out


def _key(name, s):
    return " ".join(sorted(_content(_tokens(name), s)))


def _is_caps(name, s):
    letters = name.replace(".", "").strip()
    return (re.fullmatch(r"(?:[A-Z]\.?)+", name.strip()) is not None
            and s["caps_min_letters"] <= len(letters) <= s["caps_max_letters"])


def _subseq(chunk, word):
    it = iter(word)
    return all(ch in it for ch in chunk)


def _lines_up(letters, words):
    """Each word gives one chunk of one or more letters that starts with its first letter and is a subsequence of it."""
    if not words:
        return not letters
    if not letters:
        return False
    w = words[0]
    for n in range(1, len(letters) - len(words) + 2):
        chunk = letters[:n]
        if chunk[0] == w[0] and _subseq(chunk, w) and _lines_up(letters[n:], words[1:]):
            return True
    return False


def _initials(a, b, s):
    for caps, other in ((a, b), (b, a)):
        if not _is_caps(caps, s):
            continue
        letters = caps.replace(".", "").strip().lower()
        full = _tokens(other)
        for words in (full, [t for t in full if t not in set(s["noise"])]):
            if len(words) >= 2 and _lines_up(letters, words):
                return True
    return False


def _vetoed(a, b, s):
    ca, cb = set(_content(_tokens(a), s)), set(_content(_tokens(b), s))
    meaning = set(s["meaning_words"])
    return any(any(ch.isdigit() for ch in t) or len(t) == 1 or t in meaning for t in ca ^ cb)


def _more_words(a, b, s):
    ta, tb = _content(_tokens(a), s), _content(_tokens(b), s)
    short, long_ = (ta, tb) if len(ta) <= len(tb) else (tb, ta)
    if not short or len(short) == len(long_) or long_[:len(short)] != short or len(short[0]) < 4:
        return False
    return all(t in set(s["ending_ok"]) for t in long_[len(short):])


def pair_reason(a, b, settings=None):
    """PROG-2: the first rule that holds, in order, or None. Rules 3 and 4 obey the PROG-2b veto."""
    s = _settings(settings)
    ka, kb = _key(a, s), _key(b, s)
    if ka and ka == kb:
        return "same_name"
    if _initials(a, b, s):
        return "initials"
    if ka and kb and difflib.SequenceMatcher(None, ka, kb).ratio() >= s["similarity"] and not _vetoed(a, b, s):
        return "nearly_same"
    if _more_words(a, b, s) and not _vetoed(a, b, s):
        return "more_words"
    return None


def label_of(names_with_rows):
    """PROG-2d: most rows, then the longest name, then the first in alphabetical order."""
    return sorted(names_with_rows, key=lambda nr: (-nr[1], -len(nr[0]), nr[0]))[0][0]


def proposal_id(members):
    return hashlib.sha256(SEP.join(sorted(members)).encode("utf-8")).hexdigest()[:12]


def propose_groups(names, settings=None):
    """PROG-2c: sets where every pair passed PROG-2, built greedily. A name is in at most one proposal."""
    order = sorted(names, key=lambda n: (-n.rows, n.name))
    rows = {n.name: n.rows for n in names}
    used, out = set(), []
    for i, first in enumerate(order):
        if first.name in used:
            continue
        members, reasons = [first.name], []
        for cand in order[i + 1:]:
            if cand.name in used:
                continue
            found = [(m, pair_reason(m, cand.name, settings)) for m in members]
            if all(r for _, r in found):
                members.append(cand.name)
                reasons += [(min(m, cand.name), max(m, cand.name), r) for m, r in found]
        if len(members) > 1:
            used.update(members)
            ms = tuple(sorted(members))
            out.append(Proposal(proposal_id(ms), ms, label_of([(m, rows[m]) for m in ms]), tuple(sorted(reasons))))
    return sorted(out, key=lambda p: p.members)


# The map

def build_program_map(names, proposals, decisions, not_in_goal2=()):
    """The only code that builds the map. Inherited decisions apply first, so a batch decision on the same names wins."""
    rows = {n.name: n.rows for n in names}
    present = set(rows)
    groups = []           # dicts: members set, rename, batch flag
    not_applied, touched = [], set()

    def group_of(name):
        return next((g for g in groups if name in g["members"]), None)

    def taken(label, g):
        others = [x for x in groups if x is not g]
        return label in present - g["members"] or any(_label(x) == label for x in others)

    def _label(g):
        return g["rename"] or label_of([(m, rows[m]) for m in g["members"]])

    for d in sorted(decisions, key=lambda d: not d.inherited):
        here = sorted(set(d.members) & present)
        need = 2 if d.kind in ("confirm", "merge") else 1
        if len(here) < need:
            if not d.inherited:
                not_applied.append((d, "names_gone"))
            continue
        if d.kind in ("confirm", "merge"):
            joined = set(here)
            for m in here:
                g = group_of(m)
                if g is not None:
                    if d.kind == "merge":
                        joined |= g["members"]
                    g["members"].discard(m)
            groups[:] = [g for g in groups if len(g["members"]) > 1]
            new = {"members": joined, "rename": d.label or None, "batch": not d.inherited}
            if d.label and taken(d.label, new):
                not_applied.append((d, "label_taken"))
                new["rename"] = None
            groups.append(new)
        elif d.kind == "split":
            for m in here:
                g = group_of(m)
                if g is not None:
                    g["members"].discard(m)
                    if g["rename"] == m:
                        g["rename"] = None
                    g["batch"] = g["batch"] or not d.inherited
            groups[:] = [g for g in groups if len(g["members"]) > 1]
        elif d.kind == "rename":
            g = group_of(here[0])
            if g is None or not d.label:
                not_applied.append((d, "not_a_group"))
                continue
            if taken(d.label, g):
                not_applied.append((d, "label_taken"))
                continue
            g["rename"] = d.label
        touched.update(here)

    out_groups = tuple(sorted((Group(_label(g), tuple(sorted(g["members"])), not g["batch"]) for g in groups),
                              key=lambda g: g.label))
    alias = {m: g.label for g in out_groups for m in g.members}
    unconfirmed = tuple(p for p in proposals if not (set(p.members) & touched))
    return ProgramMap(out_groups, alias, unconfirmed, tuple(not_in_goal2), tuple(not_applied))


def canonical_program(raw, pm):
    """The raw name unless a confirmed group holds it."""
    return pm.alias.get(raw.strip(), raw) if raw else raw


def fast_path_gate(pm):
    """PROG-4: stop at Programs while any proposal is open. It never builds groups on its own."""
    return StopAtPrograms(len(pm.unconfirmed)) if pm.unconfirmed else Proceed()


def people_without_program(master_of_record, record_program):
    """PROG-8: master IDs none of whose counted records has a program."""
    has = {}
    for rk, master in master_of_record.items():
        has[master] = has.get(master, False) or bool((record_program.get(rk) or "").strip())
    return sum(1 for v in has.values() if not v)


def audit_fields(decision):
    """PROG-6: the kind, the program names and the label. Program names are not client data."""
    return {"kind": decision.kind, "programs": tuple(sorted(decision.members)), "label": decision.label}
