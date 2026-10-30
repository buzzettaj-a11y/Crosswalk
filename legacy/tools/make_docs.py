"""
Build the documentation from the code, so it cannot drift from it.

    python tools/make_docs.py            writes docs/TECHNICAL.md, docs/USER_GUIDE.md,
                                         docs/cheatsheets/*.md
    python tools/make_docs.py --check    exits non-zero if any of those is stale

The technical reference is read straight from the source: every module, every
class and function with its signature and docstring, every API route, every
key of the working state. The narrative parts (purpose, hard rules, data
flow) are written here as text and belong to this file. The user guide and
the cheat sheets are built from ui/help.json, the same text the help buttons
in the app show, plus the screenshots in docs/screenshots/.

tests/test_docs.py runs --check, so a change to the code without a rebuild of
the documentation fails the suite.
"""
from __future__ import annotations

import ast
import inspect
import json
import os
import re
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DOCS = os.path.join(ROOT, "docs")
sys.path.insert(0, ROOT)

MODULES = [
    ("crosswalk_server.py", "The web server: every API route, the working state, and the wiring between the engine and the interface."),
    ("app.py", "The engine: reading files, cleaning, splitting, checking, geocoding, de-duplicating, and the exports. Also the original Streamlit interface."),
    ("identity.py", "Who is who across systems: the matching that produces the master ID and the two counts."),
    ("table_detect.py", "Finding the separate tables on one sheet, the header row, and what kind of table each is."),
    ("column_check.py", "Whether a matched column really holds what the field expects, and which column would."),
    ("fill_missing.py", "Proposing a missing ZIP, city or state from what a row already has, through Geosupport or the reference data."),
    ("dedupe_rules.py", "Duplicates within one file: proposed on the reviewer's fields, decided by a person, applied as marks the engine honors."),
    ("program_names.py", "Grouping the same program spelled differently, with the reason for each grouping."),
    ("review_context.py", "What a reviewer needs to decide one row: the problems in plain words, related records, suggestions."),
    ("wording.py", "The same meaning in two registers, Guided and Advanced, and the plain wording of problems and results."),
    ("audit_trail.py", "The complete audit trail: the set-up, the engine's changes by row, and every decision, with no client data."),
    ("setups.py", "Named run set-ups, saved without client data and checked part by part against the current build before loading."),
    ("sessions_store.py", "Saving progress between sessions: decisions and set-up only, purged after seven days."),
    ("launch.py", "The double-click launcher: checks, installs once, picks a port, starts the server, opens the browser, stops when the window is gone."),
]

STATE_KEYS = {
    "uploads": "the uploaded files as bytes, by file name (for Open the source file)",
    "tables": "every table found, with its kind, range and summary",
    "frames": "the raw table for each table key, as strings",
    "blocks": "the raw grid for tables whose header row can be re-chosen",
    "header_row": "which row holds the column names, per table",
    "included": "whether each table takes part",
    "schema": "the column set-up, or None for the standard set",
    "ops": "tidy-up steps, each with its table, origin (auto or manual) and removed flag",
    "map_ov": "matching choices a person made, per table, over the tool's proposal",
    "confirmed": "tables whose matching a person confirmed",
    "source_defaults": "values used where a field is blank, per table",
    "settings": "processing settings: require_geocode, jitter, seed",
    "gde_fields": "optional Geosupport fields to include in the output",
    "results": "the last processing run: transformed, clean, review, audit, quality",
    "rid_index": "record id to record, for the review stage",
    "actions": "every decision a person took, replayed to give each row its status",
    "queue_edits": "corrections applied in review, by record id and field",
    "mode": "Guided or Advanced",
    "stage": "the stage on screen",
    "max_stage": "the furthest stage reached",
    "undo": "snapshots of the set-up before each change",
    "identity": "the cached identity resolution, or None when stale",
    "id_decisions": "confirmed or rejected links between records",
    "dup_fields": "which fields make two rows one person within a file",
    "dup_decisions": "per table, per group: copies, copies:N, or keep",
    "program_groups": "the grouping of program names, and program_aliases the map it produces",
    "program_preview": "the last preview of the two counts, and whether it is stale",
    "run": "processing status: state, phase, message, progress, file, steps left",
}


