"""s01: baseline on the sample files. Compare summary vs exports, partition check."""
from cwlib import *
import glob

files = {os.path.basename(p): open(p, "rb").read() for p in sorted(glob.glob(ROOT + "/sample_data/*"))}
setup_standard(files, dob=False)
print(counts_line())
ok, rw = balanced()
print("balanced:", ok, rw, "frames rows:", input_rows())

g1, g2, per = independent_goals()
s = summary()
print("exports  G1/G2:", g1, g2)
print("summary  G1/G2:", s["goal1"]["count"], s["goal2"]["count"])
print("per program summary:", s["goal2"]["totals"])
print("per program export :", per)

clean = export_df("clean")
uc = export_df("unique_clients")
print("clean rows", len(clean), "unique_clients rows", len(uc), "source record count sum", uc["Source_Record_Count"].astype(int).sum())
# partition check: each clean row's (file,row) appears exactly once in Source_Rows
rids = [x for cell in uc["Source_Rows"] for x in cell.split("; ")]
print("rids in unique_clients:", len(rids), "distinct:", len(set(rids)))
exp = {f"{r.Source_File}||{r.Source_Row}" for r in clean.itertuples()}
print("missing from unique_clients:", len(exp - set(rids)), "extra:", len(set(rids) - exp))
print("review rows export", len(export_df("review")), "aside", len(export_df("aside")))
print("groups:", [(g['id'], g['count']) for g in groups()])
