"""
s08: corrections file re-upload (a Manual_Review_Needed export sent back).
 (a) what happens to decisions already made, (b) does the screen change before a re-run,
 (c) rows are addressed by Source_Row position, not identifier: a changed source file silently
     receives corrections meant for other people.
"""
from invariants import *
import messy, io

files = messy.make()
setup_standard(files, dob=True)
report("0 run")

# decisions first
decide("dupc", "aside")
decide("noaddr", "held")
decide("idconflict", "accept_all")
snap0, _ = report("1 three group decisions")
print("   actions before upload:", len(cw.S["actions"]))

# export the review file, fix the ZIP of the blank-zip row, upload it back
rv = export_df("review")
print("   review file rows:", len(rv), "| statuses:", rv["Resolution_Status"].value_counts().to_dict())
zcol = [c for c in rv.columns if c.lower() == "orig::zip"][0]
ccol = [c for c in rv.columns if c.lower() == "orig::city"][0]
fix = rv[rv["Error_Reason"].str.contains("Invalid ZIP Code format: \\(blank\\)") & ~rv["Error_Reason"].str.contains("City could not")].copy()
print("   rows we will fix (zipbad):", fix[["Source_File", "Source_Row"]].values.tolist())
rv.loc[fix.index, zcol] = "11201"
corr_bytes = rv.to_csv(index=False).encode()
upload({"Manual_Review_Needed.csv": corr_bytes})
print("   corrections files held:", [(n, len(d)) for n, d in cw.S["corrections_files"]])
print("   tables after upload (corrections not loaded as a source):", len(tables()))
snap1, f1 = report("2 right after uploading the corrections file (no re-run yet)")
print("   actions still there:", len(cw.S["actions"]))

# nothing has changed on screen; to apply, the operator must press Process
run()
snap2, f2 = report("3 after Process (corrections applied)")
print("   actions after Process:", len(cw.S["actions"]), "<- review decisions made earlier")
print("   groups now:", [(g["id"], g["count"], g["status"]) for g in groups()])

# (c) a changed source file
print("\n--- (c) the source file changes between the export of the review file and the re-upload ---")
reset()
files2 = messy.make()
upload(files2); set_schema(dob=True); run()
rv = export_df("review")
zrow = rv[rv["Error_Reason"].str.contains("Invalid ZIP Code format: \\(blank\\)") & ~rv["Error_Reason"].str.contains("City could not")]
tgt = int(zrow["Source_Row"].iloc[0]); print("   zipbad row is A.csv row", tgt, "id", zrow["orig::Client_ID"].iloc[0])
rv.loc[zrow.index, zcol] = "11201"
corr_bytes = rv.to_csv(index=False).encode()
# the source system is re-exported with one new client at the top
import pandas as pd
a = pd.read_csv(io.BytesIO(files2["A.csv"]), dtype=str, keep_default_na=False)
newrow = pd.DataFrame([["A777", "Newly", "Added", "2001-01-01", "9 New St", "Bronx", "NY", "10451", "Youth"]], columns=a.columns)
a2 = pd.concat([newrow, a], ignore_index=True)
files3 = dict(files2); files3["A.csv"] = a2.to_csv(index=False).encode()
reset(); upload({"A.csv": files3["A.csv"], "B.csv": files3["B.csv"], "C.csv": files3["C.csv"]}); set_schema(dob=True)
upload({"Manual_Review_Needed.csv": corr_bytes})
run()
# what did the correction do?
fr = [k for k in cw.S["frames"] if k.startswith("A.csv")][0]
df = cw.S["frames"][fr]
print("   row", tgt, "of the NEW A.csv now reads:", df.iloc[tgt].to_dict())
print("   (that row was client", files3["A.csv"].decode().splitlines()[tgt + 1].split(",")[0], "in the new file)")
audit = export_raw("audit").decode()
print("   audit lines for corrected rows:", [l for l in audit.splitlines() if "Values replaced from corrections" in l][:3])
