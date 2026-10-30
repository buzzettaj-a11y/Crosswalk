from invariants import *
import json
raw = open("/dev/stdin").read() if False else None
exec(open("/tmp/claude-0/-home-claude/ec68250d-d5ac-549e-8d94-20759c381437/scratchpad/audit/C-scripts/s28_blank_rows.py").read().split("t = tables()")[0])
s = ui("sources")["sources"]
print(json.dumps({k: v for k, v in s.items() if k != "tables"}, indent=1)[:600])
for t in s["tables"]:
    print({k: t[k] for k in t if k in ("key", "rows", "included", "kind", "note", "warn", "why", "headerWrong", "headerWhy", "state")})
print("express check:", client.get("/api/express/check").json())
