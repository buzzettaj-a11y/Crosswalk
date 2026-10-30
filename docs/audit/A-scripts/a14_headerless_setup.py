"""Claim: 'Saved set-ups and saved sessions hold no client data.' Try a file with no header row."""
import os, sys, json, glob
HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, HERE)
import a_lib
work = sys.argv[1]
FIX = os.path.join(os.path.dirname(HERE), "A-fixtures")
cw, c = a_lib.boot(work)
c.post("/api/reset")
print("upload", a_lib.upload(c, [os.path.join(FIX, "headerless.csv")]).status_code)
t = c.get("/api/ui?screen=sources").json()["sources"]["tables"][0]
print("table:", t["key"], "| header row chosen by the tool:", t.get("headerRow"), "| columns:", t.get("columns") or t.get("cols"))
print("save setup:", c.post("/api/setups/save", json={"name": "NoHeader", "note": ""}).json())
sid = cw.S.get("session_id")
for p in glob.glob(os.path.join(work, "setups", "*.json")) + glob.glob(os.path.join(work, "sessions", "*.json")):
    txt = open(p).read()
    hits = [w for w in ("Zebulon", "Quillfeather", "Marigold", "Thistlewood", "Evergreen", "C001", "11201") if w in txt]
    print(os.path.relpath(p, work), "-> client values found:", hits)
