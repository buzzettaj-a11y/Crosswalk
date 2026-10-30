"""
Crosswalk server: the redesigned UI's backend, wrapping the existing validated
engine in app.py. Runs fully offline on localhost for a single operator.

Every number shown in the UI comes from the real pipeline. Review decisions are
kept as a replayable action log; corrections made in review re-enter the same
pipeline (validation, geocoding, districts) rather than bypassing it, and every
row keeps its lineage. Lossless invariant at export: the clean file plus the
review file always equal the input rows, and the server asserts it.
"""
from __future__ import annotations

import io
import json
import os
from datetime import datetime, timezone
import threading
import time
from collections import defaultdict

import pandas as pd
from fastapi import FastAPI, File, UploadFile, Request
from fastapi.responses import HTMLResponse, JSONResponse, Response, FileResponse
from starlette.concurrency import run_in_threadpool
from fastapi.staticfiles import StaticFiles
from starlette.middleware.trustedhost import TrustedHostMiddleware

import app as engine
import table_detect
import sessions_store
import review_context
import column_check
import wording
import identity
import program_names
import dedupe_rules
import fill_missing
import audit_trail
import setups

UI_DIR = __import__("os").path.join(__import__("os").path.dirname(
    __import__("os").path.abspath(__file__)), "ui")

api = FastAPI(title="Crosswalk", docs_url=None, redoc_url=None)

# Set by the launcher so the interface can tell a person where it is running,
# and so closing the tool from inside it actually stops the process.
VERSION = "2026.09.17"
PORT = 8765
SHUTDOWN = False
LAST_SEEN = 0.0
BYE_AT = 0.0        # when the last open window said it was closing

# Only accept requests addressed to this machine. The server already binds to
# 127.0.0.1, so nothing off the machine can connect, but a browser can be talked
# into sending a request here by a hostile page that re-points its own hostname
# at the loopback address (DNS rebinding). Checking the Host header closes that:
# such a request arrives naming the attacker's hostname and is refused.
#
# Deliberately no CORS middleware. Without it a browser will not let another
# origin read responses from this server. Do not add allow_origins=["*"] to make
# something work; it removes that protection.
api.add_middleware(
    TrustedHostMiddleware,
    allowed_hosts=["127.0.0.1", "localhost", "::1", "[::1]"],
)

STAGES = ["Sources", "Schema", "Prepare", "Map", "Programs", "Run", "Review",
          "Summary", "Export"]


class _Up:
    """Adapter so engine readers accept raw uploaded bytes."""

    def __init__(self, name, data):
        self.name = name
        self._data = data

    def getvalue(self):
        """The bytes of the uploaded file, as the engine's reader expects."""
        return self._data


def _blank_state():
    """The working state as it is when nothing has been loaded."""
    return {
        "mode": "Guided",
        "stage": 0,            # 0 = system check screen
        "max_stage": 1,        # highest unlocked stage (1 = Sources)
        # sources
        "uploads": {},         # filename -> bytes
        "tables": [],          # dicts describing every detected table
        "frames": {},          # table key -> raw DataFrame
        "included": {},        # table key -> bool
        "corrections_files": [],   # (name, DataFrame)
        # prepare
        "ops": [],             # {id, table, op, origin, title, desc, removed}
        # map
        "map_ov": {},          # table key -> {role: column or ""}
        "source_defaults": {}, # table key -> {role: value} for this source only
        "header_row": {},      # table key -> 1-based header row, 0 = none
        "blocks": {},          # table key -> raw rows, so the header can change
        "confirmed": {},       # table key -> bool
        # run
        "run": {"state": "idle", "phase": "", "progress": 0, "error": ""},
        "settings": {"require_geocode": False, "jitter": True, "seed": 1337},
        "gde_fields": [],      # optional Geosupport data points to append
        "results": None,
        "rid_index": {},       # rid -> transformed record
        # review
        "actions": [],         # replayable decision log
        "queue_edits": {},     # rid -> {role: value} working copies
        # export
        "fmt": "CSV",
        "cols_off": {},
        # autosave
        "schema": None,        # None means the standard schema
        "session_id": None,
        "autosave": True,
        "resumed_from": None,
        "identity": None,      # who is who across the sources
        "id_decisions": {},    # {"ridA||ridB": "same"|"different"} from review
        "dedupe_rules": [],       # kept for saved sessions from before
        "dup_fields": ["First_Name", "Last_Name", "Zip"],   # what makes two rows one person
        "dup_decisions": {},      # {table: {group id: "copies" | "keep"}}
        "program_groups": None,   # proposed groupings of program names
        "program_preview": None,  # the last preview of the counts
        "program_preview_stale": True,
        "program_aliases": {},    # {name as recorded: agreed name}
        "undo": [],            # snapshots of what a change replaced
    }


S = _blank_state()
_baseline = None  # loaded reference indexes, cached


# ---------------------------------------------------------------------------
# helpers
# ---------------------------------------------------------------------------
UNDOABLE = ["schema", "ops", "map_ov", "confirmed", "source_defaults", "dedupe_rules",
            "dup_fields", "dup_decisions",
            "header_row", "included", "settings", "gde_fields", "cols_off",
            "fmt"]


def _snapshot(label):
    """
    Remember what the state looked like before a change, so it can be taken
    back. People only try things when backing out is safe, and every stage
    before Review had no way back.
    """
    import copy
    S["undo"].append({
        "label": label,
        "state": {k: copy.deepcopy(S.get(k)) for k in UNDOABLE},
    })
    del S["undo"][:-25]          # a couple of dozen steps is plenty


def _undo_last():
    """Restore the snapshot taken before the last change, and say what it was."""
    if not S["undo"]:
        return None
    step = S["undo"].pop()
    for k, v in step["state"].items():
        S[k] = v
    return step["label"]


def _autosave():
    """
    Write the resumable parts of the state. Never writes uploaded rows. Failure
    is not allowed to interrupt the operator's work, so it is reported on the
    screen rather than raised.
    """
    if not S.get("autosave"):
        return None
    if not S.get("session_id"):
        S["session_id"] = sessions_store.new_id()
    try:
        sessions_store.save(S["session_id"], S, source_names=list(S["uploads"]))
        S["save_error"] = ""
        return S["session_id"]
    except Exception as exc:            # pragma: no cover
        S["save_error"] = str(exc)
        return None


def _fmtn(n):
    """A number with thousands separators, for messages."""
    return f"{int(n):,}"


def _load_reference():
    """The geocoding reference: Geosupport if it is set up, else the gazetteer and district files, loaded once."""
    global _baseline
    if _baseline is None:
        gde, _ = engine.load_geosupport()
        idx, _ = engine.load_geocode_index(engine.GEOCODE_FILE)
        dist = engine.load_district_index(engine.DISTRICT_FILE)
        _baseline = {"gde": gde, "idx": idx, "dist": dist}
    return _baseline


def _preflight_summary():
    """The system check, run once and cached, with a one-line verdict."""
    checks = engine.preflight_checks()
    verdict = next((c for c in checks if c["name"] == "Geocoding backend in use"),
                   {"status": "warn", "detail": ""})
    fails = sum(1 for c in checks if c["status"] == "fail")
    warns = sum(1 for c in checks if c["status"] == "warn")
    backend = "Geosupport" if any(
        c["name"] == "Geosupport engine" and c["status"] == "ok" for c in checks
    ) else "gazetteer, sample"
    return checks, verdict, fails, warns, backend


def _included_keys():
    """The keys of the tables that take part in the run, in order."""
    return [t["key"] for t in S["tables"] if S["included"].get(t["key"])]


def _active_ops(table_key=None):
    """The tidy-up steps in force for one table, in order, skipping removed ones."""
    out = []
    for op in S["ops"]:
        if op["removed"]:
            continue
        if table_key is not None and op["table"] != table_key:
            continue
        out.append(op["op"])
    return out


_PREP_CACHE = {}    # table key -> (signature, frame)


def _prep_signature(table_key):
    """What a prepared frame depends on: the raw frame, its header row and the
    active steps. If none of these changed, neither did the frame."""
    frame = S["frames"][table_key]
    return (id(frame), len(frame), S["header_row"].get(table_key),
            json.dumps(_active_ops(table_key), sort_keys=True, default=str))


def _prepared(table_key):
    """
    The table with its tidy-up steps applied, built once and reused until
    something it depends on changes. One screen asks for this many times
    over, and a step such as the calculated ZIP column looks every address up,
    so rebuilding it on each call made every click slow. Callers that change
    the frame must copy it first.
    """
    sig = _prep_signature(table_key)
    hit = _PREP_CACHE.get(table_key)
    if hit and hit[0] == sig:
        return hit[1]
    frame = engine.apply_prep_ops(S["frames"][table_key], _active_ops(table_key))
    _PREP_CACHE[table_key] = (sig, frame)
    return frame


def _forget_prepared(table_key=None):
    """Drop cached prepared frames, for one table or all, so they are rebuilt."""
    if table_key is None:
        _PREP_CACHE.clear()
    else:
        _PREP_CACHE.pop(table_key, None)


def _schema():
    """The column set-up in force: the person's, or the standard set."""
    return S.get("schema") or [dict(f) for f in engine.DEFAULT_SCHEMA]


def _required_roles(schema):
    """The roles a row must have for the schema given."""
    return [f["role"] for f in schema if f.get("required")]


def _guess_for(table_key):
    """The matching for one table: the tool's proposal with the person's choices over it, plus the column list."""
    cols = list(_prepared(table_key).columns)
    base = engine.guess_mapping(cols)
    ov = S["map_ov"].get(table_key, {})
    out = {}
    for f in _schema():
        role = f["role"] if f["role"] != "custom" else f["label"]
        if role in ov:
            out[role] = ov[role]
        else:
            out[role] = base.get(f["role"], "") if f["role"] != "custom" else \
                base.get(f["label"], "") or _match_custom(cols, f["label"])
    return out, cols


def _match_custom(cols, label):
    """Propose a source column for one custom field by its label."""
    key = "".join(ch for ch in label.lower() if ch.isalnum())
    for c in cols:
        ck = "".join(ch for ch in str(c).lower() if ch.isalnum())
        if key and (key in ck or ck in key):
            return c
    return ""


def _table_ready(table_key):
    """
    Whether every required field has a column. City and State are filled from
    the ZIP, so a file with no column for them is ready as long as it has a
    ZIP; the matching stage says exactly that, and this must agree with it.
    """
    mapping, _ = _guess_for(table_key)
    missing = [r for r in _required_roles(_schema()) if not mapping.get(r)]
    if mapping.get("Zip"):
        missing = [r for r in missing if r not in ("City", "State")]
    return not missing, missing


def _samples(df, col, n=3):
    """A few distinct values from one column, shortened, for showing under a dropdown."""
    if not col or col not in df.columns:
        return ""
    vals, seen = [], set()
    for v in df[col].astype(str):
        v = v.strip()
        if v and v.lower() not in ("nan", "none") and v not in seen:
            seen.add(v)
            vals.append(v if len(v) <= 18 else v[:17] + "…")
        if len(vals) >= n:
            break
    return " · ".join(vals)


def _rid(rec):
    """The stable identifier of a record: its table key and row number."""
    return f"{rec['__source_file__']}||{rec['__source_row__']}"


# ---------------------------------------------------------------------------
# review model: derive statuses by replaying the action log
# ---------------------------------------------------------------------------
GROUP_DEFS = {
    "summary": {
        "title": "Not client records: totals, counts and headings",
        "desc": "Rows that are a total, a subtotal or a heading rather than a "
                "person. They are not counted in any other group. Setting them "
                "aside keeps them out of the data; they stay listed so you can "
                "check none was a real record.",
        "conf": "safe", "confCls": "neutral",
        "a": {"k": "aside", "label": "Set aside, exclude", "primary": True},
        "b": {"k": "held", "label": "Hold for review"},
    },
    "conflict": {
        "title": "City conflicts with its ZIP",
        "desc": "The ZIP is usually right, but a person decides.",
        "conf": "check a sample", "confCls": "accent",
        "a": {"k": "sent", "label": "Send all to review", "primary": True},
        "b": {"k": "approved", "label": "Apply ZIP city to all"},
    },
    "zipcity": {
        "title": "No usable ZIP code, and no city either",
        "desc": "These rows have no ZIP code, or one that is not five digits. "
                "The tool normally fills in a blank city from the ZIP, so with "
                "no ZIP it could not fill the city, and it cannot place the "
                "address on a map. Find the ZIP and both problems go away.",
        "conf": "judgment", "confCls": "accent",
        "a": {"k": "sent", "label": "Send all to review", "primary": True},
        "b": {"k": "held", "label": "Hold for review"},
    },
    "cityunknown": {
        "title": "City is not recognized, and the ZIP did not explain it",
        "desc": "The ZIP is usable but did not give a borough, so this is a "
                "city problem in its own right rather than a knock-on effect.",
        "conf": "judgment", "confCls": "accent",
        "a": {"k": "sent", "label": "Send all to review", "primary": True},
        "b": {"k": "held", "label": "Hold for review"},
    },
    "zipbad": {
        "title": "No usable ZIP code",
        "desc": "Not five digits and not recoverable from the address.",
        "conf": "judgment", "confCls": "accent",
        "a": {"k": "sent", "label": "Send all to review", "primary": True},
        "b": {"k": "held", "label": "Hold for review"},
    },
    "noaddr": {
        "title": "No usable address",
        "desc": "Blank or not a real location. Cannot be geocoded.",
        "conf": "judgment", "confCls": "accent",
        "a": {"k": "held", "label": "Hold for review", "primary": True},
        "b": {"k": "aside", "label": "Set aside, exclude"},
    },
    "missing": {
        "title": "A required field is blank",
        "desc": "Name or Client ID is missing and cannot be invented.",
        "conf": "judgment", "confCls": "accent",
        "a": {"k": "sent", "label": "Send all to review", "primary": True},
        "b": {"k": "held", "label": "Hold for review"},
    },
    "idconflict": {
        "title": "One identifier used for records that do not match",
        "desc": "The same ID carries different records. Never merged on a guess.",
        "conf": "judgment", "confCls": "accent",
        "a": {"k": "sent", "label": "Send all to review", "primary": True},
        "b": {"k": "held", "label": "Hold for review"},
    },
    "duprule": {
        "title": "Copies you confirmed",
        "desc": "You decided these rows are copies of another row in the same "
                "file. The first of each group is kept; these are the rest, "
                "listed so you can bring any of them back.",
        "conf": "your rule", "confCls": "accent",
        "a": {"k": "aside", "label": "Set aside, keep the first", "primary": True},
        "b": {"k": "approved", "label": "Keep them all, flag only"},
    },
    "dupc": {
        "title": "Confirmed duplicates, identical rows with one ID",
        "desc": "The only automatic merge. Keep the first, set the copies aside.",
        "conf": "safe to batch", "confCls": "neutral",
        "a": {"k": "aside", "label": "Keep one of each", "primary": True},
        "b": {"k": "sent", "label": "Send all to review"},
    },
    "dupp": {
        "title": "Two records in one file that may be one person",
        "desc": "Same name, street, ZIP and program in the same file, but "
                "different identifiers: a likely double entry. The tool cannot "
                "tell whether it is one person entered twice or two people who "
                "share a name and a building. It never merges them; it asks. "
                "Matches across different files are not listed here; the "
                "Results stage works those out.",
        "conf": "check a sample", "confCls": "accent",
        "a": {"k": "sent", "label": "Send all to review", "primary": True},
        "b": {"k": "kept", "label": "Keep both, flag only"},
    },
    "geo": {
        "title": "Address could not be matched",
        "desc": "The geocoder found no confident match for the street.",
        "conf": "judgment", "confCls": "accent",
        "a": {"k": "sent", "label": "Send all to review", "primary": True},
        "b": {"k": "held", "label": "Hold for review"},
    },
    "other": {
        "title": "Other validation problems",
        "desc": "Type, length, or structure checks that did not pass.",
        "conf": "judgment", "confCls": "accent",
        "a": {"k": "sent", "label": "Send all to review", "primary": True},
        "b": {"k": "held", "label": "Hold for review"},
    },
}

GROUP_ORDER = ["summary", "conflict", "zipcity", "zipbad", "cityunknown", "noaddr",
               "missing", "idconflict", "duprule", "dupc", "geo", "other"]


