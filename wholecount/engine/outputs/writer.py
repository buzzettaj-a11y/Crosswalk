"""Writing the files (SPEC 9.1, OUT-12, OUT-13). Plain inputs only: the gate lives in session/export.py.

Each file is written under a temporary name in the chosen folder and renamed. A failure removes the temporary files, so the
folder holds exactly the receipt's files afterward. Nothing is overwritten without a yes.
"""
import csv
import datetime as dt
import io
import json
import os
import pathlib
import zipfile

from wholecount import copy
from wholecount.engine.outputs import audit_text, receipt as rc, tables
from wholecount.engine.outputs.columns import LOG_FILES, PRACTICE_COLUMN, FileId, chip_columns
from wholecount.engine.outputs.folders import folder_warning
from wholecount.engine.outputs.review_file import manual_review_needed

FIXED_ZIP_TIME = (2000, 1, 1, 0, 0, 0)


class FolderNeedsConfirm(Exception):
    def __init__(self, kind):
        super().__init__(kind)
        self.kind = kind


class WouldOverwrite(Exception):
    def __init__(self, names):
        super().__init__(", ".join(names))
        self.names = tuple(names)


def files_to_write(view, settings):
    """The files this run writes, in a fixed order."""
    out = [FileId.FINAL_CLEAN_MAPPED, FileId.UNIQUE_CLIENTS, FileId.UNIQUE_CLIENTS_BY_PROGRAM, FileId.MANUAL_REVIEW_NEEDED,
           FileId.SET_ASIDE_RECORDS]
    if not view.practice:
        out.append(FileId.MAP_COUNTS)
        if settings.map_points:
            out.append(FileId.MAP_POINTS)
    return out + [FileId.DATA_QUALITY_REPORT, FileId.INTERNAL_AUDIT_LOG, FileId.SHAREABLE_AUDIT_LOG]


def file_format(file_id, settings):
    if file_id in LOG_FILES:
        return "txt"
    if file_id == FileId.DATA_QUALITY_REPORT:
        return "csv"
    return settings.formats.get(file_id.value, "csv")


def file_name(file_id, view, settings):
    prefix = "PRACTICE_" if view.practice else ""
    return f"{prefix}{file_id.value}.{file_format(file_id, settings)}"


def table_rows(file_id, view, settings):
    if file_id == FileId.MANUAL_REVIEW_NEEDED:
        rows = manual_review_needed(view, settings)
    else:
        rows = tables.BUILDERS[file_id.value](view, settings)
    return tables.with_practice(view, rows)


def encode_csv(columns, rows):
    buf = io.StringIO()
    w = csv.writer(buf, lineterminator="\r\n")
    w.writerow(columns)
    for r in rows:
        w.writerow([r.get(c, "") for c in columns])
    return ("﻿" + buf.getvalue()).encode("utf-8")


def encode_json(columns, rows):
    return json.dumps([{c: str(r.get(c, "")) for c in columns} for r in rows], ensure_ascii=False, indent=1).encode("utf-8")


def encode_xlsx(columns, rows, notes=(), clock_time=None):
    """Every cell as text, so =1+1 stays text and 00123 keeps its zeros. One Data sheet, plus Notes when a note applies."""
    import openpyxl
    from openpyxl.comments import Comment

    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = "Data"

    def put(row, col, value):
        c = ws.cell(row=row, column=col)
        c.value = str(value)
        c.data_type = "s"
        c.number_format = "@"
        return c

    for j, name in enumerate(columns, start=1):
        put(1, j, name)
    for i, r in enumerate(rows, start=2):
        for j, name in enumerate(columns, start=1):
            put(i, j, r.get(name, ""))
    if notes:
        ns = wb.create_sheet("Notes")
        for i, (column, text) in enumerate(notes, start=1):
            ns.cell(row=i, column=1).value = text
            ns.cell(row=i, column=1).data_type = "s"
            if column in columns:
                ws.cell(row=1, column=columns.index(column) + 1).comment = Comment(text, "")
    when = clock_time or dt.datetime(2000, 1, 1)
    wb.properties.created = when.replace(tzinfo=None)
    wb.properties.modified = when.replace(tzinfo=None)
    raw = io.BytesIO()
    wb.save(raw)
    return _fixed_zip(raw.getvalue())


