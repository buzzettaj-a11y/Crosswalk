"""Claim: the audit trail lists 'every decision a reviewer took' by ID. Group decisions past 2,000 rows."""
import os, sys, re
HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, HERE)
import a_lib
work = sys.argv[1]
cw, c = a_lib.boot(work)
c.post("/api/reset")
rows = ["Client_ID,First_Name,Last_Name,Address_1,City,State,Zip,Program"]
for i in range(2100):
    rows.append(f"B{i:05d},Fn{i},Ln{i},{i+1} Test St,Brooklyn,NY,,Youth")      # every row is missing its ZIP
a_lib.upload_bytes(c, [("big.csv", ("\n".join(rows) + "\n").encode())])
a_lib.relax_client_id(c); a_lib.fix_mapping(c); a_lib.run(c)
rv = a_lib.review(c)
print("groups:", [(g["id"], g["count"]) for g in rv["groups"]])
g = rv["groups"][0]
print(c.post("/api/review/group", json={"gid": g["id"], "decision": "accept_all"}).json())
t = c.get("/api/audit/text").text
i = t.index("== Decisions by the reviewer")
sec = t[i:]
ids = re.findall(r"\bid (B\d{5})", sec)
print("rows accepted by the reviewer:", g["count"], "| rows listed by ID in the audit trail:", len(set(ids)))
print("last lines:", sec.strip().splitlines()[-2:])
