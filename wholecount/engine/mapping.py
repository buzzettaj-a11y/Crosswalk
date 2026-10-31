"""Matching columns to fields by meaning (P-MAP-1, P-MAP-3, P-MAP-8), checking them against their values (P-MAP-2), and the one
question Process asks before it runs (process_blocks, P-MAP-7).

Scoring is by name only, over normalized header tokens. Assignment is global, so the result never depends on column order:
a column goes to the field that scores it highest, and two columns tied at the top for one field become a question.
"""
import re
from collections import Counter
from dataclasses import dataclass, field, replace

from wholecount.engine.read.sensitive import ssn_shaped
from wholecount.engine.schema import ADDRESS_FIELDS
from wholecount.settings.loader import load

PERSON_FIELDS = ("First_Name", "Middle_Initial", "Last_Name", "Client_ID", "Date_of_Birth")
NAME_FIELDS = ("First_Name", "Middle_Initial", "Last_Name")
PENALTY = 40

UNIT_WORDS = r"apt|apartment|ste|suite|unit|fl|floor|rm|room|bldg|building|ph|penthouse|bsmt|basement|lobby|mezzanine|rear|front"
_UNIT = re.compile(r"(?i)^\s*(?:#|(?:" + UNIT_WORDS + r")\b)")
_UNIT_OR_DIGIT = re.compile(r"(?i)^\s*(?:#|(?:" + UNIT_WORDS + r")|\d)")
_STREET = re.compile(r"^\s*\d+[\w\-]*\s+[A-Za-z]")
_DATE = re.compile(r"\s*\d{1,4}[/.\-]\d{1,2}[/.\-]\d{1,4}\s*")
_NUMERIC = re.compile(r"[\d.\-]+")
_DIGITS_ONLY = re.compile(r"[\d\-]+")
_FIVE = re.compile(r"\d{5}(-\d{4})?")
_FOUR = re.compile(r"\d{4}")
_TWO_LETTERS = re.compile(r"(?i)[a-z]{2}")
_ADDR_WORDS = re.compile(r"(?i)\b(st|ave|road|rd|blvd|street)\b")
_LEADING_NUMBER_WORD = re.compile(r"^\d+\s+\w")
BOROUGHS = {"brooklyn", "queens", "bronx", "manhattan", "new york", "staten island"}


# Columns and their profiles

@dataclass(frozen=True)
class ColumnRef:
    index: int
    name: str
    derived: bool = False
    derived_from: str | None = None
    derived_kind: str | None = None      # "split" or "calculated" (M03)


@dataclass(frozen=True)
class ColumnProfile:
    column: ColumnRef
    n_rows: int
    n_values: int
    distinct: int
    counts: dict                         # how many non-blank values have each shape
    top_count: int                       # how often the most common value occurs
    filled_mask: tuple                   # True where the row has a value
    samples: tuple = ()                  # up to three values, for the screen only

    @property
    def filled_share(self):
        return self.n_values / self.n_rows if self.n_rows else 0.0

    def share(self, kind):
        return self.counts.get(kind, 0) / self.n_values if self.n_values else 0.0

    @property
    def date_share(self):
        return self.share("date")


def _profile(col, values):
    vals = [v.strip() for v in values]
    filled = [v for v in vals if v]
    low = Counter(v.lower() for v in filled)
    counts = {
        "date": sum(1 for v in filled if _DATE.fullmatch(v)),
        "numeric": sum(1 for v in filled if _NUMERIC.fullmatch(v)),
        "unit": sum(1 for v in filled if _UNIT.match(v)),
        "unit_or_digit": sum(1 for v in filled if _UNIT_OR_DIGIT.match(v)),
        "street": sum(1 for v in filled if _STREET.match(v)),
        "ssn": sum(1 for v in filled if ssn_shaped(v)),
        "digits_only": sum(1 for v in filled if _DIGITS_ONLY.fullmatch(v)),
        "has_digit": sum(1 for v in filled if re.search(r"\d", v)),
        "five": sum(1 for v in filled if _FIVE.fullmatch(v)),
        "four": sum(1 for v in filled if _FOUR.fullmatch(v)),
        "two_letters": sum(1 for v in filled if _TWO_LETTERS.fullmatch(v)),
        "address_like": sum(1 for v in filled if _LEADING_NUMBER_WORD.match(v) or _ADDR_WORDS.search(v)),
        "borough": sum(1 for v in filled if v.lower() in BOROUGHS),
        "long": sum(1 for v in filled if len(v) > 1),
        "repeats": sum(c for c in low.values() if c > 1),
    }
    return ColumnProfile(col, len(vals), len(filled), len(low), counts, max(low.values(), default=0),
                         tuple(bool(v) for v in vals), tuple(filled[:3]))


