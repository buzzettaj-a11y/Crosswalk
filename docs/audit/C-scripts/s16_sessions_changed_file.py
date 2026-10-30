"""
s16: a within-file duplicate decision 'keep row N' (copies:N) is a row NUMBER. Save, restart, resume
with the source file changed (one client added at the top): the decision silently flips.
Also: a new real person who matches an already-decided group is set aside with no one looking.
"""
from invariants import *
import messy, io, json
import pandas as pd

files = messy.make()
reset(); upload(files); set_schema(dob=True); run()
dp = client.get("/api/ui?screen=review").json()["dupes"]
grp = None
for t in dp["tables"]:
    for g in t["groups"]:
        ids = [r["values"].get("Client_ID") for r in g["rows"]]
        if "A950" in ids:
            grp, tab = g, t["table"]
print("group:", [(r["row"], r["values"]["Client_ID"]) for r in grp["rows"]], "on table", tab)
keep_row = [r["row"] for r in grp["rows"] if r["values"]["Client_ID"] == "A950"][0]
verdict = f"copies:{keep_row}"
client.post("/api/prepare/dupes/decide", json={"decisions": [{"table": tab, "gid": grp["gid"], "decision": verdict}]})
clean = export_df("clean"); aside = export_df("review")
def status(cid):
    c = set(clean["Client_ID"]); r = export_df("review")
    rr = r[r["orig::Client_ID"] == cid]
    return "clean" if cid in set(export_df("clean")["Client_ID"]) else ("review/aside: " + ", ".join(rr["Resolution_Status"]) if len(rr) else "?")
print(f"decision {verdict}: A950 ->", status("A950"), "| A005 ->", status("A005"))
sid = cw.S["session_id"]

# restart + resume. Variant 1: the source system is re-exported with one new client at the top (table range changes)
# Variant 2 (used below): same rows, same count, re-exported sorted by name instead of by ID
a = pd.read_csv(io.BytesIO(files["A.csv"]), dtype=str, keep_default_na=False)
new = pd.DataFrame([["A777", "Newly", "Added", "2001-01-01", "9 New St", "Bronx", "NY", "10451", "Youth"]], columns=a.columns)
VARIANT = int(os.environ.get("VARIANT", "2"))
files2 = dict(files)
if VARIANT == 1:
    files2["A.csv"] = pd.concat([new, a], ignore_index=True).to_csv(index=False).encode()
else:
    files2["A.csv"] = a.sort_values(["Last_Name", "First_Name", "Client_ID"], kind="stable").to_csv(index=False).encode()
cw.S = cw._blank_state(); cw._forget_prepared()
print("resume ->", client.post("/api/sessions/resume", json={"id": sid}).json())
print("dup_decisions restored:", cw.S["dup_decisions"])
upload(files2); run()
dp2 = client.get("/api/ui?screen=review").json()["dupes"]
for t in dp2["tables"]:
    for g in t["groups"]:
        ids = [r["values"].get("Client_ID") for r in g["rows"]]
        if "A950" in ids:
            print("same group now shows rows:", [(r["row"], r["values"]["Client_ID"]) for r in g["rows"]], "| decision:", g["decision"])
print("after changed file:  A950 ->", status("A950"), "| A005 ->", status("A005"))
print("(the reviewer chose to keep A950's row and set A005 aside; the opposite happened)")
