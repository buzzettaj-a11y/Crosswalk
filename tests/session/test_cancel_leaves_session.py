"""A cancelled run leaves the session as it was: the new state is built beside the old one."""
import pytest

from tests.support.session import base, snapshot
from wholecount.engine.progress import RecordingSink
from wholecount.session.loader import Cancelled
from wholecount.session.runner import process


def test_cancel(tmp_path):
    s = base(tmp_path)
    before = (snapshot(s), s.results.version)
    s._load_cache = None
    with pytest.raises(Cancelled):
        process(s, RecordingSink(cancel_after=0))
    assert (snapshot(s), s.results.version) == before
