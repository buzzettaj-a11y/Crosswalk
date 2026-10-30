"""
s18: after a run and review decisions, change the set-up (mapping, table inclusion, header row,
program grouping, program column) WITHOUT re-running. What do the Results, the exports and the audit say?
Each case starts from the same state: messy fixture, run, three group decisions.
"""
from invariants import *
import messy, hashlib


def start():
    setup_standard(messy.make(), dob=True)
    decide("dupc", "aside"); decide("idconflict", "accept_all"); decide("zipbad", "sent")
    summary(True)     # Results screen opened: identity computed
    return counts_line(True)


def tkey(f):
    return [t for t in tables() if t["file"] == f][0]["key"]


print("baseline:", start())

# 1. exclude a table after decisions (no re-run)
client.post("/api/sources/include", json={"key": tkey("C.csv"), "on": False})
print("\n1. C.csv excluded, no re-run")
print("   sources screen says rows staged:", ui("sources")["sources"]["stats"]["rows"], "| Results says rows received:", summary()["rows"]["input"])
print("   Download screen: ", ui("export")["export"]["recon"])
print("   audit set-up says C.csv:", [l for l in export_raw("audit").decode().splitlines() if l.startswith("Table C.csv")])
print("   Final_Clean_Mapped still contains C.csv rows:", int((export_df("clean")["Source_File"].str.startswith("C.csv")).sum()))
# restore
client.post("/api/undo")

# 2. change a column mapping after decisions
print("\n2. Last_Name remapped to the Address column (a wrong choice), no re-run")
client.post("/api/map", json={"table": tkey("B.csv"), "field": "Last_Name", "column": "Address"})
print("   Results:", counts_line())
print("   audit set-up Matching for B.csv:", [l[:90] for l in export_raw("audit").decode().splitlines() if l.startswith("Matching for B.csv")])
print("   Final_Clean_Mapped B.csv Last_Name sample:", export_df("clean").query("Source_File.str.startswith('B.csv')", engine="python")["Last_Name"].head(2).tolist())
client.post("/api/undo")

# 3. header row change on a table with decisions
print("\n3. header row set to 2 on A.csv (drops the first data row), no re-run")
key = tkey("A.csv")
before_tb = [t for t in tables() if t["key"] == key][0]["rows"]
r = client.post("/api/map/header", json={"key": key, "row": 2}).json()
print("   response:", r)
print("   S['tables'] rows column still says:", [t for t in tables() if t["key"] == key][0]["rows"], "| frame now has:", len(cw.S["frames"][key]))
print("   Results rows received:", summary()["rows"]["input"], "| sources screen rows:", ui("sources")["sources"]["stats"]["rows"])
print("   audit says:", [l for l in export_raw("audit").decode().splitlines() if l.startswith("Table A.csv")])
print("   actions still held:", len(cw.S["actions"]), "-> rids now point at different rows")

# 4. program grouping changed after the run
print("\n4. (fresh) program group changed after the run, no re-run")
print("   baseline:", start())
ui("programs")
client.post("/api/programs/group", json={"name": "Youth", "into": "Housing"})
print("   Youth merged into Housing, Results still say:", counts_line(True), summary(True)["goal2"]["totals"])
print("   audit set-up says:", [l for l in export_raw("audit").decode().splitlines() if "<-" in l][:3])
