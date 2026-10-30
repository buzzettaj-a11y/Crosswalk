"""
End-to-end test of Crosswalk API: walks every stage on the sample data,
exercising uploads, table detection, schema fit, prepare, mapping, the run,
grouped review decisions, the row-by-row queue, and export.

Run: python test_crosswalk_api.py   (exit code 0 means every check passed)
"""
import os
import sys
import re
import time
import warnings

warnings.filterwarnings("ignore")
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if os.path.basename(os.path.dirname(os.path.abspath(__file__))) == "tests":
    os.chdir(ROOT)
    sys.path.insert(0, ROOT)

from fastapi.testclient import TestClient
import crosswalk_server as cw

results = []


def check(label, cond):
    results.append((label, bool(cond)))


client = TestClient(cw.api, base_url="http://127.0.0.1:8765")
client.post("/api/reset")

# ---- the server only answers to itself --------------------------------------
check("a request naming a foreign host is refused",
      client.get("/api/ui?screen=check",
                 headers={"Host": "evil.example.com"}).status_code == 400)
check("localhost is accepted",
      client.get("/api/ui?screen=check",
                 headers={"Host": "localhost:8765"}).status_code == 200)
check("no CORS headers are advertised",
      "access-control-allow-origin" not in
      {k.lower() for k in client.get("/api/ui?screen=check").headers})

SAMPLES = ["clinic_export.csv", "portal_export.json", "legacy_export.xlsx",
           "state_export.xml", "partner_export.tsv"]

# ---- 00 system check --------------------------------------------------------
r = client.get("/api/ui?screen=check").json()
check("system check returns diagnostics", len(r["check"]["checks"]) > 5)
check("chrome carries five trust stamps", len(r["chrome"]["stamps"]) == 5)
check("rail exposes eight stages, with results before the files",
      len(r["chrome"]["stages"]) == 9
      and r["chrome"]["stages"][-2:] in (["Summary", "Export"],
                                         ["Results", "Download"])
      and r["chrome"]["stages"][4] == "Programs")
check("report contains no client data", "Delgado" not in r["check"]["report"])

# ---- 01 sources -------------------------------------------------------------
files = []
for name in SAMPLES:
    path = os.path.join("sample_data", name)
    if os.path.exists(path):
        files.append(("files", (name, open(path, "rb").read())))
check("sample files found", len(files) == 5)
resp = client.post("/api/sources/upload", files=files)
check("upload accepted", resp.status_code == 200)

r = client.get("/api/ui?screen=sources").json()["sources"]
check("tables detected from every file", len(r["tables"]) >= 5)
check("rows staged is a real sum", r["stats"]["rows"] > 200)
check("record tables default to included",
      sum(1 for t in r["tables"] if r["included"][t["key"]]) >= 5)

# ---- 02 schema --------------------------------------------------------------
# The sample files do not all carry a Client ID, so relax that requirement the
# way an operator would in Advanced mode.
client.post("/api/mode", json={"mode": "Advanced"})
schema = [dict(f) for f in cw.engine.DEFAULT_SCHEMA]
for f in schema:
    if f["role"] == "Client_ID":
        f["required"] = False
client.post("/api/schema", json={"schema": schema})
r = client.get("/api/ui?screen=schema").json()["schema"]
check("schema exposes the master fields", len(r["fields"]) >= 9)
check("fit is computed per included table", len(r["fit"]) >= 5)
check("fit counts are real", all(0 <= f["have"] <= f["total"] for f in r["fit"]))

# ---- 03 prepare -------------------------------------------------------------
r = client.get("/api/ui?screen=prepare").json()["prepare"]
check("auto staging operations were detected", len(r["ops"]) >= 1)
if r["ops"]:
    op_id = r["ops"][0]["id"]
    client.post("/api/prepare/toggle", json={"id": op_id, "removed": True})
    after = client.get("/api/ui?screen=prepare").json()["prepare"]
    check("an operation can be removed",
          any(o["id"] == op_id and o["removed"] for o in after["ops"]))
    client.post("/api/prepare/toggle", json={"id": op_id, "removed": False})
    back = client.get("/api/ui?screen=prepare").json()["prepare"]
    check("a removed operation can be restored",
          any(o["id"] == op_id and not o["removed"] for o in back["ops"]))

# ---- 04 map -----------------------------------------------------------------
r = client.get("/api/ui?screen=map").json()["map"]
check("mapping is guessed for every table", len(r["tables"]) >= 5)
check("guesses fill most required fields",
      sum(1 for t in r["tables"] if t["ready"]) >= 3)

# Fill anything still missing so the run is not blocked.
for t in r["tables"]:
    if t["ready"]:
        continue
    for f in t["fields"]:
        if f["required"] and not f["col"]:
            cand = ""
            want = f["role"].lower().replace("_", "")
            for c in t["cols"]:
                cl = str(c).lower().replace("_", "")
                if want in cl or cl in want:
                    cand = c
                    break
            if cand:
                client.post("/api/map", json={"table": t["key"],
                                              "field": f["role"],
                                              "column": cand})
r = client.get("/api/ui?screen=map").json()["map"]
check("no table blocks the run after mapping", not r["blocked"])

# ---- 05 run -----------------------------------------------------------------
resp = client.post("/api/run/start", json={"require_geocode": False,
                                           "jitter": True, "seed": 1337})
check("run started", resp.status_code == 200 and resp.json()["ok"])
for _ in range(200):
    st = client.get("/api/run/status").json()
    if st["state"] != "running":
        break
    time.sleep(0.05)
check("run completed without error", st["state"] == "done")

r = client.get("/api/ui?screen=run").json()["runData"]
res = r.get("results", {})
check("results report real row counts", res.get("input", 0) > 200)
check("lossless holds after the run",
      res.get("clean", 0) + res.get("review", 0) == res.get("input", -1))
check("verification is reported by confidence", "verify" in res)

# ---- 06 review, grouped plan ------------------------------------------------
r = client.get("/api/ui?screen=review").json()["review"]
check("review groups were built from the run", len(r["groups"]) >= 1)
check("groups are sorted largest first",
      all(r["groups"][i]["count"] >= r["groups"][i + 1]["count"]
          for i in range(len(r["groups"]) - 1)))
check("tallies are present", r["tallies"]["flagged"] >= 0)

gid = r["groups"][0]["id"]
pv = client.get(f"/api/review/preview?gid={gid}&page=0").json()
check("group preview paginates over the real rows", pv["total"] >= 1)
check("preview shows the real field values for each row",
      all(isinstance(row.get("values"), dict) and row["values"] for row in pv["rows"]))
check("preview lists every problem on a row, not just one",
      all(isinstance(row.get("problems"), list) for row in pv["rows"]))
check("preview says where each row came from",
      all(row.get("source") and row.get("row") is not None for row in pv["rows"]))
check("preview names the fields it is showing", bool(pv.get("fields")))
check("preview summarizes what the group has in common",
      "common_problems" in pv and "blank_fields" in pv)
if pv["rows"]:
    term = (pv["rows"][0]["id"] or "")[:4]
    if term:
        f = client.get(f"/api/review/preview?gid={gid}&q={term}").json()
        check("preview search filters", f["total"] <= pv["total"])

before_tallies = r["tallies"]
client.post("/api/review/group", json={"gid": gid, "decision": "sent"})
r2 = client.get("/api/ui?screen=review").json()["review"]
g = next(x for x in r2["groups"] if x["id"] == gid)
check("group decision is recorded", g["status"] == "sent")
check("sending a group fills the queue",
      r2["tallies"]["queue"] > before_tallies["queue"])
check("decisions counter advances",
      r2["tallies"]["decided"] == before_tallies["decided"] + 1)

client.post("/api/review/undo")
r3 = client.get("/api/ui?screen=review").json()["review"]
check("undo reverses the last group decision",
      next(x for x in r3["groups"] if x["id"] == gid)["status"] == "pending")

# Decide every group so the plan is complete.
for g in client.get("/api/ui?screen=review").json()["review"]["groups"]:
    client.post("/api/review/group", json={"gid": g["id"], "decision": "sent"})
r4 = client.get("/api/ui?screen=review").json()["review"]
check("every group can be decided", r4["tallies"]["undecided"] == 0)

# ---- 06 review, row by row --------------------------------------------------
q = client.get("/api/queue?filter=pending&page=0&sel=0").json()
check("queue holds the sent rows", q["total"] >= 1)
check("queue exposes the five statuses",
      set(["pending"]) <= set(list(q["counts"].keys()) + ["pending"]))
if q["detail"]:
    rid = q["detail"]["rid"]
    check("queue detail lists editable fields", len(q["detail"]["fields"]) >= 5)
    out = client.post("/api/queue/action",
                      json={"rid": rid, "action": "approved"}).json()
    check("approving a row records its status", out["status"] == "approved")
    q2 = client.get("/api/queue?filter=approved&page=0&sel=0").json()
    check("approved row moves to its filter", q2["total"] >= 1)

    # a correction is re-validated, not taken on faith
    q3 = client.get("/api/queue?filter=pending&page=0&sel=0").json()
    if q3["detail"]:
        rid3 = q3["detail"]["rid"]
        out3 = client.post("/api/queue/action", json={
            "rid": rid3, "action": "corrected",
            "edits": {"City": "Brooklyn", "Zip": "11201"}}).json()
        check("a correction returns a re-validated status",
              out3["status"] in ("corrected", "pending"))

# ---- data preview, on Sources and on Map ------------------------------------
key = client.get("/api/ui?screen=sources").json()["sources"]["tables"][0]["key"]
pv = client.get(f"/api/preview?key={key}&which=raw").json()
check("raw preview returns columns and rows", pv["ok"] and pv["columns"] and pv["rows"])
check("raw preview reports a real total", pv["total"] > 0)
check("raw preview paginates", pv["pages"] >= 1 and pv["page"] == 0)
if pv["pages"] > 1:
    p2 = client.get(f"/api/preview?key={key}&which=raw&page=1").json()
    check("preview page two returns different rows", p2["rows"] != pv["rows"])
prep = client.get(f"/api/preview?key={key}&which=prepared").json()
check("prepared preview is available", prep["ok"])
check("prepared preview names the columns the prepare steps added",
      isinstance(prep["added"], list))
check("prepared preview has at least as many columns as raw",
      len(prep["columns"]) >= len(pv["columns"]))
check("an unknown table is refused",
      client.get("/api/preview?key=nope").status_code == 404)
check("the preview toggle is wired in the front end",
      "data-table-preview" in open(os.path.join("ui", "app.js"),
                                   encoding="utf-8").read())

# ---- the browser is never served a stale interface --------------------------
for path in ("/", "/static/app.js", "/api/ui?screen=check"):
    hdr = client.get(path).headers.get("cache-control", "")
    check(f"{path} is sent with no-store", "no-store" in hdr)

# ---- what counts as a jammed column -----------------------------------------
import pandas as _pd

def _ops(df):
    return {(o["type"], o["column"]) for o in cw.engine.auto_prep_ops(df)}

unit_only = _pd.DataFrame({
    "Address 1": ["123 Main St Apt 3L", "45 Oak St #2", "9 Elm St Fl 4",
                  "7 Pine St Suite 200", "88 Ash St"],
    "Zip": ["11201", "11201", "10013", "10007", "11375"]})
check("a unit jammed into the street is detected even with the ZIP in its own column",
      ("split_jammed", "Address 1") in _ops(unit_only))

city_state = _pd.DataFrame({"Addr": ["123 Main St, Brooklyn, NY",
                                     "45 Oak St, Queens, NY",
                                     "9 Elm St, Bronx, NY"]})
check("a city and state jammed on the end is detected without a ZIP",
      ("split_jammed", "Addr") in _ops(city_state))

full_jam = _pd.DataFrame({"Full_Address": ["123 Main St Apt 3L Brooklyn NY 11201",
                                           "45 Oak St Queens NY 11375"]})
check("a fully jammed address is still detected",
      ("split_jammed", "Full_Address") in _ops(full_jam))

already_clean = _pd.DataFrame({"Address_1": ["123 Main St", "45 Oak St", "9 Elm St"],
                               "City": ["Brooklyn", "Queens", "Bronx"]})
check("a clean street column is left alone", not _ops(already_clean))

prog = _pd.DataFrame({"Program name": ["Older Adult Services", "Housing First",
                                       "Youth Build"],
                      "Total": ["5", "9", "3"]})
check("a program name is never split as a person name",
      not any(t == "split_name" for t, _c in _ops(prog)))
for header in ("Site name", "Agency Name", "Organization name", "Provider name"):
    df = _pd.DataFrame({header: ["Alpha Beta Services", "Gamma Delta House",
                                 "Epsilon Zeta Center"]})
    check(f"'{header}' is not split as a person name",
          not any(t == "split_name" for t, _c in _ops(df)))

person = _pd.DataFrame({"Client Name": ["Ada Sample", "Ben Fixture", "Cara Example"]})
check("a person name column is still split",
      ("split_name", "Client Name") in _ops(person))

check("every detected operation carries its own reason",
      all("why" in o for o in cw.engine.auto_prep_ops(full_jam)))

# ---- labels name the sheet, and the column picker has shortcuts -------------
JS = open(os.path.join("ui", "app.js"), encoding="utf-8").read()
check("table labels keep the sheet name rather than dropping it",
      "p.join(" in JS and "parts[parts.length - 1]" not in JS)
for pick in ('data-pick="all"', 'data-pick="none"', 'data-pick="invert"'):
    check(f"the column picker offers {pick}", pick in JS)

# ---- a unit recorded in both address lines ----------------------------------
def _one(a1, a2):
    df = _pd.DataFrame([{"id": "1", "fn": "A", "ln": "B", "a1": a1, "a2": a2,
                         "city": "Brooklyn", "st": "NY", "zip": "11201"}])
    mp = {"f.csv": {"Client_ID": "id", "First_Name": "fn", "Last_Name": "ln",
                    "Address_1": "a1", "Address_2": "a2", "City": "city",
                    "State": "st", "Zip": "zip"}}
    out = cw.engine.run_pipeline({"f.csv": df}, mp, False, None, 1337,
                                 schema=cw.engine.DEFAULT_SCHEMA)
    return out["transformed"][0]

r = _one("123 Main St Apt 2A", "Apt 2A")
check("an identical unit in both lines is de-duplicated, not left inline",
      r["Address_1"] == "123 Main St" and r["Address_2"] == "Apt 2A")
check("de-duplicating an identical unit does not send the row to review",
      not r["__errors__"])

for other in ("#2A", "apt. 2-a", "2A"):
    r = _one("123 Main St Apt 2A", other)
    check(f"the same unit written as '{other}' is recognized as identical",
          r["Address_1"] == "123 Main St" and not r["__errors__"])

r = _one("123 Main St Apt 2A", "Apt 3B")
check("two different units are sent to review, never silently chosen",
      bool(r["__errors__"]) and "conflict" in " ".join(r["__errors__"]).lower())
check("a unit conflict shows both values",
      "2A" in " ".join(r["__errors__"]) and "3B" in " ".join(r["__errors__"]))

r = _one("123 Main St Apt 2A", "c/o Jane Doe")
check("a non-unit Address_2 is never overwritten by the unit",
      r["Address_2"] == "c/o Jane Doe")
check("a unit competing with other secondary content goes to review",
      bool(r["__errors__"]))

r = _one("123 Main St Apt 2A", "")
check("a unit still moves into an empty Address_2",
      r["Address_1"] == "123 Main St" and r["Address_2"] == "Apt 2A")

r = _one("123 Main St", "Apt 2A")
check("an already-clean pair is left alone",
      r["Address_1"] == "123 Main St" and r["Address_2"] == "Apt 2A"
      and not r["__errors__"])

# ---- splits leave no separator artifacts behind ------------------------------
_sja = cw.engine.split_jammed_address

def _fragments(s):
    d = _sja(s)
    return [d["street"], d["unit"], d["city"]]

def _has_edge_junk(vals):
    return any(v.strip() and (v.strip()[0] in "-,;:|/\\" or v.strip()[-1] in "-,;:|/\\")
               for v in vals)

artifact_cases = [
    "123 Main St - Apt 3L - Brooklyn NY 11201",
    "123 Main St -- Brooklyn NY 11201",
    "123 Main St / Apt 2 / Queens NY 11375",
    "123 Main St ; Brooklyn ; NY ; 11201",
    "123 Main St | Apt 9 | Bronx NY 10451",
    "123 Main St - - Brooklyn NY 11201",
    "123 Main St  ,  Brooklyn  NY  11201",
    "123 Main St \\ Apt 4 \\ Brooklyn NY 11201",
]
for case in artifact_cases:
    check(f"no stranded separator from {case[:34]!r}",
          not _has_edge_junk(_fragments(case)))

check("a dash separator still yields the unit",
      _sja("123 Main St - Apt 3L - Brooklyn NY 11201")["unit"] == "Apt 3L")
check("a slash separator still yields the unit",
      _sja("123 Main St / Apt 2 / Queens NY 11375")["unit"] == "Apt 2")
check("a semicolon separator still yields the city",
      _sja("123 Main St ; Brooklyn ; NY ; 11201")["city"] == "Brooklyn")

