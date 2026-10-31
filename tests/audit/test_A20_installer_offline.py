"""A-20 (Medium): the old build ran pip on every start and could reach the network. The installer, the build files, every
shipped module and every PowerShell script hold no URL and no download command; every other file under wholecount/, tools/
and build/ may name a URL or pip only on the provenance allowlist below, each with its reason (M14)."""
import pathlib
import re
import subprocess

import pytest

from tests.conftest import ROOT
from tools.offline_rules import URL_ALLOW_PREFIXES, URL_RE

pytestmark = pytest.mark.claim("CL-OFFLINE-01")

WORDS_RE = re.compile(r"\bpip\b|\bcurl\b|\bwget\b|Invoke-WebRequest|Start-BitsTransfer|DownloadFile|DownloadTemporaryFile")
NOT_SHIPPED = ("wholecount/dev.py", "wholecount/app_imports.py")
# File -> reason. A new entry needs a reason in the same change.
PROVENANCE = {
    "tools/make_zip_table.py": "the ZIP table's source (M03)",
    "wholecount/engine/geo/data/nyc_zips.csv": "the source column of the ZIP table (M03)",
    "tools/make_district_files.py": "the district files' source (M05)",
    "tools/offline_rules.py": "URL_RE and URL_ALLOW_PREFIXES are a pattern and XML namespaces",
    "build/spec_lists.py": "DEV_ONLY names pip so the build excludes it",
    "wholecount/ui/theme/fonts/SOURCE.txt": "the Archivo source (M10)",
    "wholecount/ui/theme/fonts/OFL.txt": "the Archivo license text names its own home pages (M10)",
    "tools/signing.json": "the timestamp server the maintainer's computer asks at signing time",
    "tools/data/README.md": "where the hand-saved ZIP and district source files came from (M03, M05)",
    "tools/offline_scan.py": "its lock and pip checks name pip to find it",
}
PROVENANCE_DIRS = ("tools/sandbox/",)


def repo_files():
    out = subprocess.run(["git", "ls-files", "--cached", "--others", "--exclude-standard", "-z"], cwd=ROOT,
                         capture_output=True, check=True).stdout.decode().split("\0")
    return [f for f in out if f]


def urls(text, unc_ok=False):
    found = [m.group(0) for m in URL_RE.finditer(text) if not m.group(0).startswith(URL_ALLOW_PREFIXES)]
    return [u for u in found if not (unc_ok and u.startswith("\\\\"))]


def strict_files(files):
    out = []
    for f in files:
        if f.startswith("installer/") or f in ("build/wholecount.spec", "build/rthook_offline.py"):
            out.append(f)
        elif f.startswith("wholecount/") and f.endswith(".py") and f not in NOT_SHIPPED:
            out.append(f)
        elif f.startswith("tools/") and f.endswith(".ps1"):
            out.append(f)
    return out


def strict_problems(root, files):
    bad = []
    for f in files:
        text = (pathlib.Path(root) / f).read_text(encoding="utf-8", errors="replace")
        guard = f.startswith("wholecount/guard/")
        # The guard names what it refuses: its network-path examples and its deny lists are exempt, its http URLs are not.
        if urls(text, unc_ok=guard):
            bad.append((f, "url"))
        if not guard and WORDS_RE.search(text):
            bad.append((f, "word"))
    return bad


def provenance_problems(root, files):
    strict = set(strict_files(files))
    bad = []
    for f in files:
        if f in strict or not f.startswith(("wholecount/", "tools/", "build/")):
            continue
        if f in PROVENANCE or f.startswith(PROVENANCE_DIRS):
            continue
        try:
            text = (pathlib.Path(root) / f).read_text(encoding="utf-8")
        except (UnicodeDecodeError, OSError):
            continue
        if urls(text) or re.search(r"\bpip\b", text):
            bad.append(f)
    return bad


def test_installer_build_shipped_code_and_scripts_hold_no_url_or_download():
    files = repo_files()
    scanned = strict_files(files)
    assert "installer/wholecount.iss" in scanned and "tools/build.ps1" in scanned and "wholecount/selfcheck.py" in scanned
    assert strict_problems(ROOT, scanned) == []


def test_every_other_url_or_pip_is_on_the_allowlist():
    assert provenance_problems(ROOT, repo_files()) == []
    assert all(reason for reason in PROVENANCE.values())


def test_no_launcher_scripts_in_the_shipped_folder():
    shipped = [f for f in repo_files() if f.startswith(("wholecount/", "installer/"))]
    assert [f for f in shipped if f.lower().endswith((".bat", ".cmd", ".sh", ".command", ".vbs"))] == []


def test_negative_controls(tmp_path):
    (tmp_path / "wholecount").mkdir()
    (tmp_path / "tools").mkdir()
    (tmp_path / "wholecount" / "x.py").write_text('URL = "https://example.com/api"\n')
    (tmp_path / "tools" / "go.ps1").write_text("pip install requests\n")
    (tmp_path / "wholecount" / "data.txt").write_text("see https://example.com\n")
    files = ["wholecount/x.py", "tools/go.ps1", "wholecount/data.txt"]
    assert strict_problems(tmp_path, strict_files(files)) == [("wholecount/x.py", "url"), ("tools/go.ps1", "word")]
    assert provenance_problems(tmp_path, files) == ["wholecount/data.txt"]
    assert urls("\\\\server\\share", unc_ok=True) == [] and urls("https://a.b/c", unc_ok=True) == ["https://a.b/c"]
