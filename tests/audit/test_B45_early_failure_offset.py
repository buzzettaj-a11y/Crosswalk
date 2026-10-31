"""B-45: one shared random stream meant an early failed row shifted every later row's jitter. Each row stands alone now."""
from tests.support.geo import MAC, NO_EXTRAS, reference_of, row
from wholecount.engine.geo.offset import PrivacyOffset
from wholecount.engine.geo.place import place_rows

N = 400


def _rows():
    return [row(f"r{i}", f"{i + 1} Test St", "11201") for i in range(N)]


def _reference(include_first):
    pts = [(str(i + 1), "Test St", "11201", "Brooklyn", 40.6 + i * 0.0002, -73.95) for i in range(N)]
    return reference_of(pts if include_first else pts[1:])


def _moved(pr):
    off = PrivacyOffset(MAC)
    return {k: off.apply(pr.building_keys[k], r.latitude, r.longitude) for k, r in pr.results.items() if r.placed}


def test_row_zero_failing_changes_no_other_row():
    good = place_rows(_rows(), _reference(True), None, NO_EXTRAS)
    bad = place_rows(_rows(), _reference(False), None, NO_EXTRAS)
    assert not bad.results["r0"].placed and good.results["r0"].placed
    for i in range(1, N):
        assert bad.results[f"r{i}"] == good.results[f"r{i}"]
    g, b = _moved(good), _moved(bad)
    assert all(b[k] == g[k] for k in b)
    assert len(b) == N - 1


class _Boom:
    name, release = "reference", "1"

    def __init__(self, inner):
        self.inner = inner

    def lookup(self, house, street, where):
        if house == "1":
            raise RuntimeError("broken row")
        return self.inner.lookup(house, street, where)


def test_an_exception_in_one_row_is_that_row_only():
    good = place_rows(_rows(), _reference(True), None, NO_EXTRAS)
    bad = place_rows(_rows(), _Boom(_reference(True)), None, NO_EXTRAS)
    assert bad.results["r0"].reason == "not_found"
    assert all(bad.results[f"r{i}"] == good.results[f"r{i}"] for i in range(1, N))
