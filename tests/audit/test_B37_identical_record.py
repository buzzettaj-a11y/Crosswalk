"""B-37: the old copy key left out DOB, middle initial and custom fields, so different people read as identical rows."""
from tests.fixtures.people.builders import crow
from wholecount.engine.copies import TableInfo, find_copies

T = {"t": TableInfo(True, "S")}


def base(key, **kw):
    v = dict(client_id="7", first="Ana", last="Perez", dob="1990-03-04", street="7 Elm St", zip5="11201", program="Housing")
    v.update(kw)
    return crow(key, "t", "S", v["client_id"], v["first"], v["last"], v["dob"], v["street"], v["zip5"], v["program"],
                v.get("middle", ""))


def test_different_dob_is_not_identical_and_raises_same_id():
    groups = find_copies([base("r1"), base("r2", dob="1955-09-09")], T)
    assert [g.kind for g in groups] == ["same_id_different"]


def test_different_middle_initial_is_not_identical():
    groups = find_copies([base("r1", client_id="", middle="A"), base("r2", client_id="", middle="B")], T)
    assert all(g.kind != "identical" for g in groups)


def test_fully_equal_rows_are_identical():
    (g,) = find_copies([base("r1"), base("r2")], T)
    assert (g.kind, g.rule_id, g.members) == ("identical", "P-DUP-1", ("r1", "r2"))
