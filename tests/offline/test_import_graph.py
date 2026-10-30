"""Layer: runtime import graph (H1, research R6). Starts the real app import graph in a fresh interpreter and inspects sys.modules."""
import json
import os
import subprocess
import sys

import pytest

from tests.conftest import ROOT
from tools.offline_rules import FORBIDDEN_MODULES

pytestmark = pytest.mark.claim("CL-OFFLINE-01")


def test_app_import_graph_has_no_network_modules():
    env = dict(os.environ, QT_QPA_PLATFORM="offscreen")
    code = f"import sys, json; sys.path.insert(0, {str(ROOT)!r}); import wholecount.app_imports; print(json.dumps(sorted(sys.modules)))"
    p = subprocess.run([sys.executable, "-I", "-c", code], capture_output=True, text=True, env=env, cwd=ROOT, timeout=120)
    assert p.returncode == 0, p.stderr[-2000:]
    loaded = set(json.loads(p.stdout.strip().splitlines()[-1]))
    bad = sorted(m for m in loaded if m in FORBIDDEN_MODULES)
    assert not bad, f"forbidden modules imported by the app: {bad}"


def test_app_import_graph_loads_under_the_guard_with_no_violations():
    env = dict(os.environ, QT_QPA_PLATFORM="offscreen")
    code = (f"import sys, json; sys.path.insert(0, {str(ROOT)!r}); import wholecount.guard as g; v = g.install_for_app(); "
            "import wholecount.app_imports; print(json.dumps(v))")
    p = subprocess.run([sys.executable, "-I", "-c", code], capture_output=True, text=True, env=env, cwd=ROOT, timeout=120)
    assert p.returncode == 0, p.stderr[-2000:]
    assert json.loads(p.stdout.strip().splitlines()[-1]) == []
