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


# M04, standardizing and row checks. This flag table is binding (SPEC P-VAL-3, M04). Only a reason that makes a P-VAL-2
# condition fail holds the count. M06 adds the open same-ID conflict.
for _id in ("name_missing", "no_identifier", "needed_field_failed"):
    register(_id, "decision", "holds_count")
for _id in ("address_part_missing", "zip_not_valid", "zip_unicode_digits", "city_not_recognized", "city_zip_disagree",
            "state_not_recognized", "state_zip_disagree", "address_incomplete", "address_text_disagrees", "units_differ"):
    register(_id, "decision", "location")
for _id in ("placeholder_in_value", "name_may_be_placeholder", "digits_in_name", "unreadable_character", "date_not_readable",
            "date_impossible", "date_order_unclear", "date_both_ways", "date_two_digit_year", "date_excel_number", "dob_out_of_range",
            "dob_age_over_115", "value_wrong_type", "value_too_long", "required_field_blank"):
    register(_id, "decision", "soft")
for _note in ("blank_marker", "no_fixed_address", "zip_outside_nyc", "state_outside_nyc", "zip_plus4_reduced", "zip_zero_restored",
              "name_recased", "middle_initial_reduced", "middle_initial_dropped", "city_standardized", "city_filled_from_zip",
              "state_standardized", "state_filled_from_zip", "address_place_moved", "unit_moved", "unit_deduplicated",
              "date_standardized", "value_standardized", "default_used"):
    register(_note, "note")

# Why a row is set aside rather than counted. Not a problem kind: the row leaves the count with its reason (P-VAL-1).
SET_ASIDE_REASONS = ("summary_row",)
