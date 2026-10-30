"""Claims: saved progress keeps your decisions; 'Preview' decides nothing; closing keeps your progress."""
import os, sys, json
HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, HERE)
import a_lib
work = sys.argv[1]
cw, c = a_lib.boot(work)
SAMPLES = [os.path.join(work, "sample_data", n) for n in
           ["clinic_export.csv", "portal_export.json", "legacy_export.xlsx", "state_export.xml", "partner_export.tsv"]]

def setup_and_run():
    a_lib.upload(c, SAMPLES)
    a_lib.relax_client_id(c)
    a_lib.fix_mapping(c)
    return a_lib.run(c)

c.post("/api/reset")
setup_and_run()
rv = a_lib.review(c)
print("groups:", [(g["id"], g["count"]) for g in rv["groups"]])
decs = [{"gid": g["id"], "decision": ("accept_all" if g["id"] not in ("summary", "duprule") else g["a"]["k"])} for g in rv["groups"]]
c.post("/api/review/decide-many", json={"decisions": decs})
s0 = a_lib.summary(c)
print("BEFORE preview: actions =", len(cw.S["actions"]), "| rows", s0["rows"], "| goal1", s0["goal1"]["count"], "goal2", s0["goal2"]["count"])
print("   review tallies:", a_lib.review(c)["tallies"])

print("--- T1: press 'Preview the counts' on the Programs stage")
r = c.post("/api/programs/preview"); print("   HTTP", r.status_code)
print("AFTER  preview: actions =", len(cw.S["actions"]), "| tallies:", a_lib.review(c)["tallies"])
s1 = a_lib.summary(c)
print("   rows", s1["rows"], "| goal1", s1["goal1"]["count"], "goal2", s1["goal2"]["count"])

print("--- T2: decisions, program grouping, then close and resume")
# re-decide (preview wiped them)
rv = a_lib.review(c)
decs = [{"gid": g["id"], "decision": ("accept_all" if g["id"] not in ("summary", "duprule") else g["a"]["k"])} for g in rv["groups"]]
c.post("/api/review/decide-many", json={"decisions": decs})
p = c.get("/api/identity/proposals?page=0&per=50").json()
for it in p["items"][:6]:
    c.post("/api/identity/decide", json={"a": it["pair"][0], "b": it["pair"][1], "verdict": "same"})
pg = c.get("/api/ui?screen=programs").json()["programs"]
groups = pg["groups"]
# merge two program names by hand
if len(groups) >= 2:
    c.post("/api/programs/group", json={"name": groups[1]["canonical"], "into": groups[0]["canonical"]})
sid = cw.S["session_id"]
print("   session id", sid, "| id_decisions", len(cw.S["id_decisions"]), "| program_aliases", len(cw.S["program_aliases"]),
      "| actions", len(cw.S["actions"]))
s2 = a_lib.summary(c)
print("   BEFORE close: goal1", s2["goal1"], "goal2", s2["goal2"]["count"])
# now 'close the window and come back': the saved file is all that survives
saved = json.load(open(cw.sessions_store.path_for(sid)))
print("   keys in the saved file:", sorted(saved["state"].keys()))
print("   saved file has id_decisions:", "id_decisions" in saved["state"], "| program_groups:", "program_groups" in saved["state"],
      "| program_aliases:", "program_aliases" in saved["state"])
r = c.post("/api/sessions/resume", json={"id": sid}).json()
print("   resume said:", r)
print("   after resume: id_decisions", len(cw.S["id_decisions"]), "| program_aliases", len(cw.S["program_aliases"]), "| actions", len(cw.S["actions"]))
a_lib.upload(c, SAMPLES)
print("   files back; actions still", len(cw.S["actions"]))
a_lib.fix_mapping(c)
st = a_lib.run(c)
print("   after Process: actions", len(cw.S["actions"]), "| queue_edits", len(cw.S["queue_edits"]))
s3 = a_lib.summary(c)
print("   AFTER resume + Process: rows", s3["rows"], "goal1", s3["goal1"], "goal2", s3["goal2"]["count"])
