"""Resume (SPEC 10.2, fix plan 5.5). Files match by fingerprint; decisions replay by record key through M08.

A file with a new fingerprint but the same normalized name is `changed`, and its rows whose text didn't change keep their
keys, so their decisions still apply (10.2 wins over fix plan 5.5). Letters are display only and are not restored.
"""
import hashlib
import pathlib
from dataclasses import dataclass

from wholecount.engine.outputs.audit_entry import entry
from wholecount.session.keys import normalize_file_name
from wholecount.session.store import apply_setup_json, decision_from_json


@dataclass(frozen=True)
class ResumePlan:
    restored: tuple
    changed: tuple
    missing: tuple
    extra: tuple
    kept: int
    lapsed: int
    lapsed_list: tuple                    # (decision ID, reason)


def fingerprint(path):
    return hashlib.sha256(pathlib.Path(path).read_bytes()).hexdigest()


def plan_files(saved_sources, added_paths):
    saved_fp = {s["fingerprint"]: s for s in saved_sources}
    saved_name = {s["normalized"]: s for s in saved_sources}
    restored, changed, extra, seen = [], [], [], set()
    for p in added_paths:
        fp = fingerprint(p)
        name = pathlib.Path(p).name
        if fp in saved_fp:
            restored.append(name)
            seen.add(saved_fp[fp]["normalized"])
        elif normalize_file_name(name) in saved_name:
            changed.append(name)
            seen.add(normalize_file_name(name))
        else:
            extra.append(name)
    missing = [s["file_name"] for s in saved_sources if s["normalized"] not in seen]
    return tuple(restored), tuple(changed), tuple(missing), tuple(extra)


def resume(session, saved, added_paths):
    """Restore the set-up and decisions into a fresh session for these files, process, and report the plan (STORE-7)."""
    from wholecount.session.runner import process

    apply_setup_json(session.setup, saved["setup"])
    session.setup.sections["sources"] = {str(p): True for p in added_paths}
    session.decisions.add([decision_from_json(d) for d in saved["decisions"]])
    restored, changed, missing, extra = plan_files(saved.get("sources", ()), added_paths)
    session.log(entry("RESUME", count=len(saved["decisions"]), reviewer=session.reviewer or None))
    results = process(session)
    return ResumePlan(restored, changed, missing, extra, results.kept, results.lapsed,
                      tuple((n.decision.decision_id, n.reason) for n in results.no_longer_apply))
