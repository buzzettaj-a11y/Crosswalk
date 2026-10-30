"""
Saved set-ups: the work of configuring a run, kept so it need not be redone.

A set-up records what shaped a run and nothing else: the files by name and
the columns each had, the header rows, the column set-up, the tidy-up steps,
how columns were matched, the defaults per file, how program names were
grouped, what counted as a duplicate, and the settings. No client data is
written, ever. A set-up is loaded against whatever files are present now:
each part is checked against the current build and the current files, and
anything that no longer fits is reported by name rather than applied blindly
or silently dropped. The tool changes over time; a set-up that quietly stopped
working would be worse than none.
"""
from __future__ import annotations

import json
import os
import re
import time

FOLDER = os.path.join(os.path.dirname(os.path.abspath(__file__)), "setups")
FORMAT = 1                     # bumped when the shape of a set-up changes

SAVED = ["schema", "ops", "map_ov", "source_defaults", "header_row", "included",
         "settings", "gde_fields", "cols_off", "fmt", "mode", "dup_fields",
         "program_groups", "program_aliases"]


def stem(key):
    """A table key without its row range, so the same file loaded with more
    or fewer rows is still the same file: 'a.xlsx :: Sheet1 :: A1:I58' and
    'a.xlsx :: Sheet1 :: A1:I70' both give 'a.xlsx :: Sheet1'."""
    parts = str(key).split(" :: ")
    if len(parts) > 1 and re.fullmatch(r"[A-Z]+\d+:[A-Z]+\d+", parts[-1]):
        parts = parts[:-1]
    return " :: ".join(parts)


def _present_by_stem(S):
    """The tables loaded now, by their key without the row range."""
    return {stem(k): k for k in S["frames"]}


def _safe_name(name):
    """A set-up name reduced to characters safe in a file name."""
    name = re.sub(r"[^\w\- ]+", "", str(name or "")).strip()
    return name[:60] or "set-up"


def _path(name):
    """Where a set-up's file lives."""
    return os.path.join(FOLDER, _safe_name(name) + ".json")


def list_setups():
    """The saved set-ups, with any that cannot be read marked as broken rather than hidden."""
    if not os.path.isdir(FOLDER):
        return []
    out = []
    for fn in sorted(os.listdir(FOLDER)):
        if not fn.endswith(".json"):
            continue
        try:
            with open(os.path.join(FOLDER, fn), encoding="utf-8") as fh:
                d = json.load(fh)
            out.append({"name": d.get("name", fn[:-5]), "saved_at": d.get("saved_at", ""),
                        "version": d.get("app_version", ""),
                        "files": [f["name"] for f in d.get("files", [])],
                        "note": d.get("note", "")})
        except Exception as exc:
            out.append({"name": fn[:-5], "saved_at": "", "version": "",
                        "files": [], "note": "", "broken": f"cannot be read: {exc}"})
    return out


def save_setup(S, name, note, app_version, frames_columns):
    """Write the current set-up under a name. frames_columns: {table key: [columns]}."""
    os.makedirs(FOLDER, exist_ok=True)
    d = {"format": FORMAT, "app_version": app_version, "name": _safe_name(name),
         "note": str(note or "")[:400], "saved_at": time.strftime("%Y-%m-%d %H:%M:%S"),
         "files": [{"name": k, "columns": cols} for k, cols in frames_columns.items()],
         "state": {k: S.get(k) for k in SAVED}}
    with open(_path(name), "w", encoding="utf-8") as fh:
        json.dump(d, fh, indent=1, default=str)
    return d["name"]


def delete_setup(name):
    """Remove one saved set-up."""
    try:
        os.remove(_path(name))
        return True
    except OSError:
        return False


def read_setup(name):
    """Read one saved set-up from disk."""
    with open(_path(name), encoding="utf-8") as fh:
        return json.load(fh)


def _columns_added_by_steps(st, table):
    """The columns the saved tidy-up steps on a table create, so a matching
    that points at one of them is not mistaken for a missing column."""
    out = set()
    for o in st.get("ops") or []:
        if stem(o.get("table")) != stem(table):
            continue
        op = o.get("op", {})
        c = op.get("column")
        if op.get("type") == "split_jammed" and c:
            out |= {f"{c}_street", f"{c}_address2", f"{c}_city", f"{c}_state", f"{c}_zip"}
        elif op.get("type") == "split_name" and c:
            out |= {f"{c}_first", f"{c}_middle", f"{c}_last"}
        elif op.get("type") == "split_delim" and c:
            names = op.get("names") or []
            out |= set(names) | {f"{c}_{i}" for i in range(1, 12)}
        elif op.get("type") == "calc_zip":
            n = op.get("name") or "Zip_calculated"
            out |= {n, f"{n}_note"}
    return out


