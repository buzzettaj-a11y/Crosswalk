"""Standardizing one row (P-STD, P-VAL). A row's result depends only on its own inputs, never on other rows (H3).

The order is the milestone's: summary check, placeholders, unreadable characters, names, ZIP, city and state, the street line's
own text and a place left in it, units, dates, typed fields, then the count checks. A row counts on person data alone (P-VAL-2):
nothing here lets an address problem change the count status.
"""
from dataclasses import dataclass, field

from wholecount.engine.prepare.casing import title_name
from wholecount.engine.prepare.names import middle_initial
from wholecount.engine.progress import ProgressMessage, Step, Unit
from wholecount.engine.standardize import placeholders as ph
from wholecount.engine.standardize.dates import parse_date
from wholecount.engine.standardize.model import FillRef, ReasonRef, StdRow, StdValue, sort_refs
from wholecount.engine.standardize.place import move_place, standardize_city_state, text_disagreements
from wholecount.engine.standardize.summary import is_summary_row
from wholecount.engine.standardize.typed import standardize_typed
from wholecount.engine.standardize.units import reconcile_units
from wholecount.engine.standardize.zipcode import standardize_zip

REPLACEMENT = "�"
PROGRESS_EVERY = 200


@dataclass(frozen=True)
class TableOptions:
    date_contexts: dict = field(default_factory=dict)     # field key -> DateContext


class _Work:
    def __init__(self, row, schema):
        self.row = row
        self.schema = schema
        self.entered = dict(row.values)
        self.value = dict(row.values)
        self.suggestions = {}
        self.reasons = list(row.step_reasons)
        self.notes = list(row.step_notes)
        self.fills = []
        self.no_fixed_address = False
        self.outside_nyc = False
        self.place = ""

    def reason(self, rid, fld):
        self.reasons.append(ReasonRef(rid, fld))

    def note(self, rid, fld):
        self.notes.append(ReasonRef(rid, fld))


def standardize_row(row, schema, options=None, today=None):
    if today is None:
        raise ValueError("today is always passed in (H3)")
    options = options or TableOptions()
    w = _Work(row, schema)
    order = [f.key for f in schema.fields]

    if is_summary_row(row.values, row.unmapped):
        return StdRow(row.record_key, row.table_key, row.row_number,
                      {k: StdValue(v, v) for k, v in row.values.items()}, set_aside_reason="summary_row")

    for f in row.defaults_used:
        w.note("default_used", f)
    _placeholders(w)
    for k, v in w.value.items():
        if REPLACEMENT in v:
            w.reason("unreadable_character", k)
    _names(w)
    zr = standardize_zip(w.value.get("Zip", ""), row.kinds.get("Zip"))
    _zip(w, zr)
    _city_state(w, zr)
    _street(w)
    _dates_and_types(w, options, today)
    _count_checks(w, schema)

    values = {k: StdValue(w.value.get(k, ""), w.entered.get(k, ""), tuple(w.suggestions.get(k, ()))) for k in row.values}
    return StdRow(row.record_key, row.table_key, row.row_number, values, w.place, w.no_fixed_address, w.outside_nyc,
                  sort_refs(w.reasons, order), sort_refs(w.notes, order), tuple(dict.fromkeys(w.fills)), None)


def _placeholders(w):
    for k, v in list(w.value.items()):
        m = ph.marker(k, v)
        if m is None:
            continue
        if m.kind == "name_kept":
            w.reason("name_may_be_placeholder", k)
        elif m.kind == "housing":
            w.no_fixed_address = True
            w.value[k] = ""
            w.note("no_fixed_address", k)
        elif m.kind == "identifier_and_address" and k != "Address_2":
            w.value[k] = ""
            w.reason("placeholder_in_value", k)
        else:
            w.value[k] = ""
            w.note("blank_marker", k)


def _names(w):
    for k in ("First_Name", "Last_Name"):
        v = " ".join(w.value.get(k, "").split())
        if not v:
            w.value[k] = ""
            continue
        cased = title_name(v)
        if cased != w.entered.get(k, ""):
            w.note("name_recased", k)
        w.value[k] = cased
        if any(ch.isdigit() for ch in v):
            w.reason("digits_in_name", k)
    if "Middle_Initial" in w.value:
        initial, note = middle_initial(w.value["Middle_Initial"])
        w.value["Middle_Initial"] = initial
        if note:
            w.note(note, "Middle_Initial")


def _zip(w, zr):
    if "Zip" not in w.value:
        return
    w.value["Zip"] = zr.value
    if zr.reason:
        w.reason(zr.reason, "Zip")
    for n in zr.notes:
        w.note(n, "Zip")
    if zr.suggestions:
        w.suggestions["Zip"] = zr.suggestions
    if zr.outside_nyc:
        w.outside_nyc = True


