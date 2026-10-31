"""Row outcomes and review (SPEC 6.5, 8.1, 8.4). Rows are addressed by record key, never by position (H12).

A row counts on its person data alone (P-VAL-2). An open copy group keeps its rows counted and widens the range (P-VAL-3);
an open same-ID conflict holds them. Location and soft reasons never change the count status.
"""
from dataclasses import dataclass, replace
from typing import Literal

from wholecount.engine import reasons as registry
from wholecount.engine.mapping import better_column
from wholecount.engine.standardize.model import CountStatus

COUNTED = (CountStatus.COUNTED_PASSED, CountStatus.COUNTED_APPROVED, CountStatus.COUNTED_CORRECTED)
SAME_ID = "same_id_conflict"
COPY_CAUSE = {"identical": "copies_identical", "possible": "copies_possible"}
TABS = ("counts", "location", "look")
TAB_OF_FLAG = {"holds_count": "counts", "location": "location", "soft": "look"}
ACTIONS = {
    "holds_count": ("approve", "accept_group", "set_aside", "route"),
    "location": ("accept_fills", "approve", "set_aside", "route"),
    "soft": ("accept_group", "set_aside", "route"),
    "copies_identical": ("keep_one", "keep_one_per_program"),
    "copies_possible": ("keep_one", "not_copies", "keep_one_per_program"),
    SAME_ID: ("different_people", "approved_as_entered"),
}
TITLE = {"copies_identical": "copies.cause.identical", "copies_possible": "copies.cause.possible",
         SAME_ID: "copies.cause.same_id_different"}


@dataclass(frozen=True)
class RowOutcome:
    record_key: str
    table_key: str
    row_number: int
    count_status: CountStatus
    location: object = None               # LocationOutcome, counted rows only
    reasons: tuple = ()                   # open reason IDs
    set_aside_reason: str | None = None
    kept_record_key: str | None = None
    reason_fields: tuple = ()             # (reason ID, field) for the open reasons

    @property
    def counted(self):
        return self.count_status in COUNTED


@dataclass(frozen=True)
class Cause:
    cause_id: str
    count: int
    title_key: str
    actions: tuple
    routed: bool
    tab: Literal["counts", "location", "look", "settled"]
    kind: str
    record_keys: tuple
    field: str | None = None


@dataclass(frozen=True)
class FinishGate:
    held: bool
    left: tuple                           # (cause ID, rows) still holding Finish review
    open_rows: int                        # not-counted-yet rows still open


@dataclass(frozen=True)
class KeepOneResult:
    kept: tuple
    set_aside: tuple                      # (record key, kept record key)
    left_alone: tuple


@dataclass(frozen=True)
class MappingDiagnosis:
    table_key: str
    field: str
    column_now: str
    column_better: str
    rows_fixed: int


def flag_of(reason_id):
    if reason_id == SAME_ID:
        return "holds_count"
    return registry.get(reason_id).flag


def status_for(reasons, set_aside_reason=None, approved=False, corrected=False):
    """P-VAL-2: set aside, else not counted yet while a holds_count reason is open, else counted."""
    if set_aside_reason:
        return CountStatus.SET_ASIDE
    if any(flag_of(r) == "holds_count" for r in reasons):
        return CountStatus.NOT_COUNTED_YET
    if corrected:
        return CountStatus.COUNTED_CORRECTED
    if approved:
        return CountStatus.COUNTED_APPROVED
    return CountStatus.COUNTED_PASSED


def base_outcome(row, same_id_rows=frozenset()):
    """The outcome of a standardized row before any decision. Open reasons are the decision reasons M04 raised."""
    refs = [r for r in row.reasons if registry.get(r.reason_id).severity == "decision"]
    reasons = tuple(dict.fromkeys(r.reason_id for r in refs))
    fields = tuple(dict.fromkeys((r.reason_id, r.field) for r in refs))
    if row.record_key in same_id_rows:
        reasons += (SAME_ID,)
    return RowOutcome(row.record_key, row.table_key, row.row_number, status_for(reasons, row.set_aside_reason), None,
                      reasons, row.set_aside_reason, None, fields)


def close_reasons(outcome, which=None, approved=False, corrected=False):
    """Close the given reasons (all of them when which is None) and recompute the count status."""
    keep = () if which is None else tuple(r for r in outcome.reasons if r not in which)
    fields = tuple(rf for rf in outcome.reason_fields if rf[0] in keep)
    return replace(outcome, reasons=keep, reason_fields=fields,
                   count_status=status_for(keep, outcome.set_aside_reason, approved, corrected))


def set_aside(outcome, reason, kept=None):
    return replace(outcome, count_status=CountStatus.SET_ASIDE, set_aside_reason=reason, kept_record_key=kept, location=None)


