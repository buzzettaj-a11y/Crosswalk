from _common import *
import csv, tempfile, os, json

d = tempfile.mkdtemp(prefix="distB_")
def square(lon0, lon1, lat0=40.60, lat1=40.80):
    return {"type":"Polygon","coordinates":[[[lon0,lat0],[lon1,lat0],[lon1,lat1],[lon0,lat1],[lon0,lat0]]]}
gj = {"type":"FeatureCollection","features":[
  {"type":"Feature","properties":{"senate_district":10,"assembly_district":20,"council_district":30},"geometry":square(-74.0,-73.985)},
  {"type":"Feature","properties":{"senate_district":11,"assembly_district":21,"council_district":31},"geometry":square(-73.985,-73.9)}]}
gp = os.path.join(d, "d.geojson"); json.dump(gj, open(gp, "w"))
dist, meta = engine.load_district_index(gp)

rows = [("1 Main St","11201","Brooklyn",40.7000,-73.9900),    # truly in district A (west of -73.985)
        ("11 Main St","11201","Brooklyn",40.7040,-73.9800),    # in district B
        ("5 Edge St","11201","Brooklyn",40.7100,-73.98505)]    # 5 ft west of the boundary, district A
rp = os.path.join(d, "ref.csv")
with open(rp, "w", newline="") as f:
    w = csv.writer(f); w.writerow(["address","zip","city","latitude","longitude"]); w.writerows(rows)
idx, _ = engine.load_geocode_index(rp)

def go(addr, ref_idx=idx, seed=1337):
    res = pipeline([dict(First="Ana", Last="Lopez", ID="A1", Addr=addr, Addr2="", City="Brooklyn", State="NY", Zip="11201")], index=ref_idx, districts=dist, seed=seed, jitter=True)
    r = res["transformed"][0]
    return ("CLEAN" if not r["__errors__"] else "REVIEW "+str(r["__errors__"])), r["Verification_Status"], r["Geocode_Confidence"], r["Latitude"], r["Longitude"], (r["Senate_District"], r["Assembly_District"], r["Council_District"])

print("districts are from the true point, not the jittered one (5 Edge St is 5 ft inside A; jitter moves it 150-250 ft):")
crossed = 0
for seed in range(1, 41):
    st, ver, conf, lat, lon, dd = go("5 Edge St", seed=seed)
    stored_side = "A" if float(lon) < -73.985 else "B"
    crossed += stored_side == "B"
    assert dd == ("10","20","30"), (seed, dd)
print(f"   40 seeds: district always A (10/20/30); stored point landed in B on {crossed} of 40 seeds, so the stored point and its district disagree on those rows")

# fuzzy wrong building -> district of the wrong building
only_11 = [rows[1]]
rp2 = os.path.join(d, "ref2.csv")
with open(rp2, "w", newline="") as f:
    w = csv.writer(f); w.writerow(["address","zip","city","latitude","longitude"]); w.writerows(only_11)
idx2, _ = engine.load_geocode_index(rp2)
print("\nask '1 Main St' (truly district A, 10/20/30) with only '11 Main St' (district B) in the reference:")
print("  ", go("1 Main St", ref_idx=idx2))
