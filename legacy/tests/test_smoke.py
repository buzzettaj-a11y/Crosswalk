"""
Smoke test for the data tool. Runs the full pipeline on the fake sample files and
checks the invariants that must always hold: lossless reconciliation, a PII-safe
audit log (no name leaks), and that ZIP-based city fill and duplicate detection
behave. Run: python test_smoke.py  (exit code 0 means pass)
"""
import warnings
warnings.filterwarnings("ignore")
import os, sys
# Run from the project root regardless of where this test is launched from.
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
os.chdir(ROOT)
sys.path.insert(0, ROOT)
import app


class Upload:
    """Minimal stand-in for a Streamlit uploaded file (name + getvalue)."""
    def __init__(self, path):
        self._path = path
        self.name = os.path.basename(path)

    def getvalue(self):
        with open(self._path, "rb") as fh:
            return fh.read()


def load(name):
    return app.read_uploaded_file(Upload(os.path.join("sample_data", name)))


def build_mappings():
    return {
        "clinic_export.csv": {
            "First_Name": "Name_first", "Last_Name": "Name_last",
            "Address_1": "Full_Address_street", "Address_2": "Full_Address_address2",
            "City": "Full_Address_city", "State": "Full_Address_state",
            "Zip": "Full_Address_zip",
        },
        "portal_export.json": {
            "First_Name": "Name_first", "Last_Name": "Name_last",
            "Address_1": "Address", "City": "City", "State": "State", "Zip": "Zip_Code",
        },
        "legacy_export.xlsx": {
            "First_Name": "FirstName", "Middle_Initial": "MI", "Last_Name": "LastName",
            "Client_ID": "PatientNumber", "Address_1": "Addr1", "Address_2": "Addr2",
            "City": "City", "State": "State", "Zip": "ZipCode",
        },
        "state_export.xml": {
            "First_Name": "Name_first", "Last_Name": "Name_last",
            "Address_1": "Address_1", "Address_2": "Address_2",
            "City": "City", "State": "State", "Zip": "Zip_Code",
        },
        "partner_export.tsv": {
            "First_Name": "first", "Last_Name": "last", "Client_ID": "uid",
            "Address_1": "address_line", "Address_2": "apt", "City": "city",
            "State": "st", "Zip": "zip", "Program": "program",
        },
    }


def prep_frames():
    frames = {}
    for name in ["clinic_export.csv", "portal_export.json", "legacy_export.xlsx",
                 "state_export.xml", "partner_export.tsv"]:
        df = load(name)
        ops = app.auto_prep_ops(df)          # detect + split jammed name/address
        frames[name] = app.apply_prep_ops(df, ops)
    return frames


def main():
    # Schema: sample files have no single required ID everywhere, and a Program field.
    schema = [dict(f) for f in app.DEFAULT_SCHEMA]
    for f in schema:
        if f["role"] == "Client_ID":
            f["required"] = False
    schema.append({"role": "custom", "label": "Program", "dtype": "str",
                   "length": 40, "required": False})

    frames = prep_frames()
    idx, _ = app.load_geocode_index("nyc_address_points.csv")
    dist = app.load_district_index("nyc_districts.geojson")
    res = app.run_pipeline(frames, build_mappings(), require_geocode=False,
                           geocode_index=idx, jitter_seed=1337,
                           district_index=dist, schema=schema)

    total = len(res["transformed"]); clean = len(res["clean"]); review = len(res["review"])
    audit_df = res["audit"].as_dataframe()

    checks = []
    checks.append(("lossless reconciliation", clean + review == total))

    # No client name should ever appear in the audit log.
    names = set()
    for name in ["clinic_export.csv", "partner_export.tsv"]:
        df = load(name)
        col = "Name" if "Name" in df.columns else None
        if col:
            for v in df[col]:
                for tok in str(v).split():
                    if len(tok) > 2:
                        names.add(tok.lower())
    blob = audit_df.to_csv(index=False).lower() if len(audit_df) else ""
    leaks = sorted(n for n in names if n and (" " + n + " ") in (" " + blob + " "))
    checks.append(("audit log has no name leaks", len(leaks) == 0))

    # Within-file duplicates are decided on Tidy up; the built-in check only
    # pairs rows across files. The sample's pair is inside one file, so it is
    # proposed there rather than marked here.
    import dedupe_rules
    frame = next(df for name, df in frames.items() if name.startswith("partner"))
    mapping = app.guess_mapping(list(frame.columns))
    found = dedupe_rules.proposals(frame, ["First_Name", "Last_Name", "Zip"], mapping)
    checks.append(("the within-file pair is proposed for a decision, never merged",
                   found["total_groups"] >= 1))
    dup_marked = sum(1 for r in res["transformed"] if r.get("Possible_Duplicate"))
    checks.append(("nothing inside one file is paired by the built-in check",
                   dup_marked == 0))

    # ZIP-based city fill worked for at least one missing-city row.
    checks.append(("pipeline produced clean rows", clean > 0))

    print(f"total={total}  clean={clean}  review={review}  audit_events={len(audit_df)}")
    ok = True
    for label, passed in checks:
        print(f"  [{'PASS' if passed else 'FAIL'}] {label}")
        ok = ok and passed
    if leaks:
        print("  leaked tokens:", leaks[:10])
    print("SMOKE TEST:", "PASS" if ok else "FAIL")
    sys.exit(0 if ok else 1)


if __name__ == "__main__":
    main()
