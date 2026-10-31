"""Shared pieces for the M05 geo tests: fixture paths, backends, the test secret's HMAC, and placeable rows."""
import hashlib
import hmac

from tests.conftest import ROOT
from tests.support.secrets import OTHER_SECRET, TEST_SECRET
from tests.support.std import std
from wholecount.engine.geo.backend import GeoOptions
from wholecount.engine.geo.districts import DistrictIndex
from wholecount.engine.geo.fake import FakeGeoBackend
from wholecount.engine.geo.reference import ReferenceBackend

FIX = ROOT / "tests" / "fixtures" / "geo"
SAMPLE = ROOT / "wholecount" / "sample_data" / "sample_reference.csv"
NO_EXTRAS = GeoOptions()
TRACT = GeoOptions(frozenset({"census_tract"}))


def mac_for(secret=TEST_SECRET):
    return lambda message: hmac.new(secret, message, hashlib.sha256).digest()


MAC = mac_for(TEST_SECRET)
OTHER_MAC = mac_for(OTHER_SECRET)


def fake():
    return FakeGeoBackend(FIX / "fake_gazetteer.csv")


def ref_b17():
    return ReferenceBackend.from_path(FIX / "refdata_b17.csv")


def reference_of(rows, header="house_number,street,zip,borough,latitude,longitude"):
    return ReferenceBackend.from_text(header + "\n" + "\n".join(",".join(map(str, r)) for r in rows) + "\n")


def donut():
    return DistrictIndex.from_files([FIX / "districts_donut.geojson"])


def row(key, address, zip5, city="Brooklyn", **kw):
    """A counted row M04 marks to_place (when the address is whole)."""
    return std(record_key=key, Address_1=address, Zip=zip5, City=city, **kw)
