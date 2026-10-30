"""Helpers for the claims audit (agent A). Drives the Crosswalk server in process."""
import os
import sys
import time
import json
import warnings

warnings.filterwarnings("ignore")


def boot(workdir):
    """chdir into a copy of the app and return (module, TestClient)."""
    os.chdir(workdir)
    sys.path.insert(0, workdir)
    from fastapi.testclient import TestClient
    import crosswalk_server as cw
    client = TestClient(cw.api, base_url="http://127.0.0.1:8765")
    return cw, client


def upload(client, paths):
    files = []
    for p in paths:
        files.append(("files", (os.path.basename(p), open(p, "rb").read())))
    return client.post("/api/sources/upload", files=files)


def upload_bytes(client, named):
    files = [("files", (n, b)) for n, b in named]
    return client.post("/api/sources/upload", files=files)


def relax_client_id(client, extra_custom=None):
    """Advanced mode, Client_ID not required, optional extra custom fields."""
    import copy
    cw = sys.modules["crosswalk_server"]
    client.post("/api/mode", json={"mode": "Advanced"})
    schema = [dict(f) for f in cw.engine.DEFAULT_SCHEMA]
    for f in schema:
        if f["role"] == "Client_ID":
            f["required"] = False
    for c in (extra_custom or []):
        schema.append(c)
    client.post("/api/schema", json={"schema": schema})
    return schema


def fix_mapping(client):
    """Fill anything the guesser left unmatched, the way the project's own test does."""
    r = client.get("/api/ui?screen=map").json()["map"]
    for t in r["tables"]:
        if t["ready"]:
            continue
        for f in t["fields"]:
            if f["required"] and not f["col"]:
                want = f["role"].lower().replace("_", "")
                for c in t["cols"]:
                    cl = str(c).lower().replace("_", "")
                    if want in cl or cl in want:
                        client.post("/api/map", json={"table": t["key"], "field": f["role"], "column": c})
                        break
    return client.get("/api/ui?screen=map").json()["map"]


def run(client, seed=1337, jitter=True, require_geocode=False):
    resp = client.post("/api/run/start", json={"require_geocode": require_geocode,
                                                "jitter": jitter, "seed": seed})
    assert resp.status_code == 200, resp.text
    for _ in range(600):
        st = client.get("/api/run/status").json()
        if st["state"] != "running":
            break
        time.sleep(0.05)
    return st


def runstate(client):
    return client.get("/api/ui?screen=run").json()["runData"]


def review(client):
    return client.get("/api/ui?screen=review").json()["review"]


def summary(client):
    return client.get("/api/ui?screen=summary").json()["summary"]


def download(client, which):
    r = client.get(f"/api/export/file?which={which}")
    assert r.status_code == 200, (which, r.status_code, r.text[:200])
    return r.content


def decide_all_proposals(client, verdict="different"):
    while True:
        p = client.get("/api/identity/proposals?page=0&per=50").json()
        items = p.get("items", [])
        if not items:
            return
        for it in items:
            client.post("/api/identity/decide", json={"a": it["pair"][0], "b": it["pair"][1], "verdict": verdict})
