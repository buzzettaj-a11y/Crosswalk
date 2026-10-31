"""The pipeline steps of SPEC 6.10, each a pure function of its inputs and the decisions that apply to it.

Steps 1 and 2 (read, choose tables) need the install secret for record keys, so the session runner does them and hands the
tables in. Everything here takes plain data. The adapters between earlier milestones' types are the small functions marked
"adapter"; the report lists them.
"""
import re
from dataclasses import dataclass, field, replace

from wholecount.engine import reasons as registry
from wholecount.engine.addresskey import address_key, split_house_street
from wholecount.engine.copies import CopyRow, TableInfo, find_copies
from wholecount.engine.dateorder import collect_evidence, decide
from wholecount.engine.fold import fold
from wholecount.engine.geo.fill import propose_fills
from wholecount.engine.geo.place import outcome_for
from wholecount.engine.identity import PersonRow
from wholecount.engine.mapping import auto_map, profile_columns
from wholecount.engine.prepare.steps import apply_steps, propose_steps
from wholecount.engine.programs import TableProgram, build_program_map, canonical_program, program_sources, propose_groups
from wholecount.engine.review import base_outcome
from wholecount.engine.standardize.dates import date_context
from wholecount.engine.standardize.inputs import build_inputs
from wholecount.engine.standardize.model import location_for
from wholecount.engine.standardize.rows import TableOptions, standardize_row, standardize_table

ISO = re.compile(r"\d{4}-\d{2}-\d{2}")


@dataclass
class TableWork:
    """One included table as it moves through steps 3 to 5."""
    table: object                         # LoadedTable
    system: str
    file_name: str
    prepared: object = None
    mapping: object = None
    profiles: tuple = ()
    contexts: dict = field(default_factory=dict)
    inputs: list = field(default_factory=list)
    rows: list = field(default_factory=list)


# Steps 3 to 5: tidy up, map, standardize

def prepare(work, schema, steps=None):
    """Step 2b (P-PREP): the proposed steps, or the set-up's steps for this table."""
    t = work.table
    chosen = propose_steps(t, auto_map(schema, profile_columns(t), t.key)) if steps is None else steps
    work.prepared = apply_steps(t, chosen)
    return work


def map_table(work, schema, overrides=()):
    """Step 3 (P-MAP): the automatic mapping, then the operator's choices. overrides: ((field, column name or ""), ...)."""
    t, prep = work.table, work.prepared
    work.profiles = tuple(profile_columns(t, prep.column_refs()))
    m = auto_map(schema, list(work.profiles), t.key)
    by_name = {p.column.name: p.column for p in work.profiles}
    for fld, col in overrides:
        m = m.with_choice(fld, by_name[col]) if col in by_name else m.without(fld)
    work.mapping = m
    return work


def standardize(work, schema, defaults, today, date_setting=None):
    """Steps 4 and 5 (P-STD, P-VAL)."""
    t, prep, m = work.table, work.prepared, work.mapping
    dob = m.column_for("Date_of_Birth")
    if dob is not None:
        meta = {} if dob.derived else {i: x for (i, c), x in t.meta.items() if c == dob.index}
        work.contexts["Date_of_Birth"] = date_context(decide(collect_evidence(prep.values(dob.name), meta)), date_setting)
    work.inputs = build_inputs(prep, m, defaults, schema)
    work.rows = standardize_table(work.inputs, schema, TableOptions(work.contexts), today)
    return work


def restandardize(row_input, values, schema, contexts, today):
    """Re-run P-STD and P-VAL on one row with new field text (an accepted fill or a correction)."""
    v = dict(row_input.values)
    v.update(values)
    return standardize_row(replace(row_input, values=v), schema, TableOptions(contexts), today)


# Step 6: place addresses

def fill_proposals(rows, backend, reference=None):
    """record key -> [FillProposal] for rows with an open location reason (P-GEO-9)."""
    out = {}
    for r in rows:
        if r.set_aside_reason:
            continue
        if any(registry.get(x.reason_id).flag == "location" for x in r.reasons if registry.get(x.reason_id).severity == "decision"):
            props = propose_fills(r, backend, reference)
            if props:
                out[r.record_key] = props
    return out


