"""Builds the district files in wholecount/engine/geo/data/districts/ from NYC Planning boundary files (P-GEO-5). A dev tool
that never ships, and the app never imports it.

    python tools/make_district_files.py [--check]

It reads the files listed in SOURCES from tools/data/districts/, saved there by hand from NYC Planning's district boundary
downloads in GeoJSON with latitude and longitude ("clipped to shoreline" is fine). It never fetches anything. Each output file
keeps only the district number, renamed to senate_district, assembly_district or council_district, and the geometry, and it
records the source and the date the source was saved. Polygons keep their holes.
"""
import argparse
import json
import pathlib
import sys

ROOT = pathlib.Path(__file__).resolve().parents[1]
DATA = ROOT / "tools" / "data" / "districts"
OUT = ROOT / "wholecount" / "engine" / "geo" / "data" / "districts"

# (file in tools/data/districts, property holding the number in the source, our property, output file, citation)
SOURCES = [
    ("nysenate.geojson", "StSenDist", "senate_district", "senate.geojson",
     "NYC Planning, State Senate Districts (clipped to shoreline), GeoJSON. Saved on: fill in when saved."),
    ("nyassembly.geojson", "AssemDist", "assembly_district", "assembly.geojson",
     "NYC Planning, State Assembly Districts (clipped to shoreline), GeoJSON. Saved on: fill in when saved."),
    ("nycouncil.geojson", "CounDist", "council_district", "council.geojson",
     "NYC Planning, City Council Districts (clipped to shoreline), GeoJSON. Saved on: fill in when saved."),
]


def _number(props, key):
    for k, v in props.items():
        if k.lower() == key.lower() and v not in (None, ""):
            return int(float(v))
    raise KeyError(f"no {key} property")


def _check_lonlat(geometry):
    rings = geometry["coordinates"] if geometry["type"] == "Polygon" else [r for p in geometry["coordinates"] for r in p]
    for ring in rings:
        for x, y in ring:
            if not (-74.3 <= x <= -73.6 and 40.4 <= y <= 41.0):
                raise ValueError("coordinates are not longitude and latitude in New York City")


def build(src_name, src_key, our_key, citation):
    data = json.loads((DATA / src_name).read_text(encoding="utf-8"))
    feats = []
    for f in data["features"]:
        g = f["geometry"]
        if g["type"] not in ("Polygon", "MultiPolygon"):
            continue
        _check_lonlat(g)
        feats.append({"type": "Feature", "properties": {our_key: _number(f["properties"], src_key)}, "geometry": g})
    feats.sort(key=lambda f: f["properties"][our_key])
    return {"type": "FeatureCollection", "properties": {"source": citation, "built_by": "tools/make_district_files.py"},
            "features": feats}


def text_of(fc):
    return json.dumps(fc, separators=(",", ":"), sort_keys=True) + "\n"


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--check", action="store_true")
    args = ap.parse_args(argv)
    missing = [s[0] for s in SOURCES if not (DATA / s[0]).exists()]
    if missing:
        print(f"sources_missing {len(missing)}")
        return 1
    differing = 0
    for src_name, src_key, our_key, out_name, citation in SOURCES:
        text = text_of(build(src_name, src_key, our_key, citation))
        target = OUT / out_name
        if args.check:
            differing += not target.exists() or target.read_text(encoding="utf-8") != text
        else:
            OUT.mkdir(parents=True, exist_ok=True)
            target.write_text(text, encoding="utf-8")
    print(f"files_{'differing' if args.check else 'written'} {differing if args.check else len(SOURCES)}")
    return 1 if differing else 0


if __name__ == "__main__":
    sys.exit(main())
