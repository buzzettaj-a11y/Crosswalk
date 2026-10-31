"""Dates, including date of birth (P-STD-6, B-13, B-14, B-15, B-16). Nothing is guessed: no silent swap, no century pivot without
the operator's rule, and no Excel serial conversion. `today` is always a parameter (H3)."""
import datetime as dt
import re
from dataclasses import dataclass
from functools import lru_cache

from wholecount.engine.dateorder import DateOrder
from wholecount.settings.loader import load

_ISO = re.compile(r"\s*([0-9]{4})([-/.])([0-9]{1,2})\2([0-9]{1,2})(?:[ T][0-9:]+)?\s*")
_ABY = re.compile(r"\s*([0-9]{1,2})([-/.])([0-9]{1,2})\2([0-9]{4}|[0-9]{2})\s*")
_FIVE = re.compile(r"[0-9]{5}")


@dataclass(frozen=True)
class DateContext:
    order: DateOrder | None = None
    state: str = "not_needed"
    answered: bool = False
    pivot: int | None = None


def date_context(decision=None, setting=None):
    """From M02's DateDecision and DateFieldSetting."""
    order = setting.order if setting is not None and setting.order is not None else (decision.order if decision else None)
    answered = bool(decision and decision.answered) or (setting is not None and setting.order is not None)
    pivot = setting.pivot.pivot if setting is not None and setting.pivot is not None else None
    return DateContext(order, decision.state if decision else "not_needed", answered, pivot)


@dataclass(frozen=True)
class DateParse:
    iso: str | None
    reason: str | None = None
    readings: tuple = ()          # both readings of a two-digit year, or the date an Excel number would be


@lru_cache(maxsize=1)
def limits():
    s = load("standardize")
    return s["earliest_year"], s["max_age"]


def excel_serial(n):
    """The date Excel would show for a serial: 1 to 59 count from 1899-12-31, 60 has no date, 61 and up count from 1899-12-30."""
    if n <= 0 or n == 60:
        return None
    base = dt.date(1899, 12, 31) if n < 60 else dt.date(1899, 12, 30)
    try:
        return (base + dt.timedelta(days=n)).isoformat()
    except OverflowError:
        return None


def _real(y, m, d):
    try:
        return dt.date(y, m, d).isoformat()
    except ValueError:
        return None


def _ages(born, today):
    return today.year - born.year - ((today.month, today.day) < (born.month, born.day))


def dob_check(iso, today):
    """None, dob_out_of_range or dob_age_over_115. Out of range means not a valid date of birth."""
    earliest, max_age = limits()
    born = dt.date.fromisoformat(iso)
    if born > today or born.year < earliest:
        return "dob_out_of_range"
    if _ages(born, today) > max_age:
        return "dob_age_over_115"
    return None


def parse_date(text, kind, ctx, today, dob=False):
    ctx = ctx or DateContext()
    t = text.strip()
    if not t:
        return DateParse(None)
    if kind == "date":
        m = _ISO.fullmatch(t)
        iso = _real(int(m.group(1)), int(m.group(3)), int(m.group(4))) if m else None
        return _dob(DateParse(iso), today, dob) if iso else DateParse(None, "date_not_readable")
    if _FIVE.fullmatch(t):
        s = excel_serial(int(t))
        return DateParse(None, "date_excel_number", (s,) if s else ())
    if re.fullmatch(r"[0-9]+(?:\.[0-9]+)?", t):
        return DateParse(None, "date_not_readable")
    m = _ISO.fullmatch(t)
    if m:
        iso = _real(int(m.group(1)), int(m.group(3)), int(m.group(4)))
        return _dob(DateParse(iso), today, dob) if iso else DateParse(None, "date_impossible")
    m = _ABY.fullmatch(t)
    if not m:
        return DateParse(None, "date_not_readable")
    a, b, year = int(m.group(1)), int(m.group(3)), m.group(4)
    both_ways = ctx.state == "ask_both_ways"
    if both_ways and not ctx.answered:
        return DateParse(None, "date_both_ways")
    if a > 12 and b > 12:
        return DateParse(None, "date_impossible")
    if a > 12:
        readable = DateOrder.DAY_FIRST
    elif b > 12:
        readable = DateOrder.MONTH_FIRST
    elif a == b:
        readable = None
    else:
        readable = "either"
    in_force = ctx.order if (ctx.answered or ctx.state == "resolved") else None
    if readable in (DateOrder.DAY_FIRST, DateOrder.MONTH_FIRST):
        if in_force is not None and in_force != readable:
            return DateParse(None, "date_both_ways" if both_ways else "date_impossible")
        order = readable
    elif readable is None:
        order = in_force or DateOrder.MONTH_FIRST
    else:
        if in_force is None:
            return DateParse(None, "date_order_unclear")
        order = in_force
    month, day = (a, b) if order == DateOrder.MONTH_FIRST else (b, a)
    if len(year) == 2:
        yy = int(year)
        if ctx.pivot is None:
            readings = tuple(r for r in (_real(1900 + yy, month, day), _real(2000 + yy, month, day)) if r)
            return DateParse(None, "date_two_digit_year" if readings else "date_impossible", readings)
        full = 2000 + yy if yy <= ctx.pivot else 1900 + yy
    else:
        full = int(year)
    iso = _real(full, month, day)
    if iso is None:
        return DateParse(None, "date_impossible")
    return _dob(DateParse(iso), today, dob)


def _dob(p, today, dob):
    if not dob or p.iso is None:
        return p
    reason = dob_check(p.iso, today)
    return DateParse(p.iso, reason) if reason else p
