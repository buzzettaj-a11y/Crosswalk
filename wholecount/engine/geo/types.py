"""Placing addresses: the types every backend speaks (P-GEO-1, P-GEO-2, 7.4). Coordinates here are the TRUE point, in memory only."""
from dataclasses import dataclass
from typing import Literal, Protocol

# The engine returns a code; the copy registry holds one sentence for each (H11).
GEO_REASONS = {
    "matched_building": "high", "matched_with_warning": "low", "house_out_of_range": "low", "matched_street_only": "low",
    "not_found": "not_placed", "reference_ambiguous": "not_placed", "no_backend": "not_placed",
}
BOROUGH_CODES = {"New York": "MN", "Bronx": "BX", "Brooklyn": "BK", "Queens": "QN", "Staten Island": "SI"}


@dataclass(frozen=True)
class AddressQuery:
    house_number: str
    street: str
    borough_or_zip: str          # "11201" or "Brooklyn"


@dataclass(frozen=True)
class Districts:
    senate: str | None = None
    assembly: str | None = None
    council: str | None = None

    def any(self):
        return any((self.senate, self.assembly, self.council))


@dataclass(frozen=True)
class GeoResult:
    confidence: Literal["high", "low", "not_placed"]
    reason: str
    latitude: float | None = None
    longitude: float | None = None
    borough: str | None = None
    zip5: str | None = None
    districts: Districts | None = None
    census_tract: str | None = None
    source: Literal["geosupport", "reference", "reference_sample", "fake", "none"] = "none"
    grc: str | None = None

    def __post_init__(self):
        if self.reason not in GEO_REASONS or GEO_REASONS[self.reason] != self.confidence:
            raise ValueError(f"{self.reason} is not a {self.confidence} reason")

    @property
    def placed(self):
        return self.confidence in ("high", "low")

    @property
    def verified(self):
        """"Verified" appears only for High (P-GEO-2, B-35)."""
        return self.confidence == "high"


def not_placed(reason, source):
    return GeoResult("not_placed", reason, source=source)


@dataclass(frozen=True)
class LocationOutcome:
    kind: Literal["mapped", "not_mapped"]
    confidence: Literal["high", "low"] | None = None
    reason: Literal["no_fixed_address", "outside_nyc", "address_problem", "not_found", "no_geocoder"] | None = None
    filled: bool = False


class GeoBackend(Protocol):
    name: str
    release: str

    def lookup(self, house_number, street, borough_or_zip) -> GeoResult:
        ...
