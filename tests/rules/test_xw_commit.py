"""The commit at Download (M13 XW-6 to XW-8)."""
import dataclasses

import pytest

from tests.support import crosswalk as X
from wholecount.engine.crosswalk import apply
from wholecount.engine.identity import master_id


@pytest.mark.claim("CL-XW-FAILED-01")
def test_a_failed_commit_rolls_back_and_says_so(tmp_path, monkeypatch):
    xw = tmp_path / "data" / "crosswalk.db"
    s = X.session(tmp_path / "b1", xw, ["batch1_a.csv", "batch1_b.csv"])
    X.turn_on(s)
    X.run(s)
    X.decide_truth(s)
    before = xw.read_bytes()
    real = apply.plan_commit

    def bad(store, view, reviewer, time):
        plan = real(store, view, reviewer, time)
        # A how the CHECK constraint refuses, after rows were already inserted in the transaction.
        return dataclasses.replace(plan, keys=plan.keys + (("f" * 64, plan.keys[0][1], "guessed"),))
    monkeypatch.setattr(apply, "plan_commit", bad)
    receipt = X.download(s, tmp_path / "o1")
    assert xw.read_bytes() == before
    assert ("outputs.note.crosswalk_failed", {}) in receipt.notes
    assert not any(e.code == "CROSSWALK_UPDATED" for e in s.audit)


def test_download_leaves_nothing_stale_and_process_again_is_the_same(tmp_path):
    xw = tmp_path / "data" / "crosswalk.db"
    s = X.session(tmp_path / "b1", xw, ["batch1_a.csv", "batch1_b.csv"])
    X.turn_on(s)
    X.run(s)
    X.decide_truth(s)
    X.download(s, tmp_path / "o1")
    assert not s.stale
    digest, earlier = s.results.digest(), s.results.counts.matched_from_earlier
    X.run(s)
    assert s.results.digest() == digest and s.results.counts.matched_from_earlier == earlier == 0


def test_master_ids_with_the_crosswalk_off_are_m06s():
    assert master_id("064ab6000867a82fc1aae7bbbbf3d62558904674cd07672d911107e7ea45d2af") == "M-a7e53489dc"
    assert master_id("1479425de31cd50ffc98c3d015fb5f7ea08fe5c57c8c2981b4f43ee0f12f96c6") == "M-10438b4e7e"


def test_the_receipt_and_audit_line_after_a_commit(tmp_path):
    xw = tmp_path / "data" / "crosswalk.db"
    s = X.session(tmp_path / "b1", xw, ["batch1_a.csv", "batch1_b.csv"])
    X.turn_on(s)
    X.run(s)
    X.decide_truth(s)
    receipt = X.download(s, tmp_path / "o1")
    assert ("outputs.note.crosswalk_failed", {}) not in receipt.notes
    up = [e for e in s.audit if e.code == "CROSSWALK_UPDATED"]
    assert len(up) == 1 and up[0].get("count")[0] == 10 and up[0].get("reviewer") == ["Joe"]