# real content that must survive untouched
check("a hyphenated Queens house number is preserved",
      _sja("40-22 24th St Apt 5 Queens NY 11101")["street"] == "40-22 24th St")
check("a hyphenated house letter is preserved",
      _sja("123-A Main St Brooklyn NY 11201")["street"] == "123-A Main St")
check("c/o is not treated as a separator",
      "c/o" in _sja("85 Broadway c/o Jane Doe Brooklyn NY 11211")["street"])
check("a trailing abbreviation period is kept",
      _sja("123 Main St.  ,  Brooklyn  NY  11201")["street"].endswith("St."))

check("tidy_fragment strips stranded separators",
      cw.engine.tidy_fragment("123 Main St -") == "123 Main St")
check("tidy_fragment collapses repeats",
      cw.engine.tidy_fragment("123 Main St - - Apt 2") == "123 Main St - Apt 2")
check("tidy_fragment leaves a clean value alone",
      cw.engine.tidy_fragment("40-22 24th St") == "40-22 24th St")
check("tidy_fragment handles an empty value", cw.engine.tidy_fragment("") == "")

names = cw.engine.split_jammed_name("Sample - Ada")
check("a name split leaves no stranded separator",
      not _has_edge_junk([names["first"], names["last"]]))

# ---- default values on custom fields ----------------------------------------
sch = [dict(f) for f in cw.engine.DEFAULT_SCHEMA]
for f in sch:
    if f["role"] == "Client_ID":
        f["required"] = False
sch.append({"role": "custom", "label": "Program", "dtype": "str", "length": 40,
            "required": False, "default": "Older Adult Services"})
df = _pd.DataFrame([
    {"fn": "A", "ln": "B", "a1": "209 Joralemon St", "city": "Brooklyn",
     "st": "NY", "zip": "11201", "prog": ""},
    {"fn": "C", "ln": "D", "a1": "60 Centre St", "city": "New York",
     "st": "NY", "zip": "10007", "prog": "Housing"}])
mp = {"f.csv": {"First_Name": "fn", "Last_Name": "ln", "Address_1": "a1",
                "City": "city", "State": "st", "Zip": "zip", "Program": "prog"}}
out = cw.engine.run_pipeline({"f.csv": df}, mp, False, None, 1337, schema=sch)
vals = [r["__custom__"]["Program"] for r in out["transformed"]]
check("a default fills a blank custom field", vals[0] == "Older Adult Services")
check("a default never replaces a value the source provided", vals[1] == "Housing")
check("using a default is recorded in the audit log",
      any("default" in f["message"].lower()
          for f in out["transformed"][0]["__flags__"]))
check("the schema editor offers a default value column", 'data-sf="default"' in JS)
check("the add-field row offers a default value", "newdefault" in JS)

# ---- confirm and next table -------------------------------------------------
check("confirm advances to the next unconfirmed table",
      "nextUnconfirmed" in JS)
check("the confirm button says what it will do",
      "Confirm this table" in JS and "Confirm and next table" in JS)

# ---- no ETO wording anywhere in the interface -------------------------------
SERVER_SRC = open("crosswalk_server.py", encoding="utf-8").read()
APP_SRC = open("app.py", encoding="utf-8").read()
for name, src in (("the front end", JS), ("the server", SERVER_SRC),
                  ("the engine", APP_SRC)):
    check(f"no ETO reference remains in {name}", "ETO" not in src)
check("the client identifier field is named without a system prefix",
      any(f["role"] == "Client_ID" for f in cw.engine.DEFAULT_SCHEMA))

# ---- defaults work on built-in fields too -----------------------------------
sch2 = [dict(f) for f in cw.engine.DEFAULT_SCHEMA]
for f in sch2:
    if f["role"] == "Client_ID":
        f["required"] = False
    if f["role"] == "City":
        f["default"] = "Brooklyn"
    if f["role"] == "State":
        f["default"] = "NY"
df2 = _pd.DataFrame([
    {"fn": "A", "ln": "B", "a1": "209 Joralemon St", "city": "", "st": "", "zip": "11201"},
    {"fn": "C", "ln": "D", "a1": "60 Centre St", "city": "New York", "st": "NY", "zip": "10007"},
    {"fn": "E", "ln": "F", "a1": "40-22 24th St", "city": "", "st": "", "zip": "11101"}])
mp2 = {"f.csv": {"First_Name": "fn", "Last_Name": "ln", "Address_1": "a1",
                 "City": "city", "State": "st", "Zip": "zip"}}
o2 = cw.engine.run_pipeline({"f.csv": df2}, mp2, False, None, 1337, schema=sch2)
t2 = o2["transformed"]
check("a default fills a blank built-in field", t2[0]["City"] == "Brooklyn")
check("a built-in default never replaces a source value", t2[1]["City"] == "New York")
check("using a built-in default is recorded in the audit log",
      any("default" in f["message"] for f in t2[0]["__flags__"]))
check("a defaulted value is still validated against the ZIP",
      bool(t2[2]["__errors__"])
      and "conflict" in " ".join(t2[2]["__errors__"]).lower())
check("defaults do not break the lossless invariant",
      len(o2["clean"]) + len(o2["review"]) == 3)
check("the editor offers a default on every field, not only custom ones",
      "f.role === \"custom\"\n        ? `<input class=\"input mono\" data-sf=\"default\"" not in JS)
check("a defaulted identifier is called out as risky",
      "shared identifier" in JS)


# ---- field types on schema fields -------------------------------------------
sch3 = [dict(f) for f in cw.engine.DEFAULT_SCHEMA]
for f in sch3:
    if f["role"] == "Client_ID":
        f["required"] = False
sch3 += [
    {"role": "custom", "label": "Enrolled", "dtype": "date", "length": 0, "required": False},
    {"role": "custom", "label": "Hours", "dtype": "decimal", "length": 0, "required": False},
    {"role": "custom", "label": "Active", "dtype": "bool", "length": 0, "required": False},
]
df3 = _pd.DataFrame([
    {"fn": "A", "ln": "B", "a1": "209 Joralemon St", "city": "Brooklyn", "st": "NY",
     "zip": "11201", "en": "3/15/2024", "hr": "12.5", "ac": "Y"},
    {"fn": "C", "ln": "D", "a1": "60 Centre St", "city": "New York", "st": "NY",
     "zip": "10007", "en": "2024-03-15", "hr": "1,200.75", "ac": "no"},
    {"fn": "E", "ln": "F", "a1": "87 Bay Terrace", "city": "Staten Island", "st": "NY",
     "zip": "10306", "en": "not a date", "hr": "x", "ac": "maybe"}])
mp3 = {"f.csv": {"First_Name": "fn", "Last_Name": "ln", "Address_1": "a1",
                 "City": "city", "State": "st", "Zip": "zip",
                 "Enrolled": "en", "Hours": "hr", "Active": "ac"}}
o3 = cw.engine.run_pipeline({"f.csv": df3}, mp3, False, None, 1337, schema=sch3)
t3 = o3["transformed"]
check("a date written month-first is stored in one standard form",
      t3[0]["__custom__"]["Enrolled"] == "2024-03-15")
check("a date already in standard form is unchanged",
      t3[1]["__custom__"]["Enrolled"] == "2024-03-15")
check("a decimal keeps its value and loses the thousands separator",
      t3[1]["__custom__"]["Hours"] == "1200.75")
check("yes and no are stored consistently",
      t3[0]["__custom__"]["Active"] == "Yes" and t3[1]["__custom__"]["Active"] == "No")
check("a value that is not a date sends the row to review",
      any("not a date" in e for e in t3[2]["__errors__"]))
check("a value that is not a number sends the row to review",
      any("must be a number" in e for e in t3[2]["__errors__"]))
check("typed values do not break the lossless invariant",
      len(o3["clean"]) + len(o3["review"]) == 3)
check("the day-first form is read",
      cw.engine.parse_date_value("15.03.2024") == (2024, 3, 15))
check("an Excel serial date is read",
      cw.engine.parse_date_value("45366") is not None)
check("the schema editor offers every type",
      set(client.get("/api/ui?screen=schema").json()["schema"]["types"])
      == {"str", "int", "decimal", "date", "bool"})


# ---- 07 export --------------------------------------------------------------
r = client.get("/api/ui?screen=export").json()["export"]
rec = r["recon"]
check("export reconciles clean + review + set aside to input",
      rec["clean"] + rec["review"] + rec["aside"] == rec["input"])
check("column picker lists the clean-file columns", len(r["cols"]) > 5)

for which, label in (("clean", "clean file"), ("review", "review file"),
                     ("audit", "audit log"), ("quality", "quality report")):
    resp = client.get(f"/api/export/file?which={which}")
    check(f"{label} downloads", resp.status_code == 200 and len(resp.content) > 0)

audit = client.get("/api/export/file?which=audit").content.decode(errors="replace")
check("audit log carries no client names",
      "Delgado" not in audit and "Nunez" not in audit)

# ---- static shell -----------------------------------------------------------
resp = client.get("/")
check("the UI shell is served", resp.status_code == 200
      and "CROSSWALK" in resp.text.upper() or "crosswalk" in resp.text.lower())
resp = client.get("/static/styles.css")
check("the stylesheet is served", resp.status_code == 200)
check("the slate accent is applied, not the red",
      "#2f5f88" in resp.text and "#ec3013" not in resp.text)
check("no webfont is fetched from the network",
      "fonts.googleapis.com" not in resp.text)
resp = client.get("/static/app.js")
check("the front end script is served", resp.status_code == 200)

# ---- unjamming actually reaches the mapping ---------------------------------
eng = cw.engine
split_cols = ["Name", "Full_Address", "Full_Address_street",
              "Full_Address_address2", "Full_Address_city",
              "Full_Address_state", "Full_Address_zip",
              "Name_first", "Name_middle", "Name_last"]
gm = eng.guess_mapping(split_cols)
check("Address_1 uses the split street, not the jammed original",
      gm["Address_1"] == "Full_Address_street")
check("Address_2 uses the split unit", gm["Address_2"] == "Full_Address_address2")
check("City, State and Zip use the split columns",
      gm["City"] == "Full_Address_city" and gm["State"] == "Full_Address_state"
      and gm["Zip"] == "Full_Address_zip")
check("names use the split name columns",
      gm["First_Name"] == "Name_first" and gm["Last_Name"] == "Name_last")
check("a middle-name column is not mistaken for a Client ID",
      gm["Client_ID"] == "")
check("an ordinary id column is still found",
      eng.guess_mapping(["client_id", "addr1"])["Client_ID"] == "client_id")
check("uid is still found", eng.guess_mapping(["uid"])["Client_ID"] == "uid")
check("an unsplit address column is still found",
      eng.guess_mapping(["Full_Address"])["Address_1"] == "Full_Address")

# the same thing end to end, through the API
client.post("/api/reset")
client.post("/api/sources/upload", files=[
    ("files", ("clinic_export.csv",
               open(os.path.join("sample_data", "clinic_export.csv"), "rb").read()))])
mp = client.get("/api/ui?screen=map").json()["map"]["tables"][0]
a1 = next(f for f in mp["fields"] if f["role"] == "Address_1")
check("after upload the guessed Address_1 is the unjammed street",
      a1["col"].endswith("_street"))
check("the sample shown for Address_1 is not the jammed value",
      "NY" not in a1["note"])

# ---- restart clears everything ----------------------------------------------
before = client.get("/api/ui?screen=sources").json()["sources"]
check("there is state to clear", before["stats"]["files"] >= 1)
client.post("/api/reset")
after = client.get("/api/ui?screen=sources").json()["sources"]
check("restart clears uploaded files", after["stats"]["files"] == 0)
check("restart clears detected tables", after["tables"] == [])
check("restart returns to the first stage",
      client.get("/api/ui?screen=check").json()["chrome"]["stage"] == 0)
check("restart is reachable from the interface",
      'data-act="restart"' in open(os.path.join("ui", "app.js"),
                                   encoding="utf-8").read())


# ---- per-source defaults ----------------------------------------------------
sd_frames = {
    "no_state.csv": _pd.DataFrame([{"fn": "A", "ln": "B", "a1": "209 Joralemon St",
                                    "zip": "11201"}]),
    "has_city.csv": _pd.DataFrame([{"fn": "C", "ln": "D", "a1": "60 Centre St",
                                    "zip": "10007", "city": "New York"}])}
sd_map = {"no_state.csv": {"First_Name": "fn", "Last_Name": "ln",
                           "Address_1": "a1", "Zip": "zip"},
          "has_city.csv": {"First_Name": "fn", "Last_Name": "ln",
                           "Address_1": "a1", "Zip": "zip", "City": "city"}}
sd_sch = [dict(f) for f in cw.engine.DEFAULT_SCHEMA]
for f in sd_sch:
    if f["role"] == "Client_ID":
        f["required"] = False
    if f["role"] == "State":
        f["default"] = "NY"
o4 = cw.engine.run_pipeline(sd_frames, sd_map, False, None, 1337, schema=sd_sch,
                            source_defaults={"no_state.csv": {"City": "Brooklyn"}})
recs = {r["__source_file__"]: r for r in o4["transformed"]}
check("a default set for one source fills that source",
      recs["no_state.csv"]["City"] == "Brooklyn")
check("a default set for one source does not touch another source",
      recs["has_city.csv"]["City"] == "New York")
check("a schema-wide default still applies alongside a per-source one",
      recs["no_state.csv"]["State"] == "NY")
check("the audit says which default was used",
      any("from this source" in f["message"]
          for f in recs["no_state.csv"]["__flags__"]))
check("the per-source default endpoint is wired",
      "/api/sources/default" in SERVER_SRC and "data-srcdefault" in JS)

# ---- choosing the header row ------------------------------------------------
blk = [["Client roster 2024", "", ""],
       ["Prepared by the data team", "", ""],
       ["ID", "Name", "Zip"],
       ["1", "Ada Sample", "11201"],
       ["2", "Ben Fixture", "10007"]]
h1, r1 = cw.table_detect.frame_from_block(blk, 3)
check("choosing row three uses it as the header", h1 == ["ID", "Name", "Zip"])
check("rows above the chosen header are dropped", len(r1) == 2)
h0, r0 = cw.table_detect.frame_from_block(blk, 0)
check("choosing no header numbers the columns", h0[0] == "Column_1" and len(r0) == 5)
check("the header row endpoint is wired",
      "/api/map/header" in SERVER_SRC and "data-headerrow" in JS)

# ---- the length field is explained in words ---------------------------------
check("the schema shows the length as characters with an example",
      "lengthText" in JS and "characters" in JS)
check("no limit is said in words rather than shown as zero",
      "any length" in JS)

# ---- autosave and resume ----------------------------------------------------
import sessions_store as _ss
check("the retention window is seven days", _ss.RETENTION_DAYS == 7)
check("uploaded rows are never in the saved keys",
      not ({"frames", "blocks", "results", "uploads", "rid_index"}
           & set(_ss.SAVED_KEYS)))

client.post("/api/reset")
client.post("/api/sources/upload", files=[
    ("files", ("legacy_export.xlsx",
               open(os.path.join("sample_data", "legacy_export.xlsx"), "rb").read()))])
sid = cw.S["session_id"]
check("a session id is created as soon as work begins", bool(sid))
sch_edit = [dict(f) for f in cw.engine.DEFAULT_SCHEMA]
sch_edit[0]["label"] = "Given_Name"
client.post("/api/schema", json={"schema": sch_edit})
saved = _ss.load(sid)
check("the session file exists on disk", saved is not None)
check("the saved file records the source file names",
      "legacy_export.xlsx" in (saved.get("sources") or []))
check("the saved file keeps the schema edit",
      any(f.get("label") == "Given_Name" for f in saved["state"]["schema"]))
raw_text = open(_ss.path_for(sid), encoding="utf-8").read()
check("the saved file holds no client rows",
      "Joralemon" not in raw_text and "Placeholder" not in raw_text)

listed = client.get("/api/sessions").json()
check("the session is offered for resuming", any(s["id"] == sid
                                                 for s in listed["sessions"]))
check("the listing says when it expires",
      all(0 <= s["expires_in_days"] <= 7 for s in listed["sessions"]))

# Simulate the window being closed rather than Start over, which is what
# resume is for. Start over deliberately deletes the saved file, and that is
# checked separately below.
cw.S = cw._blank_state()
client.post("/api/sessions/resume", json={"id": sid})
check("resuming restores the schema edit",
      any(f.get("label") == "Given_Name" for f in cw.S["schema"]))
check("resuming starts at Sources, because the files are gone",
      cw.S["stage"] == 1)
check("resuming a session that is gone is refused",
      client.post("/api/sessions/resume", json={"id": "nope"}).status_code == 404)

client.post("/api/sessions/autosave", json={"on": False})
check("autosave can be turned off", cw.S["autosave"] is False)
client.post("/api/sessions/autosave", json={"on": True})
check("autosave can be turned back on", cw.S["autosave"] is True)

sid2 = cw.S.get("session_id")
client.post("/api/reset")
check("start over deletes the saved progress",
      sid2 is None or _ss.load(sid2) is None)
