"""One function per output file, each returning rows as plain dicts keyed by column (SPEC 9.1, OUT-2 to OUT-9).

Rows sort by normalized file name, sheet, row number, then record key; person tables by Master_ID, then program (C-27).
Unmapped columns never appear (H10). Words come from the copy registry.
"""
import re
import tomllib
from importlib import resources

from wholecount import copy
from wholecount.engine.geo.mapdata import build_map_counts, small_cell_max
from wholecount.engine.outputs.columns import ADDRESS_FIELDS, DISTRICT_COLUMNS, NAME_FIELDS, PRACTICE_COLUMN

SEP = "; "
_PUNCT = re.compile(r"[\W_]+", re.UNICODE)


def normalize_file_name(name):
    """The sort key for a file name, as SPEC 5.1 normalizes it: lowercase, no folder, punctuation runs to one underscore."""
    base = re.split(r"[\\/]", name)[-1]
    return _PUNCT.sub("_", base.lower()).strip("_")


def source_file(row):
    """The file name as added, with no folder, plus " / " and the sheet for a workbook sheet."""
    return f"{row.file_name} / {row.sheet}" if row.sheet else row.file_name


def row_order(row):
    return (normalize_file_name(row.file_name), row.sheet or "", row.row_number, row.record_key)


def yes_no(flag):
    return copy.get("common.yes") if flag else copy.get("common.no")


def count_status_text(row):
    return copy.get(f"status.count.{row.count_status}")


def _problem_titles(row, flag):
    from wholecount.engine import reasons as registry

    titles = []
    for rid in row.reasons:
        try:
            if registry.get(rid).flag == flag:
                titles.append(problem_title(rid))
        except KeyError:
            continue
    return titles


def problem_title(rid):
    return _problems()[rid]["title"]


def _problems():
    global _PROBLEMS
    if _PROBLEMS is None:
        _PROBLEMS = tomllib.loads(resources.files("wholecount.copy").joinpath("problems.toml").read_text(encoding="utf-8"))
    return _PROBLEMS


_PROBLEMS = None


def location_status_text(row):
    if row.location is None:
        return ""
    kind, conf, reason, filled = row.location
    if kind == "mapped":
        return copy.get("status.location.filled") if filled else copy.get(f"location.mapped_{conf}")
    words = copy.get(f"status.location.reason.{reason}")
    if reason == "address_problem":
        titles = _problem_titles(row, "location")
        if titles:
            words = f"{words}: {SEP.join(titles)}"
    return copy.get("status.location.not_mapped", reason=words)


def location_confidence_text(row):
    if row.location is None:
        return ""
    kind, conf, _, _ = row.location
    return copy.get(f"status.confidence.{conf}") if kind == "mapped" else copy.get("status.confidence.not_placed")


def _fmt(x):
    return f"{x:.6f}"


def final_clean_mapped(view, settings):
    out = []
    for r in sorted((r for r in view.rows if r.counted), key=row_order):
        d = {f: r.value(f) for f in view.fields}
        d["Count_Status"] = count_status_text(r)
        d["Location_Status"] = location_status_text(r)
        d["Location_Confidence"] = location_confidence_text(r)
        if not view.practice:
            dist = r.districts or (None, None, None)
            d.update({c: v or "" for c, v in zip(DISTRICT_COLUMNS, dist)})
        if settings.exact_coordinates:
            d["Latitude"], d["Longitude"] = (_fmt(r.point[0]), _fmt(r.point[1])) if r.point else ("", "")
        d.update({"Source_File": source_file(r), "Source_Row": str(r.row_number), "Record_Key": r.record_key,
                  "Duplicate_In_File": yes_no(r.in_copy_group), "Possible_Duplicate_Of": SEP.join(sorted(r.copy_others))})
        out.append(d)
    return out


def _filled(r, fields):
    return sum(1 for f in fields if r.value(f).strip())


def most_complete(rows, fields):
    """The record with the most non-blank mapped fields, ties by the smallest record key. Fields are never blended."""
    return sorted(rows, key=lambda r: (-_filled(r, fields), r.record_key))[0]


def source_records(rows):
    return SEP.join(f"{r.letter} :: {source_file(r)} :: {r.row_number}" for r in sorted(rows, key=row_order))


