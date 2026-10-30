"""Cross-checks between /api/ui numbers and the exports. Returns a list of failures."""
from cwlib import *


def snapshot(label=""):
    """Everything an observer could see, as a dict, plus a list of invariant failures."""
    fails = []
    s = summary()
    rw = s["rows"]
    exp_ui = ui("export")["export"]
    inputs = input_rows()

    n_crash = len(CRASHES)
    clean = export_df("clean")
    review = export_df("review")
    aside = export_df("aside")
    uc = export_df("unique_clients")
    bp = export_df("unique_by_program")

    if len(CRASHES) > n_crash:
        fails.append("EXPORT CRASH: " + "; ".join(f"{w}: {e}" for w, e in CRASHES[n_crash:]))
    if rw["clean"] + rw["review"] + rw["aside"] != rw["input"]:
        fails.append(f"BALANCE: {rw}")
    if rw["input"] != inputs:
        fails.append(f"INPUT: summary says {rw['input']} rows received, included frames hold {inputs}")
    if len(clean) != rw["clean"]:
        fails.append(f"CLEAN FILE: {len(clean)} rows vs screen clean {rw['clean']}")
    if len(review) != rw["review"]:
        fails.append(f"REVIEW FILE: {len(review)} rows vs screen review {rw['review']}")
    if len(aside) != rw["aside"]:
        fails.append(f"ASIDE FILE: {len(aside)} rows vs screen aside {rw['aside']}")
    tri = len(clean) + len(review) + len(aside)
    if tri != rw["input"]:
        fails.append(f"THREE FILES: {len(clean)}+{len(review)}+{len(aside)}={tri} vs input {rw['input']}")
    # each source row appears once overall
    def keyset(df):
        if not len(df):
            return []
        return [f"{a}||{b}" for a, b in zip(df["Source_File"], df["Source_Row"])]
    allk = keyset(clean) + keyset(review) + keyset(aside)
    if len(allk) != len(set(allk)):
        dup = len(allk) - len(set(allk))
        fails.append(f"ROW IN TWO FILES: {dup} source rows appear in more than one of clean/review/aside")
    if exp_ui.get("recon") and exp_ui["recon"] != {"input": rw["input"], "clean": rw["clean"],
                                                     "review": rw["review"], "aside": rw["aside"],
                                                     "kept": exp_ui["recon"]["kept"]}:
        fails.append(f"DOWNLOAD SCREEN recon {exp_ui['recon']} vs summary {rw}")
    g1 = summary()["goal1"]
    g2 = summary()["goal2"]
    ug1 = uc["Master_ID"].nunique() if len(uc) else 0
    ug2 = len(bp)
    if ug1 != g1["count"]:
        fails.append(f"GOAL1: screen {g1['count']} vs Unique_Clients rows {ug1}")
    if ug2 != g2["count"]:
        fails.append(f"GOAL2: screen {g2['count']} vs Unique_Clients_By_Program rows {ug2}")
    cover = sum(int(x) for x in uc["Source_Record_Count"]) if len(uc) else 0
    if cover != len(clean):
        fails.append(f"COUNTED ROWS: Unique_Clients covers {cover} source rows but Final_Clean_Mapped has {len(clean)}")
    return {"label": label, "rows": rw, "inputs": inputs, "g1": (g1["low"], g1["count"], g1["high"]),
            "g2": g2["count"], "files": (len(clean), len(review), len(aside)),
            "uc": ug1, "bp": ug2}, fails


def report(label):
    snap, fails = snapshot(label)
    print(f"[{label}] rows={snap['rows']} G1(low,settled,high)={snap['g1']} G2={snap['g2']} "
          f"files(clean,review,aside)={snap['files']} frames={snap['inputs']}")
    for f in fails:
        print("    FAIL ->", f)
    return snap, fails
