"""Who is the same person across files (SPEC 6.8, P-ID). Keys are strings: the engine never sees the install secret.

Joins happen only for the three named reasons in P-ID-3, returned as values: same_system_id, four_exact_facts and
earlier_batch. A score never joins anything. Every other likely pair is a proposal with evidence codes; the copy registry holds
the sentences.
"""
import copy as _copy
import hashlib
from dataclasses import dataclass
from typing import Literal

from wholecount.engine.fold import fold
from wholecount.engine.names import given_keys, head, same_given, suffix_of, surname_core, surname_tokens
from wholecount.settings.loader import load

REASONS = ("same_system_id", "four_exact_facts", "earlier_batch")
# Evidence code -> weight name. Codes not listed carry no points.
WEIGHT_OF = {
    "dob_exact": "dob_exact", "dob_swapped": "dob_near", "dob_one_digit": "dob_near", "dob_differs": "dob_differs",
    "surname_exact": "last_exact", "surname_part": "last_overlap", "names_swapped": "last_swapped",
    "given_exact": "first_exact", "given_nickname": "first_nick", "given_initial": "first_initial",
    "address_exact": "addr_exact", "zip_only": "zip_only", "same_system_id": "same_system_id", "rare_name": "rare_name_bonus",
}
EVIDENCE_CODES = ("dob_exact", "dob_swapped", "dob_one_digit", "dob_differs", "surname_exact", "surname_part", "names_swapped",
                  "given_exact", "given_nickname", "given_initial", "address_exact", "zip_only", "same_system_id",
                  "same_system_id_differs", "suffix_differs", "rare_name")
CAUTION_CODES = frozenset({"dob_swapped", "dob_one_digit", "dob_differs", "surname_part", "names_swapped", "suffix_differs"})


class InconsistentInput(Exception):
    """The caller skipped a step: rows under one Client_ID key disagree (DUP-3), or rows share a name-based key (DUP-7)."""

    def __init__(self, code):
        super().__init__(code)
        self.code = code


@dataclass(frozen=True)
class PersonRow:
    record_key: str
    person_key: str
    system: str
    client_id: str
    first: str
    last: str
    dob: str              # ISO YYYY-MM-DD or ""
    address_key: str      # "" when there's no address
    unit: str = ""
    zip5: str = ""
    program: str = ""


@dataclass(frozen=True)
class Evidence:
    code: str
    params: tuple = ()


@dataclass(frozen=True)
class AutoJoin:
    pair: tuple           # record keys for same_system_id, person keys for the other two
    reason: Literal["same_system_id", "four_exact_facts", "earlier_batch"]
    evidence: tuple = ()


@dataclass(frozen=True)
class Proposal:
    pair: tuple           # person keys, a < b
    score: int
    band: Literal["likely", "possible"]
    evidence: tuple
    cautions: tuple
    features: tuple
    found_via: tuple


@dataclass(frozen=True)
class PairVerdict:
    a: str
    b: str
    verdict: Literal["same", "different"]
    decision_id: str = ""
    reviewer: str = ""
    inherited: bool = False

    def __post_init__(self):
        if self.a > self.b:
            a, b = self.b, self.a
            object.__setattr__(self, "a", a)
            object.__setattr__(self, "b", b)

    @property
    def pair(self):
        return (self.a, self.b)

    def audit_fields(self, master_before, master_after):
        """ID-11: the decision ID, the reviewer, the verdict word and both master IDs, nothing else (C-21, H8)."""
        return {"decision_id": self.decision_id, "reviewer": self.reviewer, "verdict": self.verdict,
                "master_before": master_before, "master_after": master_after}


@dataclass(frozen=True)
class KnownMaster:
    master_id: str
    created_at: str
    linked_at: str
    how: Literal["derived", "same_system_id", "four_exact_facts", "reviewer"]


@dataclass(frozen=True)
class Score:
    points: int
    evidence: tuple
    cautions: tuple


@dataclass(frozen=True)
class IdentityResult:
    master_of: dict
    master_of_record: dict
    groups: dict
    auto_joins: tuple
    proposals: tuple
    settled: int
    low: int
    low_master_of: dict
    refused: tuple
    merged: tuple
    skipped_buckets: int
    released: tuple
    compared: frozenset | None = None


def master_id(person_key):
    return "M-" + hashlib.sha256(person_key.encode("utf-8")).hexdigest()[:10]


def load_settings(overrides=None):
    s = _copy.deepcopy(load("identity"))
    for section, values in (overrides or {}).items():
        s.setdefault(section, {}).update(values)
    return s


# Dates of birth

def _dob_parts(dob):
    if len(dob) == 10 and dob[4] == "-" and dob[7] == "-":
        return dob[:4], dob[5:7], dob[8:]
    return None


