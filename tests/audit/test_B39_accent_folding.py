"""B-39: accents, apostrophes and hyphens made one person look like several. Every comparison folds first (P-DUP-6)."""
import pytest

from tests.fixtures.people.builders import crow, prow
from wholecount.engine.copies import TableInfo, find_copies
from wholecount.engine.identity import resolve


def test_copies_fold_names():
    t = {"t": TableInfo(False, "S")}
    rows = [crow("g1", "t", "S", "", "Maria", "Garcia", "", "10 Main St", "11201"),
            crow("g2", "t", "S", "", "MARIA", "GARCIA", "", "10 Main St", "11201"),
            crow("g3", "t", "S", "", "María", "García", "", "10 Main St", "11201"),
            crow("o1", "t", "S", "", "Pat", "O'Brien", "", "5 Elm St", "11201"),
            crow("o2", "t", "S", "", "Pat", "OBrien", "", "5 Elm St", "11201"),
            crow("w1", "t", "S", "", "Wei", "Li", "", "7 Oak Ave", "11201"),
            crow("w2", "t", "S", "", "Li", "Wei", "", "7 Oak Ave", "11201")]
    assert sorted(g.members for g in find_copies(rows, t)) == [("g1", "g2", "g3"), ("o1", "o2")]


@pytest.mark.parametrize("a,b", [(("Maria", "Garcia"), ("María", "García")), (("Pat", "OBrien"), ("Pat", "O'Brien")),
                                 (("Ana Maria", "Lopez"), ("Ana-Maria", "Lopez")), (("Jose", "Nunez"), ("José", "Núñez"))])
def test_across_files_one_possible_proposal(a, b):
    rows = [prow("a", "A", "1", a[0], a[1], "", "10 Main St", "11201"), prow("b", "B", "2", b[0], b[1], "", "10 Main St", "11201")]
    r = resolve(rows)
    assert r.auto_joins == ()
    (p,) = r.proposals
    assert p.band == "possible" and p.score >= 86
