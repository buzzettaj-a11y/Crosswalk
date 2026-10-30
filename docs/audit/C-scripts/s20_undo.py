"""
s20: undo semantics. Spec: 'every decision is an action; undo is a pop'.
Code: /api/review/undo pops the last GROUP decision only, skips row actions, and does not refresh identity.
"""
from invariants import *
import messy

setup_standard(messy.make(), dob=True)
base = counts_line(True)
print("baseline:", base)

# A: group decision sends zipbad rows to the queue; B: a row decision approves one of them
decide("zipbad", "sent")
rid = queue("pending")["items"][0]["rid"]
client.post("/api/queue/action", json={"rid": rid, "action": "approved"})
print("after group 'sent' + row 'approved':", counts_line(True))
print("   actions:", [(a["type"], a.get("gid") or a.get("rid"), a.get("decision") or a.get("status")) for a in cw.S["actions"]])
r = client.post("/api/review/undo").json()
print("undo ->", r)
print("   actions left:", [(a["type"], a.get("gid") or a.get("rid"), a.get("decision") or a.get("status")) for a in cw.S["actions"]])
print("   summary (cached identity):", counts_line())
print("   summary (fresh identity)  :", counts_line(True))
g = {x["id"]: x for x in groups()}
print("   zipbad group status:", g["zipbad"]["status"], "| row", rid, "status now:", [i["status"] for i in queue("all")["items"] if i["rid"] == rid])
print("   -> the group decision is undone but the row it created is still approved and counted")

# undo with nothing but row actions
reset(); upload(messy.make()); set_schema(dob=True); run()
decide("zipbad", "sent"); rid = queue("pending")["items"][0]["rid"]
client.post("/api/queue/action", json={"rid": rid, "action": "approved"})
client.post("/api/review/undo")   # removes the group decision
r = client.post("/api/review/undo").json()
print("\nsecond undo with only a row action left ->", r, "(the approved row cannot be undone through Undo)")
