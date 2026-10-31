"""Building RowInputs from a prepared table and its mapping. Unmapped cells are read only to set two booleans (UnmappedHint)."""
from functools import partial

from wholecount.engine.defaults import default_for, fill_default
from wholecount.engine.prepare.address import parse_address
from wholecount.engine.standardize.model import AddressText, ReasonRef, RowInput, UnmappedHint
from wholecount.engine.standardize.placeholders import is_blank
from wholecount.engine.standardize.summary import NUMBERS_ONLY, SUMMARY_WORDS

# Which field a tidy-up step's reason belongs to, when the step's columns are mapped.
STEP_REASON_FIELD = {"address_extra_text": "Address_1", "name_order_unclear": "First_Name", "name_extra_tokens": "First_Name",
                     "zip_had_9_digits": "Zip"}


def _column_values(prepared, ref):
    return prepared.values(ref.name)


def build_inputs(prepared, mapping, defaults, schema):
    """One RowInput per included row of the table."""
    table = prepared.table
    cols = {a.field: a.column for a in mapping.assignments if a.field not in {q.field for q in mapping.questions}}
    values = {f: _column_values(prepared, c) for f, c in cols.items()}
    mapped_names = {c.name for c in cols.values()}
    unmapped_idx = [i for i, h in enumerate(table.headers) if h not in mapped_names]
    a1 = cols.get("Address_1")
    siblings = {}
    if a1 is not None and a1.derived and a1.derived_from:
        for part in ("city", "state", "zip"):
            name = f"{a1.derived_from}_{part}"
            if name in prepared.names() and name not in mapped_names:
                siblings[part] = prepared.values(name)
    derived_from = {}
    for f, c in cols.items():
        if c.derived and c.derived_from:
            derived_from.setdefault(c.derived_from, set()).add(f)

    out = []
    for i in range(len(table.rows)):
        if not table.is_row_included(i):
            continue
        row_values, used, kinds = {}, [], {}
        for f in schema.enabled_fields():
            v = values[f.key][i] if f.key in values else ""
            d = default_for(defaults, table.key, f.key)
            res = fill_default(v, d, partial(is_blank, f.key))
            if res.used:
                used.append(f.key)
            row_values[f.key] = res.value
            c = cols.get(f.key)
            if c is not None and not c.derived and (i, c.index) in table.meta:
                kinds[f.key] = table.meta[(i, c.index)].kind
        if a1 is not None and not a1.derived:
            pa = parse_address(row_values.get("Address_1", ""))
            text = AddressText(pa.city, pa.state, pa.zip)
        else:
            text = AddressText(*(siblings.get(p, [""] * len(table.rows))[i] for p in ("city", "state", "zip")))
        unmapped = [table.rows[i][j] for j in unmapped_idx if table.rows[i][j].strip()]
        hint = UnmappedHint(any(SUMMARY_WORDS.match(v) for v in unmapped),
                            bool(unmapped) and all(NUMBERS_ONLY.fullmatch(v) for v in unmapped))
        step_reasons, step_notes = [], []
        for rid, source in prepared.row_reasons.get(i, ()):
            fields = derived_from.get(source, set())
            fld = STEP_REASON_FIELD.get(rid) if STEP_REASON_FIELD.get(rid) in fields else (min(fields) if fields else None)
            if fld is None:
                continue
            ref = ReasonRef(rid, fld)
            (step_notes if rid == "zip_had_9_digits" else step_reasons).append(ref)
        out.append(RowInput(table.record_keys[i] if table.record_keys else str(i), table.key, table.row_numbers[i], row_values,
                            kinds, text, hint, tuple(used), tuple(step_reasons), tuple(step_notes)))
    return out
