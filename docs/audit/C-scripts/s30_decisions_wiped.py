"""s30: which routine actions silently throw away review decisions."""
from invariants import *
import messy

def fresh():
    setup_standard(messy.make(), dob=True)
    decide("dupc", "aside"); decide("idconflict", "accept_all"); decide("zipbad", "sent")
    rid = queue("pending")["items"][0]["rid"]; client.post("/api/queue/action", json={"rid": rid, "action": "approved"})
    return len(cw.S["actions"])

n = fresh(); print("decisions held:", n, "|", counts_line(True))
r = client.post("/api/programs/preview", json={}).json()
print("1. Programs screen: Preview ->", r.get("ok"), "| decisions now:", len(cw.S["actions"]), "|", counts_line(True))

n = fresh(); print("\ndecisions held:", n)
run()
print("2. Process again with no change at all -> decisions now:", len(cw.S["actions"]), "|", counts_line(True))
print("   audit 'Decisions' lines:", sum(1 for l in export_raw("audit").decode().splitlines() if "approved" in l or "set aside" in l or "sent" in l))

n = fresh(); print("\ndecisions held:", n)
r = client.post("/api/express/run", json={"despite_warnings": True}).json(); wait_run()
print("3. Fast path again ->", r.get("ok"), "| decisions now:", len(cw.S["actions"]))
