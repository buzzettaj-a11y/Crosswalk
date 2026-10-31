"""A-25 (Low): the old docs named a launcher script and a function that didn't exist.

tools/check_doc_refs.py checks every file, command and code name in README.md and docs/*.md against the repository. It passes on
the real docs and finds both kinds of miss the audit found, a missing script and a missing function, without importing anything.
"""
import subprocess
import sys

from tests.conftest import ROOT
from tools import check_doc_refs


def test_real_docs_have_no_missing_references():
    assert check_doc_refs.check() == []


def test_reads_readme_and_top_level_docs_only():
    docs = check_doc_refs.docs()
    assert ROOT / "README.md" in docs
    assert ROOT / "docs" / "USER_GUIDE.md" in docs
    assert all(p.parent in (ROOT, ROOT / "docs") for p in docs)


def test_finds_a_missing_script_and_a_missing_function(tmp_path):
    """The negative control: the two kinds of miss in A-25."""
    doc = tmp_path / "BAD.md"
    doc.write_text("Run `run_wholecount.sh` on Linux.\n\n"
                   "Tables come from `wholecount.engine.geo.reference.detect_tables`.\n", encoding="utf-8")
    misses = check_doc_refs.check([doc])
    assert [(n, ref) for _, n, ref, _ in misses] == [(1, "run_wholecount.sh"), (3, "wholecount.engine.geo.reference.detect_tables")]


def test_finds_missing_targets_modules_paths_and_images(tmp_path):
    doc = tmp_path / "BAD.md"
    doc.write_text("`make nothere`\n`python -m wholecount.nothere`\n`tools/nothere.py`\n![shot](img/none.png)\n"
                   "`make test`\n`python -m wholecount`\n`wholecount.engine.geo.reference.ReferenceBackend.from_path`\n"
                   "`%LOCALAPPDATA%\\Wholecount\\reference\\`\n`<version>.exe`\n```\nmake nothere\n```\n", encoding="utf-8")
    misses = check_doc_refs.check([doc])
    assert [n for _, n, _, _ in misses] == [1, 2, 3, 4]


def test_checker_imports_nothing_it_checks():
    code = ("import sys; sys.path.insert(0, 'tools'); import check_doc_refs as c; c.check(); "
            "print(sorted(m for m in sys.modules if m.split('.')[0] in ('wholecount', 'tools')))")
    out = subprocess.run([sys.executable, "-I", "-c", code], cwd=ROOT, capture_output=True, text=True, check=True)
    assert out.stdout.strip() == "[]"
