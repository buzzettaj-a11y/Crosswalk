"""P-READ-9 and fix plan 4.1: columns that suggest sensitive data, by name or by values. M02 reuses these for P-MAP-7."""
import re

from wholecount.settings.loader import load

_DASHED = re.compile(r"\d{3}-\d{2}-\d{4}")
_NINE = re.compile(r"\d{9}")
_WORDS = re.compile(r"[a-z0-9]+")


def ssn_shaped(value):
    """###-##-####, or nine digits with area not 000, 666 or 9xx, group not 00 and serial not 0000."""
    v = value.strip()
    if _DASHED.fullmatch(v):
        return True
    if not _NINE.fullmatch(v):
        return False
    area, group, serial = v[:3], v[3:5], v[5:]
    return area != "000" and area != "666" and not area.startswith("9") and group != "00" and serial != "0000"


def looks_like_ssn_column(values):
    """More than half of the non-blank values are SSN-shaped. Exactly half is not enough."""
    filled = [v for v in values if v.strip()]
    return bool(filled) and sum(ssn_shaped(v) for v in filled) * 2 > len(filled)


def _phrases():
    return [p.split() for group in load("sensitive_columns")["phrases"].values() for p in group]


def sensitive_name(header, phrases=None):
    """True when a whole-word phrase from settings/sensitive_columns.toml appears in the header. Never a part of a word."""
    words = _WORDS.findall(header.lower())
    for phrase in phrases if phrases is not None else _phrases():
        n = len(phrase)
        if any(words[i:i + n] == phrase for i in range(len(words) - n + 1)):
            return True
    return False


def sensitive_columns(table, phrases=None):
    """[(column index, by_values)] for columns to drop: a sensitive name, or more than half SSN-shaped values."""
    phrases = phrases if phrases is not None else _phrases()
    out = []
    for ci, h in enumerate(table.headers):
        raw = table.raw_headers[ci] if ci < len(table.raw_headers) else h
        if sensitive_name(h, phrases) or sensitive_name(raw, phrases):
            out.append((ci, False))
        elif looks_like_ssn_column([r[ci] for r in table.rows]):
            out.append((ci, True))
    return out


def drop_sensitive(table, keep=frozenset()):
    """Remove matching columns from the table everywhere it holds them, and list their header texts (P-READ-9, H10).
    A column whose header text is in keep stays. Changes the table in place and returns it."""
    found = [(ci, v) for ci, v in sensitive_columns(table) if table.headers[ci] not in keep]
    if not found:
        return table
    drop = {ci for ci, _ in found}
    keep_idx = [i for i in range(len(table.headers)) if i not in drop]
    remap = {old: new for new, old in enumerate(keep_idx)}

    def cut(cells):
        return [cells[i] for i in keep_idx if i < len(cells)]

    def cut_meta(meta):
        return {remap[c]: m for c, m in meta.items() if c in remap}

    table.sensitive_dropped = table.sensitive_dropped + [table.headers[ci] for ci, _ in found]
    table.sensitive_by_values += sum(1 for _, v in found if v)
    table.rows = [cut(r) for r in table.rows]
    table.meta = {(r, remap[c]): m for (r, c), m in table.meta.items() if c in remap}
    for s in table.source_rows:
        s.cells = cut(s.cells)
        s.meta = cut_meta(s.meta)
    if table.raw_headers:
        table.raw_headers = cut(table.raw_headers)
    dropped_names = {table.headers[i] for i in drop}
    table.headers = cut(table.headers)
    table.empty_columns = [h for h in table.empty_columns if h not in dropped_names]
    return table
