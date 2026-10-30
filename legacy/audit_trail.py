"""
The audit trail, complete.

Three things change a row and all three must be traceable afterward without
opening the client data:

  the set-up that shaped the run: which files, which header rows, which
  tidy-up steps, how columns were matched, how programs were grouped, what
  counted as a duplicate;

  what the engine did to each row, by file, row number and identifier: every
  fix, fill, split, default and check;

  what a person decided: every group decision, row decision, fill approved,
  duplicate confirmed, and the rows each one touched, by identifier.

The trail carries identifiers and column names only, never a name, address
or value, so it can be read and shared safely. It is available on screen
during the session and as the Secure_Audit_Log file.
"""
from __future__ import annotations

import time
from collections import Counter


def configuration_lines(S, engine, describe_op, guess_for, included_keys):
    """The set-up of the run, as it stood when it was processed."""
    out = ["== Set-up ==",
           f"Recorded {time.strftime('%Y-%m-%d %H:%M:%S')}"]
    files = sorted(S["uploads"])
    out.append(f"Files loaded: {len(files)}")
    for f in files:
        out.append(f"  {f}")
    for tb in S["tables"]:
        k = tb["key"]
        inc = "included" if S["included"].get(k) else "not included"
        hr = S["header_row"].get(k)
        out.append(f"Table {k}: {inc}, {tb['rows']:,} rows"
                   + (f", header row {hr}" if hr is not None else ""))
    schema = S.get("schema")
    if schema:
        out.append("Columns set up: " + ", ".join(
            f"{f['label']}({f['dtype']}{', required' if f.get('required') else ''})"
            for f in schema))
    else:
        out.append("Columns set up: the standard set")
    ops = [o for o in S["ops"] if not o.get("removed")]
    out.append(f"Tidy-up steps in force: {len(ops)}")
    for o in ops:
        out.append(f"  [{o['origin']}] {o['table'].split(' :: ')[0]}: {describe_op(o['op'])}")
    for k in included_keys():
        mapping, _cols = guess_for(k)
        pairs = ", ".join(f"{role}<-{col}" for role, col in mapping.items() if col)
        out.append(f"Matching for {k.split(' :: ')[0]}: {pairs}")
    for k, vals in (S.get("source_defaults") or {}).items():
        if vals:
            out.append(f"Defaults for {k.split(' :: ')[0]}: "
                       + ", ".join(f"{r}={v}" for r, v in vals.items()))
    groups = S.get("program_groups") or []
    if groups:
        out.append("Program names grouped:")
        for g in groups:
            names = [v["name"] for v in g["variants"]]
            if len(names) > 1 or names[0] != g["canonical"]:
                out.append(f"  {g['canonical']} <- {', '.join(names)}")
    out.append(f"Duplicate within a file means the same: {', '.join(S.get('dup_fields') or [])}")
    st = S.get("settings") or {}
    out.append(f"Settings: geocode required={st.get('require_geocode')}, "
               f"jitter={st.get('jitter')}, seed={st.get('seed')}")
    return out


def decision_lines(S, rid_index):
    """Every decision a person made, with the rows it touched by identifier."""
    out = ["== Decisions by the reviewer =="]
    if not S["actions"]:
        out.append("(none yet)")
        return out
    for i, act in enumerate(S["actions"], start=1):
        if act["type"] == "group":
            n = len(act.get("rids", []))
            out.append(f"{i}. Group '{act['gid']}': {act['decision']} "
                       f"({n:,} rows{': ' + act['outcome'] if act.get('outcome') else ''})")
            for rid in act.get("rids", [])[:2000]:
                rec = rid_index.get(rid)
                ident = rec.get("Client_ID", "") if rec else ""
                out.append(f"     {rid}{' id ' + ident if ident else ''}")
            if n > 2000:
                out.append(f"     ... and {n - 2000:,} more")
        elif act["type"] == "row":
            rec = rid_index.get(act["rid"])
            ident = rec.get("Client_ID", "") if rec else ""
            note = f" ({act['note']})" if act.get("note") else ""
            out.append(f"{i}. Row {act['rid']}{' id ' + ident if ident else ''}: "
                       f"{act['status']}{note}")
        else:
            out.append(f"{i}. {act}")
    return out


def dedupe_lines(S):
    """The duplicate decisions within each file, summarized for the trail."""
    out = []
    dec = S.get("dup_decisions") or {}
    total = sum(len(v) for v in dec.values())
    if not total:
        return out
    out.append("== Duplicates within a file, as decided ==")
    for table, groups in dec.items():
        c = Counter(groups.values())
        out.append(f"{table.split(' :: ')[0]}: "
                   + ", ".join(f"{n} group(s) {v}" for v, n in c.items()))
    return out


def full_text(S, engine, describe_op, guess_for, included_keys, rid_index):
    """The whole trail as plain text: set-up, engine changes, decisions."""
    parts = configuration_lines(S, engine, describe_op, guess_for, included_keys)
    parts.append("")
    res = S.get("results")
    if res:
        parts.append("== Changes made while processing, by row ==")
        parts.append("(file, row, identifier, what was done; column names only)")
        parts.append(res["audit"].as_secure_text())
    else:
        parts.append("== Changes made while processing ==")
        parts.append("(not processed yet)")
    parts.append("")
    parts.extend(dedupe_lines(S))
    parts.append("")
    parts.extend(decision_lines(S, rid_index))
    return "\n".join(parts)


def entries(S, engine, guess_for, included_keys, rid_index, query="", source="",
            kind="", page=0, per=100):
    """
    The trail as a list for the screen: one entry per line, filterable by
    source file, kind (set-up, engine, decision) and text. Newest decisions
    first, engine entries in row order.
    """
    items = []
    for line in configuration_lines(S, engine, engine.describe_op, guess_for, included_keys)[2:]:
        items.append({"kind": "set-up", "source": "", "text": line.strip()})
    res = S.get("results")
    if res:
        for e in res["audit"].entries:
            items.append({"kind": "engine",
                          "source": str(e.get("source_file", "")).split(" :: ")[0],
                          "row": e.get("row_idx"), "id": e.get("client_id", ""),
                          "text": e.get("message", "")})
    for line in dedupe_lines(S)[1:]:
        items.append({"kind": "decision", "source": line.split(":")[0], "text": line})
    for line in reversed(decision_lines(S, rid_index)[1:]):
        if line.startswith("     "):
            continue
        items.append({"kind": "decision", "source": "", "text": line.strip()})
    if source:
        items = [i for i in items if not i.get("source") or i["source"] == source]
    if kind:
        items = [i for i in items if i["kind"] == kind]
    if query:
        q = query.lower()
        items = [i for i in items if q in i["text"].lower()
                 or q in str(i.get("id", "")).lower()]
    total = len(items)
    per = max(1, min(int(per), 500))
    pages = max(1, (total + per - 1) // per)
    page = max(0, min(int(page), pages - 1))
    counts = Counter(i["kind"] for i in items)
    return {"total": total, "page": page, "pages": pages, "per": per,
            "counts": dict(counts),
            "items": items[page * per:(page + 1) * per]}
