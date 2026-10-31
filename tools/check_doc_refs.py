"""Checks the file, command and code names in the docs against the repository (A-25). A dev tool that never ships.

    python tools/check_doc_refs.py [DOC ...]

With no arguments it reads README.md and docs/*.md. The subfolders of docs/ (milestones, audit, research, context and
planning) are other people's records and aren't read. Every backticked reference outside fenced code blocks is checked:

- `make <target>` names a target in the Makefile
- `python -m <module>` names a module in the repository or the standard library
- `python <path>` names a file that exists
- a dotted name under `wholecount.` is a module, or a function, class or name in one, found by parsing with ast
- a path (it has a slash or a known extension) exists, or is one of the files the app or a build makes at run time
- an image link points at a file

References with angle brackets, braces, `%` or `*`, drive letters, bare file types such as `.csv`, and commands of other programs are skipped. Nothing it
checks is imported, because importing could run code.
"""
import ast
import importlib.util
import pathlib
import re
import sys

ROOT = pathlib.Path(__file__).resolve().parents[1]
SKIPPED_DIRS = ("milestones", "audit", "research", "context", "planning")
EXTENSIONS = (".py", ".md", ".toml", ".json", ".csv", ".txt", ".ps1", ".iss", ".yml", ".yaml", ".spec", ".lock", ".png",
              ".bat", ".sh", ".exe", ".bin", ".db", ".cer", ".in", ".wsb", ".ico", ".ttf")
# Files that don't live in the repository: the app writes them in the data folder, a build makes them, or git ignores them.
RUNTIME = {
    "key.bin": "the install secret, in the data folder",
    "prefs.json": "settings, in the data folder",
    "crosswalk.db": "the saved crosswalk, in the data folder",
    "Wholecount.exe": "the built program",
    "wholecount-signing.cer": "the public certificate make_cert.ps1 exports",
    "Output/wholecount-signing.cer": "the public certificate make_cert.ps1 exports",
    "tools/signing.local.json": "the maintainer's thumbprint, ignored by git",
    "dist/Wholecount/": "the build output",
    "build/screens/": "the output of make screens",
    "perf-report.txt": "the output of tools/perf_report.py",
    "sessions/": "saved progress, in the data folder",
    "setups/": "saved set-ups, in the data folder",
    "calibration/": "matching labels, in the data folder",
    "reference/": "the address reference folder, in the data folder",
    "tools/data/districts/": "where the boundary downloads are saved by hand, empty until then",
    "signtool.exe": "the Windows SDK's signing program",
}
_TICK = re.compile(r"`([^`\n]+)`")
_IMAGE = re.compile(r"!\[[^\]]*\]\(([^)\s]+)\)")
_FENCE = re.compile(r"^(```|~~~)")


def docs():
    found = [ROOT / "README.md"] if (ROOT / "README.md").exists() else []
    return found + sorted(p for p in (ROOT / "docs").glob("*.md") if p.parent.name not in SKIPPED_DIRS)


def references(text):
    """(line number, reference, kind) for every backticked span and image link outside fenced blocks."""
    out, fenced = [], False
    for n, line in enumerate(text.splitlines(), 1):
        if _FENCE.match(line.strip()):
            fenced = not fenced
            continue
        if fenced:
            continue
        out += [(n, m.group(1).strip(), "tick") for m in _TICK.finditer(line)]
        out += [(n, m.group(1).strip(), "image") for m in _IMAGE.finditer(line)]
    return out


def make_targets():
    targets = set()
    for line in (ROOT / "Makefile").read_text(encoding="utf-8").splitlines():
        m = re.match(r"^([A-Za-z][\w .-]*?)\s*:(?!=)", line)
        if m and not line.startswith("\t"):
            targets.update(m.group(1).split())
    return targets


def _module_file(dotted):
    """The source file of a repository module, or None."""
    base = ROOT.joinpath(*dotted.split("."))
    for cand in (base.with_suffix(".py"), base / "__init__.py"):
        if cand.is_file():
            return cand
    return None


def module_exists(dotted):
    if _module_file(dotted) is not None:
        return True
    top = dotted.split(".")[0]
    if (ROOT / top).exists():
        return False
    return dotted == top and importlib.util.find_spec(top) is not None


