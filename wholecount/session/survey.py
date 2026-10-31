"""The survey: what stages 01 to 05 show before Process (SPEC 11.5). Files, tables, the rows accounted for, the steps,
the mapping with its column checks and blocks, the date questions and the program names. It runs the engine's own steps
(read, find tables, tidy, match, standardize) on the set-up as it stands, and is cached by the fingerprints it depends on.

Nothing here is written to disk, and nothing here decides anything.
"""
import dataclasses
from dataclasses import dataclass, field

from wholecount.engine import pipeline as pl
from wholecount.engine.dateorder import collect_evidence, decide, suggest_pivot
from wholecount.engine.mapping import auto_map, check_mapping, process_blocks, profile_columns
from wholecount.engine.prepare.steps import propose_steps
from wholecount.engine.progress import NullSink
from wholecount.engine.read.sensitive import sensitive_name
from wholecount.session import runner


@dataclass(frozen=True)
class FileFacts:
    name: str
    letter: str | None
    status: str                           # ok, unreadable or duplicate_file
    reason_id: str | None
    encoding: str | None
    encoding_samples: tuple               # up to five, on screen only (P-READ-2)
    sensitive: tuple                      # (column name, "name" or "values")
    accounting: object
    in_tables: int = 0
    in_excluded: int = 0
    not_tables: int = 0
    above_header: int = 0
    header_rows: int = 0
    total: int = 0

    @property
    def balanced(self):
        return self.in_tables + self.in_excluded + self.not_tables + self.above_header + self.header_rows == self.total


@dataclass(frozen=True)
class TableFacts:
    key: str
    letter: str
    file_name: str
    idx: int
    sheet: str | None
    location: str
    rows: int
    columns: int
    filled_pct: int
    kind: str
    kind_reason: str
    included: bool
    header_row: int
    header_is_virtual: bool
    suggested_header_row: int | None
    header_warning: str | None
    dob_present: bool
    continuation_blocks: int
    headers: tuple

    @property
    def name(self):
        return (self.file_name, self.idx)


@dataclass
class Survey:
    files: tuple
    tables: tuple
    works: dict                           # table key -> TableWork (prepared, mapped, checked, standardized)
    steps: dict                           # table key -> the steps that run (proposed or the set-up's)
    proposed_steps: dict                  # table key -> what the tool proposes
    blocks: tuple
    dates: dict                           # (table key, field) -> (DateEvidence, DateDecision, DateFieldSetting or None)
    pivots: dict                          # (table key, field) -> suggested pivot or None
    program_names: tuple = ()
    program_proposals: tuple = ()
    program_map: object = None
    program_tables: tuple = ()
    systems: dict = field(default_factory=dict)   # letter -> system name
    loaded: dict = field(default_factory=dict)    # table key -> LoadedTable, every table, for Show data

    def table(self, key):
        return next(t for t in self.tables if t.key == key)

    def work(self, key):
        return self.works.get(key)


def _col_letter(n):
    s = ""
    while n:
        n, r = divmod(n - 1, 26)
        s = chr(65 + r) + s
    return s or "A"


def _location(t):
    if not t.blocks:
        return ""
    b = t.blocks[0].block
    span = f"{_col_letter(b.c0 + 1)}{b.r0 + 1}:{_col_letter(b.c1 + 1)}{b.r1 + 1}" if hasattr(b, "c0") else ""
    return f"{t.sheet} {span}".strip() if t.sheet else span


def _filled(t):
    cells = len(t.rows) * max(1, len(t.headers))
    filled = sum(1 for r in t.rows for c in r if str(c).strip())
    return int(round(100 * filled / cells)) if cells else 0


def _table_facts(t, name, idx):
    return TableFacts(
        key=t.key, letter=t.letter, file_name=name, idx=idx, sheet=t.sheet, location=_location(t), rows=len(t.rows),
        columns=len(t.headers), filled_pct=_filled(t), kind=t.kind, kind_reason=t.kind_reason, included=t.included,
        header_row=t.header_row, header_is_virtual=t.header_is_virtual, suggested_header_row=t.suggested_header_row,
        header_warning=t.header_warning,
        dob_present=any("birth" in h.lower() or h.lower() in ("dob", "d.o.b.") for h in t.headers),
        continuation_blocks=sum(1 for b in t.blocks[1:] if getattr(b, "continuation", False)), headers=tuple(t.headers))


