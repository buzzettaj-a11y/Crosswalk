"""P-READ-3: invisible characters and spacing, applied to every cell. Case, digits and punctuation are never changed."""
import re
import unicodedata
from dataclasses import dataclass, fields

ZERO_WIDTH = frozenset("​‌‍⁠")
BOM = "﻿"
SOFT_HYPHEN = "­"
SPACE_CONTROLS = frozenset("\t\r\n")
_RUNS = re.compile(" {2,}")


@dataclass
class CleanCounts:
    """How many of each invisible group were removed. These go to the quality report, never a value."""

    zero_width: int = 0
    bom: int = 0
    soft_hyphen: int = 0
    control: int = 0
    apostrophe: int = 0

    def add(self, other):
        for f in fields(self):
            setattr(self, f.name, getattr(self, f.name) + getattr(other, f.name))
        return self

    def total(self):
        return sum(getattr(self, f.name) for f in fields(self))

    def as_dict(self):
        return {f.name: getattr(self, f.name) for f in fields(self)}


def _is_space(ch):
    return ch in SPACE_CONTROLS or ch == " " or unicodedata.category(ch) in ("Zs", "Zl", "Zp")


def clean_cell(text):
    """(cleaned text, CleanCounts). NUL and other controls are removed, not turned into spaces."""
    counts = CleanCounts()
    if not text:
        return "", counts
    out = []
    for ch in text:
        if ch in ZERO_WIDTH:
            counts.zero_width += 1
        elif ch == BOM:
            counts.bom += 1
        elif ch == SOFT_HYPHEN:
            counts.soft_hyphen += 1
        elif _is_space(ch):
            out.append(" ")
        elif ord(ch) < 0x20 or ch == "\x7f":
            counts.control += 1
        else:
            out.append(ch)
    s = _RUNS.sub(" ", "".join(out)).strip()
    if len(s) > 1 and s[0] == "'":
        s = s[1:].lstrip()
        counts.apostrophe += 1
    return s, counts