def profile_columns(table, derived=()):
    """Profiles of the table's real columns, then of derived columns given as (ColumnRef, values)."""
    out = [_profile(ColumnRef(i, h), [r[i] for r in table.rows]) for i, h in enumerate(table.headers)]
    out += [_profile(ref, list(values)) for ref, values in derived]
    return out


# Scoring by name

_SETTINGS = None


def _settings():
    global _SETTINGS
    if _SETTINGS is None:
        s = load("mapping")
        _SETTINGS = {
            "extras_all": set(s["allowed_extras"]["all"]),
            "extras_address": set(s["allowed_extras"]["address"]),
            "deny": {k: set(v) for k, v in s["deny"].items()},
            "penalty": set(s["penalty"]["mailing"]),
            "synonyms": {f: {norm(x) for x in v} for f, v in s["synonyms"].items()},
            "phrases": {f: [[t for p in phrase for t in tokens(p)] for phrase in v] for f, v in s["phrases"].items()},
            "derived_suffix": dict(s["derived_suffix"]),
        }
    return _SETTINGS


def tokens(header):
    s = re.sub(r"([a-z])([A-Z])", r"\1 \2", header)
    s = re.sub(r"([A-Z]+)([A-Z][a-z])", r"\1 \2", s)
    s = re.sub(r"([A-Za-z])(\d)", r"\1 \2", s)
    return [t for t in re.split(r"[^a-z0-9]+", s.lower()) if t]


def norm(header):
    return "_".join(tokens(header))


def _deny_groups(field_key):
    groups = []
    if field_key in PERSON_FIELDS:
        groups.append("person_fields")
    if field_key in ADDRESS_FIELDS:
        groups.append("address_fields")
    if field_key in NAME_FIELDS:
        groups.append("name_fields")
    if field_key == "Client_ID":
        groups.append("client_id")
    if field_key == "Program":
        groups.append("program")
    return groups


def _has_run(hay, needle):
    return any(hay[i:i + len(needle)] == needle for i in range(len(hay) - len(needle) + 1))


def name_score(fld, col, profile=None):
    """The score of a column for a field, from its name (and, for Program, a date check on its values)."""
    st = _settings()
    toks = tokens(col.name)
    if not toks:
        return 0
    if col.derived:
        # A step's column is named <source>_<suffix> (M03). The suffix says the field. A calculated ZIP fills Zip, a cleaned
        # column scores as its source column does, and any other derived column is scored by its own name.
        suffix = col.name.rsplit("_", 1)[-1].lower() if "_" in col.name else ""
        if col.derived_kind == "calculated":
            return 90 if fld.key == "Zip" and suffix != "note" else 0
        suffix_field = st["derived_suffix"].get(suffix)
        if suffix_field:
            return 90 if suffix_field == fld.key else 0
        if col.derived_kind == "clean" and col.derived_from:
            return name_score(fld, ColumnRef(col.index, col.derived_from), profile)
        col = ColumnRef(col.index, col.name)
    if any(set(toks) & st["deny"][g] for g in _deny_groups(fld.key)):
        return 0
    if fld.key == "Address_1" and toks[-1] == "2":
        return 0
    if fld.key == "Program" and profile is not None and profile.n_values and profile.counts["date"] * 10 >= profile.n_values * 6:
        return 0
    address = fld.key in ADDRESS_FIELDS
    penalized = address and bool(set(toks) & st["penalty"])
    n = "_".join(toks)
    base = 0
    if n in (norm(fld.key), norm(fld.label)):
        base = 100
    elif n in st["synonyms"].get(fld.key, ()):
        base = 90
    else:
        allowed = st["extras_all"] | (st["extras_address"] | st["penalty"] if address else set())
        for phrase in st["phrases"].get(fld.key, []):
            if _has_run(toks, phrase):
                rest = list(toks)
                for t in phrase:
                    rest.remove(t)
                if set(rest) <= allowed:
                    base = 60
                    break
    if not base:
        return 0
    return max(base - PENALTY, 1) if penalized else base


