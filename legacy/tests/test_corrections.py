"""
Tests for the corrections re-import round trip. Run: python test_corrections.py
Exit code 0 means every check passed.
"""
import io
import os
import sys
import warnings

warnings.filterwarnings("ignore")
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if os.path.basename(os.path.dirname(os.path.abspath(__file__))) == "tests":
    os.chdir(ROOT)
    sys.path.insert(0, ROOT)

import pandas as pd
import app

results = []


def check(label, condition):
    results.append((label, bool(condition)))


SCHEMA = [dict(f) for f in app.DEFAULT_SCHEMA]
for f in SCHEMA:
    if f["role"] == "Client_ID":
        f["required"] = False

MAPPING = {"legacy.csv": {
    "Client_ID": "id", "First_Name": "fn", "Last_Name": "ln",
    "Address_1": "a1", "City": "city", "State": "st", "Zip": "zip",
}}


def fresh_frames():
    return {"legacy.csv": pd.DataFrame([
        # 0: clean
        {"id": "1", "fn": "Ada", "ln": "Sample", "a1": "209 Joralemon St",
         "city": "Brooklyn", "st": "NY", "zip": "11201"},
        # 1: bad city and ZIP, fixable
        {"id": "2", "fn": "Ben", "ln": "Fixture", "a1": "60 Centre St",
         "city": "Springfield", "st": "NY", "zip": "#N/A"},
        # 2: missing address, left broken on purpose
        {"id": "3", "fn": "Cara", "ln": "Mock", "a1": "",
         "city": "", "st": "", "zip": ""},
    ])}


def run(frames, meta=None):
    return app.run_pipeline(frames, MAPPING, require_geocode=False,
                            geocode_index=None, jitter_seed=1337,
                            schema=SCHEMA, corrections_meta=meta)


# ---- first run produces a review file with the corrections signature --------
res1 = run(fresh_frames())
check("first run: 1 clean, 2 review",
      len(res1["clean"]) == 1 and len(res1["review"]) == 2)
review_df = app.review_rows_to_dataframe(res1["review"])
check("review export carries the corrections signature",
      app.is_corrections_frame(review_df))

# ---- the caseworker fixes one row in the exported file ----------------------
fixed = review_df.copy()
mask = fixed["orig::id"] == "2"
fixed.loc[mask, "orig::city"] = "New York"
fixed.loc[mask, "orig::zip"] = "10007"

# round trip through CSV exactly as a person would save it from Excel
csv_text = fixed.to_csv(index=False)
reread = pd.read_csv(io.StringIO(csv_text), dtype=str, keep_default_na=False)
check("csv round trip keeps the signature", app.is_corrections_frame(reread))

pending, problems = app.parse_corrections_frame(reread, "fixes.csv")
check("both review rows parsed as pending patches", len(pending) == 2)
check("no parse problems", not problems)

# ---- apply and re-run -------------------------------------------------------
frames2 = fresh_frames()
changed, still_pending, apply_problems = app.apply_corrections(frames2, pending)
check("exactly one row changed", list(changed) == [("legacy.csv", 1)])
check("changed columns are city and zip",
      changed[("legacy.csv", 1)]["cols"] == {"city", "zip"})
check("untouched row produced no change entry", ("legacy.csv", 2) not in changed)
check("no apply problems", not apply_problems)

meta = {k: (v["from"], sorted(v["cols"])) for k, v in changed.items()}
res2 = run(frames2, meta)
check("after corrections: 2 clean, 1 review",
      len(res2["clean"]) == 2 and len(res2["review"]) == 1)
check("lossless after corrections",
      len(res2["clean"]) + len(res2["review"]) == 3)
fixed_rec = [r for r in res2["transformed"] if r["Client_ID"] == "2"][0]
check("fixed row is clean with the corrected borough",
      not fixed_rec["__errors__"] and fixed_rec["City"] == "New York"
      and fixed_rec["Zip"] == "10007")
check("still-broken row remains in review",
      res2["review"][0]["Client_ID"] == "3")

# ---- the audit note is present and PII-safe ---------------------------------
corr_flags = [f for f in fixed_rec["__flags__"]
              if f["scenario"] == "15 Corrections"]
check("corrections flag recorded on the fixed row", len(corr_flags) == 1)
msg = corr_flags[0]["message"] if corr_flags else ""
check("flag names the corrections file and columns",
      "fixes.csv" in msg and "city" in msg and "zip" in msg)
check("flag contains column names only, not values",
      "New York" not in msg and "10007" not in msg)
audit_df = res2["audit"].as_dataframe()
blob = audit_df.to_csv(index=False)
check("audit records the corrections event", "15 Corrections" in blob)
check("audit contains no client names", "Ben" not in blob and "Fixture" not in blob)

# ---- clean export is one combined file --------------------------------------
out = app.clean_rows_to_dataframe(res2["clean"], res2["schema"])
check("combined clean export holds both rows",
      set(out["Client_ID"]) == {"1", "2"})

# ---- corrections referencing a missing source are carried, then reported ----
ghost = [{"src": "ghost.csv", "row": 0, "values": {"city": "Bronx"},
          "from": "fixes.csv"}]
ch_g, still_g, prob_g = app.apply_corrections(fresh_frames(), ghost)
check("missing source stays pending, not applied",
      not ch_g and len(still_g) == 1 and not prob_g)

# ---- out-of-range row is skipped with a problem note ------------------------
oob = [{"src": "legacy.csv", "row": 99, "values": {"city": "Bronx"},
        "from": "fixes.csv"}]
ch_o, still_o, prob_o = app.apply_corrections(fresh_frames(), oob)
check("out-of-range row reported and skipped",
      not ch_o and not still_o and len(prob_o) == 1)

# ---- phase 2: a correction to a prep-derived column applies after prep ------
raw = {"jam.csv": pd.DataFrame([
    {"Name": "Ada Sample", "Full_Address": "209 Joralemon St Brooklyn NY 11201"},
])}
derived_fix = [{"src": "jam.csv", "row": 0,
                "values": {"Full_Address_street": "211 Joralemon St"},
                "from": "fixes.csv"}]
ch1, still1, _ = app.apply_corrections(raw, derived_fix)
check("derived column is carried past phase 1",
      not ch1 and len(still1) == 1)
prepared = {"jam.csv": app.apply_prep_ops(
    raw["jam.csv"], [{"type": "split_jammed", "column": "Full_Address"}])}
ch2, still2, _ = app.apply_corrections(prepared, still1)
check("derived column applies in phase 2 after prep",
      ("jam.csv", 0) in ch2 and not still2)
check("prepared frame holds the corrected street",
      prepared["jam.csv"].iloc[0]["Full_Address_street"] == "211 Joralemon St")

# ---- a normal data file is never mistaken for corrections -------------------
check("ordinary table is not a corrections file",
      not app.is_corrections_frame(fresh_frames()["legacy.csv"]))

for label, passed in results:
    print(f"  [{'PASS' if passed else 'FAIL'}] {label}")
ok = all(p for _, p in results)
print(f"CORRECTIONS TESTS: {'PASS' if ok else 'FAIL'} "
      f"({sum(1 for _, p in results if p)}/{len(results)})")
sys.exit(0 if ok else 1)
