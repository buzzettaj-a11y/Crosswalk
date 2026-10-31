"""PowerShell from the Windows tests."""
import json
import subprocess


def ps(script):
    p = subprocess.run(["powershell", "-NoProfile", "-Command", script], capture_output=True, text=True, timeout=300)
    return p.returncode, p.stdout.strip(), p.stderr.strip()


def ps_json(script):
    code, out, err = ps(f"{script} | ConvertTo-Json -Depth 4")
    assert code == 0, err
    data = json.loads(out) if out else []
    return data if isinstance(data, list) else [data]
