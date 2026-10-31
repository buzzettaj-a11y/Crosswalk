"""crosswalk.db holds no client value (H9, M13 XW-2)."""
import csv
import re
import sqlite3

from tests.support import crosswalk as X

NAMES = ["batch1_a.csv", "batch1_b.csv", "batch2_c.csv"]


def fixture_values():
    out = set()
    for n in NAMES:
        with open(X.FIX / n, encoding="utf-8") as f:
            for row in csv.DictReader(f):
                for k, v in row.items():
                    if k != "Program" and v:
                        out.add(v)
                        out.update(w for w in v.split() if len(w) > 3)
    return out


def test_no_client_value_in_the_file(tmp_path):
    xw = tmp_path / "data" / "crosswalk.db"
    s = X.session(tmp_path / "b1", xw, NAMES)
    X.turn_on(s)
    X.run(s)
    X.decide_truth(s)
    X.download(s, tmp_path / "o1")
    raw = xw.read_bytes()
    for v in fixture_values():
        assert v.encode("utf-8") not in raw, v
    assert sorted(p.name for p in xw.parent.iterdir()) == ["crosswalk.db"]
    con = sqlite3.connect(str(xw))
    assert all(re.fullmatch(r"[0-9a-f]{64}", k) and re.fullmatch(r"M-[0-9a-f]{10}", m)
               for k, m in con.execute("SELECT person_key, master_id FROM person_key"))
    assert all(re.fullmatch(r"M-[0-9a-f]{10}", m) for (m,) in con.execute("SELECT master_id FROM person"))
    assert all(re.fullmatch(r"[0-9a-f]{64}", a) and re.fullmatch(r"[0-9a-f]{64}", b)
               for a, b in con.execute("SELECT key_a, key_b FROM pair_verdict"))
    assert con.execute("PRAGMA journal_mode").fetchone() == ("delete",)
    con.close()
    from wholecount.session.store import snapshot
    snap = repr(snapshot(s))
    # Saved progress holds decisions, never a crosswalk row: no batch ID, master ID or crosswalk table name.
    assert s.results.crosswalk.batch_id not in snap and "first_batch" not in snap and "merged_into" not in snap
    con = sqlite3.connect(str(xw))
    assert not [m for (m,) in con.execute("SELECT master_id FROM person") if m in snap]
    con.close()
