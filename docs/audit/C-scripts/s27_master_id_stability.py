"""s27: is a Master_ID stable when one unrelated decision is made?"""
from invariants import *
import glob
sample = {os.path.basename(p): open(p, "rb").read() for p in sorted(glob.glob(ROOT + "/sample_data/*"))}
setup_standard(sample, dob=False)
u0 = export_df("unique_clients")
m0 = {}
for m, rows in zip(u0["Master_ID"], u0["Source_Rows"]):
    for rid in rows.split("; "):
        m0[rid] = m
props = client.get("/api/identity/proposals?per=50").json()["items"]
# decide the first open pair 'same'
client.post("/api/identity/decide", json={"a": props[0]["pair"][0], "b": props[0]["pair"][1], "verdict": "same"})
cw.S["identity"] = None
u1 = export_df("unique_clients")
m1 = {}
for m, rows in zip(u1["Master_ID"], u1["Source_Rows"]):
    for rid in rows.split("; "):
        m1[rid] = m
changed = [r for r in m0 if m0[r] != m1[r]]
print("rows:", len(m0), "| Master_ID of the same source row changed after ONE 'same' verdict:", len(changed), "rows")
for r in changed[:3]:
    print("   ", r, m0[r], "->", m1[r])
# and when the file order changes which row comes first
