"""What standardizing a row produces (P-VAL-1). Every value keeps its text as entered beside its standard form (H6, A-11).
Audit events carry IDs only (H8)."""
import enum
from dataclasses import dataclass, field

from wholecount.engine import reasons as registry
from wholecount.engine.schema import BUILTIN_KEYS


@dataclass(frozen=True)
class AddressText:
    """City, state and ZIP read from the street line itself, as evidence for B-27. Nothing is filled from it."""

    city: str = ""
    state: str = ""
    zip: str = ""


@dataclass(frozen=True)
class UnmappedHint:
    """Two facts about the row's unmapped cells, for P-VAL-4. Holds no text."""

    summary_word: bool = False
    numbers_only: bool = False


@dataclass(frozen=True)
class ReasonRef:
    reason_id: str
    field: str | None = None


@dataclass(frozen=True)
class RowInput:
    record_key: str
    table_key: str
    row_number: int
    values: dict                          # field key -> cleaned text
    kinds: dict = field(default_factory=dict)     # field key -> "number" or "date", from .xlsx cell formats
    address_text: AddressText = AddressText()
    unmapped: UnmappedHint = UnmappedHint()
    defaults_used: tuple = ()
    step_reasons: tuple = ()              # ReasonRefs a tidy-up step raised on this row (M03)
    step_notes: tuple = ()


@dataclass(frozen=True)
class StdValue:
    value: str
    entered: str
    suggestions: tuple = ()               # in memory only, never written to the audit


@dataclass(frozen=True)
class FillRef:
    field: str
    kind: str                             # zip or default


class CountStatus(enum.Enum):
    COUNTED_PASSED = "counted_passed"
    COUNTED_APPROVED = "counted_approved"
    COUNTED_CORRECTED = "counted_corrected"
    NOT_COUNTED_YET = "not_counted_yet"
    SET_ASIDE = "set_aside"

    @property
    def counted(self):
        return self in (CountStatus.COUNTED_PASSED, CountStatus.COUNTED_APPROVED, CountStatus.COUNTED_CORRECTED)


@dataclass(frozen=True)
class LocationStatus:
    kind: str                             # not_mapped or to_place
    reason: str | None = None             # no_fixed_address, outside_nyc or address_problem
    problems: tuple = ()
    filled: bool = False


def _order(field_order):
    def key(ref):
        pos = field_order.index(ref.field) if ref.field in field_order else len(field_order)
        return (pos, ref.reason_id, ref.field or "")
    return key


def sort_refs(refs, field_order=BUILTIN_KEYS):
    """Unique, sorted by schema position, then reason ID."""
    return tuple(sorted(set(refs), key=_order(list(field_order))))


@dataclass(frozen=True)
class StdRow:
    record_key: str
    table_key: str
    row_number: int
    values: dict                          # field key -> StdValue
    place: str = ""
    no_fixed_address: bool = False
    outside_nyc: bool = False
    reasons: tuple = ()
    notes: tuple = ()
    fills: tuple = ()
    set_aside_reason: str | None = None

    @property
    def count_status(self):
        return count_status_for(self)

    @property
    def location(self):
        return location_for(self)

    def reason_ids(self):
        return [r.reason_id for r in self.reasons]

    def value(self, field_key):
        v = self.values.get(field_key)
        return v.value if v else ""


def count_status_for(row, approved=False, corrected=False):
    if row.set_aside_reason:
        return CountStatus.SET_ASIDE
    if any(registry.get(r.reason_id).flag == "holds_count" for r in row.reasons) and not (approved or corrected):
        return CountStatus.NOT_COUNTED_YET
    if corrected:
        return CountStatus.COUNTED_CORRECTED
    if approved:
        return CountStatus.COUNTED_APPROVED
    return CountStatus.COUNTED_PASSED


def location_for(row):
    problems = tuple(r.reason_id for r in row.reasons if registry.get(r.reason_id).flag == "location")
    filled = any(f.kind == "zip" for f in row.fills)
    if row.no_fixed_address:
        return LocationStatus("not_mapped", "no_fixed_address", problems, filled)
    if row.outside_nyc:
        return LocationStatus("not_mapped", "outside_nyc", problems, filled)
    if problems:
        return LocationStatus("not_mapped", "address_problem", problems, filled)
    return LocationStatus("to_place", None, (), filled)


@dataclass(frozen=True)
class AuditEvent:
    record_key: str
    field: str | None
    rule_id: str
    reason_id: str


RULE_FOR_NOTE = {
    "blank_marker": "P-STD-2", "no_fixed_address": "P-STD-2", "name_recased": "P-STD-1", "middle_initial_reduced": "P-STD-1",
    "middle_initial_dropped": "P-STD-1", "zip_outside_nyc": "P-STD-3", "zip_plus4_reduced": "P-STD-3", "zip_zero_restored": "P-STD-3",
    "zip_had_9_digits": "P-PREP-3", "city_standardized": "P-STD-4", "city_filled_from_zip": "P-STD-4", "address_place_moved": "P-STD-4",
    "state_standardized": "P-STD-5", "state_filled_from_zip": "P-STD-5", "state_outside_nyc": "P-STD-5", "date_standardized": "P-STD-6",
    "value_standardized": "P-STD-7", "unit_moved": "P-STD-8", "unit_deduplicated": "P-STD-8", "default_used": "P-MAP-4",
}


def audit_events(row):
    """One event per standardization, fill and default use. IDs only: record key, field name, rule ID, reason ID (H8)."""
    return [AuditEvent(row.record_key, n.field, RULE_FOR_NOTE.get(n.reason_id, "P-STD"), n.reason_id) for n in row.notes]
