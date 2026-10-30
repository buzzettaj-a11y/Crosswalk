"""
s15: save progress, restart, resume. Counts, decisions, exports identical? Changed source file?
A server restart is simulated by rebinding cw.S to a blank state WITHOUT calling /api/reset
(reset deletes the saved session by design).
"""
from invariants import *
import messy, re, hashlib, json, glob
import pandas as pd

H = ["Client_ID", "First_Name", "Last_Name", "DOB", "Address", "City", "State", "Zip", "Program"]
D = pd.DataFrame([["D1", "Zoe", "Quill", "1990-01-01", "1 Q St", "New York", "NY", "10013", "Workforce Development"],
                  ["D2", "Moe", "Lang", "1980-03-03", "3 L St", "New York", "NY", "10013", "Youth"]], columns=H).to_csv(index=False).encode()
E = pd.DataFrame([["E1", "Zoe", "Quill", "1990-01-01", "99 R St", "Brooklyn", "NY", "11201", "Workforce Dev."],
                  ["E2", "Moe", "Lang", "1980-03-03", "3 L St", "New York", "NY", "10013", "youth"]], columns=H).to_csv(index=False).encode()
files = dict(messy.make()); files["D.csv"] = D; files["E.csv"] = E


def mask(b):
    s = b.decode("utf-8", "replace")
    s = re.sub(r"Generated \(UTC\): [0-9T:\-+]+", "Generated (UTC): <T>", s)
    s = re.sub(r"Recorded \d{4}-\d\d-\d\d \d\d:\d\d:\d\d", "Recorded <T>", s)
    return s.encode()


def dump():
    return {k: hashlib.sha256(mask(export_raw(k))).hexdigest()[:10] for k in EXPORTS}


# ---------------- original session ----------------
reset(); upload(files); set_schema(dob=True)
ui("programs")                                  # builds the grouping proposal
# the operator confirms the grouping by applying it (UI sends the whole set-up)
pg = ui("programs")["programs"]
client.post("/api/programs/apply", json={"columns": [], "groups": [
    {"canonical": g["canonical"], "names": [v["name"] for v in g["variants"]]} for g in pg["groups"]]})
run()
decide("dupc", "aside"); decide("idconflict", "accept_all"); decide("zipbad", "sent")
rid = queue("pending")["items"][0]["rid"]
client.post("/api/queue/action", json={"rid": rid, "action": "approved"})
props = client.get("/api/identity/proposals").json()["items"]
print("open proposals:", len(props))
for p in props:                                 # the operator says Zoe Quill is one person
    client.post("/api/identity/decide", json={"a": p["pair"][0], "b": p["pair"][1], "verdict": "same"})
orig_counts = counts_line(True)
orig_files = dump()
sid = cw.S["session_id"]
sess = json.load(open(ROOT + f"/sessions/{sid}.json"))
print("session id:", sid, "| keys saved:", sorted(sess["state"].keys()))
print("original:", orig_counts)
print("   actions:", len(cw.S["actions"]), "| id_decisions:", len(cw.S["id_decisions"]),
      "| program_groups:", len(cw.S["program_groups"] or []), "| program_aliases:", len(cw.S["program_aliases"]))

# ---------------- restart + resume ----------------
cw.S = cw._blank_state(); cw._forget_prepared()
r = client.post("/api/sessions/resume", json={"id": sid}).json()
print("\nresume ->", r)
print("   actions:", len(cw.S["actions"]), "| id_decisions:", len(cw.S["id_decisions"]),
      "| program_groups:", cw.S["program_groups"], "| program_aliases:", len(cw.S["program_aliases"]))

# the operator adds the same files again and processes
upload(files)
print("   after re-adding files: schema kept:", bool(cw.S["schema"]), "| ops:", len(cw.S["ops"]), "| tables:", len(cw.S["tables"]))
run()
print("   actions after Process:", len(cw.S["actions"]))
print("resumed :", counts_line(True))
now = dump()
for k in EXPORTS:
    print(f"   {EXPORTS[k]:<28} identical to original = {now[k] == orig_files[k]}")
print("   open proposals now:", len(client.get('/api/identity/proposals').json()["items"]))
print("   groups now:", [(g["id"], g["count"], g["status"]) for g in groups()])
