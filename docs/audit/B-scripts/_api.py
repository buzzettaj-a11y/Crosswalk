"""Helper to drive the Crosswalk server in-process the way tests/test_crosswalk_api.py does."""
import os, sys, time, warnings, logging
warnings.filterwarnings("ignore"); logging.disable(logging.CRITICAL)
SRC = "/tmp/claude-0/-home-claude/ec68250d-d5ac-549e-8d94-20759c381437/scratchpad/src/agentB"
os.chdir(SRC); sys.path.insert(0, SRC)
from fastapi.testclient import TestClient
import crosswalk_server as cw

def new_client():
    c = TestClient(cw.api, base_url="http://127.0.0.1:8765")
    c.post("/api/reset")
    return c

def upload(c, files):
    """files: {name: bytes}"""
    r = c.post("/api/sources/upload", files=[("files", (n, b)) for n, b in files.items()])
    assert r.status_code == 200, r.text
    return r

def run_and_wait(c, require_geocode=False, jitter=True, seed=1337):
    r = c.post("/api/run/start", json={"require_geocode": require_geocode, "jitter": jitter, "seed": seed})
    assert r.status_code == 200 and r.json()["ok"], r.text
    for _ in range(600):
        st = c.get("/api/run/status").json()
        if st["state"] != "running":
            break
        time.sleep(0.05)
    return st

def relax_client_id(c):
    schema = [dict(f) for f in cw.engine.DEFAULT_SCHEMA]
    c.post("/api/schema", json={"schema": schema})
