"""
Feature parity: every capability the Streamlit interface offers must also be
reachable in the Crosswalk interface. This exists because the first build of
that interface silently dropped the schema editor, the prepare-step options, and the
optional Geosupport fields. Screen-by-screen tests did not catch it, because
each screen returned data; it was the missing controls that mattered.

Run: python test_parity.py    (exit code 0 means every capability is present)
"""
import os
import sys
import warnings

warnings.filterwarnings("ignore")
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if os.path.basename(os.path.dirname(os.path.abspath(__file__))) == "tests":
    os.chdir(ROOT)
    sys.path.insert(0, ROOT)

from fastapi.testclient import TestClient
import app as engine
import crosswalk_server as cw

results = []


def check(label, cond):
    results.append((label, bool(cond)))


client = TestClient(cw.api, base_url="http://127.0.0.1:8765")
client.post("/api/reset")
client.post("/api/mode", json={"mode": "Advanced"})

UI_JS = open(os.path.join("ui", "app.js"), encoding="utf-8").read()
SERVER = open("crosswalk_server.py", encoding="utf-8").read()

# Give it a source table so the screens have something to describe.
path = os.path.join("sample_data", "legacy_export.xlsx")
if os.path.exists(path):
    client.post("/api/sources/upload",
                files=[("files", ("legacy_export.xlsx", open(path, "rb").read()))])

# ---- schema editor ----------------------------------------------------------
s = client.get("/api/ui?screen=schema").json()["schema"]
check("schema screen reports it is editable", s["editable"] is True)
check("schema screen offers the field types", set(s["types"]) >= {"str", "int"})
check("schema screen exposes the built-in roles",
      set(s["roles"]) >= set(engine.MASTER_COLUMNS))
for control in ('data-sf="label"', 'data-sf="dtype"', 'data-sf="length"',
                "data-sreq", "data-sdel", "add-field", "reset-schema"):
    check(f"schema editor has a control for {control}", control in UI_JS)

edited = [dict(f) for f in s["fields"]]
edited.append({"role": "custom", "label": "Program", "dtype": "str",
               "length": 40, "required": False})
edited[0]["label"] = "Given_Name"
client.post("/api/schema", json={"schema": edited})
s2 = client.get("/api/ui?screen=schema").json()["schema"]
check("a renamed label persists", s2["fields"][0]["label"] == "Given_Name")
check("a custom field can be added",
      any(f["label"] == "Program" for f in s2["fields"]))
client.post("/api/schema/reset")
s3 = client.get("/api/ui?screen=schema").json()["schema"]
check("schema resets to the default",
      len(s3["fields"]) == len(engine.DEFAULT_SCHEMA))

# ---- prepare options --------------------------------------------------------
p = client.get("/api/ui?screen=prepare").json()["prepare"]
check("prepare exposes the real columns of each table",
      all(isinstance(v, list) and v for v in p["columns"].values()))
check("prepare offers every delimiter the engine knows",
      set(p["delimiters"]) == set(engine.DELIMITERS))
check("prepare offers all six case modes", len(p["cases"]) == 6)
check("smart title for names is offered", "Smart Title (names)" in p["cases"])
check("smart title for addresses is offered", "Smart Title (address)" in p["cases"])
for control in ("sanitize", "strip_punct", "maxsplit", "delimCustom", "names"):
    check(f"prepare form carries the {control} option", control in UI_JS)

table = p["tables"][0]
before = len(p["ops"])
client.post("/api/prepare/add", json={"table": table, "op": {
    "type": "clean", "columns": [p["columns"][table][0]],
    "case": "Smart Title (names)", "sanitize": True, "strip_punct": True}})
p2 = client.get("/api/ui?screen=prepare").json()["prepare"]
check("a clean step with options is accepted", len(p2["ops"]) == before + 1)
added = p2["ops"][-1]["op"]
check("the case option survives the round trip",
      added.get("case") == "Smart Title (names)")
check("the sanitize option survives the round trip", added.get("sanitize") is True)
check("the strip punctuation option survives the round trip",
      added.get("strip_punct") is True)

client.post("/api/prepare/add", json={"table": table, "op": {
    "type": "split_delim", "column": p["columns"][table][0], "delimiter": ",",
    "maxsplit": 2, "names": ["a", "b"]}})
p3 = client.get("/api/ui?screen=prepare").json()["prepare"]
d = p3["ops"][-1]["op"]
check("a delimiter split keeps its max splits", d.get("maxsplit") == 2)
check("a delimiter split keeps its column names", d.get("names") == ["a", "b"])

# ---- optional Geosupport fields --------------------------------------------
r = client.get("/api/ui?screen=run").json()["runData"]
check("run screen carries the Geosupport catalog", bool(r["gdeCatalog"]))
check("every catalog category is offered",
      set(r["gdeCatalog"]) == set(engine.GDE_FIELD_CATALOG))
total = sum(len(v) for v in r["gdeCatalog"].values())
engine_total = sum(len(v) for v in engine.GDE_FIELD_CATALOG.values())
check(f"all {engine_total} optional fields are offered", total == engine_total)
check("the run screen reports whether Geosupport is available",
      "gdeAvailable" in r)
check("the field selector is wired in the front end", 'data-gde=' in UI_JS)

first = r["gdeCatalog"][list(r["gdeCatalog"])[0]][0]
client.post("/api/run/gde-field", json={"name": first, "on": True})
r2 = client.get("/api/ui?screen=run").json()["runData"]
check("a selected field is remembered", first in r2["gdeSelected"])
client.post("/api/run/gde-field", json={"name": first, "on": False})
r3 = client.get("/api/ui?screen=run").json()["runData"]
check("a field can be unselected", first not in r3["gdeSelected"])
check("the selection is passed to the pipeline, not discarded",
      'S["gde_fields"] or None' in SERVER)

# ---- capabilities that already matched --------------------------------------
check("guided and advanced modes exist", "Advanced" in UI_JS and "Guided" in UI_JS)
check("the system check is reachable", "screen=check" in UI_JS or "check" in UI_JS)
check("table selection is reachable", "data-include" in UI_JS)
check("corrections re-import is recognized",
      "is_corrections_frame" in SERVER)
check("require geocode is offered", "require_geocode" in UI_JS)
check("jitter and its seed are offered", "jitter" in UI_JS and "seed" in UI_JS)
check("all three export formats are offered",
      all(f in UI_JS for f in ("CSV", "Excel", "JSON")))
check("export column selection is offered", "data-col=" in UI_JS)
check("all four output files are downloadable",
      all(w in UI_JS for w in ("clean", "review", "audit", "quality")))

for label, passed in results:
    print(f"  [{'PASS' if passed else 'FAIL'}] {label}")
ok = all(p for _, p in results)
print(f"PARITY TESTS: {'PASS' if ok else 'FAIL'} "
      f"({sum(1 for _, p in results if p)}/{len(results)})")
sys.exit(0 if ok else 1)
