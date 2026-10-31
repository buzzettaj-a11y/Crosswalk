"""The version 1.1 copy claims (M10 to M12): each has a test that drives the behavior the sentence states, not one that only
reads the sentence back. A test drives the behavior when it calls anything beyond reading copy and widget text."""
import ast
import pathlib

from tests.conftest import ROOT
from wholecount import copy

V11 = ("CL-TRUST-SAVED-01", "CL-PRACTICE-01", "CL-BALANCE-LOC-01", "CL-NOADDR-COUNTED-01", "CL-LOC-COUNTS-01",
       "CL-REVIEWER-LOGGED-01", "CL-NOTE-INTERNAL-01", "CL-UNMATCHED-SCREEN-01", "CL-COORDS-INTERNAL-01", "CL-SMALLCELL-01",
       "CL-RUN-MAPS-01")
# Calls that only build a static screen or read text back. Anything else runs the app: a session, a command, a click, a
# download, a log.
READS = {"claim", "parametrize", "get", "text", "texts", "findChild", "findChildren", "isVisible", "objectName", "len", "str",
         "int", "bool", "repr", "set", "list", "tuple", "dict", "sorted", "all", "any", "next", "items", "keys", "values",
         "lower", "upper", "strip", "split", "join", "startswith", "endswith", "replace", "format", "encode", "isinstance",
         "after_run", "make_window", "settle", "labels", "panel", "named", "maxLength", "findData", "isChecked", "toolTip"}


def _marked(fn):
    return {a.value for d in fn.decorator_list for a in ast.walk(d) if isinstance(a, ast.Constant) and isinstance(a.value, str)}


def _module_marks(tree):
    out = set()
    for n in tree.body:
        if isinstance(n, ast.Assign) and any(isinstance(t, ast.Name) and t.id == "pytestmark" for t in n.targets):
            out |= {a.value for a in ast.walk(n.value) if isinstance(a, ast.Constant) and isinstance(a.value, str)}
    return out


def drives_behavior(fn):
    calls = {c.func.attr if isinstance(c.func, ast.Attribute) else getattr(c.func, "id", "") for c in ast.walk(fn)
             if isinstance(c, ast.Call)}
    return bool(calls - READS)


def claims_to_tests(paths):
    """{claim ID: [(file, function name, drives behavior)]}."""
    out = {}
    for p in paths:
        tree = ast.parse(pathlib.Path(p).read_text(encoding="utf-8"))
        module = _module_marks(tree)
        for fn in (n for n in ast.walk(tree) if isinstance(n, ast.FunctionDef) and n.name.startswith("test")):
            for cid in (_marked(fn) | module) & set(V11):
                out.setdefault(cid, []).append((pathlib.Path(p).name, fn.name, drives_behavior(fn)))
    return out


def test_every_v11_claim_is_registered():
    assert set(V11) <= set(copy.claims())


def test_every_v11_claim_has_a_test_that_drives_the_behavior():
    found = claims_to_tests(sorted((ROOT / "tests").rglob("test_*.py")))
    for cid in V11:
        assert cid in found, f"{cid} has no test"
        assert any(d for _, _, d in found[cid]), f"{cid} is only read back: {found[cid]}"


def test_a_test_that_only_reads_the_text_is_caught(tmp_path):
    f = tmp_path / "test_fake.py"
    f.write_text("import pytest\nfrom wholecount import copy\n\n"
                 "@pytest.mark.claim('CL-SMALLCELL-01')\n"
                 "def test_reads(make_window):\n"
                 "    w = make_window(F.after_run())\n"
                 "    assert w.findChild(QLabel, 'x').text() == copy.get('a')\n\n"
                 "@pytest.mark.claim('CL-RUN-MAPS-01')\n"
                 "def test_drives(tmp_path):\n"
                 "    s = example_session(tmp_path)\n"
                 "    s.history.execute(C.AcknowledgeLowConfidence())\n", encoding="utf-8")
    found = claims_to_tests([f])
    assert found["CL-SMALLCELL-01"] == [("test_fake.py", "test_reads", False)]
    assert found["CL-RUN-MAPS-01"] == [("test_fake.py", "test_drives", True)]
