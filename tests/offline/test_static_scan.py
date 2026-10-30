"""Layer: source hygiene (H1, H2, SPEC 12.1 layer 3). Pure text and AST checks over the app source.

The research's three source checks (R6) are here, plus model files, legacy imports and the os.startfile exemption. R6's two lockfile
checks are in test_lockfile.py. Each check has a negative control that feeds the same helper a bad temp file.
"""
import ast
import pathlib
import subprocess

import pytest

from tests.conftest import ROOT
from tools.offline_rules import MODEL_BIN_MAX_BYTES, MODEL_FILE_SUFFIXES
from tools.offline_scan import imported_modules, scan_forbidden_calls, scan_imports, scan_startfile, scan_url_literals

pytestmark = pytest.mark.claim("CL-OFFLINE-01")


def app_sources(root=ROOT):
    """Every .py file under wholecount/, except the guard, which names what it forbids."""
    return [p for p in sorted((root / "wholecount").rglob("*.py")) if "guard" not in p.relative_to(root / "wholecount").parts[:1]]


def write(tmp_path, rel, text):
    p = tmp_path / rel
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(text)
    return p


def test_app_sources_are_found():
    names = {p.relative_to(ROOT).as_posix() for p in app_sources()}
    assert "wholecount/__main__.py" in names and "wholecount/dev.py" in names
    assert not any(n.startswith("wholecount/guard/") for n in names)


# R6's source checks

def test_no_forbidden_imports_in_app_source():
    assert scan_imports(app_sources(), ROOT) == []


def test_no_url_literals_in_app_source():
    assert scan_url_literals(app_sources(), ROOT) == []


def test_no_desktop_services_or_shell_open_calls():
    assert scan_forbidden_calls(app_sources(), ROOT) == []


def test_negative_controls_for_the_source_checks(tmp_path):
    bad = write(tmp_path, "wholecount/bad.py",
                "import socket\nfrom PySide6 import QtNetwork\nfrom PySide6.QtGui import QDesktopServices\n"
                "URL = 'https://example.com/x'\nUNC = '\\\\\\\\server\\\\share'\nimport subprocess\n")
    assert {m for _, m in scan_imports([bad], tmp_path)} >= {"socket", "PySide6.QtNetwork"}
    assert {m for _, m in scan_url_literals([bad], tmp_path)} == {"https://example.com/x", "\\\\server\\share"}
    assert {m for _, m in scan_forbidden_calls([bad], tmp_path)} == {"QDesktopServices", "subprocess"}
    ok = write(tmp_path, "wholecount/ok.py", "NS = 'http://schemas.openxmlformats.org/spreadsheetml/2006/main'\n")
    assert scan_url_literals([ok], tmp_path) == []


# Added in M00

def repo_files(root=ROOT):
    """Tracked and untracked-but-not-ignored files, so .venv and build outputs don't count."""
    out = subprocess.run(["git", "ls-files", "--cached", "--others", "--exclude-standard", "-z"], cwd=root,
                         capture_output=True, check=True).stdout.decode().split("\0")
    return [root / f for f in out if f and (root / f).is_file()]


def model_files(paths, root):
    bad = []
    for p in paths:
        rel = p.relative_to(root).as_posix()
        if rel.startswith("legacy/"):
            continue
        if p.suffix.lower() in MODEL_FILE_SUFFIXES or (p.suffix.lower() == ".bin" and p.stat().st_size > MODEL_BIN_MAX_BYTES):
            bad.append(rel)
    return bad


def test_no_model_files_in_repo():
    """H2, SPEC 12.2: no model files anywhere outside legacy/."""
    assert model_files(repo_files(), ROOT) == []


def test_model_file_check_catches_suffixes_and_big_bin_files(tmp_path):
    files = [write(tmp_path, "a/model.onnx", "x"), write(tmp_path, "b/weights.SAFETENSORS", "x"),
             write(tmp_path, "c/small.bin", "x"), write(tmp_path, "legacy/old.pkl", "x")]
    big = tmp_path / "d" / "big.bin"
    big.parent.mkdir()
    big.write_bytes(b"\0" * (MODEL_BIN_MAX_BYTES + 1))
    assert sorted(model_files(files + [big], tmp_path)) == ["a/model.onnx", "b/weights.SAFETENSORS", "d/big.bin"]


def legacy_imports(paths, root):
    bad = []
    for p in paths:
        tree = ast.parse(p.read_text(encoding="utf-8"))
        bad += [(p.relative_to(root).as_posix(), m) for m in imported_modules(tree) if m.split(".")[0] == "legacy"]
        for n in ast.walk(tree):
            if isinstance(n, ast.Constant) and isinstance(n.value, str) and n.value.replace("\\", "/").rstrip("/").endswith("/legacy"):
                bad.append((p.relative_to(root).as_posix(), "path to legacy/"))
    return bad


def test_no_import_from_legacy():
    paths = sorted((ROOT / "wholecount").rglob("*.py")) + sorted((ROOT / "tools").rglob("*.py"))
    assert legacy_imports(paths, ROOT) == []


def test_legacy_import_check_catches_imports(tmp_path):
    bad = write(tmp_path, "wholecount/x.py", "import legacy.identity\nfrom legacy import app\n")
    assert {m for _, m in legacy_imports([bad], tmp_path)} >= {"legacy.identity", "legacy"}


def test_startfile_only_in_ui_shell():
    """SPEC 12.6: the only os.startfile in the code base is in wholecount/ui/shell.py."""
    paths = sorted((ROOT / "wholecount").rglob("*.py")) + sorted((ROOT / "tools").rglob("*.py"))
    assert scan_startfile(paths, ROOT) == []


def test_startfile_exemption_covers_one_file_and_one_pattern(tmp_path):
    call = "import os, subprocess\nos.startfile(path, 'open')\n"
    shell = write(tmp_path, "wholecount/ui/shell.py", call + "from PySide6.QtGui import QDesktopServices\n")
    other = write(tmp_path, "wholecount/ui/other.py", call)
    tool = write(tmp_path, "tools/x.py", "from os import startfile\ngetattr(os, 'startfile')\n")
    assert scan_startfile([shell], tmp_path) == []
    assert scan_startfile([other], tmp_path) == [("wholecount/ui/other.py", "os.startfile")]
    assert sorted(m for _, m in scan_startfile([tool], tmp_path)) == ["from os import startfile", "getattr startfile"]
    assert sorted(m for _, m in scan_forbidden_calls([shell], tmp_path)) == ["QDesktopServices", "subprocess"]
