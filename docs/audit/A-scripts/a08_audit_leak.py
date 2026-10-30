"""Do raw names/addresses reach the 'IDs only' audit log when a column holds the wrong kind of value?"""
import os, sys
HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, HERE)
import a_lib
work = sys.argv[1]
FIX = os.path.join(os.path.dirname(HERE), "A-fixtures")
cw, c = a_lib.boot(work)
c.post("/api/reset")
print("upload", a_lib.upload(c, [os.path.join(FIX, "misplaced.csv")]).status_code)
a_lib.relax_client_id(c)
m = a_lib.fix_mapping(c)
print("blocked", m["blocked"])
st = a_lib.run(c); print("run", st["state"])
txt = c.get("/api/audit/text").text
print(txt)