def _sig(node):
    """A readable signature for a function node."""
    args = []
    a = node.args
    pos = a.posonlyargs + a.args
    defaults = [None] * (len(pos) - len(a.defaults)) + list(a.defaults)
    for arg, d in zip(pos, defaults):
        s = arg.arg
        if d is not None:
            s += "=" + ast.unparse(d)
        args.append(s)
    if a.vararg:
        args.append("*" + a.vararg.arg)
    for arg, d in zip(a.kwonlyargs, a.kw_defaults):
        s = arg.arg + ("=" + ast.unparse(d) if d is not None else "")
        args.append(s)
    if a.kwarg:
        args.append("**" + a.kwarg.arg)
    return f"{node.name}({', '.join(args)})"


def _first_line(doc):
    return (doc or "").strip().split("\n")[0].strip()


def module_reference(fname):
    """Every class and function in a module, with signature and docstring."""
    src = open(os.path.join(ROOT, fname), encoding="utf-8").read()
    tree = ast.parse(src)
    out = []
    mod_doc = ast.get_docstring(tree)
    if mod_doc:
        out.append(mod_doc.strip())
        out.append("")
    routes = []
    for node in tree.body:
        if isinstance(node, ast.ClassDef):
            out.append(f"#### class `{node.name}`")
            out.append(ast.get_docstring(node) or "_No docstring._")
            for sub in node.body:
                if isinstance(sub, (ast.FunctionDef, ast.AsyncFunctionDef)):
                    d = _first_line(ast.get_docstring(sub))
                    if not d and sub.name == "__init__":
                        d = "Creates one, with the values given."
                    out.append(f"- `{_sig(sub)}`: {d or '_No docstring._'}")
            out.append("")
        elif isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            route = ""
            for dec in node.decorator_list:
                if isinstance(dec, ast.Call) and isinstance(dec.func, ast.Attribute) \
                        and dec.func.attr in ("get", "post", "put", "delete") and dec.args:
                    route = f"`{dec.func.attr.upper()} {ast.literal_eval(dec.args[0])}` → "
            doc = ast.get_docstring(node) or "_No docstring._"
            out.append(f"#### {route}`{_sig(node)}`")
            out.append(doc.strip())
            out.append("")
            if route:
                routes.append((route.strip("` →"), node.name, _first_line(doc)))
    return "\n".join(out), routes


