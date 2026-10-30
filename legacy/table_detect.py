"""
Table detection: find the separate, complete tables inside one spreadsheet or
sheet, so that two datasets sitting side by side (or stacked) are never merged
into one corrupted table.

The method is deterministic and explainable, with no guessing:

  1. Read the sheet into a grid of cleaned text values.
  2. Split the region by fully blank ROWS, then by fully blank COLUMNS, and
     recurse. A fully blank row or column is a separator, which is how people
     actually lay out multiple tables on one tab.
  3. Each remaining block is one table. Detect its header row, then describe it
     (range, size, columns, fill rate, empty columns, sensitive fields) and
     classify it as record-level or summary so a person can decide what to keep.

Nothing is altered or dropped. Detection only partitions the sheet, and the
caller chooses which tables to include.
"""
from __future__ import annotations

import datetime as _dt
import re

# Values that mean "empty" for layout purposes.
_BLANK_TOKENS = {"", "null", "#n/a", "n/a", "none", "nan", "nil", "-", "--"}

# Field-name vocabulary used only to CLASSIFY a table for the user's benefit.
# It never changes data and never decides inclusion on its own.
_PERSON_HINTS = {
    "id", "clientid", "client_id", "pid", "participantid", "recordid",
    "first", "firstn", "firstname", "fname", "given", "givenname",
    "last", "lastn", "lastname", "lname", "surname", "family", "familyname",
    "middle", "mi", "middleinitial", "name", "fullname", "clientname",
}
_ADDRESS_HINTS = {
    "address", "address1", "address_1", "addr", "addr1", "street", "streetaddress",
    "address2", "address_2", "addr2", "apt", "unit",
    "city", "borough", "town", "state", "st", "zip", "zipcode", "zip_code",
    "postal", "postalcode", "county",
}
_SUMMARY_HINTS = {
    "total", "totals", "count", "number", "numberof", "sum", "avg", "average",
    "pct", "percent", "rate", "subtotal", "grandtotal", "measure", "metric",
}
# Columns that carry sensitive detail and are worth flagging on sight.
_SENSITIVE_HINTS = {
    "ssn": "Social Security Number", "socialsecurity": "Social Security Number",
    "dob": "date of birth", "dateofbirth": "date of birth", "birthdate": "date of birth",
    "birth": "date of birth", "race": "race", "ethnicity": "ethnicity",
    "gender": "gender", "sex": "sex", "diagnosis": "diagnosis", "medicaid": "Medicaid ID",
    "medicare": "Medicare ID", "income": "income",
}

MAX_DEPTH = 12


# ----------------------------------------------------------------------------
# helpers
# ----------------------------------------------------------------------------
def _to_text(value) -> str:
    """Normalize a cell to trimmed text. Dates keep an unambiguous ISO form."""
    if value is None:
        return ""
    if isinstance(value, _dt.datetime):
        if value.hour or value.minute or value.second:
            return value.strftime("%Y-%m-%d %H:%M:%S")
        return value.strftime("%Y-%m-%d")
    if isinstance(value, _dt.date):
        return value.strftime("%Y-%m-%d")
    if isinstance(value, float) and value.is_integer():
        return str(int(value))
    text = str(value).replace("\t", " ").replace("\r", " ").replace("\n", " ")
    return re.sub(r"\s+", " ", text).strip()


def _is_blank(text: str) -> bool:
    """Whether a cell holds nothing."""
    return text.strip().lower() in _BLANK_TOKENS


def _norm_key(text: str) -> str:
    """A column name normalized for comparison."""
    return re.sub(r"[^a-z0-9]", "", text.lower())


def _looks_numeric(text: str) -> bool:
    """Whether a value reads as a number."""
    if _is_blank(text):
        return False
    return bool(re.fullmatch(r"[-+]?\$?\d{1,3}(,\d{3})*(\.\d+)?%?|[-+]?\$?\d+(\.\d+)?%?",
                             text.strip()))


