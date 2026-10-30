from cwlib import *
import pandas as pd
rows = [
 ["Quarterly client list"] + [""]*8,
 ["Generated 2026-01-01"] + [""]*8,
 ["Client_ID","First_Name","Last_Name","DOB","Address","City","State","Zip","Program"],
 ["F1","Ana","Perez","1990-05-06","7 Elm St","New York","NY","10013","Housing"],
 ["F2","Bo","Lee","1991-01-01","8 Elm St","New York","NY","10013","Housing"],
 ["F3","Cy","Kim","1992-02-02","9 Elm St","New York","NY","10013","Housing"],
]
import io, csv
buf = io.StringIO(); w = csv.writer(buf); [w.writerow(r) for r in rows]
reset(); upload({"T.csv": buf.getvalue().encode()})
t = tables()[0]; print({k: t[k] for k in ("key","rows","cols","kind","headerRow","headerWrong","headerWhy")})
print(list(cw.S["frames"][t["key"]].columns)[:4], len(cw.S["frames"][t["key"]]))
r = client.post("/api/map/header", json={"key": t["key"], "row": 3}).json(); print(r)
print(list(cw.S["frames"][t["key"]].columns)[:4], len(cw.S["frames"][t["key"]]))
