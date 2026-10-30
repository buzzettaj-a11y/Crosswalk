from cwlib import *
import traceback, importlib
exec(open('/tmp/claude-0/-home-claude/ec68250d-d5ac-549e-8d94-20759c381437/scratchpad/audit/C-scripts/s14_jitter.py').read().split("def coords")[0])
reset(); upload({"G.csv": data}); set_schema(dob=True)
cw.S["settings"].update({"require_geocode": False, "jitter": True, "seed": 1337})
try:
    cw._execute_pipeline()
    print("OK, no crash")
except Exception:
    traceback.print_exc()