def _fixed_zip(data):
    """Re-pack the workbook with fixed entry times, so equal inputs give equal bytes."""
    src = zipfile.ZipFile(io.BytesIO(data))
    out = io.BytesIO()
    with zipfile.ZipFile(out, "w", zipfile.ZIP_DEFLATED) as dst:
        for info in src.infolist():
            zi = zipfile.ZipInfo(info.filename, FIXED_ZIP_TIME)
            zi.compress_type = zipfile.ZIP_DEFLATED
            zi.external_attr = info.external_attr
            dst.writestr(zi, src.read(info.filename))
    return out.getvalue()


def _notes(file_id, view, settings):
    notes = []
    if file_id == FileId.FINAL_CLEAN_MAPPED and settings.exact_coordinates:
        notes.append(("Latitude", copy.get("outputs.note.exact_coordinates")))
    if file_id == FileId.MAP_POINTS:
        notes.append(("Latitude", copy.get("geo.moved_point_note")))
    return notes


def encode(file_id, view, settings, now):
    if file_id == FileId.INTERNAL_AUDIT_LOG:
        return audit_text.render_internal(view).encode("utf-8")
    if file_id == FileId.SHAREABLE_AUDIT_LOG:
        return audit_text.render_shareable(view).encode("utf-8")
    cols = chip_columns(file_id, view, settings)
    rows = table_rows(file_id, view, settings)
    fmt = file_format(file_id, settings)
    if fmt == "xlsx":
        return encode_xlsx(cols, rows, _notes(file_id, view, settings), now)
    if fmt == "json":
        return encode_json(cols, rows)
    return encode_csv(cols, rows)


def read_back(path):
    """(rows, columns) as written, for the receipt."""
    suffix = path.suffix.lower()
    if suffix == ".csv":
        rows = list(csv.reader(io.StringIO(path.read_bytes().decode("utf-8-sig"))))
        return max(len(rows) - 1, 0), len(rows[0]) if rows else 0
    if suffix == ".json":
        data = json.loads(path.read_text(encoding="utf-8"))
        return len(data), len(data[0]) if data else 0
    if suffix == ".xlsx":
        import openpyxl
        wb = openpyxl.load_workbook(path, read_only=True)
        try:
            ws = wb["Data"]
            return ws.max_row - 1, ws.max_column
        finally:
            wb.close()
    return len(path.read_text(encoding="utf-8").splitlines()), 1


def write_outputs(view, folder, settings, clock, confirmed_synced=False, overwrite=False, environ=None):
    """Write every file. Returns the Receipt. Raises FolderNeedsConfirm or WouldOverwrite before writing anything."""
    folder = pathlib.Path(folder)
    kind = folder_warning(str(folder), os.environ if environ is None else environ)
    if kind and not confirmed_synced:
        raise FolderNeedsConfirm(kind)
    ids = files_to_write(view, settings)
    names = [file_name(f, view, settings) for f in ids]
    existing = [n for n in names if (folder / n).exists()]
    if existing and not overwrite:
        raise WouldOverwrite(existing)
    now = clock()
    payloads = [(n, encode(f, view, settings, now)) for f, n in zip(ids, names)]
    temps = []
    try:
        for n, data in payloads:
            tmp = folder / f".{n}.part"
            tmp.write_bytes(data)
            temps.append((tmp, folder / n))
        for tmp, final in temps:
            os.replace(tmp, final)
    except BaseException:
        for tmp, _ in temps:
            if tmp.exists():
                tmp.unlink()
        raise
    time_iso = now.astimezone(dt.timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")
    files = []
    for n in names:
        rows, cols = read_back(folder / n)
        files.append(rc.ReceiptFile(str(folder / n), rows, cols, time_iso))
    return rc.Receipt(tuple(files), receipt_notes(view, settings))


def receipt_notes(view, settings):
    notes = []
    if settings.exact_coordinates:
        notes.append(("outputs.note.exact_coordinates", {}))
    if settings.map_points and not view.practice:
        notes.append(("geo.moved_point_note", {}))
    if view.practice:
        notes.append(("outputs.practice.no_maps", {}))
    if view.counts.open_pairs:
        notes.append(("outputs.note.open_pairs", {"count": view.counts.open_pairs}))
    return tuple(notes)


__all__ = ["write_outputs", "FolderNeedsConfirm", "WouldOverwrite", "files_to_write", "file_name", "encode_csv", "encode_xlsx",
           "encode_json", "PRACTICE_COLUMN"]


def write_text(path, text, overwrite=False):
    """The printable page and other single text files, through a temporary name. Nothing is overwritten without a yes."""
    path = pathlib.Path(path)
    if path.exists() and not overwrite:
        raise WouldOverwrite([path.name])
    tmp = path.with_name(f".{path.name}.part")
    tmp.write_bytes(text.encode("utf-8"))
    os.replace(tmp, path)
    return path
