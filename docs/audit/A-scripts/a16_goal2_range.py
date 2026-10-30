"""Claim: only the first count is a range while pairs are open; the second count is shown as a single number."""
import os, sys
HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, HERE)
import a_lib
work = sys.argv[1]
cw, c = a_lib.boot(work)
SAMPLES = [os.path.join(work, "sample_data", n) for n in
           ["clinic_export.csv", "portal_export.json", "legacy_export.xlsx", "state_export.xml", "partner_export.tsv"]]
def fresh():
    c.post("/api/reset"); a_lib.upload(c, SAMPLES); a_lib.relax_client_id(c); a_lib.fix_mapping(c); a_lib.run(c)
    for g in a_lib.review(c)["groups"]:
        c.post("/api/review/group", json={"gid": g["id"], "decision": "accept_all" if g["id"] not in ("summary", "duprule") else g["a"]["k"]})
for verdict in ("same", "different"):
    fresh()
    s = a_lib.summary(c)
    if verdict == "same":
        print("BEFORE deciding any open pair: goal1", s["goal1"], "| goal2 shown as one number:", s["goal2"]["count"], "| goal2 object keys:", sorted(s["goal2"]))
    a_lib.decide_all_proposals(c, verdict)
    s = a_lib.summary(c)
    print(f"AFTER every open pair is decided '{verdict}': goal1", s["goal1"], "| goal2", s["goal2"]["count"])
