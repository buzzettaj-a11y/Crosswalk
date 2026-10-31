"""STORE-6: an imported set-up is validated: unknown keys, wrong types and oversize files are refused; a valid one round-trips."""
import json

import pytest

from tests.fixtures.outputs.fixture import session
from wholecount.session.state import Setup
from wholecount.session.store import StoreError, export_setup, import_setup


def test_round_trip(tmp_path):
    s = session(tmp_path)
    s.setup.set("defaults", ("S.csv", 0, "Program"), "Youth")
    export_setup(s.setup, tmp_path / "s.json")
    assert import_setup(tmp_path / "s.json", Setup()).get("defaults", ("S.csv", 0, "Program")) == "Youth"


@pytest.mark.parametrize("body,code", [
    ({"setup_format": 1, "setup": {"secrets": []}}, "unknown_key"),
    ({"setup_format": 1, "setup": {}, "extra": 1}, "unknown_key"),
    ({"setup_format": 1, "setup": {"mappings": "x"}}, "wrong_type"),
    ({"setup_format": 9, "setup": {}}, "unknown_version"),
    ({"setup_format": 1, "setup": {"schema": [[{"t": "dc", "c": "os.system", "f": {}}, 1]]}}, "unknown_value"),
])
def test_refusals(tmp_path, body, code):
    p = tmp_path / "bad.json"
    p.write_text(json.dumps(body))
    with pytest.raises(StoreError, match=code):
        import_setup(p, Setup())


def test_oversize(tmp_path):
    p = tmp_path / "big.json"
    p.write_text(" " * 1_000_001)
    with pytest.raises(StoreError, match="too_big"):
        import_setup(p, Setup())
