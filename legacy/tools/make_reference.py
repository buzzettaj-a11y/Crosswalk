"""
Generate a SAMPLE offline geocoding reference file (nyc_address_points.csv) so the
app can demonstrate matching + jitter without any external service.

It derives address points from the cleaned, master-mapped addresses found across
the real source files, assigns plausible per-borough coordinates, and deliberately
omits a small fraction so the 'could not be matched locally' path is also exercised.

This is a DEMO aid. In production, replace nyc_address_points.csv with the city's
real address-points export (any file exposing address / zip / lat / lon columns).
"""
import random
import pandas as pd

import app  # reuse the exact cleaning / transform logic

# Borough centroids (approx) -> coordinates are spread slightly around these.
CENTROIDS = {
    "New York": (40.7831, -73.9712),
    "Brooklyn": (40.6782, -73.9442),
    "Queens": (40.7282, -73.7949),
    "Bronx": (40.8448, -73.8648),
    "Staten Island": (40.5795, -74.1502),
}

# Mapping for each source file so we can compute master Address_1 / Zip / City.
MAPPINGS = {
    "system_1_clinic.csv": {
        "First_Name": "F_Name", "Middle_Initial": "M_Name", "Last_Name": "L_Name",
        "Client_ID": "EHR_ID", "Address_1": "Full_Address", "Address_2": "",
        "City": "", "State": "", "Zip": "ZipCode",
    },
    "system_2_portal.json": {
        "First_Name": "first_name", "Middle_Initial": "middle_initial",
        "Last_Name": "last_name", "Client_ID": "system_id",
        "Address_1": "location.street", "Address_2": "", "City": "location.city",
        "State": "", "Zip": "location.zip",
    },
    "system_3_legacy.xlsx": {
        "First_Name": "FirstName", "Middle_Initial": "MI", "Last_Name": "LastName",
        "Client_ID": "PatientNumber", "Address_1": "Addr1", "Address_2": "Addr2",
        "City": "City", "State": "State", "Zip": "ZipCode",
    },
    "system_4_state.xml": {
        "First_Name": "GivenName", "Middle_Initial": "", "Last_Name": "FamilyName",
        "Client_ID": "ID", "Address_1": "Street", "Address_2": "",
        "City": "City", "State": "State", "Zip": "Zip",
    },
    "system_5_partner.tsv": {
        "First_Name": "first", "Middle_Initial": "", "Last_Name": "last",
        "Client_ID": "uid", "Address_1": "address_line", "Address_2": "apt",
        "City": "city", "State": "st", "Zip": "zip",
    },
}


class _Up:
    """Tiny shim so we can reuse app.read_uploaded_file with a local path."""
    def __init__(self, path):
        self.name = path
        self._b = open(path, "rb").read()
    def getvalue(self):
        return self._b


def collect_points():
    """
    Build a realistic city-wide gazetteer from every source address.

    Pass 1 learns a ZIP -> borough mapping from the rows that DO carry a city.
    Pass 2 emits one point per unique (address, zip), tagging the borough from
    the row itself when known, else from the learned ZIP map, else a stable
    pseudo-random borough. (In production this file is the city's real
    address-points export; here it is synthetic demo data.)
    """
    audit = app.AuditLog()
    frames = {f: app.read_uploaded_file(_Up(f)) for f in MAPPINGS}

    # ---- Pass 1: learn ZIP -> borough -------------------------------------
    zip_city = {}  # zip -> Counter(city)
    from collections import Counter
    for fname, mapping in MAPPINGS.items():
        for idx, row in frames[fname].iterrows():
            rec = app.transform_row(dict(row), mapping, fname, int(idx), audit)
            if rec["City"] in CENTROIDS and rec["Zip"]:
                zip_city.setdefault(rec["Zip"], Counter())[rec["City"]] += 1

    def borough_for(zp, rng):
        if zp in zip_city:
            return zip_city[zp].most_common(1)[0][0]
        return rng.choice(list(CENTROIDS))

    # ---- Pass 2: emit one point per unique (address, zip) -----------------
    seen = {}
    rng = random.Random(7)
    for fname, mapping in MAPPINGS.items():
        for idx, row in frames[fname].iterrows():
            rec = app.transform_row(dict(row), mapping, fname, int(idx), audit)
            if not rec["Address_1"] or not rec["Zip"]:
                continue
            key = (app._norm_addr(rec["Address_1"]), rec["Zip"])
            if key in seen:
                continue
            city = rec["City"] if rec["City"] in CENTROIDS else borough_for(
                rec["Zip"], rng
            )
            seen[key] = (rec["Address_1"], rec["Zip"], city)
    return list(seen.values())


def main():
    rng = random.Random(42)
    pts = collect_points()
    rng.shuffle(pts)
    # Omit ~7% so some clean rows legitimately fail to geocode (demo coverage).
    keep = pts[: int(len(pts) * 0.93)]

    rows = []
    for addr, zp, city in keep:
        clat, clon = CENTROIDS[city]
        lat = clat + rng.uniform(-0.03, 0.03)
        lon = clon + rng.uniform(-0.03, 0.03)
        rows.append(
            {
                "address": addr,
                "zip": zp,
                "city": city,
                "latitude": round(lat, 6),
                "longitude": round(lon, 6),
            }
        )
    out = pd.DataFrame(rows)
    out.to_csv("nyc_address_points.csv", index=False)
    print(f"Wrote nyc_address_points.csv with {len(out):,} points "
          f"(from {len(pts):,} unique addresses; ~7% withheld).")


if __name__ == "__main__":
    main()