def _file_facts(o, tables):
    rf = o.read_file
    mine = [t for t in tables if t.letter == o.letter]
    sens = []
    for t in mine:
        for c in t.sensitive_dropped:
            sens.append((c, "name" if sensitive_name(c) else "values"))
    a = o.accounting
    in_tables = sum(t.included_row_count for t in mine)
    return FileFacts(
        name=o.name, letter=o.letter, status=o.status, reason_id=o.reason_id,
        encoding=rf.encoding if rf else None, encoding_samples=tuple((rf.encoding_samples or [])[:5]) if rf else (),
        sensitive=tuple(sens), accounting=a, in_tables=in_tables, in_excluded=sum(t.excluded_row_count for t in mine),
        not_tables=a.non_table if a else 0, above_header=sum(t.above_header_rows for t in mine),
        header_rows=sum(1 for t in mine if t.header_row and not t.header_is_virtual),
        total=(a.non_empty_rows + a.shared_rows) if a else 0)


def _key(session):
    """The survey's own inputs only. A review decision changes none of them, so it never re-reads or re-checks a file."""
    own = session.own_inputs()
    from wholecount.session.crosswalk import fingerprint

    return (tuple(own[n] for n in ("sources", "tables", "steps", "mappings", "standardized", "programs")),
            repr(sorted(session.keep_sensitive)), session.backend.name, fingerprint(session))


def survey(session, sink=None):
    """The survey for the set-up as it stands. Cached until a set-up change makes it stale."""
    k = _key(session)
    if session._survey_cache is not None and session._survey_cache[0] == k:
        return session._survey_cache[1]
    sink = sink or NullSink()
    load = runner._load(session, sink)
    tables, file_of = runner._tables(session, load)
    files = tuple(_file_facts(o, tables) for o in load.files)
    facts = tuple(_table_facts(t, *file_of[t.key]) for t in tables)
    works_list = runner._works(session, load, tables, file_of, sink)
    schema = session.schema()
    works, steps, proposed, dates, pivots = {}, {}, {}, {}, {}
    for w in works_list:
        w.mapping = check_mapping(schema, w.mapping, list(w.profiles))
        works[w.table.key] = w
        name, idx = file_of[w.table.key]
        chosen = session.setup.get("steps", (name, idx))
        proposed[w.table.key] = tuple(propose_steps(w.table, auto_map(schema, profile_columns(w.table), w.table.key)))
        steps[w.table.key] = tuple(chosen) if chosen is not None else proposed[w.table.key]
        for fld in schema.enabled_fields():
            if getattr(fld, "type", None) != "date" and fld.key != "Date_of_Birth":
                continue
            col = w.mapping.column_for(fld.key)
            if col is None:
                continue
            values = w.prepared.values(col.name)
            answer = session.setup.get("date_orders", (name, idx, fld.key))
            order = getattr(answer, "order", None)
            ev = collect_evidence(values)
            dates[(w.table.key, fld.key)] = (ev, decide(ev, order.value if order else None), answer)
            pivots[(w.table.key, fld.key)] = suggest_pivot(fld.key, session.today())
    from wholecount.engine.defaults import SourceDefault

    defaults = tuple(SourceDefault(k, f, v) for (fn, i, f), v in session.setup.items("defaults")
                     for k, nm in file_of.items() if nm == (fn, i))
    blocks = tuple(b for w in works_list for b in process_blocks(schema, {w.table.key: w.mapping}, defaults,
                                                                  {w.table.key: tuple(w.profiles)}))
    all_rows = {r.record_key for w in works_list for r in w.rows}
    decisions = [runner.program_decision(d) for d in sorted(session.decisions.of_kind("program"),
                                                             key=lambda d: (d.made_at, d.decision_id))]
    overrides = {}
    for (name, idx), v in session.setup.items("program_columns"):
        tk = next((k for k, f in file_of.items() if f == (name, idx)), None)
        if tk:
            overrides[tk] = v
    from wholecount.session.crosswalk import inherited_program_decisions

    decisions += inherited_program_decisions(session, {r.value("Program") for w in works_list for r in w.rows})
    names, proposals, pm, _ = pl.programs_step(works_list, all_rows, decisions, overrides)
    s = Survey(files=files, tables=facts, works=works, steps=steps, proposed_steps=proposed, blocks=blocks, dates=dates,
               pivots=pivots, program_names=tuple(names), program_proposals=tuple(proposals), program_map=pm,
               program_tables=tuple(pl.table_programs(works_list, all_rows, overrides)),
               systems=runner.system_names(session, load), loaded={t.key: t for t in tables})
    session._survey_cache = (k, s)
    return s


def preview_step(session, table_key, step):
    """M03's apply_steps with only this step on this table: its counts and amber reason, for the dry-run sentence."""
    from wholecount.engine.prepare.steps import apply_steps

    sv = survey(session)
    w = sv.work(table_key)
    prepared = apply_steps(w.table, [dataclasses.replace(step, removed=False)])
    return prepared.results[0] if prepared.results else None
