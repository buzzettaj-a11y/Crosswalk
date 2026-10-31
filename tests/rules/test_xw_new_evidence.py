"""New evidence against a saved decision (M13 XW-5): a differing date of birth lapses a saved same; nothing lapses a saved
different."""
import pytest

from tests.support import crosswalk as X


@pytest.fixture
def xw(tmp_path):
    xw = tmp_path / "data" / "crosswalk.db"
    s = X.session(tmp_path / "b1", xw, ["batch1_a.csv", "batch1_b.csv"])
    X.turn_on(s)
    X.run(s)
    X.decide_truth(s)
    X.download(s, tmp_path / "o1")
    return xw


def edit(changes):
    def f(row):
        row.update(changes.get(row["Client_ID"], {}))
        return row
    return f


def test_a_saved_same_whose_dob_now_differs_lapses(tmp_path, xw):
    s = X.session(tmp_path / "b2", xw, ["batch1_a.csv", "batch1_b.csv"], edit=edit({"B4": {"DOB": "1991-11-30"}}), day=1)
    X.run(s)
    lapsed = [n for n in s.results.no_longer_apply if n.reason == "dob_now_differs"]
    assert len(lapsed) == 1 and set(lapsed[0].decision.person_keys) == {X.pk(s, "A4"), X.pk(s, "B4")}
    assert X.master(s, "A4") != X.master(s, "B4")
    assert ("A4", "B4") not in X.joins(s)
    assert ("A4", "B4") in X.open_pairs(s)


def test_a_saved_different_whose_four_facts_now_agree_stays_split(tmp_path, xw):
    s = X.session(tmp_path / "b2", xw, ["batch1_a.csv", "batch1_b.csv"], edit=edit({"B5": {"Address": "123 45th St"}}), day=1)
    X.run(s)
    assert X.master(s, "A5") != X.master(s, "B5")
    assert ("A5", "B5") not in X.joins(s) and ("A5", "B5") not in X.open_pairs(s)
    assert not [n for n in s.results.no_longer_apply if n.reason == "dob_now_differs"]
