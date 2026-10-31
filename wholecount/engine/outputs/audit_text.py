"""The two audit logs (SPEC 9.2, fix plan 4.5). Plain text, one event per line, built only from AuditEntry objects.

`<ISO time, UTC> <EVENT_CODE> key=value ...`, strings JSON-quoted. No cap on lines (A-24). The shareable log drops file
names, fingerprints, row numbers and notes, shows a table as its letter and number, and replaces each record key with its
second keyed hash (A-02, C-22).
"""
import json

from wholecount import copy
from wholecount.brand import VERSION
from wholecount.engine.outputs.audit_entry import KeyedHash

COMMON = ("reviewer", "second_reviewer", "time_iso")
EVENT_SLOTS = {
    "FILE_ADDED": ("letter", "file_name", "fingerprint"),
    "TABLE_INCLUDED": ("table_key", "letter", "count"),
    "TABLE_EXCLUDED": ("table_key", "letter", "count"),
    "HEADER_CHOSEN": ("table_key", "letter", "row_number"),
    "SETUP_CHANGE": ("reason_code",) + COMMON,
    "FILL": ("record_key", "field_name", "rule_id", "reason_code", "decision_id") + COMMON,
    "STANDARDIZED": ("record_key", "field_name", "rule_id", "reason_code"),
    "DEFAULT_USED": ("record_key", "field_name", "rule_id"),
    "CORRECTION": ("record_key", "field_name", "old_hash", "new_hash", "count", "file_name", "decision_id") + COMMON,
    "DECISION": ("decision_id", "record_key", "reason_code", "note") + COMMON,
    "BULK_ACCEPT": ("decision_id", "typed_count", "reason_code", "count") + COMMON,
    "UNDO": ("decision_id",) + COMMON,
    "AUTO_JOIN": ("reason_code", "master_id"),
    "PAIR_VERDICT": ("decision_id", "master_id", "reason_code") + COMMON,
    "PROGRAM": ("decision_id", "program_name", "reason_code") + COMMON,
    "RUN": ("backend_name", "release", "reason_code", "count") + COMMON,
    "FINISH_REVIEW": ("count",) + COMMON,
    "CONFIDENCE_ACK": ("count", "reason_code") + COMMON,
    "REVIEWER_SET": COMMON,
    "RESUME": ("count",) + COMMON,
    "DOWNLOAD": ("file_name", "count") + COMMON,
    "CROSSWALK_ON": COMMON,
    "CROSSWALK_UPDATED": ("count",) + COMMON,
    "CROSSWALK_FORGET": COMMON,
    "SECRET_BACKUP": COMMON,
    "SECRET_RESTORE": COMMON,
    "CALIBRATION": ("count",) + COMMON,
    "THRESHOLD_SET": ("field_name", "count") + COMMON,
}
# M13's events: each holds the reviewer, the time and counts, never a value.
M13_EVENTS = ("CROSSWALK_ON", "CROSSWALK_UPDATED", "CROSSWALK_FORGET", "SECRET_BACKUP", "SECRET_RESTORE", "CALIBRATION",
              "THRESHOLD_SET")
EVENT_CODES = tuple(EVENT_SLOTS)
SHAREABLE_DROP = frozenset({"file_name", "fingerprint", "row_number", "note"})


class AuditRenderError(ValueError):
    pass


def _value(v):
    if isinstance(v, KeyedHash):
        return v.hex
    if isinstance(v, int):
        return str(v)
    return json.dumps(v, ensure_ascii=False)


def render_line(time_iso, e, share_keys=None, table_names=None):
    allowed = EVENT_SLOTS.get(e.code)
    if allowed is None:
        raise AuditRenderError(f"unknown event {e.code}")
    parts = [time_iso, e.code]
    for slot, v in e.fields:
        if slot == "time_iso":
            continue
        if slot not in allowed:
            raise AuditRenderError(f"{e.code} can't carry {slot}")
        if share_keys is not None:
            if slot in SHAREABLE_DROP:
                continue
            if slot == "record_key":
                v = share_keys.get(v, "")
            if slot == "table_key":
                v = table_names.get(v, "")
        parts.append(f"{slot}={_value(v)}")
    return " ".join(parts)


def _header(view):
    rows = sum(t.received for t in view.balance.tables)
    return copy.get("log.header", version=VERSION, backend=view.backend, release=view.release or "-",
                    offset=copy.get("common.yes") if view.offset_applied else copy.get("common.no"), tables=len(view.tables),
                    rows=rows)


def render_internal(view):
    lines = []
    if view.practice:
        lines.append(copy.get("log.practice_line"))
    lines += [copy.get("log.internal_first_line"), _header(view)]
    lines += [copy.get("log.legend", letter=letter, file_name=name) for letter, name, _ in view.sources]
    lines += [render_line(t, e) for t, e in view.events]
    if view.reviewer_counts:
        lines.append(copy.get("log.reviewer_table"))
        lines += [copy.get("log.reviewer_row", reviewer=c.reviewer, kind=c.kind, count=c.count) for c in view.reviewer_counts]
    return "\r\n".join(lines) + "\r\n"


def render_shareable(view):
    names = {t.table_key: f"{t.letter}.{t.number}" for t in view.tables}
    lines = []
    if view.practice:
        lines.append(copy.get("log.practice_line"))
    lines += [copy.get("log.shareable_first_line"), _header(view)]
    lines += [render_line(t, e, view.share_keys, names) for t, e in view.events]
    return "\r\n".join(lines) + "\r\n"