def _city_state(w, zr):
    if "City" not in w.value and "State" not in w.value:
        return
    pr = standardize_city_state(w.value.get("City", ""), w.value.get("State", ""), zr)
    if w.no_fixed_address:
        # A row with no fixed address keeps its blanks: nothing is filled from the ZIP, and a blank part raises nothing.
        blank = {f for f in ("City", "State") if not w.value.get(f, "")}
        pr.notes = [(r, f) for r, f in pr.notes if f not in blank]
        pr.fills = [(f, k) for f, k in pr.fills if f not in blank]
        pr.reasons = [(r, f) for r, f in pr.reasons if f not in blank]
        pr.city = "" if "City" in blank else pr.city
        pr.state = "" if "State" in blank else pr.state
    if "City" in w.value:
        w.value["City"] = pr.city
    if "State" in w.value:
        w.value["State"] = pr.state
    for rid, f in pr.reasons:
        w.reason(rid, f)
    for rid, f in pr.notes:
        w.note(rid, f)
    for f, kind in pr.fills:
        w.fills.append(FillRef(f, kind))
    w.suggestions.update(pr.suggestions)
    if pr.outside_nyc:
        w.outside_nyc = True


def _street(w):
    if "Address_1" not in w.value:
        return
    a1 = w.value["Address_1"]
    for f, text_value in text_disagreements(w.row.address_text, w.value.get("City", ""), w.value.get("State", ""),
                                            w.value.get("Zip", "")):
        w.reason("address_text_disagrees", f)
        w.suggestions[f] = tuple(w.suggestions.get(f, ())) + (text_value,)
    street, place = move_place(a1) if a1 else (a1, "")
    if place:
        w.place = place
        w.value["Address_1"] = street
        w.note("address_place_moved", "Address_1")
    ur = reconcile_units(w.value["Address_1"], w.value.get("Address_2", ""))
    w.value["Address_1"] = ur.address_1
    if "Address_2" in w.value or ur.address_2:
        w.value["Address_2"] = ur.address_2
    if ur.note:
        w.note(ur.note, "Address_2")
    if ur.reason:
        w.reason(ur.reason, "Address_2")


def _dates_and_types(w, options, today):
    for f in w.schema.enabled_fields():
        if f.key not in w.value:
            continue
        ctx = options.date_contexts.get(f.key)
        kind = w.row.kinds.get(f.key)
        if f.key == "Date_of_Birth":
            p = parse_date(w.value[f.key], kind, ctx, today, dob=True)
            if p.reason:
                w.reason(p.reason, f.key)
            if p.readings:
                w.suggestions[f.key] = p.readings
            if p.iso and p.reason != "dob_out_of_range":
                if p.iso != w.entered.get(f.key, ""):
                    w.note("date_standardized", f.key)
                w.value[f.key] = p.iso
            elif p.iso and p.reason == "dob_out_of_range":
                w.value[f.key] = w.entered.get(f.key, "")
        elif not f.builtin:
            value, reason = standardize_typed(f, w.value[f.key], kind, ctx, today)
            if reason:
                w.reason(reason, f.key)
            elif value != w.entered.get(f.key, ""):
                w.note("value_standardized", f.key)
            w.value[f.key] = value if reason is None else w.entered.get(f.key, "")


def _valid_dob(w):
    v = w.value.get("Date_of_Birth", "")
    if not v:
        return False
    bad = {"date_not_readable", "date_impossible", "date_order_unclear", "date_both_ways", "date_two_digit_year", "date_excel_number",
           "dob_out_of_range", "placeholder_in_value", "unreadable_character"}
    return not any(r.field == "Date_of_Birth" and r.reason_id in bad for r in w.reasons)


def _count_checks(w, schema):
    for k in ("First_Name", "Last_Name"):
        if k in w.value and not w.value[k]:
            w.reason("name_missing", k)
    dob_on = schema.is_enabled("Date_of_Birth")
    if not w.value.get("Client_ID", "") and not (dob_on and _valid_dob(w)):
        w.reason("no_identifier", "Client_ID")
    for f in schema.enabled_fields():
        if f.builtin or not f.needed_to_count or f.key not in w.value:
            continue
        if not w.value[f.key] or any(r.field == f.key and r.reason_id in ("value_wrong_type", "value_too_long") for r in w.reasons):
            w.reason("needed_field_failed", f.key)
    if not w.no_fixed_address:
        for k in ("Address_1", "Zip"):
            if not w.value.get(k, ""):
                w.reason("address_part_missing", k)
    else:
        w.reasons = [r for r in w.reasons if r.reason_id not in ("address_part_missing", "address_incomplete")
                     and not (r.reason_id == "state_not_recognized" and not w.entered.get("State", "").strip())]


def standardize_table(inputs, schema, options, today, sink=None):
    """Every row of one table. Progress under Checking every row, at least every 200 rows, counts only."""
    out = []
    if sink is not None:
        sink.begin(Step.CHECKING_EVERY_ROW, len(inputs), Unit.ROWS)
    for i, row in enumerate(inputs, start=1):
        out.append(standardize_row(row, schema, options, today))
        if sink is not None and (i % PROGRESS_EVERY == 0 or i == len(inputs)):
            sink.advance(i, ProgressMessage("progress.rows_checked", {"done": i, "total": len(inputs)}))
    if sink is not None:
        counted = sum(1 for r in out if r.count_status.counted)
        sink.end(ProgressMessage("progress.found.checking_rows", {"counted": counted, "rows": len(out)}))
    return out
