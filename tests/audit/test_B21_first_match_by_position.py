"""B-21 (High): auto-map took the first matching column in file order, not the one that meant the field."""
import pytest

from tests.support.mapping import mapped


def orders(cols):
    return [cols, list(reversed(cols)), cols[1::2] + cols[::2]]


@pytest.mark.parametrize("i", range(3))
def test_B21_emergency_contact_before_client(i):
    cols = ["Emergency Contact First Name", "Emergency Contact Last Name", "First Name", "Last Name", "Client ID"]
    m = mapped(orders(cols)[i]).as_names()
    assert m["First_Name"] == "First Name" and m["Last_Name"] == "Last Name"


@pytest.mark.parametrize("i", range(3))
def test_B21_provider_loses_to_client(i):
    cols = ["Provider First Name", "Provider Last Name", "Client First Name", "Client Last Name", "Client ID"]
    m = mapped(orders(cols)[i]).as_names()
    assert m["First_Name"] == "Client First Name" and m["Last_Name"] == "Client Last Name"


@pytest.mark.parametrize("i", range(3))
def test_B21_mailing_before_home(i):
    cols = ["First Name", "Last Name", "Client ID", "Mailing Address", "Mailing City", "Mailing State", "Mailing Zip",
            "Home Address", "Home City", "Home State", "Home Zip"]
    m = mapped(orders(cols)[i])
    names = m.as_names()
    assert [names[f] for f in ("Address_1", "City", "State", "Zip")] == ["Home Address", "Home City", "Home State", "Home Zip"]
    a1 = next(a for a in m.assignments if a.field == "Address_1")
    assert "Mailing Address" in [c.name for c in a1.alternatives]


@pytest.mark.parametrize("i", range(3))
def test_B21_place_of_birth_city_before_city_of_residence(i):
    cols = ["First Name", "Last Name", "Client ID", "Address", "Place of Birth City", "City of Residence", "State", "Zip"]
    assert mapped(orders(cols)[i]).as_names()["City"] == "City of Residence"