# Assignment

@dataclass(frozen=True)
class FieldAssignment:
    field: str
    column: ColumnRef
    score: int
    alternatives: tuple = ()
    chosen: bool = False                 # the operator picked it


@dataclass(frozen=True)
class MappingQuestion:
    field: str
    candidates: tuple                    # ColumnRefs tied at the top


@dataclass(frozen=True)
class TableMapping:
    table_key: str
    assignments: tuple
    questions: tuple = ()
    checks: dict = field(default_factory=dict, compare=False)

    def column_for(self, field_key):
        for a in self.assignments:
            if a.field == field_key:
                return a.column
        return None

    def as_names(self):
        return {a.field: a.column.name for a in self.assignments}

    def with_choice(self, field_key, column):
        """The operator's pick: this column fills this field, leaves any other field, and settles any question for the field."""
        kept = tuple(a for a in self.assignments if a.field != field_key and a.column != column)
        old = next((a for a in self.assignments if a.field == field_key), None)
        alts = old.alternatives if old else ()
        new = FieldAssignment(field_key, column, old.score if old and old.column == column else 0, alts, chosen=True)
        return replace(self, assignments=tuple(sorted(kept + (new,), key=lambda a: a.field)),
                       questions=tuple(q for q in self.questions if q.field != field_key))

    def without(self, field_key):
        return replace(self, assignments=tuple(a for a in self.assignments if a.field != field_key))


def _scores(schema, profiles):
    fields = schema.enabled_fields()
    return {(f.key, p.column): s for f in fields for p in profiles if (s := name_score(f, p.column, p))}


def _assign(field_order, scores, columns):
    """Rounds of global assignment over the given columns. Returns ({field: (column, score)}, [MappingQuestion])."""
    assigned, questions, settled, used = {}, [], set(), set()
    while True:
        best = {}
        for c in columns:
            if c in used:
                continue
            options = {f: s for (f, cc), s in scores.items() if cc == c and f not in settled}
            if options:
                top = max(options.values())
                best[c] = (top, {f for f, s in options.items() if s == top})
        changed = False
        round_used = set()
        pools = []
        for f in field_order:
            if f in settled:
                continue
            pool = [(s, c) for c, (s, fs) in best.items() if f in fs]
            if pool:
                pools.append((max(s for s, _ in pool), field_order.index(f), f, pool))
        for top, _, f, pool in sorted(pools, key=lambda p: (-p[0], p[1])):
            tops = [c for s, c in pool if s == top and c not in round_used]
            if not tops:
                continue
            if len(tops) == 1:
                assigned[f] = (tops[0], top)
                round_used.add(tops[0])
            else:
                questions.append(MappingQuestion(f, tuple(sorted(tops, key=lambda c: c.name))))
            settled.add(f)
            changed = True
        used |= round_used
        if not changed:
            return assigned, questions