def technical():
    """docs/TECHNICAL.md, in full."""
    parts = []
    parts.append("# Crosswalk: technical documentation\n")
    parts.append("_Generated by `tools/make_docs.py` from the source. Do not edit by hand; "
                 "change the code or the generator and rebuild. `tests/test_docs.py` fails when this file is stale._\n")
    parts.append("""## 1. Purpose

Crosswalk exists to answer two questions for a New York City human-services
nonprofit whose clients are recorded in many separate systems (ETO, property
management, DYCD exports, partner spreadsheets), each with its own identifiers,
column names and spellings:

1. **Unique clients across every system**: each person counted once, however
   many files they appear in.
2. **Unique clients per program**: the same person counted once in each
   program they take part in.

To get there, every file is turned into one shape, cleaned, checked, placed on
the map through the city's own address engine, de-duplicated within files, and
resolved across files into one master identity per person. Every change is
recorded by identifier, never by value, so the result can be trusted and
traced without exposing client data.

## 2. Hard rules

These are design constraints, not preferences. Code that violates one is a bug.

- **Offline.** No network calls in the processing path. Geosupport runs locally.
- **Deterministic.** The same input and settings give the same output. No model, no black box. Every rule is written down in this file's reference.
- **Lossless.** clean + review + set aside = input, on every run. Rows are set aside, never deleted.
- **Nothing merged on a guess.** The engine collapses records only where the same identifier appears with identical data. Everything else is proposed to a person, with evidence.
- **Originals preserved.** A tidy-up step adds columns; it never overwrites. The value as entered stays on the row and in the audit.
- **PII-safe audit.** The audit trail and the summary page carry identifiers and column names only.
- **No per-value editing in the app.** The record panel offers only the changes that are safe at scale: fills derived from the row's own address, keeping one of a group of copies, splits. Anything else is fixed at the source and reloaded.
- **Plain words.** Guided mode uses no jargon. Advanced mode uses the precise terms. Only the words differ.

## 3. Architecture

```
Crosswalk.vbs / .command / .sh     double-click launchers, no terminal
        └── launch.py                checks, installs once, picks a port, starts the server, opens the browser
                └── crosswalk_server.py   FastAPI, 127.0.0.1 only; holds the working state S; every API route
                        ├── ui/index.html, ui/app.js, ui/styles.css   single-page interface, no framework
                        ├── ui/help.json                  every help text; also the source of the user guide
                        ├── app.py                        the engine (also the Streamlit front end, run.bat)
                        ├── identity.py                   who is who across systems
                        ├── table_detect.py               tables within a sheet, header rows, table kinds
                        ├── column_check.py               does a matched column hold what the field expects
                        ├── fill_missing.py               ZIP / city / state from the row's own address
                        ├── dedupe_rules.py               duplicates within a file, by the reviewer's fields
                        ├── program_names.py              grouping program spellings
                        ├── review_context.py             what a reviewer needs to decide one row
                        ├── wording.py                    Guided vs Advanced words
                        ├── audit_trail.py                the complete trail
                        ├── setups.py                     saved run set-ups
                        └── sessions_store.py             progress between sessions
```

The server is a single process. All state lives in one dictionary, `S`, in
`crosswalk_server.py`; section 5 lists its keys. The interface fetches one
JSON payload per screen (`GET /api/ui?screen=...`) and renders it; every
change is a POST that mutates `S` and, where needed, reprocesses. Reprocessing
runs in a worker thread so the server keeps answering, and reports progress
per file into `S["run"]`, which the page polls to draw the processing card.

## 4. Data flow, stage by stage

| Stage | What happens | Where |
|---|---|---|
| 00 Check | Environment diagnostics: Python, packages, Geosupport, reference files | `app.preflight_checks`, `GET /api/ui?screen=check` |
| 01 Sources | Files are read as strings; tables found per sheet; header row detected and checkable; tidy-up steps proposed | `table_detect.detect_tables`, `table_detect.header_looks_wrong`, `app.auto_prep_ops`, `POST /api/sources/upload` |
| 02 Schema | The column set-up; the standard set plus custom typed fields | `app.DEFAULT_SCHEMA`, `POST /api/schema` |
| 03 Tidy up | Steps that add columns: clean, split by delimiter, split jammed address or name, calculated ZIP | `app.apply_prep_ops`, `app.op_calc_zip`, `POST /api/prepare/add` |
| 04 Map | Each table's columns matched to the schema; every matched column checked against its values; per-source defaults | `app.guess_mapping`, `column_check.check_mapping`, `POST /api/map`, `POST /api/sources/default` |
| 05 Programs | Which column carries the program per file; grouping of spellings; preview of the two counts | `program_names.suggest_groups`, `_programs_payload`, `POST /api/programs/apply`, `POST /api/programs/preview` |
| 06 Process | `run_pipeline`: transform each row, check, duplicate tiers, geocode, districts; progress per file | `app.run_pipeline`, `_execute_pipeline`, `POST /api/run/start` |
| 07 Fix problems | Rows that failed a check, grouped by cause; diagnosis when the cause is the matching; fills; duplicates within a file; decisions batched and applied once | `_review_rows`, `_classify`, `_group_diagnosis`, `fill_missing`, `dedupe_rules`, `POST /api/review/decide-many`, `POST /api/prepare/dupes/decide` |
| 08 Results | Identity resolution over the clean rows; Goal 1 and Goal 2; open proposals | `identity.resolve`, `_resolve_identity`, `_program_matrix`, `POST /api/identity/decide` |
| 09 Download | The output files, written on demand | `GET /api/export/file?which=...` |

### The row's journey through `app.transform_row`

1. Read each mapped column, cleaned (`clean_cell`: placeholders such as NULL emptied, spacing and hidden characters removed).
2. A summary row (a total, a heading, bare numbers) is flagged as exactly that and returned; it joins no other group.
3. Defaults fill blanks: a value set for this source first, then the schema's. Program is a custom field and takes both.
4. Names: a jammed name is split earlier by a tidy-up step; here the middle initial is reduced to one letter; digits in a name are flagged.
5. Address: a unit found at the end of the street is moved to Address 2; a unit in both lines is de-duplicated, or flagged when they disagree.
6. ZIP is reduced to five digits or flagged. City is filled from the ZIP when blank; a recognized borough that contradicts the ZIP is flagged; an unrecognized city with a valid ZIP is replaced by the ZIP's borough, recorded. State is written as NY or flagged.
7. Custom fields are cleaned, typed and validated.
8. A duplicate rule's marks from `dedupe_rules.apply_decisions` are honored: kept rows are marked, set-aside rows are flagged with the row they copy.
9. Every fix, fill and failed check is written to the audit by identifier.

Then, over all rows: Tier 1 duplicates (same identifier, identical data: keep the first, set the rest aside), Tier 2 possible duplicates across files (same person key, shown, never merged), geocoding (Geosupport, else the reference data), districts from true coordinates, jitter applied to stored coordinates only.

### Identity resolution (`identity.py`)

Records are blocked into candidate pairs that agree on two independent facts,
scored on name (with nickname groups and each half of a double surname), date
of birth (with swapped-digit tolerance), address and identifier, and joined
automatically only above a threshold that coincidence cannot reasonably
reach. Pairs between the propose and auto thresholds are shown with evidence.
The person's decisions are replayed on every resolution. Goal 1 is the count
of master identities; Goal 2 the count of distinct (master identity, program)
pairs.
""")
    parts.append("## 5. The working state `S`\n")
    parts.append("Every key of the server's state and what it holds. Saved between sessions by `sessions_store` (decisions and set-up only, never `frames`, `uploads` or `results`).\n")
    for k, v in STATE_KEYS.items():
        parts.append(f"- `{k}`: {v}")
    parts.append("")
    parts.append("## 6. API routes\n")
    parts.append("Every route the interface calls, generated from the server. Bodies are JSON; all routes are bound to 127.0.0.1.\n")
    all_routes = []
    refs = {}
    for fname, _desc in MODULES:
        text, routes = module_reference(fname)
        refs[fname] = text
        all_routes += routes
    parts.append("| Route | Handler | What it does |")
    parts.append("|---|---|---|")
    for route, name, doc in all_routes:
        parts.append(f"| `{route}` | `{name}` | {doc} |")
    parts.append("")
    parts.append("## 7. Module reference\n")
    parts.append("Every class and function, with its signature and docstring, read from the source.\n")
    for fname, desc in MODULES:
        parts.append(f"### `{fname}`\n")
        parts.append(f"_{desc}_\n")
        parts.append(refs[fname])
    parts.append("## 8. The interface (`ui/app.js`)\n")
    parts.append("""A single page with no framework. `UI` holds the page's own state (which screen, filters, pending choices). `load(screen)` fetches that screen's payload and calls `render()`, which rebuilds the content from one `vScreen()` function per stage: `vCheck`, `vSources`, `vSchema`, `vPrepare`, `vMap`, `vPrograms`, `vRun`, `vReview`, `vQueue`, `vSummary`, `vProposals`, `vExport`, `vAudit`. One document-level click handler dispatches on `data-act` and `data-*` attributes. Grids keep their scroll position across a redraw. Every request shows a bar; when the server reports processing, the screen grays out behind one card. Help buttons read `ui/help.json`.

Choices that used to cost a round trip each are held locally and applied once: program grouping (`progLocal`, `progApply`), review group decisions (`pendingGroups`), duplicate decisions (`pendingDups`).
""")
    parts.append("## 9. Tests\n")
    tests = sorted(f for f in os.listdir(os.path.join(ROOT, "tests")) if f.startswith("test_") and f.endswith(".py"))
    for tname in tests:
        src = open(os.path.join(ROOT, "tests", tname), encoding="utf-8").read()
        doc = ""
        try:
            doc = ast.get_docstring(ast.parse(src)) or ""
        except Exception:
            pass
        parts.append(f"- `tests/{tname}`: {_first_line(doc) or 'checks in the file'}")
    parts.append("\nAll suites must pass from inside the packaged archive before a build is shipped. `proof/Proof_Workbook.xlsx` is both a human-readable demonstration of every rule and an automated test of it.\n")
    parts.append("## 10. Keeping this current\n")
    parts.append("""Documentation is generated, not written, wherever it describes the code:

- `python tools/make_docs.py` rebuilds this file, the user guide and the cheat sheets.
- `python tools/take_screenshots.py` retakes the screenshots the guide and the deck use.
- `python tools/make_guide_docx.js` and `tools/make_deck.js` rebuild the Word guide and the PowerPoint deck from the same sources.
- `tests/test_docs.py` fails when the generated files no longer match the code, and when any public function or class lacks a docstring, which is what the reference is built from.

So the rule for a change is: change the code, add the docstring, run the generators, run the tests.
""")
    return "\n".join(parts)


