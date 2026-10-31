"""Copies inside one file, and one Client ID used for different people inside one system (SPEC 6.7, P-DUP).

Groups hold record keys and codes only. An open group keeps its rows counted and widens the range (P-VAL-3, SPEC 7.2); it
never makes a row not counted yet.
"""
import hashlib
from dataclasses import dataclass, field
from typing import Literal

from wholecount.engine.fold import fold
from wholecount.engine.names import same_given

SEP = "\x1f"
RULE_IDENTICAL, RULE_POSSIBLE, RULE_SAME_ID = "P-DUP-1", "P-DUP-2", "P-DUP-3"


@dataclass(frozen=True)
class CopyRow:
    record_key: str
    table_key: str
    system: str
    client_id: str
    first: str
    middle_initial: str
    last: str
    dob: str
    address_key: str
    program: str
    values: tuple = ()                    # every mapped field, standardized: ((field, value), ...)


@dataclass(frozen=True)
class TableInfo:
    has_dob_column: bool
    system: str = ""


@dataclass(frozen=True)
class CopyGroup:
    group_id: str
    kind: Literal["identical", "possible", "same_id_different"]
    rule_id: str
    members: tuple                        # record keys, sorted
    evidence: tuple = ()                  # codes only
    same_client_id: bool = False          # every member carries one system's one Client_ID


@dataclass(frozen=True)
class CopyRule:
    """The fields that must all agree for two rows in one table to group (P-DUP-2). Surname, given name and one of dob,
    address_key or client_id are required, so a name alone, or a name and ZIP, never groups (B-47)."""
    fields: tuple = ("surname", "given", "dob")

    def __post_init__(self):
        f = set(self.fields)
        if not {"surname", "given"} <= f or not f & {"dob", "address_key", "client_id"}:
            raise ValueError("a copy rule needs surname, given name and one of dob, address_key or client_id")


@dataclass(frozen=True)
class KeepOne:
    kept: str


@dataclass(frozen=True)
class NotCopies:
    pass


@dataclass(frozen=True)
class DifferentPeople:
    pass


@dataclass(frozen=True)
class ApprovedAsEntered:
    pass


ALLOWED = {"identical": (KeepOne,), "possible": (KeepOne, NotCopies), "same_id_different": (DifferentPeople, ApprovedAsEntered)}


class Unresolvable(Exception):
    def __init__(self, code):
        super().__init__(code)
        self.code = code


@dataclass(frozen=True)
class CopyOutcome:
    kept: tuple = ()                      # record keys still counted
    set_aside: tuple = ()                 # (record key, copy_of record key)
    counted: tuple = ()
    verdict_pairs: tuple = ()             # (record key, record key, "different"), a < b


def group_id(kind, members):
    """DUP-5: a new member changes the ID, so an old decision no longer matches (B-38)."""
    return hashlib.sha256(SEP.join([kind, *sorted(members)]).encode("utf-8")).hexdigest()[:12]


def _group(kind, rule_id, members, evidence=(), same_client_id=False):
    m = tuple(sorted(members))
    return CopyGroup(group_id(kind, m), kind, rule_id, m, tuple(evidence), same_client_id)


def _ids_agree(a, b):
    """DUP-3: surname, given name (nicknames allowed) and DOB (when both have one) agree."""
    if fold(a.last) != fold(b.last) or not same_given(a.first, b.first):
        return False
    return not (a.dob and b.dob and a.dob != b.dob)


def _same_id_groups(rows):
    by_id = {}
    for r in rows:
        if r.client_id.strip():
            by_id.setdefault((r.system.strip().lower(), r.client_id.strip()), []).append(r)
    groups, consistent = [], {}
    for key in sorted(by_id):
        rs = by_id[key]
        if len(rs) < 2:
            continue
        if all(_ids_agree(a, b) for i, a in enumerate(rs) for b in rs[i + 1:]):
            for r in rs:
                consistent[r.record_key] = key
            continue
        groups.append(_group("same_id_different", RULE_SAME_ID, [r.record_key for r in rs], ("same_system_id_differs",), True))
    return groups, consistent


def _matches(a, b, rule, has_dob):
    for f in rule.fields:
        if f == "surname" and (not fold(a.last) or fold(a.last) != fold(b.last)):
            return False
        if f == "given" and not same_given(a.first, b.first):
            return False
        if f == "dob":
            if has_dob:
                if not a.dob or a.dob != b.dob:
                    return False
            elif not a.address_key or a.address_key != b.address_key:
                return False
        if f == "address_key" and (not a.address_key or a.address_key != b.address_key):
            return False
        if f == "client_id" and (not a.client_id or a.client_id != b.client_id):
            return False
    return True