def _one_edit_apart(a, b):
    if len(a) != len(b) or a == b:
        return False
    diff = [i for i in range(len(a)) if a[i] != b[i]]
    if len(diff) == 1:
        return True
    return len(diff) == 2 and diff[1] == diff[0] + 1 and a[diff[0]] == b[diff[1]] and a[diff[1]] == b[diff[0]]


def compare_dob(a, b):
    """dob_exact, dob_swapped, dob_one_digit, dob_differs, or None when either is missing."""
    pa, pb = _dob_parts(a or ""), _dob_parts(b or "")
    if pa is None or pb is None:
        return None
    if pa == pb:
        return "dob_exact"
    if pa[0] == pb[0] and {pa[1], pa[2]} == {pb[1], pb[2]}:
        return "dob_swapped"
    if _one_edit_apart("".join(pa), "".join(pb)):
        return "dob_one_digit"
    return "dob_differs"


# Scoring (P-ID-2)

def score_from_codes(codes, weights):
    """The sum of weights over evidence codes, so a stored pair replays when a weight changes (M13)."""
    return sum(int(weights.get(WEIGHT_OF[c], 0)) for c in codes if c in WEIGHT_OF)


def score_pair(a, b, rare, weights):
    """Points, evidence and cautions for two person records' facts. rare adds rare_name (ID-10)."""
    ev = []
    d = compare_dob(a.dob, b.dob)
    if d:
        ev.append(d)
    la, lb = surname_tokens(a.last), surname_tokens(b.last)
    if la and lb:
        if la == lb:
            ev.append("surname_exact")
        elif la & lb:
            ev.append("surname_part")
    ga, gb = given_keys(a.first), given_keys(b.first)
    ha, hb = head(a.first), head(b.first)
    if ga and gb:
        if ha == hb:
            ev.append("given_exact")
        elif ga & gb:
            ev.append("given_nickname")
        elif (len(ha) == 1 or len(hb) == 1) and ha[:1] == hb[:1]:
            ev.append("given_initial")
    if (ga & lb or gb & la or (ha and ha in lb and hb in la)) and not (la & lb):
        ev.append("names_swapped")
    if a.address_key and a.address_key == b.address_key:
        ev.append("address_exact")
    elif a.zip5 and a.zip5 == b.zip5:
        ev.append("zip_only")
    if a.client_id.strip() and a.client_id.strip() == b.client_id.strip() and a.system.strip().lower() == b.system.strip().lower():
        ev.append("same_system_id_differs")
    if rare:
        ev.append("rare_name")
    cautions = [c for c in ev if c in CAUTION_CODES]
    if suffix_of(a.last) != suffix_of(b.last):
        cautions.append("suffix_differs")
    return Score(score_from_codes(ev, weights), tuple(ev), tuple(cautions))


def four_exact_facts(a, b):
    """P-ID-3: DOB, folded surname, folded given name and address key exact, unit equal when both have one, suffix equal."""
    if not (a.dob and a.last and a.first and a.address_key):
        return False
    return (a.dob == b.dob and surname_core(a.last) == surname_core(b.last) and fold(a.first) == fold(b.first)
            and a.address_key == b.address_key and not (a.unit and b.unit and fold(a.unit) != fold(b.unit))
            and suffix_of(a.last) == suffix_of(b.last))


# Blocking (P-ID-1)

def block_keys(r):
    """{key: family}. K1 surname+DOB, K2 surname+address, K3 given+DOB, K4 surname+given, each with a swapped-name form, plus
    id:<system>|<client_id>. K1 and K3 also match on birth year and on month and day."""
    out = {}
    parts = _dob_parts(r.dob)
    for first, last in ((r.first, r.last), (r.last, r.first)):
        ls, gs = surname_tokens(last), given_keys(first)
        for l in ls:
            if parts:
                out[f"K1:{l}|{r.dob}"] = "K1"
                out[f"K1y:{l}|{parts[0]}"] = "K1"
                out[f"K1md:{l}|{parts[1]}{parts[2]}"] = "K1"
            if r.address_key:
                out[f"K2:{l}|{r.address_key}"] = "K2"
            for g in gs:
                out[f"K4:{l}|{g}"] = "K4"
        for g in gs:
            if parts:
                out[f"K3:{g}|{r.dob}"] = "K3"
                out[f"K3y:{g}|{parts[0]}"] = "K3"
                out[f"K3md:{g}|{parts[1]}{parts[2]}"] = "K3"
    if r.client_id.strip():
        out[f"id:{r.system.strip().lower()}|{r.client_id.strip()}"] = "id"
    return out