def user_guide():
    """docs/USER_GUIDE.md from ui/help.json and the screenshots."""
    help_ = json.load(open(os.path.join(ROOT, "ui", "help.json"), encoding="utf-8"))
    shots = {
        "check": "00_check.png", "sources": "01_sources.png", "schema": "02_schema.png",
        "prepare": "03_prepare.png", "map": "04_map.png", "programs": "05_programs.png",
        "run": "06_run.png", "review": "07_review.png", "queue": "07c_queue.png",
        "summary": "08_summary.png", "export": "09_export.png", "audit": "10_audit.png",
    }
    out = ["# Crosswalk: user guide\n",
           "_Built by `tools/make_docs.py` from `ui/help.json`, the same text the help buttons in the app show, and the screenshots in `docs/screenshots/`. Do not edit by hand._\n",
           """## Before you start

Crosswalk takes the client lists your systems export, cleans them into one
shape, places every address on the map, works out which records are the same
person, and gives you two numbers: how many people you serve in all, and how
many in each program. Nothing leaves your computer and nothing is written to
disk until you download it.

Start it by double-clicking `Crosswalk.vbs` (Windows) or `Crosswalk.command`
(Mac). It opens in your browser. Close it with the Close Crosswalk button at
the foot of the menu; closing the browser works too.

Every stage and every complex element has a small **?** button. Press it for
what that thing is for and how to use it. This guide is the same text, in
order, with pictures.

## The stages
"""]
    order = ["check", "sources", "schema", "prepare", "map", "programs", "run", "review", "queue", "summary", "export", "audit"]
    for i, key in enumerate(order):
        e = help_["stages"][key]
        out.append(f"### {i}. {e['title']}\n")
        out.append(f"**Why this exists.** {e['purpose']}\n")
        out.append(f"**What to do.** {e['how']}\n")
        if key in shots and os.path.exists(os.path.join(DOCS, "screenshots", shots[key])):
            out.append(f"![{e['title']}](screenshots/{shots[key]})\n")
    out.append("## The elements that need a closer look\n")
    for key, e in help_["elements"].items():
        out.append(f"### {e['title']}\n")
        out.append(f"**Why this exists.** {e['purpose']}\n")
        out.append(f"**What to do.** {e['how']}\n")
    out.append("""## Workflows

### A first run, end to end
1. Add your files. Untick anything that is a summary rather than a list of people.
2. On Match your columns, read the warnings; a wrong column is the mistake that matters most.
3. On Programs, group the spellings and preview the counts until the program list looks right.
4. Process.
5. On Fix problems, work the groups: look ZIPs up, decide duplicates, accept or set aside. Apply once.
6. On Results, decide any open pairs. The counts are final when none are open.
7. Download the files, and save the set-up for next time.

### The quick run
Add your files, then press "Process everything and show me what needs fixing". It stops only when something would make the run wrong, and says what.

### Next quarter
Add the new files, load the saved set-up, read what fitted and what did not, then run.

### When a file has no program column
On Match your columns, under Fill a field for this source only, type the program. Every row of that file counts under it.

### When the tool cannot place an address
Look up the ZIPs from the street on the review group. A street in several ZIPs needs a house number; one the engine does not know needs a person.
""")
    return "\n".join(out)


