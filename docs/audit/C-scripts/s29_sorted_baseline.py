"""s29: baseline for s09: the same re-exported (sorted) A.csv, no corrections file at all."""
from invariants import *
import messy, io
import pandas as pd
files = messy.make()
a = pd.read_csv(io.BytesIO(files["A.csv"]), dtype=str, keep_default_na=False)
a2 = a.sort_values(["Last_Name", "First_Name", "Client_ID"], kind="stable").reset_index(drop=True)
reset(); upload({"A.csv": a2.to_csv(index=False).encode(), "B.csv": files["B.csv"], "C.csv": files["C.csv"]}); set_schema(dob=True); run()
print("sorted A.csv, no corrections file:", counts_line(True))
