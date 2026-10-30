"""
Tests for the preflight system check. Run: python test_preflight.py
Exit code 0 means every check passed.
"""
import os
import sys
import tempfile
import warnings

warnings.filterwarnings("ignore")
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if os.path.basename(os.path.dirname(os.path.abspath(__file__))) == "tests":
    os.chdir(ROOT)
    sys.path.insert(0, ROOT)

import app

results = []


def check(label, condition):
    results.append((label, bool(condition)))


checks = app.preflight_checks()
by_name = {c["name"]: c for c in checks}

# ---- structure --------------------------------------------------------------
check("preflight returns results", len(checks) > 5)
check("every result has name, status, detail",
      all({"name", "status", "detail"} <= set(c) for c in checks))
check("statuses are limited to ok, warn, fail",
      all(c["status"] in ("ok", "warn", "fail") for c in checks))

# ---- the checks that must always be present --------------------------------
for required in ("Python version", "Package: pandas", "Package: streamlit",
                 "GEOFILES environment variable", "Gazetteer reference file",
                 "District boundary file", "Geocoding backend in use"):
    check(f"reports '{required}'", required in by_name)

# ---- it never raises, even with everything missing --------------------------
saved_geo, saved_dist = app.GEOCODE_FILE, app.DISTRICT_FILE
try:
    app.GEOCODE_FILE = "does_not_exist.csv"
    app.DISTRICT_FILE = "does_not_exist.geojson"
    missing = app.preflight_checks()
    check("survives missing reference files", len(missing) > 5)
    m = {c["name"]: c for c in missing}
    check("missing gazetteer is reported as a failure",
          m["Gazetteer reference file"]["status"] == "fail")
finally:
    app.GEOCODE_FILE, app.DISTRICT_FILE = saved_geo, saved_dist

# ---- reference quality judges files on their own consistency ----------------
with tempfile.TemporaryDirectory() as tmp:
    good = os.path.join(tmp, "good.csv")
    with open(good, "w", newline="") as fh:
        fh.write("address,zip,city,latitude,longitude\n")
        # ZIP and city agree throughout
        for i in range(40):
            fh.write(f"{i} Example St,11201,Brooklyn,40.69,-73.99\n")
            fh.write(f"{i} Sample Ave,10007,New York,40.71,-74.00\n")
    s, d = app.check_reference_quality(good)
    check("consistent reference file passes", s == "ok")

    bad = os.path.join(tmp, "bad.csv")
    with open(bad, "w", newline="") as fh:
        fh.write("address,zip,city,latitude,longitude\n")
        # every row claims a borough that contradicts its ZIP
        for i in range(40):
            fh.write(f"{i} Example St,11201,Queens,40.69,-73.99\n")
    s, d = app.check_reference_quality(bad)
    check("contradictory reference file fails", s == "fail")
    check("failure message explains the contradiction",
          "contradicts" in d and "%" in d)

    empty = os.path.join(tmp, "empty.csv")
    with open(empty, "w", newline="") as fh:
        fh.write("address,latitude,longitude\nx,40.1,-73.1\n")
    s, d = app.check_reference_quality(empty)
    check("file without zip or city columns warns rather than fails", s == "warn")

    s, d = app.check_reference_quality(os.path.join(tmp, "nope.csv"))
    check("absent file reports failure", s == "fail")

# ---- the shipped sample data is correctly identified as untrustworthy -------
if os.path.exists(app.GEOCODE_FILE):
    s, d = app.check_reference_quality(app.GEOCODE_FILE)
    check("shipped sample gazetteer is flagged as demo data", s == "fail")

# ---- the report is text and leaks nothing -----------------------------------
text = app.preflight_report_text()
check("report is non-empty text", isinstance(text, str) and len(text) > 100)
check("report has a header", "Preflight report" in text)
check("report lists a status for each check",
      text.count("[") >= len(checks))

for label, passed in results:
    print(f"  [{'PASS' if passed else 'FAIL'}] {label}")
ok = all(p for _, p in results)
print(f"PREFLIGHT TESTS: {'PASS' if ok else 'FAIL'} "
      f"({sum(1 for _, p in results if p)}/{len(results)})")
sys.exit(0 if ok else 1)