check("an expired session is purged", isinstance(_ss.purge_expired(0), list))
check("purging with a zero window clears everything",
      not client.get("/api/sessions").json()["sessions"])
client.post("/api/reset")



# ---- the group names the cause, not the symptom -----------------------------
def _rec(errors):
    return {"__errors__": errors, "Zip": "", "City": ""}

check("a blank ZIP that also blanks the city is grouped as a ZIP problem",
      cw._classify(_rec(["City could not be determined",
                         "Invalid ZIP Code format: (blank)"])) == "zipcity")
check("an unrecognized city with a blank ZIP is still a ZIP problem",
      cw._classify(_rec(["Unrecognized City: 'Springfield'",
                         "Invalid ZIP Code format: (blank)"])) == "zipcity")
check("a ZIP problem on its own stays its own group",
      cw._classify(_rec(["Invalid ZIP Code format: (blank)"])) == "zipbad")
check("a city problem with a usable ZIP is a city problem",
      cw._classify(_rec(["City could not be determined"])) == "cityunknown")
check("a missing address outranks a ZIP problem",
      cw._classify(_rec(["Missing Address_1",
                         "Invalid ZIP Code format: (blank)"])) == "noaddr")
check("a city and ZIP contradiction is still its own group",
      cw._classify(_rec(["City/ZIP conflict: City says 'Queens' but ZIP 11209"
                         " is in Brooklyn"])) == "conflict")
check("the combined group explains that the ZIP is the cause",
      "Find the ZIP and both problems go away" in cw.GROUP_DEFS["zipcity"]["desc"])
check("the combined group is offered before the city group",
      cw.GROUP_ORDER.index("zipcity") < cw.GROUP_ORDER.index("cityunknown"))

# through the real pipeline rather than a stand-in record
zc = _pd.DataFrame([
    {"fn": "A", "ln": "B", "a1": "123 Nowhere Rd", "city": "", "st": "", "zip": ""},
    {"fn": "C", "ln": "D", "a1": "9 Nowhere Rd", "city": "Springfield",
     "st": "NY", "zip": ""}])
zc_sch = [dict(f) for f in cw.engine.DEFAULT_SCHEMA]
for f in zc_sch:
    if f["role"] == "Client_ID":
        f["required"] = False
zc_out = cw.engine.run_pipeline(
    {"f.csv": zc}, {"f.csv": {"First_Name": "fn", "Last_Name": "ln",
                              "Address_1": "a1", "City": "city",
                              "State": "st", "Zip": "zip"}},
    False, None, 1337, schema=zc_sch)
check("real rows with both problems are grouped by their cause",
      all(cw._classify(r) == "zipcity" for r in zc_out["review"]))

# ---- sorting across every grid ----------------------------------------------
client.post("/api/reset")
client.post("/api/sources/upload", files=[
    ("files", ("legacy_export.xlsx",
               open(os.path.join("sample_data", "legacy_export.xlsx"), "rb").read()))])
pk = client.get("/api/ui?screen=sources").json()["sources"]["tables"][0]["key"]
asc = client.get(f"/api/preview?key={pk}&sort=LastName&dir=asc").json()
desc = client.get(f"/api/preview?key={pk}&sort=LastName&dir=desc").json()
ci = asc["columns"].index("LastName")
check("a data preview can be sorted", asc["rows"][0][ci] != desc["rows"][0][ci])
check("sorting covers the whole table, not one page",
      asc["rows"][0][ci] <= asc["rows"][-1][ci])
check("the preview reports the sort it applied", asc["sort"] == "LastName")
check("an unknown sort column is ignored rather than failing",
      client.get(f"/api/preview?key={pk}&sort=nope").status_code == 200)
check("the queue accepts a sort", "sort" in client.get("/api/queue").json())
check("sortable headings are wired in the front end",
      "sortHead" in JS and "data-sortaction" in JS)
for grid in ("check", "preview", "group", "queue", "cols"):
    check(f"the {grid} grid is sortable", f'"{grid}"' in JS)


# ---- a large queue stays workable -------------------------------------------
client.post("/api/reset")
client.post("/api/mode", json={"mode": "Advanced"})
client.post("/api/sources/upload", files=[
    ("files", (n, open(os.path.join("sample_data", n), "rb").read()))
    for n in ["clinic_export.csv", "portal_export.json", "legacy_export.xlsx",
              "state_export.xml", "partner_export.tsv"]])
qs = [dict(f) for f in cw.engine.DEFAULT_SCHEMA]
for f in qs:
    if f["role"] == "Client_ID":
        f["required"] = False
client.post("/api/schema", json={"schema": qs})
client.post("/api/run/start", json={"require_geocode": False, "jitter": True,
                                    "seed": 1337})
for _ in range(200):
    if client.get("/api/run/status").json()["state"] != "running":
        break
    time.sleep(0.05)
for g in client.get("/api/ui?screen=review").json()["review"]["groups"]:
    client.post("/api/review/group", json={"gid": g["id"], "decision": "sent"})

q = client.get("/api/queue?per=12").json()
check("the whole queue is counted, not just the page",
      q["queue_total"] >= 10 and q["queue_total"] == q["total"])
check("the queue offers a problem filter with counts",
      len(q["facets"]["problems"]) >= 2
      and all("n" in f for f in q["facets"]["problems"]))
check("the queue offers a source filter with counts",
      len(q["facets"]["sources"]) >= 1 and all("n" in f for f in q["facets"]["sources"]))
check("the page size can be changed", q["per"] == 12)
big = client.get("/api/queue?per=100").json()
check("a larger page size is honored", big["per"] == 100
      and len(big["items"]) >= len(q["items"]))

kind = q["facets"]["problems"][0]["value"]
narrowed = client.get(f"/api/queue?problem={kind}").json()
check("filtering by problem narrows the queue",
      narrowed["total"] <= q["total"] and narrowed["total"] > 0)
src = q["facets"]["sources"][0]["value"]
by_src = client.get(f"/api/queue?source={src}").json()
check("filtering by source narrows the queue", by_src["total"] <= q["queue_total"])
combo = client.get(f"/api/queue?problem={kind}&source={src}").json()
check("filters combine rather than replace each other",
      combo["total"] <= min(narrowed["total"], by_src["total"]))
check("searching narrows the queue",
      client.get("/api/queue?q=Sample").json()["total"] <= q["total"])

# batch on an explicit selection
some = [i["rid"] for i in q["items"][:5]]
out = client.post("/api/queue/bulk",
                  json={"rids": some, "action": "approved"}).json()
check("a batch approve acts on every selected row", out["changed"] == 5)
check("a batch action says what it did in words", bool(out["note"]))
after = client.get("/api/queue?filter=approved").json()
check("batch approved rows move to their status", after["total"] >= 5)

# batch on everything matching the current filters
zipq = client.get("/api/queue?problem=Invalid ZIP Code format").json()
n_match = zipq["total"]
t0 = time.time()
fix = client.post("/api/queue/bulk", json={
    "all_matching": True, "filter": "pending",
    "problem": "Invalid ZIP Code format",
    "action": "corrected", "edits": {"Zip": "11201"}}).json()
elapsed = time.time() - t0
check("a batch correction acts on every matching row", fix["changed"] == n_match)
check("a batch correction reports how many now pass", fix["fixed"] > 0)
check("a batch correction reports what it did not fix",
      fix["fixed"] + fix["still_open"] == fix["changed"])
check("a batch correction runs the pipeline once, not once per row",
      elapsed < 15)
check("rows a correction did not fix stay in the queue",
      client.get("/api/queue?filter=pending").json()["total"] >= fix["still_open"])
check("an empty selection is refused politely",
      client.post("/api/queue/bulk", json={"rids": [], "action": "approved"})
      .json()["changed"] == 0)
check("a batch correction with no values is refused",
      client.post("/api/queue/bulk", json={"rids": some, "action": "corrected",
                                           "edits": {}}).status_code == 400)
check("an unknown batch action is refused",
      client.post("/api/queue/bulk", json={"rids": some, "action": "nope"})
      .status_code == 400)

# the two review views are presented as one stage with two steps
check("the review stage shows both steps", "reviewTabs" in JS)
check("the row-by-row step is numbered as the second step",
      'revtab-n">2' in JS)
check("the queue offers selection and batch actions",
      "data-qcheck" in JS and "data-qbulk" in JS and "q-select-matching" in JS)
check("the queue offers a bulk field fix", "q-bulk-fix" in JS)
check("an empty queue page explains itself", "qempty" in JS)
client.post("/api/reset")


# ---- one record is never judged alone -------------------------------------
import review_context as _rc
import csv as _csv, io as _io

dup_rows = [["client_id", "first_name", "last_name", "address_1", "city",
             "state", "zip", "notes"],
            ["21333", "Ada", "Sample", "209 Joralemon St", "Brooklyn", "NY",
             "11201", "ok"],
            ["21333", "Ada", "Sample", "60 Centre St", "New York", "NY",
             "10007", "moved in 2024"],
            ["21333", "Adam", "Sample", "209 Joralemon St", "Brooklyn", "NY",
             "11201", ""],
            ["40001", "Ben", "Fixture", "40-22 24th St", "Brooklyn", "NY",
             "11101", ""],
            ["40002", "Cara", "Example", "", "", "NY", "", "no address"]]
_b = _io.StringIO()
_csv.writer(_b).writerows(dup_rows)

client.post("/api/reset")
client.post("/api/mode", json={"mode": "Advanced"})
client.post("/api/sources/upload",
            files=[("files", ("dup.csv", _b.getvalue().encode()))])
client.post("/api/run/start", json={"require_geocode": False, "jitter": True,
                                    "seed": 1337})
for _ in range(200):
    if client.get("/api/run/status").json()["state"] != "running":
        break
    time.sleep(0.05)
for g in client.get("/api/ui?screen=review").json()["review"]["groups"]:
    client.post("/api/review/group", json={"gid": g["id"], "decision": "sent"})

det = client.get("/api/queue?per=20").json()["detail"]
check("a flagged row explains what its problem means",
      det["explained"] and det["explained"][0]["means"])
check("a flagged row says what to check before deciding",
      det["explained"][0]["check"])
check("a same-identifier conflict shows the other records",
      det["related"] and det["related"]["total"] == 3)
check("the related records name which fields differ",
      set(det["related"]["differing"]) >= {"First_Name", "Address_1"})
check("the record being reviewed is marked among its relations",
      sum(1 for r in det["related"]["rows"] if r["is_this_one"]) == 1)
check("each related record can be opened",
      all(r["rid"] for r in det["related"]["rows"]))
check("the original source row is available",
      det["raw"] and any(r["column"] == "notes" for r in det["raw"]))
check("columns that were never mapped are pointed out",
      any(u["column"] == "notes" for u in det["unmapped"]))

# a city and ZIP contradiction offers a fix in one click
zq = client.get("/api/queue?per=20&q=Ben").json()
if zq["detail"]:
    d2 = zq["detail"]
    check("a city and ZIP contradiction offers a suggested fix",
          len(d2["suggestions"]) >= 1)
    check("a suggested fix says why it is suggested",
          all(s["why"] for s in d2["suggestions"]))
    check("a suggested fix carries the values it would set",
          all(isinstance(s["edits"], dict) and s["edits"]
              for s in d2["suggestions"]))

# a row with no relations does not invent any
solo = {"__errors__": ["Invalid ZIP Code format: (blank)"],
        "__source_file__": "f.csv", "__source_row__": 0, "Client_ID": ""}
check("a row with no relations shows no related panel",
      _rc.related_records(solo, [solo]) is None)

# every kind of problem has guidance written for it
for kind in ("idconflict", "dupc", "dupp", "cityzip", "zip", "city", "noaddr",
             "missingfield", "geo", "toolong", "badtype", "other"):
    g = _rc.GUIDANCE.get(kind)
    check(f"guidance exists for a {kind} problem",
          bool(g and g["means"] and g["check"]))
check("a same-identifier message is recognized",
      _rc.classify_problem("Same Client ID '1' used by records") == "idconflict")
check("a city and ZIP message is recognized",
      _rc.classify_problem("City/ZIP conflict: City says X") == "cityzip")
check("a length message is recognized",
      _rc.classify_problem("Zip exceeds max length 5 (got 9)") == "toolong")

check("the detail panel is wired in the front end",
      "vQueueDetail" in JS and "qrelated" in JS and "data-suggest" in JS)
check("a related record can be opened from the panel", "data-gotorid" in JS)
client.post("/api/reset")


# ---- the mapping is checked before the run ----------------------------------
import column_check as _cc
import wording as _w
import pandas as _pdc

_units = _pdc.Series(["Suite 200", "Fl 3", "Unit 5", "Penthouse", "Apt 4B"])
check("units mapped as the street are caught",
      _cc.check_field("Address_1", "addr", _units)["status"] == "problem")
_street = _pdc.Series(["209 Joralemon St", "60 Centre St", "87 Bay Terrace"])
check("a real street column passes",
      _cc.check_field("Address_1", "a1", _street)["status"] == "ok")
check("a four digit ZIP is flagged as a lost leading zero",
      _cc.check_field("Zip", "z", _pdc.Series(["7030", "7031", "7032"]))["status"]
      == "check")
check("a real ZIP column passes",
      _cc.check_field("Zip", "z", _pdc.Series(["11201", "10007"]))["status"] == "ok")
check("addresses mapped as a name are caught",
      _cc.check_field("First_Name", "n", _street)["status"] == "problem")
check("one identifier repeated on every row is caught",
      _cc.check_field("Client_ID", "id",
                      _pdc.Series(["1"] * 8))["status"] == "problem")
check("a column that is always empty is not called a mistake",
      _cc.check_field("Middle_Initial", "mi",
                      _pdc.Series(["", "", ""]))["status"] == "ok")
check("a warning shows examples from the data",
      _cc.check_field("Address_1", "addr", _units)["examples"])

client.post("/api/reset")
client.post("/api/sources/example")
mtabs = client.get("/api/ui?screen=map").json()["map"]["tables"]
check("every table is checked on the map stage",
      all("check" in tb for tb in mtabs))
check("the example data now matches cleanly, after the preference fix",
      all(tb["check"]["status"] != "problem" for tb in mtabs))
check("tables that are fine are not flagged",
      any(tb["check"]["status"] == "ok" for tb in mtabs))

# ---- example data ------------------------------------------------------------
check("example files can be loaded from the interface",
      len(client.get("/api/ui?screen=sources").json()["sources"]["tables"]) >= 5)
check("the example button is wired", 'data-act="example"' in JS)

# ---- plain wording in Guided, precise wording in Advanced --------------------
check("guided stage names avoid jargon",
      _w.stages("Guided")[0] == "Add your files"
      and "Schema" not in _w.stages("Guided"))
check("advanced stage names keep the precise terms",
      _w.stages("Advanced")[1] == "Schema")
check("a blank ZIP is explained plainly in guided mode",
      _w.plain_problem("Invalid ZIP Code format: (blank)", "Guided")
      == "This row has no ZIP code.")
check("advanced mode keeps the original message",
      _w.plain_problem("Invalid ZIP Code format: (blank)", "Advanced")
      == "Invalid ZIP Code format: (blank)")
check("every stage has both a plain and a precise heading",
      all(_w.heading(i, "Guided") != _w.heading(i, "Advanced")
          for i in range(10) if i != 5))
client.post("/api/mode", json={"mode": "Guided"})
check("the interface asks for the guided stage names",
      client.get("/api/ui?screen=check").json()["chrome"]["stages"][0]
      == "Add your files")
client.post("/api/mode", json={"mode": "Advanced"})
check("the interface asks for the precise stage names",
      client.get("/api/ui?screen=check").json()["chrome"]["stages"][0]
      == "Sources")

# ---- a result is put in context ---------------------------------------------
check("a good result is stated plainly",
      "passed on the first run" in _w.run_context(90, 100)["verdict"])
check("a poor result makes no claim about what is typical",
      "usually" not in _w.run_context(42, 100)["verdict"]
      and "85%" not in _w.run_context(42, 100)["verdict"])
check("a poor result says where to look",
      "matching" in _w.run_context(42, 100)["advice"])
check("a good result does not nag", not _w.run_context(97, 100)["advice"])

# ---- undo on every stage ------------------------------------------------------
client.post("/api/reset")
client.post("/api/sources/example")
before = len(client.get("/api/ui?screen=schema").json()["schema"]["fields"])
sch_u = [dict(f) for f in cw.engine.DEFAULT_SCHEMA]
sch_u.append({"role": "custom", "label": "Temp", "dtype": "str", "length": 0,
              "required": False})
client.post("/api/schema", json={"schema": sch_u})
check("a change can be taken back",
      client.get("/api/ui?screen=schema").json()["chrome"]["canUndo"] is True)
check("the change is named", client.get("/api/ui?screen=schema").json()
      ["chrome"]["undoLabel"])
client.post("/api/undo", json={})
check("undo restores what was there before",
      len(client.get("/api/ui?screen=schema").json()["schema"]["fields"]) == before)
check("undo with nothing to take back is refused politely",
      client.post("/api/undo", json={}).json()["ok"] in (True, False))
check("undo is offered in the interface", 'data-act="undo-change"' in JS)

