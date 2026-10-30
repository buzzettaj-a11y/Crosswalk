"""Auto-mapping mistakes followed through the fast path (express check, then express run): what is stored, and is the row clean?"""
from _api import *

def go(label, header, rows):
    c = new_client()
    body = ",".join(header) + "\n" + "\n".join(",".join(f'"{v}"' for v in r) for r in rows) + "\n"
    upload(c, {"case.csv": body.encode()})
    m = c.get("/api/ui?screen=map").json()["map"]["tables"][0]
    mapped = {f["role"]: f["col"] for f in m["fields"] if f["col"]}
    chk = c.get("/api/express/check").json()
    c.post("/api/express/run", json={})
    for _ in range(400):
        if c.get("/api/run/status").json()["state"] != "running": break
        time.sleep(0.05)
    print(f"== {label}")
    print("   mapped:", mapped)
    print("   express check ok =", chk["ok"], "| warnings =", chk["warnings"], "| blockers =", chk["blockers"])
    res = cw.S["results"]
    if not res:
        print("   (express run did not produce results)"); return
    for rec in res["transformed"][:2]:
        st = "REVIEW " + str(rec["__errors__"]) if rec["__errors__"] else "CLEAN"
        prog = rec.get("__program__", "")
        print(f"   stored First={rec['First_Name']!r} Last={rec['Last_Name']!r} ID={rec['Client_ID']!r} A1={rec['Address_1']!r} City={rec['City']!r} Zip={rec['Zip']!r} Program={prog!r}  {st}")

go("Emergency-contact name columns come first in the file",
   ["Emergency Contact First Name","Emergency Contact Last Name","First Name","Last Name","Client ID","Street Address","City","State","Zip"],
   [("Rosa","Diaz","Ana","Lopez","5001","10 Main St","Brooklyn","NY","11201"),
    ("Luis","Perez","Bo","Chen","5002","11 Main St","Brooklyn","NY","11201")])

go("Mailing address columns come before Home address columns",
   ["First Name","Last Name","Client ID","Mailing Address","Mailing City","Mailing State","Mailing Zip","Home Address","Home City","Home State","Home Zip"],
   [("Ana","Lopez","5101","99 Elm St","Brooklyn","NY","11202","10 Main St","Brooklyn","NY","11201"),
    ("Bo","Chen","5102","98 Elm St","Queens","NY","11355","12 Oak Ave","Queens","NY","11354")])

go("'Last Visit' comes before 'Surname'",
   ["First Name","Last Visit","Surname","Client ID","Street Address","City","State","Zip"],
   [("Ana","March 2024","Lopez","5201","10 Main St","Brooklyn","NY","11201"),
    ("Bo","June 2024","Chen","5202","12 Oak Ave","Queens","NY","11355")])

go("No Program column, but 'Program Start Date' with US-format dates",
   ["First Name","Last Name","Client ID","Street Address","City","State","Zip","Program Start Date"],
   [("Ana","Lopez","5301","10 Main St","Brooklyn","NY","11201","03/04/2024"),
    ("Bo","Chen","5302","12 Oak Ave","Queens","NY","11355","06/15/2024")])

go("'Program ID' is the only ID-like column; 'Household ID' is the client's",
   ["First Name","Last Name","Program ID","Street Address","City","State","Zip"],
   [("Ana","Lopez","P-7","10 Main St","Brooklyn","NY","11201"),
    ("Bo","Chen","P-7","12 Oak Ave","Queens","NY","11355")])

go("'Place of Birth City' comes before 'City of Residence'",
   ["First Name","Last Name","Client ID","Street Address","Place of Birth City","City of Residence","State","Zip"],
   [("Ana","Lopez","5401","10 Main St","San Juan","Brooklyn","NY","11201"),
    ("Bo","Chen","5402","12 Oak Ave","Beijing","Queens","NY","11355")])

go("'Program ID' is the only ID-like column, values unique per row (enrollment numbers)",
   ["First Name","Last Name","Program ID","Street Address","City","State","Zip"],
   [("Ana","Lopez","P-7","10 Main St","Brooklyn","NY","11201"),
    ("Bo","Chen","P-8","12 Oak Ave","Queens","NY","11355")])
