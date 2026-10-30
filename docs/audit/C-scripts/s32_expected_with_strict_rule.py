"""
s32: what the spec's rule gives on the s03 fixture. The engine copy in memory is given the spec's own test
(four strong facts, or same identifier in one system) in place of 'score >= 100'. Nothing on disk is changed.
"""
from cwlib import *
import fixtures as F
import identity

def spec_is_auto(a, b, pts, ev):
    if a.client_id and a.client_id == b.client_id and a.system == b.system:
        return True
    return {"date of birth matches exactly", "surname matches", "given name matches", "address matches"}.issubset(set(ev))

files = {"A.csv": F.csv(F.A_ROWS), "B.csv": F.csv(F.B_ROWS)}
setup_standard(files, dob=True)
print("as shipped          :", counts_line(True))
identity._is_auto = spec_is_auto
cw.S["identity"] = None
print("spec rule in memory :", counts_line(True))
print("   auto links:", [(l["pair"][0].split("||")[1], l["points"]) for l in cw.S["identity"]["auto_links"]])
print("   proposals :", [(p["pair"][0].split("||")[1], p["pair"][1].split("||")[1], p["points"], p["reason"]) for p in cw.S["identity"]["proposals"]])
