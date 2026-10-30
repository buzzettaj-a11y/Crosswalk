"""
Generate a SMALL synthetic district GeoJSON (nyc_districts.geojson) purely to
demonstrate the offline point-in-polygon district assignment. It draws coarse
rectangles around each borough centroid and tags them with placeholder Senate /
Assembly / Council numbers.

This is NOT real district geography. Replace it with the official NYC/NY State
district boundary GeoJSON for production (any FeatureCollection whose feature
properties contain 'senate', 'assembly', and 'council').
"""
import json

# (name, center_lat, center_lon, senate, assembly, council)
BOROUGHS = [
    ("New York", 40.7831, -73.9712, 27, 75, 3),
    ("Brooklyn", 40.6782, -73.9442, 20, 52, 33),
    ("Queens", 40.7282, -73.7949, 16, 30, 19),
    ("Bronx", 40.8448, -73.8648, 33, 77, 11),
    ("Staten Island", 40.5795, -74.1502, 24, 61, 49),
]

HALF = 0.05  # degrees; sized so the five borough boxes do not overlap in 2D


def box(lat, lon, half):
    return [[
        [lon - half, lat - half],
        [lon + half, lat - half],
        [lon + half, lat + half],
        [lon - half, lat + half],
        [lon - half, lat - half],
    ]]


def main():
    feats = []
    for name, lat, lon, sen, asm, cnc in BOROUGHS:
        feats.append({
            "type": "Feature",
            "properties": {
                "borough": name,
                "senate_district": sen,
                "assembly_district": asm,
                "council_district": cnc,
            },
            "geometry": {"type": "Polygon", "coordinates": box(lat, lon, HALF)},
        })
    gj = {"type": "FeatureCollection", "features": feats}
    with open("nyc_districts.geojson", "w", encoding="utf-8") as fh:
        json.dump(gj, fh)
    print(f"Wrote nyc_districts.geojson with {len(feats)} placeholder district areas.")


if __name__ == "__main__":
    main()
