"""Run code in a fresh `python -I` interpreter with the guard installed. Audit hooks can't be removed, so each case gets its own process."""
import json
import os
import pathlib
import subprocess
import sys
import textwrap

ROOT = pathlib.Path(__file__).resolve().parents[2]


def run_guarded(body, preload=(), install="offline_guard.install(allowed_dll_prefixes=['/nonexistent'], allowed_symbols=[])",
                env=None, timeout=60):
    """Run body after installing the guard and return the `out` dict it fills. attempt(name, fn) records blocked, NOT BLOCKED or other."""
    pre = "".join(f"import {m}\n" for m in preload)
    code = textwrap.dedent(f"""
        import sys, json
        sys.path.insert(0, {str(ROOT)!r})
        from wholecount.guard import offline_guard
        import wholecount.guard as guard
        """) + pre + textwrap.dedent(f"""
        violations = {install}
        V = offline_guard.OfflineViolation
        out = {{}}
        def attempt(name, fn):
            try:
                fn(); out[name] = 'NOT BLOCKED'
            except V as e:
                out[name] = 'blocked'
            except BaseException as e:
                out[name] = 'other:' + type(e).__name__
    """) + textwrap.dedent(body) + "\nprint(json.dumps(out))\n"
    p = subprocess.run([sys.executable, "-I", "-c", code], capture_output=True, text=True, timeout=timeout,
                       env=env if env is not None else dict(os.environ))
    assert p.returncode == 0, p.stderr
    return json.loads(p.stdout.strip().splitlines()[-1])
