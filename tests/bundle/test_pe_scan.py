"""Windows networking imports (M14, SPEC 12.1 layer 3). On a Windows folder, every binary that imports a networking DLL is in
PE_NETWORK_IMPORT_ALLOWLIST and no entry is stale. The logic is tested on Linux with imported_dlls stubbed."""
import shutil
import sys

import pytest

from tools import pe_net_imports as pe
from tools.offline_rules import PE_NETWORK_IMPORT_ALLOWLIST


def problems(found, allow=PE_NETWORK_IMPORT_ALLOWLIST):
    """(binaries that import a networking DLL and aren't allowed, allowlist entries that no binary needs)."""
    names = {p.rsplit("/", 1)[-1].lower() for p in found}
    return sorted(n for n in names if n not in allow), sorted(a for a in allow if a not in names)


def test_logic_with_a_stubbed_scan(monkeypatch, tmp_path):
    for n in ("python312.dll", "Qt6Network.dll", "plain.dll"):
        (tmp_path / n).write_bytes(b"MZ")
    table = {"python312.dll": {"ws2_32.dll"}, "Qt6Network.dll": {"ws2_32.dll", "dnsapi.dll"}, "plain.dll": {"kernel32.dll"}}
    monkeypatch.setattr(pe, "imported_dlls", lambda p: table[p.name])
    found = pe.scan(tmp_path)
    assert set(found) == {"python312.dll", "Qt6Network.dll"}
    bad, stale = problems(found, frozenset({"python312.dll", "select.pyd"}))
    assert bad == ["qt6network.dll"] and stale == ["select.pyd"]


@pytest.mark.skipif(sys.platform != "win32", reason="needs a Windows build with PE files")
def test_every_networking_binary_is_allowed_and_no_entry_is_stale(dist):
    bad, stale = problems(pe.scan(dist))
    assert bad == [] and stale == []


@pytest.mark.skipif(sys.platform != "win32", reason="needs a Windows build with PE files")
def test_a_renamed_allowed_binary_is_flagged(dist, tmp_path):
    src = next(p for p in dist.rglob("*") if p.name.lower() in PE_NETWORK_IMPORT_ALLOWLIST)
    shutil.copy(src, tmp_path / ("renamed_" + src.name))
    bad, _ = problems(pe.scan(tmp_path))
    assert bad == [("renamed_" + src.name).lower()]
