"""Date order per table and date field (P-MAP-5), and the two-digit-year rule (P-MAP-6). Counts evidence only; M04 reads dates."""
import enum
import re
from dataclasses import dataclass

_SLASHED = re.compile(r"\s*(\d{1,2})([/.\-])(\d{1,2})\2(\d{2}|\d{4})\s*")


class DateOrder(enum.Enum):
    MONTH_FIRST = "month_first"
    DAY_FIRST = "day_first"


@dataclass(frozen=True)
class DateEvidence:
    month_first_only: int = 0
    day_first_only: int = 0
    either: int = 0
    other: int = 0


STATES = ("not_needed", "resolved", "ask_no_evidence", "ask_both_ways")


@dataclass(frozen=True)
class DateDecision:
    order: DateOrder | None
    state: str
    answered: bool = False


def _skip(i, meta):
    m = meta.get(i) if meta else None
    return m is not None and getattr(m, "kind", None) == "date"


def collect_evidence(values, meta=None):
    """Counts over values written as two numbers and a year with one separator used twice. ISO forms and .xlsx date cells are
    skipped. meta maps a value's index to its CellMeta."""
    mf = df = either = other = 0
    for i, v in enumerate(values):
        if _skip(i, meta):
            continue
        m = _SLASHED.fullmatch(v)
        if not m:
            continue
        a, b = int(m.group(1)), int(m.group(3))
        if a <= 12 < b:
            mf += 1
        elif b <= 12 < a:
            df += 1
        elif a <= 12 and b <= 12:
            either += 1
        else:
            other += 1
    return DateEvidence(mf, df, either, other)


def decide(evidence, answer=None):
    if evidence.month_first_only and evidence.day_first_only:
        state, order = "ask_both_ways", None
    elif evidence.month_first_only:
        state, order = "resolved", DateOrder.MONTH_FIRST
    elif evidence.day_first_only:
        state, order = "resolved", DateOrder.DAY_FIRST
    elif evidence.either:
        state, order = "ask_no_evidence", None
    else:
        state, order = "not_needed", None
    if answer is not None:
        return DateDecision(DateOrder(answer), state, answered=True)
    return DateDecision(order, state)


@dataclass(frozen=True)
class TwoDigitRule:
    """"Two-digit years up to NN mean 20NN, otherwise 19NN." """

    pivot: int

    def __post_init__(self):
        if isinstance(self.pivot, bool) or not isinstance(self.pivot, int) or not 0 <= self.pivot <= 99:
            raise ValueError("a pivot is 0 to 99")

    def century(self, yy):
        return 2000 + yy if yy <= self.pivot else 1900 + yy


@dataclass(frozen=True)
class DateFieldSetting:
    """What the operator settled for one table and date field. Feeds the session's date_orders."""

    order: DateOrder | None = None
    pivot: TwoDigitRule | None = None


def suggest_pivot(field_key, today):
    return today.year % 100 if field_key == "Date_of_Birth" else None


def rule_needed(values, meta=None):
    """True only when the column holds a non-ISO date written with a two-digit year."""
    for i, v in enumerate(values):
        if _skip(i, meta):
            continue
        m = _SLASHED.fullmatch(v)
        if m and len(m.group(4)) == 2:
            return True
    return False