def col_letter(index0: int) -> str:
    """0-based column index to spreadsheet letters (0 -> A, 27 -> AB)."""
    n, out = index0 + 1, ""
    while n:
        n, rem = divmod(n - 1, 26)
        out = chr(65 + rem) + out
    return out


# ----------------------------------------------------------------------------
# region splitting
# ----------------------------------------------------------------------------
def _runs(flags) -> list[tuple[int, int]]:
    """Maximal runs of True in flags, as inclusive (start, end) index pairs."""
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


def _split_region(grid, r0, r1, c0, c1, depth=0):
    """
    Recursively split a region on fully blank rows, then fully blank columns.
    Returns a list of atomic (r0, r1, c0, c1) blocks that each hold one table.
    """
    if r0 > r1 or c0 > c1:
        return []

    row_has = [any(not _is_blank(grid[r][c]) for c in range(c0, c1 + 1))
               for r in range(r0, r1 + 1)]
    row_runs = _runs(row_has)
    if not row_runs:
        return []

    # Trim to the occupied envelope first.
    if len(row_runs) == 1 and (row_runs[0][0] > 0 or row_runs[0][1] < r1 - r0):
        nr0, nr1 = r0 + row_runs[0][0], r0 + row_runs[0][1]
        if (nr0, nr1) != (r0, r1) and depth < MAX_DEPTH:
            return _split_region(grid, nr0, nr1, c0, c1, depth + 1)

    if len(row_runs) > 1 and depth < MAX_DEPTH:
        out = []
        for a, b in row_runs:
            out.extend(_split_region(grid, r0 + a, r0 + b, c0, c1, depth + 1))
        return out

    col_has = [any(not _is_blank(grid[r][c]) for r in range(r0, r1 + 1))
               for c in range(c0, c1 + 1)]
    col_runs = _runs(col_has)
    if not col_runs:
        return []

    if len(col_runs) == 1 and (col_runs[0][0] > 0 or col_runs[0][1] < c1 - c0):
        nc0, nc1 = c0 + col_runs[0][0], c0 + col_runs[0][1]
        if (nc0, nc1) != (c0, c1) and depth < MAX_DEPTH:
            return _split_region(grid, r0, r1, nc0, nc1, depth + 1)

    if len(col_runs) > 1 and depth < MAX_DEPTH:
        out = []
        for a, b in col_runs:
            out.extend(_split_region(grid, r0, r1, c0 + a, c0 + b, depth + 1))
        return out

    return [(r0, r1, c0, c1)]


# ----------------------------------------------------------------------------
# header detection and description
# ----------------------------------------------------------------------------
def _detect_header(block_rows) -> bool:
    """
    True when the first row of a block reads like a header: mostly non-blank
    text, not numeric, and different in character from the row beneath it.
    """
    if len(block_rows) < 2:
        return False
    head, body = block_rows[0], block_rows[1:]
    filled = [v for v in head if not _is_blank(v)]
    if not filled:
        return False
    if len(filled) < max(1, int(0.6 * len(head))):
        return False
    if any(_looks_numeric(v) for v in filled):
        return False
    # A header is more convincing when the column below holds different types.
    numeric_below = 0
    for ci in range(len(head)):
        col_vals = [r[ci] for r in body if not _is_blank(r[ci])]
        if col_vals and all(_looks_numeric(v) for v in col_vals):
            numeric_below += 1
    return True if numeric_below or len(filled) >= 2 else False


def _unique_headers(raw) -> list[str]:
    """Column names made unique, so two blank or equal headers do not collide."""
    out, seen = [], {}
    for i, name in enumerate(raw):
        base = name.strip() if not _is_blank(name) else f"Column_{i + 1}"
        key = base.lower()
        if key in seen:
            seen[key] += 1
            base = f"{base}_{seen[key]}"
        else:
            seen[key] = 1
        out.append(base)
    return out


