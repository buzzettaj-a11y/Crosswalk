"""Building the OutputView and writing the files through the download gate (SPEC 9, OUT-13).

This is the only place that turns session state into output data. Values that need the install secret (moved points, the
review file's run ID and signatures, the shareable log's keyed hashes) are made here through InstallSecret.mac and reach
the engine finished.
"""
import tomllib
from importlib import resources

from wholecount.engine.addresskey import address_key, split_house_street
from wholecount.engine.confidence import master_match_confidence
from wholecount.engine.geo.mapdata import MapEntry, MapPointEntry, build_map_points
from wholecount.engine.geo.place import building_key, to_query
from wholecount.engine.geo.types import Districts
from wholecount.engine.outputs import writer
from wholecount.engine.outputs.audit_entry import entry
from wholecount.engine.outputs.review_file import row_signature, run_id, share_key
from wholecount.engine.outputs.view import ExportSettings, OutputView, OutRow, TableSummary
from wholecount.engine.standardize.model import audit_events
from wholecount.session.reviewer import decisions_by_reviewer


class DownloadHeld(Exception):
    def __init__(self, reasons):
        super().__init__(", ".join(reasons))
        self.reasons = tuple(reasons)


def _problem_ids():
    return tuple(tomllib.loads(resources.files("wholecount.copy").joinpath("problems.toml").read_text(encoding="utf-8")))


def mapped_fields(session, results):
    """Fields with a column in some included table, or a default for one, in schema order (H10)."""
    have = set()
    for w in results.works:
        for a in w.mapping.assignments:
            have.add(a.field)
    for (fn, idx, f), _ in session.setup.items("defaults"):
        have.add(f)
    return tuple(f.key for f in session.schema().enabled_fields() if f.key in have)


def _sheet(w):
    return w.table.sheet if w.file_name.lower().endswith((".xlsx", ".xlsm")) else None


def build_events(session, results):
    """Every log event, in time order (AUD-2): files and tables, notes for fills and defaults, decisions one line per record
    key, the commands' own entries, distinct automatic joins, and the run."""
    t0 = session.audit_log[0][0] if session.audit_log else session.now_iso()
    events = []
    load = results.load
    for o in load.files if load else ():
        if o.status == "ok":
            events.append((t0, entry("FILE_ADDED", letter=o.letter, file_name=o.name, fingerprint=o.fingerprint)))
    for w in results.works:
        events.append((t0, entry("TABLE_INCLUDED", table_key=w.table.key, letter=w.table.letter, count=len(w.rows))))
    for rk in sorted(results.rows):
        for ev in audit_events(results.rows[rk]):
            code = "DEFAULT_USED" if ev.reason_id == "default_used" else (
                "FILL" if "filled" in ev.reason_id else "STANDARDIZED")
            if code == "DEFAULT_USED":
                events.append((t0, entry(code, record_key=rk, field_name=ev.field, rule_id=ev.rule_id)))
            else:
                events.append((t0, entry(code, record_key=rk, field_name=ev.field, rule_id=ev.rule_id, reason_code=ev.reason_id)))
    masters = results.identity.master_of_record
    for d in sorted(session.decisions, key=lambda d: (d.made_at, d.decision_id)):
        common = {"reviewer": d.reviewer or None, "second_reviewer": d.second_reviewer}
        if d.kind == "pair":
            ms = sorted({results.identity.master_of.get(k) for k in d.person_keys} - {None})
            events.append((d.made_at, entry("PAIR_VERDICT", decision_id=d.decision_id, master_id=ms or None,
                                            reason_code=d.get("verdict"), **common)))
        elif d.kind == "program":
            events.append((d.made_at, entry("PROGRAM", decision_id=d.decision_id, program_name=list(d.all("program")),
                                            reason_code=d.get("program_kind"), **common)))
        elif d.kind == "accept_fill":
            for rk in d.record_keys:
                for f in d.all("field"):
                    events.append((d.made_at, entry("FILL", record_key=rk, field_name=f, rule_id="P-GEO-9",
                                                    reason_code="fill_accepted", decision_id=d.decision_id, **common)))
        elif d.kind != "correction":
            for rk in d.record_keys or ("",):
                events.append((d.made_at, entry("DECISION", decision_id=d.decision_id, record_key=rk or None,
                                                reason_code=d.kind if d.kind != "set_aside" else d.basis, **common)))
    translate = {"ACCEPT_GROUP": "BULK_ACCEPT", "CORRECTION": "CORRECTION", "UNDO": "UNDO", "REVIEWER": "REVIEWER_SET",
                 "LOW_CONFIDENCE_ACKNOWLEDGED": "CONFIDENCE_ACK", "FINISH_REVIEW": "FINISH_REVIEW", "SETUP_CHANGE": "SETUP_CHANGE",
                 "RESUME": "RESUME"}
    from wholecount.engine.outputs.audit_text import EVENT_SLOTS
    for t, e in session.audit_log:
        code = translate.get(e.code)
        if code is None:
            continue
        allowed = EVENT_SLOTS[code]
        fields = {}
        for slot, v in e.fields:
            if slot in allowed:
                fields.setdefault(slot, []).append(v)
        if code == "CONFIDENCE_ACK":
            fields["reason_code"] = ["low_confidence"]
        events.append((t, entry(code, **fields)))
    seen = set()
    for j in results.identity.auto_joins:
        if j.reason == "same_system_id":
            ms = (masters.get(j.pair[0]), masters.get(j.pair[1]))
        else:
            ms = (results.identity.master_of.get(j.pair[0]), results.identity.master_of.get(j.pair[1]))
        key = (j.reason, ms)
        if key in seen:
            continue
        seen.add(key)
        events.append((t0, entry("AUTO_JOIN", reason_code=j.reason, master_id=sorted({m for m in ms if m}))))
    events.append((session.now_iso(), entry("RUN", backend_name=results.backend, release=results.release or None,
                                            reason_code="privacy_offset_applied",
                                            count=[results.kept, results.lapsed])))
    return tuple(sorted(events, key=lambda te: te[0]))


