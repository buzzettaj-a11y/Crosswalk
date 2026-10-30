"""s26: is a person's 'same person' / 'different people' verdict written to the audit trail?"""
from invariants import *
import glob
sample = {os.path.basename(p): open(p, "rb").read() for p in sorted(glob.glob(ROOT + "/sample_data/*"))}
setup_standard(sample, dob=False)
props = client.get("/api/identity/proposals?per=50").json()["items"]
before = export_raw("audit").decode()
print("open proposals:", len(props), "| Goal 1 range:", counts_line().split("|")[0])
client.post("/api/identity/decide", json={"a": props[0]["pair"][0], "b": props[0]["pair"][1], "verdict": "same"})
client.post("/api/identity/decide", json={"a": props[1]["pair"][0], "b": props[1]["pair"][1], "verdict": "different"})
after = export_raw("audit").decode()
print("after one 'same' and one 'different':", counts_line(True).split("|")[0])
print("audit lines before/after:", len(before.splitlines()), len(after.splitlines()), "| identical text apart from timestamps:",
      [l for l in before.splitlines() if "Recorded" not in l and "Generated" not in l] == [l for l in after.splitlines() if "Recorded" not in l and "Generated" not in l])
print("lines mentioning the two rows:", [l[:100] for l in after.splitlines() if props[0]["pair"][0].split("||")[1] in l and "Decision" in l][:3])
a = client.get("/api/audit?kind=decision&per=200").json() if client.get("/api/audit?kind=decision").status_code == 200 else {}
print("GET /api/audit?kind=decision items:", len(a.get("items", [])) if a else "n/a", "| any mention of identity:", any("person" in i["text"].lower() or "same" in i["text"].lower() for i in a.get("items", [])))
