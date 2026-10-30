"""Shared setup for the audit B scripts. Run from anywhere; the engine copy is agentB."""
import os, sys, warnings, logging
warnings.filterwarnings("ignore")
logging.disable(logging.CRITICAL)
SRC = "/tmp/claude-0/-home-claude/ec68250d-d5ac-549e-8d94-20759c381437/scratchpad/src/agentB"
os.chdir(SRC)
sys.path.insert(0, SRC)
import app as engine   # noqa: E402
import pandas as pd    # noqa: E402

MAPPING = {"First_Name": "First", "Last_Name": "Last", "Client_ID": "ID",
           "Address_1": "Addr", "Address_2": "Addr2", "City": "City",
           "State": "State", "Zip": "Zip"}

def one_row(**kw):
    """Run one row through transform_row with the default schema and return the record."""
    base = {"First": "Ana", "Last": "Lopez", "ID": "A1", "Addr": "10 Main St",
            "Addr2": "", "City": "Brooklyn", "State": "NY", "Zip": "11201"}
    base.update(kw)
    audit = engine.AuditLog()
    return engine.transform_row(base, MAPPING, "t.csv", 0, audit)

def status(rec):
    """clean or REVIEW for a transform_row record (no geocoding)."""
    return "REVIEW: " + "; ".join(rec["__errors__"]) if rec["__errors__"] else "CLEAN"

def pipeline(rows, require_geocode=False, index=None, districts=None, seed=1337, jitter=True,
             schema=None, mapping=None):
    """Run run_pipeline on a list of dict rows as one file; returns the result dict."""
    df = pd.DataFrame(rows).astype(str)
    df = engine.clean_dataframe(df)
    res = engine.run_pipeline({"t.csv": df}, {"t.csv": mapping or MAPPING}, require_geocode,
                              index, seed, districts, None, schema, None, jitter)
    return res


def final(**kw):
    """Run ONE row through the full run_pipeline (no geocoder) and return (status_text, record)."""
    base = {"First": "Ana", "Last": "Lopez", "ID": "A1", "Addr": "10 Main St",
            "Addr2": "", "City": "Brooklyn", "State": "NY", "Zip": "11201"}
    base.update(kw)
    res = pipeline([base])
    rec = res["transformed"][0]
    st = ("REVIEW: " + "; ".join(rec["__errors__"])) if rec["__errors__"] else "CLEAN"
    return st, rec

def show(label, st, rec):
    print(f"{label:38} -> {st}")
    print(f"{'':38}    First={rec['First_Name']!r} Last={rec['Last_Name']!r} ID={rec['Client_ID']!r} "
          f"A1={rec['Address_1']!r} A2={rec['Address_2']!r} City={rec['City']!r} St={rec['State']!r} Zip={rec['Zip']!r}")
