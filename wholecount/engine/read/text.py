"""P-READ-2: decoding text files, and choosing a delimiter. Never decodes with replacement characters."""
import csv
import io

from wholecount.engine.read.model import UnreadableFile

UTF8_BOM = b"\xef\xbb\xbf"
MAX_SAMPLES = 5
DELIMITER_ORDER = (",", "\t", ";", "|")
REPLACEMENT = "�"


def decode(data):
    """(text, encoding). Strict UTF-8 after removing a BOM, then strict Windows-1252, else unreadable_encoding."""
    if data.startswith(UTF8_BOM):
        data = data[len(UTF8_BOM):]
    try:
        return data.decode("utf-8", errors="strict"), "utf-8"
    except UnicodeDecodeError:
        pass
    try:
        # Python's cp1252 leaves 0x81, 0x8D, 0x8F, 0x90 and 0x9D undefined, so a file holding them fails here.
        return data.decode("cp1252", errors="strict"), "windows-1252"
    except UnicodeDecodeError:
        raise UnreadableFile("unreadable_encoding") from None


def encoding_samples(rows):
    """Up to five cells holding a non-ASCII letter, for the Windows Western callout."""
    out = []
    for row in rows:
        for cell in row:
            if any(ord(ch) > 127 and ch.isalpha() for ch in cell):
                out.append(cell)
                if len(out) == MAX_SAMPLES:
                    return out
    return out


def choose_delimiter(extension, text):
    if extension == ".csv":
        return ","
    if extension == ".tsv":
        return "\t"
    lines = [ln for ln in text.splitlines() if ln.strip()][:20]
    best, best_count = ",", 0
    for d in DELIMITER_ORDER:
        counts = {ln.count(d) for ln in lines}
        if len(counts) == 1 and (c := counts.pop()) > best_count:
            best, best_count = d, c
    return best


def parse_delimited(text, delimiter):
    return [list(r) for r in csv.reader(io.StringIO(text, newline=""), delimiter=delimiter)]
