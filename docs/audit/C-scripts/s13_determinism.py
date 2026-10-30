"""
s13: determinism. Same input twice from a reset; upload order; one decision then everyone's jitter;
jitter per address.
"""
from invariants import *
import re, glob, hashlib
import messy


def mask(b):
    s = b.decode("utf-8", "replace")
    s = re.sub(r"Generated \(UTC\): [0-9T:\-+]+", "Generated (UTC): <T>", s)
    s = re.sub(r"Recorded \d{4}-\d\d-\d\d \d\d:\d\d:\d\d", "Recorded <T>", s)
    return s.encode()


def dump():
    return {k: mask(export_raw(k)) for k in EXPORTS}


def h(b):
    return hashlib.sha256(b).hexdigest()[:10]


sample = {os.path.basename(p): open(p, "rb").read() for p in sorted(glob.glob(ROOT + "/sample_data/*"))}

for label, files in (("sample", sample), ("messy", messy.make())):
    runs = []
    for i in range(2):
        reset(); upload(files); set_schema(dob=True); run(); summary(True)
        runs.append(dump())
    print(f"== {label}: two identical runs from /api/reset")
    for k in EXPORTS:
        print(f"   {EXPORTS[k]:<28} {h(runs[0][k])} {h(runs[1][k])} identical={runs[0][k] == runs[1][k]}")
    # raw audit differences beyond the two timestamps?
    print("   (audit/other timestamps masked)")

# jitter: seeded? same address same jitter?
reset(); upload(sample); set_schema(dob=True); run(seed=1337)
c = export_df("clean")
print("\n== jitter")
print("   lat/long filled on", int((c["Latitude"] != "").sum()), "of", len(c), "clean rows")
g = c[c["Latitude"] != ""].copy()
g["addr"] = g["Address_1"].str.lower() + "|" + g["Zip"]
dups = g.groupby("addr").agg(n=("Latitude", "size"), distinct=("Latitude", "nunique"))
print("   addresses used by 2+ rows:", int((dups.n > 1).sum()), "| of those, rows share identical stored coordinates:",
      int(((dups.n > 1) & (dups.distinct == 1)).sum()), "(each row gets its own random offset)")

# upload order
print("\n== upload order (same files, different order)")
msy = messy.make()
reset(); upload({k: msy[k] for k in ("A.csv", "B.csv", "C.csv")}); set_schema(dob=True); run(); summary(True)
d1 = dump()
reset(); upload({k: msy[k] for k in ("C.csv", "B.csv", "A.csv")}); set_schema(dob=True); run(); summary(True)
d2 = dump()
for k in EXPORTS:
    print(f"   {EXPORTS[k]:<28} identical={d1[k] == d2[k]}")
import io
u1 = pd.read_csv(io.BytesIO(d1["unique_clients"]), dtype=str, keep_default_na=False)
u2 = pd.read_csv(io.BytesIO(d2["unique_clients"]), dtype=str, keep_default_na=False)
m = u1.merge(u2, on="Master_ID", suffixes=("_ABC", "_CBA"))
diff = m[(m.First_Name_ABC != m.First_Name_CBA) | (m.Address_1_ABC != m.Address_1_CBA)]
print("   Master IDs whose displayed name/address differ with upload order:", len(diff), "of", len(m))
print(diff[["Master_ID", "First_Name_ABC", "Address_1_ABC", "First_Name_CBA", "Address_1_CBA"]].head(5).to_string())

# one decision moves every later row's jitter
print("\n== one review decision shifts other rows' jitter")
reset(); upload(messy.make()); set_schema(dob=True); run()
before = export_df("clean").set_index(["Source_File", "Source_Row"])[["Latitude", "Longitude"]]
# approving nothing changes; fix one earlier row so it becomes geocodable: use bulk correct
client.post("/api/review/group", json={"gid": "zipbad", "decision": "sent"})
rid = queue("pending")["items"][0]["rid"]
r = client.post("/api/queue/action", json={"rid": rid, "action": "corrected", "edits": {"Zip": "11201"}}).json()
after = export_df("clean").set_index(["Source_File", "Source_Row"])[["Latitude", "Longitude"]]
common = before.index.intersection(after.index)
moved = [i for i in common if (before.loc[i].values != after.loc[i].values).any()]
print("   corrected row", rid, "->", r["status"])
print("   clean rows whose stored coordinates changed although nothing about them changed:", len(moved), "of", len(common))