def build_view(session, settings=None):
    settings = settings or ExportSettings()
    r = session.results
    session.counts()
    mac = session.secret.mac
    rid = run_id(mac, [w.table.key for w in r.works])
    groups_of = {}
    for g in r.groups:
        for m in g.members:
            groups_of.setdefault(m, []).append(g)
    open_kind = {m: g.kind for g in r.open_groups for m in g.members}
    fields = mapped_fields(session, r)
    rows = []
    for w in r.works:
        for std in w.rows:
            rk = std.record_key
            o = r.outcomes[rk]
            res = r.placements.get(rk)
            loc = None if o.location is None else (o.location.kind, o.location.confidence, o.location.reason, o.location.filled)
            dist = None
            if res is not None and res.placed and res.districts is not None:
                dist = (res.districts.senate, res.districts.assembly, res.districts.council)
            point = (res.latitude, res.longitude) if res is not None and res.placed else None
            others = sorted({m for g in groups_of.get(rk, ()) for m in g.members} - {rk})
            house, street = split_house_street(std.value("Address_1"))
            rows.append(OutRow(
                record_key=rk, table_key=w.table.key, letter=w.table.letter, file_name=w.file_name, sheet=_sheet(w),
                row_number=std.row_number, system=w.system, count_status=o.count_status.value, location=loc,
                values=tuple((f, std.value(f)) for f in fields), originals=tuple((f, v.entered) for f, v in std.values.items()),
                reasons=o.reasons, reason_fields=o.reason_fields, set_aside_reason=o.set_aside_reason,
                kept_record_key=o.kept_record_key, in_copy_group=bool(groups_of.get(rk)), copy_others=tuple(others),
                open_copy_kind=open_kind.get(rk) if o.set_aside_reason is None else None,
                master_id=r.identity.master_of_record.get(rk) if o.counted else None,
                program=r.program_of_record.get(rk, "") if o.counted else "", districts=dist, point=point,
                address_key=address_key(house, street, std.value("Zip")) if house else "",
                signature=row_signature(mac, rid, rk)))
    by_key = {x.record_key: x for x in rows}
    order = {x.record_key: i for i, x in enumerate(rows)}
    masters = {}
    for rk, m in r.identity.master_of_record.items():
        if by_key[rk].counted:
            masters.setdefault(m, []).append(rk)
    master_rows = tuple((m, tuple(sorted(ks, key=order.get)), master_match_confidence(m, r.identity))
                        for m, ks in sorted(masters.items()))
    tables, numbers = [], {}
    files = {o.name: o for o in (r.load.files if r.load else ()) if o.status == "ok"}
    for w in r.works:
        numbers[w.table.letter] = numbers.get(w.table.letter, 0) + 1
        rf = files[w.file_name].read_file if w.file_name in files else None
        tables.append(TableSummary(w.table.key, w.table.letter, w.file_name, _sheet(w), numbers[w.table.letter],
                                   (rf.encoding or "") if rf else "", sum((rf.clean_counts or {}).values()) if rf else 0))
    system_of_letter = {w.table.letter: w.system for w in r.works}
    sources = tuple((o.letter, o.name, system_of_letter.get(o.letter, o.name)) for o in files.values())
    practice = r.practice
    entries, points = [], []
    if not practice:
        for m, ks, _ in master_rows:
            rs = [by_key[k] for k in ks]
            for prog in sorted({x.program for x in rs if x.program}):
                held = [x for x in rs if x.program == prog and x.districts is not None]
                if held:
                    best = sorted(held, key=lambda x: (-sum(1 for f in fields if x.value(f)), x.record_key))[0]
                    entries.append(MapEntry(m, prog, Districts(*best.districts), None))
        if settings.map_points:
            pe = []
            for m, ks, _ in master_rows:
                rs = [by_key[k] for k in ks if by_key[k].point is not None]
                for prog in sorted({x.program for x in rs if x.program}):
                    held = [x for x in rs if x.program == prog]
                    best = sorted(held, key=lambda x: (-sum(1 for f in fields if x.value(f)), x.record_key))[0]
                    res = r.placements[best.record_key]
                    key = building_key(to_query(r.rows[best.record_key]), res, r.rows[best.record_key].value("Zip"))
                    pe.append(MapPointEntry(prog, key, res.latitude, res.longitude))
            points = build_map_points(pe, mac)
    return OutputView(
        practice=practice, backend=r.backend, release=r.release, offset_applied=not practice, fields=fields, rows=tuple(rows),
        masters=master_rows, tables=tuple(tables), sources=sources, counts=r.counts, balance=r.balance, confidence=r.confidence,
        map_entries=tuple(entries), map_points=tuple(points), run_id=rid, events=build_events(session, r),
        share_keys={x.record_key: share_key(mac, x.record_key) for x in rows},
        reviewer_counts=decisions_by_reviewer(session.decisions), problem_ids=_problem_ids())


def download(session, folder, settings=None, clock=None, confirmed_synced=False, overwrite=False, environ=None):
    """OUT-13: the gate first, then the engine writer. Returns the Receipt and logs the DOWNLOAD entry."""
    settings = settings or ExportSettings()
    gate = session.download_gate()
    if gate.held:
        raise DownloadHeld(gate.reasons)
    view = build_view(session, settings)
    receipt = writer.write_outputs(view, folder, settings, clock or session.clock, confirmed_synced, overwrite, environ)
    import pathlib
    session.log(entry("DOWNLOAD", file_name=[pathlib.Path(f.path).name for f in receipt.files], count=len(receipt.files),
                      reviewer=session.reviewer or None))
    return receipt


def save_summary(session, path, include_file_names=False, overwrite=False):
    """The printable page as HTML (SUM-1). M12 draws the PDF from the same SummaryDoc."""
    from wholecount.engine.outputs.summary_doc import build_summary, render_summary_html

    gate = session.download_gate()
    if "stale" in gate.reasons or "balance_failed" in gate.reasons:
        raise DownloadHeld(gate.reasons)
    doc = build_summary(build_view(session), include_file_names)
    return writer.write_text(path, render_summary_html(doc), overwrite)
