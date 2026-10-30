"""
s17: exports vs the Download screen, columns, and PII in the audit trail.
"""
from invariants import *
import messy, re
import pandas as pd

H = ["Client_ID", "First_Name", "Last_Name", "DOB", "Address", "Address_2", "City", "State", "Zip", "Program"]
rows = [
    ["P1", "Marisol", "Quintanilla", "1984-07-19", "4417 Wyckoff Avenue", "Apt 3B", "Brooklyn", "NY", "11201", "Housing"],
    ["P2", "Tobias", "Fenwick", "1971-02-11", "92 Ocelot Place", "Apt 9C", "Brooklyn", "NY", "11201", "Housing"],
    ["P3", "Odalys", "Pemberton", "1990-12-01", "18 Marlowe Court Apt 4D", "Apt 7F", "Brooklyn", "NY", "11201", "Youth"],   # unit conflict
    ["P4", "Ignatius", "Brightwater", "1963-05-30", "301 Zinnia Drive", "c/o Jane Doe", "Brooklyn", "NY", "11201-4455", "Youth"], # ZIP+4, c/o
    ["P5", "Lorelei", "Vandermeer", "1999-09-09", "55 Cobalt Lane", "", "Wodside", "NY", "11377", "Housing"],                   # city typo
    ["P6", "Anselm", "Okonkwo", "1955-01-01", "12 Juniper Street", "", "Queens", "NY", "10451", "Housing"],                     # city/zip conflict
    ["P7", "Philippa", "Strongbow", "1949-04-04", "7 Quill Road", "", "Brooklyn", "NY", "", "Housing"],                        # zip blank (fillable?)
]
data = pd.DataFrame(rows, columns=H).to_csv(index=False).encode()
messy_files = messy.make()
files = {"P.csv": data, **messy_files}
reset(); upload(files); set_schema(dob=True)
# map Address_2
for t in map_ui()["tables"]:
    pass
run()
# a fill approval and a decision with a note
client.post("/api/review/group", json={"gid": "zipbad", "decision": "sent"})
client.post("/api/fill/apply", json={})
audit = export_raw("audit").decode()
print("audit bytes:", len(audit))

# every name, street, DOB in the data: does any appear in the audit?
leaks = {}
allv = pd.concat([pd.read_csv(io.BytesIO(b), dtype=str, keep_default_na=False) for b in files.values()], ignore_index=True).fillna("")
low = audit.lower()
for col in ("First_Name", "Last_Name", "Address", "Address_2", "DOB"):
    if col not in allv.columns:
        continue
    for v in sorted(set(allv[col]) - {""}):
        if len(v) >= 4 and v.lower() in low:
            leaks.setdefault(col, []).append(v)
print("data values found inside Secure_Audit_Log, by column:", {k: v[:6] for k, v in leaks.items()})
for l in audit.splitlines():
    if any(x in l for x in ("Unit conflict", "recorded as", "standardized", "filled", "default", "conflict:", "ZIP+4", "reduced")):
        print("   ", l[:200])

# Download screen vs files
ex = ui("export")["export"]
clean = export_df("clean")
print("\nDownload screen column chips :", [c["name"] for c in ex["cols"]])
print("Final_Clean_Mapped columns   :", list(clean.columns))
print("in file, not on screen       :", [c for c in clean.columns if c not in [x["name"] for x in ex["cols"]]])
client.post("/api/export/col", json={"name": "Resolution_Status", "on": False})
print("after switching Resolution_Status off, still in file:", "Resolution_Status" in export_df("clean").columns)
client.post("/api/export/col", json={"name": "DOB", "on": False})
print("after switching DOB off, DOB in clean file:", "DOB" in export_df("clean").columns,
      "| DOB still used for identity:", ui("summary")["summary"]["goal1"]["count"])
print("Unique_Clients columns:", list(export_df("unique_clients").columns))
print("Set_Aside columns     :", list(export_df("aside").columns))
print("Manual_Review columns (head):", list(export_df("review").columns)[:6])
print("Quality columns       :", list(export_df("quality").columns))
