"""List binaries (.dll/.pyd/.exe) that import Windows networking DLLs. Pure Python (pefile), runs on Linux against a Windows dist folder.

Taken from docs/research/offline-enforcement.md R6. M14's bundle tests use it.
"""
import pathlib
import sys

import pefile

NET_DLLS = {"ws2_32.dll", "wsock32.dll", "mswsock.dll", "winhttp.dll", "wininet.dll", "urlmon.dll", "iphlpapi.dll", "dnsapi.dll",
            "netapi32.dll", "mpr.dll", "wldap32.dll", "httpapi.dll", "webservices.dll", "rasapi32.dll", "wlanapi.dll", "nlaapi.dll"}


def imported_dlls(path):
    pe = pefile.PE(str(path), fast_load=True)
    pe.parse_data_directories(directories=[pefile.DIRECTORY_ENTRY["IMAGE_DIRECTORY_ENTRY_IMPORT"],
                                           pefile.DIRECTORY_ENTRY["IMAGE_DIRECTORY_ENTRY_DELAY_IMPORT"]])
    names = {e.dll.decode("ascii", "replace").lower() for a in ("DIRECTORY_ENTRY_IMPORT", "DIRECTORY_ENTRY_DELAY_IMPORT") for e in getattr(pe, a, [])}
    pe.close()
    return names


def scan(root):
    out = {}
    for p in sorted(pathlib.Path(root).rglob("*")):
        if p.suffix.lower() in (".dll", ".pyd", ".exe"):
            try:
                hit = imported_dlls(p) & NET_DLLS
            except pefile.PEFormatError:
                continue
            if hit:
                out[p.relative_to(root).as_posix()] = sorted(hit)
    return out


if __name__ == "__main__":
    for f, d in scan(sys.argv[1]).items():
        print(f"{f}: {d}")
