"""M15 performance finding: a decision re-ran tidying, matching, standardizing, placing and the copy search, though none of
them depends on a decision. A run after a decision now reuses those steps, the way loading is reused, and gives the same
results as a full run. Process itself always runs every step."""
from tests.support.example_session import PLAN, decide, example_session, key
from wholecount.engine import pipeline as pl
from wholecount.session import commands as C
from wholecount.session.runner import process


class Counter:
    def __init__(self, monkeypatch):
        self.n = 0
        real = pl.standardize

        def counted(*a, **k):
            self.n += 1
            return real(*a, **k)
        monkeypatch.setattr(pl, "standardize", counted)


def test_a_decision_reuses_the_steps_before_decisions(tmp_path, monkeypatch):
    s = example_session(tmp_path)
    c = Counter(monkeypatch)
    g = PLAN["decisions"]["copy_groups"][0]
    members = {key(s, x) for x in g["rows"]}
    grp = next(x for x in s.results.groups if set(x.members) == members)
    s.history.execute(C.KeepOneInCopyGroup(grp.group_id, key(s, g["keep"])))
    assert c.n == 0 and not s.stale


def test_results_after_reuse_equal_a_full_run(tmp_path):
    s = decide(example_session(tmp_path))
    reused = s.results.digest()
    process(s)
    assert s.results.digest() == reused


def test_process_runs_every_step(tmp_path, monkeypatch):
    s = example_session(tmp_path)
    c = Counter(monkeypatch)
    process(s)
    assert c.n == len(s.results.works) > 0


def test_a_set_up_change_is_never_reused(tmp_path, monkeypatch):
    s = example_session(tmp_path)
    from wholecount.session.runner import recompute_from

    s.history.execute(C.SetupChange("run_settings", "extra_fields", frozenset({"census_tract"})))
    c = Counter(monkeypatch)
    recompute_from(s)
    assert c.n == len(s.results.works)
