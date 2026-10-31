"""build_view(session) -> FrameView (SPEC 11.3): a snapshot from the session with no rule worked out in the UI."""
from tests.support.session import base, decided
from wholecount.ui.frame.view import FrameView, build_view


def test_view_from_the_r_fixture(tmp_path):
    s = base(tmp_path)
    v = build_view(s)
    assert isinstance(v, FrameView)
    c = s.results.counts
    assert (v.counts.received, v.counts.counted, v.counts.not_counted_yet, v.counts.set_aside) == \
        (c.received, c.counted, c.not_counted_yet, c.set_aside)
    assert v.counts.goal1 == (c.goal1.low, c.goal1.high) and v.counts.is_final == c.final
    assert v.confidence.level == s.results.confidence.level
    assert v.files == 2 and v.tables == 2 and v.has_run


def test_view_is_frozen_and_has_no_cell_values(tmp_path):
    import dataclasses

    s = decided(tmp_path)
    v = build_view(s)
    assert dataclasses.is_dataclass(v)
    text = repr(v)
    for r in s.results.rows.values():
        for _, val in r.values.items():
            if val.entered and len(val.entered) >= 4 and not val.entered.isdigit():
                assert val.entered not in text, val.entered


def test_before_a_run(tmp_path):
    from tests.fixtures.session import r_fixture

    s = r_fixture.session(tmp_path)
    v = build_view(s)
    assert v.counts is None and v.confidence is None and not v.has_run and v.files == 2
