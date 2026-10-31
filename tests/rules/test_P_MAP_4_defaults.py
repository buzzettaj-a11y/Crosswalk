"""P-MAP-4: a per-source default fills a blank and never replaces a supplied value (H6)."""
from tests.support.mapping import profiles
from wholecount.engine.defaults import SourceDefault, default_for, fill_default
from wholecount.engine.mapping import auto_map, process_blocks
from wholecount.engine.schema import default_schema


def test_supplied_value_kept_and_blank_filled():
    assert fill_default("Bronx", "Queens") == fill_default("Bronx", "Queens")
    assert fill_default("Bronx", "Queens").value == "Bronx" and not fill_default("Bronx", "Queens").used
    assert fill_default("  ", "Queens").value == "Queens" and fill_default("", "Queens").used


def test_placeholder_aware_blank_is_passed_in():
    assert fill_default("N/A", "NY", is_blank=lambda v: v in ("", "N/A")).used


def test_no_default_changes_nothing():
    assert fill_default("", None).value == "" and not fill_default("", None).used


def test_default_for_is_per_table_and_field():
    ds = [SourceDefault("t1", "State", "NY"), SourceDefault("t2", "State", "NJ")]
    assert default_for(ds, "t1", "State") == "NY" and default_for(ds, "t2", "State") == "NJ" and default_for(ds, "t1", "City") is None


def test_a_default_supplies_a_required_field():
    s = default_schema()
    p = profiles(["Last Name", "Client ID"])
    m = auto_map(s, p, "t")
    assert process_blocks(s, {"t": m}, [SourceDefault("t", "First_Name", "Unknown")], {"t": p}) == []
