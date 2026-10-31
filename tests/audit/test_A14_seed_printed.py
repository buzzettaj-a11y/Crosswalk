"""A-14: the old app printed the jitter seed in its audit. Now no secret, offset, 1337 or seed reaches a result, the audit or a
progress line, and the audit records only that the offset was applied (P-GEO-7, H8)."""
import dataclasses

import pytest

from tests.support.geo import NO_EXTRAS, fake, row
from tests.support.secrets import TEST_SECRET
from wholecount import copy
from wholecount.engine.geo.place import place_rows
from wholecount.engine.progress import RecordingSink, render

pytestmark = pytest.mark.claim("CL-GEO-OFFSET-02")

ADDRESSES = ["1 Main St", "11 Main St", "100 W 10 St", "85 Montague St", "123 Fulton St"]


def test_nothing_secret_in_results_audit_or_progress():
    rows = [row(f"r{i}", ADDRESSES[i % 5], "11201") for i in range(20)]
    sink = RecordingSink()
    pr = place_rows(rows, fake(), None, NO_EXTRAS, sink)
    texts = [repr(r) for r in pr.results.values()] + [repr(a) for a in pr.audit]
    texts += [render(m) for m in sink.messages()]
    forbidden = [TEST_SECRET.hex(), repr(TEST_SECRET), "1337", "seed"]
    for t in texts:
        for f in forbidden:
            assert f not in t.lower()
    (applied,) = [a for a in pr.audit if a.event == "privacy_offset_applied"]
    assert (applied.backend, applied.release) == ("fake", "")
    assert copy.get("audit.geo.privacy_offset_applied") == "Privacy offset applied to map points."
    for a in pr.audit:
        assert all(isinstance(getattr(a, f.name), (str, int, bool)) for f in dataclasses.fields(a))
