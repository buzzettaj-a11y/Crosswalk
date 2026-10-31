"""P-VAL-3: the flag table is binding. Only the count conditions hold the count."""
from wholecount.engine import reasons


def test_holds_count_is_exactly_the_count_conditions():
    held = {r.id for r in reasons.all_reasons().values() if r.flag == "holds_count"}
    # M06 adds the open same-ID conflict kind; read it from the registry once it exists.
    extra = {r for r in held if r not in ("name_missing", "no_identifier", "needed_field_failed")}
    assert held - extra == {"name_missing", "no_identifier", "needed_field_failed"}
    assert all("conflict" in r or "same_id" in r for r in extra)
    assert not any("copy" in r for r in held)


def test_location_kinds():
    for rid in ("state_zip_disagree", "address_incomplete", "address_extra_text", "city_zip_disagree", "units_differ"):
        assert reasons.get(rid).flag == "location", rid


def test_date_reasons_are_soft():
    for rid in ("date_not_readable", "date_impossible", "date_order_unclear", "date_both_ways", "date_two_digit_year", "date_excel_number",
                "dob_out_of_range", "dob_age_over_115"):
        assert reasons.get(rid).flag == "soft", rid
