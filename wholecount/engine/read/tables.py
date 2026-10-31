"""P-READ-4 to P-READ-6: finding the tables inside a grid, their header rows and their kind.

Ported from legacy/table_detect.py with three changes: a cell is blank only when its text is empty, so a row of dashes or a
column headed NULL is data; header problems come back as reason IDs and never switch the header silently; and a block that
follows a records table with the same shape joins it as a continuation (A-09).
"""
import re
from dataclasses import dataclass, field, replace

from wholecount.engine.read.model import Block, BlockInfo, LoadedTable
from wholecount.settings.loader import load

MAX_DEPTH = 12
_NUMERIC = re.compile(r"[-+]?\$?\d{1,3}(,\d{3})*(\.\d+)?%?|[-+]?\$?\d+(\.\d+)?%?")
_DATA_LIKE = re.compile(r"^\s*(\d{5}(-\d{4})?|\d{1,2}/\d{1,2}/\d{2,4}|\d{4}-\d{2}-\d{2}|[\d,.\-$%]+)\s*$")
_NAME_LIKE = re.compile(r"[A-Za-z_][A-Za-z0-9_ .#/()-]{0,40}")
_BELOW_WORD = re.compile(r"[A-Za-z_ ][A-Za-z0-9_ .#/-]{0,30}")

HEADER_WARNINGS = (
    "header_row_empty", "header_mostly_blank", "header_looks_like_data", "header_duplicate_name",
    "header_same_shape_as_row_below", "header_row_below_is_better", "no_header_but_row_looks_like_names",
)
KIND_REASONS = ("person_and_address", "address_fields", "person_fields", "summary_narrow", "summary_headers", "no_known_headers",
                "continuation")


@dataclass
class SourceRow:
    """One row of a table as read: its file row number, cells, .xlsx cell formats by column, and which block it came from."""

    number: int
    cells: list
    meta: dict = field(default_factory=dict)
    block: int = 0


# Splitting

def _blank(text):
    return text == ""


def _runs(flags):
    out, start = [], None
    for i, f in enumerate(flags):
        if f and start is None:
            start = i
        elif not f and start is not None:
            out.append((start, i - 1))
            start = None
    if start is not None:
        out.append((start, len(flags) - 1))
    return out


def _split(rows, r0, r1, c0, c1, depth=0):
    if r0 > r1 or c0 > c1:
        return []
    row_runs = _runs([any(not _blank(rows[r][c]) for c in range(c0, c1 + 1)) for r in range(r0, r1 + 1)])
    if not row_runs:
        return []
    if len(row_runs) == 1 and (row_runs[0][0] > 0 or row_runs[0][1] < r1 - r0) and depth < MAX_DEPTH:
        return _split(rows, r0 + row_runs[0][0], r0 + row_runs[0][1], c0, c1, depth + 1)
    if len(row_runs) > 1 and depth < MAX_DEPTH:
        return [b for a, z in row_runs for b in _split(rows, r0 + a, r0 + z, c0, c1, depth + 1)]
    col_runs = _runs([any(not _blank(rows[r][c]) for r in range(r0, r1 + 1)) for c in range(c0, c1 + 1)])
    if not col_runs:
        return []
    if len(col_runs) == 1 and (col_runs[0][0] > 0 or col_runs[0][1] < c1 - c0) and depth < MAX_DEPTH:
        return _split(rows, r0, r1, c0 + col_runs[0][0], c0 + col_runs[0][1], depth + 1)
    if len(col_runs) > 1 and depth < MAX_DEPTH:
        return [b for a, z in col_runs for b in _split(rows, r0, r1, c0 + a, c0 + z, depth + 1)]
    return [Block(r0, r1, c0, c1)]


def split_blocks(grid):
    """Blocks of the grid, split on fully blank rows, then fully blank columns, recursively."""
    if not grid.rows:
        return []
    width = max(len(r) for r in grid.rows)
    if grid.fixed_header is not None:
        # JSON and XML: the records are one table. Blank records separate runs, which join as continuations.
        return [Block(a, z, 0, max(width, len(grid.fixed_header)) - 1)
                for a, z in _runs([any(c for c in r) for r in grid.rows])]
    return _split(grid.rows, 0, len(grid.rows) - 1, 0, width - 1)


def block_rows(grid, b):
    return [grid.rows[r][b.c0:b.c1 + 1] for r in range(b.r0, b.r1 + 1)]


# Headers

def _looks_numeric(text):
    return not _blank(text) and bool(_NUMERIC.fullmatch(text.strip()))


