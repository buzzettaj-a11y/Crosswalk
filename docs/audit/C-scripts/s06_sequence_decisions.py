"""
s06: reconciliation and numbers after each review action, plus undo after each.
Checks every step with invariants.report (screen vs exports vs raw frames).
"""
from invariants import *
import messy

setup_standard(messy.make(), dob=True)
report("0 run")

def gmap():
    return {g["id"]: g for g in groups()}

# 1. accept_all on idconflict (two rows from different files, same ID) -----------------------------
decide("idconflict", "accept_all")
report("1 idconflict accept_all")
client.post("/api/review/undo")
snap_after_undo, f = report("1u undo (idconflict accept_all)")

# 2. dupc aside ("keep one of each")
decide("dupc", "aside")
report("2 dupc aside")
client.post("/api/review/undo")
report("2u undo dupc aside")

# 3. group sent -> rows to queue, then approve/reject/remove single rows
decide("zipbad", "sent"); decide("zipcity", "sent"); decide("noaddr", "sent"); decide("conflict", "sent")
report("3 four groups sent to queue")
q = queue("pending")
rids = [i["rid"] for i in q["items"]]
print("   queue pending rids:", rids)
client.post("/api/queue/action", json={"rid": rids[0], "action": "approved"})
report("3a approve one")
client.post("/api/queue/action", json={"rid": rids[1], "action": "rejected"})
report("3b reject one")
client.post("/api/queue/action", json={"rid": rids[2], "action": "removed"})
report("3c remove (set aside) one")
r = client.post("/api/queue/bulk", json={"all_matching": True, "action": "approved", "filter": "pending"}).json()
print("   bulk approve all matching ->", r)
report("3d bulk approve all pending")
r = client.post("/api/queue/bulk", json={"all_matching": True, "action": "removed", "filter": "approved"}).json()
print("   bulk remove all approved ->", r)
report("3e bulk set aside all approved")
r = client.post("/api/queue/bulk", json={"all_matching": True, "action": "pending", "filter": "all"}).json()
print("   bulk back to pending (all) ->", r)
report("3f bulk back to pending")

# 4. keep one per program
r = client.post("/api/queue/keep-one-per-program").json()
print("   keep one per program ->", r)
report("4 keep one per program")
q = queue("all")
print("   queue counts after keep-one-per-program:", q["counts"])
