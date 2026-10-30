"""Drive a full Crosswalk session through the server for the disk-write check.

usage: python a01_disk_session.py WORKDIR OUTDIR
Everything the session downloads is saved under OUTDIR (outside the app folder).
"""
import os, sys, json, time
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import a_lib

work, out = sys.argv[1], sys.argv[2]
os.makedirs(out, exist_ok=True)
FIX = os.path.join(os.path.dirname(HERE), "A-fixtures")
cw, c = a_lib.boot(work)

c.post("/api/reset")
files = [os.path.join(work, "sample_data", n) for n in
         ["clinic_export.csv", "portal_export.json", "legacy_export.xlsx",
          "state_export.xml", "partner_export.tsv"]]
files.append(os.path.join(FIX, "canary_clients.csv"))
print("upload", a_lib.upload(c, files).status_code)

dob = {"role": "custom", "label": "DOB", "dtype": "date", "length": 0, "required": False}
a_lib.relax_client_id(c, [dob])
m = a_lib.fix_mapping(c)
print("blocked", m["blocked"])
# make sure the canary DOB column is matched
for t in m["tables"]:
    if "canary" in t["key"]:
        c.post("/api/map", json={"table": t["key"], "field": "DOB", "column": "DOB"})
# program preview (stage 5), as a user would
print("preview", c.post("/api/programs/preview").status_code)
st = a_lib.run(c)
print("run", st["state"])
rd = a_lib.runstate(c)["results"]
print("run counts", {k: rd[k] for k in ("input", "clean", "review")})

# review: decide groups
rv = a_lib.review(c)
for g in rv["groups"]:
    print("group", g["id"], g["count"])
    if g["id"] in ("zipbad", "zipcity", "cityunknown", "missing"):
        # batch ZIP look-up
        fp = c.get(f"/api/fill/preview?gid={g['id']}").json()
        print("  fill preview", fp["fillable"], fp["stuck"])
        if fp["fillable"]:
            print("  fill apply", c.post("/api/fill/apply", json={"gid": g["id"]}).json())
rv = a_lib.review(c)
decisions = []
for i, g in enumerate(rv["groups"]):
    d = g["a"]["k"] if i % 2 == 0 else "accept_all"
    if g["id"] in ("summary", "duprule"):
        d = g["a"]["k"]
    decisions.append({"gid": g["id"], "decision": d})
print("decide-many", c.post("/api/review/decide-many", json={"decisions": decisions}).json())

q = c.get("/api/queue?filter=pending&page=0&sel=0").json()
print("queue total", q["total"])
if q["detail"]:
    rid = q["detail"]["rid"]
    print("approve", c.post("/api/queue/action", json={"rid": rid, "action": "approved"}).json())
q = c.get("/api/queue?filter=pending&page=0&sel=0").json()
if q["detail"]:
    rid = q["detail"]["rid"]
    print("typed correction", c.post("/api/queue/action", json={"rid": rid, "action": "corrected",
          "edits": {"City": "Brooklyn", "Zip": "11201"}}).json())
q = c.get("/api/queue?filter=pending&page=0&sel=0").json()
if q["detail"]:
    print("leave for later", c.post("/api/queue/action", json={"rid": q["detail"]["rid"], "action": "rejected"}).json())
q = c.get("/api/queue?filter=pending&page=0&sel=0").json()
if q["detail"]:
    print("set aside", c.post("/api/queue/action", json={"rid": q["detail"]["rid"], "action": "removed"}).json())

# duplicates within a file: decide the first group of every table as copies
dp = c.get("/api/ui?screen=review").json()["dupes"]
dd = []
for t in dp["tables"]:
    for g in t["groups"][:2]:
        dd.append({"table": t["table"], "gid": g["gid"], "decision": "copies"})
print("dupe decide", len(dd), c.post("/api/prepare/dupes/decide", json={"decisions": dd}).json())

# results: decide a few open pairs
p = c.get("/api/identity/proposals?page=0&per=8").json()
print("open proposals", p["total"])
for i, it in enumerate(p["items"][:4]):
    c.post("/api/identity/decide", json={"a": it["pair"][0], "b": it["pair"][1],
                                         "verdict": "same" if i % 2 == 0 else "different"})
s = a_lib.summary(c)
print("goal1", s["goal1"], "goal2", s["goal2"]["count"], s["rows"])

# explicit save progress, set-up
print("sessions", c.get("/api/sessions").json()["current"])
print("save setup", c.post("/api/setups/save", json={"name": "Audit Run", "note": "disk check"}).json())

# every export
for which, name in [("clean", "Final_Clean_Mapped"), ("review", "Manual_Review_Needed"),
                    ("aside", "Set_Aside_Records"), ("unique_clients", "Unique_Clients"),
                    ("unique_by_program", "Unique_Clients_By_Program"),
                    ("audit", "Secure_Audit_Log.txt"), ("quality", "Data_Quality_Report.csv")]:
    data = a_lib.download(c, which)
    ext = "" if "." in name else ".csv"
    with open(os.path.join(out, name + ext), "wb") as fh:
        fh.write(data)
    print("downloaded", name, len(data))
html = c.get("/api/summary").text
open(os.path.join(out, "printable_summary.html"), "w", encoding="utf-8").write(html)
open(os.path.join(out, "audit_api_text.txt"), "w", encoding="utf-8").write(c.get("/api/audit/text").text)
print("done")