def causes(outcomes, open_groups=(), routed=frozenset(), fillable=frozenset(), no_address=frozenset()):
    """REV-2. Open rows grouped by reason into the three tabs, largest first, ties by cause ID."""
    by_cause, fields = {}, {}
    for o in outcomes:
        if o.set_aside_reason == "summary_row":
            by_cause.setdefault("summary_row", []).append(o.record_key)
            continue
        if o.count_status == CountStatus.SET_ASIDE:
            continue
        for r in o.reasons:
            by_cause.setdefault(r, []).append(o.record_key)
        for r, f in o.reason_fields:
            fields.setdefault(r, set()).add(f)
    for g in open_groups:
        if g.kind in COPY_CAUSE:
            by_cause.setdefault(COPY_CAUSE[g.kind], []).extend(g.members)
    out = []
    for cid, keys in by_cause.items():
        keys = tuple(sorted(set(keys)))
        if cid == "summary_row":
            out.append(Cause(cid, len(keys), "set_aside.summary_row", (), False, "settled", "settled", keys))
            continue
        if cid in COPY_CAUSE.values():
            tab, kind, actions, title = "counts", "copies", ACTIONS[cid], TITLE[cid]
        elif cid == SAME_ID:
            tab, kind, actions, title = "counts", "same_id", ACTIONS[cid], TITLE[cid]
        else:
            flag = flag_of(cid)
            tab, actions, title = TAB_OF_FLAG[flag], ACTIONS[flag], f"problems.{cid}.title"
            if flag == "location" and keys and set(keys) <= set(no_address):
                kind = "no_address"
            elif flag == "location" and set(keys) & set(fillable):
                kind = "fill_from_street"
            else:
                kind = "other"
        f = fields.get(cid)
        out.append(Cause(cid, len(keys), title, actions, cid in routed, tab, kind, keys, next(iter(f)) if f and len(f) == 1 else None))
    order = {t: i for i, t in enumerate(TABS + ("settled",))}
    return sorted(out, key=lambda c: (order[c.tab], -c.count, c.cause_id))


def open_rows(cause_list):
    """Rows with at least one open cause, counted once."""
    return len({k for c in cause_list if c.tab != "settled" for k in c.record_keys})


def finish_gate(outcomes, open_groups=(), routed=frozenset()):
    """REV-5 (8.4): held while an Affects the counts cause has open rows and isn't routed."""
    left = tuple((c.cause_id, c.count) for c in causes(outcomes, open_groups, routed)
                 if c.tab == "counts" and c.count and not c.routed)
    n = sum(1 for o in outcomes if o.count_status == CountStatus.NOT_COUNTED_YET)
    return FinishGate(bool(left), left, 0 if left else n)


def keep_one_per_program(selection, open_groups, programs):
    """REV-3: in each open identical or possible group, per program, keep the smallest record key among the selected members
    and set the rest aside. Nothing outside a copy group is touched."""
    selection = set(selection)
    kept, aside, touched = [], [], set()
    for g in sorted(open_groups, key=lambda g: g.members):
        if g.kind not in COPY_CAUSE:
            continue
        chosen = [m for m in g.members if m in selection]
        by_prog = {}
        for m in chosen:
            by_prog.setdefault(programs.get(m) or "", []).append(m)
        for prog, ms in sorted(by_prog.items()):
            ms = sorted(ms)
            kept.append(ms[0])
            aside += [(m, ms[0]) for m in ms[1:]]
        touched.update(chosen)
    return KeepOneResult(tuple(sorted(kept)), tuple(sorted(aside)), tuple(sorted(selection - touched)))


def diagnose_mapping(cause, table_mapping, profiles, row_index):
    """A cause whose rows all come from one table, whose field is blank on them, while another column is filled on all of
    them. row_index maps record key -> (table key, row index). Names and counts only."""
    if cause.field is None or not cause.record_keys:
        return None
    places = {row_index.get(k) for k in cause.record_keys}
    if None in places or len({t for t, _ in places}) != 1:
        return None
    table_key = next(iter(places))[0]
    idx = sorted(i for _, i in places)
    current_ref = table_mapping.column_for(cause.field)
    by_col = {p.column: p for p in profiles}
    current = by_col.get(current_ref)
    if current is None or any(current.filled_mask[i] for i in idx):
        return None
    taken = {a.column for a in table_mapping.assignments} - {current_ref}
    filled_here = {p.column for p in profiles if all(p.filled_mask[i] for i in idx)}
    better = better_column(cause.field, current, profiles, filled_here, taken)
    if better is None:
        return None
    return MappingDiagnosis(table_key, cause.field, current_ref.name, better.name, len(idx))


def people_in_other_files(master_of_record, file_of_record, counted):
    """Master IDs whose counted records come from two or more source files (the cross-file note)."""
    files = {}
    for rk in counted:
        m = master_of_record.get(rk)
        if m is not None:
            files.setdefault(m, set()).add(file_of_record.get(rk))
    return sum(1 for fs in files.values() if len(fs) > 1)
