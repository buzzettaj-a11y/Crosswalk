"""Claim: 'a reviewer can't type a new value into a cell' / 'Values are never edited here one by one'."""
import os, sys, csv, io
HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, HERE)
import a_lib
work = sys.argv[1]
FIX = os.path.join(os.path.dirname(HERE), "A-fixtures")
cw, c = a_lib.boot(work)
c.post("/api/reset")
a_lib.upload(c, [os.path.join(FIX, "household.csv")])
a_lib.relax_client_id(c); a_lib.fix_mapping(c); a_lib.run(c)
for g in a_lib.review(c)["groups"]:
    print("send group", g["id"], c.post("/api/review/group", json={"gid": g["id"], "decision": g["a"]["k"]}).json())
q = c.get("/api/queue?filter=pending&page=0&sel=0").json()
print("queue total", q["total"])
print("fields the screen offers for 'Set a field on all selected':", q["fields"])
d = q["detail"]; print("row in the queue:", d["rid"], "|", d.get("reason") or d.get("errors"))
# type a brand-new ZIP and a brand-new last name into the one row with a missing ZIP
rid = "household.csv :: A1:H5||3"     # the Zed Nobody row, missing a ZIP
r = c.post("/api/queue/action", json={"rid": rid, "action": "corrected", "edits": {"Zip": "11201", "Last_Name": "Somebodyelse"}}).json()
print("typed Zip=11201 and Last_Name=Somebodyelse ->", r)
clean = list(csv.DictReader(io.StringIO(a_lib.download(c, "clean").decode())))
for row in clean:
    print("clean row:", row["Client_ID"], row["First_Name"], row["Last_Name"], row["Zip"], "|", row["Resolution_Status"])
