"""A-07: the old program preview cleared decisions. preview_counts works on a copy."""
from tests.support.session import decided
from wholecount.session.decisions import make
from wholecount.session.runner import preview_counts


def test_preview_changes_nothing(tmp_path):
    s = decided(tmp_path)
    before = (s.decisions.snapshot(), s.stale, list(s.history.stack), s.results.version, s.results.digest())
    d = make("program", (), "Housing|Workforce|confirm", s.now_iso(), "Joe",
             detail=(("program_kind", "confirm"), ("program", "Housing"), ("program", "Workforce")))
    preview = preview_counts(s, [d])
    assert preview.per_program != s.counts().per_program and len(preview.per_program) == 2
    assert (s.decisions.snapshot(), s.stale, list(s.history.stack), s.results.version, s.results.digest()) == before
