from _api import *
c = new_client()
rows = ["Maria de la Cruz","Martin Van Buren","Ana Garcia Lopez","John Smith V","Dr. John Smith","John Smith, MD","Kim Soo Jin","Smith, John Q Public","Pat O'Brien","Garcia Lopez, Ana"]
body = "Client Name,Client ID,Street Address,City,State,Zip\n" + "\n".join(
    f'"{n}",{1000+i},{10+i} Main St,Brooklyn,NY,11201' for i, n in enumerate(rows)) + "\n"
upload(c, {"jammed_names.csv": body.encode()})
ops = c.get("/api/ui?screen=prepare").json()["prepare"]["ops"]
print("tidy-up steps proposed on upload:", [(o.get("type"), o.get("label") or o.get("desc"), o.get("removed")) for o in ops])
chk = c.get("/api/express/check").json()
print("express check: ok =", chk["ok"], "| warnings =", chk["warnings"], "| blockers =", chk["blockers"])
r = c.post("/api/express/run", json={})
print("express/run:", r.status_code)
for _ in range(400):
    if c.get("/api/run/status").json()["state"] != "running": break
    time.sleep(0.05)
res = cw.S["results"]
for src, rec in zip(rows, res["transformed"]):
    print(f"{src!r:26} -> first={rec['First_Name']!r:9} mi={rec['Middle_Initial']!r:4} last={rec['Last_Name']!r:14}", "REVIEW" if rec["__errors__"] else "CLEAN")
