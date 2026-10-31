"""FakeGeoBackend: tests and wholecount.dev only. select_backend never returns it, and nothing else in the package imports it.

Gazetteer columns: house,street,zip,borough,lat,lon,senate,assembly,council,tract,grc. Matching is the exact address key.
"""
import csv
import pathlib

from wholecount.engine.addresskey import address_key, normalize_house, normalize_street
from wholecount.engine.geo import places
from wholecount.engine.geo.types import Districts, GeoResult, not_placed


class FakeGeoBackend:
    name = "fake"
    release = ""

    def __init__(self, gazetteer_csv):
        self._by_zip, self._by_borough = {}, {}
        with open(pathlib.Path(gazetteer_csv), newline="", encoding="utf-8") as f:
            for row in csv.DictReader(f):
                self._by_zip[address_key(row["house"], row["street"], row["zip"])] = row
                hs = f"{normalize_house(row['house'])}|{normalize_street(row['street'])}"
                self._by_borough[(hs, places.borough_of(row["borough"]))] = row

    def lookup(self, house_number, street, borough_or_zip):
        v = (borough_or_zip or "").strip()
        if v.isdigit() and len(v) == 5:
            row = self._by_zip.get(address_key(house_number, street, v))
        else:
            hs = f"{normalize_house(house_number)}|{normalize_street(street)}"
            row = self._by_borough.get((hs, places.borough_of(v)))
        if row is None:
            return not_placed("not_found", "fake")
        conf, reason = ("high", "matched_building") if row["grc"] == "00" else ("low", "matched_with_warning")
        return GeoResult(conf, reason, float(row["lat"]), float(row["lon"]), row["borough"], row["zip"],
                         Districts(row["senate"] or None, row["assembly"] or None, row["council"] or None), row["tract"] or None, "fake",
                         row["grc"])