def _classify(headers, n_rows, n_cols) -> tuple[str, str]:
    """
    Return (kind, reason). kind is 'records', 'summary', or 'unknown'.

    Matching is by exact field name first, then by a small set of compound
    forms, so a jammed column such as Full_Address or client_name is still
    recognized. Each header counts once, toward the first category it matches.
    """
    person = address = summary = 0
    for h in headers:
        k = _norm_key(h)
        if k in _PERSON_HINTS or "name" in k:
            person += 1
        elif k in _ADDRESS_HINTS or "address" in k or k.startswith("addr"):
            address += 1
        elif k in _SUMMARY_HINTS:
            summary += 1

    if person and address:
        return ("records",
                f"has person fields and {address} address field(s)")
    if address >= 3:
        return "records", f"has {address} address fields"
    if person >= 2:
        return "records", f"has {person} person fields"
    if summary and n_cols <= 4:
        return "summary", f"narrow table with aggregate headers ({summary} matched)"
    if summary:
        return "summary", f"has aggregate headers ({summary} matched)"
    return "unknown", "no recognizable person, address, or aggregate headers"


class DetectedTable:
    """One table found inside a sheet, with everything needed to show a person."""

    synthetic = False   # True when the table is a whole already-parsed file
    block = None        # every row of the block, header included

    def __init__(self, source, sheet, r0, r1, c0, c1, headers, rows,
                 has_header, kind, reason, block=None):
        self.source = source
        self.sheet = sheet
        self.r0, self.r1, self.c0, self.c1 = r0, r1, c0, c1
        self.headers = headers
        self.rows = rows                      # list of lists of text, data only
        self.has_header = has_header
        self.kind = kind
        self.reason = reason
        self.block = block if block is not None else (
            ([headers] if has_header else []) + list(rows))

    # -- description -------------------------------------------------------
    @property
    def a1_range(self) -> str:
        """The block's position on the sheet in A1 notation, such as A1:H63."""
        return (f"{col_letter(self.c0)}{self.r0 + 1}:"
                f"{col_letter(self.c1)}{self.r1 + 1}")

    @property
    def n_rows(self) -> int:
        """How many rows the block has, including its header."""
        return len(self.rows)

    @property
    def n_cols(self) -> int:
        """How many columns the block has."""
        return len(self.headers)

    @property
    def key(self) -> str:
        """The stable name for this table: file, sheet and range."""
        if self.synthetic:
            return self.source
        sheet = f" :: {self.sheet}" if self.sheet else ""
        return f"{self.source}{sheet} :: {self.a1_range}"

    @property
    def label(self) -> str:
        """A short name for this table for screens."""
        if self.synthetic:
            return self.source
        sheet = f"{self.sheet} " if self.sheet else ""
        return f"{sheet}{self.a1_range}"

    @property
    def fill_rate(self) -> float:
        """The share of cells that hold a value."""
        total = self.n_rows * self.n_cols
        if not total:
            return 0.0
        filled = sum(1 for r in self.rows for v in r if not _is_blank(v))
        return filled / total

    @property
    def empty_columns(self) -> list[str]:
        """The columns of a block that hold no value at all."""
        out = []
        for ci, name in enumerate(self.headers):
            if all(_is_blank(r[ci]) for r in self.rows):
                out.append(name)
        return out

    @property
    def sensitive_columns(self) -> list[tuple[str, str]]:
        """Columns whose names suggest sensitive personal data, with the reason."""
        out = []
        for name in self.headers:
            key = _norm_key(name)
            for hint, what in _SENSITIVE_HINTS.items():
                if key == hint or key.startswith(hint):
                    out.append((name, what))
                    break
        return out

    @property
    def suggested_include(self) -> bool:
        """Recommend record-level tables. The person still decides."""
        return self.kind == "records"

    def to_dataframe(self):
        """The block as a table, with the chosen header row as column names."""
        import pandas as pd
        return pd.DataFrame(self.rows, columns=self.headers, dtype=str)

    def summary_line(self) -> str:
        """One line saying what this table looks like, for the files stage."""
        return (f"{self.label}  |  {self.n_rows} rows x {self.n_cols} cols  |  "
                f"{self.kind} ({self.reason})")