def detect_header(rows):
    """True when the first row reads like a header: mostly filled, no numbers, and different from the rows below."""
    if len(rows) < 2:
        return False
    head, body = rows[0], rows[1:]
    filled = [v for v in head if not _blank(v)]
    if not filled or len(filled) < max(1, int(0.6 * len(head))):
        return False
    if any(_looks_numeric(v) for v in filled):
        return False
    numeric_below = 0
    for ci in range(len(head)):
        col = [r[ci] for r in body if not _blank(r[ci])]
        if col and all(_looks_numeric(v) for v in col):
            numeric_below += 1
    return bool(numeric_below or len(filled) >= 2)


def looks_like_names(row):
    filled = [c.strip() for c in row if c.strip()]
    if len(filled) < 3 or len(filled) < len(row) * 0.6:
        return False
    wordy = sum(1 for c in filled if _NAME_LIKE.fullmatch(c) and not _DATA_LIKE.match(c))
    return wordy == len(filled) and len({c.lower() for c in filled}) == len(filled)


def header_looks_wrong(rows, header_row):
    """(warning ID or None, suggested header row or None). Never changes the header itself."""
    if not rows:
        return None, None
    if not header_row:
        for i, row in enumerate(rows[:6], start=1):
            if looks_like_names(row) and i < len(rows):
                return "no_header_but_row_looks_like_names", i
        return None, None
    if header_row > len(rows):
        return None, None
    hdr = [c.strip() for c in rows[header_row - 1]]
    filled = [c for c in hdr if c]
    better = _first_name_row_below(rows, header_row)
    if not filled:
        return "header_row_empty", better
    if len(hdr) >= 3 and len(filled) <= max(1, len(hdr) // 3):
        return "header_mostly_blank", better
    if sum(1 for c in filled if _DATA_LIKE.match(c)) * 2 >= len(filled):
        return "header_looks_like_data", better
    lowered = [c.lower() for c in filled]
    if len(set(lowered)) < len(lowered):
        return "header_duplicate_name", None
    if header_row < len(rows):
        below = [c.strip() for c in rows[header_row]]
        if len(below) == len(hdr):
            def shape(v):
                return "-" if not v else ("n" if _DATA_LIKE.match(v) else "w")
            hs, bs = [shape(c) for c in hdr], [shape(c) for c in below]
            same = sum(1 for a, b in zip(hs, bs) if a == b and a != "-")
            if hs.count("n") >= 1 and same >= max(2, int(len(hdr) * 0.8)):
                return "header_same_shape_as_row_below", None
        below_f = [c for c in below if c]
        if below_f and len(below_f) >= len(filled) + 2:
            words = sum(1 for c in below_f if _BELOW_WORD.fullmatch(c) and not _DATA_LIKE.match(c))
            if words * 5 >= len(below_f) * 4:
                return "header_row_below_is_better", header_row + 1
    return None, None


def _first_name_row_below(rows, header_row):
    for i in range(header_row + 1, min(len(rows), header_row + 6) + 1):
        if looks_like_names(rows[i - 1]) and i < len(rows):
            return i
    return None


def unique_headers(raw):
    out, seen = [], {}
    for i, name in enumerate(raw):
        base = name.strip() or f"Column_{i + 1}"
        key = base.lower()
        if key in seen:
            seen[key] += 1
            base = f"{base}_{seen[key]}"
        else:
            seen[key] = 1
        out.append(base)
    return out


# Classifying

def _norm_key(text):
    return re.sub(r"[^a-z0-9]", "", text.lower())


def classify(headers, hints=None):
    """(kind, reason ID). Kind is records, summary or unknown. Each header counts once, toward its first match."""
    hints = hints or load("table_hints")
    person_h = {_norm_key(h) for h in hints["person"]}
    address_h = {_norm_key(h) for h in hints["address"]}
    summary_h = {_norm_key(h) for h in hints["summary"]}
    person = address = summary = 0
    for h in headers:
        k = _norm_key(h)
        if k in person_h or "name" in k:
            person += 1
        elif k in address_h or "address" in k or k.startswith("addr"):
            address += 1
        elif k in summary_h:
            summary += 1
    if person and address:
        return "records", "person_and_address"
    if address >= 3:
        return "records", "address_fields"
    if person >= 2:
        return "records", "person_fields"
    if summary and len(headers) <= 4:
        return "summary", "summary_narrow"
    if summary:
        return "summary", "summary_headers"
    return "unknown", "no_known_headers"


# Assembling a table from its source rows

def assemble(table, header_row):
    """The table's header, data rows and counts for a chosen header row. Pure: returns a new table."""
    first = [s for s in table.source_rows if s.block == 0]
    rest = [s for s in table.source_rows if s.block != 0]
    if table.header_is_virtual:
        raw = list(table.raw_headers)
        headers = unique_headers(raw)
        data, above = first + rest, 0
    elif header_row:
        raw = list(first[header_row - 1].cells)
        headers = unique_headers(raw)
        data, above = first[header_row:] + rest, header_row - 1
    else:
        raw = []
        headers = [f"Column_{i + 1}" for i in range(len(first[0].cells))]
        data, above = first + rest, 0
    blocks = [replace(b, rows=sum(1 for s in data if s.block == i)) for i, b in enumerate(table.blocks)]
    meta = {(i, c): m for i, s in enumerate(data) for c, m in s.meta.items()}
    rows = [list(s.cells) for s in data]
    empty = [h for ci, h in enumerate(headers) if all(not r[ci] for r in rows)] if rows else list(headers)
    return replace(
        table, header_row=header_row, raw_headers=raw, headers=headers, rows=rows, row_numbers=[s.number for s in data],
        row_block=[s.block for s in data], meta=meta, blocks=blocks, above_header_rows=above, empty_columns=empty,
    )


def rebuild_with_header(table, header_row):
    """The table rebuilt with another header row, its kind and default inclusion recomputed. What Show data calls (P-READ-6).
    Record keys are left to the loader, which recomputes them for the new header."""
    if table.header_is_virtual:
        raise ValueError("a JSON or XML table's header is its keys")
    t = assemble(table, header_row)
    kind, reason = classify(t.headers)
    first = [s.cells for s in t.source_rows if s.block == 0]
    warning, suggested = header_looks_wrong(first, header_row)
    return replace(t, kind=kind, kind_reason=reason, included=kind == "records", header_warning=warning,
                   suggested_header_row=suggested, record_keys=[])


# Finding the tables in a grid

@dataclass
class GridTables:
    tables: list            # LoadedTable, keys and letters not yet set
    non_table_blocks: list  # Block


def _source_rows(grid, b, block_index):
    out = []
    for r in range(b.r0, b.r1 + 1):
        meta = {c - b.c0: m for (rr, c), m in grid.meta.items() if rr == r and b.c0 <= c <= b.c1}
        out.append(SourceRow(r + 1, grid.rows[r][b.c0:b.c1 + 1], meta, block_index))
    return out


def find_tables(grid, hints=None):
    hints = hints or load("table_hints")
    tables, non_table = [], []
    for b in split_blocks(grid):
        rows = block_rows(grid, b)
        if grid.fixed_header is not None:
            if tables:
                t = tables[-1]
                t.blocks.append(BlockInfo(b, b.n_rows, True, True))
                t.source_rows.extend(_source_rows(grid, b, len(t.blocks) - 1))
                continue
            header = grid.fixed_header
            kind, reason = classify(header, hints)
            t = _new_table(grid, b, kind, reason, header_row=0, virtual=True, raw_headers=list(header))
            tables.append(t)
            continue
        cont = _continuation_of(tables, b, rows)
        if cont is not None:
            cont.blocks.append(BlockInfo(b, b.n_rows, True, True))
            cont.source_rows.extend(_source_rows(grid, b, len(cont.blocks) - 1))
            continue
        if b.n_rows < 2:
            non_table.append(b)
            continue
        header_row = 1 if detect_header(rows) else 0
        headers = unique_headers(rows[0]) if header_row else [f"Column_{i + 1}" for i in range(b.n_cols)]
        kind, reason = classify(headers, hints)
        warning, suggested = header_looks_wrong(rows, header_row)
        t = _new_table(grid, b, kind, reason, header_row=header_row, virtual=False, raw_headers=[])
        t.header_warning, t.suggested_header_row = warning, suggested
        tables.append(t)
    return GridTables([assemble(t, t.header_row) for t in tables], non_table)


def _new_table(grid, b, kind, reason, header_row, virtual, raw_headers):
    t = LoadedTable(
        key="", letter="", sheet=grid.sheet, blocks=[BlockInfo(b, 0, True, False)], header_row=header_row,
        header_is_virtual=virtual, raw_headers=raw_headers, headers=[], rows=[], row_numbers=[], row_block=[], meta={},
        record_keys=[], kind=kind, kind_reason=reason, included=kind == "records",
    )
    t.source_rows = _source_rows(grid, b, 0)
    return t


def _continuation_of(tables, b, rows):
    """The records table this block continues, or None. The nearest records table above must have the same column count and
    first column, and the block's first row must not read like a header or like column names (P-READ-5)."""
    above = [t for t in tables if t.kind == "records" and t.blocks[-1].block.r1 < b.r0]
    if not above:
        return None
    nearest = max(above, key=lambda t: t.blocks[-1].block.r1)
    last = nearest.blocks[-1].block
    if last.c0 != b.c0 or last.n_cols != b.n_cols:
        return None
    if detect_header(rows) or looks_like_names(rows[0]):
        return None
    return nearest
