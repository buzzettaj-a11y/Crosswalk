"""
s10: re-running Process does not invalidate the cached identity result (S['identity']), so Goal 1 and
Goal 2 keep describing the previous run. Also the Unique_Clients exports.
Sequence: run, open Results (identity is computed and cached), exclude a file, run again, open Results.
"""
from invariants import *
import messy

setup_standard(messy.make(), dob=True)
print("A. first run         :", counts_line())
tbs = tables()
target = [t for t in tbs if t["file"] == "C.csv"][0]
client.post("/api/sources/include", json={"key": target["key"], "on": False})
run()
print("B. C.csv excluded + Process again (before opening Results):")
print("   rows:", summary()["rows"])
print("   ", counts_line())
snap, fails = report("B")
fresh = None
# what a fresh computation gives for the same state
cw.S["identity"] = None
print("C. same state, identity recomputed from scratch:", counts_line())