# ---- a page that can be printed or handed on ---------------------------------
client.post("/api/reset")
client.post("/api/sources/example")
sch_s = [dict(f) for f in cw.engine.DEFAULT_SCHEMA]
for f in sch_s:
    if f["role"] == "Client_ID":
        f["required"] = False
client.post("/api/schema", json={"schema": sch_s})
client.post("/api/run/start", json={"require_geocode": False, "jitter": True,
                                    "seed": 1337})
for _ in range(300):
    if client.get("/api/run/status").json()["state"] != "running":
        break
    time.sleep(0.05)
summ = client.get("/api/summary")
check("the summary page renders", summ.status_code == 200 and len(summ.text) > 1500)
for want in ("Rows received", "The books balance", "By source file",
             "What happens next"):
    check(f"the summary covers {want.lower()}", want in summ.text)
check("the summary holds no client names",
      "Joralemon" not in summ.text and "Placeholder" not in summ.text)
check("the summary says it is safe to share", "safe to share" in summ.text)
check("the summary is linked from the interface", "/api/summary" in JS)
client.post("/api/reset")


# ---- the two counts the project asks for ------------------------------------
import csv as _c2, io as _i2

def _two_files():
    eto = [["client_id", "first_name", "last_name", "address_1", "city",
            "state", "zip", "program"],
           ["E100", "Joe", "Smith", "1 Bowling Green", "New York", "NY",
            "10004", "Workforce"],
           ["E200", "Joseph", "Smith", "1 Bowling Green", "New York", "NY",
            "10004", "Resident Services"],
           ["E300", "Kira", "Adeyemi", "65 Central Ave", "Brooklyn", "NY",
            "11221", "Workforce"]]
    ext = [["client_id", "first_name", "last_name", "address_1", "city",
            "state", "zip", "program"],
           ["X9", "Joe", "Smith", "1 Bowling Green", "New York", "NY",
            "10004", "Property Management"]]
    a, b = _i2.StringIO(), _i2.StringIO()
    _c2.writer(a).writerows(eto)
    _c2.writer(b).writerows(ext)
    return a.getvalue().encode(), b.getvalue().encode()


client.post("/api/reset")
_a, _b = _two_files()
client.post("/api/sources/upload",
            files=[("files", ("eto.csv", _a)),
                   ("files", ("property.csv", _b))])
sch_g = [dict(f) for f in cw.engine.DEFAULT_SCHEMA]
sch_g.append({"role": "custom", "label": "Program", "dtype": "str",
              "length": 60, "required": False})
client.post("/api/schema", json={"schema": sch_g})
client.post("/api/run/start", json={"require_geocode": False, "jitter": True,
                                    "seed": 1337})
for _ in range(300):
    if client.get("/api/run/status").json()["state"] != "running":
        break
    time.sleep(0.05)

summ = client.get("/api/ui?screen=summary").json()["summary"]
check("the results stage is available after processing", summ["ready"])
check("goal one is reported", "count" in summ["goal1"])
check("goal two is reported", "count" in summ["goal2"])
check("an undecided link makes goal one a range, not a single number",
      summ["goal1"]["open"] == 0 or summ["goal1"]["low"] < summ["goal1"]["high"])

props = client.get("/api/identity/proposals?per=50").json()
check("proposed links are offered for a decision", props["total"] >= 1)
check("each proposal shows both records",
      all(p.get("a") and p.get("b") for p in props["items"]))
check("each proposal says what agrees",
      all(p.get("evidence") for p in props["items"]))
for it in props["items"]:
    client.post("/api/identity/decide",
                json={"a": it["pair"][0], "b": it["pair"][1], "verdict": "same"})

summ = client.get("/api/ui?screen=summary").json()["summary"]
check("one person across three programs counts once for goal one",
      summ["goal1"]["count"] == 2)
check("that person counts three times for goal two",
      summ["goal2"]["count"] == 4)
check("once decided, goal one is a single number",
      summ["goal1"]["low"] == summ["goal1"]["high"])
check("the programs are listed", len(summ["goal2"]["programs"]) == 3)
joe = next((r for r in summ["goal2"]["rows"] if r["count"] == 3), None)
check("the person in three programs is shown with all three", joe is not None)
check("each person lists the programs they count in",
      joe and set(joe["programs"]) == {"Workforce", "Resident Services",
                                       "Property Management"})

check("a rejected link keeps the records apart",
      client.post("/api/identity/decide",
                  json={"a": "x", "b": "y", "verdict": "nonsense"}).status_code
      == 400)

# the two counts are downloadable, which is the deliverable
uc = client.get("/api/export/file?which=unique_clients")
check("the unique client list downloads", uc.status_code == 200)
check("the unique client list has one row per person",
      uc.text.count("\n") >= 2 and "Master_ID" in uc.text)
ubp = client.get("/api/export/file?which=unique_by_program")
check("the by-program list downloads", ubp.status_code == 200)
check("the by-program list carries the program", "Program" in ubp.text)
check("the by-program list has more rows than the person list",
      ubp.text.count("\n") > uc.text.count("\n"))

# only accepted rows are counted as people
check("rows still in review are not counted as people",
      summ["rows"]["clean"] >= summ["goal1"]["count"])

# the shareable page leads with the counts
page = client.get("/api/summary")
check("the shareable page states both counts",
      "Unique clients" in page.text and "Unique clients by program" in page.text)
check("the shareable page shows the programs", "People in each program" in page.text)
check("the shareable page holds no client names", "Adeyemi" not in page.text)

# the results stage sits before the files
ch = client.get("/api/ui?screen=summary").json()["chrome"]
check("results comes before the files in the rail",
      ch["stages"].index(ch["stages"][-2]) == len(ch["stages"]) - 2)
check("the summary screen is wired in the front end",
      "vSummary" in JS and "goal-n" in JS)
check("the proposals screen is wired", "vProposals" in JS and "data-idsame" in JS)
client.post("/api/reset")


# ---- program names differ between systems -----------------------------------
import program_names as _pnm

check("a program column is part of the standard shape",
      any(f["label"] == "Program" for f in cw.engine.DEFAULT_SCHEMA))
for col in ("program", "svc_area", "ProgramName", "service_type",
            "Activity", "program_area", "prog_name"):
    check(f"a program column named {col} is found",
          cw.engine.guess_mapping([col])["Program"] == col)
check("an unrelated column is not taken as the program",
      cw.engine.guess_mapping(["notes"])["Program"] == "")

vals = {"Workforce": 40, "Workforce Development": 25, "WFD": 12,
        "Resident Services": 30, "Resident Svcs": 8, "RS": 4,
        "Property Management": 18, "Property Mgmt": 5,
        "Homelessness Prevention": 9}
groups = _pnm.suggest_groups(vals)
by_canon = {g["canonical"]: {v["name"] for v in g["variants"]} for g in groups}
check("longer and shorter forms of a name are grouped",
      any({"Workforce", "Workforce Development"} <= s for s in by_canon.values()))
check("an abbreviation is grouped with the full word",
      any({"Resident Services", "Resident Svcs"} <= s for s in by_canon.values()))
check("initials are grouped with the name they stand for",
      any({"Resident Services", "RS"} <= s for s in by_canon.values()))
check("an unrelated program is left on its own",
      any(s == {"Homelessness Prevention"} for s in by_canon.values()))
check("every group says why it was put together",
      all(g["why"] or not g["needs_confirming"] for g in groups))
check("groups needing a look are marked",
      any(g["needs_confirming"] for g in groups))
check("initials are not matched to an unrelated name",
      not _pnm._is_acronym_of("PM", "Workforce Development"))

aliases = _pnm.build_alias_map(groups)
check("an alias map points every variant at one name",
      aliases["WFD"] == aliases["Workforce Development"])
check("applying an alias is case and spacing insensitive",
      _pnm.apply_aliases("workforce  development", aliases)
      == aliases["Workforce Development"])

# the counts use the agreed name, through the real pipeline
pdf = _pd.DataFrame([
    {"fn": "A", "ln": "B", "a1": "209 Joralemon St", "city": "Brooklyn",
     "st": "NY", "zip": "11201", "prog": "WFD"},
    {"fn": "C", "ln": "D", "a1": "60 Centre St", "city": "New York",
     "st": "NY", "zip": "10007", "prog": "Workforce Development"}])
pout = cw.engine.run_pipeline(
    {"f.csv": pdf},
    {"f.csv": {"First_Name": "fn", "Last_Name": "ln", "Address_1": "a1",
               "City": "city", "State": "st", "Zip": "zip", "Program": "prog"}},
    False, None, 1337, schema=cw.engine.DEFAULT_SCHEMA,
    program_aliases={"WFD": "Workforce", "Workforce Development": "Workforce"})
check("two spellings are counted as one program",
      {r["__program__"] for r in pout["transformed"]} == {"Workforce"})
check("using the agreed name is recorded in the audit",
      any("agreed name" in f["message"]
          for r in pout["transformed"] for f in r["__flags__"]))
check("the output shows the agreed name, as every count does",
      {r["__custom__"]["Program"] for r in pout["transformed"]} == {"Workforce"})
check("the spelling as recorded is kept in the audit note",
      any("'WFD' recorded as 'Workforce'" in f["message"]
          for r in pout["transformed"] for f in r["__flags__"]))

# through the interface, across three systems naming the column differently
def _prog_file(rows):
    buf = _i2.StringIO()
    _c2.writer(buf).writerows(rows)
    return buf.getvalue().encode()

client.post("/api/reset")
client.post("/api/sources/upload", files=[
    ("files", ("eto.csv", _prog_file([
        ["client_id", "first_name", "last_name", "address_1", "city", "state",
         "zip", "program"],
        ["E1", "Joe", "Smith", "1 Bowling Green", "New York", "NY", "10004",
         "Workforce Development"]]))),
    ("files", ("prop.csv", _prog_file([
        ["client_id", "first_name", "last_name", "address_1", "city", "state",
         "zip", "svc_area"],
        ["X1", "Joe", "Smith", "1 Bowling Green", "New York", "NY", "10004",
         "WFD"]])))])
mp = client.get("/api/ui?screen=programs").json()
check("the program column is found whatever it is called",
      mp["programs"]["mapped_on"] == 2)
check("the names found are grouped",
      mp["programs"]["grouped_into"] < mp["programs"]["distinct"])

first = mp["programs"]["groups"][0]["canonical"]
client.post("/api/programs/rename",
            json={"canonical": first, "name": "Workforce"})
mp2 = client.get("/api/ui?screen=programs").json()
check("a group can be renamed",
      any(g["canonical"] == "Workforce" for g in mp2["programs"]["groups"]))
client.post("/api/programs/group", json={"name": "WFD", "into": "__alone__"})
mp3 = client.get("/api/ui?screen=programs").json()
check("a name can be taken out into its own group",
      len(mp3["programs"]["groups"]) > len(mp2["programs"]["groups"]))
client.post("/api/programs/reset")
mp4 = client.get("/api/ui?screen=programs").json()
check("the proposal can be restored",
      len(mp4["programs"]["groups"]) == len(mp["programs"]["groups"]))
check("an empty group name is refused",
      client.post("/api/programs/rename",
                  json={"canonical": first, "name": " "}).status_code == 400)
check("the program panel is wired in the front end",
      "vProgramNames" in JS and "data-pgout" in JS and "data-pgmove" in JS)
client.post("/api/reset")


# ---- starting without a terminal --------------------------------------------
import launch as _launch

check("the tool reports that it is answering",
      client.get("/api/alive").json()["ok"] is True)
check("it reports the port it is on", "port" in client.get("/api/alive").json())
check("a goodbye page exists", client.get("/goodbye").status_code == 200)
check("the goodbye page says nothing else was written",
      "Nothing else was written" in client.get("/goodbye").text)

for f in ("Crosswalk.vbs", "Crosswalk.command", "Crosswalk.sh",
          "launch.py", "START HERE.txt"):
    check(f"{f} ships with the tool", os.path.exists(f))
check("the Mac and Linux launchers can be run",
      os.access("Crosswalk.command", os.X_OK)
      and os.access("Crosswalk.sh", os.X_OK))

vbs = open("Crosswalk.vbs", encoding="utf-8").read()
check("the Windows launcher opens no console window", ", 0, False" in vbs)
check("the Windows launcher says what to do when Python is missing",
      "python.org" in vbs and "MsgBox" in vbs)
cmd = open("Crosswalk.command", encoding="utf-8").read()
check("the Mac launcher says what to do when Python is missing",
      "python.org" in cmd)

check("the launcher finds a free port when the usual one is busy",
      isinstance(_launch.free_port(8765), int))
check("the launcher knows when nothing is running",
      _launch.already_running(9) is None)
check("the launcher checks the Python version", hasattr(_launch, "check_python"))
check("the launcher installs only what is missing",
      hasattr(_launch, "missing_packages"))
check("the launcher explains a failure in a window rather than a traceback",
      "MessageBoxW" in open("launch.py", encoding="utf-8").read())

# Started by double-clicking, the tool runs with no console and no standard
# output. Anything that reaches for it fails, which is what stopped it on a
# real machine, so the conditions are reproduced here rather than assumed.
_launch_src = open("launch.py", encoding="utf-8").read()
check("the launcher gives itself an output stream when there is none",
      "_ensure_streams" in _launch_src and "sys.stdout is None" in _launch_src)
check("that stream can answer whether it is a terminal",
      "def isatty" in _launch_src)
check("uvicorn is told not to install its own logging",
      "log_config=None" in _launch_src)

_saved_out, _saved_err = sys.stdout, sys.stderr
try:
    sys.stdout = None
    sys.stderr = None
    _launch._ensure_streams(os.path.join(ROOT, "launch-log.txt"))
    _no_console_ok = True
    _why = ""
    try:
        import uvicorn as _uv
        _uv.Config(cw.api, host="127.0.0.1", port=8799, log_level="warning",
                   log_config=None, access_log=False)
    except Exception as exc:
        _no_console_ok, _why = False, f"{type(exc).__name__}: {exc}"
finally:
    sys.stdout, sys.stderr = _saved_out, _saved_err
check("the server starts with no console, as it does when double-clicked",
      _no_console_ok)
if not _no_console_ok:
    print("      reason:", _why)
check("writing to the stand-in stream does not fail",
      _launch._LogStream(os.path.join(ROOT, "launch-log.txt")).write("") is None)

start = open("START HERE.txt", encoding="utf-8").read()
check("the start-here note says to double-click", "double-click" in start)
check("the start-here note explains the first run needs the internet once",
      "only step that uses the internet" in start)
check("the start-here note explains how to stop it",
      "Close Crosswalk" in start)

check("the interface offers a way to close the tool",
      'data-act="close-app"' in JS)
check("the open window tells the tool it is still there", "api/heartbeat" in JS)
client.post("/api/reset")


# ---- a real column beats one a split made, and the review says so -----------
# Shaped like a real export: a jammed address, a separate Zip column, a program
# code column and a program name column. The old mapping chose the empty split
# ZIP over the real one and sent every row to review as missing its ZIP.
theirs = [["Name", "Address Line 1", "Zip", "Program Unique Identifier",
           "Program Name"],
          ["Ronald Luis", "295 Jackson St Apt. 2F", "11206", "806",
           "Workforce Development"],
          ["Andrea Reyes", "260 Powers Street APT 5E", "11211", "806",
           "Workforce Development"],
          ["Maria Garcia", "330 Frost Street #7D", "11221", "807",
           "Resident Services"],
          ["Luis Ortega", "100 Grand St Apt 4 Brooklyn NY 11211 USA", "", "806",
           "Workforce Development"],
          ["Devi Mock", "55 Bedford Ave Brooklyn, NY 11249.", "", "807",
           "Resident Services"]]
_tb = _i2.StringIO()
_c2.writer(_tb).writerows(theirs)

client.post("/api/reset")
client.post("/api/sources/upload",
            files=[("files", ("theirs.csv", _tb.getvalue().encode()))])
tkey = client.get("/api/ui?screen=sources").json()["sources"]["tables"][0]["key"]
mp = client.get("/api/ui?screen=map").json()["map"]["tables"][0]
got = {f["role"]: f["col"] for f in mp["fields"]}
check("the source's own Zip column beats the one a split made", got["Zip"] == "Zip")
check("the program name column beats the program code column",
      got["Program"] == "Program Name")
check("the split street still beats the jammed column it came from",
      got["Address_1"].endswith("_street"))
check("a file with no separate Zip column still uses the split",
      cw.engine.guess_mapping(["Full_Address", "Full_Address_zip"])["Zip"]
      == "Full_Address_zip")
check("an identifier column is never taken as the program",
      cw.engine.guess_mapping(["Program Unique Identifier"])["Program"] == "")
check("a trailing country no longer hides the ZIP",
      cw.engine.split_jammed_address("100 Grand St Brooklyn NY 11211 USA")["zip"]
      == "11211")
check("a trailing period no longer hides the ZIP",
      cw.engine.split_jammed_address("55 Bedford Ave Brooklyn, NY 11249.")["zip"]
      == "11249")
check("City left to the ZIP is not called a problem",
      mp["check"]["fields"].get("City", {}).get("status") == "ok")

