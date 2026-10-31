"""The installer's firewall rule blocks the program it names (research 7.3, with its control). The probe is a separate small
exe built without the guard, so only the firewall stands between it and the network. The rule text is the installer's."""
import pathlib
import socket
import subprocess
import sys

import pytest

pytestmark = [pytest.mark.windows, pytest.mark.skipif(sys.platform != "win32", reason="Windows only")]
ROOT = pathlib.Path(__file__).resolve().parents[1]
NETSH = r"C:\Windows\System32\netsh.exe"
PROBE = '''
import socket, sys
s = socket.socket(); s.settimeout(3)
try:
    s.connect((sys.argv[1], int(sys.argv[2]))); print("CONNECTED")
except OSError as e:
    print("BLOCKED_OR_FAILED", e.errno)
'''


def iss_rule(direction, program_dir):
    """The installer's add-rule parameters for one direction, with {app} replaced and the name made the probe's."""
    sys.path.insert(0, str(ROOT))
    from tests.unit.test_iss import netsh_params

    line = next(p for p in netsh_params("Run") if p.startswith("advfirewall firewall add rule") and f"dir={direction}" in p)
    line = line.replace("{app}\\Wholecount.exe", str(program_dir / "probe.exe"))
    return line.replace("Wholecount offline", "Wholecount probe")


def run_probe(exe, host, port):
    return subprocess.run([str(exe), host, str(port)], capture_output=True, text=True, timeout=30).stdout.strip()


def test_outbound_block_rule_blocks_the_ruled_program(tmp_path):
    src = tmp_path / "probe.py"
    src.write_text(PROBE)
    subprocess.run([sys.executable, "-m", "PyInstaller", "--onefile", "--distpath", str(tmp_path / "dist"), "--workpath",
                    str(tmp_path / "work"), "--specpath", str(tmp_path), str(src)], check=True)
    exe = tmp_path / "dist" / "probe.exe"
    host = socket.gethostbyname(socket.gethostname())
    srv = socket.socket()
    srv.bind((host, 0))
    srv.listen(5)
    port = srv.getsockname()[1]
    rule = iss_rule("out", exe.parent)
    name = rule.split('name="', 1)[1].split('"', 1)[0]
    try:
        assert run_probe(exe, host, port) == "CONNECTED", "control failed"
        subprocess.run(f'"{NETSH}" {rule}', check=True, shell=False)
        assert run_probe(exe, host, port).startswith("BLOCKED_OR_FAILED")
    finally:
        subprocess.run([NETSH, "advfirewall", "firewall", "delete", "rule", f"name={name}"])
        srv.close()
