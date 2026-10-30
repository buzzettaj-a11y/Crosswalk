from _common import *
import io
class U:
    def __init__(s, name, b): s.name, s._b = name, b
    def getvalue(s): return s._b
bom = "﻿First,Last,ID,Addr,Addr2,City,State,Zip\nAna,Lopez,A1,10 Main St,,Brooklyn,NY,11201\n".encode("utf-8")
df = engine.read_uploaded_file(U("bom.csv", bom)); print("BOM csv columns:", list(df.columns))
bom16 = "First,Last,ID,Addr,Addr2,City,State,Zip\nAna,Lopez,A1,10 Main St,,Brooklyn,NY,11201\n".encode("utf-16")
try:
    df = engine.read_uploaded_file(U("u16.csv", bom16)); print("UTF-16 csv columns:", list(df.columns))
except Exception as e: print("UTF-16 csv ->", type(e).__name__, str(e)[:80])
latin = "First,Last,ID,Addr,Addr2,City,State,Zip\nJos\xe9,Mu\xf1oz,A1,10 Main St,,Brooklyn,NY,11201\n".encode("latin-1")
try:
    df = engine.read_uploaded_file(U("lat.csv", latin)); print("latin-1 csv ->", df.iloc[0].tolist())
except Exception as e: print("latin-1 csv ->", type(e).__name__, str(e)[:80])

print("\nIDs that differ only by an invisible character are not seen as the same ID:")
rows = [dict(First="Ana", Last="Lopez", ID="A1", Addr="10 Main St", Addr2="", City="Brooklyn", State="NY", Zip="11201"),
        dict(First="Ana", Last="Lopez", ID="A1​", Addr="10 Main St", Addr2="", City="Brooklyn", State="NY", Zip="11201")]
res = pipeline(rows)
for r in res["transformed"]: print("  ", repr(r["Client_ID"]), "->", "REVIEW: " + "; ".join(r["__errors__"]) if r["__errors__"] else "CLEAN")
rows[1]["ID"] = "A1"
res = pipeline(rows)
print("  with identical plain IDs:")
for r in res["transformed"]: print("  ", repr(r["Client_ID"]), "->", "REVIEW: " + "; ".join(r["__errors__"]) if r["__errors__"] else "CLEAN")

print("\nname with ZWSP / soft hyphen / NUL / BOM stays in the clean row:")
for v in ["Ana​", "﻿Ana", "An­a", "Ana\x00"]:
    st, r = final(First=v)
    print("  ", repr(v), "->", st, repr(r["First_Name"]))
print("\nfull-width and Arabic-Indic digits in a ZIP:")
for v in ["１１２０１", "١١٢٠١"]:
    st, r = final(Zip=v)
    print("  ", repr(v), "->", st, "Zip=", repr(r["Zip"]), "City=", r["City"])
print("\nMiddle initial placeholders:")
for v in ["NMI", "NMN", "None", "N/A", "Jr", "no", "Unknown", ".", "(none)", "X"]:
    mi, note = engine.normalize_middle_initial(v)
    print("  ", repr(v), "->", repr(mi), note)
