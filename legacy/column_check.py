"""
Column check: does each mapped column actually hold what the field expects?

Everything else in this tool guards the data. Nothing guarded the mapping, which
is the mistake a person is most likely to make and the one with the worst
consequence: a column mapped to the wrong field processes without complaint and
produces confidently wrong results.

This reads a sample of the values behind each mapped column and says plainly
when they do not look like the field they have been mapped to. It is a warning,
never a block. The operator knows their data and may have a good reason; the
point is that they are told before the run rather than discovering it after.
"""
from __future__ import annotations

import re
from collections import Counter

SAMPLE = 200          # values read per column, enough to judge without cost

UNIT_WORDS = (r"apt|apartment|ste|suite|unit|fl|floor|rm|room|bldg|building|"
              r"ph|penthouse|bsmt|basement|lobby|mezzanine|rear|front")

BOROUGHS = {"brooklyn", "queens", "bronx", "manhattan", "new york",
            "staten island"}


def _values(series):
    """A sample of the non-empty values in a column."""
    out = []
    for v in series.head(SAMPLE * 3):
        s = "" if v is None else str(v).strip()
        if s and s.lower() not in ("nan", "none", "null", "#n/a", "n/a"):
            out.append(s)
        if len(out) >= SAMPLE:
            break
    return out


def _pct(n, total):
    """A share, safe when the total is zero."""
    return 0.0 if not total else n / total


def _examples(vals, test, limit=3):
    """A few values that meet a test, shortened, for a warning."""
    out = []
    for v in vals:
        if test(v):
            out.append(v if len(v) <= 28 else v[:27] + "…")
        if len(out) >= limit:
            break
    return out


def _result(status, message, examples=None, fill=None):
    """A check result: status, message, examples, fill rate."""
    return {"status": status, "message": message,
            "examples": examples or [], "fill": fill}


