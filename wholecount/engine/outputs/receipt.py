"""The receipt (SPEC 9.4): what was written, read back from the folder, and the notes that apply."""
from dataclasses import dataclass

from wholecount import copy


@dataclass(frozen=True)
class ReceiptFile:
    path: str
    rows: int
    columns: int
    time_iso: str


@dataclass(frozen=True)
class Receipt:
    files: tuple
    notes: tuple                          # (copy key, params)


def receipt_text(receipt):
    lines = [copy.get("receipt.title")]
    for f in receipt.files:
        lines.append(copy.get("receipt.file", path=f.path, rows=f.rows, columns=f.columns, time=f.time_iso))
    lines.append(copy.get("receipt.nothing_else"))
    lines += [copy.get(k, **params) for k, params in receipt.notes]
    return "\r\n".join(lines) + "\r\n"
