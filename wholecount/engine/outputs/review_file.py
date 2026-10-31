"""The review file, Manual_Review_Needed (SPEC 8.6, fix plan 4.3). Shrunk and signed: identity columns, the reasons, and for
each field that failed on a row its original, standardized and a blank corrected cell. No other source column (H10).

Run_ID isn't defined in the spec, so it is an HMAC over the included tables' keys. The engine gets `mac`, never the secret.
"""
from wholecount import copy
from wholecount.engine.outputs.tables import problem_title, row_order, source_file, yes_no

LOCKED = ("Record_Key", "Run_ID", "Signature", "System", "Client_ID", "Source_Letter", "Source_File", "Source_Row", "Counted",
          "Reasons", "First_Name", "Middle_Initial", "Last_Name")
COPY_TITLE = {"identical": "copies.title.identical", "possible": "copies.title.possible"}


def run_id(mac, table_keys):
    return "R-" + mac(b"run|" + "\x1f".join(sorted(table_keys)).encode("utf-8")).hex()[:10]


def row_signature(mac, run_id_, record_key):
    return mac(f"{run_id_}|{record_key}".encode("utf-8")).hex()[:16]


def share_key(mac, record_key):
    """The shareable log's second keyed hash of a record key."""
    return mac(b"share|" + record_key.encode("utf-8")).hex()[:10]


def needs_review(row):
    """An open problem: an open reason or an open copy group, counted or not (7.3). Set-aside rows are never here (C-11)."""
    return row.set_aside_reason is None and bool(row.reasons or row.open_copy_kind)


def failing_fields(row):
    return [f for _, f in row.reason_fields if f]


def review_fields(view):
    """Fields that fail on some review row, in schema order, then any others in reason order."""
    seen = []
    for r in view.rows:
        if needs_review(r):
            for f in failing_fields(r):
                if f not in seen:
                    seen.append(f)
    order = list(view.fields)
    return [f for f in order if f in seen] + [f for f in seen if f not in order]


def review_columns(view):
    cols = list(LOCKED)
    for f in review_fields(view):
        cols += [f"Original_{f}", f"Standardized_{f}", f"Corrected_{f}"]
    return cols


def reasons_text(row):
    titles = [problem_title(r) for r in row.reasons]
    if row.open_copy_kind:
        titles.append(copy.get(COPY_TITLE[row.open_copy_kind]))
    return "; ".join(titles)


def review_row(view, r, fields=None):
    fields = review_fields(view) if fields is None else fields
    cid = r.value("Client_ID")
    show_names = not cid.strip() or "Client_ID" in failing_fields(r)
    d = {"Record_Key": r.record_key, "Run_ID": view.run_id, "Signature": r.signature, "System": r.system, "Client_ID": cid,
         "Source_Letter": r.letter, "Source_File": source_file(r), "Source_Row": str(r.row_number), "Counted": yes_no(r.counted),
         "Reasons": reasons_text(r)}
    for f in ("First_Name", "Middle_Initial", "Last_Name"):
        d[f] = r.value(f) if show_names else ""
    failing = set(failing_fields(r))
    for f in fields:
        on = f in failing
        d[f"Original_{f}"] = r.original(f) if on else ""
        d[f"Standardized_{f}"] = r.value(f) if on else ""
        d[f"Corrected_{f}"] = ""
    return d


def manual_review_needed(view, settings=None):
    fields = review_fields(view)
    return [review_row(view, r, fields) for r in sorted((r for r in view.rows if needs_review(r)), key=row_order)]
