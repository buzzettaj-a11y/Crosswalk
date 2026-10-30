"""
s09: a corrections file is addressed by (Source_File, Source_Row) position. If the source file is
re-exported in a different order (same rows, same count), the corrections land on other people.
Also: when the table range changes, they silently do not apply and nothing says so.
"""
from invariants import *
import messy, io
import pandas as pd

files = messy.make()
reset(); upload(files); set_schema(dob=True); run()
rv = export_df("review")
zcol = [c for c in rv.columns if c.lower() == "orig::zip"][0]
# the operator fixes the blank ZIP of A900 (Zed Zimmer) in the review file
mask = rv["orig::Client_ID"] == "A900"
rv.loc[mask, zcol] = "11201"
corr = rv.to_csv(index=False).encode()
print("corrections file rows:", len(rv), "| fixed row:", rv.loc[mask, ["Source_File", "Source_Row", "orig::Client_ID", "orig::First_Name"]].values.tolist())

# next day: fresh session, the system is re-exported SORTED BY LAST NAME (same rows, same count)
a = pd.read_csv(io.BytesIO(files["A.csv"]), dtype=str, keep_default_na=False)
a2 = a.sort_values(["Last_Name", "First_Name", "Client_ID"], kind="stable").reset_index(drop=True)
reset()
upload({"A.csv": a2.to_csv(index=False).encode(), "B.csv": files["B.csv"], "C.csv": files["C.csv"]})
set_schema(dob=True)
upload({"Manual_Review_Needed.csv": corr})
run()

fr = [k for k in cw.S["frames"] if k.startswith("A.csv")][0]
df = cw.S["frames"][fr]
print("\nA900 (Zed Zimmer) is now at row", int(a2.index[a2['Client_ID'] == 'A900'][0]), "in the re-exported file")
# which rows differ from the re-exported file the operator supplied?
orig = a2.astype(str)
cur = df.astype(str)
changed = [(i, a2.loc[i, "Client_ID"], a2.loc[i, "First_Name"] + " " + a2.loc[i, "Last_Name"]) for i in range(len(orig))
           if not (orig.iloc[i].values == cur.iloc[i].values).all()]
print("rows of the raw frame that were overwritten by the corrections file:", len(changed))
for i, cid, nm in changed[:10]:
    print(f"   row {i}: was {cid} {nm!r:<22} -> now {cur.iloc[i]['Client_ID']} {cur.iloc[i]['First_Name']} {cur.iloc[i]['Last_Name']} zip {cur.iloc[i]['Zip']}")
print("row for A900 itself:", cur[cur['Client_ID'] == 'A900'][['Client_ID', 'Zip']].values.tolist())
print("summary:", counts_line())
audit = export_raw("audit").decode()
print([l for l in audit.splitlines() if "Values replaced from corrections" in l][:2])