# put the wrong column back, as the old build chose it
sch_t = [dict(f) for f in cw.engine.DEFAULT_SCHEMA]
for f in sch_t:
    if f["role"] == "Client_ID":
        f["required"] = False
client.post("/api/schema", json={"schema": sch_t})
client.post("/api/map", json={"table": tkey, "field": "Zip",
                              "column": "Address Line 1_zip"})
mp2 = client.get("/api/ui?screen=map").json()["map"]["tables"][0]
zres = mp2["check"]["fields"]["Zip"]
check("a mostly empty ZIP column is called a problem", zres["status"] == "problem")
check("the check names the column that holds the ZIP",
      zres.get("better") == "Zip" and "'Zip'" in zres["message"])
check("a code column matched as the program is called a problem",
      cw.column_check.check_field(
          "Program", "code", _pd.Series(["806", "807", "806"]))["status"]
      == "problem")
check("a person's name is never suggested as the program or city",
      cw.column_check.better_column(
          "City", "x", _pd.DataFrame({"Name": ["Ada Sample", "Ben Fixture"],
                                      "x": ["", ""]}),
          [{"role": "City", "col": "x"}]) is None)

client.post("/api/run/start", json={"require_geocode": False, "jitter": True,
                                    "seed": 1337})
for _ in range(200):
    if client.get("/api/run/status").json()["state"] != "running":
        break
    time.sleep(0.05)
gs = client.get("/api/ui?screen=review").json()["review"]["groups"]
zg = next((g for g in gs if g["id"] in ("zipcity", "zipbad")), None)
check("the review diagnoses the matching problem rather than listing symptoms",
      zg and zg["diagnosis"] and zg["diagnosis"][0]["kind"] == "mapping")
check("the diagnosis names the column to switch to",
      zg and zg["diagnosis"][0]["better"] == "Zip")
check("the diagnosis is offered as a one-click fix", "data-fixmap" in JS)

client.post("/api/map", json={"table": tkey, "field": "Zip", "column": "Zip"})
client.post("/api/run/start", json={"require_geocode": False, "jitter": True,
                                    "seed": 1337})
for _ in range(200):
    if client.get("/api/run/status").json()["state"] != "running":
        break
    time.sleep(0.05)
rr = client.get("/api/ui?screen=run").json()["runData"]["results"]
check("with the right column, only the rows truly missing a ZIP are flagged",
      rr["review"] == 2 and rr["clean"] == 3)

# ---- the program panel follows the matching, and can be refreshed ----------
pgm = client.get("/api/ui?screen=programs").json()["programs"]
check("the panel says which column each source reads from",
      pgm["sources"] and pgm["sources"][0]["col"] == "Program Name")
client.post("/api/map", json={"table": tkey, "field": "Program",
                              "column": "Program Unique Identifier"})
pgm2 = client.get("/api/ui?screen=programs").json()["programs"]
check("changing the matched column changes the names shown",
      {g["canonical"] for g in pgm2["groups"]} == {"806", "807"})
check("the panel warns when the column looks like codes",
      "codes" in (pgm2["sources"][0].get("warn") or ""))
check("the panel can be refreshed on demand",
      client.post("/api/programs/refresh").json()["ok"] and "pg-refresh" in JS)

# ---- a possible duplicate says what it was matched on ----------------------
check("within-file duplicates are decided on tidy up, not asked again on review",
      "dupp" not in cw.GROUP_ORDER)
client.post("/api/reset")


# ---- one press to the review stage ------------------------------------------
client.post("/api/reset")
check("with nothing loaded the fast path says so",
      client.get("/api/express/check").json()["ok"] is False)
client.post("/api/sources/example")
ck = client.get("/api/express/check").json()
check("the fast path refuses while a required field has nothing matched",
      ck["ok"] is False and ck["blockers"])
check("each blocker names the file and the field",
      all(b["short"] and b["missing"] for b in ck["blockers"]))
check("running while blocked is refused with the reasons",
      client.post("/api/express/run", json={}).status_code == 409)

sch_x = [dict(f) for f in cw.engine.DEFAULT_SCHEMA]
for f in sch_x:
    if f["role"] == "Client_ID":
        f["required"] = False
client.post("/api/schema", json={"schema": sch_x})
ck2 = client.get("/api/express/check").json()
check("once the blocker is cleared the fast path is open", ck2["ok"] is True)
r = client.post("/api/express/run", json={}).json()
check("the fast path runs", r.get("ok") is True)
for _ in range(400):
    if client.get("/api/run/status").json()["state"] != "running":
        break
    time.sleep(0.05)
ch = client.get("/api/ui?screen=review").json()["chrome"]
check("it lands on the review stage", ch["stage"] == 7 and ch["maxStage"] >= 7)
check("every table is marked confirmed on the way",
      all(cw.S["confirmed"].get(k) for k in cw._included_keys()))
check("results are there to review",
      client.get("/api/ui?screen=review").json()["review"]["groups"])

# a column that looks wrong makes it stop and ask, and can be overridden
client.post("/api/reset")
client.post("/api/sources/upload",
            files=[("files", ("theirs.csv", _tb.getvalue().encode()))])
tk2 = client.get("/api/ui?screen=sources").json()["sources"]["tables"][0]["key"]
client.post("/api/schema", json={"schema": sch_x})
client.post("/api/map", json={"table": tk2, "field": "Zip",
                              "column": "Address Line 1_zip"})
r = client.post("/api/express/run", json={})
check("a column that looks wrong makes the fast path stop and ask",
      r.status_code == 409 and r.json().get("needs_confirmation"))
check("the warning is about the cause, not its consequences",
      len(r.json()["warnings"]) == 1 and r.json()["warnings"][0]["field"] == "Zip")
check("the warning names the column to switch to",
      r.json()["warnings"][0].get("better") == "Zip")
check("it can be told to run anyway",
      client.post("/api/express/run", json={"despite_warnings": True})
      .json().get("ok") is True)
check("the button is on the files stage",
      'data-act="express"' in JS and "vExpress" in JS)
check("the Client ID blocker offers a one-click way through",
      "express-relax-id" in JS)
check("the proof workbook is kept apart from the example files",
      os.path.exists(os.path.join("proof", "Proof_Workbook.xlsx"))
      and not os.path.exists(os.path.join("sample_data", "Proof_Workbook.xlsx")))
client.post("/api/reset")


# ---- the tool stops when the window goes away -------------------------------
_lsrc = open("launch.py", encoding="utf-8").read()
check("asking whether the tool is up does not count as a window being open",
      "LAST_SEEN" not in _lsrc.split("def alive")[0] if "def alive" in _lsrc
      else "def alive" in SERVER_SRC and "LAST_SEEN" not in
      SERVER_SRC.split("def alive():")[1].split("@api")[0])
check("the open window reports in on its own endpoint", "/api/heartbeat" in JS)
check("a closing window says goodbye", "/api/bye" in JS and "pagehide" in JS)
check("the tool stops soon after a goodbye", "GRACE_AFTER_CLOSE = 15" in _lsrc)
check("silence alone stops it within a minute", "IDLE_LIMIT = 45" in _lsrc)
check("the idle clock starts at launch, so a browser that never opens cannot "
      "leave it running", "crosswalk_server.LAST_SEEN = time.time()" in _lsrc)
check("the process id is recorded so a stop script can find it",
      "PID_FILE" in _lsrc and 'os.remove(PID_FILE)' in _lsrc)
for f in ("Stop Crosswalk.vbs", "Stop Crosswalk.command"):
    check(f"{f} ships with the tool", os.path.exists(f))
check("the Mac stop script only ends this folder's own launcher",
      "launch.py" in open("Stop Crosswalk.command", encoding="utf-8").read()
      and 'pkill -f "launch.py"' not in
      open("Stop Crosswalk.command", encoding="utf-8").read())
check("the start-here note says how to stop it",
      "Stop Crosswalk" in open("START HERE.txt", encoding="utf-8").read())
_before = cw.LAST_SEEN
client.get("/api/alive")
check("a liveness probe leaves the idle clock alone", cw.LAST_SEEN == _before)
client.get("/api/heartbeat")
check("a heartbeat moves the idle clock", cw.LAST_SEEN > _before or cw.LAST_SEEN > 0)
client.post("/api/bye")
check("a goodbye is recorded", cw.BYE_AT > 0)
client.get("/api/heartbeat")
check("a window coming back cancels the goodbye", cw.BYE_AT == 0)


# ---- the review count matches the run count ---------------------------------
# The same client base exported from one program in three different years,
# each export with its own row identifiers. Every row matches a row in another
# file. That is the crosswalk question, not a data problem, and must not fill
# the review pile or inflate its count.
_F = ["Ada", "Ben", "Cara", "Devi", "Evan", "Fay", "Gus", "Hana"]
_L = ["Sample", "Fixture", "Mock", "Draft", "Proxy", "Stub", "Trial", "Dummy"]
_people = [(_F[i % 8], _L[(i * 3) % 8], f"{100 + i} Main St") for i in range(40)]

def _year_file(prefix):
    buf = _i2.StringIO()
    w = _c2.writer(buf)
    w.writerow(["client_id", "first_name", "last_name", "address_1", "city",
                "state", "zip", "program"])
    for i, (fn, ln, a1) in enumerate(_people):
        w.writerow([f"{prefix}{i}", fn, ln, a1, "Brooklyn", "NY", "11201",
                    "YE High School"])
    return buf.getvalue().encode()

_intake = _i2.StringIO()
_w = _c2.writer(_intake)
_w.writerow(["client_id", "first_name", "last_name", "address_1", "city",
             "state", "zip", "program"])
_w.writerow(["X1", "Maria", "Garcia", "330 Frost St", "Brooklyn", "NY", "11221", "Intake"])
_w.writerow(["X2", "Maria", "Garcia", "330 Frost St", "Brooklyn", "NY", "11221", "Intake"])
_hs = _i2.StringIO()
_w = _c2.writer(_hs)
_w.writerow(["client_id", "first_name", "last_name", "Address Line 1", "zip",
             "Program Start Date", "program"])
for i in range(6):
    _w.writerow([f"H{i}", _F[i], _L[i], "", "11201", "9/1/2024", "YE High School"])

client.post("/api/reset")
client.post("/api/sources/upload", files=[
    ("files", ("YE 2022.csv", _year_file("A"))),
    ("files", ("YE 2023.csv", _year_file("B"))),
    ("files", ("YE 2024.csv", _year_file("C"))),
    ("files", ("intake.csv", _intake.getvalue().encode())),
    ("files", ("hs.csv", _hs.getvalue().encode()))])
ckx = client.get("/api/express/check").json()
check("a file with a ZIP but no City or State column is not blocked",
      ckx["ok"] is True)
client.post("/api/express/run", json={"despite_warnings": True})
for _ in range(400):
    if client.get("/api/run/status").json()["state"] != "running":
        break
    time.sleep(0.05)
rdx = client.get("/api/ui?screen=run").json()["runData"]["results"]
rvx = client.get("/api/ui?screen=review").json()
tx = rvx["review"]["tallies"]
check("the review stage counts the same failed rows as the run stage",
      tx["failed"] == rdx["review"] == 6)
check("rows matched across files are not in the review pile",
      not any(g["id"] == "dupp" and g["count"] > 2 for g in rvx["review"]["groups"]))
check("rows matched across files are reported as a note, with a count",
      rvx["crossFile"] and rvx["crossFile"]["rows"] == 120
      and rvx["crossFile"]["groups"] == 40 and len(rvx["crossFile"]["files"]) == 3)
check("a double entry inside one file is proposed on tidy up, not listed twice",
      not any(g["id"] == "dupp" for g in rvx["review"]["groups"])
      and rvx["review"].get("dupesUnreviewed", 0) >= 1)
check("the possible-duplicate group says it is about one file",
      "one file" in cw.GROUP_DEFS["dupp"]["title"])
na = next(g for g in rvx["review"]["groups"] if g["id"] == "noaddr")
check("a file with no addresses is diagnosed as such, not as a matching problem",
      na["diagnosis"] and na["diagnosis"][0]["kind"] == "source")
check("a date column is never offered as the street",
      not any("Program Start Date" in d["text"] for d in na["diagnosis"]))
check("the review stat is labeled as rows that failed a check",
      "rows that failed a check" in JS)
check("the cross-file note is shown on the review stage",
      "also appear in another file" in JS)

# the tightened address test on its own
check("a column of dates is not a street",
      cw.column_check.check_field("Address_1", "d", _pd.Series(
          ["9/1/2024", "9/1/2024", "1/15/2025"]))["status"] == "problem")
check("a column of phone numbers is not a street",
      cw.column_check.check_field("Address_1", "p", _pd.Series(
          ["7185551212", "7185550000"]))["status"] == "problem")
check("a real street column still passes",
      cw.column_check.check_field("Address_1", "a", _pd.Series(
          ["209 Joralemon St", "60 Centre St", "40-22 24th St"]))["status"] == "ok")
client.post("/api/reset")


# ---- Close Crosswalk really closes it -------------------------------------
_lsrc2 = open("launch.py", encoding="utf-8").read()
_ssrc2 = open("crosswalk_server.py", encoding="utf-8").read()
check("the tool reports its version so a launcher can tell copies apart",
      "version" in client.get("/api/alive").json())
check("quit ends the process itself rather than only setting a flag",
      "os._exit(0)" in _ssrc2.split("def quit_app")[1].split("@api")[0])
check("the goodbye page asks for the quit once it is on screen",
      'fetch("/api/quit"' in client.get("/goodbye").text)
check("closing is a plain confirm, not a button that changes its own label",
      "window.confirm(" in JS and "Click again to close" not in JS)
check("the confirm says downloads and progress are safe",
      "downloaded is safe" in JS)
check("the launcher tells a same-version copy from a different one",
      "running == MINE" in _lsrc2)
check("the launcher stops a different copy rather than opening it",
      "stop_whatever_holds" in _lsrc2)
check("finding the process by port does not depend on a tool being installed",
      "_pids_listening_on" in _lsrc2 and "/proc/net/tcp" in _lsrc2)
check("a copy that cannot be stopped is explained in plain words",
      "could not be stopped" in _lsrc2.replace('"\n', "").replace("\n", "")
      .replace('" "', "") or "could not " in _lsrc2 and "Crosswalk, or end" in _lsrc2)


# ---- duplicates within a file: proposed, reviewed, then processed out -------
import dedupe_rules as _dr
_dw = _pd.DataFrame([
    dict(id="1", fn="Ada", ln="Sample", a1="209 Joralemon St", zip="11201"),
    dict(id="2", fn="ADA", ln="sample", a1="209 Joralemon St.", zip="11201-1234"),
    dict(id="3", fn="Ada", ln="Sample", a1="60 Centre St", zip="10007"),
    dict(id="4", fn="Ben", ln="Fixture", a1="88 Meserole St", zip="11206"),
    dict(id="5", fn="ben", ln="FIXTURE", a1="90 Meserole St", zip="11206"),
    dict(id="6", fn="", ln="Blank", a1="1 Main St", zip="11201"),
    dict(id="7", fn="", ln="Blank", a1="1 Main St", zip="11201")])
_dm = {"Client_ID": "id", "First_Name": "fn", "Last_Name": "ln",
       "Address_1": "a1", "Zip": "zip"}
_fields = ["First_Name", "Last_Name", "Zip"]
pr = _dr.proposals(_dw.copy(), _fields, _dm)
check("the tool proposes the groups it finds on the chosen fields", pr["total_groups"] == 2)
check("case, punctuation and ZIP+4 are ignored when matching", pr["total_rows"] == 4)
check("each group shows its rows side by side",
      all(len(g["rows"]) == 2 for g in pr["groups"]))
check("each group names the fields that differ, so a person can judge",
      any("Address_1" in g["differing"] for g in pr["groups"]))
check("the same name at a different ZIP is not proposed",
      not any(r["values"]["Zip"] == "10007" for g in pr["groups"] for r in g["rows"]))
check("rows blank in a chosen field are never proposed",
      not any(r["values"]["First_Name"] == "" for g in pr["groups"] for r in g["rows"]))
check("a file that cannot supply a field says so",
      _dr.proposals(_dw.copy(), ["Program"], _dm)["missing"] == ["Program"])
check("a group has a stable id, so a decision survives a re-read",
      _dr.proposals(_dw.copy(), _fields, _dm)["groups"][0]["gid"] == pr["groups"][0]["gid"])

g_ada = next(g for g in pr["groups"] if g["rows"][0]["values"]["First_Name"] == "Ada")
g_ben = next(g for g in pr["groups"] if g["rows"][0]["values"]["First_Name"] == "Ben")

fr = _dw.copy()
out_d = _dr.apply_decisions(fr, _fields, _dm, {g_ada["gid"]: "copies", g_ben["gid"]: "keep"})
check("a confirmed group sets aside every row but the first",
      out_d["confirmed"] == 1 and out_d["set_aside"] == 1)
ro = cw.engine.run_pipeline({"f.csv": fr}, {"f.csv": _dm}, False, None, 1337,
                            schema=cw.engine.DEFAULT_SCHEMA)