def check_setup(d, S, app_version, known_op_types, known_roles, describe_op,
                default_schema=None):
    """
    Check every part of a saved set-up against the current build and the files
    loaded now. Returns a report: what will apply, what will not, and why.
    Nothing is changed here.
    """
    problems, notes, applies = [], [], []
    if d.get("format") != FORMAT:
        problems.append(f"this set-up was saved in format {d.get('format')}, and the "
                        f"tool now uses format {FORMAT}; parts of it may not fit")
    if d.get("app_version") and d["app_version"] != app_version:
        notes.append(f"saved with version {d['app_version']}, checked against {app_version}")

    st = d.get("state") or {}
    by_stem = _present_by_stem(S)
    present = {stem(k): list(S["frames"][k].columns) for k in S["frames"]}
    saved_files = {stem(f["name"]): f.get("columns", []) for f in d.get("files", [])}

    # files: which of the saved ones are here, and do they still look the same
    for name, cols in saved_files.items():
        if name in present:
            missing = [c for c in cols if c not in present[name]]
            if missing:
                problems.append(f"{name.split(' :: ')[0]} is loaded but no longer has "
                                f"column(s) {', '.join(missing[:6])}; matching and "
                                "steps that use them will not apply")
            else:
                applies.append(f"{name.split(' :: ')[0]}: loaded, same columns")
        else:
            problems.append(f"{name.split(' :: ')[0]} is not loaded now; its header row, "
                            "steps, matching and defaults will be skipped")
    for name in present:
        if name not in saved_files:
            notes.append(f"{name.split(' :: ')[0]} is loaded now but was not part of "
                         "this set-up; it keeps the tool's own proposal")

    # schema
    schema = st.get("schema")
    if schema:
        bad = [f for f in schema if not isinstance(f, dict) or "role" not in f
               or (f["role"] != "custom" and f["role"] not in known_roles)]
        if bad:
            problems.append(f"the column set-up names {len(bad)} field(s) this version "
                            "does not know; it will not apply")
        else:
            applies.append(f"column set-up with {len(schema)} field(s)")

    # steps
    for o in st.get("ops") or []:
        op = o.get("op", {})
        who = o.get("table", "").split(" :: ")[0]
        if op.get("type") not in known_op_types:
            problems.append(f"a tidy-up step on {who} is of a kind this version does not "
                            f"have ({op.get('type')}); it will be left out")
            continue
        if stem(o.get("table")) not in present:
            continue
        cols = present[stem(o["table"])]
        used = [c for c in ([op.get("column")] + (op.get("columns") or [])
                            + [op.get("street_col"), op.get("city_col"), op.get("zip_col")])
                if c]
        gone = [c for c in used if c not in cols]
        if gone:
            problems.append(f"a tidy-up step on {who} uses column(s) {', '.join(gone)} "
                            "that the file no longer has; it will be left out")
        else:
            try:
                applies.append(f"{who}: {describe_op(op)}")
            except Exception:
                applies.append(f"{who}: a tidy-up step")

    # matching, checked against the columns that will apply: the saved ones,
    # or the standard set when none were saved
    effective_schema = schema or default_schema or []
    labels = {f.get("label") for f in effective_schema} | set(known_roles)
    # the columns a table will have once the saved steps have run
    for table, fields in (st.get("map_ov") or {}).items():
        if stem(table) not in present:
            continue
        will_have = set(present[stem(table)]) | _columns_added_by_steps(st, table)
        for role, col in (fields or {}).items():
            if role not in labels:
                problems.append(f"matching on {table.split(' :: ')[0]} refers to a field "
                                f"'{role}' that the column set-up does not have")
            elif col and col not in will_have:
                problems.append(f"matching on {table.split(' :: ')[0]} points {role} at "
                                f"column '{col}', which the file no longer has")

    if st.get("program_groups"):
        applies.append(f"program names grouped into {len(st['program_groups'])} program(s)")
    if st.get("dup_fields"):
        applies.append("what counts as a duplicate: " + ", ".join(st["dup_fields"]))
    return {"ok": not problems, "problems": problems, "notes": notes, "applies": applies,
            "saved_at": d.get("saved_at"), "version": d.get("app_version"),
            "name": d.get("name")}


def apply_setup(d, S, known_op_types, present_tables):
    """
    Apply what fits. Parts the check flagged are skipped, so what is loaded is
    exactly what the report said would load. Saved table keys are translated
    to the keys of the tables present now, by file name. Returns what was
    applied.
    """
    st = d.get("state") or {}
    by_stem = {stem(k): k for k in present_tables}

    def now(saved_key):
        """The key of the table present now that a saved key refers to, by file name."""
        return by_stem.get(stem(saved_key))

    applied = []
    if st.get("schema"):
        S["schema"] = st["schema"]
        applied.append("column set-up")
    for k in ("settings", "gde_fields", "cols_off", "fmt", "mode", "dup_fields"):
        if st.get(k) is not None:
            S[k] = st[k]

    ops = []
    for o in st.get("ops") or []:
        key = now(o.get("table"))
        op = o.get("op", {})
        if not key or op.get("type") not in known_op_types:
            continue
        cols = list(S["frames"][key].columns)
        used = [c for c in ([op.get("column")] + (op.get("columns") or [])
                            + [op.get("street_col"), op.get("city_col"), op.get("zip_col")]) if c]
        if all(c in cols for c in used):
            o2 = dict(o)
            o2["table"] = key
            ops.append(o2)
    S["ops"] = ops
    if ops:
        applied.append(f"{len(ops)} tidy-up step(s)")

    S["map_ov"] = {now(k): v for k, v in (st.get("map_ov") or {}).items() if now(k)}
    if S["map_ov"]:
        applied.append(f"matching for {len(S['map_ov'])} table(s)")
    S["source_defaults"] = {now(k): v for k, v in (st.get("source_defaults") or {}).items()
                            if now(k)}
    for k, v in (st.get("header_row") or {}).items():
        if now(k):
            S["header_row"][now(k)] = v
    for k, v in (st.get("included") or {}).items():
        if now(k):
            S["included"][now(k)] = v
    if st.get("program_groups"):
        S["program_groups"] = st["program_groups"]
        S["program_aliases"] = st.get("program_aliases") or {}
        S["_keep_program_groups"] = True
        applied.append("program grouping")
    S["dup_decisions"] = {}
    S["results"] = None
    S["identity"] = None
    return applied
