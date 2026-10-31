"""M15 acceptance finding: Show data names why a header row may be wrong, and every warning the engine gives has its
sentence. A missing one crashed the preview for the example housing sheet."""
from wholecount import copy
from wholecount.engine.read.tables import HEADER_WARNINGS


def test_every_header_warning_has_a_sentence():
    for code in HEADER_WARNINGS:
        assert copy.get(f"preview.header_reason.{code}")


def test_no_sentence_for_a_warning_the_engine_never_gives():
    keys = [e.key for e in copy.all_entries() if e.key.startswith("preview.header_reason.")]
    assert sorted(k.rsplit(".", 1)[1] for k in keys) == sorted(HEADER_WARNINGS)
