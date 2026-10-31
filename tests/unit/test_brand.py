"""The product name lives in one constant (SPEC preamble, H11). It appears as a string literal only in brand.py, and in no copy text."""
import ast

from tests.conftest import ROOT
from wholecount import brand, copy


def test_brand_constants():
    assert brand.PRODUCT_NAME == "Wholecount"
    assert brand.PACKAGE_NAME == "wholecount"
    assert brand.VERSION == "0.1.0"


def _docstrings(path):
    tree = ast.parse(path.read_text(encoding="utf-8"))
    out = set()
    for n in ast.walk(tree):
        if isinstance(n, (ast.Module, ast.ClassDef, ast.FunctionDef, ast.AsyncFunctionDef)) and n.body:
            first = n.body[0]
            if isinstance(first, ast.Expr) and isinstance(first.value, ast.Constant) and isinstance(first.value.value, str):
                out.add(id(first.value))
    return tree, out


def product_name_literals(paths, root, name=None):
    """String constants that contain the product name, ignoring docstrings, which are not user-facing.
    Case-sensitive, because the package name is the same word in lowercase and appears in module paths."""
    name = name or brand.PRODUCT_NAME
    bad = []
    for p in paths:
        tree, docs = _docstrings(p)
        for n in ast.walk(tree):
            if isinstance(n, ast.Constant) and isinstance(n.value, str) and id(n) not in docs and name in n.value:
                bad.append(p.relative_to(root).as_posix())
    return bad


def test_product_name_is_a_literal_only_in_brand():
    paths = sorted((ROOT / "wholecount").rglob("*.py"))
    assert product_name_literals(paths, ROOT) == ["wholecount/brand.py"]


def test_product_name_check_catches_a_literal(tmp_path):
    (tmp_path / "wholecount").mkdir()
    bad = tmp_path / "wholecount" / "x.py"
    bad.write_text('"""Wholecount docstrings are fine."""\nTITLE = "Wholecount results"\n')
    assert product_name_literals([bad], tmp_path) == ["wholecount/x.py"]


def test_product_name_appears_in_no_copy_text():
    assert [e.key for e in copy.all_entries() if brand.PRODUCT_NAME.lower() in e.text.lower()] == []