def _names(tree):
    names = {}
    for node in tree.body:
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
            names[node.name] = node
        elif isinstance(node, (ast.Assign, ast.AnnAssign)):
            for t in node.targets if isinstance(node, ast.Assign) else [node.target]:
                if isinstance(t, ast.Name):
                    names[t.id] = node
        elif isinstance(node, (ast.Import, ast.ImportFrom)):
            for a in node.names:
                names[(a.asname or a.name).split(".")[0]] = node
    return names


def code_name_exists(dotted):
    """A wholecount module, or a name in one, or a method of a class in one. Parsed with ast, never imported."""
    parts = dotted.rstrip("()").split(".")
    for cut in range(len(parts), 0, -1):
        f = _module_file(".".join(parts[:cut]))
        if f is None:
            continue
        rest = parts[cut:]
        if not rest:
            return True
        names = _names(ast.parse(f.read_text(encoding="utf-8")))
        node = names.get(rest[0])
        if node is None:
            return False
        if len(rest) == 1:
            return True
        if isinstance(node, ast.ClassDef) and len(rest) == 2:
            return any(getattr(b, "name", None) == rest[1] or
                       any(isinstance(t, ast.Name) and t.id == rest[1] for t in getattr(b, "targets", []))
                       for b in node.body)
        return False
    return False


def _looks_like_path(ref):
    if ref.startswith(".") and "/" not in ref and "\\" not in ref:
        return False        # a file type such as .csv, not a file
    return "/" in ref or "\\" in ref or ref.lower().endswith(EXTENSIONS)


def _repo_names():
    return {p.name for p in ROOT.rglob("*") if ".git" not in p.parts and ".venv" not in p.parts}


def path_exists(ref, doc):
    """A bare file name may be anywhere in the repository. A name with a folder must be at that place."""
    p = ref.replace("\\", "/")
    p = p[2:] if p.startswith("./") else p
    if p in RUNTIME or pathlib.PurePosixPath(p).name in RUNTIME:
        return True
    if (ROOT / p).exists() or (doc.parent / p).exists():
        return True
    return "/" not in p and p in _repo_names()


def check_reference(ref, kind, doc, targets):
    """None when the reference is fine or skipped, else a short reason."""
    if kind == "image":
        return None if (doc.parent / ref).exists() else "image not found"
    if any(c in ref for c in "<>{}%*") or re.match(r"^[A-Za-z]+:\\", ref) or ref.startswith(("http", "-")):
        return None
    words = ref.split()
    if len(words) > 1:
        if words[0] == "make":
            missing = [w for w in words[1:] if not w.startswith("-") and "=" not in w and w not in targets]
            return f"no make target {missing[0]}" if missing else None
        if words[0] in ("python", "python3", "python3.12", "py") and len(words) > 1:
            if words[1] == "-m" and len(words) > 2:
                return None if module_exists(words[2]) else f"no module {words[2]}"
            if _looks_like_path(words[1]):
                return None if path_exists(words[1], doc) else f"no file {words[1]}"
        return None        # a command of another program
    if ref.startswith("wholecount.") and "/" not in ref and not ref.endswith(EXTENSIONS):
        return None if code_name_exists(ref) else f"no code name {ref}"
    if _looks_like_path(ref):
        return None if path_exists(ref, doc) else f"no file {ref}"
    return None


def check(paths=None):
    """[(doc, line, reference, reason)] for every reference that doesn't resolve."""
    targets = make_targets()
    misses = []
    for doc in (paths or docs()):
        doc = pathlib.Path(doc)
        for n, ref, kind in references(doc.read_text(encoding="utf-8")):
            reason = check_reference(ref, kind, doc, targets)
            if reason:
                misses.append((doc, n, ref, reason))
    return misses


def main(argv=None):
    args = sys.argv[1:] if argv is None else argv
    misses = check([pathlib.Path(a) for a in args] or None)
    for doc, n, ref, reason in misses:
        try:
            shown = doc.relative_to(ROOT)
        except ValueError:
            shown = doc
        print(f"{shown}:{n}: {reason}")
    print(f"{len(misses)} references not found")
    return 1 if misses else 0


if __name__ == "__main__":
    sys.exit(main())