class _Union:
    def __init__(self, keys, cannot):
        self.parent = {k: k for k in keys}
        self.members = {k: {k} for k in keys}
        self.cannot = cannot

    def find(self, x):
        while self.parent[x] != x:
            self.parent[x] = self.parent[self.parent[x]]
            x = self.parent[x]
        return x

    def blocked(self, a, b):
        ra, rb = self.find(a), self.find(b)
        small, other = (ra, rb) if len(self.members[ra]) <= len(self.members[rb]) else (rb, ra)
        return any(self.find(p) == other for m in self.members[small] for p in self.cannot.get(m, ()))

    def union(self, a, b):
        """True when joined or already together, False when a cannot-link refuses it."""
        ra, rb = self.find(a), self.find(b)
        if ra == rb:
            return True
        if self.blocked(a, b):
            return False
        if rb < ra:
            ra, rb = rb, ra
        self.parent[rb] = ra
        self.members[ra] |= self.members.pop(rb)
        return True

    def groups(self):
        out = {}
        for k in self.parent:
            out.setdefault(self.find(k), []).append(k)
        return {min(v): tuple(sorted(v)) for v in out.values()}

    def clone(self):
        u = _Union((), self.cannot)
        u.parent = dict(self.parent)
        u.members = {k: set(v) for k, v in self.members.items()}
        return u


def _records(rows):
    """Person key -> rows, with ID-0's checks and same_system_id joins."""
    by_key = {}
    for r in sorted(rows, key=lambda r: r.record_key):
        by_key.setdefault(r.person_key, []).append(r)
    joins = []
    for key, rs in sorted(by_key.items()):
        if len(rs) < 2:
            continue
        ids = {(r.system.strip().lower(), r.client_id.strip()) for r in rs}
        if len(ids) != 1 or not next(iter(ids))[1]:
            raise InconsistentInput("name_key_shared")
        for i, a in enumerate(rs):
            for b in rs[i + 1:]:
                if fold(a.last) != fold(b.last) or not same_given(a.first, b.first) or (a.dob and b.dob and a.dob != b.dob):
                    raise InconsistentInput("id_record_disagrees")
        for extra in rs[1:]:
            joins.append(AutoJoin((rs[0].record_key, extra.record_key), "same_system_id", (Evidence("same_system_id"),)))
    return by_key, joins


def _facts(rs):
    def filled(r):
        return sum(1 for v in (r.first, r.last, r.dob, r.address_key, r.zip5) if v)
    return sorted(rs, key=lambda r: (-filled(r), r.record_key))[0]


def _band(score, s):
    return "likely" if score >= s["bands"]["likely_min"] else "possible"


