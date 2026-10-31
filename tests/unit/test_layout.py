"""SPEC 3.3: the package layout exists, each package with a one-line docstring __init__.py."""
import ast

import pytest

from tests.conftest import ROOT

PACKAGES = [
    "wholecount", "wholecount/guard", "wholecount/copy", "wholecount/settings", "wholecount/session",
    "wholecount/engine", "wholecount/engine/read", "wholecount/engine/prepare", "wholecount/engine/standardize",
    "wholecount/engine/geo", "wholecount/engine/outputs",
    "wholecount/ui", "wholecount/ui/theme", "wholecount/ui/frame", "wholecount/ui/stages", "wholecount/ui/widgets",
    "tools", "tests", "tests/unit", "tests/rules", "tests/audit", "tests/golden", "tests/invariants", "tests/offline", "tests/ui",
    "tests/copy", "tests/acceptance",
]
KEPT_EMPTY = ["tests_windows", "installer", "build"]


@pytest.mark.parametrize("pkg", PACKAGES)
def test_package_exists_with_a_docstring(pkg):
    init = ROOT / pkg / "__init__.py"
    assert init.is_file(), pkg
    tree = ast.parse(init.read_text(encoding="utf-8"))
    assert ast.get_docstring(tree), pkg


@pytest.mark.parametrize("folder", KEPT_EMPTY)
def test_placeholder_folder_exists(folder):
    assert (ROOT / folder / ".gitkeep").is_file()


@pytest.mark.parametrize("pkg", [p for p in PACKAGES if p.startswith("wholecount/") and p not in ("wholecount/guard", "wholecount/copy", "wholecount/ui/theme", "wholecount/ui/stages")])
def test_later_packages_hold_only_their_docstring(pkg):
    """Each later milestone creates its own module files, so these packages hold nothing else yet."""
    init = ROOT / pkg / "__init__.py"
    tree = ast.parse(init.read_text(encoding="utf-8"))
    assert len(tree.body) == 1 and ast.get_docstring(tree), pkg


def test_wholecount_init_imports_nothing():
    tree = ast.parse((ROOT / "wholecount" / "__init__.py").read_text(encoding="utf-8"))
    assert len(tree.body) == 1 and ast.get_docstring(tree)
