"""
Documentation stays true to the code.

Two things are checked. Every class and function, public or private, has a
docstring, because the technical reference is built from them. And the
generated documents (docs/TECHNICAL.md, docs/USER_GUIDE.md, the cheat
sheets) match what the generator would write from the code right now, so a
change to the code without a rebuild of the documentation fails the suite.
"""
import ast
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
os.chdir(ROOT)
sys.path.insert(0, os.path.join(ROOT, "tools"))
import make_docs

results = []


def check(label, cond):
    results.append((label, bool(cond)))


missing = []
for fname, _desc in make_docs.MODULES:
    tree = ast.parse(open(os.path.join(ROOT, fname), encoding="utf-8").read())
    for node in tree.body:
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)) \
                and not ast.get_docstring(node):
            missing.append(f"{fname}:{node.name}")
        if isinstance(node, ast.ClassDef):
            for sub in node.body:
                if isinstance(sub, (ast.FunctionDef, ast.AsyncFunctionDef)) \
                        and sub.name != "__init__" and not ast.get_docstring(sub):
                    missing.append(f"{fname}:{node.name}.{sub.name}")
check("every function and class has a docstring" + (f" (missing: {missing[:5]})" if missing else ""),
      not missing)

stale = make_docs.check()
check("the generated documentation matches the code"
      + (f" (stale: {stale})" if stale else ""), not stale)

for f in ("docs/TECHNICAL.md", "docs/USER_GUIDE.md", "docs/VIDEO_SCRIPT.md",
          "docs/cheatsheets/01_the_two_counts.md", "ui/help.json"):
    check(f"{f} exists", os.path.exists(os.path.join(ROOT, f)))

import json
help_ = json.load(open(os.path.join(ROOT, "ui", "help.json"), encoding="utf-8"))
check("every stage has help text",
      all(k in help_["stages"] for k in ("check", "sources", "schema", "prepare", "map",
                                         "programs", "run", "review", "queue", "summary",
                                         "export", "audit")))
check("every help entry says what it is for and how to use it",
      all(e.get("purpose") and e.get("how") for group in ("stages", "elements")
          for e in help_[group].values()))
js = open(os.path.join(ROOT, "ui", "app.js"), encoding="utf-8").read()
check("every element with help text has a help button in the interface",
      all(f'helpBtn("element", "{k}")' in js for k in help_["elements"]))
shots = os.path.join(ROOT, "docs", "screenshots")
check("the screenshots the guide uses exist",
      os.path.isdir(shots) and len([f for f in os.listdir(shots) if f.endswith(".png")]) >= 12)

failed = [l for l, ok in results if not ok]
for l in failed:
    print(f"  [FAIL] {l}")
print(f"DOCS TESTS: {'PASS' if not failed else 'FAIL'} ({len(results) - len(failed)}/{len(results)})")
sys.exit(0 if not failed else 1)
