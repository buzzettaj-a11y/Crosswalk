"""B-27 (Medium): address text that contradicted the City or ZIP column was discarded with a note only."""
from tests.support.std import ids, std
from wholecount.engine.prepare.address import parse_address
from wholecount.engine.standardize.model import AddressText


def text_of(a1):
    p = parse_address(a1)
    return AddressText(p.city, p.state, p.zip)


def test_B27_both_audit_inputs():
    r = std(Address_1="123 Main St, Brooklyn", City="Queens", Zip="11355", address_text=text_of("123 Main St, Brooklyn"))
    assert "address_text_disagrees" in ids(r) and "Brooklyn" in r.values["City"].suggestions and r.count_status.counted
    r = std(Address_1="123 Main St, Brooklyn, NY 11201", City="Brooklyn", Zip="11234",
            address_text=text_of("123 Main St, Brooklyn, NY 11201"))
    assert "address_text_disagrees" in ids(r) and "11201" in r.values["Zip"].suggestions and r.count_status.counted


def test_B27_an_alias_agrees():
    r = std(Address_1="123 Main St, Bklyn", City="Brooklyn", address_text=text_of("123 Main St, Bklyn"))
    assert "address_text_disagrees" not in ids(r)
