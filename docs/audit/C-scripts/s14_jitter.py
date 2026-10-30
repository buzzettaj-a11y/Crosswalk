"""
s14: privacy jitter: seeded? identical across runs? stable under unrelated decisions? per address?
The shipped gazetteer is synthetic, so addresses are drawn from it so rows really geocode.
"""
from invariants import *
import pandas as pd

ref = pd.read_csv(ROOT + "/nyc_address_points.csv", dtype=str, keep_default_na=False)
ok = []
for r in ref.itertuples():
    if "apt" in r.address.lower() or not r.address[0].isdigit():
        continue
    if cw.engine.borough_from_zip(r.zip) == r.city:
        ok.append(r)
    if len(ok) >= 30:
        break
print("usable gazetteer addresses:", len(ok))
H = ["Client_ID", "First_Name", "Last_Name", "DOB", "Address", "City", "State", "Zip", "Program"]
rows = []
for i, r in enumerate(ok):
    rows.append([f"G{i:03d}", f"First{chr(65 + i % 26)}", f"Last{chr(97 + i % 26)}x{chr(97 + i // 26)}", f"19{60 + i}-01-01", r.address, r.city, "NY", r.zip, "Housing"])
# three households: same address as row 0, 1, 2
for j in range(3):
    r = ok[j]
    rows.append([f"H{j:03d}", f"Kin{chr(97 + j)}", f"Last{chr(97 + j % 26)}x{chr(97 + j // 26)}", f"20{10 + j}-02-02", r.address, r.city, "NY", r.zip, "Youth"])
# one row that fails (blank ZIP) near the top so a fix changes how many rows are geocoded before the rest
X = ok[5]
rows.insert(2, ["X001", "Zed", "Zimmer", "1970-01-01", X.address, X.city, "NY", "", "Housing"])
data = pd.DataFrame(rows, columns=H).to_csv(index=False).encode()


# WORKAROUND for finding C-0x: _load_reference() keeps the (features, meta) tuple from load_district_index,
# so the first geocoded row raises TypeError. Unwrap it in memory only, to be able to test jitter.
ref_ = cw._load_reference()
if isinstance(ref_["dist"], tuple):
    print("district index is a tuple:", type(ref_["dist"]), "-> unwrapping in memory for this test only")
    ref_["dist"] = ref_["dist"][0]


def coords():
    c = export_df("clean")
    return c.set_index("Client_ID")[["Latitude", "Longitude", "Zip", "Address_1"]]


reset(); upload({"G.csv": data}); set_schema(dob=True); run(seed=1337)
a = coords()
print("geocoded rows:", int((a.Latitude != "").sum()), "of", len(a))
reset(); upload({"G.csv": data}); set_schema(dob=True); run(seed=1337)
b = coords()
print("run 1 vs run 2 (same seed) coordinates identical:", a.equals(b))
reset(); upload({"G.csv": data}); set_schema(dob=True); run(seed=1338)
c = coords()
print("seed 1338 differs from 1337:", not a.equals(c))
# same address, different row
k = ok[0]
print("households at one address:", a[a.Address_1 == a.loc["G000", "Address_1"]][["Latitude", "Longitude"]].to_string())

# unrelated decision shifts other people's jitter
reset(); upload({"G.csv": data}); set_schema(dob=True); run(seed=1337)
before = coords()
client.post("/api/review/group", json={"gid": "zipbad", "decision": "sent"})
rid = queue("pending")["items"][0]["rid"]
res = client.post("/api/queue/action", json={"rid": rid, "action": "corrected", "edits": {"Zip": X.zip}}).json()
after = coords()
common = before.index.intersection(after.index)
moved = [i for i in common if (before.loc[i, ["Latitude", "Longitude"]].values != after.loc[i, ["Latitude", "Longitude"]].values).any()]
print("fixed the ZIP of", rid, "->", res["status"], "| geocoded now:", int((after.Latitude != '').sum()))
print("rows whose stored coordinates changed though their own data did not:", len(moved), "of", len(common))
print(before.loc[moved[:3]].to_string() if moved else "")
print(after.loc[moved[:3]].to_string() if moved else "")
