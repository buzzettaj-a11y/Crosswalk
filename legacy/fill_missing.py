"""
Filling in what a row is missing from what it already has.

A row with a street and a borough but no ZIP is not stuck: the reference data
says which ZIPs that street falls in. When there is exactly one answer it is
proposed, with the evidence, for a person to approve. When there are several,
or none, nothing is proposed, because a guess in a location field moves a
person into the wrong district.

This is the only kind of change the tool makes to a value: supporting location
data, derived from the row's own address, shown before it is applied, and
recorded when it is.
"""
from __future__ import annotations

import re
from collections import defaultdict

import app as engine

BOROUGHS = {"new york": "New York", "manhattan": "New York", "brooklyn": "Brooklyn",
            "queens": "Queens", "bronx": "Bronx", "the bronx": "Bronx",
            "staten island": "Staten Island"}


def _street_key(street):
    """The same form the reference data uses for a street."""
    return engine._norm_addr(street) if street else ""


def _borough(city):
    """The borough a city value names, if it names one."""
    c = engine.clean_cell(city).lower()
    if c in BOROUGHS:
        return BOROUGHS[c]
    alias = engine.normalize_city(city) if hasattr(engine, "normalize_city") else None
    if isinstance(alias, tuple):
        alias = alias[0]
    return alias if alias in BOROUGHS.values() else ""


class ZipFinder:
    """Street and borough to ZIP, built once from the reference index."""

    def __init__(self, geocode_index, gde=None):
        self.gde = gde
        self.by_street = defaultdict(set)      # (street key, borough) -> {zip}
        self.by_street_any = defaultdict(set)  # street key -> {zip}
        self.boroughs_of = defaultdict(set)    # street key -> {borough}
        if not geocode_index:
            return
        buckets = geocode_index[0] if isinstance(geocode_index, tuple) else geocode_index
        for zip5, rows in buckets.items():
            for entry in rows:
                street, boro = entry[0], entry[3] if len(entry) > 3 else ""
                # the reference stores house number and street; keep the street part
                parts = street.split(" ", 1)
                name = parts[1] if len(parts) > 1 and parts[0].replace("-", "").isdigit() else street
                self.by_street[(name, boro)].add(zip5)
                self.by_street_any[name].add(zip5)
                if boro:
                    self.boroughs_of[name].add(boro)

    def _gde_lookup(self, house, name, boro_name):
        """One Geosupport call, the way the engine makes it. Returns the ZIP
        it found, or None."""
        code = engine.BOROUGH_TO_GDE_CODE.get(boro_name)
        if not code or not house:
            return None
        try:
            res = self.gde.address(house_number=house,
                                   street_name=engine._strip_gde_ignore_words(name) or name,
                                   borough_code=code)
        except Exception:
            return None
        f = engine._extract_geosupport_fields(res)
        z = (f.get("zip") or "")[:5]
        return z if re.fullmatch(r"\d{5}", z) else None

    def propose(self, street, city):
        """
        (zip, evidence) when exactly one ZIP fits, else (None, reason).

        With a borough, the street is looked up in that borough. Without one,
        every borough is tried, and a ZIP is proposed only when exactly one
        borough knows the street; a street that exists in several is not
        guessed. Geosupport is asked first where it is active, since it
        answers for the exact house number; the reference data is used
        otherwise.
        """
        st = engine.clean_cell(street)
        if not st:
            return None, "no street to look up"
        boro = _borough(city)
        house, name = _split_house(st)
        boros = [boro] if boro else ["New York", "Brooklyn", "Queens", "Bronx",
                                     "Staten Island"]

        if self.gde is not None and house:
            hits = {}
            for b in boros:
                z = self._gde_lookup(house, name, b)
                if z:
                    hits[b] = z
            if len(hits) == 1:
                b, z = next(iter(hits.items()))
                return z, (f"Geosupport: {st} in {b} is ZIP {z}" if not boro
                           else f"Geosupport: {st}, {b}")
            if len(hits) > 1:
                return None, (f"{st} exists in {len(hits)} boroughs "
                              f"({', '.join(sorted(hits))}); a city is needed")
            if boro:
                return None, f"Geosupport does not know {st} in {boro}"
            # fall through to the reference data when Geosupport found nothing

        key = _street_key(st)
        parts = key.split(" ", 1)
        sname = parts[1] if len(parts) > 1 and parts[0].replace("-", "").isdigit() else key
        if boro:
            zips = self.by_street.get((sname, boro), set())
            if not zips:
                return None, f"the street is not in the reference data for {boro}"
            if len(zips) == 1:
                z = next(iter(zips))
                return z, f"{sname} in {boro} is only in ZIP {z}"
            return None, (f"{sname} runs through {len(zips)} ZIPs in {boro} "
                          f"({', '.join(sorted(zips)[:4])}); a house number is needed")
        found = self.boroughs_of.get(sname, set())
        if not found:
            return None, "the street is not in the reference data"
        if len(found) > 1:
            return None, (f"{sname} exists in {len(found)} boroughs "
                          f"({', '.join(sorted(found))}); a city is needed")
        b = next(iter(found))
        zips = self.by_street.get((sname, b), set())
        if len(zips) == 1:
            z = next(iter(zips))
            return z, f"{sname} is only in {b}, ZIP {z}"
        return None, (f"{sname} is only in {b} but runs through {len(zips)} ZIPs; "
                      "a house number is needed")

    def propose_city(self, street, zip5=""):
        """
        (borough, evidence) when the street points to exactly one borough,
        else (None, reason). Asked when the city as entered is not one the
        tool recognizes: a typo, an out-of-town name, or a neighborhood it
        does not know. The ZIP is tried first, then the street.
        """
        z = engine.clean_cell(zip5)
        if re.fullmatch(r"\d{5}", z):
            b = engine.borough_from_zip(z)
            if b:
                return b, f"ZIP {z} is in {b}"
        st = engine.clean_cell(street)
        if not st:
            return None, "no street to look up"
        if self.gde is not None:
            house, name = _split_house(st)
            hits = []
            for boro in ("Manhattan", "Brooklyn", "Queens", "Bronx", "Staten Island"):
                try:
                    r = self.gde.address(house, name, boro)
                    if r and (r.get("Latitude") or r.get("ZIP Code") or r.get("Zip Code")):
                        hits.append("New York" if boro == "Manhattan" else boro)
                except Exception:
                    continue
            if len(hits) == 1:
                return hits[0], f"Geosupport finds {st} only in {hits[0]}"
            if len(hits) > 1:
                return None, f"{st} exists in {len(hits)} boroughs ({', '.join(hits)})"
        key = _street_key(st)
        parts = key.split(" ", 1)
        name = parts[1] if len(parts) > 1 and parts[0].replace("-", "").isdigit() else key
        boros = self.boroughs_of.get(name, set())
        if len(boros) == 1:
            b = next(iter(boros))
            return b, f"{name} is only in {b}"
        if len(boros) > 1:
            return None, f"{name} exists in {len(boros)} boroughs ({', '.join(sorted(boros))})"
        return None, "the street is not in the reference data"


