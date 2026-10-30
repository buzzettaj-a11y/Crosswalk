"""
Review context: everything a person needs to decide about one flagged row.

Some problems are about a single value, such as a ZIP that is not five digits.
Others are about a relationship between records: two rows sharing one identifier,
or two rows that may be the same person. A relational problem cannot be judged
from one record alone, so this module gathers the other records involved and
shows them side by side with the differences marked.

Every problem also gets three things in plain language: what it means, what to
check before deciding, and where possible a suggested fix the reviewer can apply
in one click. Nothing here changes data; it only assembles what is already known
so the decision can be made with the facts in view.
"""
from __future__ import annotations

import re

# Fields shown when records are compared with one another.
COMPARE_FIELDS = ["Client_ID", "First_Name", "Middle_Initial", "Last_Name",
                  "Address_1", "Address_2", "City", "State", "Zip"]


def _val(rec, field):
    """A record's value for a field, as a string."""
    if field in rec:
        return str(rec.get(field, "") or "")
    return str((rec.get("__custom__") or {}).get(field, "") or "")


def _rid(rec):
    """The stable identifier of a record: its table key and row number."""
    return f"{rec['__source_file__']}||{rec['__source_row__']}"


def classify_problem(text: str) -> str:
    """Name the kind of a single problem so the right guidance can be attached."""
    low = (text or "").lower()
    if "same client id" in low:
        return "idconflict"
    if "confirmed duplicate" in low:
        return "dupc"
    if "city/zip conflict" in low:
        return "cityzip"
    if "invalid zip" in low or ("zip" in low and "missing" in low):
        return "zip"
    if "could not be determined" in low or "unrecognized city" in low:
        return "city"
    if "missing address" in low:
        return "noaddr"
    if "missing" in low:
        return "missingfield"
    if "could not be matched" in low or "geosupport" in low or "geocod" in low:
        return "geo"
    if "exceeds max length" in low:
        return "toolong"
    if "must be" in low or "not a date" in low:
        return "badtype"
    if "name" in low and "digit" in low:
        return "nameDigits"
    return "other"


GUIDANCE = {
    "idconflict": {
        "means": "More than one record carries this identifier, but the records "
                 "do not match. Either the identifier was reused for a different "
                 "person, or one of the records was edited and the other was not.",
        "check": [
            "Compare the records below. If the names and addresses describe one "
            "person, the difference is probably an out of date record.",
            "If they describe different people, the identifier has been reused "
            "and the source system needs correcting, not this file.",
            "Keep the record that matches the most recent information you trust, "
            "and reject or remove the others.",
        ],
    },
    "dupc": {
        "means": "Another record has the same identifier and identical data. "
                 "This is the only case the tool collapses on its own.",
        "check": ["Confirm the records below really are identical.",
                  "Keeping one loses nothing, because the others are copies."],
    },
    "dupp": {
        "means": "These records share a name, address, ZIP and program but carry "
                 "different identifiers. They may be one person entered twice, or "
                 "two people who genuinely share a household.",
        "check": [
            "Compare the records below, including any middle initial.",
            "Two people at one address with the same surname are common. A "
            "shared first name as well is less likely.",
            "The tool never merges these. Approving keeps them both.",
        ],
    },
    "cityzip": {
        "means": "The city on the record and the borough its ZIP belongs to do "
                 "not agree. One of the two is wrong, and which one decides the "
                 "political districts this person is counted in.",
        "check": [
            "The ZIP is usually the reliable one, because it is machine "
            "generated while the city is often typed.",
            "Check the street against the borough. A street that exists in only "
            "one borough settles it.",
        ],
    },
    "zip": {
        "means": "The ZIP is missing or is not five digits, so it cannot be "
                 "used. The city is filled from the ZIP and the address is "
                 "geocoded using it, so this one field blocks both.",
        "check": [
            "Look at the original row below. The ZIP is often present in a "
            "column that was not mapped.",
            "A four digit ZIP usually lost a leading zero when the file was "
            "opened in a spreadsheet.",
            "If the address and city are correct, the ZIP can be looked up.",
        ],
    },
    "city": {
        "means": "The city is not one of the five boroughs, is not a "
                 "neighborhood the tool knows, and the ZIP did not supply it.",
        "check": ["Check the original row below for a borough recorded elsewhere.",
                  "A neighborhood name such as Woodside is fine to enter; the "
                  "tool translates the ones it knows."],
    },
    "noaddr": {
        "means": "There is no street address, so the record cannot be placed "
                 "anywhere and cannot be geocoded.",
        "check": [
            "Look at the original row below. The address is often in a column "
            "that was not mapped, or split across two columns.",
            "If the source genuinely holds no address, this record cannot be "
            "mapped and should be set aside rather than guessed at.",
        ],
    },
    "missingfield": {
        "means": "A field marked required on the schema is empty.",
        "check": ["Check the original row below; the value may be in an "
                  "unmapped column.",
                  "If the field is not truly required for this work, it can be "
                  "unmarked on the Schema stage instead of filled in here."],
    },
    "geo": {
        "means": "The address is complete but the geocoder found no confident "
                 "match, so no coordinates or districts could be assigned.",
        "check": ["Check the spelling of the street.",
                  "A unit left in the street stops a match. It belongs in "
                  "Address 2.",
                  "A very new address may not be in the reference data yet."],
    },
    "toolong": {
        "means": "The value is longer than the schema allows for this field.",
        "check": ["Either shorten the value here, or raise the limit on the "
                  "Schema stage if the limit is wrong.",
                  "Nothing is ever truncated automatically."],
    },
    "badtype": {
        "means": "The value does not fit the type the schema declares for this "
                 "field.",
        "check": ["Correct the value, or change the field's type on the Schema "
                  "stage if the type is wrong.",
                  "Nothing is converted automatically."],
    },
    "nameDigits": {
        "means": "A name field contains digits, which usually means the columns "
                 "are mapped one across.",
        "check": ["Look at the original row below and compare it with the "
                  "mapping on the Map stage."],
    },
    "other": {
        "means": "A validation check did not pass.",
        "check": ["Compare the record with the original row below."],
    },
}


