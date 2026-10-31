"""P-ID-1 and fix plan 5.2: one person in two files at different addresses. Rare names meet on name alone; common names don't."""
import pytest

from tests.fixtures.people.builders import prow
from wholecount.engine.identity import resolve


def priya(dob_a, dob_b):
    return [prow("a", "A", "1", "Priya", "Venkataraman", dob_a, "10 Oak St", "11201"),
            prow("b", "B", "2", "Priya", "Venkataraman", dob_b, "77 Pine Ave", "10451")]


def test_with_the_same_dob_a_likely_proposal():
    (p,) = resolve(priya("1988-07-21", "1988-07-21")).proposals
    assert (p.score, p.band) == (98, "likely")


@pytest.mark.claim("CL-ID-EV-16")
def test_no_dob_and_a_rare_name_is_possible_via_k4():
    (p,) = resolve(priya("", "")).proposals
    assert (p.score, p.band, p.found_via) == (64, "possible", ("K4",))
    assert "rare_name" in [e.code for e in p.evidence]


def maria(n):
    streets = ["1 Oak St", "2 Elm St", "3 Pine Ave", "4 Ash Rd"]
    zips = ["11201", "10451", "10001", "11375"]
    return [prow(f"m{i}", "ABCD"[i], str(i), "Maria", "Rodriguez", "", streets[i], zips[i]) for i in range(n)]


def test_a_common_name_stays_apart():
    r = resolve(maria(4))
    assert r.proposals == () and r.settled == 4


def test_three_is_still_rare():
    assert len(resolve(maria(3)).proposals) == 3


def test_a_nickname_alone_is_not_shown():
    rows = [prow("a", "A", "1", "Bob", "Smith", "", "1 Oak St", "11201"), prow("b", "B", "2", "Robert", "Smith", "", "9 Pine Ave", "10451")]
    assert resolve(rows).proposals == ()
    assert resolve(rows, settings={"bands": {"possible_min": 40}}).proposals[0].score == 60