CHEATSHEETS = {
    "01_the_two_counts.md": ("The two counts", ["summary"], ["identity", "program_grouping", "program_preview"]),
    "02_matching_columns.md": ("Matching columns", ["map"], ["column_check", "header_row", "source_defaults"]),
    "03_programs.md": ("Programs", ["programs"], ["program_grouping", "program_preview"]),
    "04_fixing_problems.md": ("Fixing problems", ["review", "queue"], ["group_decisions", "fill_lookup", "dupes"]),
    "05_duplicates.md": ("Duplicates", [], ["dupes", "identity"]),
    "06_set_ups_and_audit.md": ("Set-ups and the audit trail", ["audit"], ["setups", "express", "calc_zip"]),
}


def cheatsheets():
    """docs/cheatsheets/*.md, one page each, from ui/help.json."""
    help_ = json.load(open(os.path.join(ROOT, "ui", "help.json"), encoding="utf-8"))
    files = {}
    for fname, (title, stages, elements) in CHEATSHEETS.items():
        out = [f"# Cheat sheet: {title}\n", "_One page. Built from `ui/help.json` by `tools/make_docs.py`._\n"]
        for s in stages:
            e = help_["stages"][s]
            out.append(f"## {e['title']}\n- **For:** {e['purpose']}\n- **Do:** {e['how']}\n")
        for el in elements:
            e = help_["elements"][el]
            out.append(f"## {e['title']}\n- **For:** {e['purpose']}\n- **Do:** {e['how']}\n")
        files[fname] = "\n".join(out)
    return files


def build():
    os.makedirs(DOCS, exist_ok=True)
    os.makedirs(os.path.join(DOCS, "cheatsheets"), exist_ok=True)
    outputs = {os.path.join(DOCS, "TECHNICAL.md"): technical(),
               os.path.join(DOCS, "USER_GUIDE.md"): user_guide()}
    for fname, text in cheatsheets().items():
        outputs[os.path.join(DOCS, "cheatsheets", fname)] = text
    return outputs


def check():
    """True when every generated file matches what the code would generate now."""
    stale = []
    for path, text in build().items():
        try:
            cur = open(path, encoding="utf-8").read()
        except OSError:
            cur = None
        if cur != text:
            stale.append(os.path.relpath(path, ROOT))
    return stale


if __name__ == "__main__":
    if "--check" in sys.argv:
        s = check()
        if s:
            print("STALE:", ", ".join(s))
            sys.exit(1)
        print("documentation is current")
        sys.exit(0)
    for path, text in build().items():
        with open(path, "w", encoding="utf-8") as fh:
            fh.write(text)
        print("wrote", os.path.relpath(path, ROOT))