def auto_map(schema, profiles, table_key=""):
    """The mapping by meaning. Derived columns fill a field only as P-MAP-3 and P-MAP-8 allow."""
    scores = _scores(schema, profiles)
    order = [f.key for f in schema.enabled_fields()]
    real = [p.column for p in profiles if not p.column.derived]
    derived = [p.column for p in profiles if p.column.derived]
    assigned, questions = _assign(order, scores, real)
    question_fields = {q.field for q in questions}

    def real_scores_for(f):
        return any(scores.get((f, c)) for c in real)

    for f in order:
        cands = sorted([(scores[(f, d)], d) for d in derived if scores.get((f, d))], key=lambda x: (-x[0], x[1].name))
        if not cands or f in question_fields:
            continue
        chosen = assigned.get(f, (None, 0))[0]
        calculated = [x for x in cands if x[1].derived_kind == "calculated"]
        from_chosen = [x for x in cands if chosen is not None and x[1].derived_from == chosen.name]
        if f == "Zip" and calculated:
            assigned[f] = (calculated[0][1], calculated[0][0])
        elif from_chosen:
            assigned[f] = (from_chosen[0][1], from_chosen[0][0])
        elif not real_scores_for(f) and f not in assigned:
            top = cands[0][0]
            tops = [d for s, d in cands if s == top]
            if len(tops) == 1:
                assigned[f] = (tops[0], top)
            else:
                questions.append(MappingQuestion(f, tuple(tops)))

    out = []
    for f in order:
        if f not in assigned:
            continue
        col, s = assigned[f]
        alts = sorted([(sc, c) for (ff, c), sc in scores.items() if ff == f and c != col], key=lambda x: (-x[0], x[1].name))
        out.append(FieldAssignment(f, col, s, tuple(c for _, c in alts)))
    return TableMapping(table_key, tuple(sorted(out, key=lambda a: a.field)), tuple(questions))


# Column check (P-MAP-2)

@dataclass(frozen=True)
class FieldCheck:
    status: str                          # ok, check or problem
    reason_id: str
    params: dict = field(default_factory=dict)
    better: ColumnRef | None = None


def _pct(n):
    return int(round(n * 100))


def check_field(field_key, p):
    """Does the mapped column hold what the field expects? A warning never blocks."""
    n, filled = p.n_values, p.filled_share
    if not n:
        if field_key in ("Middle_Initial", "Address_2", "City", "State"):
            return FieldCheck("ok", "col_empty_ok")
        return FieldCheck("check", "col_empty")
    if filled < 0.5 and field_key in ("Address_1", "Zip", "City", "State", "First_Name", "Last_Name", "Client_ID"):
        return FieldCheck("problem", "col_mostly_empty", {"percent": _pct(filled)})
    sh = p.share
    if field_key == "Address_1":
        if sh("date") > 0.5:
            return FieldCheck("problem", "col_address1_dates")
        if sh("unit") > 0.4:
            return FieldCheck("problem", "col_address1_mostly_units")
        if sh("street") < 0.4:
            return FieldCheck("problem", "col_address1_not_streets")
        if sh("digits_only") > 0.5:
            return FieldCheck("problem", "col_address1_digits_only")
        if sh("has_digit") < 0.4:
            return FieldCheck("check", "col_address1_no_house_number")
    if field_key == "Zip":
        if sh("five") < 0.5 and sh("four") > 0.3:
            return FieldCheck("check", "col_zip_lost_zero")
        if sh("five") < 0.5:
            return FieldCheck("problem", "col_zip_not_zips")
    if field_key == "State" and sh("two_letters") < 0.6:
        return FieldCheck("problem", "col_state_not_two_letters")
    if field_key == "City":
        if sh("has_digit") > 0.3:
            return FieldCheck("problem", "col_city_has_digits")
        if p.distinct > max(25, n * 0.5) and sh("borough") < 0.2:
            return FieldCheck("check", "col_city_many_values", {"distinct": p.distinct})
    if field_key in ("First_Name", "Last_Name"):
        if sh("address_like") > 0.3:
            return FieldCheck("problem", "col_name_looks_like_address")
        if sh("has_digit") > 0.2:
            return FieldCheck("problem", "col_name_has_digits")
        if n > 10 and p.top_count / n > 0.8:
            return FieldCheck("problem", "col_name_mostly_one_value", {"percent": _pct(p.top_count / n)})
    if field_key == "Middle_Initial" and sh("long") > 0.6:
        return FieldCheck("check", "col_middle_full_names")
    if field_key == "Client_ID":
        if sh("repeats") > 0.5:
            return FieldCheck("problem", "col_id_repeats", {"times": p.top_count})
    if field_key == "Program":
        if sh("date") > 0.5:
            return FieldCheck("problem", "col_program_looks_like_dates")
        if sh("numeric") > 0.7:
            return FieldCheck("problem", "col_program_looks_like_codes")
    if field_key == "Address_2":
        if n > 5 and sh("street") >= 0.5:
            return FieldCheck("check", "col_address2_mostly_streets")
        if n > 5 and sh("unit_or_digit") < 0.3:
            return FieldCheck("check", "col_address2_not_units")
    if filled < 0.3 and field_key not in ("Middle_Initial", "Address_2"):
        return FieldCheck("check", "col_low_fill", {"percent": _pct(filled)})
    return FieldCheck("ok", "col_ok")


