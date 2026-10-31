"""H3: no random and no clock call in engine/ or session/ outside the one injected default clock."""
import ast
import re

from tests.conftest import ROOT


def test_scan():
    bad = []
    for base in ("engine", "session"):
        for p in (ROOT / "wholecount" / base).rglob("*.py"):
            text = p.read_text(encoding="utf-8")
            tree = ast.parse(text)
            for n in ast.walk(tree):
                if isinstance(n, (ast.Import, ast.ImportFrom)):
                    names = [a.name for a in n.names] + ([n.module] if isinstance(n, ast.ImportFrom) and n.module else [])
                    if "random" in names:
                        bad.append(f"{p.name}: import random")
            for m in re.finditer(r"(datetime\.now|date\.today|time\.time\(|time\.monotonic)", text):
                line = text[:m.start()].count("\n") + 1
                if not (p.name == "state.py" and "self.clock = clock or" in text.splitlines()[line - 1]):
                    bad.append(f"{p.name}:{line}")
    assert bad == []
