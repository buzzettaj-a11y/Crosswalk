"""Accent folding in the person key (with a positive control) and the corrections reader. Encoding is in b35."""
from _common import *

def row(first, last, i, addr="10 Main St"):
    return dict(First=first, Last=last, ID=i, Addr=addr, Addr2="", City="Brooklyn", State="NY", Zip="11201")

print("== person key across two files: accents and punctuation ==")
pairs = [("Maria","Garcia","Maria","Garcia"), ("Maria","Garcia","MARIA","GARCIA"), ("Maria","Garcia","María","García"), ("Pat","OBrien","Pat","O'Brien"), ("Ana Maria","Lopez","Ana-Maria","Lopez"),
         ("Jose","Nunez","José","Núñez")]
for f1, l1, f2, l2 in pairs:
    dfA = engine.clean_dataframe(pd.DataFrame([row(f1, l1, "A1")]).astype(str))
    dfB = engine.clean_dataframe(pd.DataFrame([row(f2, l2, "B9")]).astype(str))
    res = engine.run_pipeline({"A.csv": dfA, "B.csv": dfB}, {"A.csv": MAPPING, "B.csv": MAPPING}, False, None, 1337, None, None, None, None, True)
    paired = any("possible duplicate" in m["message"].lower() or "possible" in m["message"].lower()
                 for r in res["transformed"] for m in r["__flags__"] if m["scenario"].startswith("9"))
    print(f"   {f1} {l1!r:14} vs {f2} {l2!r:14} -> paired as possible duplicate: {paired}")

print("\n== _corr_value (reads cells of a corrections file) ==")
for v in ["Na", "Nan", "None", "nan", "N/A", "Null"]:
    print(f"   {v!r:8} -> {engine._corr_value(v)!r}")