def _classify(rec):
    """
    Put a row in the group that names the CAUSE of its problem, not a symptom.

    A blank or unusable ZIP is the common root cause: the city is filled from
    the ZIP, so when the ZIP is missing the city cannot be worked out either and
    the row reports both. Grouping such a row under the city sends a reviewer to
    fix the wrong field. Order below runs from most fundamental to least, and a
    row that reports both a ZIP and a city problem is grouped as a ZIP problem.
    """
    errs = " | ".join(rec["__errors__"]).lower()

    zip_bad = ("invalid zip" in errs or "missing zip" in errs
               or ("zip" in errs and "missing" in errs))
    city_bad = ("could not be determined" in errs or "unrecognized city" in errs)

    # 0. not a record at all, so it belongs to no other group
    if "summary row, not a client record" in errs:
        return "summary"
    # 1. a contradiction between two values a person must settle
    if "city/zip conflict" in errs:
        return "conflict"
    # 2. duplicate and identifier problems, which are about the record itself
    if "duplicate within file by your rule" in errs:
        return "duprule"
    if "confirmed duplicate" in errs:
        return "dupc"
    if "same client id" in errs:
        return "idconflict"
    # 3. no address at all, which makes every location question moot
    if "missing address_1" in errs or ("address" in errs and "missing" in errs):
        return "noaddr"
    # 4. the ZIP, which is the root of most location problems
    if zip_bad:
        return "zipcity" if city_bad else "zipbad"
    # 5. a city problem that is genuinely its own, because the ZIP was fine
    if city_bad:
        return "cityunknown"
    if "missing" in errs:
        return "missing"
    if "could not be matched" in errs or "geocod" in errs or "geosupport" in errs:
        return "geo"
    return "other"


GROUP_FIELD = {"zipcity": "Zip", "zipbad": "Zip", "cityunknown": "City",
               "noaddr": "Address_1", "geo": "Address_1"}


def _group_diagnosis(gid, rows):
    """
    Say what a group's rows have in common that a person can act on.

    A field blank on every flagged row from one source is not a data problem
    on those rows, it is a matching problem on that source, and the fix is one
    dropdown on the Map stage rather than a decision per row. This finds that
    case and names the column that looks right.
    """
    field = GROUP_FIELD.get(gid)
    if gid == "missing":
        # the field is named in the message
        names = defaultdict(int)
        for r in rows:
            for e in r["__errors__"]:
                m = re.match(r"Missing (\w+)", e)
                if m:
                    names[m.group(1)] += 1
        if names:
            field = max(names.items(), key=lambda kv: kv[1])[0]
    if not field:
        return []

    by_src = defaultdict(list)
    for r in rows:
        by_src[r["__source_file__"]].append(r)

    out = []
    for key, members in by_src.items():
        blank = sum(1 for r in members if not str(r.get(field, "")).strip())
        if len(members) < 2 or blank / len(members) < 0.9:
            continue
        src_total = len(S["frames"].get(key, []))
        mapping, _c = _guess_for(key)
        mapped = mapping.get(field, "")
        better = None
        try:
            frame = _prepared(key)
            fields = [{"role": field, "label": field, "col": mapped}]
            better = column_check.better_column(field, mapped, frame, fields)
        except Exception:
            better = None
        short = key.split(" :: ")[0]
        if better:
            out.append({
                "source": key, "field": field, "rows": len(members),
                "kind": "mapping",
                "text": (f"Every one of the {len(members)} flagged rows from "
                         f"{short} has no {field}. The {field} is matched to "
                         f"'{mapped or 'nothing'}', which is empty, but the "
                         f"column '{better}' in that file holds it. This is a "
                         "matching problem, not a data problem: fix it once on "
                         "the matching stage and these rows clear together."),
                "better": better, "mapped": mapped,
            })
        elif not mapped:
            out.append({
                "source": key, "field": field, "rows": len(members),
                "kind": "unmapped",
                "text": (f"{short} has no column matched to {field}, so every "
                         f"row from it is missing one. If the file holds it "
                         "under another name, match it on the matching stage. "
                         "If the whole file shares one value, fill it there "
                         "for this source only."),
                "better": None, "mapped": "",
            })
        elif len(members) >= max(2, int(src_total * 0.9)):
            out.append({
                "source": key, "field": field, "rows": len(members),
                "kind": "source",
                "text": (f"{short} has no {field} on any row at all, in the "
                         f"column matched for it ('{mapped}'). The file itself "
                         "does not carry it. If the whole file shares one value, "
                         "fill it for this source only on the matching stage; "
                         "otherwise these rows need the value from elsewhere."),
                "better": None, "mapped": mapped,
            })
    return out


def _calc_note(rec):
    """
    The reason a calculated column left a row blank, read from the prepared
    row. A row whose ZIP could not be worked out arrives in review saying why,
    which is what a person needs to decide it.
    """
    key = rec.get("__source_file__")
    try:
        df = _prepared(key)
        idx = int(rec["__source_row__"])
        if idx >= len(df):
            return ""
        for col in df.columns:
            if str(col).endswith("_note") and str(col)[:-5] in df.columns:
                calc = str(col)[:-5]
                mapping, _c = _guess_for(key)
                if mapping.get("Zip") == calc:
                    note = engine.clean_cell(df.iat[idx, df.columns.get_loc(col)])
                    if note and not note.startswith("kept"):
                        return note
    except Exception:
        return ""
    return ""


def _review_rows():
    """The rows in review, grouped by the cause each is classified under."""
    res = S["results"]
    if not res:
        return {}
    groups = defaultdict(list)
    for rec in res["review"]:
        groups[_classify(rec)].append(rec)
    # Possible duplicates live on the clean side, marked, never merged. Only a
    # pair inside ONE file is a review question, because that is a likely
    # double entry. A match across files is expected whenever the same people
    # appear in several exports, and is what the Results stage resolves; it is
    # not put in the review pile.
    # Within-file duplicates are decided on Tidy up and are not asked about
    # again here. Matches across files are a note, not a decision.
    return groups


def _split_possible_duplicates(res):
    """Possible-duplicate rows split into within-one-file and across-files."""
    tagged = [r for r in res["clean"] if r.get("Possible_Duplicate")]
    files_by_tag = defaultdict(set)
    for r in tagged:
        files_by_tag[r["Possible_Duplicate"]].add(r["__source_file__"])
    # A within-file pair already shown on Tidy up under the reviewer's own
    # rule is not shown a second time here.
    within = []                                 # decided on Tidy up instead
    cross = [r for r in tagged if len(files_by_tag[r["Possible_Duplicate"]]) > 1]
    return within, cross


def _cross_file_matches():
    """What the review stage says about rows matched across files: a count and
    an explanation, never a decision to make."""
    res = S["results"]
    if not res:
        return None
    _within, cross = _split_possible_duplicates(res)
    if not cross:
        return None
    tags = {r["Possible_Duplicate"] for r in cross}
    files = sorted({r["__source_file__"].split(" :: ")[0] for r in cross})
    return {"rows": len(cross), "groups": len(tags), "files": files}


def _replay():
    """Replay the action log into per-rid and per-group statuses."""
    row_status = {}     # rid -> pending|corrected|approved|rejected|removed|held|aside|cleared
    group_status = {}   # gid -> pending|approved|sent|kept|held|aside
    group_outcome = {}
    for act in S["actions"]:
        if act["type"] == "group":
            gid, decision = act["gid"], act["decision"]
            group_status[gid] = "approved" if decision == "accept_all" else decision
            group_outcome[gid] = act.get("outcome", "")
            for rid in act["rids"]:
                if decision == "sent":
                    row_status[rid] = "pending"
                elif decision == "held":
                    row_status[rid] = "held"
                elif decision == "aside":
                    row_status[rid] = "removed"
                elif decision == "kept":
                    row_status[rid] = "cleared"
                elif decision in ("approved", "accept_all"):
                    row_status[rid] = act["row_status"].get(rid, "approved")
        elif act["type"] == "row":
            row_status[act["rid"]] = act["status"]
    return row_status, group_status, group_outcome


def _tallies():
    """The counts the review stage shows: failed, cleared, queued, undecided, decided."""
    res = S["results"]
    if not res:
        return None
    row_status, group_status, _ = _replay()
    groups = _review_rows()
    flagged = sum(len(v) for v in groups.values())
    queue_rids = [r for r, st in row_status.items()
                  if st in ("pending", "corrected", "approved", "rejected",
                            "removed")]
    cleared = sum(1 for st in row_status.values()
                  if st in ("cleared", "corrected", "approved"))
    undecided = sum(len(v) for g, v in groups.items()
                    if group_status.get(g, "pending") == "pending")
    return {
        "flagged": flagged,
        "failed": len(S["results"]["review"]) if S["results"] else 0,
        "cleared": cleared,
        "queue": len(queue_rids),
        "undecided": undecided,
        "decided": sum(1 for g in groups if group_status.get(g) and
                       group_status[g] != "pending"),
        "groups_total": len(groups),
    }


# ---------------------------------------------------------------------------
# pipeline execution and recompute
# ---------------------------------------------------------------------------
def _collect_corrections_meta_and_patch(prepared_frames):
    """Apply uploaded corrections files plus in-review corrections; return meta."""
    meta = {}
    # uploaded Manual_Review_Needed files
    pending, _problems = [], []
    for name, df in S["corrections_files"]:
        p, _ = engine.parse_corrections_frame(df, name)
        pending.extend(p)
    if pending:
        ch1, pending, _ = engine.apply_corrections(S["frames"], pending)
        # frames patched in place; prepared frames rebuilt by caller
        for key, entry in ch1.items():
            meta[key] = (entry["from"], sorted(entry["cols"]))
        ch2, pending, _ = engine.apply_corrections(prepared_frames, pending)
        for key, entry in ch2.items():
            got = meta.setdefault(key, (entry["from"], []))
            meta[key] = (got[0], sorted(set(got[1]) | entry["cols"]))
    # in-review working-copy corrections (queue edits and group fixes)
    for rid, edits in S["queue_edits"].items():
        tkey, row = rid.rsplit("||", 1)
        row = int(row)
        if tkey not in prepared_frames:
            continue
        mapping, _cols = _guess_for(tkey)
        df = prepared_frames[tkey]
        changed = []
        for role, val in edits.items():
            col = mapping.get(role, "")
            if col and col in df.columns and 0 <= row < len(df):
                if str(df.iat[row, df.columns.get_loc(col)]) != str(val):
                    df.iat[row, df.columns.get_loc(col)] = str(val)
                    changed.append(col)
        if changed:
            got = meta.setdefault((tkey, row), ("in-app review", []))
            meta[(tkey, row)] = ("in-app review",
                                 sorted(set(got[1]) | set(changed)))
    return meta


def _execute_pipeline():
    """Build the prepared frames, apply corrections and duplicate decisions, run the engine with progress, and index the result."""
    ref = _load_reference()
    schema = _schema()
    prepared, mappings = {}, {}
    # Corrections from a re-imported file patch the raw frames. The prepared
    # frames are then rebuilt on top of the patched raw frames, and in-app
    # corrections are applied to those. The metadata from both passes is
    # merged, so every correction carries its audit note; an earlier version
    # took only the second pass, which saw no change on a row the first pass
    # had already patched, and the note was silently lost.
    for key in _included_keys():
        prepared[key] = _prepared(key).copy()
    meta_first = _collect_corrections_meta_and_patch(prepared)
    for key in _included_keys():
        prepared[key] = engine.apply_prep_ops(S["frames"][key], _active_ops(key))
    meta = _collect_corrections_meta_and_patch(prepared)
    for k, (src, cols) in meta_first.items():
        got = meta.get(k)
        meta[k] = (got[0] if got else src, sorted(set(cols) | set(got[1] if got else [])))
    for key in prepared:
        mapping, _cols = _guess_for(key)
        role_map = {}
        for f in schema:
            role = f["role"] if f["role"] != "custom" else f["label"]
            col = mapping.get(role, "")
            if col:
                role_map[f["role"] if f["role"] != "custom" else f["label"]] = col
        mappings[key] = role_map
    # Duplicate rules the reviewer wrote are applied here, after the frames
    # are prepared and the matching is known, since a rule is written in
    # schema terms and resolved to each file's columns through its matching.
    # Duplicates within each file: groups the reviewer confirmed as copies keep
    # their first row and set the rest aside; groups nobody has looked at are
    # flagged and kept. Nothing is processed out without a person's say-so.
    for key in prepared:
        prepared[key] = prepared[key].copy()      # never mark the stored frame
        dedupe_rules.apply_decisions(prepared[key], S["dup_fields"], mappings[key],
                                     S["dup_decisions"].get(key, {}))
    def _progress(done, total, phase, file_name="", file_index=0, file_count=0):
        # each phase covers a share of the bar, so it never runs backward
        base = {"Cleaning and checking": (8, 45),
                "Checking for duplicates": (53, 4),
                "Finding locations": (57, 38)}.get(phase, (8, 88))
        pct = int(base[0] + base[1] * (done / max(total, 1)))
        # one calm message per file, and how much of the batch is left
        steps_total = file_count * 2 + 1          # check each file, dedupe, locate each file
        steps_done = ({"Cleaning and checking": 0, "Checking for duplicates": file_count,
                       "Finding locations": file_count + 1}.get(phase, 0)
                      + max(0, file_index - 1))
        if file_name:
            message = ("Finding locations for the rows in " if phase == "Finding locations"
                       else f"{phase} the rows in ") + file_name
        else:
            message = phase
        S["run"].update(state="running", phase=phase, progress=pct,
                        done=done, total=total, message=message,
                        file_name=file_name, file_index=file_index,
                        file_count=file_count,
                        steps_left=max(0, steps_total - steps_done),
                        steps_total=steps_total)

    S["run"] = {"state": "running", "phase": "Starting", "progress": 3,
                "error": "", "done": 0, "total": 0, "message": "Getting ready",
                "steps_left": 0, "steps_total": 0}
    res = engine.run_pipeline(
        prepared, mappings,
        S["settings"]["require_geocode"], ref["idx"],
        int(S["settings"]["seed"]), ref["dist"], ref["gde"], schema,
        S["gde_fields"] or None, bool(S["settings"]["jitter"]), meta or None,
        {k: v for k, v in S["source_defaults"].items() if v},
        S["program_aliases"] or None, progress=_progress,
    )
    S["run"].update(phase="Reconciling", progress=97, message="Reconciling the counts",
                    steps_left=0)
    S["results"] = res
    S["rid_index"] = {_rid(r): r for r in res["transformed"]}
    return res


def _run_thread():
    """Run the pipeline in the background, recording progress and any error in the run status."""
    try:
        S["run"] = {"state": "running", "phase": "Starting", "progress": 3,
                    "error": "", "done": 0, "total": 0}
        _execute_pipeline()
        res = S["results"]
        ok = len(res["clean"]) + len(res["review"]) == len(res["transformed"])
        if not ok:
            raise RuntimeError("Lossless reconciliation failed")
        S["run"] = {"state": "done", "phase": "Done", "progress": 100,
                    "error": ""}
        if S["max_stage"] < 6:
            S["max_stage"] = 6
    except Exception as exc:   # pragma: no cover
        S["run"] = {"state": "error", "phase": "", "progress": 0,
                    "error": str(exc)}


def _recompute():
    """Re-run the pipeline with all accumulated corrections, synchronously.
    The status is updated as it goes, so a page can show what is happening
    while it waits for the answer."""
    try:
        _execute_pipeline()
    finally:
        S["run"].update(state="done", phase="Finished", progress=100)
    S["identity"] = None        # who is who depends on the rows that survived


# ---------------------------------------------------------------------------
# export assembly
# ---------------------------------------------------------------------------
def _export_sets():
    """The four sets a run resolves into after decisions: clean, kept by a reviewer, set aside, still in review."""
    res = S["results"]
    row_status, _gs, _go = _replay()
    clean, review = list(res["clean"]), []
    kept, aside, still = [], [], []
    for rec in res["review"]:
        st = row_status.get(_rid(rec), "")
        if st in ("cleared", "approved"):
            kept.append(rec)
        elif st in ("removed", "aside"):
            aside.append(rec)
        else:
            still.append((rec, st or "pending"))
    return clean, kept, aside, still


def _reconciliation():
    """The counts that must add up: input equals clean plus review plus set aside."""
    res = S["results"]
    clean, kept, aside, still = _export_sets()
    total = len(res["transformed"])
    n_clean = len(clean) + len(kept)
    n_review = len(still)
    n_aside = len(aside)
    assert n_clean + n_review + n_aside == total, "reconciliation failed"
    return {"input": total, "clean": n_clean, "review": n_review,
            "aside": n_aside, "kept": len(kept)}


