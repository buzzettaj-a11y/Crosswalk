"""A-20 (Medium, closed by design): the old launchers ran `pip install` on every start and launched a second, server-based UI.

The rewrite ships no launcher script, no code path that installs packages or starts a server or browser, no lock that names the
old server stack, and both entry points install the offline guard before anything else.
"""
import ast
import subprocess

import pytest

from tests.conftest import DEV_LOCK, LOCK, ROOT
from tools.offline_scan import lock_pins, scan_module_use

pytestmark = pytest.mark.claim("CL-OFFLINE-01")

LAUNCHER_NAMES = ("run.bat", "run.sh", "launch.py")
LAUNCHER_SUFFIXES = (".command", ".vbs")
BANNED_MODULES = ("pip", "streamlit", "fastapi", "uvicorn", "webbrowser")
# These name the banned modules on purpose, as deny lists and scan patterns.
EXEMPT = ("tools/offline_rules.py", "tools/offline_scan.py")


def repo_files():
    out = subprocess.run(["git", "ls-files", "--cached", "--others", "--exclude-standard", "-z"], cwd=ROOT,
                         capture_output=True, check=True).stdout.decode().split("\0")
    return [f for f in out if f]


def launcher_files(rel_paths):
    bad = []
    for rel in rel_paths:
        if rel.startswith(("legacy/", "docs/")):
            continue
        name = rel.rsplit("/", 1)[-1]
        if name in LAUNCHER_NAMES or name.lower().endswith(LAUNCHER_SUFFIXES) or "start here" in name.lower():
            bad.append(rel)
    return bad


def scanned_sources(root=ROOT):
    paths = sorted((root / "wholecount").rglob("*.py")) + sorted((root / "tools").rglob("*.py"))
    return [p for p in paths if p.relative_to(root).as_posix() not in EXEMPT
            and not p.relative_to(root).as_posix().startswith("wholecount/guard/")]


def test_no_launcher_scripts_outside_legacy_and_docs():
    assert launcher_files(repo_files()) == []


def test_launcher_check_catches_the_old_names():
    paths = ["run.bat", "tools/run.sh", "Crosswalk.vbs", "Stop Crosswalk.command", "START HERE.txt", "launch.py",
             "legacy/run.sh", "docs/context/START_HERE.md", "wholecount/__main__.py"]
    assert launcher_files(paths) == ["run.bat", "tools/run.sh", "Crosswalk.vbs", "Stop Crosswalk.command", "START HERE.txt", "launch.py"]


def test_no_pip_server_or_browser_use_in_source():
    assert scan_module_use(scanned_sources(), BANNED_MODULES, ROOT) == []


def test_module_use_check_catches_imports_and_calls(tmp_path):
    (tmp_path / "wholecount").mkdir()
    bad = tmp_path / "wholecount" / "bad.py"
    bad.write_text("import webbrowser\nfrom pip._internal import main\nwebbrowser.open('x')\n# import streamlit\nNAME = 'uvicorn'\n")
    found = scan_module_use([bad], BANNED_MODULES, tmp_path)
    assert ("wholecount/bad.py", "webbrowser") in found
    assert ("wholecount/bad.py", "pip._internal") in found
    assert ("wholecount/bad.py", "webbrowser call") in found
    assert not any("streamlit" in m or "uvicorn" in m for _, m in found)


def test_neither_lock_names_the_old_server_stack():
    for lock in (LOCK, DEV_LOCK):
        pinned = set(lock_pins(lock.read_text(encoding="utf-8")))
        assert not pinned & {"streamlit", "fastapi", "uvicorn"}, lock.name


def first_statements(path):
    """The module's statements after its docstring."""
    body = ast.parse(path.read_text(encoding="utf-8")).body
    if body and isinstance(body[0], ast.Expr) and isinstance(body[0].value, ast.Constant) and isinstance(body[0].value.value, str):
        body = body[1:]
    return body


def installs_guard_first(path):
    """True if the module imports install_for_app from wholecount.guard and calls it before any other statement."""
    body = first_statements(path)
    if len(body) < 2:
        return False
    imp, call = body[0], body[1]
    imports_guard = (isinstance(imp, ast.ImportFrom) and imp.module == "wholecount.guard"
                     and [a.name for a in imp.names] == ["install_for_app"])
    value = call.value if isinstance(call, (ast.Expr, ast.Assign)) else None
    calls_install = isinstance(value, ast.Call) and isinstance(value.func, ast.Name) and value.func.id == "install_for_app"
    return imports_guard and calls_install


@pytest.mark.parametrize("entry", ["wholecount/__main__.py", "wholecount/dev.py"])
def test_entry_points_install_the_guard_first(entry):
    assert installs_guard_first(ROOT / entry)


def test_guard_first_check_catches_a_late_install(tmp_path):
    late = tmp_path / "late.py"
    late.write_text('"""Doc."""\nimport pandas\nfrom wholecount.guard import install_for_app\ninstall_for_app()\n')
    assert not installs_guard_first(late)
    good = tmp_path / "good.py"
    good.write_text('"""Doc."""\nfrom wholecount.guard import install_for_app\n\nv = install_for_app()\nimport pandas\n')
    assert installs_guard_first(good)