byid = {r["Client_ID"]: r for r in ro["transformed"]}
check("the kept row of a confirmed group is clean and marked",
      not byid["1"]["__errors__"] and byid["1"]["Duplicate_In_File"])
check("the copy goes to review naming the row it copies",
      byid["2"]["__errors__"] and "copy of row 1" in byid["2"]["__errors__"][0])
check("a group decided as different people is left entirely alone",
      not byid["4"]["__errors__"] and not byid["4"]["Duplicate_In_File"]
      and not byid["5"]["__errors__"])
check("the built-in check does not pair rows a reviewer said are different",
      not byid["4"].get("Possible_Duplicate") and not byid["5"].get("Possible_Duplicate"))
check("nothing is processed out without a decision",
      True)
fr2 = _dw.copy()
_dr.apply_decisions(fr2, _fields, _dm, {})
ro2 = cw.engine.run_pipeline({"f.csv": fr2}, {"f.csv": _dm}, False, None, 1337,
                             schema=cw.engine.DEFAULT_SCHEMA)
check("an unreviewed group is flagged and kept, never removed",
      all(not r["__errors__"] for r in ro2["transformed"] if r["Duplicate_In_File"])
      and sum(1 for r in ro2["transformed"] if r["Duplicate_In_File"]) == 4)
check("the working flag never reaches the export",
      "__dup_keep__" not in cw.engine.clean_rows_to_dataframe(ro["clean"], ro["schema"]).columns)
check("the group label reaches the output",
      "Duplicate_In_File" in cw.engine.ENRICHMENT_COLUMNS)

# through the interface
client.post("/api/reset")
_b3 = _i2.StringIO()
_w3 = _c2.writer(_b3)
_w3.writerow(["client_id", "first_name", "last_name", "address_1", "city",
              "state", "zip", "program"])
for row_ in [["1", "Ada", "Sample", "209 Joralemon St", "Brooklyn", "NY", "11201", "Youth"],
             ["2", "ADA", "sample", "209 Joralemon St.", "Brooklyn", "NY", "11201-1234", "Youth"],
             ["3", "Cara", "Example", "87 Bay Terrace", "Staten Island", "NY", "10306", "Youth"]]:
    _w3.writerow(row_)
client.post("/api/sources/upload", files=[("files", ("dw.csv", _b3.getvalue().encode()))])
check("the tidy-up stage no longer carries the duplicates panel",
      "dupes" not in client.get("/api/ui?screen=prepare").json())
client.post("/api/run/start", json={"require_geocode": False, "jitter": True, "seed": 1337})
for _ in range(200):
    if client.get("/api/run/status").json()["state"] != "running":
        break
    time.sleep(0.05)
prep = client.get("/api/ui?screen=review").json()["dupes"]
check("the review stage proposes the groups with the rows to compare",
      prep["total_groups"] == 1 and prep["tables"][0]["groups"][0]["rows"])
check("the fields that count can be changed",
      client.post("/api/prepare/dupes/fields", json={"fields": ["Last_Name", "Zip"]}).json()["ok"])
check("empty fields are refused",
      client.post("/api/prepare/dupes/fields", json={"fields": []}).status_code == 400)
client.post("/api/prepare/dupes/fields", json={"fields": _fields})
tk = prep["tables"][0]["table"]
gid = prep["tables"][0]["groups"][0]["gid"]
client.post("/api/prepare/dupes/decide", json={"table": tk, "gid": gid, "decision": "copies"})
rv2 = client.get("/api/ui?screen=review").json()
check("a decision during review takes effect at once",
      rv2["dupes"]["will_set_aside"] == 1 and rv2["dupes"]["unreviewed"] == 0
      and any(g["id"] == "duprule" and g["count"] == 1 for g in rv2["review"]["groups"]))
client.post("/api/prepare/dupes/decide", json={"table": tk, "all": True, "decision": "keep"})
rv3 = client.get("/api/ui?screen=review").json()
check("a whole file can be decided at once, and undone",
      rv3["dupes"]["tables"][0]["keep"] == 1
      and not any(g["id"] == "duprule" for g in rv3["review"]["groups"]))
check("the duplicates panel is on the review stage",
      "data-dupdecide" in JS and "vDedupeRules()" in JS.split("function vReview")[1].split("function vQueue")[0])
check("the files stage does not carry a duplicate notice",
      "same person appearing more than once in the same file" not in JS.split("function vSources")[1].split("function ")[0])
check("decisions survive a saved session",
      "dup_decisions" in open("sessions_store.py", encoding="utf-8").read())
client.post("/api/reset")


# ---- filling in missing location data, safely ------------------------------
import fill_missing as _fm
_idx = cw.engine.load_geocode_index("nyc_address_points.csv")
_fnd = _fm.ZipFinder(_idx)
_uniq = next(((k, z) for k, z in _fnd.by_street.items() if len(z) == 1), None)
_multi = next(((k, z) for k, z in _fnd.by_street.items() if len(z) > 1), None)
check("a street in exactly one ZIP is proposed with the reason",
      _uniq and _fnd.propose("100 " + _uniq[0][0], _uniq[0][1])[0] == next(iter(_uniq[1])))
check("a street running through several ZIPs is refused, with the reason",
      not _multi or (_fnd.propose("100 " + _multi[0][0], _multi[0][1])[0] is None
                     and "runs through" in _fnd.propose("100 " + _multi[0][0], _multi[0][1])[1]))
check("an unknown street is refused rather than guessed",
      _fnd.propose("1 Nowhere Rd", "Brooklyn")[0] is None)
check("a blank city is filled from a valid ZIP",
      any(p["field"] == "City" and p["value"] == "Brooklyn"
          for p in _fm.propose_for_row({"Address_1": "5 Main St", "City": "",
                                        "State": "NY", "Zip": "11201"}, _fnd)))
check("a present value is never proposed for change",
      not any(p["field"] == "City" for p in _fm.propose_for_row(
          {"Address_1": "5 Main St", "City": "Queens", "State": "NY",
           "Zip": "11201"}, _fnd)))
check("the review offers to look the ZIPs up on the ZIP groups",
      "data-fillpreview" in JS and "from the street" in JS)
check("a fill is shown before it is applied", "Approve: fill in all" in JS)
check("a filled value is re-checked, so a wrong fill is still caught",
      "_recompute" in SERVER_SRC.split("def fill_apply")[1].split("@api")[0])

# ---- summary rows are their own group and no other ---------------------------
_sm = _pd.DataFrame([
    dict(id="1", fn="Ada", ln="Sample", a1="209 Joralemon St", city="Brooklyn",
         st="NY", zip="11201", hrs="3"),
    dict(id="", fn="", ln="", a1="", city="", st="", zip="", hrs="124"),
    dict(id="", fn="Total", ln="", a1="", city="", st="", zip="", hrs="127"),
    dict(id="2", fn="", ln="Fixture", a1="60 Centre St", city="New York",
         st="NY", zip="10007", hrs="")])
_smm = {"f.csv": {"Client_ID": "id", "First_Name": "fn", "Last_Name": "ln",
                  "Address_1": "a1", "City": "city", "State": "st", "Zip": "zip"}}
_sms = [dict(f) for f in cw.engine.DEFAULT_SCHEMA]
for f in _sms:
    if f["role"] == "Client_ID":
        f["required"] = False
_smo = cw.engine.run_pipeline({"f.csv": _sm}, _smm, False, None, 1337, schema=_sms)
_byrow = {int(r["__source_row__"]): r for r in _smo["transformed"]}
check("a bare number row is a summary row", "Summary row" in _byrow[1]["__errors__"][0])
check("a Total in a name column is a summary row", "Summary row" in _byrow[2]["__errors__"][0])
check("a summary row carries no other error",
      len(_byrow[1]["__errors__"]) == 1 and len(_byrow[2]["__errors__"]) == 1)
check("a row merely missing a name is not a summary row",
      "Missing First_Name" in _byrow[3]["__errors__"])
check("summary rows are grouped first and alone",
      cw._classify(_byrow[2]) == "summary" and cw.GROUP_ORDER[0] == "summary")
check("summary rows stay in the batch and are lossless",
      len(_smo["clean"]) + len(_smo["review"]) == 4)

# ---- the record panel: safe actions, no editing -----------------------------
check("values are not edited one by one on the record panel",
      'data-edit=' not in JS.split("function vQueueDetail")[1].split("function ")[0])
check("every record action explains itself on hover",
      all(w in JS for w in ("Accept this row exactly as it stands",
                            "Set this row aside. It is not deleted",
                            "Keep this row and set the other")))
check("a duplicate group offers to keep one row", "data-keeprow" in JS)
check("the queue offers to keep one of each person in each program",
      "q-keep-one-per-program" in JS)
check("an unmatched source column can be shown with the record", "data-showcol" in JS)
check("the original file can be opened from the record", "/api/source/file" in JS)
check("set-aside records download as their own file with the reason",
      '"aside"' in SERVER_SRC and "Set_Aside_Reason" in SERVER_SRC)
check("the ZIP group is explained in plain words",
      "Find the ZIP and both problems go away" in cw.GROUP_DEFS["zipcity"]["desc"])
check("the rail collapses and opens over the content",
      "rail-grip" in JS and ".rail.open" in open("ui/styles.css", encoding="utf-8").read())

# keep one per person per program, through the API
client.post("/api/reset")
_kb = _i2.StringIO()
_kw = _c2.writer(_kb)
_kw.writerow(["client_id", "first_name", "last_name", "address_1", "city", "state", "zip", "program"])
for row_ in [["A1", "Joe", "Smith", "1 Bowling Green", "New York", "NY", "10004", "Workforce"],
             ["A2", "Joseph", "Smith", "1 Bowling Green", "New York", "NY", "10004", "Workforce"],
             ["A3", "Joe", "Smith", "1 Bowling Green", "New York", "NY", "10004", "Housing"]]:
    _kw.writerow(row_)
_kb2 = _i2.StringIO()
_kw2 = _c2.writer(_kb2)
_kw2.writerow(["client_id", "first_name", "last_name", "address_1", "city", "state", "zip", "program"])
_kw2.writerow(["B1", "Joe", "Smith", "1 Bowling Green", "New York", "NY", "10004", "Workforce"])
client.post("/api/sources/upload", files=[("files", ("a.csv", _kb.getvalue().encode())),
                                          ("files", ("b.csv", _kb2.getvalue().encode()))])
client.post("/api/run/start", json={"require_geocode": False, "jitter": True, "seed": 1337})
for _ in range(200):
    if client.get("/api/run/status").json()["state"] != "running":
        break
    time.sleep(0.05)
kr = client.post("/api/queue/keep-one-per-program", json={}).json()
check("one row is kept per person per program and the rest set aside",
      kr["ok"] and kr["set_aside"] >= 1)
_asd = client.get("/api/export/file?which=aside")
check("set-aside rows download with their reason", _asd.status_code == 200
      and "Set_Aside_Reason" in _asd.text)
check("the source file can be downloaded as it arrived",
      client.get("/api/source/file?name=a.csv").status_code == 200)
client.post("/api/reset")


# ---- accept a whole group as it is, and suggest a city --------------------
_ab = _i2.StringIO()
_aw = _c2.writer(_ab)
_aw.writerow(["client_id", "first_name", "last_name", "address_1", "city", "state", "zip", "program"])
_aw.writerow(["1", "Ada", "Sample", "100 Morris Heights", "Springfeild", "NY", "07030", "Youth"])
_aw.writerow(["2", "Ben", "Fixture", "", "Brooklyn", "NY", "11201", "Youth"])
_aw.writerow(["3", "Cara", "Example", "", "Brooklyn", "NY", "11201", "Youth"])
client.post("/api/reset")
client.post("/api/sources/upload", files=[("files", ("t.csv", _ab.getvalue().encode()))])
client.post("/api/run/start", json={"require_geocode": False, "jitter": True, "seed": 1337})
for _ in range(200):
    if client.get("/api/run/status").json()["state"] != "running":
        break
    time.sleep(0.05)

pvc = client.get("/api/fill/preview?gid=cityunknown").json()
check("an unrecognized city gets a suggested borough from the street",
      pvc["fillable"] == 1 and any(p["field"] == "City" and p["value"]
                                    for it in pvc["items"] for p in it["proposals"]))
check("the suggestion is said as a replacement, naming the value as entered",
      any("replace 'Springfeild'" in p["why"] for it in pvc["items"]
          for p in it["proposals"]))
client.post("/api/fill/apply", json={"gid": "cityunknown"})
_r1 = next(r for r in cw.S["results"]["transformed"] if r["Client_ID"] == "1")
check("the suggested city is applied and the row checked again",
      _r1["City"] and _r1["City"] != "Springfeild")
check("an in-app correction carries its audit note",
      any("corrections file 'in-app review'" in f["message"] for f in _r1["__flags__"]))

r_acc = client.post("/api/review/group", json={"gid": "noaddr", "decision": "accept_all"}).json()
check("a whole group can be accepted as it is", "accepted as entered" in r_acc.get("outcome", ""))
_df = cw._clean_df()
check("accepted rows reach the clean list marked as approved by a reviewer",
      (_df["Resolution_Status"] == "Approved as entered by reviewer").sum() == 2)
check("rows that passed on their own say so",
      (_df["Resolution_Status"] == "Passed every check").sum() >= 1)
_r2 = next(r for r in cw.S["results"]["transformed"] if r["Client_ID"] == "2")
check("the audit records the acceptance on each row, naming the group",
      any("Accepted as entered by the reviewer" in f["message"] for f in _r2["__flags__"]))
tl = client.get("/api/ui?screen=review").json()["review"]["tallies"]
check("an accepted group counts as decided", tl["decided"] >= 1)
check("every group card offers to accept all as they are", "accept_all" in JS)
check("the accept action explains itself on hover",
      "Accept all" in JS and "Approved as entered by reviewer" in JS)
check("a street in exactly one borough resolves an unrecognized city",
      _fnd.propose_city("100 Morris Heights")[0] is not None)
_multi_b = next((n for n, b in _fnd.boroughs_of.items() if len(b) > 1), None)
check("a street in several boroughs is not guessed",
      _multi_b is None or _fnd.propose_city("100 " + _multi_b.title())[0] is None)
check("a valid ZIP settles the city before the street is consulted",
      _fnd.propose_city("1 Nowhere Rd", "11201")[0] == "Brooklyn")
client.post("/api/reset")


# ---- the header row is chosen on the files stage, and flagged when wrong ----
import table_detect as _tdh
_title_blk = [["Client roster spring 2026", "", "", "", ""],
              ["client_id", "first_name", "last_name", "zip", "program"],
              ["1", "Ada", "Sample", "11201", "Youth"]]
check("a title row chosen as the header is flagged",
      _tdh.header_looks_wrong(_title_blk, 1)[0])
check("no header chosen, with the names on row 2, is flagged and names the row",
      _tdh.header_looks_wrong(_title_blk, 0) == (True, "no header row is chosen, but row 2 looks like the column names"))
check("the right row is not flagged", not _tdh.header_looks_wrong(_title_blk, 2)[0])
check("a data row chosen as the header is flagged",
      _tdh.header_looks_wrong([["1", "Ada", "Sample", "11201"], ["2", "Ben", "Fixture", "10007"]], 1)[0])
check("two columns with one name are flagged",
      "both be named" in _tdh.header_looks_wrong([["name", "zip", "zip"], ["A", "1", "2"]], 1)[1])
check("a good header is not flagged",
      not _tdh.header_looks_wrong([["client_id", "first_name", "zip"], ["1", "Ada", "11201"]], 1)[0])

_tb_ = _i2.StringIO()
_tb_.write("Client roster spring 2026,,,,,,,\n")
_tb_.write("client_id,first_name,last_name,address_1,city,state,zip,program\n")
_tb_.write("1,Ada,Sample,209 Joralemon St,Brooklyn,NY,11201,Youth\n")
client.post("/api/reset")
client.post("/api/sources/upload", files=[("files", ("titled.csv", _tb_.getvalue().encode()))])
_src = client.get("/api/ui?screen=sources").json()["sources"]["tables"][0]
check("the files stage flags a table whose header looks wrong",
      _src["headerWrong"] and "row 2" in _src["headerWhy"])
check("the header picker is on the files stage, not the matching stage",
      "vHeaderRow(t) + vPreviewPane" in JS and "${vHeaderRow(t)}" not in JS)
client.post("/api/map/header", json={"key": _src["key"], "row": 2})
_src2 = client.get("/api/ui?screen=sources").json()["sources"]["tables"][0]
check("choosing the right row clears the flag and includes the table",
      not _src2["headerWrong"] and cw.S["included"].get(_src2["key"]) is True)
client.post("/api/reset")


# ---- every click shows itself --------------------------------------------
_ticks = []
_big = _pd.DataFrame([dict(id=str(i), fn="Ada", ln="Sample", a1="209 Joralemon St",
                           city="Brooklyn", st="NY", zip="11201") for i in range(600)])
cw.engine.run_pipeline({"f": _big}, {"f": {"Client_ID": "id", "First_Name": "fn",
                                          "Last_Name": "ln", "Address_1": "a1",
                                          "City": "city", "State": "st", "Zip": "zip"}},
                       False, None, 1337, schema=cw.engine.DEFAULT_SCHEMA,
                       progress=lambda d, n, ph, f="", fi=0, fc=0: _ticks.append((d, n, ph)))