def _by_master(view):
    by_key = {r.record_key: r for r in view.rows}
    return [(m, [by_key[k] for k in keys], conf) for m, keys, conf in view.masters]


def unique_clients(view, settings):
    person = [f for f in NAME_FIELDS + ADDRESS_FIELDS if f in view.fields]
    dob = ["Date_of_Birth"] if "Date_of_Birth" in view.fields else []
    systems = {letter: name for letter, _, name in view.sources}
    out = []
    for master, rows, conf in sorted(_by_master(view)):
        best = most_complete(rows, view.fields)
        d = {"Master_ID": master}
        d.update({f: best.value(f) for f in person + dob})
        d["Programs"] = SEP.join(sorted({r.program for r in rows if r.program}))
        d["Systems"] = SEP.join(sorted({systems.get(r.letter, r.system) for r in rows}))
        d["Source_Records"] = source_records(rows)
        d["Match_Confidence"] = copy.get(f"people.match.{conf}")
        out.append(d)
    return out


def unique_clients_by_program(view, settings):
    out = []
    for master, rows, _ in sorted(_by_master(view)):
        for prog in sorted({r.program for r in rows if r.program}):
            out.append({"Master_ID": master, "Program": prog, "Source_Records": source_records([r for r in rows if r.program == prog])})
    return out


def set_aside_reason_text(code):
    if code in ("summary_row", "copy_of"):
        return copy.get(f"set_aside.title.{code}")
    labels = tomllib.loads(resources.files("wholecount.copy").joinpath("reasons.toml").read_text(encoding="utf-8"))
    return labels["set_aside"][code]["label"]


def set_aside_records(view, settings):
    return [{"Record_Key": r.record_key, "Source_File": source_file(r), "Source_Row": str(r.row_number),
             "Reason": set_aside_reason_text(r.set_aside_reason), "Kept_Record_Key": r.kept_record_key or ""}
            for r in sorted((r for r in view.rows if r.set_aside_reason), key=row_order)]


def map_counts(view, settings):
    blank = copy.get("map.fewer_than", limit=small_cell_max() + 1)
    return [{"Program": m.program, "District_Type": m.district_type, "District": m.district,
             "Count": blank if m.count is None else str(m.count)}
            for m in build_map_counts(view.map_entries, small_cell_max())]


def map_points(view, settings):
    return [{"Program": p.program, "Latitude": _fmt(p.latitude), "Longitude": _fmt(p.longitude)} for p in view.map_points]


def data_quality_report(view, settings):
    by_table = {t.table_key: t for t in view.tables}
    rows_of = {}
    for r in view.rows:
        rows_of.setdefault(r.table_key, []).append(r)
    out = []
    for b in view.balance.tables:
        t = by_table[b.table_key]
        rs = rows_of.get(b.table_key, [])
        d = {"Source_File": source_file_of(t), "Table": f"{t.letter}.{t.number}", "Rows_Received": str(b.received),
             "Counted": str(b.counted), "Not_Counted_Yet": str(b.not_counted_yet), "Set_Aside": str(b.set_aside),
             "Mapped": str(b.mapped), "Counted_Not_Mapped": str(b.counted_not_mapped)}
        for p in view.problem_ids:
            d[f"Problem_{p}"] = str(sum(1 for r in rs if p in r.reasons and r.set_aside_reason is None))
        d["Invisible_Characters_Removed"] = str(t.invisible_removed)
        d["Encoding"] = t.encoding
        out.append(d)
    return sorted(out, key=lambda d: (normalize_file_name(d["Source_File"]), d["Table"]))


def source_file_of(t):
    return f"{t.file_name} / {t.sheet}" if t.sheet else t.file_name


BUILDERS = {
    "Final_Clean_Mapped": final_clean_mapped, "Unique_Clients": unique_clients,
    "Unique_Clients_By_Program": unique_clients_by_program, "Set_Aside_Records": set_aside_records, "Map_Counts": map_counts,
    "Map_Points": map_points, "Data_Quality_Report": data_quality_report,
}


def with_practice(view, rows):
    if not view.practice:
        return rows
    return [{PRACTICE_COLUMN: PRACTICE_COLUMN, **r} for r in rows]
