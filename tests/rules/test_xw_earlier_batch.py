"""earlier_batch joins (P-ID-3, M06 ID-8, M13 XW-4)."""
import sqlite3

from tests.support import crosswalk as X
from wholecount.session import commands as C


def first_batch(tmp_path, xw, decide=True):
    s = X.session(tmp_path / "b1", xw, ["batch1_a.csv", "batch1_b.csv"])
    X.turn_on(s)
    X.run(s)
    if decide:
        X.decide_truth(s)
    X.download(s, tmp_path / "o1")
    return s


def test_a_person_made_join_comes_back_and_can_be_split(tmp_path):
    xw = tmp_path / "data" / "crosswalk.db"
    first_batch(tmp_path, xw)
    s = X.session(tmp_path / "b2", xw, ["batch1_a.csv", "batch1_b.csv"], day=1)
    X.run(s)
    assert ("A4", "B4") in X.joins(s, "earlier_batch")
    s.history.execute(C.DecidePair(X.pk(s, "A4"), X.pk(s, "B4"), "different"))
    assert X.master(s, "A4") != X.master(s, "B4")
    X.download(s, tmp_path / "o2")
    con = sqlite3.connect(str(xw))
    a, b = sorted((X.pk(s, "A4"), X.pk(s, "B4")))
    assert con.execute("SELECT verdict FROM pair_verdict WHERE key_a = ? AND key_b = ?", (a, b)).fetchone() == ("different",)
    con.close()


def test_a_tool_made_join_whose_reason_is_gone_is_released(tmp_path):
    xw = tmp_path / "data" / "crosswalk.db"
    one = first_batch(tmp_path, xw)
    assert ("A1", "B1") in X.joins(one, "four_exact_facts")
    saved = X.master(one, "A1")

    def move(row):
        if row["Client_ID"] == "B1":
            row["Address"] = "200 Grand Concourse"
        return row
    s = X.session(tmp_path / "b2", xw, ["batch1_a.csv", "batch1_b.csv"], edit=move, day=1)
    X.run(s)
    assert ("A1", "B1") not in X.joins(s)
    m_a, m_b = X.master(s, "A1"), X.master(s, "B1")
    assert m_a != m_b and saved in (m_a, m_b)
    first_linked = "A1" if m_a == saved else "B1"
    other = "B1" if first_linked == "A1" else "A1"
    from wholecount.engine.identity import master_id
    assert X.master(s, other) == master_id(X.pk(s, other))
    X.download(s, tmp_path / "o2")
    con = sqlite3.connect(str(xw))
    assert con.execute("SELECT master_id FROM person_key WHERE person_key = ?", (X.pk(s, other),)).fetchone() == \
        (X.master(s, other),)
    con.close()


def test_with_the_crosswalk_off_nothing_is_an_earlier_batch_join(tmp_path):
    s = X.session(tmp_path / "b1", None, ["batch1_a.csv", "batch1_b.csv"])
    X.run(s)
    X.decide_truth(s)
    assert X.joins(s, "earlier_batch") == []