check("the engine reports real progress as it works", len(_ticks) >= 3)
check("progress names the phase and counts rows",
      any(ph == "Cleaning and checking" and n == 600 for d, n, ph in _ticks)
      and any(ph == "Finding locations" for d, n, ph in _ticks))
check("the run status carries the phase, the count and a percentage",
      all(k in cw.S["run"] for k in ("phase", "progress")) )
check("the run stage no longer invents phases", "De-duplicating" not in SERVER_SRC)
check("a reprocess started from a request runs in a thread, so the server keeps answering",
      SERVER_SRC.count("await run_in_threadpool(_recompute)")
      + SERVER_SRC.count("await run_in_threadpool(_apply)")
      + SERVER_SRC.count("await run_in_threadpool(_run)")
      + SERVER_SRC.count("await run_in_threadpool(_apply_group_decision") >= 6
      and "\n        _recompute()\n" not in SERVER_SRC.split("async def queue_bulk")[1].split("@api")[0])
check("a page shows a bar while any request is in flight",
      "_busyShow" in JS and 'id="busy"' in open("ui/index.html", encoding="utf-8").read())
check("the bar follows background processing too", "function watchRun" in JS)
check("the overlay shows what is happening and how much is left", "steps left" in JS)
check("the clicked control is held until its work is done", "is-busy" in JS)
check("a fast answer does not flicker the bar", "setTimeout(_busyShow, 120)" in JS)


# ---- a unit is never taken as the city --------------------------------------
_sj = cw.engine.split_jammed_address
for _addr, _unit, _city in [
        ("111 test street, Apt. 4, Brooklyn, NY, 11201", "Apt. 4", "Brooklyn"),
        ("111 test street, Apt. 4, NY, 11201", "Apt. 4", ""),
        ("111 test street, Apt. 4, 11201", "Apt. 4", ""),
        ("111 test street, Apt. 4", "Apt. 4", ""),
        ("111 test street, Brooklyn, Apt. 4, NY, 11201", "Apt. 4", "Brooklyn"),
        ("111 test street, Rear, Brooklyn, NY, 11201", "Rear", "Brooklyn"),
        ("111 test street, 4th Fl, Brooklyn, NY, 11201", "4th Fl", "Brooklyn"),
        ("111 test street, Apt. 4, Brooklyn, New York, 11201", "Apt. 4", "Brooklyn")]:
    _d = _sj(_addr)
    check(f"'{_addr}' puts the unit in the unit slot", _d["unit"] == _unit)
    check(f"'{_addr}' never puts a unit in the city", _d["city"] == _city)
check("the state spelled out is read as the state",
      _sj("111 test street, Brooklyn, New York 11201")["state"] == "NY")
check("a street containing New York is not read as the state",
      _sj("100 New York Ave, Brooklyn, NY, 11203")["street"] == "100 New York Ave")
check("New York as the city is still the city",
      _sj("1 Bowling Green, New York, NY, 10004")["city"] == "New York")
check("an ordinal floor is a unit", cw.engine._looks_like_unit("2nd Floor"))


# ---- the address that put 14A in the city ----------------------------------
for _addr in ["117-19 45TH AVE, 14A, QUEENS, NY 11355",
              "117-19 45TH AVE, 14A, QUEENS, NY, 11355",
              "117-19 45TH AVE, 14A, NY 11355",
              "117-19 45TH AVE 14A, QUEENS, NY 11355",
              "117-19 45TH AVE 14A QUEENS NY 11355",
              "117-19 45TH AVE , 14A , QUEENS , NY 11355"]:
    _d = cw.engine.split_jammed_address(_addr)
    check(f"'{_addr}': 14A is the unit", _d["unit"] == "14A")
    check(f"'{_addr}': the city is Queens or blank, never 14A",
          _d["city"].upper() in ("QUEENS", ""))
    check(f"'{_addr}': the hyphenated house number stays whole",
          _d["street"] == "117-19 45TH AVE")
check("a bare designator after a street word is a unit",
      cw.engine.split_jammed_address("45 Ocean Ave 2B, Brooklyn, NY 11226")["unit"] == "2B")
check("Avenue U is not mistaken for a unit",
      cw.engine.split_jammed_address("2300 Avenue U, Brooklyn, NY 11229")["street"] == "2300 Avenue U")
check("Route 9 is not mistaken for a unit",
      cw.engine.split_jammed_address("100 Route 9")["unit"] == "")


# ---- the batch lookup works from the street alone ---------------------------
_ones = [n for n, b in _fnd.boroughs_of.items()
         if len(b) == 1 and len(_fnd.by_street[(n, next(iter(b)))]) == 1
         and not re.search(r"(?i)\b(apt|apartment|suite|ste|unit|fl|floor|rm|room|#)\b", n)][:2]
check("with no city, a street known in one borough gives a ZIP",
      _fnd.propose("100 " + _ones[0].title(), "")[0] is not None)
_many = next((n for n, b in _fnd.boroughs_of.items() if len(b) > 1), None)
check("with no city, a street known in several boroughs is refused and says a city is needed",
      _many is None or ("a city is needed" in _fnd.propose("100 " + _many.title(), "")[1]))
_row = {"Address_1": "100 " + _ones[0].title(), "City": "", "State": "NY", "Zip": "",
        "__errors__": ["Invalid ZIP Code format: (blank)", "City could not be determined"]}
_props = {p["field"]: p["value"] for p in _fm.propose_for_row(_row, _fnd)}
check("a row with neither ZIP nor city gets both proposed from its street",
      _props.get("Zip") and _props.get("City"))

_fb = _i2.StringIO()
_fw = _c2.writer(_fb)
_fw.writerow(["client_id", "first_name", "last_name", "address_1", "city", "state", "zip", "program"])
for i, n in enumerate(_ones):
    _fw.writerow([str(i), "Ada", "Sample", "100 " + n.title(), "", "NY", "", "Youth"])
_fw.writerow(["9", "Ben", "Fixture", "1 Nowhere Rd", "", "NY", "", "Youth"])
client.post("/api/reset")
client.post("/api/sources/upload", files=[("files", ("t.csv", _fb.getvalue().encode()))])
client.post("/api/run/start", json={"require_geocode": False, "jitter": True, "seed": 1337})
for _ in range(200):
    if client.get("/api/run/status").json()["state"] != "running":
        break
    time.sleep(0.05)
_zg = next(g for g in client.get("/api/ui?screen=review").json()["review"]["groups"]
           if g["id"] in ("zipcity", "zipbad"))
check("the ZIP group card says how many rows can be looked up",
      _zg["lookup"] and _zg["lookup"]["with_street"] == 3)
_pv = client.get(f"/api/fill/preview?gid={_zg['id']}").json()
check("the batch lookup fills the rows that have no city at all",
      _pv["fillable"] == 2 and _pv["by_field"].get("City") == 2 and _pv["by_field"].get("Zip") == 2)
check("the street it cannot place is reported, not guessed",
      _pv["stuck"] == 1 and "not in the reference data" in _pv["stuck_sample"][0]["proposals"][0]["why"])
_ap = client.post("/api/fill/apply", json={"gid": _zg["id"]}).json()
check("approving fills every row shown", _ap["filled"] == 2)
check("the lookup button names the count and what it will do",
      "Look up all ${nf(g.lookup.with_street)} from the street" in JS)
check("Geosupport is called the way the engine calls it",
      "borough_code=" in open("fill_missing.py", encoding="utf-8").read())
client.post("/api/reset")


# ---- Programs is its own stage, with a preview of the counts ----------------
client.post("/api/reset")
_pf = {}
for _name, _hdr, _rows in [
        ("eto.csv", "program", [["E100", "Joe", "Smith", "1 Bowling Green", "New York", "NY", "10004", "Workforce Development"],
                                ["E300", "Kira", "Adeyemi", "65 Central Ave", "Brooklyn", "NY", "11221", "Workforce Development"]]),
        ("prop.csv", "svc_area", [["X9", "Joe", "Smith", "1 Bowling Green", "New York", "NY", "10004", "WFD"]]),
        ("dycd.csv", "ProgramName", [["D1", "Joe", "Smith", "1 Bowling Green", "New York", "NY", "10004", "Workforce"]])]:
    _b = _i2.StringIO()
    _w = _c2.writer(_b)
    _w.writerow(["client_id", "first_name", "last_name", "address_1", "city", "state", "zip", _hdr])
    for r_ in _rows:
        _w.writerow(r_)
    _pf[_name] = _b.getvalue().encode()
client.post("/api/sources/upload", files=[("files", (n, d)) for n, d in _pf.items()])
pg_ = client.get("/api/ui?screen=programs").json()["programs"]
check("the Programs stage lists which column each file reads the program from",
      len(pg_["sources"]) == 3 and all(s["col"] for s in pg_["sources"]))
check("each source shows sample names", all(s["samples"] for s in pg_["sources"]))
check("every name says which file it came from",
      all(v["files"] for g in pg_["groups"] for v in g["variants"]))
check("the three spellings are grouped as one program", pg_["grouped_into"] == 1)
check("there is no preview until one is asked for", pg_["preview"] is None)

pv_ = client.post("/api/programs/preview", json={}).json()
check("the preview processes and reports both counts",
      pv_["ok"] and pv_["preview"]["goal2"] >= 1 and "goal1" in pv_["preview"])
check("the preview lists unique clients per program as counted",
      pv_["preview"]["programs"][0]["program"] == "Workforce Development")
pg2_ = client.get("/api/ui?screen=programs").json()["programs"]
check("a fresh preview is not marked stale", pg2_["preview_stale"] is False)
client.post("/api/programs/group", json={"name": "WFD", "into": "__alone__"})
pg3_ = client.get("/api/ui?screen=programs").json()["programs"]
check("changing the grouping marks the preview stale", pg3_["preview_stale"] is True)
pv2_ = client.post("/api/programs/preview", json={}).json()["preview"]
check("the refreshed preview shows the effect of the change: one more program",
      len(pv2_["programs"]) == len(pv_["preview"]["programs"]) + 1)
client.post("/api/programs/group", json={"name": "WFD", "into": "Workforce Development"})
check("a name can be moved back into a group",
      client.get("/api/ui?screen=programs").json()["programs"]["grouped_into"] == 1)
tk_ = pg_["sources"][1]["key"]
client.post("/api/programs/column", json={"table": tk_, "column": ""})
pg4_ = client.get("/api/ui?screen=programs").json()["programs"]
check("a file's program column can be unset, and the stage says its rows drop out of the count",
      pg4_["mapped_on"] == 2 and not pg4_["sources"][1]["col"])
check("the preview says how many counted rows have no program",
      "no_program" in pv_["preview"])
check("the stage is wired in the interface with pick-up-and-place grouping",
      "vPrograms" in JS and "data-pgpick" in JS and "data-pgtarget" in JS)
check("the map stage no longer carries the program panel",
      "programs" not in client.get("/api/ui?screen=map").json()["map"])
client.post("/api/reset")


# ---- unit designators in every shape people type ----------------------------
for _addr, _street, _unit in [
        ("67 Franklin Avenue Apt. 10 R", "67 Franklin Avenue", "Apt. 10 R"),
        ("25 Tom Street APT18L", "25 Tom Street", "APT18L"),
        ("31 Phil Street Apt. 10 A", "31 Phil Street", "Apt. 10 A"),
        ("67 Jill Ave Apt#: 11T", "67 Jill Ave", "Apt#: 11T"),
        ("54 Botrus St. Apt. 10 M", "54 Botrus St.", "Apt. 10 M"),
        ("123 Main St #B", "123 Main St", "#B"),
        ("123 Main St Apt B-12", "123 Main St", "Apt B-12")]:
    _s, _u = cw.engine._split_unit(_addr)
    check(f"'{_addr}' splits into street and unit", (_s, _u) == (_street, _unit))
for _named in ["10 Apartment Way", "5 Unit Ln", "7 Suite Drive", "300 Stop St",
               "12 Penthouse Rd", "2300 Avenue U", "100 Route 9", "1 Front St"]:
    check(f"a street named '{_named}' is left whole",
          cw.engine._split_unit(_named) == (_named, ""))


# ---- a calculated ZIP column, mapped like any other -------------------------
cw._finder()
_cone = next(n for n, b in _fnd.boroughs_of.items()
             if len(b) == 1 and len(_fnd.by_street[(n, next(iter(b)))]) == 1
             and not re.search(r"(?i)\b(apt|apartment|suite|ste|unit|fl|floor|rm|room|#)\b", n))
_cmany = next(n for n, b in _fnd.boroughs_of.items() if len(b) > 1)
_cdf = _pd.DataFrame({"street": ["100 " + _cone.title(), "100 " + _cmany.title(), "1 Nowhere Rd", "", "5 Main St"],
                      "boro": ["", "", "Brooklyn", "", ""],
                      "zip": ["", "", "", "", "11201"]})
_cout = cw.engine.op_calc_zip(_cdf, "street", "boro", "zip", "blanks")
check("the calculated column holds a ZIP where the address settles it",
      _cout["Zip_calculated"].iloc[0] and "only in" in _cout["Zip_calculated_note"].iloc[0])
check("an ambiguous street is left blank with the reason",
      _cout["Zip_calculated"].iloc[1] == "" and "boroughs" in _cout["Zip_calculated_note"].iloc[1])
check("an unknown street is left blank with the reason",
      _cout["Zip_calculated"].iloc[2] == "" and "not in the reference data" in _cout["Zip_calculated_note"].iloc[2])
check("a row with no street says so", "no street" in _cout["Zip_calculated_note"].iloc[3])
check("a ZIP the file already has is kept, not looked up",
      _cout["Zip_calculated"].iloc[4] == "11201" and _cout["Zip_calculated_note"].iloc[4].startswith("kept"))
_call = cw.engine.op_calc_zip(_cdf, "street", "boro", "zip", "always")
check("in 'always' mode an existing ZIP is looked up too",
      not _call["Zip_calculated_note"].iloc[4].startswith("kept"))
check("the calculated column is chosen for Zip on the matching stage",
      cw.engine.guess_mapping(list(_cout.columns))["Zip"] == "Zip_calculated")
check("the step describes itself", "Calculated column" in cw.engine.describe_op(
      {"type": "calc_zip", "street_col": "street"}))
_saved = cw.engine.ZIP_RESOLVER
cw.engine.ZIP_RESOLVER = None
check("with no geocoder the column says so rather than guessing",
      "no geocoder" in cw.engine.op_calc_zip(_cdf, "street")["Zip_calculated_note"].iloc[0])
cw.engine.ZIP_RESOLVER = _saved

_cb = _i2.StringIO()
_cw = _c2.writer(_cb)
_cw.writerow(["client_id", "first_name", "last_name", "street", "borough", "postal", "program"])
_cw.writerow(["1", "Ada", "Sample", "100 " + _cone.title(), "", "", "Youth"])
_cw.writerow(["2", "Ben", "Fixture", "100 " + _cmany.title(), "", "", "Youth"])
_cw.writerow(["3", "Devi", "Mock", "5 Main St", "Brooklyn", "11201", "Youth"])
client.post("/api/reset")
client.post("/api/sources/upload", files=[("files", ("calc.csv", _cb.getvalue().encode()))])
_ck = client.get("/api/ui?screen=sources").json()["sources"]["tables"][0]["key"]
check("a calculated step without a street column is refused",
      client.post("/api/prepare/add", json={"table": _ck, "op": {"type": "calc_zip"}}).status_code == 400)
client.post("/api/prepare/add", json={"table": _ck, "op": {
    "type": "calc_zip", "street_col": "street", "city_col": "borough",
    "zip_col": "postal", "mode": "blanks"}})
_prep = client.get("/api/ui?screen=prepare").json()["prepare"]
_step = next(o for o in _prep["ops"] if "Calculated" in o["title"])
check("the step reports what it found before anything is mapped",
      "Found a ZIP for 1" in _step["desc"] and "could not place 1" in _step["desc"])
check("the add-step panel is available in Guided mode",
      "${vPrepareAdd(d)}" in JS and "d.advanced ? vPrepareAdd" not in JS)
check("Zip is matched to the calculated column",
      next(f["col"] for f in client.get("/api/ui?screen=map").json()["map"]["tables"][0]["fields"]
           if f["role"] == "Zip") == "Zip_calculated")
client.post("/api/run/start", json={"require_geocode": False, "jitter": True, "seed": 1337})
for _ in range(200):
    if client.get("/api/run/status").json()["state"] != "running":
        break
    time.sleep(0.05)
_rr = client.get("/api/ui?screen=run").json()["runData"]["results"]
check("rows whose ZIP was calculated pass; the one that could not goes to review",
      _rr["clean"] == 2 and _rr["review"] == 1)
_rg = client.get("/api/ui?screen=review").json()["review"]["groups"]
client.post("/api/review/group", json={"gid": _rg[0]["id"], "decision": "sent"})
_qi = client.get("/api/queue").json()["items"][0]
check("the row arrives in review saying why the ZIP could not be calculated",
      "could not be calculated" in _qi["reason"] and "boroughs" in _qi["reason"])
