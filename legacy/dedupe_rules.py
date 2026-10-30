"""
Duplicates within one file, by a rule the reviewer writes.

The processing run has its own duplicate check with a fixed key. This is
different: the reviewer says which fields make two rows the same, whether that
applies to one file or every file, and what to do about it. The rule is written
in schema terms, First_Name and Zip rather than column names, so one rule
covers files whose columns are named differently; it is resolved to each file's
columns through that file's matching.

Nothing is merged. Rows are either flagged and kept, or the first is kept and
the rest are set aside where a person can see them, exactly like the built-in
check.
"""
from __future__ import annotations

import re
from collections import defaultdict

import app as engine


def _norm(field, value):
    """The comparable form of a value for one field: case, spacing and
    punctuation are ignored, addresses use the tool's own normalization, and a
    ZIP is its first five digits."""
    s = engine.clean_cell(value)
    if not s:
        return ""
    if field in ("Address_1", "Address_2"):
        return engine._norm_addr(s)
    if field == "Zip":
        m = re.match(r"\d{5}", s.replace(" ", ""))
        return m.group(0) if m else s.lower()
    s = re.sub(r"[^\w]+", " ", s.lower())
    return re.sub(r"\s+", " ", s).strip()


def resolve_columns(rule_fields, mapping):
    """{field: column} for the fields this file has a column for, and the list
    of fields it does not."""
    cols, missing = {}, []
    for f in rule_fields:
        col = mapping.get(f, "")
        if col:
            cols[f] = col
        else:
            missing.append(f)
    return cols, missing


def find_groups(frame, cols):
    """
    Row indexes grouped by the rule's key. Only groups of two or more are
    returned. A row blank in any of the chosen fields cannot be matched and is
    never grouped, because two blanks are not evidence of anything.
    """
    groups = defaultdict(list)
    for idx, row in enumerate(frame.itertuples(index=False, name=None)):
        rowd = dict(zip(frame.columns, row))
        parts = []
        for field, col in cols.items():
            v = _norm(field, rowd.get(col, ""))
            if not v:
                parts = None
                break
            parts.append(v)
        if parts is None:
            continue
        groups["|".join(parts)].append(idx)
    return {k: v for k, v in groups.items() if len(v) > 1}


def apply_rule(frame, rule, mapping, label_prefix="F"):
    """
    Mark the frame in place according to one rule. Adds two working columns
    the processing run reads: __dup_in_file__ (the group label) on every row in
    a group, and __dup_drop__ on every row but the first when the rule says to
    keep the first. Returns what it found, for the screen.
    """
    cols, missing = resolve_columns(rule["fields"], mapping)
    if missing:
        return {"groups": 0, "rows": 0, "missing": missing, "applied": False}
    groups = find_groups(frame, cols)
    if "__dup_in_file__" not in frame.columns:
        frame["__dup_in_file__"] = ""
        frame["__dup_drop__"] = ""
        frame["__dup_fields__"] = ""
    n = 0
    fields_text = ", ".join(rule["fields"])
    for key, idxs in sorted(groups.items(), key=lambda kv: kv[1][0]):
        n += 1
        label = f"{label_prefix}{n}"
        for order, idx in enumerate(idxs):
            frame.iat[idx, frame.columns.get_loc("__dup_in_file__")] = label
            frame.iat[idx, frame.columns.get_loc("__dup_fields__")] = fields_text
            if rule.get("action") == "keep_first" and order > 0:
                frame.iat[idx, frame.columns.get_loc("__dup_drop__")] = \
                    f"copy of row {idxs[0]}"
    return {"groups": len(groups), "rows": sum(len(v) for v in groups.values()),
            "missing": [], "applied": True}


def group_id(key):
    """A stable name for a group, so a decision about it survives a re-read."""
    import hashlib
    return hashlib.sha1(key.encode("utf-8")).hexdigest()[:10]


