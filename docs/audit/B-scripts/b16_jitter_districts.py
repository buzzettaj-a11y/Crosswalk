from _common import *
import _refdata, csv, tempfile, os, math, json, random, statistics

def haversine_ft(lat1, lon1, lat2, lon2):
    R = 20902231.0
    p1, p2 = math.radians(lat1), math.radians(lat2)
    dphi = p2 - p1; dl = math.radians(lon2 - lon1)
    a = math.sin(dphi/2)**2 + math.cos(p1)*math.cos(p2)*math.sin(dl/2)**2
    return 2*R*math.asin(math.sqrt(a))

# --- a reference with 400 distinct addresses on one street, all exact matches ---
def build_ref(n=400, start_lat=40.70, start_lon=-73.95):
    rows = []
    for i in range(n):
        rows.append((f"{i+1} Test St", "11201", "Brooklyn", start_lat + (i % 20)*0.0004, start_lon + (i // 20)*0.0004))
    p = os.path.join(tempfile.mkdtemp(prefix="refB_"), "ref.csv")
    with open(p, "w", newline="") as f:
        w = csv.writer(f); w.writerow(["address","zip","city","latitude","longitude"]); w.writerows(rows)
    idx, _ = engine.load_geocode_index(p)
    return idx, rows

idx, ref = build_ref()
def people(n, addr_fn):
    return [dict(First="Pat" + "abcdefghij"[i % 10], Last="Lee" + "abcdefghij"[i // 10 % 10] + "abcdefghij"[i // 100 % 10], ID=f"ID{i}", Addr=addr_fn(i), Addr2="", City="Brooklyn", State="NY", Zip="11201") for i in range(n)]

rows = people(400, lambda i: f"{i+1} Test St")
res = pipeline(rows, index=idx, seed=1337, jitter=True)
dist = []
for r in res["transformed"]:
    i = int(r["Client_ID"][2:])
    tlat, tlon = ref[i][3], ref[i][4]
    dist.append(haversine_ft(tlat, tlon, float(r["Latitude"]), float(r["Longitude"])))
print(f"jitter distance over {len(dist)} rows: min={min(dist):.1f} max={max(dist):.1f} mean={statistics.mean(dist):.1f} ft")
print("all within 150-250 ft:", all(149.0 <= d <= 251.0 for d in dist))

# determinism: same input, same output; different seed, different output
res2 = pipeline(rows, index=idx, seed=1337, jitter=True)
print("same seed, same input -> identical coordinates:", [(r["Latitude"], r["Longitude"]) for r in res["transformed"]] == [(r["Latitude"], r["Longitude"]) for r in res2["transformed"]])
res3 = pipeline(rows, index=idx, seed=1, jitter=True)
print("different seed -> different coordinates:", [(r["Latitude"], r["Longitude"]) for r in res["transformed"]] != [(r["Latitude"], r["Longitude"]) for r in res3["transformed"]])

# stability: one earlier row goes to review -> every later row's stored point moves
rows_b = [dict(r) for r in rows]
rows_b[0]["Zip"] = "BAD"        # row 0 now fails validation and is not geocoded
res4 = pipeline(rows_b, index=idx, seed=1337, jitter=True)
changed = sum(1 for a, b in zip(res["transformed"][1:], res4["transformed"][1:]) if (a["Latitude"], a["Longitude"]) != (b["Latitude"], b["Longitude"]))
print(f"rows 1..399 whose stored coordinate changed because row 0 failed: {changed} of 399")

# same address, many clients: points differ, centroid converges on the true door
same = people(300, lambda i: "1 Test St")
res5 = pipeline(same, index=idx, seed=1337, jitter=True)
lats = [float(r["Latitude"]) for r in res5["transformed"]]; lons = [float(r["Longitude"]) for r in res5["transformed"]]
print("300 clients at 1 Test St: distinct stored points:", len(set(zip(lats, lons))))
cl, cn = statistics.mean(lats), statistics.mean(lons)
print(f"centroid of the 300 jittered points is {haversine_ft(ref[0][3], ref[0][4], cl, cn):.1f} ft from the true door")
for k in (5, 20):
    cl, cn = statistics.mean(lats[:k]), statistics.mean(lons[:k])
    print(f"   centroid of first {k} points: {haversine_ft(ref[0][3], ref[0][4], cl, cn):.1f} ft from the true door")

# known default seed: anyone with the output and the seed in the docs can undo it
rng = random.Random(1337)
rec = []
for r in res["transformed"]:
    d = rng.uniform(150.0, 250.0); b = rng.uniform(0.0, 2.0*math.pi)
    lat = float(r["Latitude"]); lon = float(r["Longitude"])
    tl = lat - (d*math.cos(b))/364000.0
    tn = lon - (d*math.sin(b))/ (364000.0*math.cos(math.radians(tl)))
    i = int(r["Client_ID"][2:]); rec.append(haversine_ft(ref[i][3], ref[i][4], tl, tn))
print(f"undoing the jitter with seed 1337 and row order: max error {max(rec):.2f} ft over {len(rec)} rows (6-decimal rounding is about 0.4 ft)")
