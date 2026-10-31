"""Reading the crosswalk into a batch and writing a batch back (M13 XW-4 to XW-8).

Reading gives M06 its KnownMaster per person key and the inherited pair verdicts, and M07 its inherited program decisions. A
batch decision always beats an inherited one, and M06 and M07 already apply that. Writing happens once, after a download.
"""
from dataclasses import dataclass, field

from wholecount.engine.identity import KnownMaster, PairVerdict
from wholecount.engine.programs import ProgramDecision


def load_known(store, person_keys):
    """person key -> KnownMaster for every key the crosswalk has seen, merged masters followed to the final one."""
    return {pk: KnownMaster(k.master_id, k.created_at, k.linked_at, k.how) for pk, k in store.keys(person_keys).items()}


def inherited_verdicts(store, person_keys):
    """A PairVerdict(inherited=True) for each saved pair whose two person keys are both in this batch."""
    return [PairVerdict(v.key_a, v.key_b, v.verdict, "XW-" + v.decided_at, v.decided_by, inherited=True)
            for v in store.verdicts_among(person_keys)]


def saved_verdicts(store, person_keys):
    return store.verdicts_among(person_keys)


def inherited_programs(store, names):
    """ProgramDecision(inherited=True) for each saved group with at least one name in this batch."""
    names = set(names)
    return [ProgramDecision(g.kind, g.members, g.label, inherited=True) for g in store.program_groups()
            if set(g.members) & names]


@dataclass(frozen=True)
class CommitView:
    """What a download committed: counted rows' person keys and their masters, and this batch's own decisions."""
    batch_id: str
    master_of: dict                 # person key -> master ID, counted rows only
    how_of: dict                    # person key -> derived, same_system_id, four_exact_facts or reviewer
    merged: tuple = ()              # (old master, winning master)
    verdicts: tuple = ()            # (key a, key b, verdict, reviewer, second reviewer, decided at), batch decisions only
    programs: tuple = ()            # (kind, label, members, reviewer, decided at), batch decisions only
    keep_saved: frozenset = field(default_factory=frozenset)   # keys whose saved link lapsed on new evidence: left as saved


@dataclass(frozen=True)
class CommitPlan:
    batch_id: str
    reviewer: str
    time: str
    new_people: tuple
    merged: tuple
    keys: tuple                     # (person key, master, how)
    verdicts: tuple
    programs: tuple


@dataclass(frozen=True)
class CommitCounts:
    people: int
    person_keys: int
    pair_verdicts: int
    program_groups: int
    merged: int


def plan_commit(store, view, reviewer, time):
    saved = store.keys(view.master_of)
    existing = store.first_batches(set(view.master_of.values()))
    new_people = sorted({m for m in view.master_of.values() if m not in existing})
    keys = []
    for pk in sorted(view.master_of):
        if pk in view.keep_saved:
            continue
        master, how = view.master_of[pk], view.how_of.get(pk, "derived")
        cur = saved.get(pk)
        if cur is not None and cur.master_id == master:
            continue
        keys.append((pk, master, how))
    merged = tuple(sorted({(o, n) for o, n in view.merged if o != n}))
    return CommitPlan(view.batch_id, reviewer, time, tuple(new_people), merged, tuple(keys), tuple(view.verdicts),
                      tuple(view.programs))


def commit(store, view, reviewer, time):
    """One transaction (XW-6). Returns the counts for the CROSSWALK_UPDATED audit line."""
    plan = plan_commit(store, view, reviewer, time)
    store.write(plan)
    return CommitCounts(len(plan.new_people), len(plan.keys), len(plan.verdicts), len(plan.programs), len(plan.merged))
