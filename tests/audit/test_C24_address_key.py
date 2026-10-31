"""C-24: the old address key dropped the street type, so 123 45th St and 123 45th Ave were one address."""
import pytest

from tests.fixtures.people.builders import addr, prow
from wholecount.engine.identity import resolve

pytestmark = pytest.mark.claim("CL-ID-EV-11")


def test_street_type_stays_in_the_key():
    assert addr("123 45th St", "11377") != addr("123 45th Ave", "11377")
    assert addr("45 Park Ave", "10016") != addr("45 Park Pl", "10016")
    assert addr("12 W 45th St", "10036") == addr("12 West 45th Street", "10036")


def test_st_and_ave_give_no_address_exact():
    rows = [prow("a", "A", "1", "Luis", "Diaz", "1980-02-02", "123 45th St", "11377"),
            prow("b", "B", "2", "Luis", "Diaz", "1980-02-02", "123 45th Ave", "11377")]
    (p,) = resolve(rows).proposals
    assert "address_exact" not in [e.code for e in p.evidence]


def test_spelled_out_direction_and_type_join_by_four_exact_facts():
    rows = [prow("a", "A", "1", "Luis", "Diaz", "1980-02-02", "12 W 45th St", "10036"),
            prow("b", "B", "2", "Luis", "Diaz", "1980-02-02", "12 West 45th Street", "10036")]
    r = resolve(rows)
    assert [j.reason for j in r.auto_joins] == ["four_exact_facts"] and r.proposals == ()
