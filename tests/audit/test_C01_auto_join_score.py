"""C-01: the old matcher joined any pair scoring 100 or more. Joins now happen only for P-ID-3's named reasons.

The audit's own numbers (7 to 10, 3 open, 2 joins) assume the old address key, which dropped the street type. With the type
kept (C-24), Luis Diaz at 123 45th St and 123 45th Ave is a proposal, so this fixture gives 7 to 11, 4 open, 1 join.
"""
import pytest

from tests.fixtures.people.builders import by_record, c01_rows, pair_of, prow
from wholecount.engine.identity import load_settings, resolve, score_pair

pytestmark = pytest.mark.claim("CL-ID-JOIN-02")
W = load_settings()["weights"]


@pytest.fixture(scope="module")
def run():
    rows = c01_rows()
    return rows, resolve(rows)


def codes(items):
    return [e.code for e in items]


def test_exactly_one_join(run):
    rows, r = run
    assert [(j.pair, j.reason) for j in r.auto_joins] == [(pair_of(rows, "A1", "B1"), "four_exact_facts")]
    k = by_record(rows)
    facts = {x.record_key: x for x in rows}
    assert score_pair(facts["A1"], facts["B1"], False, W).points == 128 and k["A1"] != k["B1"]


def test_four_likely_proposals(run):
    rows, r = run
    got = {p.pair: p for p in r.proposals}
    assert len(got) == 4 and all(p.band == "likely" for p in got.values())
    p2 = got[pair_of(rows, "A2", "B2")]
    assert (p2.score, codes(p2.evidence)) == (102, ["dob_exact", "surname_exact", "address_exact"])
    p3 = got[pair_of(rows, "A3", "B3")]
    assert p3.score == 112 and "dob_one_digit" in codes(p3.evidence) and "suffix_differs" in codes(p3.cautions)
    p4 = got[pair_of(rows, "A4", "B4")]
    assert p4.score == 112 and "dob_swapped" in codes(p4.evidence)
    p5 = got[pair_of(rows, "A5", "B5")]
    assert p5.score == 104 and "zip_only" in codes(p5.evidence) and "address_exact" not in codes(p5.evidence)
    assert not any("rare_name" in codes(p.evidence) for p in got.values())


def test_vega_pair_not_shown_and_the_range(run):
    rows, r = run
    facts = {x.record_key: x for x in rows}
    assert score_pair(facts["A6"], facts["B6"], False, W).points == 16
    assert pair_of(rows, "A6", "B6") not in {p.pair for p in r.proposals}
    assert (r.low, r.settled) == (7, 11)
    assert r.low <= 10 <= r.settled


def test_a_hundred_points_without_a_reason_is_a_proposal():
    rows = [prow("x1", "A", "1", "Bill", "Smith", "1970-01-01", "1 Oak St", "11201"),
            prow("x2", "B", "2", "William", "Smith", "1970-01-01", "9 Pine St", "11201")]
    r = resolve(rows)
    assert r.auto_joins == () and [(p.score, p.band) for p in r.proposals] == [(100, "likely")]
