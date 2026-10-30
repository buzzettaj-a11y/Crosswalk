"""
s12: POST /api/express/run vs stage by stage (visiting each screen the way the UI does), same data.
Compares counts and every export byte for byte (audit/quality timestamps masked).
"""
from invariants import *
import re, difflib, sys, io, glob
import pandas as pd
import messy


def mask(b):
    s = b.decode("utf-8", "replace")
    s = re.sub(r"Generated \(UTC\): [0-9T:\-+]+", "Generated (UTC): <T>", s)
    s = re.sub(r"Recorded \d{4}-\d\d-\d\d \d\d:\d\d:\d\d", "Recorded <T>", s)
    return s.encode()


def staged(files, visit_programs=True):
    reset(); upload(files); set_schema(dob=True)
    for scr in ("sources", "schema", "prepare", "map"):
        ui(scr)
    for t in map_ui()["tables"]:
        client.post("/api/map/confirm", json={"table": t["key"]})
    if visit_programs:
        ui("programs")
    run()
    ui("review");


def fast(files):
    reset(); upload(files); set_schema(dob=True)
    express()


def dump():
    out = {k: mask(export_raw(k)) for k in EXPORTS}
    return out


def compare(label, files, visit_programs):
    staged(files, visit_programs)
    s1 = counts_line(True); d1 = dump()
    fast(files)
    s2 = counts_line(True); d2 = dump()
    print(f"\n== {label}")
    print("   staged:", s1)
    print("   fast  :", s2)
    for k in EXPORTS:
        same = d1[k] == d2[k]
        print(f"   {EXPORTS[k]:<28} identical={same}")
        if not same and k in ("unique_by_program", "unique_clients", "clean"):
            a = d1[k].decode().splitlines(); b = d2[k].decode().splitlines()
            for line in list(difflib.unified_diff(a, b, "staged", "fast", lineterm="", n=0))[:8]:
                print("      ", line[:170])


# 1. sample data from the product
sample = {os.path.basename(p): open(p, "rb").read() for p in sorted(glob.glob(ROOT + "/sample_data/*"))}
compare("product sample files (Programs screen visited in the staged run)", sample, True)

# 2. the program-spelling fixture
H = ["Client_ID", "First_Name", "Last_Name", "DOB", "Address", "City", "State", "Zip", "Program"]
A = pd.DataFrame([["A1", "Ana", "Perez", "1990-05-06", "7 Elm St", "New York", "NY", "10013", "Workforce Development"],
                  ["A2", "Bo", "Lee", "1991-01-01", "8 Elm St", "New York", "NY", "10013", "Youth"]], columns=H)
B = pd.DataFrame([["B1", "Ana", "Perez", "1990-05-06", "7 Elm St", "New York", "NY", "10013", "Workforce Dev."],
                  ["B2", "Bo", "Lee", "1991-01-01", "8 Elm St", "New York", "NY", "10013", "youth"]], columns=H)
compare("program spellings", {"A.csv": A.to_csv(index=False).encode(), "B.csv": B.to_csv(index=False).encode()}, True)