def check_field(role, column, series):
    """
    Judge one mapped column. Returns status ok, check or problem, with a message
    written for the person doing the mapping rather than for a developer.
    """
    vals = _values(series)
    total_rows = len(series)
    filled = _pct(len(vals), min(total_rows, SAMPLE) or 1)

    # An always-empty column is worth pointing out, but it is not a mapping
    # mistake: a source that never records a middle initial is normal, and
    # City and State are filled from the ZIP later. Saying "problem" here
    # drowns the real warnings, which are the ones about wrong content.
    if not vals:
        if role in ("Middle_Initial", "Address_2", "City", "State"):
            return _result("ok",
                           "Always empty in this file, which is fine for this "
                           "field.", fill=0.0)
        return _result("check",
                       f"'{column}' is empty on every row, so this field will "
                       "be blank throughout.", fill=0.0)

    n = len(vals)

    # Mostly empty is a problem for a required field before anything else is
    # judged, because the rows with no value will all fail.
    if filled < 0.5 and role in ("Address_1", "Zip", "City", "State",
                                 "First_Name", "Last_Name", "Client_ID"):
        return _result("problem",
                       f"Only about {filled * 100:.0f}% of rows have a value "
                       f"in '{column}'. The rest would fail as missing.",
                       vals[:3], filled)

    if role in ("Address_1",):
        unit_like = sum(1 for v in vals
                        if re.match(r"(?i)^\s*(?:#|" + UNIT_WORDS + r")\b", v))
        has_number = sum(1 for v in vals if re.search(r"\d", v))
        digits_only = sum(1 for v in vals if re.fullmatch(r"[\d\-]+", v))
        # a street is a house number followed by words; a date, a phone number
        # or a code has digits too but no street after them
        street_like = sum(1 for v in vals
                          if re.match(r"^\s*\d+[\w\-]*\s+[A-Za-z]", v))
        datelike = sum(1 for v in vals
                       if re.fullmatch(r"\s*\d{1,4}[/.\-]\d{1,2}[/.\-]\d{1,4}\s*", v))
        if _pct(datelike, n) > 0.5:
            return _result("problem",
                           "These are dates, not street addresses.",
                           _examples(vals, lambda v: True), filled)
        if _pct(street_like, n) < 0.4 and _pct(unit_like, n) <= 0.4:
            return _result("problem",
                           "These do not look like street addresses. A street "
                           "is a house number followed by a street name.",
                           _examples(vals, lambda v: not re.match(
                               r"^\s*\d+[\w\-]*\s+[A-Za-z]", v)), filled)
        if _pct(unit_like, n) > 0.4:
            return _result("problem",
                           "These look like apartment or floor numbers rather "
                           "than street addresses. This column probably belongs "
                           "in Address 2, and the street may be in another "
                           "column.",
                           _examples(vals, lambda v: re.match(
                               r"(?i)^\s*(?:#|" + UNIT_WORDS + r")\b", v)),
                           filled)
        if _pct(digits_only, n) > 0.5:
            return _result("problem",
                           "These are only numbers, with no street name. An "
                           "address needs both.",
                           _examples(vals, lambda v: re.fullmatch(r"[\d\-]+", v)),
                           filled)
        if _pct(has_number, n) < 0.4:
            return _result("check",
                           "Most of these have no house number, so they may not "
                           "geocode.", vals[:3], filled)

    if role == "Zip":
        five = sum(1 for v in vals if re.fullmatch(r"\d{5}(-\d{4})?", v))
        four = sum(1 for v in vals if re.fullmatch(r"\d{4}", v))
        if _pct(five, n) < 0.5 and _pct(four, n) > 0.3:
            return _result("check",
                           "Most of these are four digits. A ZIP has five, so "
                           "these have probably lost a leading zero.",
                           _examples(vals, lambda v: re.fullmatch(r"\d{4}", v)),
                           filled)
        if _pct(five, n) < 0.5:
            return _result("problem",
                           "These do not look like ZIP codes. A ZIP is five "
                           "digits.",
                           _examples(vals, lambda v: not re.fullmatch(
                               r"\d{5}(-\d{4})?", v)), filled)

    if role == "State":
        two = sum(1 for v in vals if re.fullmatch(r"(?i)[a-z]{2}", v))
        if _pct(two, n) < 0.6:
            return _result("problem",
                           "A state should be two letters, such as NY.",
                           _examples(vals, lambda v: not re.fullmatch(
                               r"(?i)[a-z]{2}", v)), filled)

    if role == "City":
        digits = sum(1 for v in vals if re.search(r"\d", v))
        if _pct(digits, n) > 0.3:
            return _result("problem",
                           "Cities should not contain numbers. This column may "
                           "hold addresses rather than city names.",
                           _examples(vals, lambda v: re.search(r"\d", v)), filled)
        distinct = len({v.lower() for v in vals})
        known = sum(1 for v in vals if v.lower() in BOROUGHS)
        if distinct > max(25, n * 0.5) and _pct(known, n) < 0.2:
            return _result("check",
                           f"There are {distinct} different values here, and few "
                           "are boroughs. Check this is a city column.",
                           vals[:3], filled)

    if role in ("First_Name", "Last_Name"):
        digits = sum(1 for v in vals if re.search(r"\d", v))
        addr_like = sum(1 for v in vals
                        if re.match(r"^\d+\s+\w", v)
                        or re.search(r"(?i)\b(st|ave|road|rd|blvd|street)\b", v))
        if _pct(addr_like, n) > 0.3:
            return _result("problem",
                           "These look like addresses rather than names. The "
                           "columns may be matched one across.",
                           _examples(vals, lambda v: re.match(r"^\d+\s+\w", v)),
                           filled)
        if _pct(digits, n) > 0.2:
            return _result("problem",
                           "Names should not contain numbers.",
                           _examples(vals, lambda v: re.search(r"\d", v)), filled)

    if role == "Middle_Initial":
        long_ones = sum(1 for v in vals if len(v) > 1)
        if _pct(long_ones, n) > 0.6:
            return _result("check",
                           "These are full middle names. Only the first letter "
                           "is kept, which is fine, but check that is what you "
                           "want.", vals[:3], filled)

    if role == "Client_ID":
        counts = Counter(v.lower() for v in vals)
        repeats = sum(c for c in counts.values() if c > 1)
        if _pct(repeats, n) > 0.5:
            top = counts.most_common(1)[0]
            return _result("problem",
                           "Most rows share the same identifier, so this cannot "
                           f"identify a person. '{top[0]}' appears {top[1]} times "
                           "in the sample.", [top[0]], filled)
        if filled < 0.5:
            return _result("check",
                           f"Only about {filled * 100:.0f}% of rows have an "
                           "identifier. Duplicate checking needs it.",
                           vals[:3], filled)

    if role == "Program":
        numeric = sum(1 for v in vals if re.fullmatch(r"[\d.\-]+", v))
        if _pct(numeric, n) > 0.7:
            return _result("problem",
                           "These are numbers, which look like program codes "
                           "rather than program names. The count by program "
                           "needs names.", vals[:3], filled)

    if role == "Address_2":
        unit_like = sum(1 for v in vals
                        if re.match(r"(?i)^\s*(?:#|" + UNIT_WORDS + r"|\d)", v))
        if n > 5 and _pct(unit_like, n) < 0.3:
            return _result("check",
                           "These do not look like apartment or floor numbers. "
                           "Check what this column holds.", vals[:3], filled)

    if filled < 0.3 and role not in ("Middle_Initial", "Address_2"):
        return _result("check",
                       f"Only about {filled * 100:.0f}% of rows have a value "
                       "here.", vals[:3], filled)

    return _result("ok", f"Looks right. For example {', '.join(vals[:2])}.",
                   vals[:2], filled)


