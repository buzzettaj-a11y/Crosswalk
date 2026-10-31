"""Two saved people decided the same in a later batch (M13 XW-6): the earlier master wins and merged_into keeps the old ID."""
import sqlite3

from tests.support import crosswalk as X


def test_merge(tmp_path):
    xw = tmp_path / "data" / "crosswalk.db"
    a = X.session(tmp_path / "b1a", xw, ["batch1_a.csv"])
    X.turn_on(a)
    X.run(a)
    m_a5 = X.master(a, "A5")
    X.download(a, tmp_path / "o1")
    b = X.session(tmp_path / "b1b", xw, ["batch1_a.csv", "batch1_b.csv"], day=1)
    X.run(b)
    for x, y, v in X.TRUTH:
        if x != "A5":
            X.decide(b, x, y, v)
    m_b5 = X.master(b, "B5")
    assert m_a5 != m_b5 and X.master(b, "A5") == m_a5
    X.download(b, tmp_path / "o2")
    c = X.session(tmp_path / "b2", xw, ["batch1_a.csv", "batch1_b.csv"], day=2)
    X.run(c)
    X.decide(c, "A5", "B5", "same")
    assert X.master(c, "A5") == X.master(c, "B5") == m_a5
    X.download(c, tmp_path / "o3")
    con = sqlite3.connect(str(xw))
    assert con.execute("SELECT old_master, new_master FROM merged_into").fetchall() == [(m_b5, m_a5)]
    con.close()
    assert any(e.code == "CROSSWALK_UPDATED" for e in c.audit)
    d = X.session(tmp_path / "b3", xw, ["batch1_a.csv", "batch1_b.csv"], day=3)
    X.run(d)
    assert X.master(d, "A5") == X.master(d, "B5") == m_a5
    assert X.joins(d, "earlier_batch").count(("A5", "B5")) == 1