# ----------------------------------------------------------------------------
# entry points
# ----------------------------------------------------------------------------
def detect_in_grid(grid, source="input", sheet="", min_rows=1, min_cols=1):
    """Find the tables inside one already-loaded grid of raw cell values."""
    if not grid:
        return []
    width = max(len(r) for r in grid)
    norm = [[_to_text(v) for v in row] + [""] * (width - len(row)) for row in grid]

    tables = []
    for (r0, r1, c0, c1) in _split_region(norm, 0, len(norm) - 1, 0, width - 1):
        block = [[norm[r][c] for c in range(c0, c1 + 1)] for r in range(r0, r1 + 1)]
        has_header = _detect_header(block)
        if has_header:
            headers = _unique_headers(block[0])
            data = block[1:]
        else:
            headers = [f"Column_{i + 1}" for i in range(c1 - c0 + 1)]
            data = block
        if len(data) < min_rows or len(headers) < min_cols:
            continue
        kind, reason = _classify(headers, len(data), len(headers))
        tables.append(DetectedTable(source, sheet, r0, r1, c0, c1,
                                    headers, data, has_header, kind, reason,
                                    block=block))
    return tables


def frame_from_block(block, header_row):
    """
    Build (headers, rows) from a block of raw rows using a chosen header row.

    header_row is 1-based and counts rows of the block as a person sees them.
    0 means the block has no header, so columns are numbered. Any rows above the
    chosen header are title or note rows and are dropped, which is the usual
    reason for choosing a later row.
    """
    import pandas as pd
    block = [list(r) for r in (block or [])]
    if not block:
        return [], []
    width = max(len(r) for r in block)
    block = [r + [""] * (width - len(r)) for r in block]
    n = int(header_row or 0)
    if n <= 0:
        return [f"Column_{i + 1}" for i in range(width)], block
    n = min(n, len(block))
    return _unique_headers(block[n - 1]), block[n:]


def table_from_dataframe(df, source="input", sheet="", synthetic=True):
    """
    Wrap an already-parsed table (for example flattened JSON or XML) as a single
    DetectedTable, so every format flows through the same selection UI.
    """
    headers = _unique_headers([str(c) for c in df.columns])
    rows = [[_to_text(v) for v in rec] for rec in df.itertuples(index=False, name=None)]
    kind, reason = _classify(headers, len(rows), len(headers))
    t = DetectedTable(source, sheet, 0, max(0, len(rows)), 0,
                      max(0, len(headers) - 1), headers, rows, True, kind, reason)
    t.synthetic = synthetic
    return t


def detect_in_excel(path_or_buffer, source="workbook.xlsx"):
    """Find the tables in every sheet of an Excel workbook."""
    import openpyxl
    wb = openpyxl.load_workbook(path_or_buffer, data_only=True, read_only=True)
    out = []
    try:
        for ws in wb.worksheets:
            grid = [list(row) for row in ws.iter_rows(values_only=True)]
            out.extend(detect_in_grid(grid, source=source, sheet=ws.title))
    finally:
        wb.close()
    return out


def detect_in_delimited(text, source="input.csv", delimiter=None):
    """Find the tables in CSV or TSV text (side-by-side tables included)."""
    import csv
    import io
    if delimiter is None:
        delimiter = "\t" if source.lower().endswith((".tsv", ".tab")) else ","
    grid = [row for row in csv.reader(io.StringIO(text), delimiter=delimiter)]
    return detect_in_grid(grid, source=source, sheet="")


# ---------------------------------------------------------------------------
# Does the chosen header row look like a header?
# ---------------------------------------------------------------------------
import re as _re