def _split_house(street):
    """A street split into its house number and the rest."""
    m = re.match(r"^\s*([\d\-]+[A-Za-z]?)\s+(.+)$", street)
    if m:
        return m.group(1), m.group(2)
    return "", street


def propose_for_row(rec, finder):
    """
    What the tool would fill on one row, field by field, with the reason.

    A blank is filled. A city that is present but not one the tool recognizes
    is offered a replacement, said as a replacement, because an unrecognized
    city places nobody anywhere; the value as entered stays in the audit log.
    Any other present value is never changed.
    """
    out = []
    errs = " ".join(rec.get("__errors__", [])).lower()
    city_unrecognized = ("unrecognized city" in errs
                         or "could not be determined" in errs)
    zip5 = engine.clean_cell(rec.get("Zip", ""))
    city = engine.clean_cell(rec.get("City", ""))
    state = engine.clean_cell(rec.get("State", ""))
    street = engine.clean_cell(rec.get("Address_1", ""))
    zip_ok = bool(re.fullmatch(r"\d{5}", zip5))

    if not zip_ok and street:
        z, why = finder.propose(street, city if _borough(city) else "")
        if z:
            out.append({"field": "Zip", "value": z, "why": why})
            if not city:
                b = engine.borough_from_zip(z)
                if b:
                    out.append({"field": "City", "value": b,
                                "why": f"ZIP {z} is in {b}"})
        else:
            out.append({"field": "Zip", "value": None, "why": why})
    elif not city and zip_ok:
        b = engine.borough_from_zip(zip5)
        if b:
            out.append({"field": "City", "value": b, "why": f"ZIP {zip5} is in {b}"})
    elif city_unrecognized and street:
        b, why = finder.propose_city(street, zip5)
        if b:
            out.append({"field": "City", "value": b,
                        "why": f"replace '{city}' with {b}: {why}"})
        else:
            out.append({"field": "City", "value": None,
                        "why": f"'{city}' is not recognized and {why}"})
    if not state and (zip_ok or _borough(city)):
        out.append({"field": "State", "value": "NY",
                    "why": "a New York City address"})
    return out
