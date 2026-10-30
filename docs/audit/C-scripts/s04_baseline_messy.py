"""s04: baseline on the messy fixture: groups, balance, exports vs screen."""
from invariants import *
import messy

setup_standard(messy.make(), dob=True)
snap, fails = report("after run")
print("groups:", [(g["id"], g["count"], g["status"]) for g in groups()])
print("review export head:")
rv = export_df("review")
print(rv[["Source_File", "Source_Row", "Resolution_Status", "Error_Reason"]].head(12).to_string() if len(rv) else "empty")
print("tallies:", ui("review")["review"]["tallies"])
print("cross-file note:", ui("review")["crossFile"])
print("express check:", {k: v for k, v in client.get("/api/express/check").json().items() if k in ("ok", "rows", "dupes_unreviewed", "dupes_rows")})
