"""s25: same three files uploaded in a different order: which output columns/rows differ in content, not just order."""
from invariants import *
import messy
files = messy.make()
def go(order):
    reset(); upload({k: files[k] for k in order}); set_schema(dob=True); run()
    return {w: export_df(w) for w in ("clean", "review", "aside", "unique_clients", "unique_by_program")}
a = go(["A.csv", "B.csv", "C.csv"]); b = go(["C.csv", "B.csv", "A.csv"])
for w in a:
    A, B = a[w], b[w]
    if len(A) != len(B):
        print(w, "row counts differ", len(A), len(B)); continue
    key = [c for c in ("Source_File", "Source_Row", "Master_ID") if c in A.columns][:2]
    A2 = A.sort_values(key).reset_index(drop=True); B2 = B.sort_values(key).reset_index(drop=True)
    diffcols = [c for c in A.columns if not (A2[c] == B2[c]).all()]
    print(f"{w:<18} same order: {A.equals(B)} | after sorting by {key}: differing columns = {diffcols}")
    if diffcols:
        c = diffcols[0]; i = (A2[c] != B2[c]).idxmax(); print("    e.g.", c, repr(A2.loc[i, c]), "vs", repr(B2.loc[i, c]))
