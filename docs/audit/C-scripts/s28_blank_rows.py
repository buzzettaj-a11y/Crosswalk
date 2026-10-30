"""s28: a CSV with a blank line and an all-empty row between two real rows. Where does the second real row go?"""
from invariants import *
raw = ("Client_ID,First_Name,Last_Name,DOB,Address,City,State,Zip,Program\n"
       "A1,Ada,Lee,1980-01-01,10 Oak St,Brooklyn,NY,11201,Housing\n"
       "\n"
       ",,,,,,,,\n"
       "A2,Ben,Cho,1981-02-02,11 Oak St,Brooklyn,NY,11201,Housing\n"
       "A3,Cy,Roe,1982-03-03,12 Oak St,Brooklyn,NY,11201,Housing\n").encode()
reset(); r = upload({"b.csv": raw}); set_schema(dob=True)
t = tables()
print("tables:", [{k: x[k] for k in ("key", "rows", "cols", "headerRow")} for x in t])
for k, df in cw.S["frames"].items():
    print("frame", k, "rows:", len(df)); print(df.iloc[:, :3].to_string())
run()
print("Process ->", summary()["rows"], "| Final_Clean ids:", export_df("clean")["Client_ID"].tolist())
print("audit mentions of this table:", [l[:120] for l in export_raw("audit").decode().splitlines() if "b.csv" in l][:4])
