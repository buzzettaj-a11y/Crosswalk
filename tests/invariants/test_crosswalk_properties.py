"""The saved crosswalk under shuffles and added subsets (M13 XW-7): a saved master ID never changes, and committing the same
batch twice changes nothing."""
import pathlib
import shutil
import sqlite3
import tempfile

from hypothesis import HealthCheck, given, settings
from hypothesis import strategies as st

from tests.support import crosswalk as X

EXTRA = ["C2", "C3", "C4", "C5"]


def _rows(xw):
    con = sqlite3.connect(str(xw))
    out = {t: sorted(con.execute(f"SELECT * FROM {t}").fetchall())
           for t in ("person", "person_key", "pair_verdict", "program_group", "merged_into")}
    con.close()
    return out


@settings(max_examples=10, deadline=None, suppress_health_check=[HealthCheck.too_slow])
@given(seed=st.integers(0, 10_000), keep=st.sets(st.sampled_from(EXTRA)))
def test_saved_masters_never_change(seed, keep):
    tmp = pathlib.Path(tempfile.mkdtemp())
    try:
        xw = tmp / "data" / "crosswalk.db"
        one = X.session(tmp / "b1", xw, ["batch1_a.csv", "batch1_b.csv"])
        X.turn_on(one)
        X.run(one)
        X.decide_truth(one)
        saved = {cid: X.master(one, cid) for cid in ("A1", "A2", "A3", "A4", "A5", "A6", "B1", "B2", "B3", "B4", "B5", "B6")}
        X.download(one, tmp / "o1")
        names = ["batch1_a.csv", "batch1_b.csv"] + (["batch2_c.csv"] if keep else [])
        two = X.session(tmp / "b2", xw, names, shuffle_seed=seed, day=1)
        if keep:  # an added subset of the new people
            src = X.FIX / "batch2_c.csv"
            lines = src.read_text(encoding="utf-8").splitlines()
            kept = [lines[0]] + [l for l in lines[1:] if l.split(",")[0] in keep]
            (tmp / "b2" / "in" / "batch2_c.csv").write_text("\n".join(kept) + "\n", encoding="utf-8")
        X.run(two)
        assert {cid: X.master(two, cid) for cid in saved} == saved
        X.download(two, tmp / "o2")
        after = _rows(xw)
        X.download(two, tmp / "o3")
        assert _rows(xw) == after
    finally:
        shutil.rmtree(tmp, ignore_errors=True)
