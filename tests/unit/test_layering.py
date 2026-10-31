"""SPEC 3.2: the engine has no Qt and never reaches up; the UI reaches the engine only through the session layer. Checked by AST."""
from tests.conftest import ROOT
from tools.offline_scan import scan_layering

RULES = {
    "wholecount.engine": ("PySide6", "shiboken6", "wholecount.session", "wholecount.ui"),
    "wholecount.session": ("wholecount.ui",),
    "wholecount.ui": ("wholecount.engine",),
}


def test_layers_import_only_downward():
    paths = sorted((ROOT / "wholecount").rglob("*.py"))
    assert scan_layering(paths, ROOT, RULES) == []


def test_layering_negative_controls(tmp_path):
    files = {
        "wholecount/engine/x.py": "from PySide6 import QtCore\nimport wholecount.session.state\n",
        "wholecount/engine/read/y.py": "from wholecount.ui import theme\n",
        "wholecount/session/z.py": "import wholecount.ui.frame\n",
        "wholecount/ui/w.py": "from wholecount.engine import counts\nfrom wholecount.session import state\n",
        "wholecount/enginex.py": "from PySide6 import QtCore\n",
    }
    for rel, text in files.items():
        (tmp_path / rel).parent.mkdir(parents=True, exist_ok=True)
        (tmp_path / rel).write_text(text)
    bad = scan_layering([tmp_path / r for r in files], tmp_path, RULES)
    assert sorted(bad) == sorted([
        ("wholecount/engine/x.py", "PySide6"),
        ("wholecount/engine/x.py", "PySide6.QtCore"),
        ("wholecount/engine/x.py", "wholecount.session.state"),
        ("wholecount/engine/read/y.py", "wholecount.ui"),
        ("wholecount/engine/read/y.py", "wholecount.ui.theme"),
        ("wholecount/session/z.py", "wholecount.ui.frame"),
        ("wholecount/ui/w.py", "wholecount.engine"),
        ("wholecount/ui/w.py", "wholecount.engine.counts"),
    ])