_DATA_LIKE = _re.compile(r"^\s*(\d{5}(-\d{4})?|\d{1,2}/\d{1,2}/\d{2,4}|\d{4}-\d{2}-\d{2}|"
                         r"[\d,.\-$%]+)\s*$")


def header_looks_wrong(block, header_row):
    """
    (True, reason) when the row chosen as the header does not look like one,
    else (False, ""). The signs: the header cells look like data (ZIPs, dates,
    plain numbers); most header cells are blank; two columns share a name; or
    the row just below the header looks more like a header than the header
    does, which is what a title row above the real header produces.
    """
    if not block:
        return False, ""

    def looks_like_names(row):
        """Whether a row reads like column names rather than data."""
        cells = [str(c).strip() for c in row]
        filled = [c for c in cells if c]
        if len(filled) < 3 or len(filled) < len(cells) * 0.6:
            return False
        wordy = sum(1 for c in filled
                    if _re.fullmatch(r"[A-Za-z_][A-Za-z0-9_ .#/()-]{0,40}", c)
                    and not _DATA_LIKE.match(c))
        return wordy == len(filled) and len(set(c.lower() for c in filled)) == len(filled)

    # "no header" chosen, but one of the first rows plainly holds column names
    if header_row is None or header_row < 1:
        for i, row in enumerate(block[:6], start=1):
            if looks_like_names(row) and i < len(block):
                return True, (f"no header row is chosen, but row {i} looks like "
                              "the column names")
        return False, ""
    if header_row > len(block):
        return False, ""
    hdr = [str(c).strip() for c in block[header_row - 1]]
    filled = [c for c in hdr if c]
    if not filled:
        return True, "the chosen row is empty"
    width = len(hdr)
    if width >= 3 and len(filled) <= max(1, width // 3):
        return True, (f"only {len(filled)} of {width} cells in the chosen row have "
                      "a value, which looks like a title, not column names")
    datalike = sum(1 for c in filled if _DATA_LIKE.match(c))
    if filled and datalike / len(filled) >= 0.5:
        return True, ("the chosen row is mostly numbers, dates or ZIPs, which "
                      "looks like data, not column names")
    lowered = [c.lower() for c in filled]
    if len(set(lowered)) < len(lowered):
        dup = next(c for c in lowered if lowered.count(c) > 1)
        return True, f"two columns would both be named '{dup}'"
    # a data row chosen as the header: the row below has the same shape,
    # cell for cell (number where it has a number, word where it has a word),
    # which two rows of data do and a header over data does not
    if header_row < len(block):
        below = [str(c).strip() for c in block[header_row]]
        if len(below) == len(hdr):
            def shape(v):
                """Whether a cell is empty, a number, or a word, for comparing rows."""
                if not v:
                    return "-"
                return "n" if _DATA_LIKE.match(v) else "w"
            hs = [shape(c) for c in hdr]
            bs = [shape(c) for c in below]
            same = sum(1 for a, b in zip(hs, bs) if a == b and a != "-")
            if hs.count("n") >= 1 and same >= max(2, int(len(hdr) * 0.8)):
                return True, ("the chosen row has the same shape as the row "
                              "below it, so it looks like a record, not the "
                              "column names")
    # the row below looks more like a header: mostly short words, few numbers
    if header_row < len(block):
        below = [str(c).strip() for c in block[header_row]]
        below_f = [c for c in below if c]
        if below_f and len(below_f) >= len(filled) + 2:
            below_words = sum(1 for c in below_f
                              if _re.fullmatch(r"[A-Za-z_ ][A-Za-z0-9_ .#/-]{0,30}", c)
                              and not _DATA_LIKE.match(c))
            if below_words / len(below_f) >= 0.8:
                return True, (f"row {header_row + 1} looks more like the column "
                              f"names than row {header_row} does")
    return False, ""
