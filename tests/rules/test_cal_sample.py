"""The calibration pass and the sample (M13 CAL-1)."""
import os
import subprocess
import sys

import pytest

from tests.conftest import ROOT
from tests.support import calibration as K
from tests.support.secrets import OTHER_SECRET
from wholecount.engine.calibration.sample import band_of, calibration_pass, draw_sample
from wholecount.session.calibration import person_rows
from wholecount.session.secret_store import InstallSecret


@pytest.fixture(scope="module")
def pop(tmp_path_factory):
    return K.population_session(tmp_path_factory.mktemp("pop"))


def test_bands_are_exact_at_their_edges():
    for s, b in ((39, None), (40, 1), (61, 1), (62, 2), (79, 2), (80, 3), (99, 3), (100, 4), (180, 4)):
        assert band_of(s, [40, 62, 80, 100]) == b, s


def test_at_most_per_band_a_thin_band_gives_all_and_joins_are_capped(pop):
    res = calibration_pass(person_rows(pop.results))
    assert all(res.populations[b] for b in (1, 2, 3, 4))
    sample = draw_sample(res.proposals, res.joins, 100, pop.secret.mac, 200)
    by = {b: sum(1 for p in sample if p.band == b) for b in (1, 2, 3, 4)}
    assert all(n <= 100 for n in by.values())
    assert by[2] == res.populations[2] < 100
    assert sum(1 for p in sample if p.kind == "join") == min(200, len(res.joins))
    small = draw_sample(res.proposals, res.joins, 3, pop.secret.mac, 10)
    assert sum(1 for p in small if p.kind == "join") == 10
    assert min(p.score for p in res.proposals) >= 40


def test_the_same_draw_twice_with_shuffled_rows_and_another_secret_differs(pop, tmp_path):
    rows = person_rows(pop.results)
    res = calibration_pass(rows)
    a = draw_sample(res.proposals, res.joins, 5, pop.secret.mac)
    assert a == draw_sample(res.proposals, res.joins, 5, pop.secret.mac)
    rev = calibration_pass(list(reversed(rows)))
    assert {p.pair_id for p in draw_sample(rev.proposals, rev.joins, 5, pop.secret.mac)} == {p.pair_id for p in a}
    other = draw_sample(res.proposals, res.joins, 5, InstallSecret(OTHER_SECRET).mac)
    assert {p.pair_id for p in other} != {p.pair_id for p in a}


def test_the_draw_does_not_depend_on_the_hash_seed(pop):
    code = ("import sys, json; sys.path.insert(0, %r); from tests.support.secrets import TEST_SECRET; "
            "from wholecount.session.secret_store import InstallSecret; "
            "from wholecount.engine.calibration.sample import draw_sample, calibration_pass; "
            "import pickle; rows = pickle.load(open(sys.argv[1], 'rb')); r = calibration_pass(rows); "
            "print(json.dumps([p.pair_id for p in draw_sample(r.proposals, r.joins, 5, InstallSecret(TEST_SECRET).mac)]))"
            % str(ROOT))
    import pickle
    import tempfile
    rows = person_rows(pop.results)
    f = tempfile.NamedTemporaryFile(delete=False, suffix=".pkl")
    pickle.dump(rows, f)
    f.close()
    outs = set()
    for seed in ("1", "2"):
        p = subprocess.run([sys.executable, "-c", code, f.name], capture_output=True, text=True, timeout=120,
                           env={**os.environ, "PYTHONHASHSEED": seed})
        assert p.returncode == 0, p.stderr
        outs.add(p.stdout)
    os.unlink(f.name)
    assert len(outs) == 1


def test_a_pass_changes_nothing_in_the_session(pop):
    before = (pop.results.digest(), len(pop.history.stack), len(pop.decisions), set(pop.stale))
    calibration_pass(person_rows(pop.results))
    K.draw(pop)
    assert (pop.results.digest(), len(pop.history.stack), len(pop.decisions), set(pop.stale)) == before
    assert min(p.score for p in pop.results.identity.proposals) >= 62


def test_no_random_in_the_engine():
    for p in (ROOT / "wholecount" / "engine").rglob("*.py"):
        text = p.read_text(encoding="utf-8")
        assert "import random" not in text and "from random" not in text, p
