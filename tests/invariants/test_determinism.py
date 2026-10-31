"""H3: the same inputs and decisions give the same digest, and shuffled rows give the same record keys, outcomes and counts."""
import random

from tests.fixtures.session import r_fixture
from tests.support.session import decide_all
from wholecount.session.runner import process


def run(tmp_path, rows):
    s = r_fixture.session(tmp_path, paths=r_fixture.files(tmp_path, r=rows))
    process(s)
    return decide_all(s)


def test_same_inputs_same_digest(tmp_path):
    a, b = run(tmp_path / "a", r_fixture.r_rows()), run(tmp_path / "b", r_fixture.r_rows())
    assert a.results.digest() == b.results.digest()


def test_shuffled_rows(tmp_path):
    rows = r_fixture.r_rows()
    shuffled = list(rows)
    random.Random(3).shuffle(shuffled)
    a, b = run(tmp_path / "a", rows), run(tmp_path / "b", shuffled)
    assert set(a.results.outcomes) == set(b.results.outcomes)
    assert {k: (o.count_status, o.reasons) for k, o in a.results.outcomes.items()} == \
        {k: (o.count_status, o.reasons) for k, o in b.results.outcomes.items()}
    assert a.counts() == b.counts()
