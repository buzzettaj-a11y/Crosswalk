"""Audit entries (SPEC 3.4 CMD-4, H8). An entry takes fields only through typed slots, so a cell value has no way in.

M09 decides which slots each log keeps and writes the lines. A KeyedHash is made only by session.keys.value_hash.
"""
import re
from dataclasses import dataclass

_TOKEN = object()


class KeyedHash:
    """An HMAC of field|text, truncated to 16 hex. It has no public constructor."""
    __slots__ = ("hex",)

    def __init__(self, token, hex_):
        if token is not _TOKEN or not re.fullmatch(r"[0-9a-f]{16}", hex_):
            raise TypeError("a KeyedHash comes from keys.value_hash only")
        object.__setattr__(self, "hex", hex_)

    def __setattr__(self, name, value):
        raise AttributeError("a KeyedHash is read only")

    def __eq__(self, other):
        return isinstance(other, KeyedHash) and other.hex == self.hex

    def __hash__(self):
        return hash(self.hex)

    def __repr__(self):
        return f"KeyedHash({self.hex})"


def _keyed_hash(hex_):
    return KeyedHash(_TOKEN, hex_)


_CODE = re.compile(r"[a-z][a-z0-9_]*")
_PATTERNS = {
    "record_key": re.compile(r"[0-9a-f]{20}|[A-Za-z0-9_.:-]{1,64}"),
    "letter": re.compile(r"[A-Z]{1,3}"),
    "decision_id": re.compile(r"D-[0-9a-f]{10}"),
    "master_id": re.compile(r"M-[0-9A-Za-z]{10}"),
    "reason_code": _CODE,
    "rule_id": re.compile(r"[A-Z][A-Za-z0-9.-]*"),
    "release": re.compile(r"[0-9A-Za-z]{0,12}"),
    "backend_name": _CODE,
    "fingerprint": re.compile(r"[0-9a-f]{64}"),
    "time_iso": re.compile(r"\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(\.\d+)?(Z|[+-]\d{2}:\d{2})"),
}
STRING_SLOTS = ("record_key", "table_key", "letter", "field_name", "column_name", "rule_id", "decision_id", "program_name",
                "backend_name", "release", "master_id", "reason_code", "reviewer", "second_reviewer", "time_iso", "file_name",
                "note", "fingerprint")
INT_SLOTS = ("row_number", "count", "typed_count")
HASH_SLOTS = ("old_hash", "new_hash")
SLOTS = STRING_SLOTS + INT_SLOTS + HASH_SLOTS
FILE_NAME_CODES = frozenset({"FILE_ADDED", "RUN", "DOWNLOAD", "CORRECTION"})
NOTE_MAX = 120


class AuditSlotError(ValueError):
    pass


@dataclass(frozen=True)
class AuditEntry:
    code: str
    fields: tuple = ()        # ((slot, value), ...) in SLOTS order; a slot may repeat for a list

    def get(self, slot):
        return [v for k, v in self.fields if k == slot]


def entry(code, **slots):
    """Build an entry. Each keyword is a slot; a list or tuple value repeats the slot."""
    if not re.fullmatch(r"[A-Z][A-Z0-9_]*", code):
        raise AuditSlotError("code")
    slots = {k: v for k, v in slots.items() if v is not None}
    out = []
    for name in SLOTS:
        if name not in slots:
            continue
        values = slots.pop(name)
        values = list(values) if isinstance(values, (list, tuple)) else [values]
        for v in values:
            out.append((name, _check(code, name, v)))
    if slots:
        raise AuditSlotError(f"not a slot: {sorted(slots)}")
    return AuditEntry(code, tuple(out))


def _check(code, name, v):
    if name in INT_SLOTS:
        if not isinstance(v, int) or isinstance(v, bool):
            raise AuditSlotError(name)
        return v
    if name in HASH_SLOTS:
        if not isinstance(v, KeyedHash):
            raise AuditSlotError(name)
        return v
    if not isinstance(v, str):
        raise AuditSlotError(name)
    if name == "file_name" and code not in FILE_NAME_CODES:
        raise AuditSlotError("file_name is only on FILE_ADDED, RUN, DOWNLOAD and CORRECTION")
    if name == "note" and len(v) > NOTE_MAX:
        raise AuditSlotError("note")
    pat = _PATTERNS.get(name)
    if pat is not None and not pat.fullmatch(v):
        raise AuditSlotError(name)
    return v
