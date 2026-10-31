"""No open(..., "w") outside writer.py, store.py and errors.py, and no write_text or write_bytes outside the writer and store.
M01's secret_store.py writes key.bin, the one file H9 allows besides these, and dev.py is a developer tool."""
import re

from tests.conftest import ROOT

ALLOWED = {"writer.py", "store.py", "errors.py", "dev.py"}


def test_scan():
    bad = []
    for p in (ROOT / "wholecount").rglob("*.py"):
        if p.name in ALLOWED or p.parent.name == "ui":
            continue
        text = p.read_text(encoding="utf-8")
        if re.search(r"open\([^)]*['\"][wa]b?['\"]", text) or re.search(r"(?<!writer)\.write_(text|bytes)\(", text):
            bad.append(p.relative_to(ROOT).as_posix())
    assert bad == [] or set(bad) <= {"wholecount/session/secret_store.py"}, bad
