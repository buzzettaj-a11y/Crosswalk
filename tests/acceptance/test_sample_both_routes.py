"""SPEC 13.5: the example data by the fast path and by every stage downloads the same files. Every data file is
byte-identical. The two audit logs are identical once timestamps and the route-only events below are removed."""
import re

import pytest

# (event code, reason code) that only one route writes, and why. Any other differing line fails the test.
ROUTE_ONLY = {
    ("SETUP_CHANGE", "prepare_confirmed"): "Tidy up's Continue, which a person presses stage by stage; the fast path skips Tidy up",
    ("SETUP_CHANGE", "table_confirmed"): "Match your columns' Confirm, once per table, which the fast path doesn't ask for",
}
LOGS = ("PRACTICE_Internal_Audit_Log.txt", "PRACTICE_Shareable_Audit_Log.txt")
_STAMP = re.compile(r"^\d{4}-\d\d-\d\dT\d\d:\d\d:\d\dZ ")


def event(line):
    """(code, reason_code) of a log line with its timestamp removed, or (line, "") for a header line."""
    parts = line.split(" ", 1)
    m = re.search(r'reason_code="([^"]*)"', line)
    return parts[0], m.group(1) if m else ""


def comparable(path):
    lines = [_STAMP.sub("", line) for line in path.read_text(encoding="utf-8").splitlines()]
    return [line for line in lines if event(line) not in ROUTE_ONLY]


def files(folder):
    return sorted(p.relative_to(folder) for p in folder.rglob("*") if p.is_file())


def test_both_routes_write_the_same_files(practice_routes):
    fast, stage = practice_routes["fast"][2], practice_routes["stage"][2]
    assert files(fast) == files(stage)
    assert len(files(fast)) == 8


def test_every_data_file_is_byte_identical(practice_routes):
    fast, stage = practice_routes["fast"][2], practice_routes["stage"][2]
    for rel in files(fast):
        if rel.name not in LOGS:
            assert (fast / rel).read_bytes() == (stage / rel).read_bytes(), rel


@pytest.mark.parametrize("log", LOGS)
def test_audit_logs_match_without_timestamps_and_route_only_events(practice_routes, log):
    fast, stage = practice_routes["fast"][2], practice_routes["stage"][2]
    a, b = comparable(fast / log), comparable(stage / log)
    if a != b:
        differing = sorted({event(x)[0] for x in set(a) ^ set(b)})
        pytest.fail(f"lines differ with event codes {differing}")


def test_the_route_only_events_are_real(practice_routes):
    """Each listed event appears in the stage-by-stage logs and not in the fast path's, so the list holds nothing stale."""
    fast, stage = practice_routes["fast"][2], practice_routes["stage"][2]
    for log in LOGS:
        seen_stage = {event(_STAMP.sub("", x)) for x in (stage / log).read_text(encoding="utf-8").splitlines()}
        seen_fast = {event(_STAMP.sub("", x)) for x in (fast / log).read_text(encoding="utf-8").splitlines()}
        for ev in ROUTE_ONLY:
            assert ev in seen_stage and ev not in seen_fast, (log, ev)


def test_both_routes_give_the_planned_counts(practice_routes):
    from tests.acceptance.drive import PLAN

    want = PLAN["counts"]["after_decisions"]
    for name in ("fast", "stage"):
        c = practice_routes[name][0].results.counts
        assert (c.received, c.counted, c.not_counted_yet, c.set_aside) == (
            want["rows_received"], want["counted"], want["not_counted_yet"], want["set_aside"])
        assert (c.goal1.low, c.goal1.high, c.goal2.low, c.goal2.high) == (
            want["goal_1"]["low"], want["goal_1"]["high"], want["goal_2"]["low"], want["goal_2"]["high"])
        assert {k: (v.low, v.high) for k, v in c.per_program.items()} == {k: (v, v) for k, v in want["per_program"].items()}
