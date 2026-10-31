"""Shared runs for the acceptance tests. Each route runs once per test session, because a run takes several seconds."""
import pytest

from tests.acceptance import drive


@pytest.fixture(scope="session")
def practice_routes(tmp_path_factory):
    """The example data by both routes with the sample reference: {"fast": (session, receipt, folder), "stage": ...}."""
    base = tmp_path_factory.mktemp("practice")
    out = {}
    for name, route in (("fast", drive.fast_path), ("stage", drive.by_stage)):
        s, receipt = route(drive.copy_inputs(base / f"in_{name}"), base / f"out_{name}")
        out[name] = (s, receipt, base / f"out_{name}")
    return out


@pytest.fixture(scope="session")
def no_backend_run(tmp_path_factory):
    """The example files as the operator's own files with nothing to place addresses: (session, receipt, folder)."""
    base = tmp_path_factory.mktemp("nobackend")
    s, receipt = drive.fast_path(drive.copy_inputs(base / "in"), base / "out", practice=False)
    return s, receipt, base / "out"


def results_numbers(s):
    """What Results shows, as plain numbers, so a test can compare files with it without importing the app."""
    c = s.results.counts
    return {"goal1": (c.goal1.low, c.goal1.high), "goal2": (c.goal2.low, c.goal2.high), "open_pairs": c.open_pairs,
            "open_copy_groups": c.open_copy_groups, "received": c.received}


def _run(tmp_path_factory, name, review):
    base = tmp_path_factory.mktemp(name)
    s, _ = drive.fast_path(drive.copy_inputs(base / "in"), base / "out", practice=False, review=review)
    return base / "out", results_numbers(s)


@pytest.fixture(scope="session")
def open_run(tmp_path_factory):
    """Every pair and copy group left open, no backend: (folder, Results numbers)."""
    return _run(tmp_path_factory, "open", drive.review_open)


@pytest.fixture(scope="session")
def different_run(tmp_path_factory):
    """Every open pair and possible copy group decided as different, no backend: (folder, Results numbers)."""
    return _run(tmp_path_factory, "different", drive.review_different)


@pytest.fixture(scope="session")
def planned_run(practice_routes):
    """The practice run by the fast path with the planned decisions: (folder, Results numbers)."""
    s, _, folder = practice_routes["fast"]
    return folder, results_numbers(s)
