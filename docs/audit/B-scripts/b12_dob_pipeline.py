from _common import *
import io, openpyxl, datetime
schema = [dict(f) for f in engine.DEFAULT_SCHEMA] + [{"role":"custom","label":"DOB","dtype":"date","length":0,"required":False}]
mapping = dict(MAPPING); mapping["DOB"] = "DOB"
def dob(v):
    base = {"First":"Ana","Last":"Lopez","ID":"A1","Addr":"10 Main St","Addr2":"","City":"Brooklyn","State":"NY","Zip":"11201","DOB":v}
    res = pipeline([base], schema=schema, mapping=mapping)
    r = res["transformed"][0]
    st = "REVIEW: " + "; ".join(r["__errors__"]) if r["__errors__"] else "CLEAN"
    return st, r["__custom__"].get("DOB"), [f["message"] for f in r["__flags__"] if "DOB" in f["message"]]
for v in ["03/04/1990","13/04/1990","1/2/26","1/2/45","2045-01-02","03/04/2050","12345","99999","73051","60000","00000","32874","19900304","1990-03-04 00:00:00","32874.0","","N/A","0"]:
    print(f"{v!r:24} -> {dob(v)}")

print("\n-- real xlsx date cells read through read_uploaded_file --")
wb = openpyxl.Workbook(); ws = wb.active
ws.append(["First","Last","ID","Addr","City","State","Zip","DOB"])
ws.append(["A","B","1","10 Main St","Brooklyn","NY","11201",datetime.datetime(1990,3,4)])
ws.append(["C","D","2","10 Main St","Brooklyn","NY","11201",datetime.date(1985,12,25)])
ws.append(["E","F","3","10 Main St","Brooklyn","NY","11201","03/04/1990"])
ws.append(["G","H","4","10 Main St","Brooklyn","NY","11201",32874])
bio = io.BytesIO(); wb.save(bio)
class U:
    name="d.xlsx"
    def getvalue(self): return bio.getvalue()
df = engine.read_uploaded_file(U())
print(df[["ID","DOB"]].to_string())
res = engine.run_pipeline({"d.xlsx": df}, {"d.xlsx": mapping}, False, None, 1337, None, None, schema, None, True)
for r in res["transformed"]:
    print(r["Client_ID"], "REVIEW: "+"; ".join(r["__errors__"]) if r["__errors__"] else "CLEAN", r["__custom__"].get("DOB"))
