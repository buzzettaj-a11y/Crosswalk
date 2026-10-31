"""H8: `python -m wholecount.dev` prints counts only. The printer is tested in a subprocess, because importing dev installs the guard."""
import os
import re
import subprocess
import sys

from tests.conftest import ROOT
from tests.support.guarded import run_guarded
from wholecount import brand

LINE_RE = re.compile(r"^[a-z_]+( [A-Z]+)? [0-9,]+$")


def test_printer_takes_closed_labels_ints_and_source_letters_only():
    r = run_guarded("""
        import io
        from wholecount import dev
        buf = io.StringIO()
        dev.emit(dev.CountLabel.PINS_RUNTIME, 1234567, out=buf)
        dev.emit(dev.CountLabel.GUARD_VIOLATIONS, 0, scope='B', out=buf)
        out['lines'] = buf.getvalue().splitlines()
        attempt('str value', lambda: dev.emit(dev.CountLabel.PINS_RUNTIME, 'Maria Lopez', out=buf))
        attempt('bool value', lambda: dev.emit(dev.CountLabel.PINS_RUNTIME, True, out=buf))
        attempt('float value', lambda: dev.emit(dev.CountLabel.PINS_RUNTIME, 1.5, out=buf))
        attempt('str label', lambda: dev.emit('pins_runtime', 1, out=buf))
        attempt('word scope', lambda: dev.emit(dev.CountLabel.PINS_RUNTIME, 1, scope='clients', out=buf))
        attempt('digit scope', lambda: dev.emit(dev.CountLabel.PINS_RUNTIME, 1, scope='1', out=buf))
        attempt('lower scope', lambda: dev.emit(dev.CountLabel.PINS_RUNTIME, 1, scope='b', out=buf))
        out['after'] = len(buf.getvalue().splitlines())
    """, install="[]")
    assert r.pop("lines") == ["pins_runtime 1,234,567", "guard_violations B 0"]
    assert r.pop("after") == 2
    assert r == {
        "str value": "other:TypeError", "bool value": "other:TypeError", "float value": "other:TypeError",
        "str label": "other:TypeError", "word scope": "other:ValueError", "digit scope": "other:ValueError",
        "lower scope": "other:ValueError",
    }, r


def test_count_labels_are_a_closed_lowercase_set():
    r = run_guarded("""
        from wholecount import dev
        out['labels'] = [l.value for l in dev.CountLabel]
    """, install="[]")
    assert r["labels"][:7] == ["pins_runtime", "pins_dev", "approved_distributions", "claims_in_registry", "audit_ids_listed",
                               "modules_imported_under_guard", "guard_violations"]
    assert all(re.fullmatch(r"[a-z_]+", label) for label in r["labels"]) and len(set(r["labels"])) == len(r["labels"])


def test_check_prints_counts_only_and_no_violations():
    env = dict(os.environ, QT_QPA_PLATFORM="offscreen")
    p = subprocess.run([sys.executable, "-m", "wholecount.dev", "check"], cwd=ROOT, capture_output=True, text=True, env=env, timeout=180)
    assert p.returncode == 0, p.stdout + p.stderr[-2000:]
    lines = p.stdout.splitlines()
    assert lines and all(LINE_RE.match(ln) for ln in lines), lines
    counts = dict(ln.rsplit(" ", 1) for ln in lines)
    assert counts["guard_violations"] == "0"
    assert counts["pins_runtime"] == "11"
    assert counts["approved_distributions"] == "11"
    assert counts["audit_ids_listed"] == "101"
    from wholecount import copy
    assert counts["claims_in_registry"] == str(len(copy.claims()))
    assert int(counts["modules_imported_under_guard"].replace(",", "")) > 100


def test_read_prints_counts_only(tmp_path):
    (tmp_path / "Zelphina Quorvath.csv").write_text("Client_ID,First_Name,Last_Name,SSN\nQX-1,Zelphina,Quorvath,078-05-1120\n")
    (tmp_path / "bad.csv").write_bytes(b"A\n\x81\n")
    p = subprocess.run([sys.executable, "-m", "wholecount.dev", "read", str(tmp_path / "Zelphina Quorvath.csv"), str(tmp_path / "bad.csv")],
                       cwd=ROOT, capture_output=True, text=True, timeout=120)
    assert p.returncode == 0, p.stderr
    lines = p.stdout.splitlines()
    assert all(LINE_RE.match(ln) for ln in lines), lines
    assert "Zelphina" not in p.stdout and "Quorvath" not in p.stdout and "QX-1" not in p.stdout
    counts = dict(ln.rsplit(" ", 1) for ln in lines)
    assert counts["balanced A"] == "1" and counts["rows_included A"] == "1" and counts["sensitive_columns_dropped A"] == "1"
    assert counts["files_read"] == "1" and counts["files_unreadable"] == "1"


def test_why_names_denied_events_without_paths():
    r = run_guarded(r"""
        from wholecount import dev
        import io
        buf = io.StringIO()
        for v in ['import of socket', "open of network path '\\\\\\\\server\\\\share\\\\clients.csv'",
                  "_winapi.CreateFile of network path 'x'", "ctypes.dlopen 'ws2_32'", 'subprocess.Popen']:
            dev.emit_denied(v, out=buf)
        out['lines'] = buf.getvalue().splitlines()
    """, install="[]")
    assert r["lines"] == ["denied import socket", "denied open", "denied _winapi.CreateFile", "denied ctypes.dlopen 'ws2_32'",
                          "denied subprocess.Popen"]


def test_main_entry_prints_name_and_version():
    p = subprocess.run([sys.executable, "-m", "wholecount"], cwd=ROOT, capture_output=True, text=True, timeout=60)
    assert p.returncode == 0, p.stderr
    assert p.stdout.strip() == f"{brand.PRODUCT_NAME} {brand.VERSION}"
