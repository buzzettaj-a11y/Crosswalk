"""Builds wholecount/engine/geo/data/nyc_zips.csv from the source extracts in tools/data/ (P-STD-3). A dev tool that never ships.

    python tools/make_zip_table.py [--check]

Every ZIP comes from a cited public source, with its URL and retrieval date in the source column. The only ZIPs typed by hand are
the ones SPEC.md P-STD-3 names, cited to the spec, and only when no source lists them. When there is more than one source, the
script reports every ZIP one source has and another lacks, and the first source wins a borough disagreement.
"""
import argparse
import csv
import io
import pathlib
import sys

ROOT = pathlib.Path(__file__).resolve().parents[1]
DATA = ROOT / "tools" / "data"
OUT = ROOT / "wholecount" / "engine" / "geo" / "data" / "nyc_zips.csv"

BOROUGHS = {"manhattan": "New York", "new york": "New York", "brooklyn": "Brooklyn", "queens": "Queens", "bronx": "Bronx",
            "the bronx": "Bronx", "staten island": "Staten Island"}

# (file in tools/data, ZIP column, borough column, citation written into the source column)
SOURCES = [
    ("nyc_zips_uhf_copy.csv", "ZipCode", "Borough",
     "NYC Health ZIP table, copy at https://raw.githubusercontent.com/erikgregorywebb/nyc-housing/master/Data/nyc-zip-codes.csv "
     "retrieved 2026-10-31"),
]

# SPEC.md P-STD-3 names these. They're added only when no source lists them.
SPEC_ZIPS = {**{z: "Queens" for z in ("11004", "11005", *(str(n) for n in range(11690, 11698)))}, "10463": "Bronx"}
SPEC_ABSENT = ("11001", "11580", "07030", "12345", "99999", "00000")


def read_source(name, zip_col, borough_col):
    out = {}
    with (DATA / name).open(encoding="utf-8", newline="") as f:
        for row in csv.DictReader(f):
            z = row[zip_col].strip()
            b = BOROUGHS[row[borough_col].strip().lower()]
            if len(z) == 5 and z.isascii() and z.isdigit():
                out.setdefault(z, b)
    return out


def build():
    """(rows, report). rows are (zip, borough, source); report lists counts and disagreements."""
    table, report = {}, {"sources": [], "only_in": {}, "borough_disagreements": [], "from_spec": []}
    read = []
    for name, zc, bc, cite in SOURCES:
        if not (DATA / name).exists():
            continue
        zips = read_source(name, zc, bc)
        read.append((name, zips))
        report["sources"].append((name, len(zips)))
        for z, b in zips.items():
            if z in table:
                if table[z][0] != b:
                    report["borough_disagreements"].append(z)
                continue
            table[z] = (b, cite)
    for name, zips in read:
        others = set().union(*[set(z) for n, z in read if n != name]) if len(read) > 1 else set()
        if others:
            report["only_in"][name] = sorted(set(zips) - others)
    for z, b in SPEC_ZIPS.items():
        if z not in table:
            table[z] = (b, "SPEC.md P-STD-3")
            report["from_spec"].append(z)
    for z in SPEC_ABSENT:
        table.pop(z, None)
    return [(z, b, s) for z, (b, s) in sorted(table.items())], report


def render(rows):
    buf = io.StringIO(newline="")
    w = csv.writer(buf, lineterminator="\n")
    w.writerow(["zip", "borough", "source"])
    w.writerows(rows)
    return buf.getvalue()


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--check", action="store_true", help="compare with the committed table instead of writing it")
    args = ap.parse_args(argv)
    rows, report = build()
    text = render(rows)
    print(f"zips {len(rows)}")
    print(f"sources_read {len(report['sources'])}")
    print(f"from_spec {len(report['from_spec'])}")
    print(f"borough_disagreements {len(report['borough_disagreements'])}")
    print(f"only_in_one_source {sum(len(v) for v in report['only_in'].values())}")
    if args.check:
        same = OUT.exists() and OUT.read_text(encoding="utf-8") == text
        print(f"table_matches {int(same)}")
        return 0 if same else 1
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(text, encoding="utf-8")
    return 0


if __name__ == "__main__":
    sys.exit(main())
