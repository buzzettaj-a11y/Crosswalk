"""Saved progress with the real DPAPI on Windows: save, load, and a flipped byte is caught. Skipped elsewhere."""
import sys

import pytest

pytestmark = pytest.mark.skipif(sys.platform != "win32", reason="Windows DPAPI only")


def test_round_trip_and_damage(tmp_path):
    from wholecount.session.store import Store, StoreError

    store = Store(tmp_path)
    path = store.save("x", {"format": 1, "decisions": []})
    assert store.load(path)["format"] == 1
    raw = bytearray(path.read_bytes())
    raw[-3] ^= 1
    path.write_bytes(bytes(raw))
    with pytest.raises(StoreError, match="damaged"):
        store.load(path)
