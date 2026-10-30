"""s35: switching DOB off in the clean file: does Goal 1 change?"""
from invariants import *
import messy
setup_standard(messy.make(), dob=True)
before = counts_line(True); b_cols = "DOB" in export_df("clean").columns
client.post("/api/export/col", json={"name": "DOB", "on": False})
after = counts_line(True); a_cols = "DOB" in export_df("clean").columns
print("before:", before, "| DOB in file:", b_cols)
print("after :", after, "| DOB in file:", a_cols)
