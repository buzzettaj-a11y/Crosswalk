"""Real .xlsx date cells and numeric ZIP cells uploaded through the server (table_detect path), then the fast path."""
from _api import *
import io, openpyxl, datetime
wb = openpyxl.Workbook(); ws = wb.active
ws.append(["First Name","Last Name","Client ID","Street Address","City","State","Zip","DOB"])
ws.append(["Ana","Lopez","6001","10 Main St","Brooklyn","NY",11201,datetime.datetime(1990,3,4)])
ws.append(["Bo","Chen","6002","12 Oak Ave","Queens","NY",11355,datetime.date(1985,12,25)])
ws.append(["Cy","Diaz","6003","14 Elm St","Bronx","NY",10452,"03/04/1990"])
ws.append(["Di","Khan","6004","16 Pine St","Brooklyn","NY",11201,32874])
bio = io.BytesIO(); wb.save(bio)
c = new_client()
upload(c, {"intake.xlsx": bio.getvalue()})
for k, df in cw.S["frames"].items():
    print("frame", k); print(df.to_string())
# add DOB to the schema as a date field, map it, run
schema = [dict(f) for f in cw.engine.DEFAULT_SCHEMA] + [{"role":"custom","label":"DOB","dtype":"date","length":0,"required":False}]
c.post("/api/schema", json={"schema": schema})
c.post("/api/express/run", json={})
for _ in range(400):
    if c.get("/api/run/status").json()["state"] != "running": break
    time.sleep(0.05)
res = cw.S["results"]
if not res:
    print("express run produced no results; check:", c.get("/api/express/check").json())
else:
    for rec in res["transformed"]:
        print(rec["Client_ID"], "REVIEW: " + "; ".join(rec["__errors__"]) if rec["__errors__"] else "CLEAN", "| DOB stored:", repr(rec["__custom__"].get("DOB")))