def proposals(frame, fields, mapping, show_cols=None, limit=200):
    """
    Everything a person needs to review the duplicates a rule finds in one
    file: each group with its rows side by side, the fields they matched on,
    and the other fields that tell the rows apart.
    """
    cols, missing = resolve_columns(fields, mapping)
    if missing:
        return {"groups": [], "total_groups": 0, "total_rows": 0,
                "missing": missing}
    groups = find_groups(frame, cols)
    show = dict(cols)
    for role in (show_cols or ("Client_ID", "Address_1", "Address_2", "City",
                               "Zip", "Program")):
        c = mapping.get(role, "")
        if c and role not in show:
            show[role] = c
    out = []
    for key, idxs in sorted(groups.items(), key=lambda kv: (-len(kv[1]), kv[1][0]))[:limit]:
        rows = []
        for idx in idxs:
            rows.append({"row": idx + 1,
                         "values": {role: str(frame.iat[idx, frame.columns.get_loc(c)])
                                    for role, c in show.items()}})
        differing = [role for role in show
                     if role not in cols and
                     len({r["values"][role].strip().lower() for r in rows}) > 1]
        out.append({"gid": group_id(key), "rows": rows, "differing": differing})
    return {"groups": out, "total_groups": len(groups),
            "total_rows": sum(len(v) for v in groups.values()),
            "matched_on": list(cols), "shown": list(show), "missing": []}


def apply_decisions(frame, fields, mapping, decisions, label_prefix="F"):
    """
    Mark the frame according to what the reviewer decided about each group.

    A group confirmed as copies keeps its first row and sets the rest aside. A
    group the reviewer said holds different people is left entirely alone. A
    group nobody has looked at yet is flagged and kept, never removed: the tool
    does not process anything out that a person has not confirmed.
    """
    cols, missing = resolve_columns(fields, mapping)
    if missing:
        return {"confirmed": 0, "set_aside": 0, "flagged": 0, "missing": missing}
    groups = find_groups(frame, cols)
    # start clean every time: a decision changed since the last run must not
    # leave the previous run's marks behind
    for c in ("__dup_in_file__", "__dup_drop__", "__dup_fields__", "__dup_keep__"):
        frame[c] = ""
    fields_text = ", ".join(fields)
    confirmed = aside = flagged = 0
    n = 0
    for key, idxs in sorted(groups.items(), key=lambda kv: kv[1][0]):
        gid = group_id(key)
        decision = decisions.get(gid, "")
        # "copies:N" keeps row N (1-based, as shown) instead of the first
        keep_row = None
        if isinstance(decision, str) and decision.startswith("copies:"):
            try:
                keep_row = int(decision.split(":", 1)[1]) - 1
            except ValueError:
                keep_row = None
            decision = "copies"
        if decision == "keep":
            # different people by the reviewer's word; the built-in check must
            # not pair them again
            for idx in idxs:
                frame.iat[idx, frame.columns.get_loc("__dup_keep__")] = "1"
            continue
        n += 1
        label = f"{label_prefix}{n}"
        kept_idx = keep_row if keep_row in idxs else idxs[0]
        for order, idx in enumerate(idxs):
            frame.iat[idx, frame.columns.get_loc("__dup_in_file__")] = label
            frame.iat[idx, frame.columns.get_loc("__dup_fields__")] = fields_text
            if decision == "copies" and idx != kept_idx:
                frame.iat[idx, frame.columns.get_loc("__dup_drop__")] = \
                    f"copy of row {kept_idx + 1}"
                aside += 1
        if decision == "copies":
            confirmed += 1
        else:
            flagged += len(idxs)
    return {"confirmed": confirmed, "set_aside": aside, "flagged": flagged,
            "missing": []}


def preview(frame, rule, mapping):
    """What a rule would find on one file, without changing anything."""
    cols, missing = resolve_columns(rule["fields"], mapping)
    if missing:
        return {"groups": 0, "rows": 0, "missing": missing}
    groups = find_groups(frame, cols)
    sample = []
    for key, idxs in list(sorted(groups.items(), key=lambda kv: -len(kv[1])))[:3]:
        sample.append({"rows": len(idxs), "first_row": idxs[0] + 1,
                       "values": {f: str(frame.iat[idxs[0], frame.columns.get_loc(c)])
                                  for f, c in cols.items()}})
    return {"groups": len(groups), "rows": sum(len(v) for v in groups.values()),
            "missing": [], "sample": sample}
