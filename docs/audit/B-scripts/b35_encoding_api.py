"""A Windows-1252 / Latin-1 CSV (what Excel's plain 'CSV' save produces) pushed through the fast path."""
from _api import *
c = new_client()
names = [("José","Núñez"),("Zoë","Müller"),("Ana","Peña"),("Renée","O'Brien"),("Bo","Chen"),("Cy","Diaz"),("Di","Khan"),("Ed","Ortiz")]
body = "First Name,Last Name,Client ID,Street Address,City,State,Zip\n" + "\n".join(
    f"{f},{l},{4000+i},{10+i} Main St,Brooklyn,NY,11201" for i, (f, l) in enumerate(names)) + "\n"
upload(c, {"intake_win1252.csv": body.encode("cp1252")})
chk = c.get("/api/express/check").json()
print("express check: ok =", chk["ok"], "| warnings =", chk["warnings"], "| blockers =", chk["blockers"])
c.post("/api/express/run", json={})
for _ in range(400):
    if c.get("/api/run/status").json()["state"] != "running": break
    time.sleep(0.05)
for (f, l), rec in zip(names, cw.S["results"]["transformed"]):
    st = "REVIEW " + str(rec["__errors__"]) if rec["__errors__"] else "CLEAN"
    print(f"typed {f} {l:8} -> stored First={rec['First_Name']!r} Last={rec['Last_Name']!r}  {st}")