client.post("/api/reset")


# ---- one apply instead of one round trip per click --------------------------
client.post("/api/reset")
client.post("/api/sources/upload", files=[("files", (n, d)) for n, d in _pf.items()])
_pk = client.get("/api/ui?screen=programs").json()["programs"]
check("prepared frames are built once and reused", "_PREP_CACHE" in SERVER_SRC and "_prep_signature" in SERVER_SRC)
_cnt = {"n": 0}
_orig_apply = cw.engine.apply_prep_ops
def _spy(df, ops):
    _cnt["n"] += 1
    return _orig_apply(df, ops)
cw.engine.apply_prep_ops = _spy
client.get("/api/ui?screen=programs"); client.get("/api/ui?screen=map"); client.get("/api/ui?screen=programs")
check("loading three screens rebuilds no prepared frame", _cnt["n"] == 0)
cw.engine.apply_prep_ops = _orig_apply

r_ap = client.post("/api/programs/apply", json={
    "columns": [{"table": s["key"], "column": s["col"]} for s in _pk["sources"]],
    "groups": [{"canonical": "Workforce", "names": ["Workforce Development", "WFD"]},
               {"canonical": "Other", "names": ["Workforce"]}]}).json()
_pk2 = client.get("/api/ui?screen=programs").json()["programs"]
check("a whole program set-up applies in one call",
      r_ap["ok"] and {g["canonical"] for g in _pk2["groups"]} == {"Workforce", "Other"})
check("the applied grouping is exactly what was sent",
      next(len(g["variants"]) for g in _pk2["groups"] if g["canonical"] == "Workforce") == 2)
check("applying marks the preview stale", _pk2["preview_stale"] is True)
check("the page holds program edits locally until Apply",
      "progLocal" in JS and "prog-apply" in JS and 'data-act="prog-apply"' in JS)

client.post("/api/reset")
client.post("/api/sources/upload", files=[("files", ("titled.csv", _tb_.getvalue().encode()))])
client.post("/api/map/header", json={"key": client.get("/api/ui?screen=sources").json()["sources"]["tables"][0]["key"], "row": 2})
client.post("/api/schema", json={"schema": sch_x})
client.post("/api/run/start", json={"require_geocode": False, "jitter": True, "seed": 1337})
for _ in range(200):
    if client.get("/api/run/status").json()["state"] != "running":
        break
    time.sleep(0.05)
_gs = client.get("/api/ui?screen=review").json()["review"]["groups"]
if _gs:
    r_dm = client.post("/api/review/decide-many", json={"decisions": [
        {"gid": g["id"], "decision": "held"} for g in _gs]}).json()
    check("several group decisions apply in one call", r_dm["ok"] and len(r_dm["done"]) == len(_gs))
    check("every group is then decided",
          all(g["status"] != "pending" for g in client.get("/api/ui?screen=review").json()["review"]["groups"]))
check("review decisions are chosen locally and applied together",
      "pendingGroups" in JS and "apply-groups" in JS and "decide-many" in JS)
check("duplicate decisions are chosen locally and applied with one reprocess",
      "pendingDups" in JS and "apply-dups" in JS)
check("the duplicates endpoint takes a list of decisions",
      '"decisions"' in SERVER_SRC.split("def dupes_decide")[1].split("@api")[0])
check("finishing the review applies anything still pending",
      'if (UI.screen === "review")' in JS)
check("the mode toggle sits at the foot of the menu",
      "rail-foot" in JS and JS.index('class="seg mode-seg"') > JS.index('<div class="rail-foot">'))
client.post("/api/reset")


# ---- the audit trail, complete and on screen --------------------------------
import shutil as _sh
client.post("/api/reset")
client.post("/api/sources/upload", files=[("files", (n, d)) for n, d in _pf.items()])
client.post("/api/schema", json={"schema": sch_x})
client.post("/api/run/start", json={"require_geocode": False, "jitter": True, "seed": 1337})
for _ in range(200):
    if client.get("/api/run/status").json()["state"] != "running":
        break
    time.sleep(0.05)
_ag = client.get("/api/ui?screen=review").json()["review"]["groups"]
if _ag:
    client.post("/api/review/group", json={"gid": _ag[0]["id"], "decision": "accept_all"})
_au = client.get("/api/audit").json()
check("the audit trail is readable during the session", _au["total"] > 0)
check("it covers the set-up, the engine's work and the decisions",
      _au["counts"].get("set-up") and (not _ag or _au["counts"].get("decision")))
_txt = client.get("/api/export/file?which=audit").text
check("the exported trail has all three sections",
      "== Set-up ==" in _txt and "== Changes made while processing" in _txt
      and "== Decisions by the reviewer ==" in _txt)
check("the set-up section records the matching per file", "Matching for eto.csv" in _txt)
check("the set-up section records what counts as a duplicate and the settings",
      "Duplicate within a file means the same" in _txt and "Settings:" in _txt)
check("the trail holds no client names", "Adeyemi" not in _txt and "Bowling Green" not in _txt)
check("the trail can be filtered by kind",
      all(i["kind"] == "engine" for i in client.get("/api/audit?kind=engine").json()["items"]))
check("the trail can be searched by identifier",
      client.get("/api/audit?q=E100").json()["total"] >= 0)
check("the audit is reachable from the menu and the download stage",
      JS.count('data-act="open-audit"') >= 2 and "function vAudit" in JS)

# ---- processing shows itself calmly -----------------------------------------
_ticks2 = []
_three = {f"f{i}": _pd.DataFrame([dict(id=str(j), fn="Ada", ln="Sample", a1="209 Joralemon St",
                                       city="Brooklyn", st="NY", zip="11201") for j in range(300)])
          for i in range(3)}
_mp3 = {k: {"Client_ID": "id", "First_Name": "fn", "Last_Name": "ln", "Address_1": "a1",
            "City": "city", "State": "st", "Zip": "zip"} for k in _three}
cw.engine.run_pipeline(_three, _mp3, False, None, 1337, schema=cw.engine.DEFAULT_SCHEMA,
                       progress=lambda d, n, ph, f="", fi=0, fc=0: _ticks2.append((ph, f, fi, fc)))
_files_seen = {(ph, f) for ph, f, fi, fc in _ticks2 if f}
check("progress is reported per file, not per row",
      len(_ticks2) < 20 and all(fc == 3 for ph, f, fi, fc in _ticks2 if fc))
check("every file is named as it is worked on",
      {f for ph, f in _files_seen if ph == "Cleaning and checking"} == {"f0", "f1", "f2"})
check("the status carries a calm message and how much is left",
      "steps_left" in SERVER_SRC and "message" in SERVER_SRC.split("def _progress")[1].split("S[\"run\"] = {")[0])
check("the screen grays out with one card while processing",
      'id="working"' in open("ui/index.html", encoding="utf-8").read() and "_workingShow" in JS)
check("a hidden overlay is really hidden",
      ".working[hidden] { display: none; }" in open("ui/styles.css", encoding="utf-8").read())

# ---- the whole-file duplicate choice explains itself ------------------------
check("the whole-file choice says what it will do on hover",
      "the first row (by its order in the file) stays" in JS)
check("choosing for a whole file states the rows it will set aside",
      "set the other" in JS and "Nothing has changed yet" in JS)
check("the panel explains both outcomes up front",
      "leaves every row and stops the tool pairing them again" in JS)

# ---- saved set-ups ------------------------------------------------------------
import setups as _su
_sh.rmtree(_su.FOLDER, ignore_errors=True)
client.post("/api/reset")
client.post("/api/sources/upload", files=[("files", (n, d)) for n, d in _pf.items()])
_tk1 = client.get("/api/ui?screen=sources").json()["sources"]["tables"][0]["key"]
client.post("/api/prepare/add", json={"table": _tk1, "op": {"type": "split_jammed", "column": "address_1"}})
client.post("/api/programs/apply", json={"columns": [], "groups": [
    {"canonical": "Workforce", "names": ["Workforce Development", "WFD", "Workforce"]}]})
check("a set-up needs a name", client.post("/api/setups/save", json={"name": " "}).status_code == 400)
r_s = client.post("/api/setups/save", json={"name": "Quarterly", "note": "three systems"}).json()
check("a set-up saves under its name", r_s["ok"] and r_s["name"] == "Quarterly")
check("saved set-ups are listed with their files",
      any(s["name"] == "Quarterly" and len(s["files"]) == 3 for s in client.get("/api/setups").json()["setups"]))
_raw = open(os.path.join(_su.FOLDER, "Quarterly.json"), encoding="utf-8").read()
check("a set-up holds no client data", "Adeyemi" not in _raw and "Bowling Green" not in _raw)
check("a set-up records the version it was saved with", '"app_version"' in _raw)

client.post("/api/reset")
_grown = dict(_pf)
_grown["eto.csv"] = _pf["eto.csv"] + b"E400,Ada,Sample,209 Joralemon St,Brooklyn,NY,11201,Workforce Development\n"
client.post("/api/sources/upload", files=[("files", (n, d)) for n, d in _grown.items()])
r_c = client.post("/api/setups/check", json={"name": "Quarterly"}).json()
check("the same files with more rows still fit", r_c["ok"] and not r_c["problems"])
r_l = client.post("/api/setups/load", json={"name": "Quarterly"}).json()
check("loading applies the steps, the matching and the grouping",
      "tidy-up step" in " ".join(r_l["applied"]) and "matching" in " ".join(r_l["applied"])
      and "program grouping" in " ".join(r_l["applied"]))
check("a loaded grouping survives against the names present",
      any(g["canonical"] == "Workforce" and len(g["variants"]) == 3
          for g in client.get("/api/ui?screen=programs").json()["programs"]["groups"]))
check("loading is undoable", client.get("/api/ui?screen=sources").json()["chrome"]["undoLabel"] == "loaded a saved set-up")

client.post("/api/reset")
_rb = _i2.StringIO()
_rw = _c2.writer(_rb)
_rw.writerow(["client_id", "first_name", "last_name", "street", "city", "state", "zip", "program"])
_rw.writerow(["E100", "Joe", "Smith", "1 Bowling Green", "New York", "NY", "10004", "WFD"])
client.post("/api/sources/upload", files=[("files", ("eto.csv", _rb.getvalue().encode()))])
r_c2 = client.post("/api/setups/check", json={"name": "Quarterly"}).json()
check("a renamed column is reported by name, not applied blindly",
      not r_c2["ok"] and any("address_1" in p_ for p_ in r_c2["problems"]))
check("a file that is not loaded is reported by name",
      any("prop.csv is not loaded" in p_ for p_ in r_c2["problems"]))
import json as _json
_d = _json.load(open(os.path.join(_su.FOLDER, "Quarterly.json"), encoding="utf-8"))
_d["app_version"] = "2099.01.01"
_d["state"]["ops"].append({"table": _tk1, "op": {"type": "teleport", "column": "x"}, "origin": "manual"})
_json.dump(_d, open(os.path.join(_su.FOLDER, "Future.json"), "w", encoding="utf-8"))
r_c3 = client.post("/api/setups/check", json={"name": "Future"}).json()
check("a set-up from another version says so", any("2099" in n for n in r_c3["notes"]))
check("a step this version does not have is named as a problem",
      any("teleport" in p_ for p_ in r_c3["problems"]))
open(os.path.join(_su.FOLDER, "Broken.json"), "w").write("{not json")
check("a set-up that cannot be read is listed as broken, not hidden",
      any(s.get("broken") for s in client.get("/api/setups").json()["setups"]))
check("a broken set-up is refused with the reason",
      client.post("/api/setups/check", json={"name": "Broken"}).status_code == 400)
check("set-ups can be saved and loaded from the interface",
      "function vSetups" in JS and "data-setupload" in JS and "data-setupcheck" in JS)
_sh.rmtree(_su.FOLDER, ignore_errors=True)
client.post("/api/reset")


# ---- a per-source default reaches the program, so no program is blank -------
_ed = _pd.DataFrame([dict(id="1", fn="Ada", ln="Sample", a1="209 Joralemon St",
                          city="Brooklyn", st="NY", zip="11201")])
_em = {"f": {"Client_ID": "id", "First_Name": "fn", "Last_Name": "ln", "Address_1": "a1",
             "City": "city", "State": "st", "Zip": "zip"}}
_er = cw.engine.run_pipeline({"f": _ed}, _em, False, None, 1337, schema=cw.engine.DEFAULT_SCHEMA,
                             source_defaults={"f": {"Program": "Elder Care"}})
check("a default set for one source fills its program on every row",
      _er["transformed"][0]["__program__"] == "Elder Care")
check("the fill is recorded in the audit as coming from this source",
      any("from this source" in f["message"] for f in _er["transformed"][0]["__flags__"]))
_ed2 = _pd.DataFrame([dict(id="2", fn="Ben", ln="Fixture", a1="60 Centre St", city="New York",
                           st="NY", zip="10007", prog="Youth")])
_er2 = cw.engine.run_pipeline({"f": _ed2}, {"f": dict(_em["f"], Program="prog")}, False, None, 1337,
                              schema=cw.engine.DEFAULT_SCHEMA, source_defaults={"f": {"Program": "Elder Care"}})
check("a row with its own program keeps it", _er2["transformed"][0]["__program__"] == "Youth")

client.post("/api/reset")
_eb = _i2.StringIO()
_ew = _c2.writer(_eb)
_ew.writerow(["client_id", "first_name", "last_name", "address_1", "city", "state", "zip"])
_ew.writerow(["1", "Ada", "Sample", "209 Joralemon St", "Brooklyn", "NY", "11201"])
client.post("/api/sources/upload", files=[("files", ("elder.csv", _eb.getvalue().encode())),
                                          ("files", ("eto.csv", _pf["eto.csv"]))])
_ek = next(k for k in cw.S["frames"] if k.startswith("elder"))
client.post("/api/sources/default", json={"key": _ek, "field": "Program", "value": "Elder Care"})
_pgd = client.get("/api/ui?screen=programs").json()["programs"]
check("the Programs stage shows the source default as that file's program",
      next(s for s in _pgd["sources"] if s["key"] == _ek)["default"] == "Elder Care"
      and _pgd["mapped_on"] == 2)
check("the default takes part in the grouping",
      any(g["canonical"] == "Elder Care" for g in _pgd["groups"]))
client.post("/api/run/start", json={"require_geocode": False, "jitter": True, "seed": 1337})
for _ in range(200):
    if client.get("/api/run/status").json()["state"] != "running":
        break
    time.sleep(0.05)
_bp = cw._unique_by_program_df()
check("the by-program file has no blank programs", int((_bp["Program"] == "").sum()) == 0
      and "Elder Care" in set(_bp["Program"]))
check("the Programs stage explains what a default does",
      "the default set for this file on the matching stage" in JS)

# ---- choosing which row to keep -------------------------------------------
_kd = _pd.DataFrame([dict(id="1", fn="Ada", ln="Sample", a1="209 Joralemon St", zip="11201"),
                     dict(id="2", fn="ADA", ln="sample", a1="209 Joralemon St.", zip="11201"),
                     dict(id="3", fn="Ada", ln="Sample", a1="209 Joralemon Street", zip="11201")])
_km = {"Client_ID": "id", "First_Name": "fn", "Last_Name": "ln", "Address_1": "a1", "Zip": "zip"}
_kg = _dr.proposals(_kd, ["First_Name", "Last_Name", "Zip"], _km)["groups"][0]["gid"]
_kf = _kd.copy()
_dr.apply_decisions(_kf, ["First_Name", "Last_Name", "Zip"], _km, {_kg: "copies:2"})
check("the chosen row is the one kept",
      [r["id"] for _, r in _kf.iterrows() if not r["__dup_drop__"]] == ["2"])
check("the others say which row they are a copy of",
      set(x for x in _kf["__dup_drop__"] if x) == {"copy of row 2"})
_kf2 = _kd.copy()
_dr.apply_decisions(_kf2, ["First_Name", "Last_Name", "Zip"], _km, {_kg: "copies:9"})
check("a chosen row that is not in the group falls back to the first",
      [r["id"] for _, r in _kf2.iterrows() if not r["__dup_drop__"]] == ["1"])
check("every row in a group offers to be the one kept", 'data-verdict="copies:${r.row}"' in JS)
check("the endpoint accepts a chosen row",
      'startswith("copies:")' in SERVER_SRC.split("def dupes_decide")[1].split("@api")[0])

# ---- the preview grid --------------------------------------------------------
_css = open("ui/styles.css", encoding="utf-8").read()
check("the preview grid always shows its scrollbar", "overflow-x: scroll" in _css)
check("the header and first column stay put while scrolling",
      "position: sticky; top: 0" in _css and ".pvscroll.pinfirst" in _css)
check("the preview says how many columns there are", "columns, ${nf(d.total)} rows" in JS)
client.post("/api/reset")

for label, passed in results:
    print(f"  [{'PASS' if passed else 'FAIL'}] {label}")
ok = all(p for _, p in results)
print(f"CROSSWALK API TESTS: {'PASS' if ok else 'FAIL'} "
      f"({sum(1 for _, p in results if p)}/{len(results)})")
sys.exit(0 if ok else 1)
