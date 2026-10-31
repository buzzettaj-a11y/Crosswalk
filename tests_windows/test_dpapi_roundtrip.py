"""The real DPAPI calls, under the offline guard, on Windows only."""
import json
import pathlib
import subprocess
import sys

import pytest

pytestmark = pytest.mark.skipif(sys.platform != "win32", reason="DPAPI needs Windows")
ROOT = pathlib.Path(__file__).resolve().parents[1]


def test_dpapi_round_trip_under_the_guard():
    code = (f"import sys, json; sys.path.insert(0, {str(ROOT)!r}); import wholecount.guard as g; v = g.install_for_app(); "
            "from wholecount.session import dpapi; s = bytes(range(32)); b = dpapi.protect(s); "
            "print(json.dumps({'same': dpapi.unprotect(b) == s, 'plain': s in b, 'longer': len(b) > 32, 'violations': v}))")
    p = subprocess.run([sys.executable, "-I", "-c", code], capture_output=True, text=True, timeout=60)
    assert p.returncode == 0, p.stderr
    assert json.loads(p.stdout.strip().splitlines()[-1]) == {"same": True, "plain": False, "longer": True, "violations": []}
