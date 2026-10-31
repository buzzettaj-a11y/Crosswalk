"""Off by default, never used by a practice run, and Forget (M13 XW-1)."""
from tests.support import crosswalk as X
from tests.support.example_session import decide, example_session
from tests.support.outputs import write
from wholecount.session import crosswalk
from wholecount.session.crosswalk import ForgetCrosswalk


def test_off_creates_no_file(tmp_path):
    xw = tmp_path / "data" / "crosswalk.db"
    s = X.session(tmp_path / "b1", xw, ["batch1_a.csv", "batch1_b.csv"])
    X.run(s)
    X.decide_truth(s)
    X.download(s, tmp_path / "o1")
    assert not xw.exists() and crosswalk.state(s) == "off" and s.results.counts.matched_from_earlier is None


def test_a_practice_run_never_reads_or_writes_it(tmp_path):
    xw = tmp_path / "data" / "crosswalk.db"
    (tmp_path / "ex").mkdir()
    s = example_session(tmp_path / "ex")
    s.crosswalk_path = xw
    X.turn_on(s)
    before = xw.read_bytes()
    from wholecount.session.runner import process
    process(s)
    assert s.results.practice and s.results.crosswalk is None
    decide(s)
    write(s, tmp_path / "o1")
    assert xw.read_bytes() == before


def test_turn_on_and_forget(tmp_path):
    xw = tmp_path / "data" / "crosswalk.db"
    s = X.session(tmp_path / "b1", xw, ["batch1_a.csv", "batch1_b.csv"])
    X.run(s)
    never = s.results.digest()
    X.turn_on(s)
    on = [e for e in s.audit if e.code == "CROSSWALK_ON"]
    assert len(on) == 1 and on[0].get("reviewer") == ["Joe"] and on[0].get("time_iso")
    assert "identity" in s.stale and "programs" in s.stale
    X.run(s)
    X.decide_truth(s)
    X.download(s, tmp_path / "o1")
    assert not ForgetCrosswalk("forgot").run(s) and xw.exists()
    assert ForgetCrosswalk("forget").run(s) and not xw.exists()
    assert "identity" in s.stale and any(e.code == "CROSSWALK_FORGET" for e in s.audit)
    fresh = X.session(tmp_path / "b2", xw, ["batch1_a.csv", "batch1_b.csv"], day=1)
    X.run(fresh)
    assert fresh.results.digest() == never
