"""s33: the exact exception text behind the 500s of s05 and s22 B."""
from cwlib import *
from fastapi.testclient import TestClient
import pandas as pd, traceback
loud = TestClient(cw.api, base_url="http://127.0.0.1:8765", raise_server_exceptions=True)
rows = pd.DataFrame([["A1", "Ada", "Lee", "10 Oak St", "Brooklyn", "NY", "11201", "Housing"],
                     ["A2", "", "Wong", "4 Test St", "Brooklyn", "NY", "11201", "Housing"]],
                    columns=["Client_ID", "First_Name", "Last_Name", "Address", "City", "State", "Zip", "Program"])
reset(); upload({"one.csv": csv_bytes(rows)}); run()
try:
    loud.get("/api/ui?screen=review")
except Exception as e:
    print("review screen:", type(e).__name__, e)
H = ["Client_ID", "First_Name", "Last_Name", "DOB", "Address", "City", "State", "Zip", "Program"]
s = pd.DataFrame([["A1", "Ada", "Lee", "1980-01-01", "10 Oak St", "Brooklyn", "NY", "11201", "Housing"], ["", "TOTAL", "", "", "", "", "", "", ""]], columns=H)
reset(); upload({"s.csv": csv_bytes(s)}); set_schema(dob=True); run()
try:
    loud.get("/api/export/file?which=review")
except Exception as e:
    print("review export:", type(e).__name__, e)
