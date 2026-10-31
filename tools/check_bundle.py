"""The pure-Python check behind make bundle and the bundle tests (M14 section 2). Reads PyInstaller's PYZ-00.toc and
COLLECT-00.toc and the warn file, walks the built folder, and prints counts only.

    python tools/check_bundle.py DIST BUILD        DIST is dist/Wholecount, BUILD is build/wholecount
"""
import ast
import pathlib
import re
import sys

ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from tools.offline_rules import (FORBIDDEN_FILE_NAME_PARTS, FORBIDDEN_MODULES, MODEL_BIN_MAX_BYTES,  # noqa: E402
                                 MODEL_FILE_SUFFIXES, WINDOWS_ONLY_FORBIDDEN_FILE_NAME_PARTS)

UNWANTED_DIRS = ("tests", "docs", "legacy", ".git")
LAUNCHERS = (".bat", ".cmd", ".sh", ".command", ".vbs")


def read_toc(path):
    """The entries of a TOC file, as (name, source, typecode) tuples. PyInstaller writes them as a Python literal."""
    data = ast.literal_eval(pathlib.Path(path).read_text(encoding="utf-8"))
    if isinstance(data, tuple) and len(data) == 2 and isinstance(data[1], list):
        data = data[1]
    if isinstance(data, tuple):
        data = data[0]
    return [tuple(e) for e in data]


def pyz_modules(build):
    return {e[0] for e in read_toc(pathlib.Path(build) / "PYZ-00.toc")}


def collect_names(build):
    return [e[0].replace("\\", "/") for e in read_toc(pathlib.Path(build) / "COLLECT-00.toc")]


def forbidden_modules(names):
    """Forbidden modules among importable names (PYZ modules and extension module names)."""
    out = set()
    for n in names:
        for f in FORBIDDEN_MODULES:
            if n == f or n.startswith(f + "."):
                out.add(n)
    return sorted(out)


def extension_modules(collect):
    """Dotted names of the compiled Python extension modules in the COLLECT table (cpython .so files and .pyd files)."""
    out = []
    for n in collect:
        m = re.match(r"(.+?)\.(cpython-[^/]*\.so|cp\d+-[^/]*\.pyd|pyd)$", n)
        if m:
            out.append(m.group(1).removeprefix("lib-dynload/").replace("/", "."))
    return out


def files(dist):
    dist = pathlib.Path(dist)
    return sorted(p.relative_to(dist).as_posix() for p in dist.rglob("*") if p.is_file())


def forbidden_files(paths, windows=None):
    parts = FORBIDDEN_FILE_NAME_PARTS
    if windows if windows is not None else any(p.lower().endswith(".dll") for p in paths):
        parts = parts + WINDOWS_ONLY_FORBIDDEN_FILE_NAME_PARTS
    return sorted(p for p in paths if any(x in "/" + p for x in parts))


def model_files(dist):
    dist = pathlib.Path(dist)
    out = []
    for p in dist.rglob("*"):
        if p.is_file():
            low = p.name.lower()
            if low.endswith(MODEL_FILE_SUFFIXES) or (low.endswith(".bin") and p.stat().st_size > MODEL_BIN_MAX_BYTES):
                out.append(p.relative_to(dist).as_posix())
    return sorted(out)


def unwanted(paths):
    out = []
    for p in paths:
        parts = p.split("/")
        if any(d in parts for d in UNWANTED_DIRS) or p.lower().endswith(LAUNCHERS):
            out.append(p)
        elif p.endswith(".md") and "/licenses/" not in "/" + p:
            out.append(p)
        elif p.endswith(("wholecount/dev.py", "wholecount/app_imports.py")):
            out.append(p)
    return sorted(out)


def warn_inclusions(build):
    """Lines in warn-wholecount.txt that name a forbidden module as missing rather than excluded: a forbidden module that
    something needs and PyInstaller couldn't find would show as missing, which is fine; one it found would not be listed."""
    text = (pathlib.Path(build) / "warn-wholecount.txt").read_text(encoding="utf-8")
    out = []
    for line in text.splitlines():
        m = re.match(r"(missing|excluded) module named '?([^' ]+)'?", line)
        if m:
            out.append((m.group(1), m.group(2)))
    return out


def report(dist, build):
    paths = files(dist)
    pyz = pyz_modules(build)
    collect = collect_names(build)
    return {
        "files": len(paths),
        "pyz_modules": len(pyz),
        "forbidden_modules": len(forbidden_modules(pyz | set(extension_modules(collect)))),
        "forbidden_files": len(forbidden_files(paths)),
        "model_files": len(model_files(dist)),
        "unwanted_files": len(unwanted(paths)),
        "excluded_in_warn": sum(1 for kind, _ in warn_inclusions(build) if kind == "excluded"),
    }


def main(argv=None):
    argv = sys.argv[1:] if argv is None else argv
    dist, build = (argv + ["dist/Wholecount", "build/wholecount"])[:2]
    r = report(dist, build)
    for k, v in r.items():
        print(f"{k} {v}")
    bad = r["forbidden_modules"] + r["forbidden_files"] + r["model_files"] + r["unwanted_files"]
    return 1 if bad else 0


if __name__ == "__main__":
    raise SystemExit(main())
