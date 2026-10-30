"""Upload behaviour: bad file in a batch, re-upload under the same name, blank line inside a CSV."""
import os, sys, json
HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, HERE)
import a_lib
work = sys.argv[1]
FIX = os.path.join(os.path.dirname(HERE), "A-fixtures")
cw, _ = a_lib.boot(work)
from fastapi.testclient import TestClient
c = TestClient(cw.api, base_url="http://127.0.0.1:8765", raise_server_exceptions=False)

print("=== T4: a batch of [good, bad.docx, good2]")
c.post("/api/reset")
good1 = open(os.path.join(FIX, "v1.csv"), "rb").read()
good2 = open(os.path.join(FIX, "blankline.csv"), "rb").read()
r = a_lib.upload_bytes(c, [("first_ok.csv", good1), ("Smith J intake.docx", b"not a table"), ("third_ok.csv", good2)])
print("HTTP", r.status_code, r.text[:80])
src = c.get("/api/ui?screen=sources").json()["sources"]
print("tables loaded:", [t["file"] for t in src["tables"]])
print("uploads recorded (audit 'Files loaded'):", sorted(cw.S["uploads"]))
print("source download route serves the failed file:", c.get("/api/source/file", params={"name": "Smith J intake.docx"}).status_code)

print("=== T3: re-upload a corrected file under the same name")
c.post("/api/reset")
a_lib.upload_bytes(c, [("export.csv", good1)])
t1 = c.get("/api/ui?screen=sources").json()["sources"]["tables"]
print("first upload rows:", [(t["key"], t["rows"]) for t in t1])
v2 = open(os.path.join(FIX, "v2_same_name_more_rows.csv"), "rb").read()
r = a_lib.upload_bytes(c, [("export.csv", v2)])
t2 = c.get("/api/ui?screen=sources").json()["sources"]["tables"]
print("after re-upload of a 4-row file under the same name, tables:", [(t["key"], t["rows"]) for t in t2])
print("bytes held for 'Open the source file' have rows:", cw.S["uploads"]["export.csv"].count(b"\n") - 1)
print("rows the pipeline will see:", sum(len(f) for f in cw.S["frames"].values()))

print("=== T5: a blank line in the middle of a CSV")
c.post("/api/reset")
a_lib.upload_bytes(c, [("blank.csv", good2)])
s = c.get("/api/ui?screen=sources").json()["sources"]
for t in s["tables"]:
    print(" table", t["key"], "rows", t["rows"], "kind", t["kind"], "included", s["included"][t["key"]], "|", t["reason"])
print("file has", good2.decode().count("\n") - 1, "data lines (excluding blank)")
a_lib.relax_client_id(c)
m = a_lib.fix_mapping(c)
a_lib.run(c)
rd = a_lib.runstate(c)["results"]
print("run counts", {k: rd[k] for k in ("input","clean","review")})
sm = a_lib.summary(c)
print("summary rows card:", sm["rows"])
html = c.get("/api/summary").text
import re
print("printable 'Rows received':", re.search(r"Rows received</th><td>([\d,]+)", html).group(1))
print("printable books-balance line:", re.search(r"The books balance:[^<]*", html).group(0).replace("\n"," ")[:160])