def _clean_df():
    """The clean output as a table, with the chosen columns and each row's resolution status."""
    clean, kept, _aside, _still = _export_sets()
    schema = S["results"].get("schema") or _schema()
    df = engine.clean_rows_to_dataframe(clean + kept, schema)
    # Every row says how it got here: on its own, or because a person looked
    # at it and accepted it as it stood, which the audit log also records.
    kept_rids = {_rid(r) for r in kept}
    df["Resolution_Status"] = [
        "Approved as entered by reviewer" if _rid(rec) in kept_rids
        else "Passed every check" for rec in clean + kept]
    off = {c for c, v in S["cols_off"].items() if v}
    keep = [c for c in df.columns if c not in off]
    return df[keep]


def _review_df():
    """The review output as a table, one reason per row."""
    _clean, _kept, aside, still = _export_sets()
    rows = [r for r, _s in still] + aside
    df = engine.review_rows_to_dataframe(rows)
    statuses = [s.replace("removed", "set aside").capitalize()
                for _r, s in still] + ["Set aside"] * len(aside)
    if len(df):
        df.insert(2, "Resolution_Status", statuses)
    return df


# ---------------------------------------------------------------------------
# chrome payload
# ---------------------------------------------------------------------------
def _rail_meta():
    """The short line under each stage name in the menu."""
    metas = {i: "" for i in range(1, 8)}
    inc = _included_keys()
    if S["tables"]:
        metas[1] = f"{len(inc)} of {len(S['tables'])} tables included"
    if inc:
        ready = sum(1 for k in inc if _table_ready(k)[0])
        metas[4] = f"{ready} of {len(inc)} tables ready"
        metas[3] = f"{sum(1 for o in S['ops'] if not o['removed'])} staged"
    if S["results"]:
        res = S["results"]
        metas[5] = (f"{_fmtn(len(res['clean']))} clean, "
                    f"{_fmtn(len(res['review']))} flagged")
        t = _tallies()
        if t:
            metas[6] = f"{t['decided']} of {t['groups_total']} groups decided"
    return metas


def _chrome():
    """What every screen shares: stages, mode, undo, save state, port, sources."""
    checks, verdict, fails, warns, backend = _preflight_summary()
    mode = S["mode"]
    return {
        "stage": S["stage"], "maxStage": S["max_stage"], "mode": mode,
        "stages": wording.stages(mode), "checkStage": wording.check_stage(mode),
        "heading": {str(i): wording.heading(i, mode) for i in range(10)},
        "canUndo": bool(S["undo"]),
        "undoLabel": S["undo"][-1]["label"] if S["undo"] else "",
        "railMeta": _rail_meta(),
        "check": {"status": verdict["status"], "fails": fails, "warns": warns},
        "backend": backend,
        "port": PORT,
        "sources": sorted(S["uploads"]),
        "save": {"on": bool(S.get("autosave")),
                 "id": S.get("session_id"),
                 "error": S.get("save_error", ""),
                 "resumedFrom": S.get("resumed_from")},
        "stamps": [
            ["OFFLINE", "no network calls"],
            ["LOSSLESS", "clean + review = input"],
            ["NO AI", "written rules only"],
            ["AUDIT", "IDs only, no PII"],
            ["BACKEND", backend],
        ],
    }


# ---------------------------------------------------------------------------
# routes
# ---------------------------------------------------------------------------
@api.middleware("http")
async def _no_store(request: Request, call_next):
    """
    Never let the browser cache the interface. This is a local tool that gets
    updated in place, and a stale app.js silently hides new controls, which
    looks exactly like missing functionality.
    """
    response = await call_next(request)
    path = request.url.path
    if path == "/" or path.startswith("/static") or path.startswith("/api"):
        response.headers["Cache-Control"] = "no-store, must-revalidate"
        response.headers["Pragma"] = "no-cache"
    return response


@api.get("/", response_class=HTMLResponse)
def index():
    """Serve the single-page interface."""
    return FileResponse(f"{UI_DIR}/index.html")


@api.get("/api/ui")
def ui(screen: str = "check"):
    """Everything one screen needs, in one call: the shared chrome (stages, mode, undo, save state) plus that screen's own data."""
    out = {"chrome": _chrome()}
    if screen == "check":
        checks, verdict, fails, warns, _b = _preflight_summary()
        out["check"] = {"checks": checks, "verdict": verdict,
                        "report": engine.preflight_report_text()}
    elif screen == "sources":
        inc = _included_keys()
        staged = sum(len(S["frames"][k]) for k in inc)
        dp = _dupes_payload(with_groups=False)
        out["dupesNote"] = ({"rows": dp["total_rows"], "groups": dp["total_groups"],
                             "files": sum(1 for x in dp["tables"] if x["total_groups"])}
                            if dp["total_groups"] else None)
        for tb in S["tables"]:
            k = tb["key"]
            tb["canSetHeader"] = k in S["blocks"]
            tb["headerRow"] = S["header_row"].get(k, 1)
            tb["blockPeek"] = [list(map(str, r[:8]))
                               for r in S["blocks"].get(k, [])[:6]]
            wrong, why = (table_detect.header_looks_wrong(S["blocks"][k], tb["headerRow"])
                          if k in S["blocks"] else (False, ""))
            tb["headerWrong"] = wrong
            tb["headerWhy"] = why
        out["sources"] = {
            "tables": S["tables"],
            "included": S["included"],
            "corrections": [{"name": n, "rows": len(d)}
                            for n, d in S["corrections_files"]],
            "stats": {"files": len(S["uploads"]), "tables": len(inc),
                      "rows": staged,
                      "corr": sum(len(d) for _n, d in S["corrections_files"])},
        }
    elif screen == "schema":
        schema = _schema()
        fits = []
        for k in _included_keys():
            mapping, _cols = _guess_for(k)
            have = sum(1 for f in schema
                       if mapping.get(f["role"] if f["role"] != "custom"
                                      else f["label"]))
            missing = [f["label"] for f in schema
                       if not mapping.get(f["role"] if f["role"] != "custom"
                                          else f["label"])]
            note = ""
            if missing:
                rec = [m for m in missing if m.lower() in ("city", "state")]
                note = ", ".join(missing[:3]) + (" missing" if missing else "")
                if rec:
                    note += ". City and State can fill from the ZIP."
            fits.append({"table": k, "have": have, "total": len(schema),
                         "note": note})
        out["schema"] = {"fields": schema, "fit": fits,
                         "editable": S["mode"] == "Advanced",
                         "roles": list(engine.MASTER_COLUMNS),
                         "types": ["str", "int", "decimal", "date", "bool"]}
    elif screen == "prepare":
        _finder()
        cols = {k: [str(c) for c in _prepared(k).columns] for k in _included_keys()}
        out["prepare"] = {"ops": S["ops"],
                          "geocoder": _chrome()["backend"],
                          "tables": _included_keys(),
                          "columns": cols,
                          "delimiters": engine.DELIMITERS,
                          "cases": ["none", "Smart Title (names)",
                                    "Smart Title (address)", "UPPERCASE",
                                    "lowercase", "Title Case (basic)"],
                          "advanced": S["mode"] == "Advanced"}
    elif screen == "map":
        tables = []
        for k in _included_keys():
            mapping, cols = _guess_for(k)
            ready, missing = _table_ready(k)
            df = _prepared(k)
            fields = []
            for f in _schema():
                role = f["role"] if f["role"] != "custom" else f["label"]
                col = mapping.get(role, "")
                note = _samples(df, col) if col else "no match, will be blank"
                fields.append({"role": role, "label": f["label"],
                               "required": bool(f.get("required")),
                               "col": col, "note": note})
            checked = column_check.check_mapping(fields, df)
            tables.append({"check": checked,
                           "key": k, "rows": len(df), "cols": cols,
                           "fields": fields, "ready": ready,
                           "missing": missing,
                           "confirmed": bool(S["confirmed"].get(k)),
                           "headerRow": S["header_row"].get(k, 1),
                           "canSetHeader": k in S["blocks"],
                           "blockPeek": [list(map(str, r[:8]))
                                         for r in S["blocks"].get(k, [])[:6]],
                           "defaults": S["source_defaults"].get(k, {})})
        out["map"] = {"tables": tables,
                      "blocked": [t["key"] for t in tables if not t["ready"]]}
    elif screen == "programs":
        out["programs"] = _programs_payload()
    elif screen == "run":
        res = S["results"]
        payload = {"run": S["run"], "settings": S["settings"],
                   "gdeAvailable": _load_reference()["gde"] is not None,
                   "gdeCatalog": {cat: [f[0] for f in fields] for cat, fields
                                  in engine.GDE_FIELD_CATALOG.items()},
                   "gdeSelected": S["gde_fields"],
                   "blocked": any(not _table_ready(k)[0]
                                  for k in _included_keys())}
        if res and S["run"]["state"] == "done":
            v = defaultdict(int)
            for r in res["transformed"]:
                v[r.get("Verification_Status", "")] += 1
            dupg = len({r.get("Possible_Duplicate") for r in res["transformed"]
                        if r.get("Possible_Duplicate")})
            payload["results"] = {
                "input": len(res["transformed"]),
                "clean": len(res["clean"]), "review": len(res["review"]),
                "verify": {
                    "high": v.get(engine.V_VERIFIED, 0),
                    "low": v.get(engine.V_LOWCONF, 0),
                    "unmatched": v.get(engine.V_UNVERIFIED, 0),
                    "needs": v.get(engine.V_REVIEW, 0)},
                "dup_groups": dupg,
                "quality": res.get("quality", []),
                "corrections": sum(1 for r in res["transformed"] for f in
                                   r["__flags__"]
                                   if f["scenario"] == "15 Corrections"),
            }
            groups = _review_rows()
            biggest = max(groups.items(), key=lambda kv: len(kv[1]),
                          default=(None, []))
            payload["results"]["context"] = wording.run_context(
                len(res["clean"]), len(res["transformed"]),
                GROUP_DEFS.get(biggest[0], {}).get("title") if biggest[0] else None)
        out["runData"] = payload
    elif screen == "review":
        out["crossFile"] = _cross_file_matches()
        out["dupes"] = _dupes_payload()
        out["ruleFields"] = [{"role": f["role"] if f["role"] != "custom" else f["label"],
                              "label": f["label"]} for f in _schema()]
        out["review_extra"] = {"dupesUnreviewed": out["dupes"]["unreviewed"],
                               "dupesRows": out["dupes"]["total_rows"]}
        groups = _review_rows()
        row_status, group_status, group_outcome = _replay()
        glist = []
        for kind in GROUP_ORDER:
            if kind not in groups:
                continue
            d = GROUP_DEFS[kind]
            glist.append({
                "id": kind, "title": d["title"], "desc": d["desc"],
                "conf": d["conf"], "confCls": d["confCls"],
                "count": len(groups[kind]),
                "a": d["a"], "b": d["b"],
                "status": group_status.get(kind, "pending"),
                "outcome": group_outcome.get(kind, ""),
                "diagnosis": _group_diagnosis(kind, groups[kind]),
                "lookup": ({"with_street": sum(1 for r in groups[kind]
                                               if engine.clean_cell(r.get("Address_1", ""))),
                            "with_city": sum(1 for r in groups[kind]
                                             if engine.clean_cell(r.get("City", "")))}
                           if kind in ("zipcity", "zipbad", "cityunknown", "missing")
                           else None),
            })
        glist.sort(key=lambda g: -g["count"])
        out["review"] = {"groups": glist, "tallies": _tallies(),
                         **(out.pop("review_extra", {}) or {})}
    elif screen == "queue":
        out["queue"] = _queue_payload()
    elif screen == "summary":
        out["summary"] = _summary_payload()
    elif screen == "export":
        if not S["results"]:
            out["export"] = {"ready": False, "recon": None, "fmt": S["fmt"],
                             "cols": [], "advanced": S["mode"] == "Advanced"}
        else:
            out["export"] = {"ready": True, "recon": _reconciliation(),
                             "fmt": S["fmt"], "cols": _export_columns(),
                             "advanced": S["mode"] == "Advanced"}
    return JSONResponse(out)


def _export_columns():
    """The columns the clean file can carry, with which are switched off."""
    df = _clean_df_all_columns()
    return [{"name": c, "on": not S["cols_off"].get(c, False)}
            for c in df.columns]


def _clean_df_all_columns():
    """The clean output with every column, before any are switched off."""
    clean, kept, _a, _s = _export_sets()
    schema = S["results"].get("schema") or _schema()
    return engine.clean_rows_to_dataframe(clean + kept, schema)


def _problem_kinds(rec):
    """The distinct problems on a row, shortened to the part before any colon
    so that 'Invalid ZIP Code format: (blank)' groups with its siblings."""
    return sorted({e.split(":")[0].strip() for e in rec["__errors__"]}) or \
        ["No blocking problem"]


def _queue_items():
    """Every row currently in the row-by-row queue, with what it is filtered on."""
    row_status, _gs, _go = _replay()
    items = []
    for rid, st in row_status.items():
        if st in ("cleared", "held"):
            continue
        rec = S["rid_index"].get(rid)
        if rec is None:
            continue
        blanks = [r for r in ("Address_1", "City", "State", "Zip", "Client_ID")
                  if not str(rec.get(r, "")).strip()]
        items.append({
            "rid": rid, "status": st,
            "id": rec.get("Client_ID", ""),
            "name": f"{rec.get('First_Name','')} {rec.get('Last_Name','')}".strip(),
            "address": (f"{rec.get('Address_1','')} {rec.get('Address_2','')}").strip(),
            "city": rec.get("City", ""), "zip": rec.get("Zip", ""),
            "reason": ("; ".join(wording.plain_problem(e, S["mode"])
                                 for e in rec["__errors__"])
                       + (f"; could not be calculated: {_calc_note(rec)}"
                          if _calc_note(rec) else "")) or
                      "; ".join(f["message"] for f in rec["__flags__"][:1]),
            "problems": _problem_kinds(rec),
            "source": rec["__source_file__"],
            "row": rec["__source_row__"],
            "lineage": f"{rec['__source_file__']} row {rec['__source_row__']}",
            "blanks": blanks,
            "group": _classify(rec),
        })
    return items


def _queue_filter(items, status="pending", problem="", source="", q=""):
    """
    Narrow the queue. Every filter is additive, so a reviewer can reach one
    workable slice of a very large queue: pending rows, from one file, that all
    have the same problem.
    """
    out = items
    if status and status != "all":
        out = [i for i in out if i["status"] == status]
    if problem:
        out = [i for i in out if problem in i["problems"]]
    if source:
        out = [i for i in out if i["source"] == source]
    if q:
        ql = q.lower()
        out = [i for i in out
               if ql in (f"{i['id']} {i['name']} {i['address']} {i['city']} "
                         f"{i['zip']} {i['reason']} {i['source']}").lower()]
    return out


def _facets(items):
    """What the queue can be narrowed by, with counts, so the reviewer can see
    where the volume actually is before choosing."""
    prob, src, grp = defaultdict(int), defaultdict(int), defaultdict(int)
    for i in items:
        for pkind in i["problems"]:
            prob[pkind] += 1
        src[i["source"]] += 1
        grp[i["group"]] += 1
    top = lambda d: [{"value": k, "n": v}
                     for k, v in sorted(d.items(), key=lambda kv: -kv[1])]
    return {"problems": top(prob)[:12], "sources": top(src),
            "groups": [{"value": k, "n": v,
                        "label": GROUP_DEFS.get(k, {}).get("title", k)}
                       for k, v in sorted(grp.items(), key=lambda kv: -kv[1])]}


