"""Copies inside one file and one Client ID for different people (SPEC 6.7, P-DUP-1 to P-DUP-6, DUP-7)."""
import pytest

from tests.fixtures.people.builders import crow
from wholecount.engine.copies import (ApprovedAsEntered, DifferentPeople, KeepOne, NotCopies, TableInfo, Unresolvable,
                                      apply_copy_decision, find_copies, group_id, key_modes, split_group)

T = {"t": TableInfo(True, "S")}
NODOB = {"t": TableInfo(False, "S")}


def r(key, cid="", first="Ana", last="Perez", dob="1990-05-06", street="7 Elm St", zip5="11201", program="Housing", **kw):
    return crow(key, "t", "S", cid, first, last, dob, street, zip5, program, **kw)


@pytest.mark.claim("CL-DUP-01")
def test_P_DUP_1_identical_uses_every_field():
    (g,) = find_copies([r("a"), r("b")], T)
    assert (g.kind, g.rule_id) == ("identical", "P-DUP-1")
    assert find_copies([r("a", Custom="1"), r("b", Custom="2")], T)[0].kind == "possible"


@pytest.mark.claim("CL-DUP-02")
def test_P_DUP_2_name_and_dob_or_name_and_address():
    assert [g.kind for g in find_copies([r("a"), r("b", street="9 Oak Ave")], T)] == ["possible"]
    assert find_copies([r("a", dob=""), r("b", dob="", street="9 Oak Ave")], T) == []
    assert [g.kind for g in find_copies([r("a", dob=""), r("b", dob="", Note="x")], NODOB)] == ["possible"]
    assert find_copies([r("a", dob=""), r("b", dob="", street="9 Oak Ave")], NODOB) == []
    assert [g.kind for g in find_copies([r("a", first="Bob"), r("b", first="Robert", Note="x")], T)] == ["possible"]
    assert find_copies([r("a", program="Housing"), r("b", program="Youth")], T) == []


def test_P_DUP_2_a_row_is_in_one_group_and_programs_never_mix():
    rows = [r("a", program=""), r("b", program="Housing", Note="1"), r("c", program="Youth", Note="2")]
    groups = find_copies(rows, T)
    members = [m for g in groups for m in g.members]
    assert len(members) == len(set(members)) and len(groups) == 1


@pytest.mark.claim("CL-DUP-03")
def test_P_DUP_3_same_id_different_people():
    (g,) = find_copies([r("a", cid="7"), r("b", cid="7", first="Beth", dob="1994-09-09")], T)
    assert (g.kind, g.rule_id, g.same_client_id) == ("same_id_different", "P-DUP-3", True)
    assert find_copies([r("a", cid="7", program="Housing"), r("b", cid="7", program="Youth")], T) == []
    assert find_copies([r("a", cid="7", dob=""), r("b", cid="7", program="Youth")], T) == []


def test_P_DUP_4_allowed_decisions():
    ident = find_copies([r("a"), r("b")], T)[0]
    poss = find_copies([r("a"), r("b", street="9 Oak Ave")], T)[0]
    same = find_copies([r("a", cid="7"), r("b", cid="7", first="Beth")], T)[0]
    for g, bad in ((ident, NotCopies()), (poss, DifferentPeople()), (same, KeepOne("a")), (same, NotCopies())):
        with pytest.raises(Unresolvable) as e:
            apply_copy_decision(g, bad)
        assert e.value.code == "decision_not_allowed"
    with pytest.raises(Unresolvable) as e:
        apply_copy_decision(ident, KeepOne("zzz"))
    assert e.value.code == "kept_not_member"
    keep = apply_copy_decision(ident, KeepOne("b"))
    assert keep.counted == ("b",) and keep.set_aside == (("a", "b"),)
    nc = apply_copy_decision(poss, NotCopies())
    assert nc.counted == ("a", "b") and nc.verdict_pairs == (("a", "b", "different"),)
    assert apply_copy_decision(same, DifferentPeople()).verdict_pairs == (("a", "b", "different"),)
    assert apply_copy_decision(same, ApprovedAsEntered()).verdict_pairs == ()
    assert apply_copy_decision(same, ApprovedAsEntered()).counted == ("a", "b")


def test_P_DUP_5_group_id():
    import hashlib
    (g,) = find_copies([r("b"), r("a")], T)
    assert g.group_id == hashlib.sha256("identical\x1fa\x1fb".encode()).hexdigest()[:12] == group_id("identical", ("b", "a"))


def test_P_DUP_6_names_fold_first():
    assert [g.kind for g in find_copies([r("a", first="José", last="Núñez"), r("b", first="Jose", last="Nunez")], T)] == ["possible"]
    assert [g.kind for g in find_copies([r("a", last="O'Brien"), r("b", last="OBrien")], T)] == ["possible"]


def test_DUP_7_key_modes():
    rows = [r("a", cid="7"), r("b", cid="7", first="Beth", dob="1994-09-09")]
    (g,) = find_copies(rows, T)
    assert key_modes([g], {}, rows=rows) == {}
    assert key_modes([g], {g.group_id: ApprovedAsEntered()}, rows=rows) == {"a": "details", "b": "details"}
    twins = [r("a", cid="7"), r("b", cid="7", Note="x"), r("c", cid="7", first="Beth")]
    (g2,) = [g for g in find_copies(twins, T) if g.kind == "same_id_different"]
    assert key_modes([g2], {g2.group_id: DifferentPeople()}, split_rows=("a", "b"), rows=twins) == {
        "a": "row", "b": "row", "c": "details"}
    shared = [r("a"), crow("x", "t2", "S", "", "Ana", "Perez", "1990-05-06", "9 Oak Ave", "10451", "Housing")]
    assert key_modes([], {}, rows=shared) == {"a": "row", "x": "row"}
    assert key_modes([], {}, rows=[r("a")]) == {}
    assert split_group(("b", "a")).members == ("a", "b")
