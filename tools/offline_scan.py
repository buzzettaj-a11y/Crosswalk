"""Static scans of source files and lockfiles. Plain functions that take paths or text and return findings.

The tests in tests/offline/ call these on the real repo, and their negative controls call them on temp files.
A finding is a tuple whose first item is the file's path relative to the scan root, so a failure names the file.
"""
import ast
import pathlib
import re

from tools.offline_rules import (
    FORBIDDEN_DISTS, FORBIDDEN_MODULES, PIP_REQ_RE, STARTFILE_EXEMPT, URL_ALLOW_PREFIXES, URL_RE, normalize_dist,
)

# The research's pattern (R6) for calls that open something outside the app. os.startfile is handled on its own below.
FORBIDDEN_CALL_RE = re.compile(
    r"\b(openUrl|QDesktopServices|setOpenExternalLinks|webbrowser|QProcess|subprocess|os\.system|QNetwork\w*|QWebEngine\w*)\b"
)


def _rel(path, root):
    path = pathlib.Path(path)
    if root is None:
        return path.as_posix()
    try:
        return path.resolve().relative_to(pathlib.Path(root).resolve()).as_posix()
    except ValueError:
        return path.as_posix()


def imported_modules(tree):
    """Every module name an AST imports with an absolute import, including `from x import y` as both x and x.y."""
    for n in ast.walk(tree):
        if isinstance(n, ast.Import):
            for a in n.names:
                yield a.name
        elif isinstance(n, ast.ImportFrom) and n.module and n.level == 0:
            yield n.module
            for a in n.names:
                yield f"{n.module}.{a.name}"


def _is_forbidden(module, forbidden):
    parts = module.split(".")
    return any(".".join(parts[:i]) in forbidden for i in range(1, len(parts) + 1))


def scan_imports(paths, root=None, forbidden=FORBIDDEN_MODULES):
    """Imports of a forbidden module (or any submodule of one)."""
    bad = []
    for p in paths:
        for m in imported_modules(ast.parse(pathlib.Path(p).read_text(encoding="utf-8"))):
            if _is_forbidden(m, forbidden):
                bad.append((_rel(p, root), m))
    return bad


def scan_url_literals(paths, root=None):
    """String constants holding a URL or a UNC path, apart from XML namespace identifiers."""
    bad = []
    for p in paths:
        for n in ast.walk(ast.parse(pathlib.Path(p).read_text(encoding="utf-8"))):
            if isinstance(n, ast.Constant) and isinstance(n.value, str):
                for m in URL_RE.findall(n.value):
                    if not m.lower().startswith(URL_ALLOW_PREFIXES):
                        bad.append((_rel(p, root), m))
    return bad


def _startfile_uses(tree):
    """Uses of os.startfile by AST: an attribute named startfile, `from os import startfile`, or getattr(x, "startfile")."""
    for n in ast.walk(tree):
        if isinstance(n, ast.Attribute) and n.attr == "startfile":
            yield "os.startfile"
        elif isinstance(n, ast.ImportFrom) and n.module in ("os", "nt") and any(a.name == "startfile" for a in n.names):
            yield f"from {n.module} import startfile"
        elif (isinstance(n, ast.Call) and isinstance(n.func, ast.Name) and n.func.id == "getattr" and len(n.args) >= 2
              and isinstance(n.args[1], ast.Constant) and n.args[1].value == "startfile"):
            yield "getattr startfile"


def scan_startfile(paths, root=None):
    """os.startfile anywhere except the one exempt file (SPEC 12.6)."""
    bad = []
    for p in paths:
        rel = _rel(p, root)
        if rel in STARTFILE_EXEMPT:
            continue
        bad += [(rel, u) for u in _startfile_uses(ast.parse(pathlib.Path(p).read_text(encoding="utf-8")))]
    return bad


def scan_forbidden_calls(paths, root=None):
    """Calls that hand something to the OS or a browser. os.startfile is allowed only in STARTFILE_EXEMPT, and every other pattern
    applies to that file too."""
    bad = []
    for p in paths:
        text = pathlib.Path(p).read_text(encoding="utf-8")
        bad += [(_rel(p, root), m.group(0)) for m in FORBIDDEN_CALL_RE.finditer(text)]
    return bad + scan_startfile(paths, root)


def scan_module_use(paths, names, root=None):
    """Imports of the named modules, and calls through a bare name such as pip.main(...). Strings and comments don't count."""
    names = frozenset(names)
    bad = []
    for p in paths:
        tree = ast.parse(pathlib.Path(p).read_text(encoding="utf-8"))
        for m in imported_modules(tree):
            if m.split(".")[0] in names:
                bad.append((_rel(p, root), m))
        for n in ast.walk(tree):
            if isinstance(n, ast.Call) and isinstance(n.func, ast.Attribute):
                base = n.func
                while isinstance(base, ast.Attribute):
                    base = base.value
                if isinstance(base, ast.Name) and base.id in names:
                    bad.append((_rel(p, root), f"{base.id} call"))
    return bad


def scan_layering(paths, root, rules):
    """Imports that cross a layer. rules maps a source package prefix to the module prefixes it must not import."""
    bad = []
    for p in paths:
        rel = _rel(p, root)
        dotted = rel[:-3].replace("/", ".") if rel.endswith(".py") else rel.replace("/", ".")
        banned = [b for src, bs in rules.items() if dotted == src or dotted.startswith(src + ".") for b in bs]
        if not banned:
            continue
        for m in imported_modules(ast.parse(pathlib.Path(p).read_text(encoding="utf-8"))):
            if any(m == b or m.startswith(b + ".") for b in banned):
                bad.append((rel, m))
    return bad


# Lockfiles

def lock_pins(text):
    """{normalized name: version} for every name==version line."""
    return {normalize_dist(n): v for n, v in PIP_REQ_RE.findall(text)}


def check_lock_clean(text):
    """Problems with a hashed lock: an empty lock, a pin with no hash, VCS, URL or editable lines, or a forbidden distribution."""
    problems = []
    pins = PIP_REQ_RE.findall(text)
    if not pins:
        return ["empty lockfile"]
    for block in re.split(r"\n(?=[A-Za-z0-9][A-Za-z0-9._-]*==)", text):
        m = PIP_REQ_RE.match(block)
        if m and "--hash=sha256:" not in block:
            problems.append(f"no hash: {m.group(1)}")
    for line in text.splitlines():
        s = line.strip()
        if re.match(r"^(-e\b|--editable\b|git\+|hg\+|svn\+|bzr\+|https?://|file:)", s) or re.search(r"\s@\s", s):
            problems.append(f"not a pinned index requirement: {s[:60]}")
        if re.match(r"^[A-Za-z0-9][A-Za-z0-9._-]*\s*(>=|<=|~=|>|<|!=)", s):
            problems.append(f"range requirement: {s[:60]}")
    problems += [f"forbidden distribution: {n}" for n in sorted(lock_pins(text)) if n in FORBIDDEN_DISTS]
    return problems


def check_lock_approved(text, approved):
    """(unexpected, missing) between the lock's pins and an approved set."""
    pinned = set(lock_pins(text))
    return sorted(pinned - set(approved)), sorted(set(approved) - pinned)


def in_file_names(text):
    """Distribution names a requirements .in file asks for, skipping comments and -c/-r lines."""
    names = []
    for line in text.splitlines():
        s = line.split("#", 1)[0].strip()
        if not s or s.startswith("-"):
            continue
        m = re.match(r"^([A-Za-z0-9][A-Za-z0-9._-]*)", s)
        if m:
            names.append(normalize_dist(m.group(1)))
    return names
