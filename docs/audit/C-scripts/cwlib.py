"""
Shared harness for the Crosswalk counting and state audit (agent C).

Drives crosswalk_server.api through FastAPI's TestClient, the same way
tests/test_crosswalk_api.py does. Works on the COPY in .../src/agentC only.
"""
import io
import os
import sys
import time
import warnings
import hashlib

warnings.filterwarnings("ignore")

ROOT = "/tmp/claude-0/-home-claude/ec68250d-d5ac-549e-8d94-20759c381437/scratchpad/src/agentC"
os.chdir(ROOT)
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

import pandas as pd
from fastapi.testclient import TestClient
import crosswalk_server as cw

client = TestClient(cw.api, base_url="http://127.0.0.1:8765", raise_server_exceptions=False)

EXPORTS = {
    "clean": "Final_Clean_Mapped",
    "review": "Manual_Review_Needed",
    "aside": "Set_Aside_Records",
    "unique_clients": "Unique_Clients",
    "unique_by_program": "Unique_Clients_By_Program",
    "audit": "Secure_Audit_Log",
    "quality": "Data_Quality_Report",
}


def reset():
    client.post("/api/reset")


def upload(files):
    """files: {name: bytes}"""
    payload = [("files", (n, b)) for n, b in files.items()]
    r = client.post("/api/sources/upload", files=payload)
    assert r.status_code == 200, r.text
    return r.json()


def csv_bytes(df):
    return df.to_csv(index=False).encode()


def schema_with(dob=True, relax_id=True, program=True):
    schema = [dict(f) for f in cw.engine.DEFAULT_SCHEMA]
    for f in schema:
        if f["role"] == "Client_ID" and relax_id:
            f["required"] = False
    if dob:
        schema.append({"role": "custom", "label": "DOB", "dtype": "str",
                       "length": 20, "required": False})
    return schema


def set_schema(dob=True, relax_id=True):
    r = client.post("/api/schema", json={"schema": schema_with(dob, relax_id)})
    assert r.status_code == 200


def tables():
    return client.get("/api/ui?screen=sources").json()["sources"]["tables"]


def map_ui():
    return client.get("/api/ui?screen=map").json()["map"]


def wait_run(timeout=120):
    t0 = time.time()
    while time.time() - t0 < timeout:
        st = client.get("/api/run/status").json()
        if st["state"] != "running":
            return st
        time.sleep(0.05)
    raise TimeoutError("run did not finish")


def run(seed=1337, jitter=True):
    r = client.post("/api/run/start", json={"require_geocode": False,
                                            "jitter": jitter, "seed": seed})
    assert r.status_code == 200, r.text
    st = wait_run()
    assert st["state"] == "done", st
    return st


def express(despite=True):
    r = client.post("/api/express/run", json={"despite_warnings": despite})
    assert r.status_code == 200, r.text
    st = wait_run()
    assert st["state"] == "done", st
    return st


UI_ERRORS = []


def ui(screen):
    r = client.get(f"/api/ui?screen={screen}")
    if r.status_code != 200:
        UI_ERRORS.append((screen, r.status_code))
        return {"__status__": r.status_code, "chrome": {}, "review": {"groups": [], "tallies": {}},
                "summary": {}, "export": {}}
    return r.json()


def summary(fresh=False):
    """fresh=True drops the cached identity first (works around the stale-cache bug C-xx)."""
    if fresh:
        cw.S["identity"] = None
    return ui("summary")["summary"]


CRASHES = []


def export_raw(which):
    r = client.get(f"/api/export/file?which={which}")
    if r.status_code != 200:
        CRASHES.append((which, f"HTTP {r.status_code}: {r.text[:80]}"))
        return b""
    return r.content


def export_df(which):
    raw = export_raw(which)
    if not raw.strip():
        return pd.DataFrame()
    try:
        return pd.read_csv(io.BytesIO(raw), dtype=str, keep_default_na=False)
    except pd.errors.EmptyDataError:
        return pd.DataFrame()


def all_exports():
    out = {}
    for k in EXPORTS:
        out[k] = export_raw(k)
    return out


def digest(b):
    return hashlib.sha256(b).hexdigest()[:12]


def recon():
    s = summary()
    return s["rows"]


def balanced(label=""):
    rw = recon()
    ok = rw["clean"] + rw["review"] + rw["aside"] == rw["input"]
    return ok, rw


def input_rows():
    """Sum of rows in the INCLUDED raw frames: the true 'rows received'."""
    return sum(len(cw.S["frames"][k]) for k in cw._included_keys())


def groups():
    return ui("review")["review"]["groups"]


def queue(filter="all", per=200, **kw):
    q = "&".join(f"{k}={v}" for k, v in kw.items())
    return client.get(f"/api/queue?filter={filter}&per={per}&{q}").json()


def decide(gid, decision):
    return client.post("/api/review/group", json={"gid": gid, "decision": decision}).json()


def setup_standard(files, dob=True, relax_id=True, fast=False):
    """reset, upload, set schema, confirm default matching, run. Returns nothing."""
    reset()
    upload(files)
    if dob is not None:
        set_schema(dob=dob, relax_id=relax_id)
    if fast:
        express()
    else:
        run()


def counts_line(fresh=False):
    s = summary(fresh)
    g1, g2 = s["goal1"], s["goal2"]
    return (f"G1 settled={g1['count']} low={g1['low']} high={g1['high']} open={g1['open']} "
            f"| G2={g2['count']} no_program={g2['no_program']} | rows={s['rows']}")


def independent_goals(clean_df=None):
    """
    Independent Goal 1 / Goal 2 from the exports only: Unique_Clients (one row per
    master ID) and Unique_Clients_By_Program (one row per master+program).
    Returns (goal1, goal2, per_program dict).
    """
    uc = export_df("unique_clients")
    bp = export_df("unique_by_program")
    g1 = uc["Master_ID"].nunique() if len(uc) else 0
    g2 = len(bp.drop_duplicates(["Master_ID", "Program"])) if len(bp) else 0
    per = bp.groupby("Program")["Master_ID"].nunique().to_dict() if len(bp) else {}
    return g1, g2, per
