"""Tidy-up steps (P-PREP). Steps only add columns: a source cell is never changed (H6).

Steps run in the listed order and may read an earlier step's output. Each step that changes nothing is amber, with a reason ID.
Output names follow the old build (<col>_street, <col>_first and so on), so the mapper's derived-column rule (P-MAP-3) can tell
which field each one fills.
"""
import re
import unicodedata
from dataclasses import dataclass, field, replace

from wholecount.engine.mapping import ColumnRef, tokens
from wholecount.engine.prepare import calc_zip
from wholecount.engine.prepare.address import parse_address
from wholecount.engine.prepare.casing import title_address, title_name
from wholecount.engine.prepare.names import parse_name
from wholecount.settings.loader import load

KINDS = ("clean", "split_delim", "split_address", "split_name", "calc_zip")
DERIVED_KIND = {"clean": "clean", "split_delim": "split", "split_address": "split", "split_name": "split", "calc_zip": "calculated"}
DELIMITERS = {"comma": ",", "tab": "\t", "pipe": "|", "semicolon": ";", "colon": ":", "space": " ", "slash": "/"}
ADDRESS_OUTPUTS = (("street", "street"), ("address2", "unit"), ("city", "city"), ("state", "state"), ("zip", "zip"), ("extra", "extra"))
NAME_OUTPUTS = ("first", "middle", "last", "title", "credential", "suffix", "extra")

_SMART = {"‘": "'", "’": "'", "‚": "'", "‛": "'", "“": '"', "”": '"', "„": '"',
          "–": "-", "—": "-", "―": "-", "−": "-", "…": "..."}
_JUNK = re.compile(r"[\^~`|<>{}\[\]\\*]")
_EDGE = re.compile(r"^[\s,;:.\-|]+|[\s,;:.\-|]+$")


@dataclass(frozen=True)
class Step:
    step_id: str
    kind: str
    params: dict
    origin: str = "added"         # proposed or added
    removed: bool = False

    def __post_init__(self):
        if self.kind not in KINDS:
            raise ValueError(self.kind)
        if self.origin not in ("proposed", "added"):
            raise ValueError(self.origin)


@dataclass(frozen=True)
class PreparedColumn:
    name: str
    values: tuple
    step_id: str
    source_column: str
    kind: str                     # the step kind that made it


@dataclass(frozen=True)
class StepResult:
    step_id: str
    amber: bool = False
    amber_reason: str | None = None
    counts: dict = field(default_factory=dict)


@dataclass
class PreparedTable:
    table: object
    columns: list
    results: list
    row_reasons: dict             # row index -> [(reason ID, column name)]

    def names(self):
        return list(self.table.headers) + [c.name for c in self.columns]

    def values(self, name):
        if name in self.table.headers:
            i = self.table.headers.index(name)
            return [r[i] for r in self.table.rows]
        for c in self.columns:
            if c.name == name:
                return list(c.values)
        raise KeyError(name)

    def column_refs(self):
        base = len(self.table.headers)
        return [(ColumnRef(base + i, c.name, derived=True, derived_from=c.source_column, derived_kind=DERIVED_KIND[c.kind]),
                 list(c.values)) for i, c in enumerate(self.columns)]

    def reasons_by_id(self):
        out = {}
        for flags in self.row_reasons.values():
            for rid, _ in flags:
                out[rid] = out.get(rid, 0) + 1
        return out


# The rules

def sanitize(text):
    t = unicodedata.normalize("NFKC", text)
    for k, v in _SMART.items():
        t = t.replace(k, v)
    t = "".join(ch for ch in t if not unicodedata.category(ch).startswith("C"))
    t = _JUNK.sub(" ", t)
    t = re.sub(r"([.,;:!?\-])\1+", r"\1", t)
    return re.sub(r"\s+", " ", t).strip()


def clean_value(v, case="none", strip_junk=False, strip_edge_punctuation=False):
    s = re.sub(r"\s+", " ", v).strip()
    if strip_junk:
        s = sanitize(s)
    if strip_edge_punctuation:
        s = _EDGE.sub("", s).strip()
    if case == "title_name":
        s = title_name(s)
    elif case == "title_address":
        s = title_address(s)
    elif case == "upper":
        s = s.upper()
    elif case == "lower":
        s = s.lower()
    elif case != "none":
        raise ValueError(case)
    return s


def _unique(name, taken):
    out, n = name, 2
    while out in taken:
        out = f"{name}_{n}"
        n += 1
    taken.add(out)
    return out


