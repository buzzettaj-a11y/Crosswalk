"""What stages 06 to 09 read, one page at a time (M12 section 0). A widget never holds more than one page of rows.

Rows carry values for the screen only. Nothing here is written, logged or sent to a progress line (H8, H9).
"""
from dataclasses import dataclass, field

from wholecount import copy
from wholecount.engine.outputs import tables as out_tables
from wholecount.engine.review import finish_gate, people_in_other_files
from wholecount.engine.standardize.model import CountStatus

STATUS_TABS = ("open", "corrected", "approved", "set_aside")
_FIRST_LAST = ("First_Name", "Last_Name")


@dataclass(frozen=True)
class QueueFilter:
    status: str = "open"
    problem: str = ""                     # a reason ID, or "" for any
    source: str = ""                      # a file name, or "" for any
    search: str = ""                      # matched in memory, never saved or logged
    cause_id: str = ""                    # Send to row by row opens step 2 filtered to one cause


@dataclass(frozen=True)
class QueueRow:
    record_key: str
    name: str
    client_id: str
    address: str
    problems: str
    counted: bool
    location: str
    source: str
    row_number: int
    letter: str
    table_key: str


@dataclass(frozen=True)
class QueuePage:
    rows: tuple
    total: int
    status_counts: dict
    problem_counts: dict
    source_counts: dict
    page: int
    pages: int


def _name(row):
    return " ".join(v for v in (row.value("First_Name"), row.value("Last_Name")) if v)


def problem_title(rid):
    try:
        return out_tables.problem_title(rid)
    except KeyError:
        return rid


def _status_of(o):
    if o.set_aside_reason is not None:
        return "set_aside"
    if o.count_status == CountStatus.COUNTED_CORRECTED:
        return "corrected"
    if o.count_status == CountStatus.COUNTED_APPROVED:
        return "approved"
    if o.reasons:
        return "open"
    return ""


def _location_word(o):
    if o.location is None:
        return ""
    if o.location.kind == "mapped":
        return copy.get(f"status.confidence.{o.location.confidence}")
    return copy.get("status.confidence.not_placed")


def _order(r, rk, letter_of):
    return (letter_of.get(rk, ""), r.outcomes[rk].table_key, r.outcomes[rk].row_number, rk)


def _matches(session, rk, f, cause_keys):
    r = session.results
    o = r.outcomes[rk]
    if _status_of(o) != f.status:
        return False
    if f.problem and f.problem not in o.reasons:
        return False
    if f.source and r.file_of_record.get(rk) != f.source:
        return False
    if cause_keys is not None and rk not in cause_keys:
        return False
    if f.search:
        row = r.rows[rk]
        hay = " ".join((_name(row), row.value("Client_ID"), row.value("Address_1"), row.value("Zip"))).lower()
        if f.search.lower() not in hay:
            return False
    return True


def _letters(r):
    return {rk: w.table.letter for w in r.works for rk in (x.record_key for x in w.rows)}


def matching_keys(session, f):
    """The record keys a filter selects, resolved by the session when a command runs (H12)."""
    from wholecount.session.runner import causes_for

    r = session.results
    cause_keys = None
    if f.cause_id:
        c = next((c for c in causes_for(r) if c.cause_id == f.cause_id), None)
        cause_keys = set(c.record_keys) if c else set()
    letters = _letters(r)
    keys = [rk for rk in r.outcomes if _matches(session, rk, f, cause_keys)]
    return sorted(keys, key=lambda rk: _order(r, rk, letters))


