from _common import *
import io
print("== normalize_zip direct ==")
for z in ["07030", "7030", "00501", "501", "11201-1234", "112011234", "11201 1234", "11201-", "7030.0", "11201.0", "1.1201E4", "11201 ", " 11201", "11,201", "NY 11201", "11201-123", "00000", "99999", "12345", "10001-0001", "112O1", "١١٢٠١"]:
    print(f"{z!r:16}", engine.normalize_zip(z))

print("\n== borough_from_zip ==")
for z in ["07030","10001","10292","10293","10301","10314","10315","10451","10475","10463","10499","11001","11004","11005","11101","11120","11201","11256","11257","11351","11430","11439","11451","11499","11500","11501","11530","11550","11553","11570","11580","11590","11599","11600","11690","11691","11697","11698","11701","11801","10701","10550","10801"]:
    print(z, repr(engine.borough_from_zip(z)))

print("\n== xlsx numeric ZIP ==")
import openpyxl, tempfile
wb = openpyxl.Workbook(); ws = wb.active
ws.append(["First","Last","ID","Addr","City","State","Zip"])
ws.append(["A","B","1","10 Main St","Hoboken","NJ",7030])          # int, numeric
ws.append(["C","D","2","10 Main St","Brooklyn","NY",11201.0])       # float
ws.append(["E","F","3","10 Main St","Queens","NY","11355"])         # text
ws.append(["G","H","4","10 Main St","Brooklyn","NY",501])
bio = io.BytesIO(); wb.save(bio)
class U:  # minimal uploaded-file stand-in
    name="z.xlsx"
    def getvalue(self): return bio.getvalue()
df = engine.read_uploaded_file(U())
print(df)
