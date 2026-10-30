"""
s03: end to end: twins, Jr/Sr, swapped DOB, namesake auto-links through the server,
and what the screen shows about them. Truth: 10 distinct people, 12 rows.
"""
from cwlib import *
import fixtures as F

files = {"A.csv": F.csv(F.A_ROWS), "B.csv": F.csv(F.B_ROWS)}
setup_standard(files, dob=True)
print(counts_line())
print("truth: rows=12 -> people: P1(2 rows) + P2 + P3 + P4 + P5 + P6(2 rows) + P7 + P7b + P8 + P9 = 10 people")
s = summary()
print("Goal 1 reported:", s["goal1"])

uc = export_df("unique_clients")
pd.set_option("display.width", 250, "display.max_columns", 20)
print(uc[["Master_ID", "First_Name", "Last_Name", "Source_Record_Count", "Source_Rows"]].to_string())

ident = cw.S["identity"]
print("\nauto_links (not shown on the screen except as a count):")
for l in ident["auto_links"]:
    print("  ", l["pair"], l["points"], l["evidence"])
print("open proposals (shown on screen):")
for p in ident["proposals"]:
    print("  ", p["pair"], p["points"], p["reason"])
r = client.get("/api/identity/proposals").json()
print("API proposals payload keys:", list(r["items"][0].keys()) if r["items"] else None)
print("proposal payload carries points:", "points" in (r["items"][0] if r["items"] else {}))
