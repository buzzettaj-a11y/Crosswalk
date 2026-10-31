"""The privacy offset for Map_Points (P-GEO-7, fix plan 4.4).

A building's point moves 150 to 250 feet in a direction taken from HMAC-SHA256(install secret, "offset|" + address key). The
engine gets `mac`, a callable bytes -> bytes, and never sees the secret. Nothing here is random, so one row never moves another.
"""
import math
from dataclasses import dataclass

from wholecount.settings import loader

FEET_TO_METERS = 0.3048
METERS_PER_DEGREE = 111_320


def stable_offset(mac, address_key, min_ft=150.0, max_ft=250.0):
    """(feet, bearing in radians) for one address key."""
    d = mac(b"offset|" + address_key.encode("utf-8"))
    u1 = int.from_bytes(d[:8], "big") / 2**64
    u2 = int.from_bytes(d[8:16], "big") / 2**64
    return min_ft + (max_ft - min_ft) * u1, 2 * math.pi * u2


def move_point(lat, lon, dist_ft, bearing):
    m = dist_ft * FEET_TO_METERS
    return (lat + m * math.cos(bearing) / METERS_PER_DEGREE,
            lon + m * math.sin(bearing) / (METERS_PER_DEGREE * math.cos(math.radians(lat))))


@dataclass(frozen=True)
class PrivacyOffset:
    mac: object
    min_ft: float = 150.0
    max_ft: float = 250.0

    @classmethod
    def from_settings(cls, mac):
        s = loader.load("geo")
        return cls(mac, float(s["offset_min_ft"]), float(s["offset_max_ft"]))

    def apply(self, address_key, lat, lon):
        """The moved point for one building. Every client at that building gets this same point (OFF-2)."""
        dist, bearing = stable_offset(self.mac, address_key, self.min_ft, self.max_ft)
        return move_point(lat, lon, dist, bearing)


def haversine_ft(lat1, lon1, lat2, lon2):
    r = 6_371_008.8
    p1, p2 = math.radians(lat1), math.radians(lat2)
    dp, dl = p2 - p1, math.radians(lon2 - lon1)
    a = math.sin(dp / 2) ** 2 + math.cos(p1) * math.cos(p2) * math.sin(dl / 2) ** 2
    return 2 * r * math.asin(math.sqrt(a)) / FEET_TO_METERS
