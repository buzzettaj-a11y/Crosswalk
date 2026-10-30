"""
s24: one system reuses an identifier for two different people (siblings). The ID group goes to review,
the reviewer accepts the rows, and the identity engine merges them without any screen showing it.
"""
from invariants import *
import pandas as pd

H = ["Client_ID", "First_Name", "Last_Name", "DOB", "Address", "City", "State", "Zip", "Program"]
rows = [["77", "Ana", "Perez", "1990-05-06", "7 Elm St", "Brooklyn", "NY", "11201", "Housing"],
        ["77", "Beth", "Perez", "1994-09-09", "55 Oak Ave", "Brooklyn", "NY", "11201", "Housing"],
        ["78", "Carl", "Ng", "1970-01-01", "1 Pine St", "Brooklyn", "NY", "11201", "Housing"]]
reset(); upload({"one.csv": pd.DataFrame(rows, columns=H).to_csv(index=False).encode()}); set_schema(dob=True); run()
print("after Process        :", counts_line(True))
print("groups               :", [(g["id"], g["count"], g["title"]) for g in groups()])
decide("idconflict", "accept_all")
print("reviewer accepts     :", counts_line(True), "(truth: 3 people, Ana and Beth Perez are different)")
ident = cw.S["identity"]
print("auto_links           :", [(l["pair"], l["points"], l["evidence"]) for l in ident["auto_links"]])
print("open proposals       :", len(ident["proposals"]))
s = ui("summary")["summary"]
print("what the Results screen offers to decide:", s["goal1"]["open"], "pairs")
html = client.get("/api/ui?screen=summary")
import re
js = open(ROOT + "/ui/app.js").read()
print("UI code that lists auto-joined pairs (search 'auto_links' in app.js):", js.count("auto_links"), "hits")
r = client.post("/api/identity/decide", json={"a": list(ident["master_of"])[0], "b": list(ident["master_of"])[1], "verdict": "different"})
print("API-only escape hatch /api/identity/decide 'different':", r.json(), "->", counts_line(True))
