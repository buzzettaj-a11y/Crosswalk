"""M15 acceptance finding: the Download button's job commits the saved crosswalk, as the session's download() does (XW-6)."""
import dataclasses

from tests.support import crosswalk as X
from tests.support.files_run import ack
from wholecount.engine.crosswalk import apply
from wholecount.engine.outputs.view import ExportSettings
from wholecount.engine.progress import NullSink
from wholecount.ui.jobs.actions import DownloadJob


def _download(s, folder):
    got = []
    folder.mkdir(parents=True)
    job = DownloadJob(s, folder, ExportSettings(), lambda kind, value: got.append((kind, value)))
    job.apply(s, job.run(NullSink()))
    return got[0]


def _batch(tmp_path):
    xw = tmp_path / "data" / "crosswalk.db"
    s = X.session(tmp_path / "b1", xw, ["batch1_a.csv", "batch1_b.csv"])
    X.turn_on(s)
    X.run(s)
    X.decide_truth(s)
    ack(s)
    return s, xw


def test_the_download_job_commits_the_crosswalk(tmp_path):
    s, _ = _batch(tmp_path)
    kind, receipt = _download(s, tmp_path / "o1")
    assert kind == "done"
    assert ("outputs.note.crosswalk_failed", {}) not in receipt.notes
    up = [e for e in s.audit if e.code == "CROSSWALK_UPDATED"]
    assert len(up) == 1 and up[0].get("count")[0] == 10
    assert not s.stale


def test_a_failed_commit_from_the_job_says_so_on_the_receipt(tmp_path, monkeypatch):
    s, xw = _batch(tmp_path)
    before = xw.read_bytes()
    real = apply.plan_commit

    def bad(store, view, reviewer, time):
        plan = real(store, view, reviewer, time)
        return dataclasses.replace(plan, keys=plan.keys + (("f" * 64, plan.keys[0][1], "guessed"),))
    monkeypatch.setattr(apply, "plan_commit", bad)
    kind, receipt = _download(s, tmp_path / "o1")
    assert kind == "done" and ("outputs.note.crosswalk_failed", {}) in receipt.notes
    assert xw.read_bytes() == before