def apply_steps(table, steps, resolver=None):
    """A PreparedTable with every live step's columns, in order. The table itself is never changed."""
    prepared = PreparedTable(table, [], [], {})
    taken = set(table.headers)
    for step in steps:
        if step.removed:
            continue
        cols, result = _run(prepared, step, resolver)
        for name, values, source in cols:
            prepared.columns.append(PreparedColumn(_unique(name, taken), tuple(values), step.step_id, source, step.kind))
        prepared.results.append(result)
    return prepared


def _flag(prepared, row, reason, column):
    prepared.row_reasons.setdefault(row, []).append((reason, column))


def _run(prepared, step, resolver):
    p, k = step.params, step.kind
    if k == "clean":
        cols, changed = [], 0
        for c in p["columns"]:
            before = prepared.values(c)
            after = [clean_value(v, p.get("case", "none"), p.get("strip_junk", False), p.get("strip_edge_punctuation", False))
                     for v in before]
            changed += sum(1 for a, b in zip(after, before) if a != b)
            cols.append((f"{c}_clean", after, c))
        return cols, StepResult(step.step_id, changed == 0, "clean_changed_nothing" if changed == 0 else None, {"changed": changed})
    if k == "split_delim":
        col = p["column"]
        d = p.get("custom") or DELIMITERS[p["delimiter"]]
        maxsplit = p.get("maxsplit", 0)
        vals = prepared.values(col)
        split = [[x.strip() for x in (v.split(d, maxsplit) if maxsplit else v.split(d))] for v in vals]
        width = max((len(s) for s in split), default=1)
        names = [n for n in p.get("names", []) if n.strip()]
        cols = [(names[i] if i < len(names) else f"{col}_{i + 1}", [s[i] if i < len(s) else "" for s in split], col)
                for i in range(width)]
        found = sum(1 for v in vals if d in v)
        return cols, StepResult(step.step_id, found == 0, "split_found_no_delimiter" if found == 0 else None, {"split": found})
    if k == "split_address":
        col = p["column"]
        parsed = [parse_address(v) for v in prepared.values(col)]
        cols = [(f"{col}_{suffix}", [getattr(a, attr) for a in parsed], col) for suffix, attr in ADDRESS_OUTPUTS]
        for i, a in enumerate(parsed):
            for note in a.notes:
                _flag(prepared, i, note, col)
        split = sum(1 for a, v in zip(parsed, prepared.values(col)) if v.strip() and a.street != v.strip())
        return cols, StepResult(step.step_id, split == 0, "split_found_nothing" if split == 0 else None, {"split": split})
    if k == "split_name":
        col = p["column"]
        parsed = [parse_name(v, form=p.get("form", "auto")) for v in prepared.values(col)]
        cols = [(f"{col}_{part}", [getattr(n, part) for n in parsed], col) for part in NAME_OUTPUTS]
        for i, n in enumerate(parsed):
            for note in n.notes:
                _flag(prepared, i, note, col)
        split = sum(1 for n in parsed if n.last or n.middle)
        return cols, StepResult(step.step_id, split == 0, "split_found_nothing" if split == 0 else None, {"split": split})
    if k == "calc_zip":
        name = p.get("name") or "Zip_calculated"
        streets = prepared.values(p["street_col"])
        cities = prepared.values(p["city_col"]) if p.get("city_col") else [""] * len(streets)
        zips = prepared.values(p["zip_col"]) if p.get("zip_col") else [None] * len(streets)
        out = [calc_zip.calculate(s, c, z, p.get("mode", "blanks"), resolver) for s, c, z in zip(streets, cities, zips)]
        counts = {"found": sum(1 for _, n in out if n == "zip_found"), "kept": sum(1 for _, n in out if n == "zip_kept"),
                  "not_worked_out": sum(1 for _, n in out if n == "zip_not_worked_out")}
        amber = resolver is None
        return ([(name, [z for z, _ in out], p["street_col"]), (f"{name}_note", [n for _, n in out], p["street_col"])],
                StepResult(step.step_id, amber, "no_lookup_available" if amber else None, counts))
    raise ValueError(k)


# Proposals

_ALREADY_SPLIT = {"first_name", "last_name", "firstname", "lastname", "f_name", "l_name", "given", "givenname", "family", "familyname",
                  "surname", "middle_initial", "mi"}
_NOT_A_PERSON = {
    "program", "service", "site", "org", "organization", "agency", "provider", "company", "business", "school", "project", "event",
    "file", "report", "group", "team", "department", "dept", "location", "facility", "vendor", "funder", "grant", "contract",
    "activity", "class", "course", "product", "type", "category", "status", "office", "borough", "city", "county", "district",
    "region", "table", "sheet", "form", "field", "column", "fund", "unit", "center", "clinic", "hospital", "shelter", "building",
    "property", "landlord", "employer",
}
_UNIT_COLUMN_NAMES = {"address2", "addr2", "apt", "apartment", "unit", "suite", "floor", "addressline2"}
_UNIT_RE = re.compile(r"(?i)(?:^|[\s,])(?:apt|apartment|ste|suite|unit|fl|floor|rm|room|bldg|building|ph|penthouse|bsmt|basement|"
                      r"lobby|mezzanine|rear|front|#)\s*[\w\-]*")
