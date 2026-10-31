"""Decisions (SPEC 5.2, 8.7, H12). Keyed by record key, or by person key for a pair. A decision never stores a cell value.

Decisions replay after every run. One that no longer fits lapses with a reason code and stays in the store, so it applies
again if its records come back. Nothing is dropped silently.
"""
import hashlib
from dataclasses import dataclass, field, replace
from typing import Literal

from wholecount.engine import copies as dup
from wholecount.engine.review import SAME_ID, close_reasons, set_aside, status_for

KINDS = ("approve", "set_aside", "accept_fill", "keep_one", "not_copies", "different_people", "approved_as_entered", "pair",
         "program", "correction", "route")
LAPSE_REASONS = ("record_gone", "person_gone", "basis_changed", "group_changed", "file_removed", "names_gone", "row_set_aside",
                 "dob_now_differs")
SEP = "\x1f"


@dataclass(frozen=True)
class Decision:
    decision_id: str
    kind: Literal["approve", "set_aside", "accept_fill", "keep_one", "not_copies", "different_people", "approved_as_entered",
                  "pair", "program", "correction", "route"]
    record_keys: tuple
    person_keys: tuple
    basis: str
    made_at: str
    reviewer: str
    second_reviewer: str | None = None
    detail: tuple = ()

    def get(self, name, default=None):
        return next((v for k, v in self.detail if k == name), default)

    def all(self, name):
        return tuple(v for k, v in self.detail if k == name)


@dataclass(frozen=True)
class NoLongerApply:
    decision: Decision
    reason: str


def decision_id(kind, record_keys, basis, person_keys=()):
    msg = SEP.join([kind, *sorted(record_keys), *sorted(person_keys), basis]).encode("utf-8")
    return "D-" + hashlib.sha256(msg).hexdigest()[:10]


def make(kind, record_keys, basis, made_at, reviewer, person_keys=(), second=None, detail=()):
    if kind not in KINDS:
        raise ValueError(kind)
    rks, pks = tuple(sorted(record_keys)), tuple(sorted(person_keys))
    return Decision(decision_id(kind, rks, basis, pks), kind, rks, pks, basis, made_at, reviewer, second, tuple(detail))


class DecisionStore:
    def __init__(self, decisions=()):
        self._items = list(decisions)

    def __iter__(self):
        return iter(self._items)

    def __len__(self):
        return len(self._items)

    def snapshot(self):
        return tuple(self._items)

    def ids(self):
        return {d.decision_id for d in self._items}

    def add(self, decisions):
        have = self.ids()
        new = [d for d in decisions if d.decision_id not in have]
        self._items.extend(new)
        return new

    def remove(self, decisions):
        ids = {d.decision_id for d in decisions}
        self._items = [d for d in self._items if d.decision_id not in ids]

    def of_kind(self, *kinds):
        return [d for d in self._items if d.kind in kinds]

    def touching(self, record_keys):
        rks = set(record_keys)
        return [d for d in self._items if rks & set(d.record_keys)]


@dataclass
class ReplayResult:
    outcomes: dict
    no_longer_apply: list = field(default_factory=list)
    verdict_pairs: list = field(default_factory=list)        # (record key, record key, decision)
    copy_decisions: dict = field(default_factory=dict)       # group id -> M06 decision
    split_rows: set = field(default_factory=set)
    routed: set = field(default_factory=set)
    applied: set = field(default_factory=set)
    filled: dict = field(default_factory=dict)               # record key -> fill proposals accepted
    corrections: dict = field(default_factory=dict)          # record key -> {field: text}, memory only


def _order(decisions):
    return sorted(decisions, key=lambda d: (d.made_at, d.decision_id))


def replay(store, outcomes, groups, fills, correction_texts):
    """Step 8: apply review decisions to the row outcomes. Pair and program decisions apply in their own steps.

    fills: record key -> [FillProposal] as the geo step found them. correction_texts: decision ID -> {record key: {field:
    text}} held in memory for the session."""
    out = dict(outcomes)
    res = ReplayResult(out)
    by_id = {g.group_id: g for g in groups}

    def lapse(d, reason):
        res.no_longer_apply.append(NoLongerApply(d, reason))

    for d in _order(store):
        if d.kind in ("pair", "program"):
            continue
        if d.kind == "route":
            res.routed.add(d.basis)
            res.applied.add(d.decision_id)
            continue
        if d.kind in ("keep_one", "not_copies", "different_people", "approved_as_entered"):
            g = by_id.get(d.basis)
            if g is None:
                lapse(d, "group_changed" if any(k in out for k in d.record_keys) else "record_gone")
                continue
            if d.kind == "keep_one":
                kept = set(d.all("kept"))
                aside_of = dict(x.split(">", 1) for x in d.all("aside_of"))
                for m in g.members:
                    if m not in kept:
                        out[m] = set_aside(out[m], "copy_of", aside_of.get(m, min(kept)))
                res.copy_decisions[g.group_id] = dup.KeepOne(min(kept))
            elif d.kind == "not_copies":
                res.copy_decisions[g.group_id] = dup.NotCopies()
                res.verdict_pairs += [(a, b, d) for a, b, _ in dup.apply_copy_decision(g, dup.NotCopies()).verdict_pairs]
            else:
                choice = dup.DifferentPeople() if d.kind == "different_people" else dup.ApprovedAsEntered()
                res.copy_decisions[g.group_id] = choice
                for m in g.members:
                    out[m] = close_reasons(out[m], {SAME_ID}, approved=True)
                if d.kind == "different_people":
                    res.verdict_pairs += [(a, b, d) for a, b, _ in dup.apply_copy_decision(g, choice).verdict_pairs]
                    res.split_rows.update(d.all("split"))
            res.applied.add(d.decision_id)
            continue
        present = [k for k in d.record_keys if k in out]
        if not present:
            lapse(d, "record_gone")
            continue
        live = [k for k in present if out[k].set_aside_reason is None or d.kind == "set_aside"]
        if not live:
            lapse(d, "row_set_aside")
            continue
        if d.kind == "approve":
            # An open same-ID conflict closes only by its own decision (different people, or approved as entered).
            closable = lambda o: tuple(r for r in o.reasons if r != SAME_ID)  # noqa: E731
            hit = [k for k in live if (closable(out[k]) if d.basis == "*" else d.basis in closable(out[k]))]
            if not hit:
                lapse(d, "basis_changed")
                continue
            for k in hit:
                which = set(closable(out[k])) if d.basis == "*" else {d.basis}
                out[k] = close_reasons(out[k], which, approved=True)
        elif d.kind == "set_aside":
            for k in live:
                if out[k].set_aside_reason is None:
                    out[k] = set_aside(out[k], d.basis)
        elif d.kind == "accept_fill":
            k = live[0]
            props = [p for p in fills.get(k, ()) if p.basis in d.all("fill")]
            if not props or len(props) != len(d.all("fill")):
                lapse(d, "basis_changed")
                continue
            res.filled[k] = props
        elif d.kind == "correction":
            texts = correction_texts.get(d.decision_id)
            if texts is None:
                lapse(d, "file_removed")
                continue
            for k in live:
                if k in texts:
                    res.corrections[k] = texts[k]
        res.applied.add(d.decision_id)
    return res


def reapply_status(outcome, approved=False, corrected=False):
    return replace(outcome, count_status=status_for(outcome.reasons, outcome.set_aside_reason, approved, corrected))
