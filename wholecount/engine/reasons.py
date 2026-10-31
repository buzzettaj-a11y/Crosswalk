"""Reasons: problem kinds with stable IDs (P-VAL-3). Severity `decision` puts the problem on Fix problems and needs a problems.toml
entry. Severity `note` is audit only. A decision reason has exactly one flag: holds_count, location or soft. Notes have none.
A soft reason never blocks counting; its likely action is "Accept all as they are" (P-STD-2). M04 adds its reasons here."""
from dataclasses import dataclass

FLAGS = ("holds_count", "location", "soft")


@dataclass(frozen=True)
class Reason:
    id: str
    severity: str                 # decision or note
    flag: str | None = None


_REASONS = {}


def register(reason_id, severity, flag=None):
    if severity == "decision" and flag not in FLAGS:
        raise ValueError(f"{reason_id}: a decision reason needs one flag")
    if severity == "note" and flag is not None:
        raise ValueError(f"{reason_id}: a note has no flag")
    if severity not in ("decision", "note"):
        raise ValueError(severity)
    r = Reason(reason_id, severity, flag)
    _REASONS[reason_id] = r
    return r


def get(reason_id):
    return _REASONS[reason_id]


def all_reasons():
    return dict(_REASONS)


# M03, tidy-up steps. None of these holds the count: none makes a P-VAL-2 condition fail.
register("address_extra_text", "decision", "location")
register("name_order_unclear", "decision", "soft")
register("name_extra_tokens", "decision", "soft")
for _note in ("zip_had_9_digits", "zip_found", "zip_kept", "zip_not_worked_out", "no_street", "no_lookup_available"):
    register(_note, "note")