def located(outcome, row, placement):
    """Adapter: M04's LocationStatus and M05's GeoResult into the outcome (P-VAL-1)."""
    if outcome.set_aside_reason:
        return outcome
    return replace(outcome, location=outcome_for(location_for(row), placement.get(row.record_key),
                                                 filled=any(f.kind == "zip" for f in row.fills)))


def base_outcomes(rows, placement, same_id_rows):
    return {r.record_key: located(base_outcome(r, same_id_rows), r, placement) for r in rows}


# Step 7: copies

def copy_rows(works):
    """Adapter: standardized rows into M06 CopyRows. Set-aside rows (summary rows) are not passed in."""
    out, tables = [], {}
    for w in works:
        tables[w.table.key] = TableInfo(w.mapping.column_for("Date_of_Birth") is not None, w.system)
        for r in w.rows:
            if r.set_aside_reason:
                continue
            out.append(copy_row(r, w.system))
    return out, tables


def copy_row(r, system):
    house, street = split_house_street(r.value("Address_1"))
    akey = address_key(house, street, r.value("Zip")) if house else ""
    values = tuple(sorted((k, v.value) for k, v in r.values.items()))
    return CopyRow(r.record_key, r.table_key, system, r.value("Client_ID"), r.value("First_Name"), r.value("Middle_Initial"),
                   r.value("Last_Name"), _iso(r), akey, r.value("Program"), values)


def _iso(r):
    v = r.value("Date_of_Birth")
    if not ISO.fullmatch(v) or any(x.field == "Date_of_Birth" for x in r.reasons):
        return ""
    return v


def dob_valid(r):
    return bool(_iso(r))


# Step 9: identity

def person_row(r, system, person_key):
    """Adapter: a standardized row into an M06 PersonRow."""
    c = copy_row(r, system)
    return PersonRow(r.record_key, person_key, system, c.client_id, c.first, c.last, c.dob, c.address_key,
                     r.value("Address_2"), r.value("Zip"), r.value("Program"))


def person_key_for(keyer, c, mode):
    """The person key M06's key_modes calls for: row, details, or the default (Client_ID when there is one)."""
    if mode == "row":
        return keyer(system="row", client_id=c.record_key)
    if c.client_id.strip() and mode != "details":
        return keyer(system=c.system, client_id=c.client_id)
    return keyer(system=c.system, given=fold(c.first), surname=fold(c.last), dob=c.dob or None, address_key=c.address_key)


# Step 10: programs

def table_programs(works, counted_rows, program_overrides=None):
    """Adapter: each table's program source (P-PROG-1). A mapped Program column wins; otherwise a per-source default fills
    the field in M04, which reads as a default here."""
    out = []
    overrides = dict(program_overrides or {})
    for w in works:
        rows = [r for r in w.rows if r.record_key in counted_rows]
        counts = {}
        for r in rows:
            v = r.value("Program")
            counts[v] = counts.get(v, 0) + 1
        mode = overrides.get(w.table.key)
        col = w.mapping.column_for("Program")
        if mode == "none" or (col is None and not any(counts.get(k) for k in counts if k)):
            out.append(TableProgram(w.table.key, "none", None, None, len(rows)))
        elif col is not None:
            out.append(TableProgram(w.table.key, "column", col.name, None, len(rows), tuple(sorted(counts.items()))))
        else:
            name = next((k for k in sorted(counts) if k), None)
            out.append(TableProgram(w.table.key, "default", None, name, len(rows)))
    return out


def programs_step(works, counted_rows, decisions, overrides=None):
    tables = table_programs(works, counted_rows, overrides)
    names, missing = program_sources(tables)
    proposals = propose_groups(names)
    pm = build_program_map(names, proposals, decisions, missing)
    program_of = {}
    for w in works:
        for r in w.rows:
            if r.record_key in counted_rows:
                v = r.value("Program")
                program_of[r.record_key] = canonical_program(v, pm) if v.strip() else ""
    return names, proposals, pm, program_of


def copies_step(works):
    rows, tables = copy_rows(works)
    return find_copies(rows, tables), rows