def describe_problems(rec):
    """Each problem on a row, with what it means and what to check."""
    out = []
    for text in rec["__errors__"]:
        kind = classify_problem(text)
        g = GUIDANCE.get(kind, GUIDANCE["other"])
        out.append({"text": text, "kind": kind,
                    "means": g["means"], "check": g["check"]})
    return out


def related_records(rec, all_records, borough_from_zip=None):
    """
    The other records this decision depends on.

    A same-identifier conflict is judged against the records sharing that
    identifier. A possible duplicate is judged against its group. Anything else
    has no relations, and the panel is simply not shown.
    """
    kinds = {classify_problem(e) for e in rec["__errors__"]}
    this_rid = _rid(rec)
    group, reason = [], ""

    if "idconflict" in kinds or "dupc" in kinds:
        cid = _val(rec, "Client_ID").strip()
        if cid:
            group = [r for r in all_records
                     if _val(r, "Client_ID").strip() == cid]
            reason = (f"These {len(group)} records all carry Client ID "
                      f"{cid}. Compare them and decide which to keep.")

    if not group and rec.get("Possible_Duplicate"):
        tag = rec.get("Possible_Duplicate")
        group = [r for r in all_records if r.get("Possible_Duplicate") == tag]
        reason = (f"These {len(group)} records share a name, address, ZIP and "
                  "program but have different identifiers. They are never "
                  "merged automatically.")

    if len(group) < 2:
        return None

    # which fields actually differ, so a reviewer's eye goes straight to them
    differing = []
    for f in COMPARE_FIELDS:
        seen = {_val(r, f).strip().lower() for r in group}
        if len(seen) > 1:
            differing.append(f)

    rows = []
    for r in group[:12]:            # a dozen is plenty to decide from
        rows.append({
            "rid": _rid(r),
            "is_this_one": _rid(r) == this_rid,
            "values": {f: _val(r, f) for f in COMPARE_FIELDS},
            "source": r["__source_file__"],
            "row": r["__source_row__"],
            "status": "in review" if r["__errors__"] else "clean",
        })

    return {"reason": reason, "fields": COMPARE_FIELDS, "rows": rows,
            "differing": differing, "total": len(group),
            "shown": len(rows)}


def suggestions(rec, borough_from_zip):
    """
    Fixes the tool can propose for this row, each applied in one click. A
    suggestion is only offered when the evidence for it is already on the record.
    """
    out = []
    kinds = {classify_problem(e) for e in rec["__errors__"]}
    zip5 = _val(rec, "Zip").strip()
    city = _val(rec, "City").strip()

    if "cityzip" in kinds and zip5:
        boro = borough_from_zip(zip5)
        if boro and boro.lower() != city.lower():
            out.append({
                "label": f"Set City to {boro}, which is what ZIP {zip5} says",
                "why": "The ZIP is machine generated and is usually the reliable "
                       "one of the two.",
                "edits": {"City": boro}})
            out.append({
                "label": f"Keep City as {city} and clear the ZIP",
                "why": "Choose this when you know the city is right and the ZIP "
                       "was mistyped. The ZIP can then be looked up.",
                "edits": {"Zip": ""}})

    if ("city" in kinds or "zip" in kinds) and zip5:
        boro = borough_from_zip(zip5)
        if boro and boro.lower() != city.lower():
            out.append({
                "label": f"Set City to {boro} from ZIP {zip5}",
                "why": "The ZIP maps to a single borough.",
                "edits": {"City": boro}})

    if "zip" in kinds and re.fullmatch(r"\d{4}", zip5 or ""):
        out.append({
            "label": f"Read the ZIP as 0{zip5}",
            "why": "A four digit ZIP usually lost a leading zero when the file "
                   "was opened in a spreadsheet. Confirm it against the address "
                   "before applying.",
            "edits": {"Zip": "0" + zip5}})

    return out


def unmapped_hint(raw_row, mapping):
    """
    Columns present in the original row that were not mapped to any field.

    This is what reveals an address sitting in a column nobody mapped, which is
    a common cause of a row arriving in review with nothing obviously wrong.
    """
    used = {c for c in mapping.values() if c}
    out = []
    for col, val in (raw_row or {}).items():
        if col in used:
            continue
        text = str(val or "").strip()
        if text:
            out.append({"column": str(col), "value": text})
    return out[:20]
