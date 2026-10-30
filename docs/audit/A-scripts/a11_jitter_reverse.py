"""Claim: 'Privacy jitter 150 to 250 ft, stored points only.' Can the exported points be un-jittered with what the tool itself publishes (the seed)?"""
import os, sys, csv, io, math, random, re
HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, HERE)
import a_lib
work = sys.argv[1]
FIX = os.path.join(os.path.dirname(HERE), "A-fixtures")
cw, c = a_lib.boot(work)
c.post("/api/reset")
a_lib.upload(c, [os.path.join(FIX, "geocodable.csv")])
a_lib.relax_client_id(c)
a_lib.fix_mapping(c)
st = a_lib.run(c, seed=1337, jitter=True); print("run", st["state"])
rows = list(csv.DictReader(io.StringIO(a_lib.download(c, "clean").decode())))
ref = {r["address"]: r for r in csv.DictReader(open(os.path.join(work, "nyc_address_points.csv")))}
audit = c.get("/api/audit/text").text
print("audit log shows the seed:", re.search(r"Settings:.*", audit).group(0))
rng = random.Random(1337)          # the seed printed above
FT = 364000.0
for r in rows:
    if not r["Latitude"]:
        print(r["Address_1"], "-> not geocoded"); continue
    d = rng.uniform(150.0, 250.0); b = rng.uniform(0.0, 2.0 * math.pi)     # same two draws jitter_point makes
    lat = float(r["Latitude"]); lon = float(r["Longitude"])
    ulat = lat - d * math.cos(b) / FT
    ulon = lon - d * math.sin(b) / (FT * math.cos(math.radians(ulat)))
    t = ref[r["Address_1"]]
    print(f'{r["Address_1"]!r}: exported {lat:.6f},{lon:.6f} | recovered {ulat:.6f},{ulon:.6f} | true {t["latitude"]},{t["longitude"]} | error {abs(ulat-float(t["latitude"]))*FT:.2f} ft')
