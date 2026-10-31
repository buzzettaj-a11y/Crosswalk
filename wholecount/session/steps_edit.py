"""Tidy-up step editing for the window, through the session layer (SPEC 3.2, 6.3)."""
from wholecount.engine.prepare.steps import DELIMITERS, KINDS, Step, restore_step, without_step  # noqa: F401


def next_step_id(steps):
    used = {s.step_id for s in steps}
    n = 1
    while f"u{n}" in used:
        n += 1
    return f"u{n}"


def with_added(steps, kind, params):
    steps = list(steps)
    return steps + [Step(next_step_id(steps), kind, dict(params), origin="added")]
