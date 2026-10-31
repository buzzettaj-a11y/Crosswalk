"""REVF-1: the run ID is stable across decisions and run order, and differs under another secret."""
import hashlib
import hmac

from tests.fixtures.outputs.fixture import session
from tests.support.session import decide_all
from wholecount.engine.outputs.review_file import run_id
from wholecount.session.export import build_view


def test_stable(tmp_path):
    s = session(tmp_path / "a")
    first = build_view(s).run_id
    decide_all(s)
    from wholecount.session import commands as C
    if s.results.confidence.level == "low":
        s.history.execute(C.AcknowledgeLowConfidence())
    assert build_view(s).run_id == first
    keys = [w.table.key for w in s.results.works]
    other = lambda m: hmac.new(bytes(range(32, 64)), m, hashlib.sha256).digest()  # noqa: E731
    assert run_id(s.secret.mac, list(reversed(keys))) == first and run_id(other, keys) != first
