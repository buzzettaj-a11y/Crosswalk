from _common import *
import _refdata, csv, tempfile, os

def make_index(rows):
    p = os.path.join(tempfile.mkdtemp(prefix="refB_"), "ref.csv")
    with open(p, "w", newline="") as f:
        w = csv.writer(f); w.writerow(["address","zip","city","latitude","longitude"]); w.writerows(rows)
    idx, meta = engine.load_geocode_index(p)
    return idx

def run(addr, zipc, ref_rows, city="New York", require=False):
    idx = make_index(ref_rows)
    res = pipeline([dict(First="Ana", Last="Lopez", ID="A1", Addr=addr, Addr2="", City=city, State="NY", Zip=zipc)],
                   require_geocode=require, index=idx, jitter=False)
    r = res["transformed"][0]
    errs = "; ".join(r["__errors__"])
    return (("REVIEW: " + errs) if errs else "CLEAN"), r["Verification_Status"], r["Geocode_Confidence"], (r["Latitude"], r["Longitude"]), [f["message"] for f in r["__flags__"] if "Geo" in f["scenario"] or "geocode" in f["message"].lower()], r["__geo_status__"]

tests = [
 ("W vs E: ask 100 E 10 St (ZIP typo 10011), ref has only 100 W 10 St", "100 E 10 St", "10011", [("100 W 10 St","10011","New York",40.7350,-73.9990)], "New York"),
 ("house no: ask 111 Main St, ref has 11 Main St only",               "111 Main St", "11201", [("11 Main St","11201","Brooklyn",40.7040,-73.9800)], "Brooklyn"),
 ("house no: ask 1 Main St, ref has 11 Main St only",                 "1 Main St", "11201", [("11 Main St","11201","Brooklyn",40.7040,-73.9800)], "Brooklyn"),
 ("avenue letter: ask Avenue U, ref has Avenue V only",               "1 Avenue U", "11223", [("1 Avenue V","11223","Brooklyn",40.5950,-73.9600)], "Brooklyn"),
 ("avenue letter: ask 1 Avenue W, ref has Avenue V only",             "1 Avenue W", "11223", [("1 Avenue V","11223","Brooklyn",40.5950,-73.9600)], "Brooklyn"),
 ("swapped numbers: ask 40 W 100 St, ref has 100 W 40 St",            "40 W 100 St", "10025", [("100 W 40 St","10025","New York",40.7540,-73.9860)], "New York"),
 ("Fulton St vs Fulton Ave: ask 123 Fulton Ave, ref has Fulton St",   "123 Fulton Ave", "11201", [("123 Fulton St","11201","Brooklyn",40.6920,-73.9870)], "Brooklyn"),
 ("Beach 9 vs Beach 19: ask 5 Beach 19 St, ref has 5 Beach 9 St",     "5 Beach 19 St", "11691", [("5 Beach 9 St","11691","Queens",40.6020,-73.7500)], "Queens"),
 ("typo only: ask 123 Fultin St, ref has 123 Fulton St (should match)", "123 Fultin St", "11201", [("123 Fulton St","11201","Brooklyn",40.6920,-73.9870)], "Brooklyn"),
 ("unit left in street: 123 Fulton St Apt B (should match)",           "123 Fulton St Apt B", "11201", [("123 Fulton St","11201","Brooklyn",40.6920,-73.9870)], "Brooklyn"),
 ("numbered street: ask 100 W 100 St, ref has 100 W 10 St only",     "100 W 100 St", "10011", [("100 W 10 St","10011","New York",40.7350,-73.9990)], "New York"),
 ("numbered street: ask 12 W 40 St, ref has 12 W 4 St only",          "12 W 40 St", "10011", [("12 W 4 St","10011","New York",40.7300,-73.9950)], "New York"),
 ("numbered street: ask 45 Beach 90 St, ref has 45 Beach 9 St only",  "45 Beach 90 St", "11693", [("45 Beach 9 St","11693","Queens",40.5900,-73.8200)], "Queens"),
 ("exact: 100 W 10 St",                                               "100 W 10 St", "10011", [("100 W 10 St","10011","New York",40.7350,-73.9990)], "New York"),
 ("exact w/ require_geocode, fuzzy wrong building",                    "111 Main St", "11201", [("11 Main St","11201","Brooklyn",40.7040,-73.9800)], "Brooklyn"),
]
for label, addr, z, ref, city in tests:
    req = "require_geocode" in label
    st, ver, conf, ll, geo, gs = run(addr, z, ref, city, require=req)
    print(f"{label}\n    {st} | status={ver!r} conf={conf!r} geo={gs} latlon={ll}\n    {geo}")
