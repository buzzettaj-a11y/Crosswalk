"""The fix plan's crosswalk test (5.4, M13 XW-4, XW-6, XW-7): two batches keep every master ID and never ask a decided pair again."""
import pytest

from tests.support import crosswalk as X


@pytest.fixture
def batch1(tmp_path):
    xw = tmp_path / "data" / "crosswalk.db"
    s = X.session(tmp_path / "b1", xw, ["batch1_a.csv", "batch1_b.csv"])
    X.turn_on(s)
    X.run(s)
    assert sorted(X.open_pairs(s)) == sorted(tuple(sorted((a, b))) for a, b, _ in X.TRUTH)
    X.decide_truth(s)
    assert s.results.counts.goal1.high == s.results.counts.goal1.low == 10
    masters = {cid: X.master(s, cid) for cid in ("A1", "A2", "A3", "A4", "A5", "A6", "B1", "B2", "B3", "B4", "B5", "B6")}
    X.download(s, tmp_path / "out1")
    return xw, masters


def test_two_batches(tmp_path, batch1):
    xw, masters = batch1
    s = X.session(tmp_path / "b2", xw, ["batch1_a.csv", "batch1_b.csv", "batch2_c.csv"], shuffle_seed=1, day=1)
    X.run(s)
    for cid, m in masters.items():
        assert X.master(s, cid) == m, cid
    # Exactly one open pair: the near-copy. No earlier decided pair is asked again.
    assert X.open_pairs(s) == [("A6", "C1")]
    assert ("A4", "B4") in X.joins(s, "earlier_batch")
    c = s.results.counts
    assert c.goal1.high == 15 and c.goal1.low == 14
    assert c.matched_from_earlier == 10
    digest = s.results.digest()
    again = X.session(tmp_path / "b2b", xw, ["batch1_a.csv", "batch1_b.csv", "batch2_c.csv"], shuffle_seed=2, day=2)
    X.run(again)
    assert {cid: X.master(again, cid) for cid in masters} == masters
    assert again.results.counts == c and X.open_pairs(again) == [("A6", "C1")]
    assert digest  # the digest covers record keys, which a shuffle keeps


def test_a_third_batch_keeps_the_near_copy(tmp_path, batch1):
    xw, masters = batch1
    s = X.session(tmp_path / "b2", xw, ["batch1_a.csv", "batch1_b.csv", "batch2_c.csv"], shuffle_seed=1, day=1)
    X.run(s)
    X.decide(s, "A6", "C1", "same")
    c1 = X.master(s, "C1")
    assert c1 == masters["A6"]
    X.download(s, tmp_path / "out2")
    third = X.session(tmp_path / "b3", xw, ["batch1_a.csv", "batch1_b.csv", "batch2_c.csv"], shuffle_seed=3, day=3)
    X.run(third)
    assert X.master(third, "C1") == masters["A6"] and X.open_pairs(third) == []
    assert ("A6", "C1") in X.joins(third, "earlier_batch")
