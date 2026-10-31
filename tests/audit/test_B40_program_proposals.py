"""B-40: the old proposer grouped Level 1 with Level 2 and Youth Services with Youth Employment, and chained near names into one
group. Every pair in b40_pairs.csv now behaves as listed, and chains give no three-name group (P-PROG-2)."""
import csv

import pytest

from tests.conftest import ROOT
from wholecount.engine.programs import REASONS, ProgramName, propose_groups

PAIRS = list(csv.DictReader((ROOT / "tests" / "fixtures" / "programs" / "b40_pairs.csv").open(encoding="utf-8")))
REASON = {("Workforce Dev.", "Workforce Development"): "same_name", ("WFD", "Workforce Development"): "initials",
          ("SYEP", "Summer Youth Employment Program"): "initials",
          ("Summer Youth Employment", "Summer Youth Employment Program"): "same_name",
          ("Workforce", "Workforce Development"): "more_words", ("youth", "Youth"): "same_name"}


def run(names):
    return propose_groups([ProgramName(n, 1) for n in names])


@pytest.mark.parametrize("pair", PAIRS, ids=[f"{p['a']}|{p['b']}" for p in PAIRS])
def test_pair(pair):
    got = run([pair["a"], pair["b"]])
    if pair["expect"] == "proposed":
        (p,) = got
        assert set(p.members) == {pair["a"], pair["b"]}
        assert all(r in REASONS for _, _, r in p.reasons)
        want = REASON.get((pair["a"], pair["b"]))
        if want:
            assert {r for _, _, r in p.reasons} == {want}
    else:
        assert got == []


def test_counts():
    assert sum(p["expect"] == "proposed" for p in PAIRS) == 7 and sum(p["expect"] == "apart" for p in PAIRS) == 27


@pytest.mark.parametrize("chain", [("Youth Services", "Youth Employment", "Youth Housing"),
                                   ("Senior Services", "Senior Housing", "Senior Employment"),
                                   ("Adult Education", "Adult", "Adult Literacy")])
def test_chains_give_nothing(chain):
    assert run(chain) == []
