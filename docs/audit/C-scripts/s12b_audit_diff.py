"""s12b: where the audit log differs between staged and fast path on the product sample files."""
from cwlib import *
import re, difflib, glob

def mask(b):
    s = b.decode("utf-8", "replace")
    s = re.sub(r"Generated \(UTC\): [0-9T:\-+]+", "Generated (UTC): <T>", s)
    s = re.sub(r"Recorded \d{4}-\d\d-\d\d \d\d:\d\d:\d\d", "Recorded <T>", s)
    return s
sample = {os.path.basename(p): open(p, "rb").read() for p in sorted(glob.glob(ROOT + "/sample_data/*"))}
reset(); upload(sample); set_schema(dob=True)
for scr in ("sources","schema","prepare","map"): ui(scr)
for t in map_ui()["tables"]: client.post("/api/map/confirm", json={"table": t["key"]})
ui("programs"); run(); a = mask(export_raw("audit")).splitlines()
reset(); upload(sample); set_schema(dob=True); express(); b = mask(export_raw("audit")).splitlines()
for l in list(difflib.unified_diff(a,b,"staged","fast",lineterm="",n=0))[:25]: print(l[:200])