def _queue_payload(filter_status: str = None, page: int = 0, sel: int = 0,
                   sort: str = "", dir: str = "asc", problem: str = "",
                   source: str = "", q: str = "", per: int = 12):
    """One page of the row-by-row queue: items, counts, facets and the open record."""
    items = _queue_items()
    counts = defaultdict(int)
    for it in items:
        counts[it["status"]] += 1

    flt = filter_status or "pending"
    shown = _queue_filter(items, flt, problem, source, q)

    if sort:
        rev = (dir or "asc").lower() == "desc"
        shown = sorted(shown, key=lambda i: str(i.get(sort, "")).lower(),
                       reverse=rev)

    per = max(1, min(int(per or 12), 200))
    pages = max(1, (len(shown) + per - 1) // per)
    page = max(0, min(page, pages - 1))
    window = shown[page * per:(page + 1) * per]

    detail = None
    if window:
        sel = max(0, min(sel, len(window) - 1))
        rec = S["rid_index"][window[sel]["rid"]]
        edits = S["queue_edits"].get(window[sel]["rid"], {})
        fields = []
        for f in _schema():
            role = f["role"] if f["role"] != "custom" else f["label"]
            entered = (rec.get("__custom__", {}).get(f["label"], "")
                       if f["role"] == "custom" else rec.get(f["role"], ""))
            fields.append({"role": role, "label": f["label"],
                           "entered": entered,
                           "working": edits.get(role, entered)})
        # Everything needed to judge this row, including the records it must be
        # judged against and the original row it came from.
        all_recs = (S["results"] or {}).get("transformed", [])
        tkey = rec["__source_file__"]
        raw_row, mapping = {}, {}
        try:
            frame = _prepared(tkey)
            idx = int(rec["__source_row__"])
            if 0 <= idx < len(frame):
                raw_row = {str(c): ("" if pd.isna(v) else str(v))
                           for c, v in frame.iloc[idx].items()}
            mapping, _cols = _guess_for(tkey)
        except Exception:      # a source that is no longer loaded
            raw_row, mapping = {}, {}

        detail = {
            **window[sel],
            "fields": fields,
            "explained": review_context.describe_problems(rec),
            "related": review_context.related_records(rec, all_recs),
            "suggestions": review_context.suggestions(
                rec, engine.borough_from_zip),
            "raw": [{"column": c, "value": v} for c, v in raw_row.items()],
            "unmapped": review_context.unmapped_hint(raw_row, mapping),
            "fills": fill_missing.propose_for_row(rec, _finder()),
        }

    return {"counts": dict(counts), "filter": flt, "page": page,
            "pages": pages, "items": window, "sel": sel, "detail": detail,
            "total": len(shown), "queue_total": len(items),
            "sort": sort, "dir": dir, "per": per,
            "problem": problem, "source": source, "q": q,
            "facets": _facets(items),
            "matching_rids": [i["rid"] for i in shown],
            "fields": [f["role"] if f["role"] != "custom" else f["label"]
                       for f in _schema()]}


@api.get("/api/queue")
def queue(filter: str = "pending", page: int = 0, sel: int = 0,
          sort: str = "", dir: str = "asc", problem: str = "",
          source: str = "", q: str = "", per: int = 12):
    """One page of the row-by-row queue with its filters, counts and facets."""
    return _queue_payload(filter, page, sel, sort, dir, problem, source, q, per)


@api.get("/api/preview")
def preview(key: str, which: str = "raw", page: int = 0, per: int = 8,
            sort: str = "", dir: str = "asc"):
    """
    Rows of one table for on-screen inspection. which='raw' shows the file as
    uploaded; 'prepared' shows it after the staging steps, which is what the
    mapping actually sees. Values are returned as text, exactly as stored.
    """
    if key not in S["frames"]:
        return JSONResponse({"ok": False, "why": "unknown table"},
                            status_code=404)
    df = _prepared(key) if which == "prepared" else S["frames"][key]
    if sort and sort in df.columns:
        # sort the whole table, not just the page on screen, and keep values as
        # text so a column of mixed content still orders predictably
        df = df.sort_values(by=sort, key=lambda c: c.astype(str).str.lower(),
                            ascending=(dir or "asc").lower() != "desc",
                            kind="stable")
    per = max(1, min(int(per), 50))
    total = len(df)
    pages = max(1, (total + per - 1) // per)
    page = max(0, min(int(page), pages - 1))
    window = df.iloc[page * per:(page + 1) * per]
    cols = [str(c) for c in df.columns]
    rows = [["" if v is None else str(v) for v in rec]
            for rec in window.itertuples(index=False, name=None)]
    added = []
    if which == "prepared":
        added = [c for c in cols if c not in [str(x) for x in S["frames"][key].columns]]
    return {"ok": True, "columns": cols, "rows": rows, "total": total,
            "page": page, "pages": pages, "first": page * per + 1 if total else 0,
            "last": min((page + 1) * per, total), "added": added,
            "sort": sort, "dir": dir}


@api.post("/api/mode")
async def set_mode(req: Request):
    """Switch between Guided (plain words) and Advanced (precise terms). Only the words change."""
    body = await req.json()
    S["mode"] = "Advanced" if body.get("mode") == "Advanced" else "Guided"
    _autosave()
    return {"ok": True}


@api.post("/api/goto")
async def goto(req: Request):
    """Open a stage the person has already reached."""
    body = await req.json()
    stage = int(body.get("stage", 0))
    if 0 <= stage <= S["max_stage"]:
        S["stage"] = stage
    _autosave()
    return {"ok": True, "stage": S["stage"]}


@api.post("/api/continue")
def cont():
    """Move to the next stage, unlocking it if this is the first time."""
    nxt = S["stage"] + 1
    # Review (06) is only reachable once the run has completed.
    if S["stage"] == 5 and S["run"]["state"] != "done":
        return JSONResponse({"ok": False, "why": "run first"}, status_code=400)
    if nxt <= 9:
        S["stage"] = nxt
        S["max_stage"] = max(S["max_stage"], nxt)
    _autosave()
    return {"ok": True, "stage": S["stage"]}


@api.post("/api/sources/upload")
async def upload(files: list[UploadFile] = File(...)):
    """Take in one or more files, find the tables inside them, and propose tidy-up steps."""
    for f in files:
        data = await f.read()
        _ingest_upload(f.filename, data)
    _seed_auto_ops()
    _autosave()
    return {"ok": True}


def _ingest_upload(filename, data):
    """Read one uploaded file into the working state. Shared by the upload
    endpoint and the example files, so both behave identically."""
    S["uploads"][filename] = data
    up = _Up(filename, data)
    try:
        probe = engine.read_uploaded_file(up)
        if engine.is_corrections_frame(probe):
            S["corrections_files"].append((filename, probe))
            return
    except Exception:
        pass
    for tbl in engine.tables_from_upload(up):
        key = tbl.key
        if key in S["frames"]:
            continue
        df = tbl.to_dataframe()
        S["frames"][key] = df
        S["included"][key] = bool(tbl.suggested_include)
        if getattr(tbl, "block", None):
            S["blocks"][key] = tbl.block
            S["header_row"][key] = 1 if tbl.has_header else 0
        S["tables"].append({
            "key": key, "file": filename,
            "range": getattr(tbl, "a1_range", "") or "whole file",
            "sheet": getattr(tbl, "sheet", ""),
            "rows": len(df), "cols": len(df.columns),
            "kind": tbl.kind, "reason": tbl.reason,
            "fill": round(getattr(tbl, "fill_rate", 1.0) * 100),
            "sensitive": [c for c, _w in getattr(tbl, "sensitive_columns", [])],
            "marker": _name_marker(filename),
        })


def _name_marker(fname):
    """A short marker derived from a file name, for labels."""
    low = fname.lower()
    return any(m in low for m in ("final", "copy", " v2", "_v2", "(2)",
                                  "verified", "updated"))


def _seed_auto_ops():
    """Propose tidy-up steps for every table just uploaded, marked as automatic."""
    have = {(o["table"], o["op"].get("type"), o["op"].get("column"))
            for o in S["ops"]}
    for key in S["frames"]:
        for op in engine.auto_prep_ops(S["frames"][key]):
            sig = (key, op.get("type"), op.get("column"))
            if sig in have:
                continue
            have.add(sig)
            S["ops"].append({
                "id": f"op{len(S['ops']) + 1}", "table": key, "op": op,
                "origin": "auto", "removed": False,
                "title": engine.describe_op(op),
                "desc": _op_evidence(key, op),
            })


def _op_evidence(key, op):
    """What a proposed step found in the data, for showing beside it."""
    why = op.get("why", "")
    if op.get("type") == "split_jammed":
        tail = ("Creates _street, _address2, _city, _state and _zip. Rows that "
                "are already clean keep their street and leave the rest blank.")
        return (f"{why}. {tail}" if why else tail)
    if op.get("type") == "split_name":
        tail = ("Handles Last, First M and First M Last. A suffix stays with "
                "the last name. DiNapoli and O'Brien keep their casing.")
        return (f"{why}. {tail}" if why else tail)
    return why or "Adds columns only. Nothing is removed."


@api.post("/api/sources/include")
async def include(req: Request):
    """Include or exclude one table found in a file."""
    body = await req.json()
    _snapshot("which tables are included")
    S["included"][body["key"]] = bool(body["on"])
    _autosave()
    return {"ok": True}


@api.post("/api/schema")
async def set_schema(req: Request):
    """Replace the column set-up. Recorded for undo."""
    body = await req.json()
    _snapshot("column set-up")
    S["schema"] = body.get("schema")
    _autosave()
    return {"ok": True}


@api.post("/api/schema/reset")
def reset_schema():
    """Go back to the standard column set-up."""
    _snapshot("reset the column set-up")
    S["schema"] = None
    _autosave()
    return {"ok": True}


@api.post("/api/prepare/toggle")
async def prep_toggle(req: Request):
    """Remove a tidy-up step or bring it back. Nothing is deleted."""
    body = await req.json()
    _snapshot("tidy-up step")
    for op in S["ops"]:
        if op["id"] == body["id"]:
            op["removed"] = bool(body["removed"])
    _autosave()
    return {"ok": True}


@api.post("/api/prepare/add")
async def prep_add(req: Request):
    """Add a tidy-up step to one table. A calculated ZIP column is run once here so the step can say what it found."""
    body = await req.json()
    op = body["op"]
    if op.get("type") == "calc_zip":
        if not op.get("street_col"):
            return JSONResponse({"ok": False, "why": "choose the street column"},
                                status_code=400)
        _finder()                       # the geocoder is ready before the step runs
        # what the step finds on this table, so the person sees it before mapping
        df = _prepared(body["table"])
        out = await run_in_threadpool(
            engine.op_calc_zip, df, op["street_col"], op.get("city_col", ""),
            op.get("zip_col", ""), op.get("mode", "blanks"),
            op.get("name") or "Zip_calculated")
        name = op.get("name") or "Zip_calculated"
        found = int((out[name].astype(str).str.strip() != "").sum())
        kept = int((out[f"{name}_note"] == "kept the ZIP the row already had").sum())
        op["_found"] = found - kept
        op["_kept"] = kept
        op["_failed"] = int(len(out) - found)
    _snapshot("added a tidy-up step")
    S["ops"].append({"id": f"op{len(S['ops']) + 1}", "table": body["table"],
                     "op": op, "origin": "manual", "removed": False,
                     "title": engine.describe_op(op),
                     "desc": ("Added by the operator." if op.get("type") != "calc_zip" else
                              f"Found a ZIP for {op['_found']:,} row(s)"
                              + (f", kept {op['_kept']:,} the file already had" if op["_kept"] else "")
                              + (f", and could not place {op['_failed']:,}; those carry the "
                                 "reason and go to review." if op["_failed"] else "."))})
    _autosave()
    return {"ok": True}


@api.post("/api/sources/default")
async def source_default(req: Request):
    """Set or clear a default that applies to one source file only."""
    body = await req.json()
    key, role = body["key"], body["field"]
    value = str(body.get("value") or "").strip()
    _snapshot("a filled-in value for one source")
    slot = S["source_defaults"].setdefault(key, {})
    if value:
        slot[role] = value
    else:
        slot.pop(role, None)
    _autosave()
    return {"ok": True, "defaults": slot}


@api.post("/api/map/header")
async def set_header_row(req: Request):
    """
    Choose which row of a table holds the column names. Rows above it are
    dropped, which is what a file with title rows above the real header needs.
    """
    body = await req.json()
    key, row = body["key"], int(body.get("row", 1))
    if key not in S["blocks"]:
        return JSONResponse({"ok": False, "why": "this table cannot be rebuilt"},
                            status_code=400)
    _snapshot("which row holds the column names")
    headers, rows = table_detect.frame_from_block(S["blocks"][key], row)
    S["header_row"][key] = row
    S["frames"][key] = pd.DataFrame(rows, columns=headers, dtype=str)
    S["map_ov"].pop(key, None)          # the old mapping named columns that are gone
    S["confirmed"][key] = False
    # a person who chooses a table's header row means to use that table
    S["included"][key] = True
    _autosave()
    return {"ok": True, "columns": headers, "rows": len(rows)}


@api.post("/api/map")
async def set_map(req: Request):
    """Match one field to one column on one table."""
    body = await req.json()
    _snapshot("column matching")
    S["map_ov"].setdefault(body["table"], {})[body["field"]] = body.get(
        "column") or ""
    S["confirmed"][body["table"]] = False
    _autosave()
    return {"ok": True}


@api.post("/api/map/confirm")
async def confirm_map(req: Request):
    """Mark a table's matching as confirmed by a person."""
    body = await req.json()
    S["confirmed"][body["table"]] = True
    _autosave()
    return {"ok": True}


@api.post("/api/run/start")
async def run_start(req: Request):
    """Process the batch in the background with the settings given."""
    body = await req.json()
    S["settings"].update({
        "require_geocode": bool(body.get("require_geocode", False)),
        "jitter": bool(body.get("jitter", True)),
        "seed": int(body.get("seed", 1337)),
    })
    if any(not _table_ready(k)[0] for k in _included_keys()):
        return JSONResponse({"ok": False, "why": "mapping incomplete"},
                            status_code=400)
    S["actions"] = []
    S["queue_edits"] = {}
    t = threading.Thread(target=_run_thread, daemon=True)
    t.start()
    return {"ok": True}


@api.get("/api/express/check")
def express_check():
    """
    What stands between the files and the review stage, before anything runs.

    The fast path does every stage in one go, so it must be honest about the two
    things that can stop it: a required field with no column matched, which
    blocks the run outright, and a matched column that does not look like its
    field, which would run but produce a review full of one mistake. Both are
    reported with what to do about them.
    """
    keys = _included_keys()
    if not keys:
        return {"ok": False, "blockers": [], "warnings": [],
                "why": "No tables are included yet."}
    blockers, warnings = [], []
    for k in keys:
        ready, missing = _table_ready(k)
        short = k.split(" :: ")[0]
        if not ready:
            blockers.append({"table": k, "short": short, "missing": missing,
                             "text": (f"{short} has no column matched for "
                                      f"{', '.join(missing)}, which "
                                      f"{'is' if len(missing) == 1 else 'are'} "
                                      "required.")})
        try:
            mapping, _c = _guess_for(k)
            fields = [{"role": r, "label": r, "col": c}
                      for r, c in mapping.items() if c]
            ck = column_check.check_mapping(fields, _prepared(k))
            for role, res in ck["fields"].items():
                if res["status"] == "problem":
                    warnings.append({"table": k, "short": short, "field": role,
                                     "text": f"{short}, {role}: {res['message']}",
                                     "better": res.get("better")})
        except Exception:
            pass
    dp = _dupes_payload(with_groups=False)
    return {"ok": not blockers, "blockers": blockers, "warnings": warnings,
            "tables": len(keys),
            "rows": sum(len(S["frames"][k]) for k in keys),
            "dupes_unreviewed": dp["unreviewed"],
            "dupes_rows": dp["total_rows"]}


@api.post("/api/express/run")
async def express_run(req: Request):
    """
    Do every stage up to review in one go: keep the tidy-up steps and the
    column matching the tool proposed, process, and land on the review stage.
    Refuses, with reasons, when a required field has nothing matched.
    """
    body = await req.json()
    state = express_check()
    if not state.get("ok"):
        return JSONResponse({"ok": False, **state}, status_code=409)
    if state["warnings"] and not body.get("despite_warnings"):
        return JSONResponse({"ok": False, "needs_confirmation": True, **state},
                            status_code=409)
    for k in _included_keys():
        S["confirmed"][k] = True
    S["actions"] = []
    S["queue_edits"] = {}
    S["max_stage"] = max(S["max_stage"], 7)
    S["stage"] = 7
    threading.Thread(target=_run_thread, daemon=True).start()
    _autosave()
    return {"ok": True}


@api.post("/api/run/gde-field")
async def gde_field(req: Request):
    """Turn one optional Geosupport field on or off in the output."""
    body = await req.json()
    name, on = body["name"], bool(body["on"])
    sel = set(S["gde_fields"])
    sel.add(name) if on else sel.discard(name)
    # keep catalog order so the output columns are stable
    order = [f[0] for _c, fields in engine.GDE_FIELD_CATALOG.items()
             for f in fields]
    S["gde_fields"] = [n for n in order if n in sel]
    return {"ok": True, "selected": S["gde_fields"]}


@api.get("/api/run/status")
def run_status():
    """How processing is going: phase, file, progress, and how many steps are left."""
    return S["run"]


@api.get("/api/review/preview")
def review_preview(gid: str, q: str = "", page: int = 0, per: int = 8,
                   sort: str = "", dir: str = "asc"):
    """
    The rows behind one group, shown as real data rather than a summary.

    A reviewer needs to see the fields the problem is about, side by side, plus
    everything that is wrong with the row and where it came from. A one line
    description is not enough to decide on.
    """
    groups = _review_rows()
    rows = groups.get(gid, [])

    # The fields worth showing depend on the problem, and identity fields are
    # always shown so a reviewer knows whose record they are looking at.
    always = ["Client_ID", "First_Name", "Last_Name"]
    by_group = {
        "conflict":    ["Address_1", "City", "State", "Zip"],
        "zipcity":     ["Address_1", "Address_2", "City", "State", "Zip"],
        "zipbad":      ["Address_1", "Address_2", "City", "State", "Zip"],
        "cityunknown": ["Address_1", "City", "State", "Zip"],
        "noaddr":      ["Address_1", "Address_2", "City", "State", "Zip"],
        "missing":     ["Address_1", "City", "State", "Zip"],
        "idconflict":  ["Address_1", "Address_2", "City", "State", "Zip"],
        "dupc":        ["Address_1", "Address_2", "City", "State", "Zip"],
        "dupp":        ["Address_1", "Address_2", "City", "State", "Zip"],
        "geo":         ["Address_1", "Address_2", "City", "State", "Zip"],
    }
    fields = always + by_group.get(gid, ["Address_1", "City", "State", "Zip"])

    def suggestion(rec):
        """A one-click correction the tool can offer for this row, if any."""
        if gid == "conflict":
            zb = engine.borough_from_zip(rec.get("Zip", ""))
            return f"ZIP says {zb}" if zb else "confirm which is correct"
        if gid == "zipcity":
            return "find the ZIP, then the city follows"
        if gid == "zipbad":
            return "find or correct the ZIP"
        if gid == "cityunknown":
            return "confirm the borough"
        if gid == "noaddr":
            return "no address to work from"
        if gid == "dupc":
            return "identical copy, keep the first"
        if gid == "dupp":
            return "same person key, never merged automatically"
        if gid == "idconflict":
            return "one identifier, two different records"
        if gid == "geo":
            return "address did not match the geocoder"
        return "a person decides"

    def line(rec):
        """One row of a group preview: its values, what is wrong, and a suggestion."""
        entered = {}
        for f in fields:
            entered[f] = rec.get(f, "")
        return {
            "rid": _rid(rec),
            "id": rec.get("Client_ID", ""),
            "values": entered,
            "problems": [wording.plain_problem(e, S["mode"])
                         for e in rec["__errors__"]]
                        + ([f"The ZIP could not be calculated from the address: "
                            f"{_calc_note(rec)}."] if _calc_note(rec) else []),
            "problem_count": len(rec["__errors__"]),
            "suggestion": suggestion(rec),
            "source": rec["__source_file__"],
            "row": rec["__source_row__"],
            "dup_group": rec.get("Possible_Duplicate", ""),
        }

    lines = [line(r) for r in rows]
    if gid == "dupp":
        # pairs sit next to each other, and each says what it was matched on
        lines.sort(key=lambda l: (l["dup_group"], l["source"], int(l["row"])))
        for l in lines:
            v = l["values"]
            basis = ["name", "street", "ZIP", "program"]
            blanks = [f for f in ("Address_2",) if not str(v.get(f, "")).strip()]
            l["suggestion"] = (
                f"{l['dup_group']}: matched on {', '.join(basis)}"
                + ("; no unit recorded, so two people in one building cannot "
                   "be told apart here" if blanks else "; unit matches too")
                + ". Different identifiers. Decide whether it is one person.")
        ql = q.lower()
        lines = [l for l in lines
                 if ql in (" ".join(map(str, l["values"].values())) + " "
                           + " ".join(l["problems"]) + " " + l["source"]).lower()]

    if sort:
        rev = (dir or "asc").lower() == "desc"

        def key(l):
            """The sort key for one candidate row."""
            if sort == "__problems__":
                return (l["problem_count"], "")
            if sort == "__source__":
                return (0, f"{l['source']}|{int(l['row']):09d}")
            return (0, str(l["values"].get(sort, "")).lower())
        lines.sort(key=key, reverse=rev)

    per = max(1, min(int(per), 50))
    pages = max(1, (len(lines) + per - 1) // per)
    page = max(0, min(page, pages - 1))

    # what the whole group has in common, so the plan is visible before paging
    counts = defaultdict(int)
    blank = defaultdict(int)
    for l in lines:
        for pr in l["problems"]:
            counts[pr.split(":")[0].strip()] += 1
        for f, v in l["values"].items():
            if not str(v).strip():
                blank[f] += 1
    common = sorted(counts.items(), key=lambda kv: -kv[1])[:4]
    empties = sorted(blank.items(), key=lambda kv: -kv[1])[:4]

    return {"total": len(lines), "page": page, "pages": pages, "per": per,
            "fields": fields, "sort": sort, "dir": dir,
            "rows": lines[page * per:(page + 1) * per],
            "common_problems": [{"text": k, "n": v} for k, v in common if v],
            "blank_fields": [{"field": k, "n": v} for k, v in empties if v]}


@api.post("/api/review/decide-many")
async def review_decide_many(req: Request):
    """Several group decisions in one go, then one save."""
    body = await req.json()

    def _run():
        out = []
        for d in body.get("decisions") or []:
            r = _apply_group_decision(d.get("gid", ""), d.get("decision", ""))
            out.append({"gid": d.get("gid"), **r})
        return out
    done = await run_in_threadpool(_run)
    S["identity"] = None
    _autosave()
    return {"ok": True, "done": done}


def _apply_group_decision(gid, decision):
    """One group decision, recorded and applied. Shared by the single and
    the batch endpoints. Returns the outcome text."""
    groups = _review_rows()
    rows = groups.get(gid, [])
    rids = [_rid(r) for r in rows]
    act = {"type": "group", "gid": gid, "decision": decision, "rids": rids,
           "row_status": {}, "outcome": ""}
    if decision == "approved" and gid == "conflict":
        # apply the ZIP borough as a real correction, then re-run the engine
        for rec in rows:
            zb = engine.borough_from_zip(rec.get("Zip", ""))
            if zb:
                S["queue_edits"].setdefault(_rid(rec), {})["City"] = zb
        _recompute()
        fixed = misfit = 0
        for rid in rids:
            rec = S["rid_index"].get(rid)
            if rec is not None and not rec["__errors__"]:
                act["row_status"][rid] = "cleared"
                fixed += 1
            else:
                act["row_status"][rid] = "pending"
                misfit += 1
        act["outcome"] = (f"{_fmtn(fixed)} applied"
                          + (f", {_fmtn(misfit)} to the queue" if misfit
                             else ""))
    elif decision in ("approved", "accept_all"):
        # Accept every row in the group exactly as it stands. The rows go to
        # the clean list marked as approved by a reviewer, and the audit log
        # records the decision on each one by identifier.
        for rid in rids:
            act["row_status"][rid] = "approved"
            rec = S["rid_index"].get(rid)
            if rec is not None:
                rec["__flags__"].append({
                    "scenario": "16 Review", "action": "approved",
                    "message": "Accepted as entered by the reviewer, as part of "
                               f"the group '{GROUP_DEFS.get(gid, {}).get('title', gid)}'"})
        act["outcome"] = f"{_fmtn(len(rids))} accepted as entered"
    elif decision == "aside":
        act["outcome"] = f"{_fmtn(len(rids))} set aside"
    elif decision == "sent":
        act["outcome"] = f"{_fmtn(len(rids))} to the queue"
    elif decision == "kept":
        act["outcome"] = f"{_fmtn(len(rids))} kept, flagged"
    elif decision == "held":
        act["outcome"] = f"{_fmtn(len(rids))} held for review"
    S["actions"].append(act)
    S["identity"] = None
    return {"outcome": act["outcome"]}

@api.post("/api/review/group")
async def review_group(req: Request):
    """One group decision."""
    body = await req.json()
    r = await run_in_threadpool(_apply_group_decision, body["gid"], body["decision"])
    S["identity"] = None
    _autosave()
    return {"ok": True, **r}


@api.post("/api/review/undo")
def review_undo():
    """Take back the last group decision."""
    for i in range(len(S["actions"]) - 1, -1, -1):
        if S["actions"][i]["type"] == "group":
            gone = S["actions"].pop(i)
            if gone["gid"] == "conflict" and gone["decision"] == "approved":
                for rid in gone["rids"]:
                    S["queue_edits"].get(rid, {}).pop("City", None)
                _recompute()
            _autosave()
            return {"ok": True}
    return {"ok": False}


@api.post("/api/queue/action")
async def queue_action(req: Request):
    """Decide one queued row: accept, leave for later, set aside, or apply a suggested correction."""
    body = await req.json()
    rid, action = body["rid"], body["action"]
    if action == "corrected":
        edits = body.get("edits", {})
        if edits:
            S["queue_edits"].setdefault(rid, {}).update(edits)
        await run_in_threadpool(_recompute)
        rec = S["rid_index"].get(rid)
        if rec is not None and not rec["__errors__"]:
            status = "corrected"
        else:
            status = "pending"   # the fix did not pass; stays in the queue
        S["actions"].append({"type": "row", "rid": rid, "status": status})
        S["identity"] = None
        _autosave()
        return {"ok": True, "status": status,
                "errors": rec["__errors__"] if rec is not None else []}
    if action in ("approved", "rejected", "removed", "pending"):
        S["actions"].append({"type": "row", "rid": rid, "status": action})
        S["identity"] = None
        _autosave()
        return {"ok": True, "status": action}
    return JSONResponse({"ok": False}, status_code=400)


@api.post("/api/queue/keep-one")
async def queue_keep_one(req: Request):
    """
    Among records that may be one person, keep the chosen row and set the rest
    of its group aside. Nothing is merged: the other rows are listed as set
    aside, with the reason, and can be brought back.
    """
    body = await req.json()
    rid = body.get("rid", "")
    rec = S["rid_index"].get(rid)
    if rec is None:
        return JSONResponse({"ok": False, "why": "unknown row"}, status_code=400)
    all_recs = (S["results"] or {}).get("transformed", [])
    rel = review_context.related_records(rec, all_recs)
    if not rel:
        return JSONResponse({"ok": False, "why": "this row has no related records"},
                            status_code=400)
    aside = 0
    for row in rel["rows"]:
        if row["rid"] == rid:
            S["actions"].append({"type": "row", "rid": rid, "status": "approved"})
        else:
            S["actions"].append({"type": "row", "rid": row["rid"], "status": "removed",
                                 "note": f"set aside as a copy of {rid}"})
            aside += 1
    S["identity"] = None
    _autosave()
    return {"ok": True, "kept": rid, "set_aside": aside}


@api.post("/api/queue/keep-one-per-program")
async def queue_keep_one_per_program(req: Request):
    """
    Across every group of records that may be one person, keep one row per
    person per program and set the rest aside. Two rows are the same person
    when name and date of birth agree as far as they are recorded; the same
    person in two programs is two enrollments and both are kept.
    """
    all_recs = (S["results"] or {}).get("transformed", [])
    row_status, _gs, _go = _replay()
    schema = _schema()
    dob_label = next((f["label"] for f in schema if f["role"] == "custom"
                      and f["label"].strip().lower().replace(" ", "")
                      in ("dob", "dateofbirth", "birthdate")), None)

    def person_key(r):
        """Who a record is, as far as name and date of birth can say, for keeping one per person."""
        first = identity._fold(r.get("First_Name", "")).split(" ")[0] if r.get("First_Name") else ""
        gk = identity.given_keys(r.get("First_Name", ""))
        last = "".join(sorted(identity.surname_tokens(r.get("Last_Name", ""))))
        dob = (r.get("__custom__", {}).get(dob_label, "") if dob_label else "")
        d = identity.parse_dob(dob)
        dobk = f"{d[0]:04d}{d[1]:02d}{d[2]:02d}" if d else ""
        # a nickname group id stands in for the given name where one exists
        g = sorted(k for k in gk if k.startswith("g"))
        return (last, g[0] if g else first, dobk)

    groups = defaultdict(list)
    for r in all_recs:
        rid = _rid(r)
        if row_status.get(rid) in ("removed", "aside", "cleared"):
            continue
        if not r.get("Possible_Duplicate") and not r.get("Duplicate_In_File"):
            continue
        groups[(person_key(r), (r.get("__program__") or "").lower())].append(r)

    kept = aside = 0
    for key, members in groups.items():
        if len(members) < 2:
            continue
        members.sort(key=lambda r: (r["__source_file__"], int(r["__source_row__"])))
        keep = members[0]
        S["actions"].append({"type": "row", "rid": _rid(keep), "status": "approved"})
        kept += 1
        for r in members[1:]:
            S["actions"].append({"type": "row", "rid": _rid(r), "status": "removed",
                                 "note": f"set aside, same person as {_rid(keep)} in the same program"})
            aside += 1
    S["identity"] = None
    _autosave()
    return {"ok": True, "kept": kept, "set_aside": aside,
            "note": (f"kept one row for each of {kept:,} person(s) per program and "
                     f"set {aside:,} row(s) aside" if kept else
                     "no groups of the same person in the same program were found")}


@api.post("/api/queue/bulk")
async def queue_bulk(req: Request):
    """
    Apply one decision to many rows at once.

    Scope is either an explicit list of rids, or every row matching the filters
    currently on screen, which is what makes a queue of thousands workable.

    Corrections are applied to every selected row first and the pipeline is then
    run once, not once per row. Each row is still validated individually, so a
    row the correction does not fix stays in the queue with its reason, exactly
    as it would if it had been corrected on its own.
    """
    body = await req.json()
    action = body.get("action", "")
    edits = {k: v for k, v in (body.get("edits") or {}).items()
             if str(v).strip() != ""}

    if body.get("all_matching"):
        items = _queue_items()
        rids = [i["rid"] for i in _queue_filter(
            items, body.get("filter", "pending"), body.get("problem", ""),
            body.get("source", ""), body.get("q", ""))]
    else:
        rids = [r for r in (body.get("rids") or []) if r in S["rid_index"]]

    if not rids:
        return {"ok": True, "changed": 0, "fixed": 0, "still_open": 0,
                "note": "nothing was selected"}

    if action == "corrected":
        if not edits:
            return JSONResponse({"ok": False, "why": "no values to apply"},
                                status_code=400)
        for rid in rids:
            S["queue_edits"].setdefault(rid, {}).update(edits)
        await run_in_threadpool(_recompute)   # once for the whole batch, not once per row
        fixed = still = 0
        for rid in rids:
            rec = S["rid_index"].get(rid)
            ok = rec is not None and not rec["__errors__"]
            S["actions"].append({"type": "row", "rid": rid,
                                 "status": "corrected" if ok else "pending"})
            fixed += 1 if ok else 0
            still += 0 if ok else 1
        _autosave()
        return {"ok": True, "changed": len(rids), "fixed": fixed,
                "still_open": still,
                "note": (f"{fixed:,} row(s) now pass every check"
                         + (f", {still:,} still have a problem and stay in the "
                            "queue" if still else ""))}

    if action in ("approved", "rejected", "removed", "pending"):
        for rid in rids:
            S["actions"].append({"type": "row", "rid": rid, "status": action})
        S["identity"] = None
        _autosave()
        word = {"approved": "approved as entered", "rejected": "rejected",
                "removed": "removed from the dataset",
                "pending": "put back to pending"}[action]
        return {"ok": True, "changed": len(rids), "fixed": 0, "still_open": 0,
                "note": f"{len(rids):,} row(s) {word}"}

    return JSONResponse({"ok": False, "why": "unknown action"}, status_code=400)


@api.post("/api/export/format")
async def export_format(req: Request):
    """Choose the format the output files are written in."""
    body = await req.json()
    S["fmt"] = body.get("fmt", "CSV")
    _autosave()
    return {"ok": True}


@api.post("/api/export/col")
async def export_col(req: Request):
    """Include or leave out one column of the clean file."""
    body = await req.json()
    S["cols_off"][body["name"]] = not bool(body["on"])
    _autosave()
    return {"ok": True}


@api.get("/api/export/file")
def export_file(which: str = "clean"):
    """Write one of the output files on demand. Nothing is written until asked for."""
    if not S["results"]:
        return JSONResponse({"ok": False, "why": "nothing has been processed yet"},
                            status_code=409)
    fmt = {"CSV": "CSV (.csv)", "Excel": "Excel (.xlsx)",
           "JSON": "JSON (.json)"}.get(S["fmt"], "CSV (.csv)")
    if which == "clean":
        data, mime, ext = engine.serialize_output(_clean_df(), fmt)
        name = f"Final_Clean_Mapped.{ext}"
    elif which == "review":
        data, mime, ext = engine.serialize_output(_review_df(), fmt)
        name = f"Manual_Review_Needed.{ext}"
    elif which == "aside":
        _clean, _kept, aside_rows, _still = _export_sets()
        cols = ["Set_Aside_Reason", "Source_File", "Source_Row"] + \
               [f["label"] for f in _schema()]
        recs = []
        for r in aside_rows:
            reasons = "; ".join(r["__errors__"]) or "set aside by a decision"
            row = {"Set_Aside_Reason": reasons,
                   "Source_File": str(r["__source_file__"]).split(" :: ")[0],
                   "Source_Row": r["__source_row__"]}
            for f in _schema():
                row[f["label"]] = (r.get("__custom__", {}).get(f["label"], "")
                                   if f["role"] == "custom" else r.get(f["role"], ""))
            recs.append(row)
        data, mime, ext = engine.serialize_output(pd.DataFrame(recs, columns=cols), fmt)
        name = f"Set_Aside_Records.{ext}"
    elif which == "unique_clients":
        data, mime, ext = engine.serialize_output(_unique_clients_df(), fmt)
        name = f"Unique_Clients.{ext}"
    elif which == "unique_by_program":
        data, mime, ext = engine.serialize_output(_unique_by_program_df(), fmt)
        name = f"Unique_Clients_By_Program.{ext}"
    elif which == "audit":
        data = audit_trail.full_text(S, engine, engine.describe_op, _guess_for,
                                     _included_keys, S["rid_index"]).encode()
        mime, name = "text/plain", "Secure_Audit_Log.txt"
    else:
        data = engine.build_quality_csv(S["results"].get("quality", [])).encode()
        mime, name = "text/csv", "Data_Quality_Report.csv"
    if isinstance(data, str):
        data = data.encode()
    return Response(content=data, media_type=mime, headers={
        "Content-Disposition": f'attachment; filename="{name}"'})


@api.get("/api/sessions")
def sessions_list():
    """Saved sessions a person can pick up again."""
    return {"sessions": sessions_store.listing(),
            "retention_days": sessions_store.RETENTION_DAYS,
            "autosave": bool(S.get("autosave")),
            "current": S.get("session_id")}


@api.post("/api/sessions/resume")
async def sessions_resume(req: Request):
    """
    Restore the saved decisions from a session. Source files are not stored, so
    the operator uploads them again and the decisions attach to the same rows.
    """
    body = await req.json()
    data = sessions_store.load(body.get("id", ""))
    if not data:
        return JSONResponse({"ok": False, "why": "that session is no longer saved"},
                            status_code=404)
    global S
    S = _blank_state()
    for k, v in (data.get("state") or {}).items():
        if v is not None:
            S[k] = v
    S["session_id"] = data.get("id")
    S["resumed_from"] = data.get("saved_at")
    S["autosave"] = True
    # Nothing can be shown until the files are back, so start at Sources.
    S["stage"] = 1
    S["max_stage"] = max(1, int(S.get("max_stage") or 1))
    S["run"] = {"state": "idle", "phase": "", "progress": 0, "error": ""}
    return {"ok": True, "sources": data.get("sources", []),
            "stage": S["stage"],
            "decisions": len(S.get("actions") or [])}


@api.post("/api/sessions/autosave")
async def sessions_autosave(req: Request):
    """Turn autosave on or off. Turning it off removes the current file."""
    body = await req.json()
    S["autosave"] = bool(body.get("on", True))
    if not S["autosave"] and S.get("session_id"):
        sessions_store.delete(S["session_id"])
        S["session_id"] = None
    else:
        _autosave()
    return {"ok": True, "autosave": S["autosave"]}


@api.post("/api/sessions/delete")
async def sessions_delete(req: Request):
    """Remove one saved session."""
    body = await req.json()
    return {"ok": sessions_store.delete(body.get("id", ""))}


def _source_program_default(key):
    """The program a person named for one file where it has no program column."""
    return engine.clean_cell((S["source_defaults"].get(key) or {}).get("Program", ""))


def _program_values():
    """
    Every program name recorded across the included tables, with row counts.
    A file with no program column but a program named for it as a default
    contributes that name for every row; a file with a column contributes the
    default for its blank rows, which is what the engine does too.
    """
    counts = defaultdict(int)
    for key in _included_keys():
        mapping, _cols = _guess_for(key)
        col = mapping.get("Program", "")
        default = _source_program_default(key)
        df = _prepared(key)
        if col and col in df.columns:
            for v in df[col]:
                s = engine.clean_cell(v) or default
                if s:
                    counts[s] += 1
        elif default:
            counts[default] += len(df)
    return dict(counts)


def _program_sources():
    """Which column each included table reads program names from."""
    out = []
    for key in _included_keys():
        mapping, _cols = _guess_for(key)
        col = mapping.get("Program", "")
        warn = ""
        if col:
            try:
                df = _prepared(key)
                if col in df.columns:
                    res = column_check.check_field("Program", col, df[col])
                    if res["status"] != "ok":
                        warn = res["message"]
            except Exception:
                pass
        out.append({"key": key, "col": col, "warn": warn})
    return out


def _program_group_state():
    """
    The proposed groupings, kept between requests so a person's edits survive.
    Recomputed when the underlying names change, for example after a new file
    or a different column being matched.
    """
    values = _program_values()
    seen = (sorted(values), sorted((s["key"], s["col"], _source_program_default(s["key"]))
                                   for s in _program_sources()))
    if S.pop("_keep_program_groups", False) and S["program_groups"]:
        # a saved grouping, applied to whatever names exist now: names it
        # knows keep their groups, new names stand alone
        known = set(values)
        placed, kept = set(), []
        for g in S["program_groups"]:
            vs = [{"name": v["name"], "rows": values.get(v["name"], 0)}
                  for v in g["variants"] if v["name"] in known]
            if vs:
                placed.update(v["name"] for v in vs)
                kept.append({**g, "variants": vs, "rows": sum(v["rows"] for v in vs)})
        for n in sorted(known - placed):
            kept.append({"canonical": n, "variants": [{"name": n, "rows": values.get(n, 0)}],
                         "rows": values.get(n, 0), "why": "", "needs_confirming": False})
        kept.sort(key=lambda g: (-g["rows"], g["canonical"]))
        S["program_groups"] = kept
        S["program_aliases"] = program_names.build_alias_map(kept)
        S["_prog_seen"] = seen
        return kept, values
    if S["program_groups"] is None or S.get("_prog_seen") != seen:
        S["program_groups"] = program_names.suggest_groups(values)
        S["_prog_seen"] = seen
        S["program_aliases"] = program_names.build_alias_map(S["program_groups"])
    return S["program_groups"], values


def _person_records():
    """
    Turn the processed rows into the records identity resolution works on.

    Only rows that survived to the clean side are counted as people. A row still
    sitting in review has not been accepted into the dataset, so counting it
    would inflate the client numbers the project reports.
    """
    res = S["results"]
    if not res:
        return []
    clean, kept, _aside, _still = _export_sets()
    schema = _schema()
    dob_label = next(
        (f["label"] for f in schema
         if f["role"] == "custom" and f["label"].strip().lower().replace(" ", "")
         in ("dob", "dateofbirth", "birthdate", "birthday")), None)

    out = []
    for rec in clean + kept:
        custom = rec.get("__custom__") or {}
        out.append(identity.PersonRecord(
            _rid(rec),
            first=rec.get("First_Name", ""),
            last=rec.get("Last_Name", ""),
            dob=custom.get(dob_label, "") if dob_label else "",
            street=rec.get("Address_1", ""),
            zip=rec.get("Zip", ""),
            program=rec.get("__program__", ""),
            client_id=rec.get("Client_ID", ""),
            system=str(rec.get("__source_file__", "")).split(" :: ")[0],
            raw=rec))
    return out


def _resolve_identity(force=False):
    """Work out who is who, and cache it until something changes."""
    if S["identity"] is not None and not force:
        return S["identity"]
    recs = _person_records()
    if not recs:
        S["identity"] = None
        return None
    decisions = {tuple(k.split("||||")): v
                 for k, v in (S["id_decisions"] or {}).items()}
    result = identity.resolve(recs, decisions)
    result["_records"] = {r.rid: r for r in recs}
    S["identity"] = result
    return result


def _program_matrix(ident):
    """
    One row per person per program, which is exactly the second count the
    project asks for. Also returns the per-program totals.
    """
    if not ident:
        return {"programs": [], "rows": [], "totals": {}}
    recs = ident["_records"]
    master = ident["master_of"]
    pairs = set()
    per_program = defaultdict(set)
    for rid, r in recs.items():
        mid = master.get(rid)
        if not mid or not r.program:
            continue
        pairs.add((mid, r.program))
        per_program[r.program].add(mid)

    programs = sorted(per_program)
    by_person = defaultdict(set)
    for mid, prog in pairs:
        by_person[mid].add(prog)

    rows = []
    for mid in sorted(by_person):
        example = next((r for rid, r in recs.items()
                        if master.get(rid) == mid), None)
        rows.append({
            "master_id": mid,
            "name": example.label() if example else "",
            "programs": sorted(by_person[mid]),
            "count": len(by_person[mid]),
        })
    rows.sort(key=lambda r: (-r["count"], r["master_id"]))
    return {
        "programs": programs,
        "rows": rows,
        "totals": {p: len(v) for p, v in sorted(per_program.items())},
        "pairs": len(pairs),
    }


def _unique_clients_df():
    """
    One row per person: the answer to the first count the project asks for.
    Every record that resolved to that person is listed, so the number can be
    traced back to the rows behind it.
    """
    ident = _resolve_identity()
    if not ident:
        return pd.DataFrame()
    recs, master = ident["_records"], ident["master_of"]
    grouped = defaultdict(list)
    for rid, r in recs.items():
        grouped[master[rid]].append(r)
    rows = []
    for mid in sorted(grouped):
        members = grouped[mid]
        first = members[0]
        rows.append({
            "Master_ID": mid,
            "First_Name": first.first,
            "Last_Name": first.last,
            "Address_1": first.street,
            "Zip": first.zip,
            "Programs": "; ".join(sorted({m.program for m in members if m.program})),
            "Program_Count": len({m.program for m in members if m.program}),
            "Systems": "; ".join(sorted({m.system for m in members if m.system})),
            "Source_Record_Count": len(members),
            "Source_Client_IDs": "; ".join(sorted({m.client_id for m in members
                                                   if m.client_id})),
            "Source_Rows": "; ".join(sorted(m.rid for m in members)),
        })
    return pd.DataFrame(rows)


def _unique_by_program_df():
    """
    One row per person per program: the answer to the second count. A person in
    three programs appears three times, which is what program reporting needs.
    """
    ident = _resolve_identity()
    if not ident:
        return pd.DataFrame()
    recs, master = ident["_records"], ident["master_of"]
    seen = {}
    for rid, r in recs.items():
        if not r.program:
            continue
        key = (master[rid], r.program)
        slot = seen.setdefault(key, {"records": [], "ids": set(),
                                     "systems": set()})
        slot["records"].append(r)
        if r.client_id:
            slot["ids"].add(r.client_id)
        if r.system:
            slot["systems"].add(r.system)
    rows = []
    for (mid, prog), slot in sorted(seen.items()):
        first = slot["records"][0]
        rows.append({
            "Master_ID": mid,
            "Program": prog,
            "First_Name": first.first,
            "Last_Name": first.last,
            "Address_1": first.street,
            "Zip": first.zip,
            "Systems": "; ".join(sorted(slot["systems"])),
            "Source_Client_IDs": "; ".join(sorted(slot["ids"])),
            "Source_Record_Count": len(slot["records"]),
        })
    return pd.DataFrame(rows)


def _summary_payload():
    """Everything the results stage shows, including the two headline counts."""
    res = S["results"]
    if not res:
        return {"ready": False}
    recon = _reconciliation()
    ident = _resolve_identity()
    matrix = _program_matrix(ident)

    v = defaultdict(int)
    for r in res["transformed"]:
        v[r.get("Verification_Status", "")] += 1

    no_program = sum(1 for r in (ident["_records"].values() if ident else [])
                     if not r.program)

    uc = ident["unique_clients"] if ident else {}
    return {
        "ready": True,
        "goal1": {
            "count": uc.get("settled", 0),
            "low": uc.get("range", (0, 0))[0],
            "high": uc.get("range", (0, 0))[1],
            "open": len(ident["proposals"]) if ident else 0,
            "auto": len(ident["auto_links"]) if ident else 0,
            "confirmed": len(ident["confirmed"]) if ident else 0,
        },
        "goal2": {
            "count": ident["unique_client_programs"] if ident else 0,
            "programs": matrix["programs"],
            "totals": matrix["totals"],
            "rows": matrix["rows"][:50],
            "more": max(0, len(matrix["rows"]) - 50),
            "no_program": no_program,
        },
        "rows": {"input": recon["input"], "clean": recon["clean"],
                 "review": recon["review"], "aside": recon["aside"]},
        "verify": {"high": v.get(engine.V_VERIFIED, 0),
                   "low": v.get(engine.V_LOWCONF, 0),
                   "unmatched": v.get(engine.V_UNVERIFIED, 0),
                   "needs": v.get(engine.V_REVIEW, 0)},
        "quality": res.get("quality", []),
        "sources": sorted(S["uploads"]),
        "backend": _chrome()["backend"],
        "context": wording.run_context(recon["clean"], recon["input"]),
    }


def _summary_html():
    """
    A one page report of the batch, written to be printed or handed on.

    A team has to tell someone what was done and pass the data to whoever draws
    the map. Without this they assemble that by hand from four files.
    """
    from html import escape as _e
    when = datetime.now(timezone.utc).strftime("%d %B %Y at %H:%M UTC")
    res = S["results"]
    if not res:
        body = ("<p>Nothing has been processed yet, so there is nothing to "
                "report. Run the tool and come back.</p>")
        recon = None
    else:
        recon = _reconciliation()
        row_status, _gs, _go = _replay()
        outcomes = defaultdict(int)
        for st in row_status.values():
            outcomes[st] += 1
        v = defaultdict(int)
        for r in res["transformed"]:
            v[r.get("Verification_Status", "")] += 1
        ctx = wording.run_context(len(res["clean"]), len(res["transformed"]))

        sources = "".join(
            f"<tr><td>{_e(str(q.get('file', '')))}</td>"
            f"<td>{_e(str(q.get('total', '')))}</td>"
            f"<td>{_e(str(q.get('clean', '')))}</td>"
            f"<td>{_e(str(q.get('review', '')))}</td>"
            f"<td>{_e(str(q.get('top_issue', '')))}</td></tr>"
            for q in res.get("quality", []))

        groups = _review_rows()
        gs = "".join(
            f"<tr><td>{_e(GROUP_DEFS.get(k, {}).get('title', k))}</td>"
            f"<td>{len(vv):,}</td></tr>"
            for k, vv in sorted(groups.items(), key=lambda kv: -len(kv[1])))

        ident = _resolve_identity()
        matrix = _program_matrix(ident)
        uc = ident["unique_clients"] if ident else {}
        g1 = uc.get("settled", 0)
        lo, hi = uc.get("range", (0, 0))
        openq = len(ident["proposals"]) if ident else 0
        g2 = ident["unique_client_programs"] if ident else 0
        progs = "".join(
            f"<tr><td>{_e(k)}</td><td>{v:,}</td></tr>"
            for k, v in (matrix["totals"] or {}).items())

        body = f"""
        <h2>The two counts</h2>
        <div class="goals">
          <div class="goal"><div class="gk">Goal 1</div>
            <div class="gt">Unique clients</div>
            <div class="gn">{g1:,}</div>
            <div class="gs">Every person counted once, however many systems they
              appear in.</div></div>
          <div class="goal"><div class="gk">Goal 2</div>
            <div class="gt">Unique clients by program</div>
            <div class="gn">{g2:,}</div>
            <div class="gs">The same person counted once in each program they
              take part in.</div></div>
        </div>
        {f'<p class="note">{openq:,} pair(s) of records may be the same person '
         f'and have not been decided, so the first count is between {lo:,} and '
         f'{hi:,}. Deciding them closes the range.</p>' if openq else
         '<p class="note">Every proposed link has been decided, so these counts '
         'are final.</p>'}
        {"<h2>People in each program</h2><table><tr><th>Program</th>"
         "<th>People</th></tr>" + progs + "</table>" if progs else ""}

        <h2>What was produced</h2>
        <table>
          <tr><th>Rows received</th><td>{recon['input']:,}</td></tr>
          <tr><th>Clean and ready</th><td>{recon['clean']:,}</td></tr>
          <tr><th>Still needing work</th><td>{recon['review']:,}</td></tr>
          <tr><th>Set aside</th><td>{recon['aside']:,}</td></tr>
        </table>
        <p class="note">{_e(ctx['verdict'])} {_e(ctx['advice'])}</p>
        <p class="assert">The books balance:
          {recon['clean']:,} + {recon['review']:,} + {recon['aside']:,}
          = {recon['input']:,} rows received. Every row is accounted for.</p>

        <h2>How confident the locations are</h2>
        <table>
          <tr><th>Verified, high confidence</th><td>{v.get(engine.V_VERIFIED, 0):,}</td></tr>
          <tr><th>Verified, low confidence</th><td>{v.get(engine.V_LOWCONF, 0):,}</td></tr>
          <tr><th>Not matched</th><td>{v.get(engine.V_UNVERIFIED, 0):,}</td></tr>
          <tr><th>Needs review</th><td>{v.get(engine.V_REVIEW, 0):,}</td></tr>
        </table>

        <h2>By source file</h2>
        <table><tr><th>File</th><th>Rows in</th><th>Clean</th>
          <th>To review</th><th>Most common problem</th></tr>{sources}</table>

        {"<h2>What needed a decision</h2><table><tr><th>Cause</th><th>Rows</th></tr>" + gs + "</table>" if gs else ""}

        <h2>What happens next</h2>
        <ol>
          <li>The clean file is ready to hand to whoever produces the map.</li>
          <li>Rows still needing work are listed in the review file with the
              reason for each. Correct them there and load that file back in to
              fold them into the clean list.</li>
          <li>The audit log records every change by record ID, with no names or
              addresses, and can be shared safely.</li>
        </ol>"""

    files = ", ".join(sorted(S["uploads"])) or "none recorded"
    backend = _chrome()["backend"]
    return f"""<!DOCTYPE html><html lang="en"><head><meta charset="utf-8">
<title>Crosswalk summary</title><style>
 @page {{ margin: 18mm; }}
 body {{ font-family: system-ui, "Segoe UI", sans-serif; color:#201e1d;
        max-width: 820px; margin: 24px auto; padding: 0 20px; line-height:1.5; }}
 h1 {{ font-size: 26px; margin:0 0 2px; }}
 h2 {{ font-size: 16px; margin:22px 0 8px; border-bottom:2px solid #2f5f88;
       padding-bottom:4px; color:#2f5f88; }}
 .sub {{ color:#61727b; font-size:13px; margin:0 0 4px; }}
 table {{ border-collapse: collapse; width:100%; font-size:13.5px; margin-bottom:6px; }}
 th, td {{ border:1px solid #d8e0e3; padding:6px 9px; text-align:left; }}
 th {{ background:#eef3f7; width:38%; }}
 .note {{ font-size:13px; background:#eef3f7; padding:9px 11px; }}
 .assert {{ font-size:13px; font-weight:600; border:2px solid #2f5f88;
            padding:9px 11px; }}
 .goals {{ display:flex; gap:12px; margin-bottom:10px; }}
 .goal {{ flex:1; border:2px solid #2f5f88; background:#eef3f7; padding:12px 14px; }}
 .gk {{ font-size:10px; letter-spacing:.12em; text-transform:uppercase;
        color:#2f5f88; font-weight:700; }}
 .gt {{ font-size:14px; font-weight:700; }}
 .gn {{ font-size:38px; font-weight:800; line-height:1.1; }}
 .gs {{ font-size:11.5px; color:#1a364c; }}
 .foot {{ margin-top:26px; font-size:11.5px; color:#61727b;
          border-top:1px solid #d8e0e3; padding-top:8px; }}
 .noprint {{ margin: 14px 0; }}
 @media print {{ .noprint {{ display none; }} body {{ margin:0; }} }}
</style></head><body>
<h1>Crosswalk: batch summary</h1>
<p class="sub">Produced {when}</p>
<p class="sub">Source files: {_e(files)}</p>
<p class="sub">Location data from: {_e(backend)}</p>
<div class="noprint"><button onclick="window.print()">Print this page</button></div>
{body}
<div class="foot">Produced by Crosswalk on this computer. No client data left
this machine. This page contains counts only, never client records, so it is
safe to share.</div>
</body></html>"""


@api.post("/api/undo")
def undo_change():
    """Take back the last change to the set-up. Review has its own undo."""
    label = _undo_last()
    if label is None:
        return {"ok": False, "why": "there is nothing to take back"}
    _autosave()
    return {"ok": True, "label": label}


@api.post("/api/sources/example")
def load_example():
    """
    Load the example files that ship with the tool.

    Someone who runs this a few times a year needs a way to practice the whole
    flow without putting real client data at risk, and without hunting through
    folders to find the samples.
    """
    folder = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                          "sample_data")
    if not os.path.isdir(folder):
        return JSONResponse({"ok": False, "why": "the example files are missing"},
                            status_code=404)
    loaded = []
    for name in sorted(os.listdir(folder)):
        path = os.path.join(folder, name)
        if not os.path.isfile(path):
            continue
        with open(path, "rb") as fh:
            data = fh.read()
        _ingest_upload(name, data)
        loaded.append(name)
    _seed_auto_ops()
    _autosave()
    return {"ok": True, "loaded": loaded}


@api.get("/api/alive")
def alive():
    """
    Answers whether the tool is up. It changes nothing, so a launcher or a
    stop script asking this question never counts as a window being open.
    """
    return {"ok": True, "port": PORT, "version": VERSION}


@api.get("/api/heartbeat")
def heartbeat():
    """
    Sent by the open window every few seconds. A window that has been closed
    stops sending it, which is how the tool knows it can stop rather than
    sitting in the background forever.
    """
    global LAST_SEEN, BYE_AT
    LAST_SEEN = time.time()
    BYE_AT = 0.0                     # a window is here, so any goodbye is void
    return {"ok": True}


@api.post("/api/bye")
async def bye():
    """
    Sent by the page as it closes. The tool then waits only a short grace
    period for the window to come back (a reload does that) before stopping,
    instead of the long silence it would otherwise wait out.
    """
    global BYE_AT
    BYE_AT = time.time()
    return {"ok": True}


@api.post("/api/quit")
def quit_app():
    """
    Close the tool from inside it, so nobody has to find a window to close.

    The process ends on its own a moment after answering, however it was
    started. Setting a flag for a launcher to notice was not enough: a server
    started any other way ignored it and kept running.
    """
    global SHUTDOWN
    SHUTDOWN = True

    def _leave():
        time.sleep(0.8)                       # let this answer reach the page
        pid = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                           "crosswalk.pid")
        try:
            os.remove(pid)
        except OSError:
            pass
        os._exit(0)
    threading.Thread(target=_leave, daemon=True).start()
    return {"ok": True}


@api.get("/goodbye", response_class=HTMLResponse)
def goodbye():
    """The page shown after the tool closes."""
    return HTMLResponse("""<!DOCTYPE html><html lang="en"><head>
<meta charset="utf-8"><title>Crosswalk is closed</title><style>
 body { font-family: system-ui, "Segoe UI", sans-serif; color:#201e1d;
        background:#f3f2f2; display:grid; place-items:center; height:100vh;
        margin:0; text-align:center; }
 .box { background:#fff; border:2px solid #2f5f88; padding:30px 36px; max-width:460px; }
 h1 { font-size:22px; margin:0 0 8px; }
 p { font-size:14px; line-height:1.55; color:#444141; margin:0 0 6px; }
</style></head><body><div class="box">
<h1>Crosswalk is closed</h1>
<p>Anything you downloaded is saved where your browser puts downloads.</p>
<p>Nothing else was written to this computer.</p>
<p>You can close this tab. To start again, double-click Crosswalk.</p>
</div>
<script>
  // Now that this page is on screen, tell the tool to stop.
  setTimeout(function () {
    try { fetch("/api/quit", { method: "POST" }).catch(function () {}); } catch (e) {}
  }, 150);
</script></body></html>""")


@api.get("/api/source/file")
def source_file(name: str):
    """The uploaded file exactly as it arrived, so a reviewer can open it."""
    data = S["uploads"].get(name)
    if data is None:
        return JSONResponse({"ok": False, "why": "not loaded"}, status_code=404)
    return Response(content=data, media_type="application/octet-stream",
                    headers={"Content-Disposition": f'attachment; filename="{name}"'})


KNOWN_OP_TYPES = {"clean", "split_delim", "split_jammed", "split_name", "calc_zip"}


@api.get("/api/setups")
def setups_list():
    """The saved set-ups, with any that cannot be read marked as broken."""
    return {"setups": setups.list_setups()}


@api.post("/api/setups/save")
async def setups_save(req: Request):
    """Save the current set-up under a name. No client data is written."""
    body = await req.json()
    name = body.get("name") or ""
    if not name.strip():
        return JSONResponse({"ok": False, "why": "give the set-up a name"}, status_code=400)
    cols = {k: [str(c) for c in S["frames"][k].columns] for k in S["frames"]}
    # The matching as it stands, proposal and overrides together, is what is
    # saved: a later version's proposal might differ, and the person meant
    # this one.
    effective = dict(S["map_ov"])
    for k in S["frames"]:
        mapping, _c = _guess_for(k)
        effective[k] = {role: col for role, col in mapping.items()}
    keep = S["map_ov"]
    S["map_ov"] = effective
    try:
        saved = setups.save_setup(S, name, body.get("note", ""), VERSION, cols)
    finally:
        S["map_ov"] = keep
    return {"ok": True, "name": saved}


@api.post("/api/setups/check")
async def setups_check(req: Request):
    """Check a saved set-up against this version and the files loaded now,
    without changing anything."""
    body = await req.json()
    try:
        d = setups.read_setup(body.get("name", ""))
    except Exception as exc:
        return JSONResponse({"ok": False, "why": f"this set-up cannot be read: {exc}"},
                            status_code=400)
    roles = set(engine.MASTER_COLUMNS) | {"custom"}
    return setups.check_setup(d, S, VERSION, KNOWN_OP_TYPES, roles, engine.describe_op,
                              engine.DEFAULT_SCHEMA)


@api.post("/api/setups/load")
async def setups_load(req: Request):
    """Apply what fits from a saved set-up, and say what was applied."""
    body = await req.json()
    try:
        d = setups.read_setup(body.get("name", ""))
    except Exception as exc:
        return JSONResponse({"ok": False, "why": f"this set-up cannot be read: {exc}"},
                            status_code=400)
    roles = set(engine.MASTER_COLUMNS) | {"custom"}
    report = setups.check_setup(d, S, VERSION, KNOWN_OP_TYPES, roles, engine.describe_op,
                                engine.DEFAULT_SCHEMA)
    _snapshot("loaded a saved set-up")
    applied = setups.apply_setup(d, S, KNOWN_OP_TYPES, list(S["frames"]))
    _forget_prepared()
    S["program_preview_stale"] = True
    _autosave()
    return {"ok": True, "applied": applied, "report": report}


@api.post("/api/setups/delete")
async def setups_delete(req: Request):
    """Remove one saved set-up."""
    body = await req.json()
    return {"ok": setups.delete_setup(body.get("name", ""))}


@api.get("/api/audit")
def audit_view(q: str = "", source: str = "", kind: str = "", page: int = 0,
               per: int = 100):
    """The audit trail as it stands right now, filterable, no client data."""
    return audit_trail.entries(S, engine, _guess_for, _included_keys,
                               S["rid_index"], q, source, kind, page, per)


@api.get("/api/audit/text", response_class=Response)
def audit_text():
    """The whole audit trail as plain text."""
    return Response(content=audit_trail.full_text(
        S, engine, engine.describe_op, _guess_for, _included_keys, S["rid_index"]),
        media_type="text/plain")


@api.get("/api/summary", response_class=HTMLResponse)
def printable_summary():
    """A one page report of the run, written to be printed or handed on."""
    return HTMLResponse(_summary_html())


def _dupes_payload(with_groups=True):
    """
    Duplicates found within each file by the current fields, with the
    reviewer's decisions attached, and a summary of what processing will do.
    """
    tables = []
    for k in _included_keys():
        mapping, _c = _guess_for(k)
        pr = dedupe_rules.proposals(_prepared(k), S["dup_fields"], mapping)
        dec = S["dup_decisions"].get(k, {})
        for g in pr["groups"]:
            g["decision"] = dec.get(g["gid"], "")
        copies = sum(1 for g in pr["groups"] if str(g["decision"]).startswith("copies"))
        keep = sum(1 for g in pr["groups"] if g["decision"] == "keep")
        aside = sum(len(g["rows"]) - 1 for g in pr["groups"] if str(g["decision"]).startswith("copies"))
        tables.append({
            "table": k, "short": k.split(" :: ")[0],
            "total_groups": pr["total_groups"], "total_rows": pr["total_rows"],
            "missing": pr["missing"], "matched_on": pr.get("matched_on", []),
            "shown": pr.get("shown", []),
            "groups": pr["groups"] if with_groups else [],
            "reviewed": copies + keep, "copies": copies, "keep": keep,
            "will_set_aside": aside,
            "unreviewed": pr["total_groups"] - copies - keep,
        })
    return {"fields": S["dup_fields"], "tables": tables,
            "total_rows": sum(t["total_rows"] for t in tables),
            "total_groups": sum(t["total_groups"] for t in tables),
            "unreviewed": sum(t["unreviewed"] for t in tables),
            "will_set_aside": sum(t["will_set_aside"] for t in tables)}


# ---------------------------------------------------------------------------
# Filling in a missing ZIP, City or State from what the row already has
# ---------------------------------------------------------------------------
_FINDER = None


def _finder():
    """The street-to-ZIP finder, built once from the reference and shared with the engine."""
    global _FINDER
    if _FINDER is None:
        ref = _load_reference()
        _FINDER = fill_missing.ZipFinder(ref["idx"], ref["gde"])
        # the calculated ZIP column looks addresses up the same way
        engine.ZIP_RESOLVER = _FINDER.propose
    return _FINDER


def _fill_candidates(gid=None):
    """
    Every row in review that is missing a ZIP, City or State, with what the
    tool would fill in and why, or why it cannot. Nothing is changed here.
    """
    groups = _review_rows()
    rows = groups.get(gid, []) if gid else [r for g in groups.values() for r in g]
    fnd = _finder()
    out = []
    for rec in rows:
        props = fill_missing.propose_for_row(rec, fnd)
        if not props:
            continue
        out.append({
            "rid": _rid(rec),
            "name": f"{rec.get('First_Name', '')} {rec.get('Last_Name', '')}".strip(),
            "address": rec.get("Address_1", ""), "city": rec.get("City", ""),
            "state": rec.get("State", ""), "zip": rec.get("Zip", ""),
            "source": rec["__source_file__"].split(" :: ")[0],
            "row": rec["__source_row__"],
            "proposals": props,
            "fillable": any(p["value"] for p in props),
        })
    return out


@api.get("/api/fill/preview")
def fill_preview(gid: str = "", page: int = 0, per: int = 25):
    """Every row in review missing a ZIP, city or state, with what would be filled and why."""
    cands = _fill_candidates(gid or None)
    fillable = [c for c in cands if c["fillable"]]
    stuck = [c for c in cands if not c["fillable"]]
    per = max(1, min(int(per), 100))
    pages = max(1, (len(fillable) + per - 1) // per)
    page = max(0, min(page, pages - 1))
    by_field = defaultdict(int)
    for c in fillable:
        for pr in c["proposals"]:
            if pr["value"]:
                by_field[pr["field"]] += 1
    return {"fillable": len(fillable), "stuck": len(stuck),
            "by_field": dict(by_field),
            "page": page, "pages": pages,
            "items": fillable[page * per:(page + 1) * per],
            "stuck_sample": stuck[:5]}


@api.post("/api/fill/apply")
async def fill_apply(req: Request):
    """
    Fill in what was shown, on the rows the reviewer approved: every fillable
    row in the group, or a chosen list. Each fill is applied as a recorded
    correction and the rows are checked again, so a filled ZIP that turns out
    to disagree with the city is still caught.
    """
    body = await req.json()
    gid = body.get("gid") or None
    only = set(body.get("rids") or [])
    cands = [c for c in _fill_candidates(gid) if c["fillable"]]
    if only:
        cands = [c for c in cands if c["rid"] in only]
    filled = 0
    for c in cands:
        edits = {p["field"]: p["value"] for p in c["proposals"] if p["value"]}
        if not edits:
            continue
        S["queue_edits"].setdefault(c["rid"], {}).update(edits)
        S["actions"].append({"type": "row", "rid": c["rid"], "status": "corrected",
                             "note": "filled " + ", ".join(
                                 f"{k}={v}" for k, v in edits.items())})
        filled += 1
    if filled:
        await run_in_threadpool(_recompute)
    S["identity"] = None
    _autosave()
    return {"ok": True, "filled": filled}


@api.post("/api/prepare/dupes/fields")
async def dupes_fields(req: Request):
    """Change what makes two rows one person. Decisions about the old groups
    no longer apply, so they are cleared."""
    body = await req.json()
    fields = [f for f in (body.get("fields") or []) if f]
    if not fields:
        return JSONResponse({"ok": False, "why": "choose at least one field"},
                            status_code=400)
    _snapshot("what counts as a duplicate")
    S["dup_fields"] = fields
    S["dup_decisions"] = {}
    if S["results"] is not None:
        await run_in_threadpool(_recompute)
    _autosave()
    return {"ok": True}


@api.post("/api/prepare/dupes/decide")
async def dupes_decide(req: Request):
    """
    Record what the reviewer decided about groups of rows that may be one
    person, then process the batch once. The page sends every decision at
    once as "decisions", each {table, gid, decision} or {table, all: true,
    decision}; a single decision is the same list with one entry. "copies"
    keeps the first row and sets the rest aside; "keep" leaves them alone;
    "" forgets the decision.
    """
    body = await req.json()
    items = body.get("decisions")
    if items is None:
        items = [body]
    _snapshot("duplicate decisions")

    def _apply():
        for d in items:
            key = d.get("table", "")
            verdict = d.get("decision", "")
            if verdict not in ("copies", "keep", "") and not \
                    (isinstance(verdict, str) and verdict.startswith("copies:")):
                continue
            slot = S["dup_decisions"].setdefault(key, {})
            if d.get("all"):
                mapping, _c = _guess_for(key)
                pr = dedupe_rules.proposals(_prepared(key), S["dup_fields"], mapping,
                                            limit=100000)
                for g in pr["groups"]:
                    if verdict:
                        slot[g["gid"]] = verdict
                    else:
                        slot.pop(g["gid"], None)
            else:
                gid = d.get("gid", "")
                if verdict:
                    slot[gid] = verdict
                else:
                    slot.pop(gid, None)
        # decided during review, so the batch is processed again, once
        if S["results"] is not None:
            _recompute()
    await run_in_threadpool(_apply)
    _autosave()
    return {"ok": True, "applied": len(items)}


@api.post("/api/prepare/dedupe")
async def add_dedupe_rule(req: Request):
    """
    A duplicate rule in the reviewer's own terms: which schema fields make two
    rows the same, whether that is for one file or every file, and whether to
    flag the copies or keep the first and set the rest aside.
    """
    body = await req.json()
    fields = [f for f in (body.get("fields") or []) if f]
    if not fields:
        return JSONResponse({"ok": False, "why": "choose at least one field"},
                            status_code=400)
    action = body.get("action") if body.get("action") in ("flag", "keep_first") \
        else "flag"
    _snapshot("a duplicate rule")
    S["dedupe_rules"].append({
        "id": f"dr{len(S['dedupe_rules']) + 1}",
        "scope": body.get("scope") or "*",
        "fields": fields, "action": action, "removed": False,
    })
    S["results"] = None
    S["identity"] = None
    _autosave()
    return {"ok": True}


@api.post("/api/prepare/dedupe/toggle")
async def toggle_dedupe_rule(req: Request):
    """Kept for saved sessions from before; the duplicates panel replaces it."""
    body = await req.json()
    _snapshot("a duplicate rule")
    for r in S["dedupe_rules"]:
        if r["id"] == body.get("id"):
            r["removed"] = bool(body.get("removed"))
    S["results"] = None
    _autosave()
    return {"ok": True}


@api.post("/api/programs/group")
async def programs_group(req: Request):
    """
    Put a program name into a group, or take it out into one of its own.

    Program names differ between systems for the same program, and counting
    them literally makes one program look like several. Nothing is merged
    without this being confirmed, and any name can be pulled back out.
    """
    body = await req.json()
    name, target = body.get("name", ""), body.get("into", "")
    groups, values = _program_group_state()

    for g in groups:
        g["variants"] = [v for v in g["variants"] if v["name"] != name]
    groups = [g for g in groups if g["variants"]]

    if target == "__alone__":
        groups.append({"canonical": name,
                       "variants": [{"name": name, "rows": values.get(name, 0)}],
                       "rows": values.get(name, 0), "why": "kept on its own",
                       "needs_confirming": False})
    else:
        for g in groups:
            if g["canonical"] == target:
                g["variants"].append({"name": name,
                                      "rows": values.get(name, 0)})
                g["needs_confirming"] = True
                break
        else:
            groups.append({"canonical": name,
                           "variants": [{"name": name,
                                         "rows": values.get(name, 0)}],
                           "rows": values.get(name, 0), "why": "",
                           "needs_confirming": False})

    for g in groups:
        g["rows"] = sum(values.get(v["name"], 0) for v in g["variants"])
    groups.sort(key=lambda g: (-g["rows"], g["canonical"]))
    S["program_groups"] = groups
    S["program_aliases"] = program_names.build_alias_map(groups)
    S["identity"] = None
    S["program_preview_stale"] = True
    _autosave()
    return {"ok": True}


@api.post("/api/programs/rename")
async def programs_rename(req: Request):
    """Set the name a group is counted under."""
    body = await req.json()
    old, new = body.get("canonical", ""), str(body.get("name", "")).strip()
    if not new:
        return JSONResponse({"ok": False, "why": "a group needs a name"},
                            status_code=400)
    groups, _values = _program_group_state()
    for g in groups:
        if g["canonical"] == old:
            g["canonical"] = new
            break
    S["program_groups"] = groups
    S["program_aliases"] = program_names.build_alias_map(groups)
    S["identity"] = None
    S["program_preview_stale"] = True
    _autosave()
    return {"ok": True}


def _programs_payload():
    """
    Everything the Programs stage shows: which column each file reads the
    program from (with samples and a warning), the grouping of names, and
    the last preview of the counts, marked stale when anything has changed
    since it was taken.
    """
    groups, values = _program_group_state()
    sources = []
    for k in _included_keys():
        mapping, cols = _guess_for(k)
        col = mapping.get("Program", "")
        df = _prepared(k)
        samples, warn, distinct = [], "", 0
        if col and col in df.columns:
            vals = [engine.clean_cell(v) for v in df[col]]
            vals = [v for v in vals if v]
            distinct = len(set(vals))
            seen = []
            for v in vals:
                if v not in seen:
                    seen.append(v)
                if len(seen) >= 4:
                    break
            samples = seen
            res = column_check.check_field("Program", col, df[col])
            if res["status"] != "ok":
                warn = res["message"]
        default = _source_program_default(k)
        if not col and default:
            samples, distinct = [default], 1
        sources.append({"key": k, "short": k.split(" :: ")[0], "col": col,
                        "cols": cols, "samples": samples, "warn": warn,
                        "distinct": distinct, "rows": len(df),
                        "default": default})
    # which files each group draws from
    file_of = defaultdict(set)
    for k in _included_keys():
        mapping, _c = _guess_for(k)
        col = mapping.get("Program", "")
        if not col:
            continue
        df = _prepared(k)
        if col in df.columns:
            for v in set(engine.clean_cell(x) for x in df[col]):
                if v:
                    file_of[v].add(k.split(" :: ")[0])
    for k in _included_keys():
        d = _source_program_default(k)
        if d:
            file_of[d].add(k.split(" :: ")[0])
    for g in groups:
        for v in g["variants"]:
            v["files"] = sorted(file_of.get(v["name"], []))
    return {"sources": sources, "groups": groups,
            "stamp": f"{len(S['actions'])}:{S.get('_prog_stamp', 0)}",
            "distinct": len(values), "grouped_into": len(groups),
            "mapped_on": sum(1 for s in sources if s["col"] or s["default"]),
            "preview": S.get("program_preview"),
            "preview_stale": bool(S.get("program_preview_stale", True)),
            "ready": all(_table_ready(k)[0] for k in _included_keys()),
            "blockers": [f"{k.split(' :: ')[0]}: no column matched for "
                         f"{', '.join(_table_ready(k)[1])}"
                         for k in _included_keys() if not _table_ready(k)[0]]}


def _build_program_preview():
    """
    What the two counts would be with the programs as they stand now. The
    batch is processed with the current grouping and identity resolved, which
    is the same work the Results stage does; nothing is decided here.
    """
    _execute_pipeline()
    S["run"].update(state="done", phase="Finished", progress=100)
    S["identity"] = None
    ident = _resolve_identity()
    matrix = _program_matrix(ident)
    uc = ident["unique_clients"] if ident else {}
    recs = ident["_records"].values() if ident else []
    no_program = sum(1 for r in recs if not r.program)
    per_program = []
    for name in matrix["programs"]:
        per_program.append({"program": name,
                            "unique_clients": matrix["totals"].get(name, 0),
                            "rows": sum(1 for r in recs if r.program == name)})
    per_program.sort(key=lambda x: -x["unique_clients"])
    res = S["results"]
    S["program_preview"] = {
        "goal1": uc.get("settled", 0),
        "goal1_low": uc.get("range", (0, 0))[0],
        "goal1_high": uc.get("range", (0, 0))[1],
        "goal2": ident["unique_client_programs"] if ident else 0,
        "programs": per_program,
        "no_program": no_program,
        "counted_rows": len(res["clean"]) if res else 0,
        "review_rows": len(res["review"]) if res else 0,
        "taken_at": time.strftime("%H:%M:%S"),
    }
    S["program_preview_stale"] = False
    return S["program_preview"]


@api.post("/api/programs/apply")
async def programs_apply(req: Request):
    """
    Apply a whole set of program changes at once: which column each file
    reads the program from, and which names are one program. The page holds
    every move locally and sends them together, so grouping feels immediate
    and the server does one pass instead of one per click.
    """
    body = await req.json()
    _snapshot("program set-up")
    for c in body.get("columns") or []:
        S["map_ov"].setdefault(c["table"], {})["Program"] = c.get("column") or ""
    S["program_groups"] = None
    S["_prog_seen"] = None
    groups, values = _program_group_state()          # fresh proposal for the new columns
    sent = body.get("groups")
    if sent:
        # the person's grouping, over whatever names now exist
        known = set(values)
        placed = set()
        new_groups = []
        for g in sent:
            names = [n for n in (g.get("names") or []) if n in known and n not in placed]
            if not names:
                continue
            placed.update(names)
            canonical = (g.get("canonical") or names[0]).strip() or names[0]
            new_groups.append({"canonical": canonical,
                               "variants": [{"name": n, "rows": values.get(n, 0)} for n in names],
                               "rows": sum(values.get(n, 0) for n in names),
                               "why": "", "needs_confirming": False})
        for n in sorted(known - placed):             # anything the page did not mention
            new_groups.append({"canonical": n, "variants": [{"name": n, "rows": values.get(n, 0)}],
                               "rows": values.get(n, 0), "why": "", "needs_confirming": False})
        new_groups.sort(key=lambda g: (-g["rows"], g["canonical"]))
        S["program_groups"] = new_groups
        S["program_aliases"] = program_names.build_alias_map(new_groups)
    S["program_preview_stale"] = True
    S["identity"] = None
    S["_prog_stamp"] = S.get("_prog_stamp", 0) + 1
    _autosave()
    return {"ok": True}


@api.post("/api/programs/preview")
async def programs_preview():
    """Refresh the preview of the counts with the programs as they stand."""
    if not _included_keys():
        return JSONResponse({"ok": False, "why": "no tables are included"}, status_code=409)
    missing = [k for k in _included_keys() if not _table_ready(k)[0]]
    if missing:
        return JSONResponse({"ok": False, "why": "a required column is not matched",
                             "blockers": [k.split(" :: ")[0] for k in missing]},
                            status_code=409)
    S["actions"] = []
    S["queue_edits"] = {}
    pv = await run_in_threadpool(_build_program_preview)
    S["max_stage"] = max(S["max_stage"], 5)
    _autosave()
    return {"ok": True, "preview": pv}


@api.post("/api/programs/column")
async def programs_column(req: Request):
    """Which column a file reads its program from."""
    body = await req.json()
    _snapshot("which column holds the program")
    S["map_ov"].setdefault(body["table"], {})["Program"] = body.get("column") or ""
    S["program_groups"] = None
    S["_prog_seen"] = None
    S["program_preview_stale"] = True
    S["identity"] = None
    _autosave()
    return {"ok": True}


@api.post("/api/programs/refresh")
def programs_refresh():
    """Read the program names again from whatever is matched right now."""
    S["program_groups"] = None
    S["_prog_seen"] = None
    _program_group_state()
    S["identity"] = None
    S["program_preview_stale"] = True
    S["_prog_stamp"] = S.get("_prog_stamp", 0) + 1
    _autosave()
    return {"ok": True}


@api.post("/api/programs/reset")
def programs_reset():
    """Go back to what the tool proposed."""
    S["program_groups"] = None
    S["_prog_seen"] = None
    _program_group_state()
    S["identity"] = None
    S["program_preview_stale"] = True
    S["_prog_stamp"] = S.get("_prog_stamp", 0) + 1
    _autosave()
    return {"ok": True}


@api.post("/api/identity/decide")
async def identity_decide(req: Request):
    """
    Confirm or reject a proposed link between two records.

    Deciding these is what closes the range on the client count, so the number
    reported is one a person has stood behind rather than one the tool guessed.
    """
    body = await req.json()
    a, b = body.get("a", ""), body.get("b", "")
    verdict = body.get("verdict", "")
    if verdict not in ("same", "different"):
        return JSONResponse({"ok": False, "why": "unknown verdict"},
                            status_code=400)
    key = "||||".join(sorted((a, b)))
    S["id_decisions"][key] = verdict
    S["identity"] = None
    _autosave()
    return {"ok": True}


@api.get("/api/identity/proposals")
def identity_proposals(page: int = 0, per: int = 8):
    """The links still waiting on a person, with the evidence for each."""
    ident = _resolve_identity()
    props = ident["proposals"] if ident else []
    per = max(1, min(int(per), 50))
    pages = max(1, (len(props) + per - 1) // per)
    page = max(0, min(page, pages - 1))
    return {"total": len(props), "page": page, "pages": pages,
            "items": props[page * per:(page + 1) * per]}


@api.post("/api/reset")
def reset():
    """Clear everything and remove this session's saved file."""
    _forget_prepared()
    global S
    old = S.get("session_id")
    keep_autosave = bool(S.get("autosave", True))
    S = _blank_state()
    S["autosave"] = keep_autosave
    if old:
        sessions_store.delete(old)
    return {"ok": True}


# Sessions older than the retention window are removed when the server starts,
# so an abandoned batch clears itself without anyone remembering to tidy up.
try:
    _purged = sessions_store.purge_expired()
    if _purged:
        print(f"Removed {len(_purged)} session(s) older than "
              f"{sessions_store.RETENTION_DAYS} days")
except Exception:      # pragma: no cover
    pass

api.mount("/static", StaticFiles(directory=UI_DIR), name="static")
