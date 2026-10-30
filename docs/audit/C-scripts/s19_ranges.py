"""
s19: Goal 1 range with open proposals; Goal 2 has no range. Independent recomputation from the exports
and from /api/identity/proposals.
"""
from invariants import *
import glob


def independent(files, dob):
    setup_standard(files, dob=dob)
    s = summary()
    g1 = s["goal1"]
    # all open proposals (page through the API)
    props, page = [], 0
    while True:
        r = client.get(f"/api/identity/proposals?page={page}&per=50").json()
        props += r["items"]
        if page >= r["pages"] - 1:
            break
        page += 1
    uc = export_df("unique_clients")
    bp = export_df("unique_by_program")
    master_of = {}
    for m, rows in zip(uc["Master_ID"], uc["Source_Rows"]):
        for rid in rows.split("; "):
            master_of[rid] = m
    parent = {m: m for m in uc["Master_ID"]}
    def find(x):
        while parent[x] != x:
            parent[x] = parent[parent[x]]; x = parent[x]
        return x
    for p in props:
        a, b = find(master_of[p["pair"][0]]), find(master_of[p["pair"][1]])
        if a != b:
            parent[b] = a
    low_g1 = len({find(m) for m in uc["Master_ID"]})
    pairs = {(find(m), prog) for m, prog in zip(bp["Master_ID"], bp["Program"])}
    low_g2 = len(pairs)
    print(f"   open proposals: {len(props)}")
    print(f"   screen Goal 1: settled/high={g1['high']} low={g1['low']} | independent low={low_g1} -> {'OK' if low_g1 == g1['low'] else 'MISMATCH'}")
    print(f"   screen Goal 2: single number {s['goal2']['count']} (no range) | independent: high={len(bp)} low-if-all-accepted={low_g2}")
    print(f"   Goal 2 range that should be shown: {low_g2} to {len(bp)}  -> screen shows only {s['goal2']['count']}")
    # per-program too
    per_hi = bp.groupby("Program")["Master_ID"].nunique().to_dict()
    per_lo = {}
    for (rm, prog) in pairs:
        per_lo[prog] = per_lo.get(prog, 0) + 1
    diff = {k: (per_lo.get(k, 0), per_hi[k]) for k in per_hi if per_lo.get(k, 0) != per_hi[k]}
    print("   programs whose per-program count would change if all open pairs are accepted:", diff)
    return props


print("== product sample files")
sample = {os.path.basename(p): open(p, "rb").read() for p in sorted(glob.glob(ROOT + "/sample_data/*"))}
props = independent(sample, dob=False)
for p in props[:2]:
    print("   e.g.", p["a"]["name"], p["a"]["system"], p["a"]["program"], "|", p["b"]["name"], p["b"]["system"], p["b"]["program"], "|", p["reason"], "| points", p["points"])

print("\n== only accepted rows count: set-aside and in-review rows are excluded")
import messy
setup_standard(messy.make(), dob=True)
rw = summary()["rows"]
uc = export_df("unique_clients")
cover = int(uc["Source_Record_Count"].astype(int).sum())
print(f"   clean={rw['clean']} review={rw['review']} aside={rw['aside']}; Unique_Clients covers {cover} source rows -> {'OK' if cover == rw['clean'] else 'MISMATCH'}")
decide("dupc", "aside"); decide("idconflict", "accept_all")
summary(True)
rw = summary()["rows"]; uc = export_df("unique_clients"); cover = int(uc["Source_Record_Count"].astype(int).sum())
print(f"   after accept_all + aside: clean={rw['clean']} review={rw['review']} aside={rw['aside']}; covered {cover} -> {'OK' if cover == rw['clean'] else 'MISMATCH'}")
allrids = [x for cell in uc["Source_Rows"] for x in cell.split("; ")]
rv = export_df("review")
review_keys = {f"{a}||{b}" for a, b in zip(rv["Source_File"], rv["Source_Row"])} if len(rv) else set()
print("   any in-review/aside row counted as a person:", bool(review_keys & set(allrids)))
