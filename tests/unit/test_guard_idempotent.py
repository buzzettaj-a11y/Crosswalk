"""install_for_app is idempotent (M14): the frozen app installs it from the runtime hook and from __main__. In a fresh
python -I subprocess, as the research says, so pytest's own process never carries the guard."""
import subprocess
import sys

from tests.conftest import ROOT

CODE = r"""
import sys
sys.path.insert(0, %r)
from wholecount.guard import install_for_app
from wholecount.guard import offline_guard
hooks = []
real = sys.addaudithook
sys.addaudithook = lambda h: (hooks.append(h), real(h))[1]
a = install_for_app(geosupport_dirs=())
b = install_for_app(geosupport_dirs=())
import wholecount.guard as g
print(len(hooks), a is b, g.INSTALLED)
try:
    sys.audit("socket.connect", None, ("192.0.2.1", 80))
except Exception as e:
    print(type(e).__name__, len(a))
"""


def test_a_second_install_adds_no_second_hook():
    p = subprocess.run([sys.executable, "-I", "-c", CODE % str(ROOT)], capture_output=True, text=True, timeout=120)
    assert p.returncode == 0, p.stderr
    first, second = p.stdout.strip().splitlines()
    assert first == "1 True True"
    assert second == "OfflineViolation 1"
