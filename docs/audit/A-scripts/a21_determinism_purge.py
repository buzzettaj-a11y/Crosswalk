"""Spot checks of two 'true' claims: same input and seed give the same files; sessions older than 7 days are purged."""
import os, sys, hashlib, time, json
HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, HERE)
import a_lib
work = sys.argv[1]
cw, c = a_lib.boot(work)
SAMPLES = [os.path.join(work, "sample_data", n) for n in
           ["clinic_export.csv", "portal_export.json", "legacy_export.xlsx", "state_export.xml", "partner_export.tsv"]]
def one_run():
    c.post("/api/reset"); a_lib.upload(c, SAMPLES); a_lib.relax_client_id(c); a_lib.fix_mapping(c); a_lib.run(c, seed=1337)
    out = {}
    for w in ("clean", "review", "unique_clients", "unique_by_program"):
        d = a_lib.download(c, w).decode()
        out[w] = hashlib.sha256(d.encode()).hexdigest()[:12]
    s = a_lib.summary(c); out["goals"] = (s["goal1"]["count"], s["goal2"]["count"])
    return out
a, b = one_run(), one_run()
print("run 1:", a); print("run 2:", b); print("identical:", a == b)
# retention
sdir = cw.sessions_store.SESSION_DIR
os.makedirs(sdir, exist_ok=True)
old = os.path.join(sdir, "s20200101-000000.json"); json.dump({"id": "s20200101-000000", "state": {}}, open(old, "w"))
t = time.time() - 8 * 86400; os.utime(old, (t, t))
fresh = os.path.join(sdir, "s20991231-000000.json"); json.dump({"id": "s20991231-000000", "state": {}}, open(fresh, "w"))
removed = cw.sessions_store.purge_expired()
print("8-day-old session removed:", not os.path.exists(old), "| fresh session kept:", os.path.exists(fresh), "| removed list:", removed)