def find_copies(rows, tables, rule=None):
    """DUP-1 to DUP-3. tables maps table key to TableInfo. Rows set aside earlier are not passed in."""
    rule = rule or CopyRule()
    rows = sorted(rows, key=lambda r: r.record_key)
    groups, consistent = _same_id_groups(rows)
    in_id_group = {m for g in groups for m in g.members}
    by_table = {}
    for r in rows:
        if r.record_key not in in_id_group:
            by_table.setdefault(r.table_key, []).append(r)
    for tk in sorted(by_table):
        rs = by_table[tk]
        info = tables.get(tk, TableInfo(True))
        parent = {r.record_key: r.record_key for r in rs}
        programs = {r.record_key: ({r.program} if r.program.strip() else set()) for r in rs}

        def find(x):
            while parent[x] != x:
                parent[x] = parent[parent[x]]
                x = parent[x]
            return x

        for i, a in enumerate(rs):
            for b in rs[i + 1:]:
                if a.program.strip() and b.program.strip() and a.program != b.program:
                    continue
                if not (a.values == b.values or _matches(a, b, rule, info.has_dob_column)):
                    continue
                ra, rb = find(a.record_key), find(b.record_key)
                if ra == rb or len(programs[ra] | programs[rb]) > 1:
                    continue
                parent[rb] = ra
                programs[ra] |= programs.pop(rb)
        clusters = {}
        for r in rs:
            clusters.setdefault(find(r.record_key), []).append(r)
        for members in clusters.values():
            if len(members) < 2:
                continue
            identical = all(m.values == members[0].values for m in members)
            ids = {consistent.get(m.record_key) for m in members}
            same_client = len(ids) == 1 and None not in ids
            if identical:
                groups.append(_group("identical", RULE_IDENTICAL, [m.record_key for m in members], ("all_values_equal",),
                                     same_client))
            else:
                ev = ("names_equal", "dob_equal" if info.has_dob_column else "address_equal")
                groups.append(_group("possible", RULE_POSSIBLE, [m.record_key for m in members], ev, same_client))
    return sorted(groups, key=lambda g: (g.members[0], g.kind))


def split_group(record_keys):
    """A same_id_different group over rows that share a Client_ID-based key, so a same_system_id join can be split the DUP-7
    way: DifferentPeople with split_rows, then resolve again (ID-7)."""
    return _group("same_id_different", RULE_SAME_ID, record_keys, ("split_requested",), True)


def _pairs(members):
    return tuple((a, b, "different") for i, a in enumerate(members) for b in members[i + 1:])


def apply_copy_decision(group, decision):
    """DUP-4."""
    if not isinstance(decision, ALLOWED[group.kind]):
        raise Unresolvable("decision_not_allowed")
    if isinstance(decision, KeepOne):
        if decision.kept not in group.members:
            raise Unresolvable("kept_not_member")
        rest = tuple((m, decision.kept) for m in group.members if m != decision.kept)
        return CopyOutcome(kept=(decision.kept,), set_aside=rest, counted=(decision.kept,))
    if isinstance(decision, NotCopies):
        if group.same_client_id:
            raise Unresolvable("same_person_key")
        return CopyOutcome(kept=group.members, counted=group.members, verdict_pairs=_pairs(group.members))
    if isinstance(decision, DifferentPeople):
        return CopyOutcome(kept=group.members, counted=group.members, verdict_pairs=_pairs(group.members))
    return CopyOutcome(kept=group.members, counted=group.members)


def details_signature(row):
    """What a person key built without the Client_ID takes: system, folded given, folded surname, DOB, and the address key
    when there's no DOB (SPEC 5.1)."""
    return (row.system.strip().lower(), fold(row.first), fold(row.last), row.dob, "" if row.dob else row.address_key)


def key_modes(groups, decisions, split_rows=(), rows=()):
    """DUP-7. record key -> "details" or "row". A record key not in the result uses the default key.

    details: a decided same_id_different group's rows, keyed without the Client_ID. row: a key from the record key alone, for
    rows in split_rows whose details keys would still be equal, and for every counted row (in rows) with no Client_ID whose
    name-based key another counted row shares. rows are the counted rows, so a row set aside by KeepOne is not among them."""
    by_key = {r.record_key: r for r in rows}
    split = set(split_rows)
    modes = {}
    for g in groups:
        if g.kind != "same_id_different" or not isinstance(decisions.get(g.group_id), (DifferentPeople, ApprovedAsEntered)):
            continue
        sigs = {}
        for m in g.members:
            if m in by_key:
                sigs.setdefault(details_signature(by_key[m]), []).append(m)
        for m in g.members:
            modes[m] = "details"
            if m in split and m in by_key and len(sigs[details_signature(by_key[m])]) > 1:
                modes[m] = "row"
    shared = {}
    for r in rows:
        if not r.client_id.strip():
            shared.setdefault(details_signature(r), []).append(r.record_key)
    for members in shared.values():
        if len(members) > 1:
            for m in members:
                modes[m] = "row"
    return modes
