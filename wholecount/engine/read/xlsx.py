"""Reading .xlsx workbooks (P-READ-1). Every sheet is read, hidden ones too, and each cell's number format is kept for numbers and dates."""
import datetime as dt
import re

import openpyxl

from wholecount.engine.read.model import CellMeta, UnreadableFile

_ZEROS = re.compile(r"0+")
_FIXED = re.compile(r"[#,]*0\.(0+)")


def cell_text(value, number_format="General"):
    """The text a cell shows, without Excel's guessing. None is empty, and a date is ISO."""
    if value is None:
        return ""
    if isinstance(value, bool):
        return "TRUE" if value else "FALSE"
    fmt = number_format or "General"
    if isinstance(value, int) or (isinstance(value, float) and value.is_integer()):
        text = str(int(value))
        if _ZEROS.fullmatch(fmt) and not text.startswith("-"):
            text = text.zfill(len(fmt))
        return text
    if isinstance(value, float):
        m = _FIXED.fullmatch(fmt)
        return f"{value:.{len(m.group(1))}f}" if m else repr(value)
    if isinstance(value, dt.datetime):
        if value.hour or value.minute or value.second or value.microsecond:
            return value.strftime("%Y-%m-%d %H:%M:%S")
        return value.strftime("%Y-%m-%d")
    if isinstance(value, dt.date):
        return value.strftime("%Y-%m-%d")
    if isinstance(value, dt.time):
        return value.strftime("%H:%M:%S")
    return str(value)


def cell_meta(value, number_format):
    if isinstance(value, bool) or value is None:
        return None
    if isinstance(value, (int, float)):
        return CellMeta("number", number_format or "General")
    if isinstance(value, (dt.datetime, dt.date, dt.time)):
        return CellMeta("date", number_format or "General")
    return None


def read_sheets(fileobj):
    """[(sheet name, hidden, [[(value, number_format), ...], ...]), ...]. Raises UnreadableFile for a damaged workbook."""
    try:
        wb = openpyxl.load_workbook(fileobj, read_only=True, data_only=True)
    except Exception:
        raise UnreadableFile("bad_workbook") from None
    out = []
    try:
        for ws in wb.worksheets:
            rows = []
            for row in ws.iter_rows():
                rows.append([(getattr(c, "value", None), getattr(c, "number_format", "General")) for c in row])
            out.append((ws.title, getattr(ws, "sheet_state", "visible") != "visible", rows))
    except UnreadableFile:
        raise
    except Exception:
        raise UnreadableFile("bad_workbook") from None
    finally:
        wb.close()
    return out
