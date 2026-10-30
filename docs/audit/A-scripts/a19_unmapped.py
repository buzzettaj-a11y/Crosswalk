"""Claim: 'Unmapped columns never enter the output. A date of birth or SSN column left unmapped stays out of every export.'"""
import os, sys
HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, HERE)
import a_lib
work = sys.argv[1]
FIX = os.path.join(os.path.dirname(HERE), "A-fixtures")
cw, c = a_lib.boot(work)
c.post("/api/reset")
a_lib.upload(c, [os.path.join(FIX, "ssn_unmapped.csv")])
a_lib.relax_client_id(c); m = a_lib.fix_mapping(c)
t = m["tables"][0]
print("mapped columns:", {f["role"]: f["col"] for f in t["fields"] if f["col"]})
print("SSN / Phone mapped to anything?", any(f["col"] in ("SSN", "Phone") for f in t["fields"]))
a_lib.run(c)
for which in ("clean", "review", "aside", "unique_clients", "unique_by_program", "audit", "quality"):
    txt = a_lib.download(c, which).decode()
    hit = [v for v in ("078-05-1120", "219-09-9999", "457-55-5462", "555-0102") if v in txt]
    head = txt.splitlines()[0][:200] if which not in ("audit",) else ""
    print(f"{which:18s} contains unmapped SSN/phone values: {hit}")
    if hit: print("   header:", head)
