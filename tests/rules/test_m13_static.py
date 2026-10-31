"""M13's static checks: no random and no clock call in engine/ or session/ outside the injected clock, and only the standard
library for the backup, the crosswalk and calibration."""
import ast
import re
import sys

from tests.conftest import ROOT

ENGINE_SESSION = [p for d in ("engine", "session") for p in (ROOT / "wholecount" / d).rglob("*.py")]


def test_no_random_anywhere_in_engine_or_session():
    for p in ENGINE_SESSION:
        tree = ast.parse(p.read_text(encoding="utf-8"))
        mods = {a.name for n in ast.walk(tree) if isinstance(n, ast.Import) for a in n.names}
        mods |= {n.module or "" for n in ast.walk(tree) if isinstance(n, ast.ImportFrom)}
        assert "random" not in mods, p


def test_the_only_clock_call_is_the_injected_default():
    hits = []
    for p in ENGINE_SESSION:
        for i, line in enumerate(p.read_text(encoding="utf-8").splitlines(), 1):
            if re.search(r"datetime\.now|time\.time\(\)|date\.today|utcnow", line):
                hits.append((p.relative_to(ROOT).as_posix(), line.strip()))
    assert hits == [("wholecount/session/state.py", "self.clock = clock or (lambda: dt.datetime.now(dt.timezone.utc))")]


def test_m13_modules_use_the_standard_library_only():
    files = [ROOT / "wholecount" / "engine" / "secretbackup.py", ROOT / "wholecount" / "session" / "backup.py",
             ROOT / "wholecount" / "session" / "crosswalk.py", ROOT / "wholecount" / "session" / "calibration.py"]
    files += list((ROOT / "wholecount" / "engine" / "crosswalk").glob("*.py"))
    files += list((ROOT / "wholecount" / "engine" / "calibration").glob("*.py"))
    for p in files:
        tree = ast.parse(p.read_text(encoding="utf-8"))
        mods = {a.name.split(".")[0] for n in ast.walk(tree) if isinstance(n, ast.Import) for a in n.names}
        mods |= {(n.module or "").split(".")[0] for n in ast.walk(tree) if isinstance(n, ast.ImportFrom) and n.level == 0}
        outside = {m for m in mods if m not in sys.stdlib_module_names and m != "wholecount"}
        assert not outside, (p.name, outside)
