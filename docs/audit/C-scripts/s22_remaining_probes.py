"""
s22: the remaining probes.
 A. ungrouping a program spelling that is the group's name does nothing
 B. a summary row ('TOTAL') crashes the Manual_Review_Needed export and the Download screen numbers
 C. a re-upload of a file with the same name: what is kept
 D. a 'different' verdict on a pair is overridden by a chain of automatic joins
 E. rows that never reach the pipeline (blank lines in a CSV): input count vs the file
 F. Goal 2 for a person whose rows are all blank-program: what the screen says
"""
from invariants import *
import pandas as pd

H = ["Client_ID", "First_Name", "Last_Name", "DOB", "Address", "City", "State", "Zip", "Program"]


def mk(rows, cols=H):
    return pd.DataFrame(rows, columns=cols).to_csv(index=False).encode()


print("== A. ungroup")
A = mk([["A1", "Ana", "Perez", "1990-05-06", "7 Elm St", "New York", "NY", "10013", "Workforce Development"]])
B = mk([["B1", "Ana", "Perez", "1990-05-06", "7 Elm St", "New York", "NY", "10013", "Workforce Dev."]])
reset(); upload({"A.csv": A, "B.csv": B}); set_schema(dob=True)
pg = ui("programs")["programs"]
print("   proposed groups:", [(g["canonical"], [v["name"] for v in g["variants"]]) for g in pg["groups"]])
client.post("/api/programs/apply", json={"columns": [], "groups": [
    {"canonical": g["canonical"], "names": [v["name"] for v in g["variants"]]} for g in pg["groups"]]})
run()
print("   confirmed:", counts_line(True), summary(True)["goal2"]["totals"])
canon = [g["canonical"] for g in ui("programs")["programs"]["groups"]][0]
other = [v["name"] for g in ui("programs")["programs"]["groups"] for v in g["variants"] if v["name"] != canon][0]
print(f"   the operator pulls '{canon}' (the group's own name) out to count it alone")
client.post("/api/programs/group", json={"name": canon, "into": "__alone__"})
print("   groups now:", [(g["canonical"], [v["name"] for v in g["variants"]]) for g in cw.S["program_groups"]])
print("   alias map :", cw.S["program_aliases"])
run()
print("   after Process:", counts_line(True), summary(True)["goal2"]["totals"], "(two separate names were asked for)")

print("\n== B. summary row")
S1 = mk([["A1", "Ada", "Lee", "1980-01-01", "10 Oak St", "Brooklyn", "NY", "11201", "Housing"],
         ["", "TOTAL", "", "", "", "", "", "", ""]])
reset(); upload({"s.csv": S1}); set_schema(dob=True); run()
print("   rows:", summary()["rows"])
for w in ("review", "aside", "clean", "unique_clients"):
    r = client.get(f"/api/export/file?which={w}")
    print(f"   export {w:<15} -> HTTP {r.status_code} {'' if r.status_code == 200 else r.text[:70]}")
print("   Download screen:", ui("export").get("export", {}).get("recon") if "__status__" not in ui("export") else ui("export")["__status__"])
r = client.get("/api/audit"); print("   GET /api/audit ->", r.status_code)

print("\n== C. a second upload of a file with the same name but different content")
v1 = mk([["A1", "Ada", "Lee", "1980-01-01", "10 Oak St", "Brooklyn", "NY", "11201", "Housing"]])
v2 = mk([["A1", "Ada", "Lee", "1980-01-01", "10 Oak St", "Brooklyn", "NY", "11201", "Housing"],
         ["A2", "Ben", "Cho", "1981-02-02", "11 Oak St", "Brooklyn", "NY", "11201", "Housing"]])
reset(); upload({"x.csv": v1}); set_schema(dob=True)
r = upload({"x.csv": v2})
print("   upload response:", {k: r[k] for k in r if k in ("ok", "added", "skipped", "held", "note", "tables")} if isinstance(r, dict) else r)
print("   frames rows now:", {k: len(v) for k, v in cw.S["frames"].items()}, "| uploads bytes:", {k: len(v) for k, v in cw.S["uploads"].items()})
run(); print("   after Process:", counts_line(True))

print("\n== D. 'different' verdict on a pair that is joined through a third record")
H3 = ["Client_ID", "First_Name", "Last_Name", "DOB", "Address", "City", "State", "Zip", "Program"]
p = ["Maria", "Rodriguez", "1985-03-14", "100 Grand Concourse", "Bronx", "NY", "10451"]
X = mk([["X1"] + p + ["Housing"]])
Y = mk([["Y1"] + p + ["Youth"]])
Z = mk([["Z1"] + p + ["Workforce"]])
reset(); upload({"X.csv": X, "Y.csv": Y, "Z.csv": Z}); set_schema(dob=True); run()
print("   three identical records:", counts_line(True), "| auto links:", len(cw.S["identity"]["auto_links"]))
ids = list(cw.S["identity"]["master_of"])
print("   the operator says X and Y are different people (API verdict):",
      client.post("/api/identity/decide", json={"a": ids[0], "b": ids[1], "verdict": "different"}).json())
print("   after verdict:", counts_line(True), "<- rejected pair still in one person via Z; rejected:", len(cw.S["identity"]["rejected"]))
print("   proposals offered for that pair:", len(cw.S["identity"]["proposals"]))

print("\n== E. blank lines / all-empty rows in a CSV")
raw = ("Client_ID,First_Name,Last_Name,DOB,Address,City,State,Zip,Program\n"
       "A1,Ada,Lee,1980-01-01,10 Oak St,Brooklyn,NY,11201,Housing\n"
       "\n"
       ",,,,,,,,\n"
       "A2,Ben,Cho,1981-02-02,11 Oak St,Brooklyn,NY,11201,Housing\n").encode()
reset(); upload({"b.csv": raw}); set_schema(dob=True); run()
print("   data lines in the file: 4 (one blank line, one row of commas)")
print("   rows received:", summary()["rows"], "| audit 'dropped'/'blank' lines:",
      [l[:100] for l in export_raw("audit").decode().splitlines() if "blank" in l.lower() or "empty" in l.lower()][:4])