def queue_page(session, f, page=0, size=50):
    r = session.results
    letters = _letters(r)
    keys = matching_keys(session, f)
    status_counts = {s: 0 for s in STATUS_TABS}
    problems, sources = {}, {}
    for rk, o in r.outcomes.items():
        st = _status_of(o)
        if st:
            status_counts[st] += 1
        if st == f.status:
            for rid in o.reasons:
                problems[rid] = problems.get(rid, 0) + 1
            fn = r.file_of_record.get(rk)
            sources[fn] = sources.get(fn, 0) + 1
    pages = max(1, -(-len(keys) // size))
    page = max(0, min(page, pages - 1))
    rows = []
    for rk in keys[page * size:(page + 1) * size]:
        row, o = r.rows[rk], r.outcomes[rk]
        rows.append(QueueRow(rk, _name(row), row.value("Client_ID"), row.value("Address_1"),
                             "; ".join(problem_title(x) for x in o.reasons), o.counted, _location_word(o),
                             r.file_of_record.get(rk, ""), o.row_number, letters.get(rk, ""), o.table_key))
    return QueuePage(tuple(rows), len(keys), status_counts, problems, sources, page, pages)


# Causes, the finish gate and the header counts (SPEC 8.1, 8.4)

@dataclass(frozen=True)
class CauseView:
    cause: object
    state: str                            # open, decided or settled
    covering: int


def cause_views(session):
    from wholecount.session.runner import causes_for

    r = session.results
    out = []
    for c in causes_for(r):
        if c.tab == "settled":
            state = "settled"
        elif c.routed or not any(r.outcomes[k].reasons or k in {m for g in r.open_groups for m in g.members}
                                 for k in c.record_keys):
            state = "decided"
        else:
            state = "open"
        out.append(CauseView(c, state, len(set(c.record_keys))))
    order = {"open": 0, "decided": 1, "settled": 2}
    return sorted(out, key=lambda v: (order[v.state], -v.cause.count, v.cause.cause_id))


def gate(session):
    r = session.results
    return finish_gate(list(r.outcomes.values()), r.open_groups, r.replay.routed)


def other_files_people(session):
    r = session.results
    counted = {k for k, o in r.outcomes.items() if o.counted}
    return people_in_other_files(r.identity.master_of_record, r.file_of_record, counted)


# Pairs, joins and people (SPEC 7.2, P-ID-2, P-ID-3)

def _person_rows(r, person_key):
    return sorted(k for k, p in r.person_of_record.items() if p == person_key)


def _sample(r, keys):
    row = r.rows[keys[0]]
    return {"source": f"{r.file_of_record[keys[0]]} {row.row_number}", "name": _name(row),
            "dob": row.value("Date_of_Birth"), "address": row.value("Address_1"), "zip": row.value("Zip"),
            "program": row.value("Program"), "id": row.value("Client_ID"), "record_key": keys[0]}


@dataclass(frozen=True)
class PairView:
    a: str
    b: str
    band: str
    rows: tuple                           # two dicts, screen only
    evidence: tuple                       # sentences
    cautions: tuple
    decided: str | None


def _evidence(items):
    out = []
    for e in items:
        try:
            out.append(copy.get(f"people.evidence.{e.code}", **dict(e.params)))
        except KeyError:
            out.append(e.code)
    return tuple(out)


def pairs_page(session, page=0, size=25):
    r = session.results
    verdicts = {}
    for d in session.decisions.of_kind("pair"):
        verdicts[tuple(sorted(d.person_keys))] = d.get("verdict")
    props = sorted(r.identity.proposals, key=lambda p: (p.band != "likely", -p.score, p.pair))
    decided = [((a, b), v) for (a, b), v in verdicts.items()]
    items = [(p.pair, p) for p in props] + [(k, None) for k, _ in decided if k not in {p.pair for p in props}]
    pages = max(1, -(-len(items) // size))
    out = []
    for pair, p in items[page * size:(page + 1) * size]:
        a_rows, b_rows = _person_rows(r, pair[0]), _person_rows(r, pair[1])
        if not a_rows or not b_rows:
            continue
        out.append(PairView(pair[0], pair[1], p.band if p else "", (_sample(r, a_rows), _sample(r, b_rows)),
                            _evidence(p.evidence) if p else (), _evidence(p.cautions) if p else (),
                            verdicts.get(tuple(sorted(pair)))))
    return tuple(out), len(items), pages


@dataclass(frozen=True)
class JoinView:
    master_id: str
    name: str
    records: int
    reason: str
    persons: tuple


def joins(session, reason="", search=""):
    r = session.results
    out = []
    for j in r.identity.auto_joins:
        if reason and j.reason != reason:
            continue
        if j.reason == "same_system_id":
            persons = (r.person_of_record.get(j.pair[0]), r.person_of_record.get(j.pair[1]))
            keys = list(j.pair)
        else:
            persons = j.pair
            keys = [k for k, p in r.person_of_record.items() if p in j.pair]
        if not keys or keys[0] not in r.rows:
            continue
        m = r.identity.master_of_record.get(keys[0], "")
        name = _name(r.rows[keys[0]])
        if search and search.lower() not in name.lower():
            continue
        out.append(JoinView(m, name, len(keys), j.reason, tuple(p for p in persons if p)))
    return tuple(sorted(out, key=lambda j: j.master_id))


def people_page(session, page=0, size=100, search=""):
    r = session.results
    by_master = {}
    for rk, m in r.identity.master_of_record.items():
        if r.outcomes[rk].counted:
            by_master.setdefault(m, []).append(rk)
    items = []
    for m in sorted(by_master):
        ks = sorted(by_master[m])
        name = _name(r.rows[ks[0]])
        if search and search.lower() not in name.lower():
            continue
        progs = sorted({r.program_of_record.get(k, "") for k in ks} - {""})
        items.append((m, name, progs))
    pages = max(1, -(-len(items) // size))
    return tuple(items[page * size:(page + 1) * size]), len(items), pages


# The export plan (SPEC 9.1): what Download would write, from the same view the writer uses

@dataclass(frozen=True)
class PlannedFile:
    file_id: object
    name: str
    fmt: str
    rows: int
    cols: int
    fixed_format: bool


@dataclass
class ExportPlan:
    files: tuple
    columns: tuple                        # every Final_Clean_Mapped column the output schema has
    columns_on: tuple
    balance: dict = field(default_factory=dict)


def export_plan(session, settings):
    """What Download would write. Building it means building every output table, so the last plan is reused while the
    results, the download settings, the log and the reviewer are the same (M15: the stage drew it twice per visit)."""
    key = (session.results, repr(settings), len(session.audit_log), session.reviewer)
    cached = getattr(session, "_plan_cache", None)
    if cached is not None and cached[0][0] is key[0] and cached[0][1:] == key[1:]:
        return cached[1]
    plan = _export_plan(session, settings)
    session._plan_cache = (key, plan)
    return plan


def _export_plan(session, settings):
    from dataclasses import replace

    from wholecount.engine.outputs import writer
    from wholecount.engine.outputs.columns import LOG_FILES, FileId, chip_columns, output_columns
    from wholecount.session import export

    view = export.build_view(session, settings)
    files = []
    for fid in writer.files_to_write(view, settings):
        if fid in LOG_FILES:
            rows, cols = len(view.events), 1
        else:
            rows, cols = len(writer.table_rows(fid, view, settings)), len(chip_columns(fid, view, settings))
        fixed = fid in LOG_FILES or fid == FileId.DATA_QUALITY_REPORT
        files.append(PlannedFile(fid, writer.file_name(fid, view, settings), writer.file_format(fid, settings),
                                 rows, cols, fixed))
    all_cols = output_columns(FileId.FINAL_CLEAN_MAPPED, view, replace(settings, columns_off={}))
    on = chip_columns(FileId.FINAL_CLEAN_MAPPED, view, settings)
    c = view.counts
    return ExportPlan(tuple(files), tuple(all_cols), tuple(on),
                      {"counted": c.counted, "not_counted_yet": c.not_counted_yet, "set_aside": c.set_aside,
                       "received": c.received})


def diagnosis(session, cause):
    """M08's diagnose_mapping for one cause: a matching problem, not a data problem. Names and counts only."""
    from wholecount.engine.review import diagnose_mapping

    r = session.results
    keys = set(cause.record_keys)
    for w in r.works:
        index = {rk: (w.table.key, i) for i, rk in enumerate(w.table.record_keys)}
        if keys <= set(index):
            return diagnose_mapping(cause, w.mapping, list(w.profiles), index)
    return None


def keep_one_plan(session, keys):
    """M08's exact plan for Keep one of each person in each program: (kept, set aside) counts (C-16)."""
    from wholecount.engine.review import keep_one_per_program

    r = session.results
    res = keep_one_per_program(tuple(sorted(keys)), r.open_groups, {k: r.rows[k].value("Program") for k in keys if k in r.rows})
    return len(res.kept), len(res.set_aside)


def unmatched_columns(session, record_key):
    """(column name, value) for every column of this row's table that no field is matched to. Screen only (H10)."""
    r = session.results
    for w in r.works:
        if record_key in w.table.record_keys:
            i = w.table.record_keys.index(record_key)
            mapped = {a.column.name for a in w.mapping.assignments}
            row = w.table.rows[i]
            return [(h, row[j] if j < len(row) else "") for j, h in enumerate(w.table.headers) if h not in mapped]
    return []


def sharing_identifier(session, record_key):
    r = session.results
    cid = r.rows[record_key].value("Client_ID")
    if not cid:
        return []
    sys_ = r.system_of_record.get(record_key)
    return sorted(k for k, row in r.rows.items() if k != record_key and row.value("Client_ID") == cid
                  and r.system_of_record.get(k) == sys_)


def source_path(session, record_key):
    import pathlib

    name = session.results.file_of_record.get(record_key)
    return next((p for p in session.setup.paths() if pathlib.Path(p).name == name), None)
