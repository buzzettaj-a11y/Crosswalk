"""s05: the review screen 500s when any 'A required field is blank' row exists (re is never imported)."""
from cwlib import *
import pandas as pd
rows = pd.DataFrame([
    ["A1", "Ada", "Lee", "10 Oak St", "Brooklyn", "NY", "11201", "Housing"],
    ["A2", "", "Wong", "4 Test St", "Brooklyn", "NY", "11201", "Housing"],     # first name blank
], columns=["Client_ID", "First_Name", "Last_Name", "Address", "City", "State", "Zip", "Program"])
reset(); upload({"one.csv": csv_bytes(rows)}); run()
r = client.get("/api/ui?screen=review")
print("GET /api/ui?screen=review ->", r.status_code, r.text[:80])
r = client.get("/api/ui?screen=summary")
print("GET /api/ui?screen=summary ->", r.status_code)
print("summary rows:", r.json()["summary"]["rows"])
