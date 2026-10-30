from _api import *
c = new_client()
rows = [("Ana","Lopez"),("Bo","Chen"),("Cy","Diaz"),("Di","Khan"),("Ed","Ortiz"),("Flo","Park"),("Gus","Reyes"),("Hal","Silva")]
body = "First Name,Last Name,Client ID,Street Address,City,State,Zip,Employer Address\n" + "\n".join(
    f'{f},{l},{3000+i},{10+i} Home St,Brooklyn,NY,11201,"{500+i} Work Ave, Manhattan, NY 10001"' for i, (f, l) in enumerate(rows)) + "\n"
upload(c, {"intake.csv": body.encode()})
ops = c.get("/api/ui?screen=prepare").json()["prepare"]["ops"]
print("tidy-up steps proposed on upload:", [o.get("desc") or o.get("label") for o in ops])
m = c.get("/api/ui?screen=map").json()["map"]["tables"][0]
print("matched columns:", {f["role"]: f["col"] for f in m["fields"] if f["col"]})
chk = c.get("/api/express/check").json()
print("express check: ok =", chk["ok"], "warnings =", chk["warnings"])
c.post("/api/express/run", json={})
for _ in range(400):
    if c.get("/api/run/status").json()["state"] != "running": break
    time.sleep(0.05)
res = cw.S["results"]
for rec in res["transformed"][:3]:
    print(f"client {rec['First_Name']} {rec['Last_Name']}: stored Address_1={rec['Address_1']!r} City={rec['City']!r} Zip={rec['Zip']!r}", "REVIEW "+str(rec['__errors__']) if rec["__errors__"] else "CLEAN")
