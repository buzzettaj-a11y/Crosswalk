"""H11: every claim in the registry has at least one test marked @pytest.mark.claim("ID"), and every marker names a real claim."""
import ast
import pathlib

from tests.conftest import ROOT
from wholecount import copy


def _claim_ids(node):
    """Claim IDs from a pytest.mark.claim("ID") expression, or a list or tuple of them."""
    if isinstance(node, (ast.List, ast.Tuple)):
        for el in node.elts:
            yield from _claim_ids(el)
    elif (isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute) and node.func.attr == "claim"
          and isinstance(node.func.value, ast.Attribute) and node.func.value.attr == "mark"):
        for arg in node.args:
            if isinstance(arg, ast.Constant) and isinstance(arg.value, str):
                yield arg.value


def claim_markers(paths):
    """{claim ID: [test file, ...]} from decorators and module-level pytestmark assignments."""
    found = {}
    for p in paths:
        tree = ast.parse(pathlib.Path(p).read_text(encoding="utf-8"))
        for n in ast.walk(tree):
            exprs = []
            if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
                exprs = n.decorator_list
            elif isinstance(n, ast.Assign) and any(isinstance(t, ast.Name) and t.id == "pytestmark" for t in n.targets):
                exprs = [n.value]
            for e in exprs:
                for cid in _claim_ids(e):
                    found.setdefault(cid, []).append(pathlib.Path(p).name)
    return found


def test_every_claim_has_a_test():
    markers = claim_markers(sorted((ROOT / "tests").rglob("*.py")))
    missing = sorted(set(copy.claims()) - set(markers))
    assert not missing, missing


def test_every_marker_names_a_real_claim():
    markers = claim_markers(sorted((ROOT / "tests").rglob("*.py")))
    unknown = sorted(set(markers) - set(copy.claims()))
    assert not unknown, unknown


def test_marker_scan_negative_controls(tmp_path):
    f = tmp_path / "test_x.py"
    f.write_text(
        "import pytest\n"
        "pytestmark = [pytest.mark.claim('CL-A-01'), pytest.mark.slow]\n"
        "@pytest.mark.claim('CL-B-01')\n"
        "def test_b(): pass\n"
        "class TestC:\n"
        "    @pytest.mark.claim('CL-C-01')\n"
        "    def test_c(self): pass\n"
        "def test_d():\n"
        "    'pytest.mark.claim(\"CL-D-01\") in a string does not count'\n"
    )
    assert set(claim_markers([f])) == {"CL-A-01", "CL-B-01", "CL-C-01"}