ROLE_WORDS = {
    "Program": ("program", "service", "svc", "activity", "enrollment",
                "project"),
    "Zip": ("zip", "postal"),
    "City": ("city", "borough", "town"),
    "State": ("state",),
    "Client_ID": ("id", "identifier", "client", "patient", "uid", "pid"),
    "First_Name": ("first", "given"),
    "Last_Name": ("last", "family", "surname"),
    "Address_1": ("address", "addr", "street"),
}


def _name_fits(role, col):
    """Whether a column's name says it holds this role."""
    words = set(re.split(r"[^a-z0-9]+", str(col).lower()))
    return bool(words & set(ROLE_WORDS.get(role, ())))


def better_column(role, current, frame, fields):
    """
    When the matched column is poor, name a column that looks right instead.

    This is what turns "the ZIP is blank on every row" into "the ZIP is blank on
    every row, but the column named Zip holds ZIP codes". The first is a
    puzzle; the second is a fix.
    """
    taken = {f.get("col") for f in fields if f.get("col") and f["role"] != role}
    # What matters is how many rows the switch would rescue: rows blank in the
    # current column that the candidate fills. A candidate that fills the same
    # rows and no more is not better, whatever its overall fill.
    def _blank(series):
        return series.map(lambda v: not str(v or "").strip()
                          or str(v).strip().lower() in ("nan", "none", "null"))

    cur_blank = (_blank(frame[current]) if current in frame.columns
                 else _pd_true(len(frame)))
    best, best_score = None, 0
    for col in frame.columns:
        if col == current or col in taken:
            continue
        res = check_field(role, col, frame[col])
        fill = res.get("fill") or 0.0
        if res["status"] != "ok" or fill < 0.5:
            continue
        rescued = int((cur_blank & ~_blank(frame[col])).sum())
        if rescued < max(2, int(len(frame) * 0.25)):
            continue
        # A column whose name says what it is beats one that merely passes the
        # content test, and for a program the name is required: a column of
        # people's names also "looks like" program names.
        named = _name_fits(role, col)
        if role not in ("Zip", "Address_1") and not named:
            continue
        if role == "Address_1" and not named:
            vals_c = _values(frame[col])
            strong = sum(1 for v in vals_c
                         if re.match(r"^\s*\d+[\w\-]*\s+[A-Za-z]", v))
            if not vals_c or strong / len(vals_c) < 0.7:
                continue
        score = rescued + (len(frame) if named else 0)
        if score > best_score:
            best, best_score = col, score
    return best


def _pd_true(n):
    """A series of True of the length given."""
    import pandas as pd
    return pd.Series([True] * n)


def check_mapping(fields, frame):
    """
    Check every mapped column on one table.

    fields is a list of {role, label, col}. Returns a per-field result plus a
    short verdict for the table as a whole.
    """
    out, problems, checks = {}, 0, 0
    for f in fields:
        col = f.get("col")
        if not col or col not in frame.columns:
            continue
        res = check_field(f["role"], col, frame[col])
        if res["status"] != "ok":
            alt = better_column(f["role"], col, frame, fields)
            if alt:
                res["better"] = alt
                res["message"] += (f" The column named '{alt}' looks like it "
                                   f"holds this field. Choose it instead.")
                res["status"] = "problem"
        out[f["role"]] = res
        if res["status"] == "problem":
            problems += 1
        elif res["status"] == "check":
            checks += 1

    # City and State are filled from the ZIP. When they are merely empty, that
    # is fine if the ZIP is sound, and a consequence of the ZIP if it is not;
    # either way it is not a separate problem to report.
    zip_status = out.get("Zip", {}).get("status")
    for role in ("City", "State"):
        res = out.get(role)
        if not res or res["status"] == "ok":
            continue
        empty_kind = "empty" in res["message"] or "have a value" in res["message"]
        if not empty_kind:
            continue
        if zip_status == "ok":
            out[role] = _result("ok",
                                "Mostly empty, which is fine: the ZIP fills it "
                                "in wherever it is blank.", fill=res.get("fill"))
        elif zip_status == "problem":
            out[role] = _result("ok",
                                "Mostly empty. It is filled from the ZIP, so "
                                "fixing the ZIP column above fixes this too.",
                                fill=res.get("fill"))
        else:
            continue
        if res["status"] == "problem":
            problems -= 1
        else:
            checks -= 1

    if problems:
        verdict = ("problem",
                   f"{problems} column(s) do not look like the field they are "
                   "matched to. Check these before processing; a column in the "
                   "wrong place produces confidently wrong results.")
    elif checks:
        verdict = ("check",
                   f"{checks} column(s) are worth a look, but nothing is "
                   "clearly wrong.")
    else:
        verdict = ("ok", "Every matched column holds what the field expects.")

    return {"fields": out, "status": verdict[0], "summary": verdict[1],
            "problems": problems, "checks": checks}
