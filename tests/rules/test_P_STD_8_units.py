"""P-STD-8: a unit in both address lines (proof sheet 11)."""
import pytest

from wholecount.engine.standardize.units import reconcile_units


@pytest.mark.parametrize("a1,a2,out1,out2,reason,note", [
    ("123 Main St Apt 2A", "Apt 2A", "123 Main St", "Apt 2A", None, "unit_deduplicated"),
    ("123 Main St Apt 2A", "#2A", "123 Main St", "#2A", None, "unit_deduplicated"),
    ("123 Main St Apt 2A", "2A", "123 Main St", "2A", None, "unit_deduplicated"),
    ("123 Main St Apt 2A", "", "123 Main St", "Apt 2A", None, "unit_moved"),
    ("123 Main St", "Apt 2A", "123 Main St", "Apt 2A", None, None),
    ("123 Main St Apt 2A", "Apt 3B", "123 Main St Apt 2A", "Apt 3B", "units_differ", None),
    ("123 Main St Apt 2A", "c/o Jane Doe", "123 Main St Apt 2A", "c/o Jane Doe", "address_extra_text", None),
])
def test_units(a1, a2, out1, out2, reason, note):
    r = reconcile_units(a1, a2)
    assert (r.address_1, r.address_2, r.reason, r.note) == (out1, out2, reason, note)