def better_column(field_key, current, profiles, candidates, taken):
    """A column that would rescue rows the current one leaves blank: it passes its own check, fills at least half the rows,
    and rescues at least 2 rows or a quarter of them. Candidates are the columns that score for the field by name."""
    best, best_rescued = None, 0
    need = max(2, int(current.n_rows * 0.25))
    for p in profiles:
        c = p.column
        if c == current.column or c not in candidates or c in taken:
            continue
        if check_field(field_key, p).status != "ok" or p.filled_share < 0.5:
            continue
        rescued = sum(1 for a, b in zip(current.filled_mask, p.filled_mask) if not a and b)
        if rescued < need:
            continue
        if rescued > best_rescued or (rescued == best_rescued and best is not None and c.name < best.name):
            best, best_rescued = c, rescued
    return best


def check_mapping(schema, mapping, profiles):
    """Every mapped column checked. A check that finds a better column becomes a problem offering it (the one-click fix)."""
    by_col = {p.column: p for p in profiles}
    taken = {a.column for a in mapping.assignments}
    out = {}
    for a in mapping.assignments:
        p = by_col.get(a.column)
        if p is None:
            continue
        res = check_field(a.field, p)
        if res.status != "ok":
            fld = schema.get(a.field)
            candidates = {pp.column for pp in profiles if name_score(fld, pp.column, pp)}
            better = better_column(a.field, p, profiles, candidates, taken - {a.column})
            if better is not None:
                res = replace(res, status="problem", better=better)
        out[a.field] = res
    return replace(mapping, checks=out)


# What blocks Process (P-MAP-2, P-MAP-7)

@dataclass(frozen=True)
class ProcessBlock:
    table_key: str
    field: str
    kind: str                            # missing_required or ssn_shaped_id
    also: str | None = None              # a second field the block names (Date_of_Birth beside Client_ID)


@dataclass(frozen=True)
class MappingWarning:
    table_key: str
    field: str
    kind: str                            # custom_required_no_column


def _has_column(mapping, field_key):
    return mapping.column_for(field_key) is not None and field_key not in {q.field for q in mapping.questions}


def process_blocks(schema, mappings, defaults=(), profiles=None):
    """The blocks for every table, named by table and field. Only `required` fields and SSN-shaped IDs can block."""
    from wholecount.engine.defaults import default_for

    profiles = profiles or {}
    out = []
    for table_key, m in mappings.items():
        def supplied(f):
            return _has_column(m, f) or default_for(defaults, table_key, f) is not None

        for f in schema.enabled_fields():
            if f.key == "Client_ID":
                if f.required and not supplied("Client_ID") and not (schema.is_enabled("Date_of_Birth") and supplied("Date_of_Birth")):
                    out.append(ProcessBlock(table_key, "Client_ID", "missing_required", also="Date_of_Birth"))
                continue
            if f.builtin and f.required and not supplied(f.key):
                out.append(ProcessBlock(table_key, f.key, "missing_required"))
            elif not f.builtin and f.needed_to_count and not supplied(f.key):
                out.append(ProcessBlock(table_key, f.key, "missing_required"))
        col = m.column_for("Client_ID")
        prof = {p.column: p for p in profiles.get(table_key, ())}.get(col)
        if col is not None and prof is not None and prof.counts["ssn"] * 2 > prof.n_values:
            out.append(ProcessBlock(table_key, "Client_ID", "ssn_shaped_id"))
    return out


def mapping_warnings(schema, mappings, defaults=()):
    from wholecount.engine.defaults import default_for

    out = []
    for table_key, m in mappings.items():
        for f in schema.enabled_fields():
            if not f.builtin and f.required and not f.needed_to_count and not _has_column(m, f.key) \
                    and default_for(defaults, table_key, f.key) is None:
                out.append(MappingWarning(table_key, f.key, "custom_required_no_column"))
    return out
