"""Does a Client ID (or other value) reach the printable summary / quality report through Top_Issue?"""
import os, sys, re, html
HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, HERE)
import a_lib
work = sys.argv[1]
FIX = os.path.join(os.path.dirname(HERE), "A-fixtures")
cw, c = a_lib.boot(work)
c.post("/api/reset")
a_lib.upload(c, [os.path.join(FIX, "idconflict.csv")])
a_lib.relax_client_id(c)
a_lib.fix_mapping(c)
print("run", a_lib.run(c)["state"])
q = a_lib.download(c, "quality").decode()
print("--- Data_Quality_Report.csv"); print(q)
h = c.get("/api/summary").text
t = re.sub(r"<style.*?</style>", "", h, flags=re.S); t = html.unescape(re.sub(r"<[^>]+>", "\n", t))
print("--- printable summary lines mentioning the ID or names")
for l in t.splitlines():
    if re.search(r"SSN|123-45|Snodgrass|Grumble|Same Client ID", l): print(repr(l.strip()))
