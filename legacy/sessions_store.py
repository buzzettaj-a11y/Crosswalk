"""
Autosave and resume.

What is saved, and what is deliberately not
------------------------------------------
A session file holds the decisions that took human time: the schema, the
staging steps, the column mapping, per-source defaults, the header row chosen
for each table, run settings, and every review decision. Losing those on a
nineteen thousand row batch would cost hours.

Uploaded files and the tables read from them are NOT saved. They stay in memory
and disappear when the server stops. This keeps the promise the rest of the tool
makes: client data is not written to disk unless an operator exports it. On
resume the operator points at the same source files again and the saved
decisions are replayed onto them.

One exception is named honestly rather than hidden. A correction typed during
review, for example a corrected borough, is part of a decision and is saved with
it. Those are single field values, not records, and a session file never
contains a whole row. If even that is unacceptable on a given machine, autosave
can be turned off and the tool behaves exactly as before.

Sessions older than seven days are deleted on startup and whenever a session is
saved.
"""
from __future__ import annotations

import json
import os
import re
import time
from datetime import datetime, timedelta, timezone

SESSION_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "sessions")
RETENTION_DAYS = 7

# Only these parts of the working state are written to disk. Anything holding
# uploaded rows (frames, blocks, results, rid_index) is deliberately absent.
SAVED_KEYS = [
    "mode", "stage", "max_stage", "schema", "ops", "map_ov", "confirmed",
    "source_defaults", "header_row", "included", "settings", "gde_fields",
    "dedupe_rules", "dup_fields", "dup_decisions",
    "actions", "queue_edits", "fmt", "cols_off",
]


def _now():
    """The current time as an ISO string."""
    return datetime.now(timezone.utc)


def ensure_dir():
    """Make sure the sessions folder exists."""
    os.makedirs(SESSION_DIR, exist_ok=True)
    return SESSION_DIR


def _safe_id(session_id: str) -> str:
    """A session id is used as a filename, so it may only be simple text."""
    return re.sub(r"[^A-Za-z0-9_-]", "", str(session_id or ""))[:64]


def new_id() -> str:
    """A fresh session identifier."""
    return _now().strftime("s%Y%m%d-%H%M%S")


def path_for(session_id: str) -> str:
    """Where one session's file lives."""
    return os.path.join(ensure_dir(), f"{_safe_id(session_id)}.json")


def purge_expired(days: int = RETENTION_DAYS):
    """
    Delete sessions older than the retention window. Returns the names removed.
    Called on startup and on every save, so an abandoned session clears itself
    without anyone remembering to tidy up.
    """
    removed = []
    cutoff = time.time() - days * 86400
    try:
        for name in os.listdir(ensure_dir()):
            if not name.endswith(".json"):
                continue
            full = os.path.join(SESSION_DIR, name)
            try:
                if os.path.getmtime(full) < cutoff:
                    os.remove(full)
                    removed.append(name[:-5])
            except OSError:
                pass
    except OSError:
        pass
    return removed


def save(session_id: str, state: dict, source_names=None) -> str:
    """Write the resumable parts of the state. Returns the file path."""
    purge_expired()
    payload = {
        "id": _safe_id(session_id),
        "saved_at": _now().isoformat(timespec="seconds"),
        "expires_at": (_now() + timedelta(days=RETENTION_DAYS)).isoformat(
            timespec="seconds"),
        "sources": sorted(source_names or []),
        "state": {k: state.get(k) for k in SAVED_KEYS},
    }
    full = path_for(session_id)
    tmp = full + ".tmp"
    with open(tmp, "w", encoding="utf-8") as fh:
        json.dump(payload, fh, indent=1, default=str)
    os.replace(tmp, full)          # replace in one step, never a half-written file
    return full


def load(session_id: str):
    """Read one session, or None when it is missing or unreadable."""
    try:
        with open(path_for(session_id), encoding="utf-8") as fh:
            return json.load(fh)
    except (OSError, ValueError):
        return None


def delete(session_id: str) -> bool:
    """Remove one session's file."""
    try:
        os.remove(path_for(session_id))
        return True
    except OSError:
        return False


def listing():
    """Every saved session, newest first, described for a person to choose from."""
    purge_expired()
    out = []
    try:
        names = os.listdir(ensure_dir())
    except OSError:
        return out
    for name in names:
        if not name.endswith(".json"):
            continue
        data = load(name[:-5])
        if not data:
            continue
        st = data.get("state") or {}
        stage = int(st.get("stage") or 0)
        decisions = len(st.get("actions") or [])
        saved = data.get("saved_at", "")
        try:
            age_days = (_now() - datetime.fromisoformat(saved)).days
        except Exception:
            age_days = 0
        out.append({
            "id": data.get("id", name[:-5]),
            "saved_at": saved,
            "expires_in_days": max(0, RETENTION_DAYS - age_days),
            "stage": stage,
            "sources": data.get("sources", []),
            "decisions": decisions,
            "summary": _describe(st, data.get("sources", [])),
        })
    return sorted(out, key=lambda s: s["saved_at"], reverse=True)


STAGE_NAMES = ["System check", "Sources", "Schema", "Prepare", "Map", "Run",
               "Review", "Export"]


def _describe(state, sources):
    """A one-line description of a saved session for the resume list."""
    stage = int(state.get("stage") or 0)
    name = STAGE_NAMES[stage] if 0 <= stage < len(STAGE_NAMES) else "in progress"
    bits = [f"stopped at {name}"]
    n = len(sources)
    if n:
        bits.append(f"{n} source file{'s' if n != 1 else ''}")
    d = len(state.get("actions") or [])
    if d:
        bits.append(f"{d} review decision{'s' if d != 1 else ''}")
    return ", ".join(bits)