_ONLY_UNIT = re.compile(r"(?i)^\s*(?:#|(?:apt|apartment|ste|suite|unit|fl|floor|rm|room|bldg|building|ph|penthouse|bsmt|basement|"
                        r"lobby|mezzanine|rear|front)\b)")
_STATE_RE = re.compile(r"(?i)(?:^|[\s,])(?:NY|N\.Y\.|New York)\s*(?:\d{5}|$)")


def _flat(name):
    return re.sub(r"[^a-z0-9]", "", name.lower())


def _denied(header):
    deny = load("mapping")["deny"]
    words = set(tokens(header))
    return bool(words & (set(deny["person_fields"]) | set(deny["address_fields"])))


def _share(values, test):
    return sum(1 for v in values if test(v)) / len(values) if values else 0.0


def propose_steps(table, mapping):
    """Steps for the client's own jammed address and jammed name, with the old build's thresholds. A column is a candidate only
    when the mapper chose it for the client's name or address, or left it unmapped, and its header has no deny word (B-23)."""
    chosen = {a.column.name: a.field for a in mapping.assignments}
    out = []

    def eligible(col, fields):
        if _denied(col):
            return False
        return col not in chosen or chosen[col] in fields

    has_unit_col = any(_flat(c) in _UNIT_COLUMN_NAMES for c in table.headers)
    best, best_score = None, 0.0
    for ci, c in enumerate(table.headers):
        if _flat(c) in _UNIT_COLUMN_NAMES or not eligible(c, ("Address_1",)):
            continue
        vals = [r[ci] for r in table.rows if r[ci].strip()]
        if not vals:
            continue
        if not (_share(vals, lambda v: re.search(r"\d", v)) > 0.5 and _share(vals, lambda v: re.search(r"[A-Za-z]", v)) > 0.5):
            continue
        if _share(vals, lambda v: _ONLY_UNIT.match(v)) > 0.6 and _share(vals, lambda v: re.match(r"^\s*\d+[\w-]*\s+\S", v)) < 0.3:
            continue
        zip_f = _share(vals, lambda v: re.search(r"\d{5}\s*$", v))
        unit_f = _share(vals, lambda v: _UNIT_RE.search(v))
        state_f = _share(vals, lambda v: _STATE_RE.search(v))
        comma_f = _share(vals, lambda v: "," in v)
        reasons = zip_f > 0.30 or state_f > 0.30 or (comma_f > 0.50 and (state_f > 0.15 or zip_f > 0.15))
        reasons = reasons or (unit_f > 0.15 and not (has_unit_col and zip_f <= 0.30 and state_f <= 0.30))
        if not reasons:
            continue
        score = zip_f + unit_f * 0.8 + state_f * 0.6 + (0.25 if set(tokens(c)) & {"address", "addr", "street", "location"} else 0)
        if score > best_score:
            best, best_score = c, score
    if best:
        out.append(Step("proposed-address", "split_address", {"column": best}, origin="proposed"))

    for ci, c in enumerate(table.headers):
        toks = tokens(c)
        if "name" not in toks and not any(t.endswith("name") for t in toks):
            continue
        if _flat(c) in {_flat(x) for x in _ALREADY_SPLIT} or set(toks) & _NOT_A_PERSON:
            continue
        if not eligible(c, ("First_Name", "Last_Name")):
            continue
        vals = [r[ci] for r in table.rows if r[ci].strip()]
        if not vals:
            continue
        multi = _share(vals, lambda v: 2 <= len(v.split()) <= 4)
        alpha = _share(vals, lambda v: re.fullmatch(r"[A-Za-z ,.'\-]+", v))
        if multi > 0.6 and alpha > 0.6:
            form = "auto"
            out.append(Step("proposed-name", "split_name", {"column": c, "form": form}, origin="proposed"))
            break
    return out


def source_cells_changed(before_rows, table):
    """How many source cells differ from a copy taken before the steps ran. Must always be 0."""
    return sum(1 for a, b in zip(before_rows, table.rows) for x, y in zip(a, b) if x != y) + abs(len(before_rows) - len(table.rows))


def without_step(steps, step_id):
    return [replace(s, removed=True) if s.step_id == step_id else s for s in steps]


def restore_step(steps, step_id):
    return [replace(s, removed=False) if s.step_id == step_id else s for s in steps]
