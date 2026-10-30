from _api import *
c = new_client()
workers = ["Jane Doe", "Raj Patel", "Mei Wong", "Tom Hill"]
rows = [("Ana","Lopez"),("Bo","Chen"),("Cy","Diaz"),("Di","Khan"),("Ed","Ortiz"),("Flo","Park"),("Gus","Reyes"),("Hal","Silva")]
body = "Caseworker Name,First Name,Last Name,Client ID,Street Address,City,State,Zip\n" + "\n".join(
    f'{workers[i%4]},{f},{l},{2000+i},{10+i} Main St,Brooklyn,NY,11201' for i, (f, l) in enumerate(rows)) + "\n"
upload(c, {"cases.csv": body.encode()})
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
for (f, l), rec in zip(rows, res["transformed"]):
    print(f"client {f} {l:7} -> stored First={rec['First_Name']!r} Last={rec['Last_Name']!r}", "REVIEW" if rec["__errors__"] else "CLEAN")