def resolve(rows, verdicts=(), known=None, settings=None, keep_compared=False, open_copy_groups=()):
    s = settings if settings and "weights" in settings else load_settings(settings)
    weights, bands, limits = s["weights"], s["bands"], s["limits"]
    known = dict(known or {})
    by_key, auto_joins = _records(rows)
    facts = {k: _facts(rs) for k, rs in by_key.items()}
    keys = sorted(facts)
    record_to_key = {r.record_key: r.person_key for r in rows}

    # Verdicts: a batch verdict beats an inherited one on the same pair (ID-6).
    effective = {}
    # Two verdicts of one kind on one pair that disagree: different wins, so a conflict never joins anyone.
    for v in sorted(verdicts, key=lambda v: (v.pair, v.inherited, v.verdict != "different", v.decision_id)):
        if v.a not in facts or v.b not in facts:
            continue
        cur = effective.get(v.pair)
        if cur is None or (cur.inherited and not v.inherited):
            effective[v.pair] = v
    cannot = {}
    for v in effective.values():
        if v.verdict == "different":
            cannot.setdefault(v.a, set()).add(v.b)
            cannot.setdefault(v.b, set()).add(v.a)
    u = _Union(keys, cannot)
    refused = []
    for pair, v in sorted(effective.items()):
        if v.verdict == "same" and not v.inherited and not u.union(v.a, v.b):
            refused.append(v)

    # Candidates.
    buckets = {}
    for k in keys:
        for bk, fam in block_keys(facts[k]).items():
            buckets.setdefault(bk, (fam, []))[1].append(k)
    skipped = 0
    shared = {}
    for bk, (fam, members) in sorted(buckets.items()):
        if len(members) < 2:
            continue
        if len(members) > limits["max_bucket"]:
            skipped += 1
            continue
        for i, a in enumerate(members):
            for b in members[i + 1:]:
                if a != b:
                    shared.setdefault((min(a, b), max(a, b)), []).append((fam, len(members)))
    copy_of = {}
    for i, grp in enumerate(open_copy_groups):
        for rk in grp:
            if rk in record_to_key:
                copy_of.setdefault(record_to_key[rk], set()).add(i)

    def same_copy_group(a, b):
        return bool(copy_of.get(a, set()) & copy_of.get(b, set()))

    scored = {}
    for pair, hits in sorted(shared.items()):
        fams = {f for f, _ in hits}
        only_k4 = fams == {"K4"}
        rare = only_k4 and min(n for _, n in hits) <= weights["rare_name_max_count"]
        if only_k4 and not rare:
            continue
        a, b = facts[pair[0]], facts[pair[1]]
        sc = score_pair(a, b, rare, weights)
        scored[pair] = (sc, tuple(sorted(fams)))

    # Automatic joins, in a fixed order: (reason, pair), each skipped if it would break a cannot-link.
    candidates = []
    for pair, (sc, _) in scored.items():
        if pair in effective or same_copy_group(*pair):
            continue
        if four_exact_facts(facts[pair[0]], facts[pair[1]]):
            candidates.append(("four_exact_facts", pair, sc.evidence))
    for pair, v in effective.items():
        if v.verdict == "same" and v.inherited:
            candidates.append(("earlier_batch", pair, ()))
    saved = {}
    for k in keys:
        if k in known:
            saved.setdefault(known[k].master_id, []).append(k)
    for mid, ks in saved.items():
        ks = sorted(ks, key=lambda k: (known[k].linked_at, k))
        for k in ks[1:]:
            if known[k].how == "reviewer" or known[ks[0]].how == "reviewer":
                pair = (min(ks[0], k), max(ks[0], k))
                if pair not in effective:
                    candidates.append(("earlier_batch", pair, ()))
    seen = set()
    for reason, pair, ev in sorted(set(candidates)):
        if (pair in seen) or u.find(pair[0]) == u.find(pair[1]):
            continue
        if u.union(*pair):
            seen.add(pair)
            auto_joins.append(AutoJoin(pair, reason, tuple(Evidence(c) for c in ev)))

    # Proposals (ID-4, ID-5, ID-13).
    proposals = []
    for pair, (sc, fams) in sorted(scored.items()):
        if pair in effective or same_copy_group(*pair) or u.find(pair[0]) == u.find(pair[1]):
            continue
        id_floor = "same_system_id_differs" in sc.evidence
        if sc.points < bands["possible_min"] and not id_floor:
            continue
        band = _band(sc.points, s) if sc.points >= bands["possible_min"] else "possible"
        feats = tuple(Evidence(c) for c in sc.evidence + tuple(c for c in sc.cautions if c not in sc.evidence))
        proposals.append(Proposal(pair, sc.points, band, tuple(Evidence(c) for c in sc.evidence),
                                  tuple(Evidence(c) for c in sc.cautions), feats, fams))
    proposals.sort(key=lambda p: (-p.score, p.pair))

    # Master IDs (ID-8).
    groups_by_root = u.groups()
    master_for_group, merged, released = {}, [], []
    claims = {}
    for root, members in groups_by_root.items():
        ids = sorted({known[k].master_id for k in members if k in known},
                     key=lambda m: (min(known[k].created_at for k in members if k in known and known[k].master_id == m), m))
        if not ids:
            master_for_group[root] = master_id(root)
            continue
        chosen = ids[0]
        merged += [(old, chosen) for old in ids[1:]]
        first_link = min((known[k].linked_at, k) for k in members if k in known and known[k].master_id == chosen)
        claims.setdefault(chosen, []).append((first_link, root))
    for mid, claimants in claims.items():
        claimants.sort()
        master_for_group[claimants[0][1]] = mid
        for _, root in claimants[1:]:
            master_for_group[root] = master_id(root)
            released += [(k, mid) for k in groups_by_root[root] if k in known and known[k].master_id == mid]
    master_of = {k: master_for_group[root] for root, members in groups_by_root.items() for k in members}
    groups = {master_for_group[root]: members for root, members in groups_by_root.items()}

    # The range (ID-9).
    low_u = u.clone()
    for p in proposals:
        low_u.union(*p.pair)
    for grp in open_copy_groups:
        ks = sorted({record_to_key[rk] for rk in grp if rk in record_to_key})
        for k in ks[1:]:
            low_u.union(ks[0], k)
    low_groups = low_u.groups()
    low_master_of = {k: master_of[root] for root, members in low_groups.items() for k in members}

    return IdentityResult(
        master_of=master_of,
        master_of_record={r.record_key: master_of[r.person_key] for r in rows},
        groups=groups,
        auto_joins=tuple(auto_joins),
        proposals=tuple(proposals),
        settled=len(groups_by_root),
        low=len(low_groups),
        low_master_of=low_master_of,
        refused=tuple(refused),
        merged=tuple(sorted(set(merged))),
        skipped_buckets=skipped,
        released=tuple(sorted(released)),
        compared=frozenset(scored) if keep_compared else None,
    )
