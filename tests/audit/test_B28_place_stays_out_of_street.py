"""B-28 (Medium): neighborhoods outside a 114-name table stayed inside Address_1."""
import pytest

from tests.support.std import TODAY, std
from tests.support.tables import table
from wholecount.engine.mapping import auto_map, profile_columns
from wholecount.engine.prepare.steps import apply_steps, propose_steps
from wholecount.engine.schema import default_schema
from wholecount.engine.standardize.inputs import build_inputs
from wholecount.engine.standardize.rows import TableOptions, standardize_table

INPUTS = ["85-10 Forest Pkwy Woodhaven NY 11421", "123 Montague St Brooklyn Heights NY 11201", "123 Main St Rockaway Park NY 11694",
          "123 Main St Kew Gardens Hills NY 11367", "123 Main St Apt 4B Bklyn NY 11201"]


def test_B28_through_the_split_step():
    t = table(["Client_ID", "First Name", "Last Name", "Full_Address"], [[f"C{i}", "Ana", "Lee", a] for i, a in enumerate(INPUTS)])
    s = default_schema()
    prep = apply_steps(t, propose_steps(t, auto_map(s, profile_columns(t), t.key)))
    m = auto_map(s, profile_columns(t, prep.column_refs()), t.key)
    rows = standardize_table(build_inputs(prep, m, (), s), s, TableOptions(), TODAY)
    assert [r.value("Address_1") for r in rows] == ["85-10 Forest Pkwy", "123 Montague St", "123 Main St", "123 Main St", "123 Main St"]
    assert rows[4].value("Address_2") == "Apt 4B"
    assert [r.value("City") for r in rows] == ["Queens", "Brooklyn", "Queens", "Queens", "Brooklyn"]
    assert rows[0].values["City"].entered == "Woodhaven" and rows[4].values["City"].entered == "Bklyn"


@pytest.mark.parametrize("a1,street,place", [("85-10 Forest Pkwy Woodhaven", "85-10 Forest Pkwy", "Woodhaven"),
                                             ("123 Montague St Brooklyn Heights", "123 Montague St", "Brooklyn Heights"),
                                             ("123 Main St Rockaway Park", "123 Main St", "Rockaway Park"),
                                             ("123 Main St Kew Gardens Hills", "123 Main St", "Kew Gardens Hills")])
def test_B28_typed_in_address_1(a1, street, place):
    r = std(Address_1=a1, City="Brooklyn")
    assert (r.value("Address_1"), r.place, r.value("City")) == (street, place, "Brooklyn")


@pytest.mark.parametrize("a1", ["100 Jamaica Ave", "1010 Grand Concourse"])
def test_B28_streets_named_for_places_stay_whole(a1):
    r = std(Address_1=a1)
    assert r.value("Address_1") == a1 and r.place == ""
