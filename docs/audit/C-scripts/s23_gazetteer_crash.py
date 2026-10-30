"""
s23: the shipped gazetteer + district file are present (the normal offline set-up). One address that
the gazetteer knows makes Process fail. No workaround is applied here.
"""
from invariants import *
import pandas as pd, time

ref = pd.read_csv(ROOT + "/nyc_address_points.csv", dtype=str, keep_default_na=False)
r0 = next(r for r in ref.itertuples() if r.address[:1].isdigit() and "apt" not in r.address.lower()
          and cw.engine.borough_from_zip(r.zip) == r.city)
H = ["Client_ID", "First_Name", "Last_Name", "DOB", "Address", "City", "State", "Zip", "Program"]
data = pd.DataFrame([["G1", "Ada", "Lee", "1980-01-01", r0.address, r0.city, "NY", r0.zip, "Housing"]], columns=H).to_csv(index=False).encode()
print("address taken from the shipped gazetteer:", r0.address, r0.city, r0.zip)
reset(); upload({"G.csv": data}); set_schema(dob=True)
r = client.post("/api/run/start", json={"require_geocode": False, "jitter": True, "seed": 1337})
t0 = time.time()
while time.time() - t0 < 60:
    st = client.get("/api/run/status").json()
    if st["state"] != "running":
        break
    time.sleep(0.05)
print("run status:", st)
print("type of the district index the server holds:", type(cw._load_reference()["dist"]).__name__)
