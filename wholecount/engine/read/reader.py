"""P-READ-10: the one way a file comes in. Only a pathlib.Path, opened here, with parsers given in-memory file objects only."""
import hashlib
import io
import pathlib

from wholecount.engine.read import structured, text, xlsx
from wholecount.engine.read.clean import CleanCounts, clean_cell
from wholecount.engine.read.model import Grid, ReadFile, UnreadableFile

TEXT_EXTENSIONS = (".csv", ".tsv", ".txt")
EXTENSIONS = TEXT_EXTENSIONS + (".xlsx", ".json", ".xml")


def _clean_rows(rows, counts):
    """Clean every cell and pad to a rectangle. Returns (rows, U+FFFD count)."""
    width = max((len(r) for r in rows), default=0)
    out, replacement = [], 0
    for r in rows:
        cleaned = []
        for cell in r:
            s, c = clean_cell(cell)
            counts.add(c)
            replacement += s.count(text.REPLACEMENT)
            cleaned.append(s)
        out.append(cleaned + [""] * (width - len(cleaned)))
    return out, replacement


def _read_bytes(path):
    from wholecount.guard import OfflineViolation

    try:
        with path.open("rb") as f:
            return f.read()
    except OfflineViolation:
        raise UnreadableFile("blocked_by_guard") from None


def read_path(path):
    """Read one file into grids of cleaned text. Raises UnreadableFile with a reason ID, never with text from the file."""
    if not isinstance(path, pathlib.Path):
        raise TypeError("read_path takes a pathlib.Path")
    ext = path.suffix.lower()
    if ext not in EXTENSIONS:
        raise UnreadableFile("unsupported_type")
    data = _read_bytes(path)
    if not data.strip():
        raise UnreadableFile("empty_file")
    counts = CleanCounts()
    encoding, samples, replacement = None, [], 0
    grids = []
    if ext in TEXT_EXTENSIONS:
        decoded, encoding = text.decode(data)
        rows = text.parse_delimited(decoded, text.choose_delimiter(ext, decoded))
        rows, replacement = _clean_rows(rows, counts)
        if encoding == "windows-1252":
            samples = text.encoding_samples(rows)
        grids.append(Grid(None, rows))
    elif ext == ".xlsx":
        for name, hidden, cells in xlsx.read_sheets(io.BytesIO(data)):
            raw = [[xlsx.cell_text(v, f) for v, f in r] for r in cells]
            rows, rep = _clean_rows(raw, counts)
            replacement += rep
            meta = {}
            for i, r in enumerate(cells):
                for j, (v, f) in enumerate(r):
                    m = xlsx.cell_meta(v, f)
                    if m is not None:
                        meta[(i, j)] = m
            grids.append(Grid(name, rows, meta, hidden=hidden))
    else:
        records = structured.json_records(data) if ext == ".json" else structured.xml_records(io.BytesIO(data))
        header, rows = structured.records_to_rows(records)
        header = [clean_cell(h)[0] for h in header]
        rows, replacement = _clean_rows(rows, counts) if rows else ([], 0)
        rows = [r + [""] * (len(header) - len(r)) for r in rows]
        grids.append(Grid(None, rows, fixed_header=header))
    return ReadFile(
        name=path.name, extension=ext, fingerprint=hashlib.sha256(data).hexdigest(), size=len(data), encoding=encoding,
        encoding_samples=samples, grids=grids, clean_counts=counts.as_dict(), replacement_chars=replacement,
    )
