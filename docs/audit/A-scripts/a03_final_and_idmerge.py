"""Claims: 'this count is final' when nothing is open; same-ID rows are never merged on a guess."""
import os, sys, re
HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, HERE)
import a_lib
work = sys.argv[1]
FIX = os.path.join(os.path.dirname(HERE), "A-fixtures")
cw, c = a_lib.boot(work)
c.post("/api/reset")
a_lib.upload(c, [os.path.join(FIX, "household.csv")])
a_lib.relax_client_id(c)
a_lib.fix_mapping(c)
st = a_lib.run(c); print("run", st["state"])
rd = a_lib.runstate(c)["results"]; print("run counts", {k: rd[k] for k in ("input","clean","review")})
rv = a_lib.review(c)
print("review groups", [(g["id"], g["count"]) for g in rv["groups"]])
# the reviewer accepts the id-conflict group as entered, leaves the missing-zip row in review
for g in rv["groups"]:
    if g["id"] == "idconflict":
        print(c.post("/api/review/group", json={"gid": "idconflict", "decision": "accept_all"}).json())
s = a_lib.summary(c)
print("goal1", s["goal1"], "goal2", s["goal2"]["count"], "rows", s["rows"])
cl = a_lib.download(c, "unique_clients").decode()
print(cl)
html = c.get("/api/summary").text
print("printable says final:", "so these counts" in html and "are final" in html)
m = re.search(r'<p class="note">(Every proposed link[^<]*)</p>', html); print(m.group(1) if m else None)
