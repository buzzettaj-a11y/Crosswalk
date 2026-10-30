"""
================================================================================
 Crosswalk
================================================================================
A 100% offline, air-gapped Streamlit application that merges messy client data
from several disparate EHR exports (.csv / .xlsx / .json / .xml / .tsv) into a
single clean "standard" dataset, validates every field, geocodes addresses
against a LOCAL reference file (no external APIs), applies a privacy jitter to
the coordinates, and presents a review dashboard before any export.

--------------------------------------------------------------------------------
 PRIVACY / SECURITY MODEL  (read before modifying)
--------------------------------------------------------------------------------
* No outbound HTTP/API calls anywhere in this file. Geocoding is performed by
  matching against a local CSV (`nyc_address_points.csv`). The only disk READ is
  that reference file. Nothing is written to disk: uploads are parsed from RAM
  (BytesIO) and all downloads are streamed from in-memory strings.
* The exported audit log (`Secure_Audit_Log.txt`) references ONLY system IDs.
  It never contains a client name or a full street address. Boroughs and ZIP
  fragments may appear because they are low-sensitivity and needed to explain a
  transformation, but personally-identifying combinations are excluded.

--------------------------------------------------------------------------------
 MASTER SCHEMA (the single target every file is transformed into)
--------------------------------------------------------------------------------
    First_Name      str            required
    Middle_Initial  str, len 1     optional/nullable, uppercased
    Last_Name       str            required
    Client_ID   str/int        required, globally unique across the merge
    Address_1       str            required (may legitimately contain Apt/Suite)
    Address_2       str            optional/nullable
    City            str            required, one of the 5 NYC boroughs
    State           str            must be "NY"
    Zip             str            required, 5 digits

--------------------------------------------------------------------------------
 LOSSLESS GUARANTEE
--------------------------------------------------------------------------------
Every input row ends up in exactly one of two output buckets:
    1. Final_Clean_Mapped.csv     -> validated, geocoded, jittered, perfect
    2. Manual_Review_Needed.csv   -> anything imperfect, with its ORIGINAL data
                                     preserved plus a human-readable reason
No row is ever silently dropped. (clean count + error count == input count).
================================================================================
"""

from __future__ import annotations

import io
import csv
import json
import math
import os
import random
import re
import unicodedata
from collections import defaultdict
from datetime import datetime, timedelta, timezone

import numpy as np
import pandas as pd
import streamlit as st

# lxml is used for robust XML parsing (per requirements).
import lxml.etree as ET

# Table detection finds the separate tables inside one sheet, so two datasets
# sitting side by side are never merged into one corrupted table. Optional: if
# the module is absent, the app falls back to reading each file as one table.
try:
    import table_detect
except Exception:      # pragma: no cover
    table_detect = None

# Hardened XML parser for untrusted-by-default input. Even though exports come
# from internal systems, we disable the features that enable XML attacks as
# defense in depth:
#   resolve_entities=False -> blocks entity-expansion ("billion laughs")
#   no_network=True        -> blocks external-entity (XXE) network fetches
#   load_dtd / dtd_validation=False -> ignore any DTD the document declares
#   huge_tree=False        -> keep lxml's built-in limits on oversized trees
_SAFE_XML_PARSER = ET.XMLParser(
    resolve_entities=False,
    no_network=True,
    load_dtd=False,
    dtd_validation=False,
    huge_tree=False,
)

# ------------------------------------------------------------------------------
# Fuzzy-matching dependency.
# `thefuzz` is preferred (per requirements). If it is not installed in the host
# environment we transparently fall back to the standard-library difflib so the
# app still runs offline without an extra install.
# ------------------------------------------------------------------------------
try:
    from thefuzz import fuzz as _fuzz

    def _ratio(a: str, b: str) -> int:
        """Token-sort ratio 0..100 (order-insensitive)."""
        return _fuzz.token_sort_ratio(a, b)

    FUZZ_BACKEND = "thefuzz"
except Exception:  # pragma: no cover - environment dependent
    import difflib

    def _ratio(a: str, b: str) -> int:
        return int(round(difflib.SequenceMatcher(None, a, b).ratio() * 100))

    FUZZ_BACKEND = "difflib (thefuzz not installed)"


# ==============================================================================
#  SECTION 1.  CONSTANTS & SCHEMA DEFINITION
# ==============================================================================

# The canonical master columns, in order. These are the internal ROLE keys that
# drive the NYC-specific logic (geocoding, borough normalization, ZIP rules, MI
# reduction). The user-facing schema can rename/retype/resize these and add extra
# fields, but the role identity below is what the engine reasons about.
MASTER_COLUMNS = [
    "First_Name",
    "Middle_Initial",
    "Last_Name",
    "Client_ID",
    "Address_1",
    "Address_2",
    "City",
    "State",
    "Zip",
]

# Which master fields are mandatory for a row to be considered "perfect".
REQUIRED_FIELDS = ["First_Name", "Last_Name", "Client_ID", "Address_1", "City", "Zip"]

# ---------------------------------------------------------------------------
# Configurable output schema.
# Each field has a ROLE (internal semantic key, or "custom" for a passthrough
# field the user adds), a LABEL (the output column header, user-editable), a
# DTYPE ("str" or "int"), a LENGTH (maximum length; 0 means unlimited), and a
# REQUIRED flag. The default reproduces the standard schema exactly, so with
# no changes the pipeline behaves identically to before.
# ---------------------------------------------------------------------------
DEFAULT_SCHEMA = [
    {"role": "First_Name",    "label": "First_Name",     "dtype": "str", "length": 60,  "required": True},
    {"role": "Middle_Initial", "label": "Middle_Initial", "dtype": "str", "length": 1,   "required": False},
    {"role": "Last_Name",     "label": "Last_Name",      "dtype": "str", "length": 60,  "required": True},
    {"role": "Client_ID", "label": "Client_ID",  "dtype": "str", "length": 30,  "required": True},
    {"role": "Address_1",     "label": "Address_1",      "dtype": "str", "length": 150, "required": True},
    {"role": "Address_2",     "label": "Address_2",      "dtype": "str", "length": 150, "required": False},
    {"role": "City",          "label": "City",           "dtype": "str", "length": 50,  "required": True},
    {"role": "State",         "label": "State",          "dtype": "str", "length": 2,   "required": True},
    {"role": "Zip",           "label": "Zip",            "dtype": "str", "length": 5,   "required": True},
    # The project counts people per program, so a program column is part
    # of the standard shape rather than something to remember to add. It
    # is not required, because plenty of sources do not record one.
    {"role": "custom",        "label": "Program",        "dtype": "str", "length": 80,  "required": False},
]

# Roles whose presence is enforced by a simple "is it empty" check. City, ZIP,
# Address_1 and State have their own richer role logic and are handled there.
SIMPLE_PRESENCE_ROLES = {"First_Name", "Last_Name", "Client_ID"}

# Enrichment columns the pipeline adds to every clean row (offered as optional
# export columns on top of the schema fields).
ENRICHMENT_COLUMNS = [
    "Latitude", "Longitude", "Verification_Status", "Geocode_Confidence",
    "Possible_Duplicate", "Duplicate_In_File",
    "Senate_District", "Assembly_District", "Council_District",
    "Source_File", "Source_Row",
]


def get_schema():
    """Return the active schema from session state, defaulting to the standard schema."""
    try:
        import streamlit as _st
        return _st.session_state.get("schema", DEFAULT_SCHEMA)
    except Exception:
        return DEFAULT_SCHEMA


def schema_required_roles(schema):
    """Roles/labels that are marked required in the schema."""
    return [f for f in schema if f.get("required")]


def schema_known_fields(schema):
    """Schema fields whose role is one of the built-in master roles."""
    return [f for f in schema if f["role"] in MASTER_COLUMNS]


def schema_custom_fields(schema):
    """Schema fields the user added (role == 'custom')."""
    return [f for f in schema if f["role"] == "custom"]

# Master fields the user must map a source column to (State can be defaulted,
# Address_2 / Middle_Initial are optional, City may be derived from a jammed
# address). The mapping UI enforces that at least these are mapped OR derivable.
MIN_MAPPED_FIELDS = ["First_Name", "Last_Name", "Client_ID", "Address_1", "Zip"]

# The five valid New York City boroughs (the only acceptable City values).
CANONICAL_CITIES = ["New York", "Brooklyn", "Queens", "Bronx", "Staten Island"]

# Hand-built alias table for the common abbreviations / misspellings we observed
# across the source systems. Keys are lowercased, value is the canonical form.
CITY_ALIASES = {
    # New York / Manhattan
    "new york": "New York",
    "newyork": "New York",
    "newyrk": "New York",
    "new york city": "New York",
    "nyc": "New York",
    "ny": "New York",
    "manhattan": "New York",
    "mahattan": "New York",
    "new yrk": "New York",
    # Brooklyn
    "brooklyn": "Brooklyn",
    "broklyn": "Brooklyn",
    "bklyn": "Brooklyn",
    "bk": "Brooklyn",
    "brooklyn": "Brooklyn",
    # Queens
    "queens": "Queens",
    "qns": "Queens",
    "queen": "Queens",
    # Bronx
    "bronx": "Bronx",
    "the bronx": "Bronx",
    "bx": "Bronx",
    # Staten Island
    "staten island": "Staten Island",
    "si": "Staten Island",
    "s.i.": "Staten Island",
    "staten is": "Staten Island",
    "statenisland": "Staten Island",
}

# Values (case-insensitive) that should be treated as "empty" wherever they
# appear in a source cell. These are the junk sentinels seen in the exports.
NULL_SENTINELS = {"", "null", "none", "n/a", "na", "#n/a", "nan", "nil", "(null)"}

# Name of the local geocoding reference file expected in the app directory.
GEOCODE_FILE = "nyc_address_points.csv"

# Privacy jitter range, in feet.
JITTER_MIN_FT = 150.0
JITTER_MAX_FT = 250.0

# Fuzzy thresholds.
CITY_FUZZ_THRESHOLD = 80      # below this, a city is considered unresolvable
ADDRESS_FUZZ_THRESHOLD = 88   # below this, a fuzzy address match is rejected

# Feet per degree of latitude (approximately constant on Earth's surface).
FEET_PER_DEG_LAT = 364000.0

# Local district-boundary file (GeoJSON). Optional; when present the app assigns
# Senate / Assembly / City-Council districts by point-in-polygon. See README.
DISTRICT_FILE = "nyc_districts.geojson"

# Output file names.
CLEAN_FILE = "Final_Clean_Mapped.csv"
REVIEW_FILE = "Manual_Review_Needed.csv"
AUDIT_FILE = "Secure_Audit_Log.txt"
QUALITY_FILE = "Data_Quality_Report.csv"

# Per-row verification states (scenario #3, #16).
V_VERIFIED = "Verified"          # geocoded with a high-confidence match
V_LOWCONF = "Verified (low confidence)"  # geocoded but the match was weak or fuzzy
V_UNVERIFIED = "Unverified"      # valid but could not be geocoded/confirmed
V_REVIEW = "Needs Review"        # has one or more blocking errors

# Duplicate handling uses EXACT key matching only. There is deliberately no
# fuzzy threshold here: records are de-duplicated automatically only when the
# Client ID matches exactly and the rest of the record is identical. Anything
# that merely looks similar is shown for a person to confirm, never merged.

# Filename fragments that signal a non-canonical / redundant export
# (scenario #14, #8). Detected on upload and surfaced to the operator.
VERSION_MARKERS = [
    "copy", "copy of", "final", "final2", "finalfinal", "backup", "bkp", "old",
    "draft", "temp", "tmp", "verified", "unverified", "upload", "uploaded",
    "done", "new", "latest", "v1", "v2", "v3", "test", "duplicate", "dup",
]

# Inline unit / secondary-address tokens (scenario #1). Used to detect unit
# information that is embedded in Address_1 rather than split into Address_2.
_UNIT_RE = re.compile(
    r"\b(apt|apartment|suite|ste|unit|fl|floor|rm|room|bldg|building|#|"
    r"bsmt|basement|rear|front|ground|lower|upper|ph|penthouse|lobby)\b",
    re.IGNORECASE,
)

# NYC neighborhood -> borough. Source systems frequently record a neighborhood
# (e.g. "Woodside", "Cambria Heights") where the master wants a borough
# (scenario #2, #12). This table folds the common ones back to their borough.
# It is not exhaustive; unknown neighborhoods fall through to fuzzy matching and,
# failing that, are flagged for review.
NEIGHBORHOOD_TO_BOROUGH = {
    # Manhattan -> New York
    "harlem": "New York", "east harlem": "New York", "washington heights": "New York",
    "inwood": "New York", "chelsea": "New York", "soho": "New York",
    "tribeca": "New York", "greenwich village": "New York", "west village": "New York",
    "east village": "New York", "midtown": "New York", "upper east side": "New York",
    "upper west side": "New York", "lower east side": "New York", "chinatown": "New York",
    "financial district": "New York", "hell's kitchen": "New York", "hells kitchen": "New York",
    "murray hill": "New York", "gramercy": "New York", "morningside heights": "New York",
    # Brooklyn
    "williamsburg": "Brooklyn", "bushwick": "Brooklyn", "bedford stuyvesant": "Brooklyn",
    "bed stuy": "Brooklyn", "crown heights": "Brooklyn", "flatbush": "Brooklyn",
    "east flatbush": "Brooklyn", "park slope": "Brooklyn", "sunset park": "Brooklyn",
    "bay ridge": "Brooklyn", "bensonhurst": "Brooklyn", "coney island": "Brooklyn",
    "brighton beach": "Brooklyn", "canarsie": "Brooklyn", "brownsville": "Brooklyn",
    "east new york": "Brooklyn", "greenpoint": "Brooklyn", "dumbo": "Brooklyn",
    "fort greene": "Brooklyn", "gowanus": "Brooklyn", "red hook": "Brooklyn",
    "sheepshead bay": "Brooklyn", "borough park": "Brooklyn", "boro park": "Brooklyn",
    "midwood": "Brooklyn", "prospect heights": "Brooklyn", "carroll gardens": "Brooklyn",
    "flatlands": "Brooklyn", "cypress hills": "Brooklyn",
    # Queens
    "astoria": "Queens", "long island city": "Queens", "lic": "Queens",
    "woodside": "Queens", "sunnyside": "Queens", "jackson heights": "Queens",
    "elmhurst": "Queens", "corona": "Queens", "flushing": "Queens",
    "jamaica": "Queens", "forest hills": "Queens", "rego park": "Queens",
    "kew gardens": "Queens", "richmond hill": "Queens", "ozone park": "Queens",
    "howard beach": "Queens", "far rockaway": "Queens", "rockaway": "Queens",
    "bayside": "Queens", "whitestone": "Queens", "college point": "Queens",
    "fresh meadows": "Queens", "ridgewood": "Queens", "maspeth": "Queens",
    "middle village": "Queens", "glendale": "Queens", "st albans": "Queens",
    "saint albans": "Queens", "cambria heights": "Queens", "queens village": "Queens",
    "springfield gardens": "Queens", "rosedale": "Queens", "laurelton": "Queens",
    "hollis": "Queens", "south ozone park": "Queens", "east elmhurst": "Queens",
    # Bronx
    "riverdale": "Bronx", "fordham": "Bronx", "pelham bay": "Bronx",
    "throgs neck": "Bronx", "morris park": "Bronx", "hunts point": "Bronx",
    "mott haven": "Bronx", "concourse": "Bronx", "kingsbridge": "Bronx",
    "morrisania": "Bronx", "soundview": "Bronx", "castle hill": "Bronx",
    "parkchester": "Bronx", "wakefield": "Bronx", "williamsbridge": "Bronx",
    "co-op city": "Bronx", "co op city": "Bronx", "tremont": "Bronx",
    # Staten Island
    "st george": "Staten Island", "saint george": "Staten Island",
    "tottenville": "Staten Island", "great kills": "Staten Island",
    "new dorp": "Staten Island", "port richmond": "Staten Island",
    "stapleton": "Staten Island", "west brighton": "Staten Island",
    "todt hill": "Staten Island", "annadale": "Staten Island",
}


# ==============================================================================
#  SECTION 2.  LOW-LEVEL CLEANING HELPERS
# ==============================================================================

def clean_cell(value) -> str:
    """
    Universal scalar cleaner applied to every source value before any logic.

    * Converts None / NaN to "".
    * Removes rogue tab, carriage-return and newline characters.
    * Collapses runs of internal whitespace to a single space.
    * Strips leading / trailing whitespace.
    * Maps junk sentinels (NULL, #N/A, None, ...) to "".

    Returns a clean string (never None) so downstream code never has to guard
    against NaN/None again.
    """
    if value is None:
        return ""
    # pandas/openpyxl may hand us floats (e.g. NaN) or ints.
    if isinstance(value, float) and math.isnan(value):
        return ""
    text = str(value)
    # Replace tabs / CR / LF with a space, then collapse whitespace.
    text = text.replace("\t", " ").replace("\r", " ").replace("\n", " ")
    text = re.sub(r"\s+", " ", text).strip()
    if text.lower() in NULL_SENTINELS:
        return ""
    return text


def clean_dataframe(df: pd.DataFrame) -> pd.DataFrame:
    """Apply `clean_cell` to every cell of a DataFrame, returning all-string columns."""
    # pandas >= 2.1 renamed DataFrame.applymap -> DataFrame.map. Support both.
    if hasattr(df, "map"):
        try:
            return df.map(clean_cell)
        except TypeError:
            pass
    return df.applymap(clean_cell)


# ------------------------------------------------------------------------------
#  Address parsing
# ------------------------------------------------------------------------------
# Some systems jam the whole address into one field, e.g.
#     "967 Curtis Mission Suite 819, New York NY 10530"
# The parser below (split_jammed_address) peels ZIP, then state, then city off
# the right and keeps the remainder (including any inline "Apt./Suite") as the
# street, matching how the master file stores Address_1.


_ZIP_TAIL_RE = re.compile(r"(\d{5})(?:-\d{4})?\s*$")
_NY_STATE_TAIL_RE = re.compile(
    r"(?:^|[\s,])(N\.?\s?Y\.?|New\s+York(?:\s+State)?)\s*$", re.IGNORECASE)

# Secondary-unit (Address_2) detector: a trailing apartment / suite / floor /
# unit / room designator, or a standalone unit word. Word boundaries stop street
# types and names (Flatbush, Grand Concourse, Richmond Terrace) from matching.
# The designator after a unit word comes in every shape people type: 10R,
# 10 R (a space inside it), 18L jammed onto the word (APT18L), or after a
# hash and a colon (Apt#: 11T). A designator is a number then at most two
# letters, or a letter then a number, with an optional space or hyphen
# between, or a hyphenated code such as 12-B.
# Every designator shape carries a digit, so a street named Apartment Way
# or Unit Lane is never mistaken for a unit. A lone letter after a hash
# (#B) is allowed, since a hash is never part of a street name.
_UNIT_DESIGNATOR = (r"(?:[0-9]{1,5}(?:[\s\-]{0,2}[A-Za-z]{1,2})?"
                    r"|[A-Za-z]{1,2}[\s\-]{0,2}[0-9]{1,5}"
                    r"|[0-9A-Za-z\-]*[0-9][0-9A-Za-z\-]*)")
_HASH_DESIGNATOR = _UNIT_DESIGNATOR[:-1] + r"|[A-Za-z]{1,2})"
_UNIT_TAIL_RE = re.compile(
    r"\s+(?P<unit>"
    r"#\s*:?\s*" + _HASH_DESIGNATOR +
    r"|(?:apt|apartment|suite|ste|unit|fl|floor|rm|room|bldg|building|dept|"
    r"department|space|spc|lot|trailer|hangar|slip|pier|stop)\.?\s*#?\s*:?\s*"
    + _UNIT_DESIGNATOR +
    r"|[0-9]+(?:st|nd|rd|th)?\s+(?:floor|fl)\b"
    r"|penthouse|basement|bsmt|lobby|mezzanine"
    r")\s*$",
    re.IGNORECASE,
)


def _split_unit(street: str):
    """
    Separate a trailing secondary unit (apartment/suite/floor/etc.) from a
    street. Returns (primary_street, unit); unit is "" when none is present.
    """
    street = clean_cell(street)
    m = _UNIT_TAIL_RE.search(street)
    if not m:
        # A bare designator such as 14A or 3L right after a street-type word
        # is a unit with the word left off: "117-19 45TH AVE 14A". Only the
        # digits-then-letter shape is taken, so "Avenue U" and "Route 9" are
        # left alone.
        m2 = re.search(
            r"\b(?:st|street|ave|avenue|rd|road|blvd|boulevard|pl|place|dr|drive|"
            r"ct|court|ln|lane|way|pkwy|parkway|ter|terrace|expy|expressway|"
            r"hwy|highway|sq|square|cir|circle|plz|plaza)\.?\s+(\d{1,4}[A-Za-z])\s*$",
            street, re.IGNORECASE)
        if m2:
            return street[: m2.start(1)].strip().rstrip(",").strip(), m2.group(1)
        return street, ""
    primary = street[: m.start()].strip().rstrip(",").strip()
    unit = clean_cell(m.group("unit"))
    if not primary:            # the whole value was a unit; keep it as street
        return street, ""
    return primary, unit


_SEP_CHARS = r"\-,;:|/\\"


def _normalize_separators(text: str) -> str:
    """
    Treat a dash, slash, semicolon, colon, pipe or backslash used as a field
    separator as if it were a comma, so the parser can find the parts around it.

    Only separators surrounded by whitespace are converted. That keeps genuine
    address content intact: 40-22 24th St, 123-A, and c/o all lack the spaces,
    so they are untouched.
    """
    s = str(text or "")
    s = re.sub(r"\s+[" + _SEP_CHARS + r"]{1,3}\s+", ", ", s)
    s = re.sub(r"\s*,\s*(?:,\s*)+", ", ", s)          # ',,' or ', ,' to one
    return re.sub(r"\s+", " ", s).strip()


def tidy_fragment(text: str) -> str:
    """
    Clean a piece produced by a split: collapse repeated separators, remove any
    separator left stranded at either end, and normalize whitespace. A trailing
    period is kept, because 'St.' and 'Ave.' are legitimate.
    """
    s = str(text or "")
    s = re.sub(r"\s+", " ", s).strip()
    # collapse a run of separators to one, keeping the spacing around the run
    s = re.sub(r"(\s*)([" + _SEP_CHARS + r"])(?:\s*[" + _SEP_CHARS + r"])+(\s*)",
               lambda m: (m.group(1) or "") + m.group(2) + (m.group(3) or ""), s)
    # a space before a comma, semicolon or colon is never correct
    s = re.sub(r"\s+([,;:])", r"\1", s)
    s = re.sub(r"^[\s" + _SEP_CHARS + r"]+", "", s)
    s = re.sub(r"[\s" + _SEP_CHARS + r"]+$", "", s)
    return re.sub(r"\s+", " ", s).strip()


def split_jammed_address(raw: str):
    """
    Split a jammed single-field address into street / unit / city / state / zip.

    Works from the right: it peels a trailing ZIP (or ZIP+4), then a trailing NY
    state token, then a city, then a secondary unit (apartment, suite, floor,
    room, etc.) which goes into `unit` (Address_2). The remaining primary street
    goes into `street`. The city is taken from the segment after the last comma
    when commas are present, or matched against the known NYC boroughs and
    neighborhoods when there are no commas. Anything it cannot confidently
    attribute stays in street, so no data is lost. Any field may be empty.
    """
    raw = clean_cell(raw)
    if not raw:
        return {"street": "", "unit": "", "city": "", "state": "", "zip": ""}

    raw = _normalize_separators(raw)
    # A country or stray punctuation after the ZIP hides it from a parser that
    # reads from the right. "Brooklyn NY 11211 USA" and "NY 11249." both mean
    # the ZIP is at the end.
    raw = re.sub(r"(?i)(?:^|[\s,]+)(?:usa|u\.s\.a\.|us|united states)\s*$", "", raw)
    raw = re.sub(r"[\s.,;]+$", "", raw)
    work = raw
    zip5 = ""
    state = ""
    city = ""

    # 1) ZIP at the very end.
    mz = _ZIP_TAIL_RE.search(work)
    if mz:
        zip5 = mz.group(1)
        work = work[: mz.start()].strip().rstrip(",").strip()

    # 2) Trailing state, restricted to NY-family so a street type like "St" is
    #    never mistaken for a state. (All data here is NYC.)
    ms = _NY_STATE_TAIL_RE.search(work)
    if ms:
        state = "NY"
        work = work[: ms.start()].strip().rstrip(",").strip()

    have_signal = bool(zip5 or state)

    if "," in work:
        # Comma structure. Each segment is looked at for what it is: the
        # first is the street; a segment that is a unit (Apt. 4, Fl 2, #4,
        # Rear) is never the city, wherever it sits; the city is the last
        # segment that is not a unit. "111 Test St, Apt. 4, 11201" therefore
        # has no city, rather than a city called "Apt. 4".
        segs = [s.strip() for s in work.split(",") if s.strip()]
        if len(segs) >= 2:
            street_seg, rest = segs[0], segs[1:]
            units = [s for s in rest if _looks_like_unit(s)]
            others = [s for s in rest if not _looks_like_unit(s)]
            if others:
                city = others[-1]
                others = others[:-1]
            # a unit named as its own segment goes straight to the unit slot;
            # the peel below still handles a unit jammed onto the street
            unit_seg = units[0] if units else ""
            street = ", ".join([street_seg] + others + units[1:])
            if unit_seg:
                primary, more = _split_unit(street)
                return {
                    "street": tidy_fragment(clean_cell(primary)),
                    "unit": tidy_fragment(clean_cell(unit_seg if not more else f"{more} {unit_seg}")),
                    "city": tidy_fragment(clean_cell(city)),
                    "state": state,
                    "zip": zip5,
                }
        else:
            street = segs[0] if segs else work
    elif have_signal:
        # No commas, but we saw a ZIP or state, so a trailing city is likely.
        # Greedily match the last 1-3 words against known boroughs/neighborhoods.
        words = work.split()
        canon = {c.lower() for c in CANONICAL_CITIES}
        picked = ""
        for n in (3, 2, 1):
            if len(words) > n:
                tail = " ".join(words[-n:])
                if tail.lower() in canon or tail.lower() in NEIGHBORHOOD_TO_BOROUGH:
                    picked = tail
                    words = words[:-n]
                    break
        city = picked
        street = " ".join(words)
    else:
        street = work

    # 3) Peel a secondary unit off the primary street into Address_2.
    primary, unit = _split_unit(street)

    return {
        "street": tidy_fragment(clean_cell(primary)),
        "unit": tidy_fragment(clean_cell(unit)),
        "city": tidy_fragment(clean_cell(city)),
        "state": state,
        "zip": zip5,
    }


def split_jammed_name(raw: str):
    """
    Split a jammed single-field name into first / middle initial / last.

    Handles the two common forms:
        "Last, First M"   (comma-separated, last name first)
        "First M Last"    (space-separated, natural order)
    The middle token is only treated as a middle initial when present; it is
    reduced to a single uppercase letter. A trailing generational suffix
    (Jr, Sr, II, III, IV) is folded back onto the last name so it is not lost.
    Returns a dict with keys first, middle, last (any of which may be "").
    """
    raw = clean_cell(raw)
    if not raw:
        return {"first": "", "middle": "", "last": ""}

    suffix = ""
    # Pull a trailing suffix off the end before splitting the core name.
    sfx = re.search(r"[,\s]+(Jr|Sr|II|III|IV|Jr\.|Sr\.)\s*$", raw, flags=re.IGNORECASE)
    if sfx:
        suffix = sfx.group(1).rstrip(".")
        raw = raw[: sfx.start()].strip()

    if "," in raw:
        # "Last, First M" form.
        last_part, _, rest = raw.partition(",")
        last = clean_cell(last_part)
        rest_tokens = clean_cell(rest).split()
        first = rest_tokens[0] if rest_tokens else ""
        middle = rest_tokens[1] if len(rest_tokens) > 1 else ""
    else:
        # "First M Last" natural order.
        tokens = raw.split()
        if len(tokens) == 1:
            first, middle, last = tokens[0], "", ""
        elif len(tokens) == 2:
            first, middle, last = tokens[0], "", tokens[1]
        else:
            # 3+ tokens: first, single middle token, everything else is the last
            # name (covers multi-word surnames like "Van Der Berg").
            first = tokens[0]
            middle = tokens[1]
            last = " ".join(tokens[2:])

    # Only keep the middle piece if it reduces to a valid single initial.
    middle_initial = ""
    if middle:
        mi, _note = normalize_middle_initial(middle)
        middle_initial = mi

    if suffix and last:
        last = f"{last} {suffix}"

    return {
        "first": tidy_fragment(clean_cell(first)),
        "middle": middle_initial,
        "last": tidy_fragment(clean_cell(last)),
    }


# ------------------------------------------------------------------------------
#  Field normalisers (each returns (value, note) where note documents any change)
# ------------------------------------------------------------------------------

def normalize_middle_initial(raw: str):
    """
    Middle initial must be a single uppercase letter (or empty).

    Handles: lowercase letters, and the case where a *full* middle name landed in
    the column (e.g. "Suzanne") -- we reduce it to its first initial rather than
    discarding the row, since the master schema only wants the initial.
    """
    raw = clean_cell(raw)
    if raw == "":
        return "", None
    original = raw
    first = raw[0].upper()
    if not first.isalpha():
        # Do not echo the raw value (could be a name fragment) into the audit log.
        return "", "Middle_Initial: dropped non-alphabetic value"
    if len(raw) > 1:
        # Echo only the resulting single initial, never the full original name.
        return first, f"Middle_Initial: reduced multi-character value to initial '{first}'"
    if raw != first:
        return first, f"Middle_Initial: upper-cased to '{first}'"
    return first, None


def normalize_zip(primary: str, fallback: str = ""):
    """
    Normalize a ZIP to 5 digits.

    * primary  : the value from the column the user mapped to Zip.
    * fallback : a ZIP discovered elsewhere (e.g. embedded in a jammed address),
                 used only when `primary` is empty.

    Returns (zip5, note, error). `error` is a human message if the ZIP is
    unusable; otherwise "".
    """
    primary = clean_cell(primary)
    fallback = clean_cell(fallback)
    note = None

    chosen = primary
    if chosen == "" and fallback != "":
        chosen = fallback
        note = "Zip: column empty; recovered ZIP from address text"
    elif (
        primary
        and fallback
        and primary != fallback
        and fallback[:5] != primary[:5]
    ):
        # Genuine conflict between the mapped column and the address text.
        # Deterministic rule: trust the explicitly-mapped column, but record it.
        note = (
            f"Zip: kept mapped column '{primary}'; address text "
            f"showed differing '{fallback}'"
        )

    digits_dash = re.match(r"^(\d{5})-\d{4}$", chosen)   # 10423-4757
    if digits_dash:
        return digits_dash.group(1), (note or "Zip: trimmed ZIP+4 to 5-digit"), ""
    if re.match(r"^\d{9}$", chosen):                     # 104234757
        return chosen[:5], (note or "Zip: trimmed 9-digit ZIP to 5-digit"), ""
    if re.match(r"^\d{5}$", chosen):
        return chosen, note, ""

    # Anything else (e.g. "#N/A", "", "1234") is invalid.
    shown = chosen if chosen else "(blank)"
    return "", note, f"Invalid ZIP Code format: {shown}"


def borough_from_zip(zip5: str):
    """
    Return the NYC borough (as a canonical City value) for a 5-digit ZIP, using
    documented NYC ZIP ranges. Returns "" when the ZIP is not a clearly-NYC ZIP,
    so this never asserts a borough it is unsure about. ZIP is authoritative for
    city and state (borough), though not for whether the street itself is valid.
    """
    if not (isinstance(zip5, str) and re.match(r"^\d{5}$", zip5)):
        return ""
    n = int(zip5)
    if 10001 <= n <= 10292:
        return "New York"          # Manhattan
    if 10301 <= n <= 10314:
        return "Staten Island"
    if 10451 <= n <= 10475:
        return "Bronx"
    if 11201 <= n <= 11256:
        return "Brooklyn"
    if n in (11004, 11005) or 11101 <= n <= 11120 or 11351 <= n <= 11697:
        return "Queens"
    return ""


_UNIT_WORDS = (r"apt|apartment|ste|suite|unit|fl|floor|rm|room|bldg|building|"
               r"ph|penthouse|bsmt|basement|lobby|mezzanine|rear|front|no|num")


def _unit_key(value: str) -> str:
    """
    Reduce a unit to a comparable core: drop the label and punctuation, keep the
    designator. 'Apt 2A', 'apt. 2-a' and '#2A' all reduce to '2a'.
    """
    v = str(value or "").strip().lower()
    v = re.sub(r"^(?:" + _UNIT_WORDS + r")\b\.?\s*", "", v)
    v = v.lstrip("#").strip()
    return re.sub(r"[^a-z0-9]", "", v)


def _same_unit(a: str, b: str) -> bool:
    """True when two unit values name the same unit, ignoring label and spacing."""
    ka, kb = _unit_key(a), _unit_key(b)
    return bool(ka) and ka == kb


def _looks_like_unit(value: str) -> bool:
    """True when a value reads as a unit rather than other secondary content."""
    v = str(value or "").strip().lower()
    if not v:
        return False
    if re.match(r"^(?:" + _UNIT_WORDS + r")\b", v):
        return True
    if v.startswith("#"):
        return True
    # an ordinal then a unit word: 4th Fl, 2nd Floor, 1st Fl Rear
    if re.match(r"^\d{1,3}(st|nd|rd|th)\s+(?:" + _UNIT_WORDS + r")\b", v):
        return True
    # a bare designator such as '2A' or '3-L'
    return bool(re.fullmatch(r"[0-9]{1,4}[a-z]?|[a-z][0-9]{1,4}|[0-9]{1,4}-?[a-z]",
                             v))


def normalize_state(raw: str):
    """State must be NY. Empty defaults to NY (every source here is NYC-only)."""
    raw = clean_cell(raw)
    if raw == "":
        return "NY", "State: defaulted empty value to 'NY'", ""
    canon = CITY_ALIASES.get(raw.lower())  # in case 'New York' state vs city slip
    if raw.upper() == "NY":
        return "NY", None, ""
    if raw.lower() in ("new york", "n.y.", "ny."):
        return "NY", f"State: normalized '{raw}' to 'NY'", ""
    return raw.upper(), None, f"State is not NY: {raw!r}"


def normalize_city(raw: str):
    """
    Resolve a city to one of the five canonical NYC boroughs.

    1. exact alias-table hit (handles known abbreviations / misspellings)
    2. already canonical
    3. fuzzy match to the nearest canonical borough (>= threshold)
    Returns (city, note, error).
    """
    raw = clean_cell(raw)
    if raw == "":
        return "", None, "City could not be determined"

    # 1) alias table
    alias = CITY_ALIASES.get(raw.lower())
    if alias:
        if alias != raw:
            return alias, f"City: normalized '{raw}'->'{alias}'", ""
        return alias, None, ""

    # 2) already canonical (case-insensitive)
    for c in CANONICAL_CITIES:
        if raw.lower() == c.lower():
            return c, (None if raw == c else f"City: cased '{raw}'->'{c}'"), ""

    # 3) NYC neighborhood -> borough (scenario #2 / #12)
    borough = NEIGHBORHOOD_TO_BOROUGH.get(raw.lower())
    if borough:
        return borough, f"City: mapped neighborhood '{raw}' to borough '{borough}'", ""

    # 4) fuzzy fallback
    best_city, best_score = None, -1
    for c in CANONICAL_CITIES:
        s = _ratio(raw.lower(), c.lower())
        if s > best_score:
            best_city, best_score = c, s
    if best_score >= CITY_FUZZ_THRESHOLD:
        return best_city, f"City: fuzzy-matched '{raw}'->'{best_city}' ({best_score}%)", ""

    return raw, None, f"Unrecognized City: {raw!r}"


def normalize_name(raw: str):
    """Light touch: strip junk; collapse spacing. Names are kept as provided."""
    return clean_cell(raw)


# ==============================================================================
#  SECTION 2b.  PRE-MAPPING STAGING  (clean & split columns before mapping)
# ==============================================================================
# Before the user maps columns to the master schema, they can stage each file:
# clean selected columns, split a column by a delimiter, or split a jammed
# address into street/city/state/zip. Each operation ADDS columns (originals are
# never dropped, preserving the lossless guarantee) so the mapping step that
# follows can point at tidy, one-to-one columns.
#
# Staging is modeled as an ordered list of operation dicts applied to the
# freshly-parsed DataFrame. This keeps it deterministic across Streamlit reruns
# and unit-testable without the UI.

# Friendly delimiter labels -> actual characters.
DELIMITERS = {
    "Comma  ,": ",",
    "Tab": "\t",
    "Pipe  |": "|",
    "Semicolon  ;": ";",
    "Colon  :": ":",
    "Space": " ",
    "Slash  /": "/",
}


# Words that keep their existing intentional casing. Roman-numeral suffixes are
# upper-cased; everything relies on the mixed-case guard below.
_ROMAN_SUFFIXES = {"ii", "iii", "iv", "vi", "vii", "viii", "ix", "xi", "xii", "xiii"}
# Mac-prefixed surnames get an internal capital; a curated list avoids turning
# ordinary words like "Machado" or "Mack" into "MacHado" / "MacK".
_MAC_NAMES = {
    "macdonald", "macarthur", "mackenzie", "macmillan", "macgregor", "macleod",
    "macintosh", "macintyre", "macneil", "macpherson", "macdougall", "mackay",
    "maclean", "macknight",
}
_ADDR_DIRECTIONALS = {"n", "s", "e", "w", "ne", "nw", "se", "sw"}

# Smart-punctuation and junk characters handled by the sanitizer. Apostrophes,
# periods, hyphens, commas, ampersands, slashes and spaces are deliberately kept.
_SMART_MAP = {
    "\u2018": "'", "\u2019": "'", "\u201a": "'", "\u201b": "'",
    "\u201c": '"', "\u201d": '"', "\u201e": '"',
    "\u2013": "-", "\u2014": "-", "\u2015": "-", "\u2212": "-",
    "\u2026": "...", "\u00a0": " ", "\u200b": "", "\ufeff": "",
}
_JUNK_SYMBOLS_RE = re.compile(r"[\^~`|<>{}\[\]\\*]")


def _is_mixed_case(w: str) -> bool:
    """True if a token already has both upper and lower letters (intentional casing)."""
    return any(c.isupper() for c in w) and any(c.islower() for c in w)


def _title_word_name(w: str) -> str:
    """Title-case a single name token, preserving intentional mixed casing."""
    if not w:
        return w
    # Leave tokens that are already mixed-case as typed (DiNapoli, McMahon,
    # O'Brien, LaGuardia, St. Claire). Only re-case all-upper or all-lower tokens.
    if _is_mixed_case(w):
        return w
    if "-" in w:
        return "-".join(_title_word_name(p) for p in w.split("-"))
    if "'" in w:
        return "'".join((p[:1].upper() + p[1:].lower()) if p else p
                        for p in w.split("'"))
    low = w.lower()
    if low in _ROMAN_SUFFIXES:
        return w.upper()
    if low.startswith("mc") and len(low) > 2 and low[2:].isalpha():
        return "Mc" + low[2].upper() + low[3:]
    if low in _MAC_NAMES:
        return "Mac" + low[3].upper() + low[4:]
    return w[:1].upper() + w[1:].lower()


def smart_title_name(text: str) -> str:
    """Title-case a name without disturbing O'Brien, St. Claire, O Toole, Van Helsing."""
    return " ".join(_title_word_name(w) for w in clean_cell(text).split())


def _title_word_addr(w: str) -> str:
    """Title-case a single address token, keeping directionals, ordinals and IDs."""
    if not w:
        return w
    if _is_mixed_case(w):
        return w
    if w.lower().strip(".") in _ADDR_DIRECTIONALS:
        return w.upper()
    m = re.match(r"^(\d+)(st|nd|rd|th)$", w.lower())
    if m:
        return m.group(1) + m.group(2)
    if any(c.isdigit() for c in w):
        return w                       # 42-09, 4B, 10007 stay as-is
    if "-" in w:
        return "-".join(_title_word_addr(p) for p in w.split("-"))
    return w[:1].upper() + w[1:].lower()


def smart_title_address(text: str) -> str:
    """Title-case a street address, keeping directionals (NW) and ordinals (3rd)."""
    return " ".join(_title_word_addr(w) for w in clean_cell(text).split())


def sanitize_special(text: str) -> str:
    """
    Strip genuine junk while preserving punctuation that belongs in real data.

    Removes control and zero-width characters, converts smart quotes and dashes
    to plain ASCII, removes symbols that never appear in names or addresses
    (^ ~ ` | < > { } [ ] backslash *), and collapses doubled punctuation typos
    (St.. -> St.). Apostrophes, single periods, single hyphens, commas,
    ampersands, slashes and spaces are kept exactly, so O'Brien, St. Claire,
    O Toole and Van Helsing pass through unchanged.
    """
    t = clean_cell(text)
    if not t:
        return t
    t = unicodedata.normalize("NFKC", t)
    for k, v in _SMART_MAP.items():
        t = t.replace(k, v)
    t = "".join(ch for ch in t if not unicodedata.category(ch).startswith("C"))
    t = _JUNK_SYMBOLS_RE.sub(" ", t)
    t = re.sub(r"([.,;:!?\-])\1+", r"\1", t)     # collapse only doubled punctuation
    return re.sub(r"\s+", " ", t).strip()


def _apply_case(val: str, mode: str) -> str:
    """Apply the chosen casing rule to one value."""
    if mode == "Smart Title (names)":
        return smart_title_name(val)
    if mode == "Smart Title (address)":
        return smart_title_address(val)
    if mode in ("Title Case (basic)", "Title Case"):
        return val.title()
    if mode == "UPPERCASE":
        return val.upper()
    if mode == "lowercase":
        return val.lower()
    return val


def op_clean(df: pd.DataFrame, columns, case="none", strip_punct=False,
             sanitize=False) -> pd.DataFrame:
    """Re-clean selected columns: sentinel/whitespace pass, optional sanitize,
    edge-punctuation strip, and case transform. All beyond the base pass are opt-in."""
    df = df.copy()
    for c in columns:
        if c not in df.columns:
            continue
        s = df[c].map(clean_cell)
        if sanitize:
            s = s.map(sanitize_special)
        if strip_punct:
            s = s.map(lambda v: re.sub(r"^[\s,;:.\-|]+|[\s,;:.\-|]+$", "", v).strip())
        if case and case != "none":
            s = s.map(lambda v: _apply_case(v, case))
        df[c] = s
    return df


def op_split_delim(df: pd.DataFrame, column, delimiter, maxsplit=0, names=None) -> pd.DataFrame:
    """Split one column on a delimiter into new columns. Originals are retained."""
    df = df.copy()
    if column not in df.columns or not delimiter:
        return df

    def splitter(v):
        """Split a jammed value on the chosen delimiter into numbered or named parts."""
        v = clean_cell(v)
        parts = v.split(delimiter, maxsplit) if maxsplit and maxsplit > 0 else v.split(delimiter)
        return [p.strip() for p in parts]

    rows = df[column].map(splitter)
    width = max((len(r) for r in rows), default=0)
    names = [n.strip() for n in (names or []) if n.strip()]
    colnames = []
    for i in range(width):
        colnames.append(names[i] if i < len(names) else f"{column}_{i + 1}")
    for i, cn in enumerate(colnames):
        df[cn] = [r[i] if i < len(r) else "" for r in rows]
    return df


def op_split_jammed(df: pd.DataFrame, column) -> pd.DataFrame:
    """Split a jammed address column into <col>_street/_address2/_city/_state/_zip."""
    df = df.copy()
    if column not in df.columns:
        return df
    parsed = df[column].map(split_jammed_address)
    df[f"{column}_street"] = parsed.map(lambda d: d["street"])
    df[f"{column}_address2"] = parsed.map(lambda d: d.get("unit", ""))
    df[f"{column}_city"] = parsed.map(lambda d: d["city"])
    df[f"{column}_state"] = parsed.map(lambda d: d["state"])
    df[f"{column}_zip"] = parsed.map(lambda d: d["zip"])
    return df


def op_split_name(df: pd.DataFrame, column) -> pd.DataFrame:
    """Split a jammed name column into <col>_first / _middle / _last."""
    df = df.copy()
    if column not in df.columns:
        return df
    parsed = df[column].map(split_jammed_name)
    df[f"{column}_first"] = parsed.map(lambda d: d["first"])
    df[f"{column}_middle"] = parsed.map(lambda d: d["middle"])
    df[f"{column}_last"] = parsed.map(lambda d: d["last"])
    return df


# Set by whoever hosts the engine to a callable (street, city) -> (zip, why),
# backed by Geosupport or the reference data. The calculated ZIP column uses
# it; with nothing set, the column says so on every row rather than guessing.
ZIP_RESOLVER = None


def op_calc_zip(df: pd.DataFrame, street_col, city_col="", zip_col="",
                mode="blanks", name="Zip_calculated") -> pd.DataFrame:
    """
    A calculated column: the ZIP each row's address points to.

    Two columns are added. The first holds the ZIP where the address settles
    it, or blank where it does not. The second holds the reason for every row:
    the evidence for a ZIP that was found, or why one could not be, so a row
    that cannot be placed reaches review carrying its own explanation. With an
    existing ZIP column and mode "blanks", rows that already have a ZIP keep
    it and are not looked up.
    """
    out = df.copy()
    note = f"{name}_note"
    zips, notes = [], []
    cache = {}
    for _, row in out.iterrows():
        street = clean_cell(row.get(street_col, "")) if street_col in out.columns else ""
        city = clean_cell(row.get(city_col, "")) if city_col and city_col in out.columns else ""
        have = clean_cell(row.get(zip_col, "")) if zip_col and zip_col in out.columns else ""
        have5 = re.match(r"\d{5}", have.replace(" ", "")).group(0) if re.match(r"\d{5}", have.replace(" ", "")) else ""
        if mode == "blanks" and have5:
            zips.append(have5)
            notes.append("kept the ZIP the row already had")
            continue
        if not street:
            zips.append("")
            notes.append("no street address to look up")
            continue
        key = (street.lower(), city.lower())
        if key not in cache:
            if ZIP_RESOLVER is None:
                cache[key] = (None, "no geocoder is available to look the address up")
            else:
                try:
                    cache[key] = ZIP_RESOLVER(street, city)
                except Exception as exc:  # pragma: no cover
                    cache[key] = (None, f"lookup failed: {exc}")
        z, why = cache[key]
        zips.append(z or "")
        notes.append(why or "")
    out[name] = zips
    out[note] = notes
    return out


def apply_prep_ops(df: pd.DataFrame, ops) -> pd.DataFrame:
    """Apply an ordered list of staging operations, returning a new DataFrame."""
    for op in ops or []:
        t = op.get("type")
        if t == "calc_zip":
            df = op_calc_zip(df, op.get("street_col"), op.get("city_col", ""),
                             op.get("zip_col", ""), op.get("mode", "blanks"),
                             op.get("name") or "Zip_calculated")
        elif t == "clean":
            df = op_clean(df, op.get("columns", []), op.get("case", "none"),
                          op.get("strip_punct", False), op.get("sanitize", False))
        elif t == "split_delim":
            df = op_split_delim(df, op.get("column"), op.get("delimiter", ""),
                                op.get("maxsplit", 0), op.get("names"))
        elif t == "split_jammed":
            df = op_split_jammed(df, op.get("column"))
        elif t == "split_name":
            df = op_split_name(df, op.get("column"))
    return df


def describe_op(op) -> str:
    """Human-readable one-line summary of a staging operation."""
    t = op.get("type")
    if t == "calc_zip":
        parts = [f"from {op.get('street_col')}"]
        if op.get("city_col"):
            parts.append(f"and {op['city_col']}")
        if op.get("zip_col") and op.get("mode", "blanks") == "blanks":
            parts.append(f"where {op['zip_col']} is blank")
        return (f"Calculated column {op.get('name') or 'Zip_calculated'}: the ZIP "
                f"the address points to, {' '.join(parts)}")
    if t == "clean":
        extras = []
        if op.get("case", "none") != "none":
            extras.append(op["case"])
        if op.get("sanitize"):
            extras.append("sanitize junk")
        if op.get("strip_punct"):
            extras.append("strip edge punctuation")
        tail = f" ({', '.join(extras)})" if extras else ""
        return f"Clean columns: {', '.join(op.get('columns', []))}{tail}"
    if t == "split_delim":
        d = op.get("delimiter", "")
        shown = {"\t": "Tab", " ": "Space"}.get(d, d)
        return f"Split '{op.get('column')}' by '{shown}'"
    if t == "split_jammed":
        return f"Split jammed address in '{op.get('column')}'"
    if t == "split_name":
        return f"Split jammed name in '{op.get('column')}'"
    return "Unknown operation"


# ==============================================================================
#  SECTION 3.  FILE INGESTION  (all parsing happens in RAM, never on disk)
# ==============================================================================

def read_uploaded_file(uploaded) -> pd.DataFrame:
    """
    Turn an uploaded file object into a flat, all-string DataFrame.

    Supports .csv .tsv .xlsx .json .xml. Nested JSON / XML are flattened so the
    mapping UI can present every leaf field as a selectable column.
    """
    name = uploaded.name.lower()
    raw_bytes = uploaded.getvalue()  # bytes, held only in memory

    if name.endswith(".csv"):
        df = pd.read_csv(io.BytesIO(raw_bytes), dtype=str, keep_default_na=False)

    elif name.endswith(".tsv"):
        df = pd.read_csv(
            io.BytesIO(raw_bytes), sep="\t", dtype=str, keep_default_na=False
        )

    elif name.endswith(".xlsx"):
        df = pd.read_excel(
            io.BytesIO(raw_bytes), dtype=str, engine="openpyxl"
        )
        df = df.astype(str)

    elif name.endswith(".json"):
        data = json.loads(raw_bytes.decode("utf-8"))
        if isinstance(data, dict):
            # Either a single record or a wrapper like {"records": [...]}.
            list_vals = [v for v in data.values() if isinstance(v, list)]
            data = list_vals[0] if len(list_vals) == 1 else [data]
        # json_normalize flattens any genuine nesting into dotted columns; the
        # files here already use dotted keys, which it also handles correctly.
        df = pd.json_normalize(data, sep=".")
        df = df.astype(str)

    elif name.endswith(".xml"):
        root = ET.fromstring(raw_bytes, parser=_SAFE_XML_PARSER)
        records = []
        # The repeating record element is the (only) repeated child tag.
        children = list(root)
        # If the root directly contains record elements, iterate them; otherwise
        # treat the root's children as records.
        record_nodes = children if children else [root]
        for node in record_nodes:
            rec = {}
            for leaf in node.iter():
                if leaf is node:
                    continue
                if list(leaf):  # has its own children -> not a leaf
                    continue
                rec[leaf.tag] = leaf.text
            if rec:
                records.append(rec)
        df = pd.DataFrame(records, dtype=str)

    else:
        raise ValueError(f"Unsupported file type: {uploaded.name}")

    # Universal clean pass and stable string dtype.
    df = df.fillna("")
    df = clean_dataframe(df)
    return df


# ==============================================================================
#  SECTION 4.  TRANSFORMATION ENGINE  (one source row -> one master row)
# ==============================================================================

class AuditLog:
    """
    Collects PII-safe audit entries. Each entry records the source file, the
    source row position, the client ID (or a placeholder), and a message that
    must not contain a client name or full street address.
    """

    def __init__(self):
        self.entries = []  # list of dicts

    def add(self, source_file, row_idx, client_id, message):
        """Record one audit entry: file, row, identifier and what was done."""
        if not message:
            return
        self.entries.append(
            {
                "source_file": source_file,
                "row": row_idx,
                "client_id": client_id or "<no-id>",
                "message": message,
            }
        )

    def as_dataframe(self) -> pd.DataFrame:
        """The audit entries as a table."""
        if not self.entries:
            return pd.DataFrame(
                columns=["source_file", "row", "client_id", "message"]
            )
        return pd.DataFrame(self.entries)

    def as_secure_text(self) -> str:
        """Render the export. Only system IDs are referenced -- no names/addresses."""
        lines = [
            "SECURE AUDIT LOG",
            f"Generated (UTC): {datetime.now(timezone.utc).isoformat(timespec='seconds')}",
            f"Fuzzy backend: {FUZZ_BACKEND}",
            "This log references system IDs only. No client names or full "
            "street addresses are included.",
            "=" * 78,
        ]
        for e in self.entries:
            lines.append(
                f"[{e['source_file']} | ID {e['client_id']} | src-row {e['row']}] "
                f"{e['message']}"
            )
        if not self.entries:
            lines.append("(no transformations were required)")
        return "\n".join(lines)


def parse_date_value(value):
    """
    Read a date written in any of the forms these exports use, and return
    (year, month, day) or None. Accepts 2024-03-15, 03/15/2024, 15.03.2024,
    and a two digit year. Returns None when the value is not a date, which is
    what routes the row to review rather than guessing at it.
    """
    s = clean_cell(value)
    if not s:
        return None
    # Excel serial date, which appears when a date column is exported as a number
    if re.fullmatch(r"\d{5}", s):
        try:
            base = datetime(1899, 12, 30)
            d = base + timedelta(days=int(s))
            return (d.year, d.month, d.day)
        except Exception:
            return None
    m = re.match(r"^(\d{4})[-/.](\d{1,2})[-/.](\d{1,2})$", s)
    if m:
        y, mo, d = int(m.group(1)), int(m.group(2)), int(m.group(3))
    else:
        m = re.match(r"^(\d{1,2})[-/.](\d{1,2})[-/.](\d{2,4})$", s)
        if not m:
            return None
        mo, d, y = int(m.group(1)), int(m.group(2)), int(m.group(3))
        if y < 100:
            y += 1900 if y > 25 else 2000
    if not (1 <= mo <= 12 and 1 <= d <= 31):
        # a day and month written the other way round
        if 1 <= d <= 12 and 1 <= mo <= 31:
            mo, d = d, mo
        else:
            return None
    if not (1900 <= y <= 2100):
        return None
    try:
        datetime(y, mo, d)
    except ValueError:
        return None
    return (y, mo, d)


def format_date_value(parts) -> str:
    """Write a date in one unambiguous form, so every source ends up alike."""
    return f"{parts[0]:04d}-{parts[1]:02d}-{parts[2]:02d}"


def normalize_typed_value(field, value):
    """
    Return (value_to_store, error_or_None) for a field's declared type.

    A date is rewritten into one consistent form so that 3/15/2024 from one
    export and 2024-03-15 from another are stored identically. Nothing else is
    changed. A value that does not fit its type is reported rather than coerced.
    """
    val = clean_cell(value)
    if not val:
        return val, None
    dtype = (field.get("dtype") or "str").lower()

    if dtype == "int":
        if not re.fullmatch(r"-?\d+", val):
            return val, f"{field['label']} must be a whole number"
        return val, None

    if dtype == "decimal":
        cleaned = val.replace(",", "")
        if not re.fullmatch(r"-?\d+(\.\d+)?", cleaned):
            return val, f"{field['label']} must be a number"
        return cleaned, None

    if dtype == "date":
        parts = parse_date_value(val)
        if parts is None:
            return val, (f"{field['label']} is not a date that can be read "
                         f"('{val}')")
        return format_date_value(parts), None

    if dtype == "bool":
        low = val.lower()
        if low in ("y", "yes", "true", "t", "1"):
            return "Yes", None
        if low in ("n", "no", "false", "f", "0"):
            return "No", None
        return val, f"{field['label']} must be yes or no"

    return val, None


def _validate_field_value(field, value, flag):
    """Flag a value that violates its schema field's max length or type."""
    val = clean_cell(value)
    if not val:
        return
    length = int(field.get("length", 0) or 0)
    if length > 0 and len(val) > length:
        flag("3 Verification", "segregated",
             f"{field['label']} exceeds max length {length} (got {len(val)})")
    _stored, err = normalize_typed_value(field, val)
    if err:
        flag("3 Verification", "segregated", err)


SUMMARY_WORDS = re.compile(
    r"(?i)^\s*(grand\s+)?(total|subtotal|sub-total|sum|count|average|avg|"
    r"mean|summary|overall|all\s+(clients|records|programs)|n\s*=)\b")


def is_summary_row(raw_row: dict, mapping: dict) -> bool:
    """
    True when a row is a total or heading rather than a person.

    The signs: no name and no street in the mapped columns, and either a word
    such as Total or Subtotal in one of the row's values, or nothing in the row
    but a handful of numbers. A row that merely lacks a name is not a summary
    row; it is a client record with a missing name, and is flagged as that.
    """
    def mapped(role):
        """The cleaned value of one field on this row, by its matched column."""
        col = mapping.get(role, "")
        return clean_cell(raw_row.get(col, "")) if col else ""

    names = [mapped("First_Name"), mapped("Last_Name")]
    # "Total" sitting in a name column is the commonest summary row of all
    if any(SUMMARY_WORDS.match(n) for n in names if n) and not mapped("Address_1"):
        return True
    if any(names) or mapped("Address_1"):
        return False
    values = [clean_cell(v) for v in raw_row.values()
              if not str(v).startswith("__")]
    values = [v for v in values if v]
    if not values:
        return False
    if any(SUMMARY_WORDS.match(v) for v in values):
        return True
    numeric = sum(1 for v in values if re.fullmatch(r"[\d,.\-%$ ]+", v))
    return numeric >= 1 and numeric == len(values)


def transform_row(raw_row: dict, mapping: dict, source_file: str, row_idx: int,
                  audit: AuditLog, schema=None, source_defaults=None,
                  program_aliases=None) -> dict:
    """
    Transform ONE cleaned source row into a master-schema record.

    `mapping` maps each master field (or custom field label) -> a source column.
    `schema` is the active output schema; it defaults to the standard schema, in which
    case behavior is identical to the original app.

    Every scenario the row triggers is recorded as a structured flag with an
    action of 'fixed', 'annotated', or 'segregated', and is mirrored to the
    audit log. A 'segregated' flag also routes the row to manual review.

    Returns a dict with every master column plus bookkeeping keys:
        __errors__   list[str]     blocking problems (empty == perfect)
        __flags__    list[dict]    every scenario detected (scenario/action/message)
        __custom__   dict          user-added passthrough fields (label -> value)
        __needs_city__ / __city_err__ / __dup_key__ / lineage / __original__
    """
    schema = schema or DEFAULT_SCHEMA
    by_role = {f["role"]: f for f in schema if f["role"] != "custom"}

    def required_of(role):
        """The roles that must be present for a row to pass."""
        return bool(by_role.get(role, {}).get("required", False))

    def label_of(role):
        """The display label of a schema field, falling back to its role."""
        return by_role.get(role, {}).get("label", role)

    errors = []
    flags = []

    def flag(scenario, action, message):
        """Annotate the row, mirror to the audit log, and (if segregating) fail it."""
        flags.append({"scenario": scenario, "action": action, "message": message})
        audit.add(source_file, row_idx, client_id, f"[{scenario} | {action}] {message}")
        if action == "segregated":
            errors.append(message)

    defaults_used = []
    src_defaults = source_defaults or {}



    def src(master_field):
        """
        The mapped source value, or a default when the source is blank.

        Two kinds of default apply, most specific first: one set for this source
        file, then one set on the schema field for every source. A default only
        fills a gap; it never replaces a value the source supplied, and every
        use is recorded so a reader can tell which values were provided rather
        than read.
        """
        col = mapping.get(master_field, "")
        value = clean_cell(raw_row.get(col, "")) if col else ""
        if value:
            return value
        for default, origin in (
                (clean_cell(src_defaults.get(master_field, "")), "this source"),
                (clean_cell(by_role.get(master_field, {}).get("default", "")), "the schema")):
            if default:
                if master_field not in dict(defaults_used):
                    defaults_used.append((master_field, origin))
                return default
        return ""

    client_id = src("Client_ID")

    # A summary row (a total, a subtotal, a heading that slipped into the data)
    # is not a client record. It is flagged as exactly that and nothing else,
    # so it does not appear as a missing name, a missing address, a bad ZIP
    # and a missing city all at once.
    if is_summary_row(raw_row, mapping):
        flag("0 Not a record", "segregated",
             "Summary row, not a client record (a total, count or heading); "
             "set aside")
        return {
            "First_Name": "", "Middle_Initial": "", "Last_Name": "",
            "Client_ID": "", "Address_1": "", "Address_2": "", "City": "",
            "State": "", "Zip": "", "Latitude": "", "Longitude": "",
            "Verification_Status": V_REVIEW, "Geocode_Confidence": "",
            "Possible_Duplicate": "", "Duplicate_In_File": "",
            "Senate_District": "", "Assembly_District": "", "Council_District": "",
            "__source_file__": source_file, "__source_row__": row_idx,
            "__errors__": errors, "__flags__": flags, "__custom__": {},
            "__program__": "", "__dup_key__": "", "__dup_keep__": False,
            "__dup_dropped__": False,
            "__summary__": True,
        }

    # --- Address handling -----------------------------------------------------
    addr1_raw = src("Address_1")
    parsed = split_jammed_address(addr1_raw)
    address_1 = parsed["street"]
    if parsed["city"] or parsed["zip"]:
        flag("1 Address parsing", "fixed",
             "Split jammed address into street + city/ZIP")

    # #1 concatenation: leftover commas in the street portion suggest more than
    # one address fragment was jammed together.
    if address_1.count(",") >= 1:
        flag("1 Address parsing", "annotated",
             "Address_1 still contains a comma; possible concatenated fragments")

    # --- Address_2 ------------------------------------------------------------
    address_2 = src("Address_2")  # already sentinel-cleaned by clean_cell

    # #1 secondary-unit handling: a unit (apartment/suite/floor/etc.) embedded in
    # a jammed Address_1 is moved into Address_2 when Address_2 is otherwise
    # empty. If Address_2 is already populated, the unit is kept inline in
    # Address_1 so nothing is lost.
    parsed_unit = parsed.get("unit", "")
    if parsed_unit and not address_2:
        address_2 = parsed_unit
        flag("1 Address parsing", "fixed",
             "Moved secondary unit from the address into Address_2")
    elif parsed_unit and address_2:
        if _same_unit(parsed_unit, address_2):
            # The identical unit is recorded twice. Dropping the copy that is
            # jammed into the street loses nothing and lets the street geocode.
            flag("1 Address parsing", "fixed",
                 "The same unit appeared in the address and in Address_2; "
                 "kept it in Address_2 and cleaned it out of the street")
        elif _looks_like_unit(address_2):
            # Two different units for one person. Never pick one silently.
            address_1 = (address_1 + " " + parsed_unit).strip()
            flag("1 Address parsing", "segregated",
                 f"Unit conflict: the address says '{parsed_unit}' but "
                 f"Address_2 says '{address_2}'; confirm which is correct")
        else:
            # Address_2 holds something else, for example 'c/o Jane Doe'.
            # Nothing is overwritten and nothing is merged on a guess.
            address_1 = (address_1 + " " + parsed_unit).strip()
            # Address_2 is not echoed: it can hold a name ('c/o Jane Doe'),
            # and this message goes to the audit log, which never holds one.
            flag("1 Address parsing", "segregated",
                 f"The address contains the unit '{parsed_unit}' but Address_2 "
                 f"already holds something else; confirm where the unit belongs")

    # --- City resolution (alias -> canonical -> neighborhood -> fuzzy) --------
    city_source = src("City") or parsed["city"]
    city, note, city_err = normalize_city(city_source)
    if note:
        # A neighborhood remap is scenario #2; any other change is standardization.
        scen = "2 Geographic naming" if "neighborhood" in note else "2 Standardization"
        flag(scen, "fixed", note)
    needs_city = False
    needs_zip = False

    # #3 malformed "street" that is really a place name (e.g. "Cambria Heights
    # St"): no leading house number AND the leading words match a known
    # neighborhood/borough. These cannot be geocoded deterministically.
    if address_1 and not re.match(r"^\s*\d", address_1):
        head = re.sub(r"\b(st|ave|street|avenue|rd|road|blvd)\b\.?$", "",
                      address_1.strip(), flags=re.IGNORECASE).strip().lower()
        if head in NEIGHBORHOOD_TO_BOROUGH or head in (c.lower() for c in CANONICAL_CITIES):
            flag("3 Verification", "segregated",
                 "Address_1 looks like a place name, not a street address")

    # --- State ----------------------------------------------------------------
    state_source = src("State") or parsed["state"]
    state, note, state_err = normalize_state(state_source)
    if note:
        flag("2 Standardization", "fixed", note)
    if state_err:
        flag("3 Verification", "segregated", state_err)

    # --- ZIP: mapped column primary, address-embedded zip as fallback ---------
    # A missing/invalid ZIP is not failed here; the recovery decision is made
    # below, since the geocoder can often supply the ZIP from street + borough.
    zip5, note, zip_err = normalize_zip(src("Zip"), parsed["zip"])
    if note:
        flag("2 Standardization", "fixed", note)

    # --- Names ----------------------------------------------------------------
    first = normalize_name(src("First_Name"))
    last = normalize_name(src("Last_Name"))
    if required_of("First_Name") and not first:
        flag("3 Verification", "segregated", f"Missing {label_of('First_Name')}")
    if required_of("Last_Name") and not last:
        flag("3 Verification", "segregated", f"Missing {label_of('Last_Name')}")

    # #7 column-misalignment heuristic: a digit inside a name field usually means
    # the columns are shifted (an address or ID landed in a name column).
    if any(ch.isdigit() for ch in first) or any(ch.isdigit() for ch in last):
        flag("7 ETL artifact", "segregated",
             "Name field contains digits; possible column misalignment")

    # --- Middle initial -------------------------------------------------------
    mid, note = normalize_middle_initial(src("Middle_Initial"))
    if note:
        flag("2 Standardization", "fixed", note)

    # --- Required-field checks (schema-driven) --------------------------------
    if required_of("Client_ID") and not client_id:
        flag("3 Verification", "segregated", f"Missing {label_of('Client_ID')}")
    if required_of("Address_1") and not address_1:
        flag("3 Verification", "segregated", f"Missing {label_of('Address_1')}")

    # --- ZIP as the authority for City and State when they are missing --------
    # A valid NYC ZIP reliably identifies the borough and state, so we fill them
    # in when they are blank rather than sending the row for a manual check. This
    # only fills blanks; it never overwrites a City the source already provided.
    # A City that is present but disagrees with the ZIP is a conflict: the row is
    # routed to review showing BOTH values, and neither is silently chosen.
    zip_borough = borough_from_zip(zip5)
    city_from_zip = False
    if zip_borough:
        if city_err or not city:
            city = zip_borough
            city_err = None
            city_from_zip = True
            flag("2 Geographic naming", "fixed",
                 f"City set to '{zip_borough}' from ZIP {zip5}")
        elif city in CANONICAL_CITIES and city != zip_borough:
            raw_city = city_source
            entered = ("" if raw_city.lower() == city.lower()
                       else f" (entered as '{raw_city}')")
            flag("3 Verification", "segregated",
                 f"City/ZIP conflict: City says '{city}'{entered} but ZIP "
                 f"{zip5} is in {zip_borough}; confirm which is correct")
        if not state:
            state = "NY"
            flag("2 Standardization", "fixed", f"State set to 'NY' from ZIP {zip5}")

    # --- Finalize City and ZIP recovery decisions ----------------------------
    # City can be recovered by the geocoder when we have a street and a ZIP.
    # ZIP can be recovered when we have a street and a known borough. If both are
    # missing there is no anchor to geocode from, so both are failed.
    have_borough = city in CANONICAL_CITIES
    if city_err:
        if address_1 and zip5:
            needs_city = True            # geocoder may supply the borough
        else:
            flag("3 Verification", "segregated", city_err)
    if zip_err:
        if address_1 and have_borough:
            needs_zip = True             # geocoder may supply the ZIP
        else:
            flag("3 Verification", "segregated", zip_err)

    # --- Data-type and length checks for the built-in roles -------------------
    role_values = {
        "First_Name": first, "Middle_Initial": mid, "Last_Name": last,
        "Client_ID": client_id, "Address_1": address_1, "Address_2": address_2,
        "City": city, "State": state, "Zip": zip5,
    }
    for role, fld in by_role.items():
        _validate_field_value(fld, role_values.get(role, ""), flag)

    # A default that filled a blank built-in field is recorded once per field,
    # so the audit shows which values were supplied rather than read.
    for _role, _origin in defaults_used:
        _lbl = by_role.get(_role, {}).get("label", _role)
        _dv = (clean_cell(src_defaults.get(_role, "")) if _origin == "this source"
               else clean_cell(by_role.get(_role, {}).get("default", "")))
        flag("2 Standardization", "fixed",
             f"{_lbl} was blank, set to the default '{_dv}' from {_origin}")

    # --- Custom passthrough fields (cleaned + validated, no special logic) ----
    custom = {}
    for fld in schema:
        if fld["role"] != "custom":
            continue
        label = fld["label"]
        val = clean_cell(raw_row.get(mapping.get(label, ""), "")) if mapping.get(label) else ""
        # A default fills a blank; it never replaces a value the source gave.
        # One set for this source alone comes first, then the schema's.
        # Program is the field this matters most for: a file with no program
        # column gets the program the person named for it, on every row.
        src_default = clean_cell(src_defaults.get(label, ""))
        default = clean_cell(fld.get("default", ""))
        if not val and src_default:
            val = src_default
            flag("2 Standardization", "fixed",
                 f"{label} was blank, set to the default '{src_default}' from this source")
        elif not val and default:
            val = default
            flag("2 Standardization", "fixed",
                 f"{label} was blank, set to the default '{default}'")
        if fld.get("required") and not val:
            flag("3 Verification", "segregated", f"Missing {label}")
        _validate_field_value(fld, val, flag)
        # Store the value in its type's standard form, so a date written
        # 3/15/2024 in one export and 2024-03-15 in another end up identical.
        stored, _err = normalize_typed_value(fld, val)
        if stored != val:
            flag("2 Standardization", "fixed",
                 f"{label} was written in a standard form for its type")
        custom[label] = stored

    # Program / service-area value (used so two same-named people in different
    # programs are not treated as the same record). Detected from a custom field
    # whose label names a program or service area.
    program = ""
    program_label = ""
    for _lbl, _val in custom.items():
        _norm_lbl = re.sub(r"[^a-z0-9]", "", _lbl.lower())
        if _norm_lbl in ("program", "programname", "programtype", "programarea",
                         "servicearea", "service", "servicetype",
                         "servicename", "svc", "svcarea", "svctype",
                         "prog", "progname", "progtype", "activity",
                         "activityname", "enrollment", "enrollmenttype",
                         "projectname", "project", "servicecategory",
                         "programcategory"):
            program = clean_cell(_val)
            program_label = _lbl
            break
    if program and program_aliases:
        _canon = program_aliases.get(program)
        if _canon is None:
            _fold_map = {re.sub(r"[^a-z0-9]", "", k.lower()): v
                         for k, v in program_aliases.items()}
            _canon = _fold_map.get(re.sub(r"[^a-z0-9]", "", program.lower()))
        if _canon and _canon != program:
            flag("2 Standardization", "fixed",
                 f"Program '{program}' recorded as '{_canon}', the agreed name "
                 "for it")
            program = _canon
            # the output shows the agreed name, the same one every count uses;
            # the spelling the source used stays in the audit note above
            custom[program_label] = _canon

    # Person key for duplicate detection (scenario #9): normalized name + street
    # + unit + ZIP + program. Different units at the same building, or the same
    # name in different programs, do NOT collide. This key is used only to SHOW
    # possible duplicates; it never triggers an automatic merge.
    dup_key = "|".join([
        last.lower(), first.lower(), _norm_addr(address_1),
        _norm_addr(address_2), zip5, program.lower(),
    ]) if (last and first and address_1 and zip5) else ""

    # A rule the reviewer wrote may have marked this row as a duplicate of
    # another row in the same file. Flagged rows are kept and marked; where
    # the rule keeps the first, the others go to review so a person sees them.
    dup_in_file = clean_cell(raw_row.get("__dup_in_file__", ""))
    dup_drop = clean_cell(raw_row.get("__dup_drop__", ""))
    dup_fields = clean_cell(raw_row.get("__dup_fields__", ""))
    dup_keep = bool(clean_cell(raw_row.get("__dup_keep__", "")))
    if dup_in_file:
        if dup_drop:
            flag("4 Deduplication", "segregated",
                 f"Duplicate within file by your rule (matched on {dup_fields}), "
                 f"{dup_drop}; set aside")
        else:
            flag("4 Deduplication", "annotated",
                 f"Duplicate within file by your rule, group {dup_in_file}, "
                 f"matched on {dup_fields}; kept and marked")

    record = {
        "__dup_keep__": dup_keep,
        "__dup_dropped__": bool(dup_drop),
        "Duplicate_In_File": dup_in_file,
        "First_Name": first,
        "Middle_Initial": mid,
        "Last_Name": last,
        "Client_ID": client_id,
        "Address_1": address_1,
        "Address_2": address_2,
        "City": city,
        "State": state,
        "Zip": zip5,
        "__errors__": errors,
        "__flags__": flags,
        "__custom__": custom,
        "__program__": program,
        "__needs_city__": needs_city,
        "__city_err__": city_err,
        "__city_from_zip__": city_from_zip,
        "__needs_zip__": needs_zip,
        "__zip_err__": zip_err,
        "__dup_key__": dup_key,
        "__source_file__": source_file,
        "__source_row__": row_idx,
        "__original__": dict(raw_row),
    }
    return record


# ==============================================================================
#  SECTION 5.  OFFLINE GEOCODER + PRIVACY JITTER
# ==============================================================================

@st.cache_data(show_spinner=False)
def load_geocode_index(path: str):
    """
    Load the local geocoding reference file (read-only) into an in-memory index.

    The loader is tolerant about column names so it works with the city's real
    address-points export or the sample shipped alongside this app. It looks for:
        address column : one of address / addr / street / full_address / addr1
        zip column     : one of zip / zipcode / postal / postcode
        lat / lon      : one of lat/latitude , lon/lng/longitude
        city (optional): city / borough

    Returns (index, meta) where index maps zip -> list of
    (normalized_address, lat, lon, city). Returns (None, reason) if unavailable.
    """
    if not os.path.exists(path):
        return None, f"Reference file '{path}' not found in app directory."

    try:
        ref = pd.read_csv(path, dtype=str, keep_default_na=False)
    except Exception as exc:  # pragma: no cover
        return None, f"Could not read '{path}': {exc}"

    cols = {c.lower(): c for c in ref.columns}

    def pick(options):
        """The first candidate column present in the frame, if any."""
        for o in options:
            if o in cols:
                return cols[o]
        return None

    addr_col = pick(["address", "addr", "street", "full_address", "addr1"])
    zip_col = pick(["zip", "zipcode", "postal", "postcode"])
    lat_col = pick(["lat", "latitude"])
    lon_col = pick(["lon", "lng", "longitude"])
    city_col = pick(["city", "borough"])

    missing = [n for n, v in
               [("address", addr_col), ("zip", zip_col),
                ("lat", lat_col), ("lon", lon_col)] if v is None]
    if missing:
        return None, (
            f"Reference file is missing required column(s): {', '.join(missing)}."
        )

    index = defaultdict(list)
    for _, r in ref.iterrows():
        z = clean_cell(r[zip_col])[:5]
        a = _norm_addr(r[addr_col])
        try:
            lat = float(r[lat_col])
            lon = float(r[lon_col])
        except (TypeError, ValueError):
            continue
        city = clean_cell(r[city_col]) if city_col else ""
        if z and a:
            index[z].append((a, lat, lon, city))

    meta = {
        "rows": int(len(ref)),
        "zips": int(len(index)),
        "address_col": addr_col,
        "zip_col": zip_col,
    }
    return dict(index), meta


def _norm_addr(s: str) -> str:
    """Normalize an address for matching: lowercase, common abbreviations folded."""
    s = clean_cell(s).lower()
    s = re.sub(r"[.,]", " ", s)
    s = re.sub(r"\s+", " ", s).strip()
    # Fold a few very common street-type / directional variants so that
    # "w main st" and "west main street" compare closely.
    repl = {
        r"\bst\b": "street", r"\bave\b": "avenue", r"\brd\b": "road",
        r"\bblvd\b": "boulevard", r"\bdr\b": "drive", r"\bln\b": "lane",
        r"\bct\b": "court", r"\bpl\b": "place", r"\bapt\b": "apartment",
        r"\bste\b": "suite", r"\bw\b": "west", r"\be\b": "east",
        r"\bn\b": "north", r"\bs\b": "south",
    }
    for pat, rep in repl.items():
        s = re.sub(pat, rep, s)
    return re.sub(r"\s+", " ", s).strip()


def jitter_point(lat: float, lon: float, rng: random.Random):
    """
    Shift a coordinate by a random 150-250 ft in a random compass direction.
    Returns (new_lat, new_lon, distance_ft, bearing_deg).
    """
    distance_ft = rng.uniform(JITTER_MIN_FT, JITTER_MAX_FT)
    bearing = rng.uniform(0.0, 2.0 * math.pi)
    dlat = (distance_ft * math.cos(bearing)) / FEET_PER_DEG_LAT
    feet_per_deg_lon = FEET_PER_DEG_LAT * math.cos(math.radians(lat)) or 1e-9
    dlon = (distance_ft * math.sin(bearing)) / feet_per_deg_lon
    return (lat + dlat, lon + dlon, distance_ft, math.degrees(bearing) % 360)


def geocode_record(record: dict, index: dict, rng: random.Random):
    """
    Geocode one validated master record against the local index.

    Strategy: exact normalized match within the record's ZIP bucket first, then
    a fuzzy match (>= ADDRESS_FUZZ_THRESHOLD) within the same ZIP bucket.

    Returns (lat, lon, status, note, matched_city) where status is one of:
        'exact' | 'fuzzy' | 'no_zip_bucket' | 'no_match'
    On success the coordinates are the TRUE matched coordinates (jitter, if any,
    is applied later by the pipeline). matched_city carries the borough recorded
    in the gazetteer (used to backfill a missing City).
    """
    z = record["Zip"]
    target = _norm_addr(record["Address_1"])
    bucket = index.get(z)
    if not bucket:
        return None, None, "no_zip_bucket", "No reference points in this ZIP", ""

    # 1) exact normalized match
    for a, lat, lon, city in bucket:
        if a == target:
            return lat, lon, "exact", "exact match", city

    # 2) fuzzy match within ZIP bucket
    best = None
    best_city = ""
    best_score = -1
    for a, lat, lon, city in bucket:
        sc = _ratio(target, a)
        if sc > best_score:
            best_score, best, best_city = sc, (lat, lon), city
    if best and best_score >= ADDRESS_FUZZ_THRESHOLD:
        return (best[0], best[1], "fuzzy",
                f"fuzzy match {best_score}%", best_city)

    return None, None, "no_match", "Address could not be matched locally", ""


# ==============================================================================
#  SECTION 5b.  OFFLINE DISTRICT ASSIGNMENT  (scenario #6 / #12)
# ==============================================================================
# District mapping depends on a valid geocode. When a local GeoJSON of district
# boundaries is present, we assign State Senate / State Assembly / City Council
# districts by point-in-polygon, entirely offline. When it is absent, every row
# is annotated "districts unresolved" rather than failed, so the rest of the
# pipeline is unaffected.
#
# Expected GeoJSON: a FeatureCollection whose features carry properties naming
# the district. The loader is tolerant about property names and looks for keys
# containing 'senate', 'assembly', and 'council' (case-insensitive).

@st.cache_data(show_spinner=False)
def load_district_index(path: str):
    """Load district polygons from a local GeoJSON. Returns (features, meta) or (None, reason)."""
    if not os.path.exists(path):
        return None, f"District file '{path}' not found; districts will be left blank."
    try:
        with open(path, "r", encoding="utf-8") as fh:
            gj = json.load(fh)
    except Exception as exc:  # pragma: no cover
        return None, f"Could not read '{path}': {exc}"

    feats = gj.get("features", []) if isinstance(gj, dict) else []
    parsed = []
    for f in feats:
        props = {k.lower(): v for k, v in (f.get("properties") or {}).items()}

        def pick(keyword):
            """The first candidate column present in the frame, if any."""
            for k, v in props.items():
                if keyword in k:
                    return v
            return ""

        geom = f.get("geometry") or {}
        polys = _extract_polygons(geom)
        if not polys:
            continue
        parsed.append({
            "senate": pick("senate"),
            "assembly": pick("assembly"),
            "council": pick("council"),
            "polygons": polys,
        })
    if not parsed:
        return None, f"'{path}' contained no usable polygon features."
    return parsed, {"features": len(parsed)}


def _extract_polygons(geom):
    """Return a list of linear rings (each a list of (lon,lat)) for Polygon/MultiPolygon."""
    t = geom.get("type")
    coords = geom.get("coordinates")
    rings = []
    if t == "Polygon":
        for ring in coords:
            rings.append([(pt[0], pt[1]) for pt in ring])
    elif t == "MultiPolygon":
        for poly in coords:
            for ring in poly:
                rings.append([(pt[0], pt[1]) for pt in ring])
    return rings


def _point_in_ring(lon, lat, ring):
    """Standard ray-casting point-in-polygon test for a single ring."""
    inside = False
    n = len(ring)
    j = n - 1
    for i in range(n):
        xi, yi = ring[i]
        xj, yj = ring[j]
        if ((yi > lat) != (yj > lat)) and (
            lon < (xj - xi) * (lat - yi) / ((yj - yi) or 1e-12) + xi
        ):
            inside = not inside
        j = i
    return inside


def assign_districts(lat, lon, features):
    """Return {'senate','assembly','council'} for the first polygon containing the point."""
    for feat in features:
        for ring in feat["polygons"]:
            if _point_in_ring(lon, lat, ring):
                return {
                    "Senate_District": str(feat["senate"]),
                    "Assembly_District": str(feat["assembly"]),
                    "Council_District": str(feat["council"]),
                }
    return None


# ==============================================================================
#  SECTION 5c.  GEOSUPPORT (GDE) LOCAL BACKEND  (preferred when installed)
# ==============================================================================
# NYC Geosupport Desktop Edition is the city's official OFFLINE geocoder. When
# python-geosupport + GDE are installed on the machine, we use them as the
# primary backend: a single local call returns coordinates, the normalized
# borough, AND the political districts, with no network access. When GDE is not
# available the pipeline transparently falls back to the CSV gazetteer plus the
# GeoJSON point-in-polygon path.

# Canonical borough -> Geosupport 2-letter borough code.
BOROUGH_TO_GDE_CODE = {
    "New York": "MN", "Bronx": "BX", "Brooklyn": "BK",
    "Queens": "QN", "Staten Island": "SI",
}

# Descriptors that appear in Address_1 (e.g. "123 Main St Rear", "45 Oak Ave
# Front", "12 Elm St Gar") but are not part of the street and make Geosupport
# miss. We drop them from the Geosupport QUERY only; the stored Address_1 is left
# untouched. A negative lookahead keeps genuine street names such as "Front St"
# or "Front Street", where the word is followed by a street type.
_GDE_STREET_TYPES = (
    r"(?:st|street|ave|avenue|rd|road|blvd|boulevard|ln|lane|pl|place|dr|drive|"
    r"ct|court|ter|terrace|way|pkwy|parkway|hwy|highway|cir|circle|sq|square|"
    r"plz|plaza|aly|alley|row|walk|path|loop|run)"
)
_GDE_IGNORE_RE = re.compile(
    r"\b(?:rear|front|gar)\b\.?(?!\s+" + _GDE_STREET_TYPES + r"\b)",
    re.IGNORECASE,
)


def _strip_gde_ignore_words(street: str) -> str:
    """Remove 'rear'/'front'/'gar' descriptors for the Geosupport query only."""
    cleaned = _GDE_IGNORE_RE.sub(" ", street)
    return re.sub(r"\s+", " ", cleaned).strip().rstrip(",").strip()


# Catalog of optional Geosupport fields the user can append to the output,
# grouped for a tidy checkbox UI. Each entry is (label, match_keywords, exclude).
# The label is the output column header; keywords are matched (all must appear,
# case-insensitive) against Geosupport's returned key names, with exclude terms
# ruling out near-collisions. Latitude, Longitude and the three legislative
# districts are always included, so they are not repeated here.
GDE_FIELD_CATALOG = {
    "Coordinates": [
        ("State_Plane_X", ["x coordinate"], ["y"]),
        ("State_Plane_Y", ["y coordinate"], ["x"]),
    ],
    "Political districts": [
        ("Congressional_District", ["congressional"], []),
        ("Election_District", ["election district"], []),
        ("Civil_Court_District", ["civil court"], []),
    ],
    "Service districts": [
        ("Community_District", ["community district"], ["school"]),
        ("Community_School_District", ["community school"], []),
        ("Police_Precinct", ["police precinct"], []),
        ("Fire_Battalion", ["fire battalion"], []),
        ("Fire_Company", ["fire company"], []),
        ("Sanitation_District", ["sanitation district"], []),
        ("Health_Area", ["health area"], []),
        ("Health_Center_District", ["health center"], []),
    ],
    "Census (2020)": [
        ("Census_Tract", ["census tract"], []),
        ("Census_Block", ["census block"], []),
        ("NTA_Neighborhood", ["neighborhood tabulation"], []),
    ],
    "Property identifiers": [
        ("BBL_Borough_Block_Lot", ["borough block lot"], []),
        ("BIN_Building_ID", ["building identification"], []),
    ],
}


def _gde_value(result: dict, keywords, exclude=()):
    """Find the first Geosupport value whose key contains all keywords and none of exclude."""
    for k, v in result.items():
        if not isinstance(k, str):
            continue
        kl = k.lower()
        if all(w in kl for w in keywords) and not any(x in kl for x in exclude):
            val = "" if v is None else str(v).strip()
            if val:
                return val
    return ""


def extract_gde_extras(result: dict, selected_labels):
    """Pull the user-selected optional Geosupport fields out of a result dict."""
    if not selected_labels:
        return {}
    wanted = set(selected_labels)
    out = {}
    for _cat, fields in GDE_FIELD_CATALOG.items():
        for label, kw, ex in fields:
            if label in wanted:
                out[label] = _gde_value(result, kw, ex)
    return out


@st.cache_resource(show_spinner=False)
def load_geosupport():
    """
    Instantiate a local Geosupport engine. Returns (engine, meta) or (None, reason).
    Cached as a resource because the engine is a live handle to the local library,
    not serialisable data. No network access occurs here or in any call.
    """
    try:
        from geosupport import Geosupport
    except Exception:
        return None, "python-geosupport is not installed."
    try:
        g = Geosupport()
        # Smoke-test a known address so we fail fast if GDE is misconfigured.
        g.address(house_number=125, street_name="Worth St", borough_code="MN")
        return g, {"backend": "Geosupport Desktop Edition (local)"}
    except Exception as exc:  # pragma: no cover - environment dependent
        return None, f"Geosupport is installed but not usable: {exc}"


def _split_house_street(address_1: str):
    """
    Split a street address into (house_number, street_name) for Geosupport input.
    Handles Queens-style hyphenated house numbers (e.g. '42-09') and strips any
    trailing unit designator, which Geosupport does not want in the street name.
    Returns ('', '') when a house number cannot be identified.
    """
    a = clean_cell(address_1)
    m = re.match(r"^\s*(\d+[A-Za-z]?(?:-\d+[A-Za-z]?)?)\s+(.*)$", a)
    if not m:
        return "", ""
    house = m.group(1).strip()
    street = m.group(2).strip()
    # Remove a trailing unit (Apt/Suite/Unit/Fl/Room/#...) from the street name.
    street = re.sub(
        r"\b(apt|apartment|suite|ste|unit|fl|floor|rm|room|#)\b.*$", "",
        street, flags=re.IGNORECASE,
    ).strip()
    return house, street


def _extract_geosupport_fields(result: dict):
    """
    Pull the fields we need out of a Geosupport result dict, tolerant of the
    exact key names across GDE versions. Returns a dict with lat, lon, borough
    (canonical), and the three district numbers (any of which may be '').
    """
    lat = lon = ""
    borough = ""
    zipc = ""
    grc = ""
    senate = assembly = council = ""
    for k, v in result.items():
        if not isinstance(k, str):
            continue
        kl = k.lower()
        val = "" if v is None else str(v).strip()
        if not val:
            continue
        if lat == "" and "latitude" in kl:
            lat = val
        elif lon == "" and "longitude" in kl:
            lon = val
        elif borough == "" and "borough name" in kl and "code" not in kl:
            borough = val
        elif zipc == "" and ("zip code" in kl or (("zip" in kl or "postal" in kl)
                                                  and "+4" not in kl)):
            zipc = val
        elif grc == "" and ("return code" in kl or kl.strip() in ("grc", "grc 1")):
            grc = val
        elif senate == "" and "senat" in kl:
            senate = val
        elif assembly == "" and "assembly" in kl:
            assembly = val
        elif council == "" and "council" in kl:
            council = val
    # Normalize the GDE borough (e.g. 'MANHATTAN') to our canonical City value.
    if borough:
        borough = CITY_ALIASES.get(borough.lower(), borough.title())
    # Keep only the 5-digit ZIP.
    mzip = re.match(r"(\d{5})", zipc)
    zipc = mzip.group(1) if mzip else ""
    return {
        "lat": lat, "lon": lon, "borough": borough, "zip": zipc, "grc": grc,
        "senate": senate, "assembly": assembly, "council": council,
    }


def _confidence_from_grc(grc: str) -> str:
    """Map a Geosupport Return Code to a confidence label. 00 is an exact match,
    01 is a match with a minor correction or warning, anything else is weaker."""
    g = (grc or "").strip()
    if g in ("", "00", "0"):
        return "High"
    if g in ("01", "1"):
        return "Medium"
    return "Low"


def geocode_with_gde(record: dict, g, rng: random.Random, extra_fields=None):
    """
    Geocode one record with Geosupport. Returns a 9-tuple:
        (lat, lon, status, note, matched_city, matched_zip, districts, extras,
         confidence)
    Coordinates are the TRUE matched coordinates (jitter, if any, is applied later
    by the pipeline). `confidence` is High, Medium, or Low from the Geosupport
    return code. status is 'exact' on success, 'no_match' otherwise.
    """
    try:
        from geosupport import GeosupportError
    except Exception:
        class GeosupportError(Exception):
            """Raised when Geosupport is asked for and cannot be reached or set up."""
            pass

    house, street = _split_house_street(record["Address_1"])
    if not house or not street:
        return None, None, "no_match", \
            "Address could not be parsed for Geosupport", "", "", None, {}, ""

    # Ignore 'rear'/'front'/'gar' descriptors for the Geosupport lookup only.
    street = _strip_gde_ignore_words(street) or street

    kwargs = {"house_number": house, "street_name": street}
    if record["City"] in BOROUGH_TO_GDE_CODE:
        kwargs["borough_code"] = BOROUGH_TO_GDE_CODE[record["City"]]
    elif record["Zip"]:
        kwargs["zip_code"] = record["Zip"]

    try:
        res = g.address(**kwargs)
    except GeosupportError:
        return None, None, "no_match", \
            "Address could not be matched locally (Geosupport)", "", "", None, {}, ""
    except Exception as exc:  # pragma: no cover
        return None, None, "no_match", f"Geosupport error: {exc}", "", "", None, {}, ""

    f = _extract_geosupport_fields(res)
    try:
        lat = float(f["lat"])
        lon = float(f["lon"])
    except (TypeError, ValueError):
        return None, None, "no_match", \
            "Geosupport returned no coordinates for this address", "", "", None, {}, ""

    districts = None
    if f["senate"] or f["assembly"] or f["council"]:
        districts = {
            "Senate_District": f["senate"],
            "Assembly_District": f["assembly"],
            "Council_District": f["council"],
        }
    extras = extract_gde_extras(res, extra_fields)
    confidence = _confidence_from_grc(f.get("grc", ""))
    return (lat, lon, "exact", "Geosupport match", f["borough"], f["zip"],
            districts, extras, confidence)


# ==============================================================================
#  SECTION 6.  PIPELINE DRIVER
# ==============================================================================

def run_pipeline(file_frames, file_mappings, require_geocode, geocode_index,
                 jitter_seed, district_index=None, gde=None, schema=None,
                 gde_extra_fields=None, jitter_enabled=True,
                 corrections_meta=None, source_defaults=None,
                 program_aliases=None, progress=None):
    """
    Execute the full transform -> validate -> dedupe -> geocode -> district ->
    verify pipeline across all files.

    Returns a dict of results for the dashboard / exports.
    """
    schema = schema or DEFAULT_SCHEMA
    audit = AuditLog()
    rng = random.Random(jitter_seed)  # deterministic jitter for reproducibility

    def pflag(r, scenario, action, message):
        """Pipeline-level flag: annotate a record, audit it, segregate if needed."""
        r.setdefault("__flags__", []).append(
            {"scenario": scenario, "action": action, "message": message})
        audit.add(r["__source_file__"], r["__source_row__"],
                  r.get("Client_ID", ""), f"[{scenario} | {action}] {message}")
        if action == "segregated":
            r["__errors__"].append(message)

    def _tick(done, total, phase, file_name="", file_index=0, file_count=0):
        if progress:
            try:
                progress(done, total, phase, file_name, file_index, file_count)
            except Exception:
                pass

    total_rows = sum(len(df) for df in file_frames.values()) or 1
    done_rows = 0
    file_count = len(file_frames)

    transformed = []   # all master records (clean + error) with bookkeeping
    for fi, (fname, df) in enumerate(file_frames.items(), start=1):
        mapping = file_mappings[fname]
        short = str(fname).split(" :: ")[0]
        _tick(done_rows, total_rows, "Cleaning and checking", short, fi, file_count)
        for idx, raw_row in df.iterrows():
            done_rows += 1
            if done_rows % 500 == 0:
                _tick(done_rows, total_rows, "Cleaning and checking", short, fi, file_count)
            rec = transform_row(dict(raw_row), mapping, fname, int(idx), audit,
                                schema, (source_defaults or {}).get(fname),
                                program_aliases)
            transformed.append(rec)
            # A row whose values were replaced from a re-imported corrections
            # file carries a visible, audited note. Column names only, never the
            # values, so the audit stays PII-safe.
            meta = (corrections_meta or {}).get((fname, int(idx)))
            if meta:
                corr_from, corr_cols = meta
                pflag(rec, "15 Corrections", "annotated",
                      f"Values replaced from corrections file '{corr_from}' "
                      f"(columns: {', '.join(corr_cols)}); re-validated like any "
                      "other row")

    _tick(total_rows, total_rows, "Checking for duplicates", "", 0, file_count)
    # ---- Duplicate handling (scenario #9) -----------------------------------
    # Two tiers, by design:
    #   1. CONFIRMED duplicate: the SAME non-blank Client ID on records that are
    #      otherwise identical (same name, address, ZIP, program). Only this case
    #      is treated as a true duplicate; the first is kept and the rest are
    #      segregated. This is the only automatic de-duplication, and it requires
    #      a 100% match, never fuzzy logic.
    #   2. POSSIBLE duplicate: records that share the person key (name + address
    #      + ZIP + program) but are NOT a confirmed ID match. These are SHOWN
    #      (marked with a group label and flagged) but never merged or removed;
    #      a human confirms them.
    for r in transformed:
        r["Possible_Duplicate"] = ""
        r.setdefault("Duplicate_In_File", "")

    # Tier 1: same Client ID.
    id_groups = defaultdict(list)
    for r in transformed:
        if r["Client_ID"]:
            id_groups[r["Client_ID"]].append(r)
    confirmed = set()
    for cid, members in id_groups.items():
        if len(members) < 2:
            continue
        person_keys = {r["__dup_key__"] for r in members}
        if len(person_keys) == 1 and members[0]["__dup_key__"]:
            # Identical records sharing one Client ID: safe to de-duplicate.
            pflag(members[0], "9 Duplicate", "annotated",
                  f"Confirmed duplicate group of {len(members)} (identical record, "
                  f"same Client ID); keeping one")
            for dup in members[1:]:
                confirmed.add(id(dup))
                pflag(dup, "9 Duplicate", "segregated",
                      "Confirmed duplicate: identical record with the same Client ID")
        else:
            # Same Client ID on records with DIFFERENT data: an integrity problem,
            # not a safe merge. Flag every member for review.
            for r in members:
                pflag(r, "9 Duplicate", "segregated",
                      f"Same Client ID '{cid}' used by records with different "
                      f"data; review required (not merged)")

    # Tier 2: possible duplicates by person key (shown, never merged). A row a
    # reviewer's decision set aside is out of the batch and takes no part. A
    # pair inside one file that the reviewer said are different people is
    # settled and is not paired again; the same rows may still match a row in
    # another file, which is a different question.
    person_groups = defaultdict(list)
    for r in transformed:
        if r["__dup_key__"] and id(r) not in confirmed \
                and not r.get("__dup_dropped__"):
            person_groups[r["__dup_key__"]].append(r)
    group_num = 0
    for key, members in person_groups.items():
        if len(members) < 2:
            continue
        # Rows from one file are the reviewer's to decide on Tidy up, where
        # they are shown side by side. This check only pairs rows that come
        # from different files, which is the crosswalk question.
        if len({r["__source_file__"] for r in members}) == 1:
            continue
        # If every member already shares one Client ID they were handled above.
        ids = {r["Client_ID"] for r in members if r["Client_ID"]}
        if len(ids) == 1 and all(r["Client_ID"] for r in members):
            continue
        group_num += 1
        label = f"Group {group_num}"
        for r in members:
            r["Possible_Duplicate"] = label
            pflag(r, "9 Duplicate", "annotated",
                  f"Possible duplicate ({label}, {len(members)} records with "
                  f"matching name/address/ZIP/program); not merged, confirm manually")


    # ---- Geocoding pass (only for rows that passed validation) ---------------
    geocode_available = (geocode_index is not None) or (gde is not None)
    district_available = (district_index is not None) or (gde is not None)
    backend = "Geosupport" if gde is not None else "gazetteer"
    geo_done = 0
    last_file = None
    file_pos = 0
    for r in transformed:
        geo_done += 1
        if r["__source_file__"] != last_file:
            last_file = r["__source_file__"]
            file_pos += 1
            _tick(geo_done, total_rows, "Finding locations",
                  str(last_file).split(" :: ")[0], file_pos, file_count)
        elif geo_done % 500 == 0:
            _tick(geo_done, total_rows, "Finding locations",
                  str(last_file).split(" :: ")[0], file_pos, file_count)
        r["Latitude"] = ""
        r["Longitude"] = ""
        r["Geocode_Confidence"] = ""
        r["Senate_District"] = ""
        r["Assembly_District"] = ""
        r["Council_District"] = ""
        r["__gde_extra__"] = {}
        r["__geo_status__"] = "skipped"
        if r["__errors__"]:
            continue  # never geocode an invalid row
        if not geocode_available:
            r["__geo_status__"] = "skipped_no_reference"
            if r.get("__needs_city__"):
                pflag(r, "3 Verification", "segregated", r["__city_err__"])
            if r.get("__needs_zip__"):
                pflag(r, "3 Verification", "segregated", r["__zip_err__"])
            continue

        # Dispatch to the preferred backend. Geosupport returns districts and a
        # ZIP inline; the gazetteer path returns districts=None and no ZIP. Both
        # return the TRUE coordinates; jitter (if enabled) is applied below.
        if gde is not None:
            (tlat, tlon, status, note, matched_city, matched_zip, gde_districts,
             gde_extras, confidence) = geocode_with_gde(r, gde, rng, gde_extra_fields)
        else:
            tlat, tlon, status, note, matched_city = geocode_record(
                r, geocode_index, rng
            )
            matched_zip = ""
            gde_districts = None
            gde_extras = {}
            confidence = "High" if status == "exact" else (
                "Low" if status == "fuzzy" else "")

        r["__geo_status__"] = status
        if status in ("exact", "fuzzy"):
            # Stored coordinates: jittered for privacy when enabled, otherwise the
            # true point. Districts are always assigned from the TRUE point below.
            if jitter_enabled:
                slat, slon, jdist, _b = jitter_point(tlat, tlon, rng)
                geo_note = f"{note}; jittered {jdist:.0f} ft"
            else:
                slat, slon = tlat, tlon
                geo_note = f"{note}; exact coordinates (no jitter)"
            r["Latitude"] = f"{slat:.6f}"
            r["Longitude"] = f"{slon:.6f}"
            r["Geocode_Confidence"] = confidence
            r["__gde_extra__"] = gde_extras
            audit.add(r["__source_file__"], r["__source_row__"],
                      r["Client_ID"],
                      f"[12 Geolocation | fixed] Geocoded via {backend} "
                      f"({geo_note}; confidence {confidence})")
            # #3 borough consistency: if the row asserted a City but the backend
            # places it in a different borough, flag the mismatch. A City that was
            # derived from the ZIP is authoritative over the CSV gazetteer, so only
            # the authoritative Geosupport engine may contradict it.
            if matched_city and not r.get("__needs_city__") and r["City"] \
                    and matched_city != r["City"] \
                    and not (r.get("__city_from_zip__") and backend != "Geosupport"):
                pflag(r, "3 Verification", "segregated",
                      f"City/geocode mismatch: row says {r['City']}, "
                      f"{backend} says {matched_city}")
            # Backfill a missing City from the geocoder's borough, if available.
            if r.get("__needs_city__"):
                if matched_city:
                    r["City"] = matched_city
                    pflag(r, "2 Geographic naming", "fixed",
                          f"Backfilled City '{matched_city}' from {backend}")
                else:
                    pflag(r, "3 Verification", "segregated", r["__city_err__"])
            # Backfill a missing ZIP from the geocoder, if available.
            if r.get("__needs_zip__"):
                if matched_zip:
                    r["Zip"] = matched_zip
                    pflag(r, "2 Standardization", "fixed",
                          f"Backfilled ZIP '{matched_zip}' from {backend}")
                else:
                    pflag(r, "3 Verification", "segregated", r["__zip_err__"])
            # ---- District assignment (scenario #6 / #12) --------------------
            if not r["__errors__"]:
                if gde_districts is not None:
                    r.update(gde_districts)
                    pflag(r, "6 District mapping", "fixed",
                          f"Assigned by Geosupport: Senate "
                          f"{gde_districts['Senate_District']}, Assembly "
                          f"{gde_districts['Assembly_District']}, Council "
                          f"{gde_districts['Council_District']}")
                elif district_index is not None:
                    d = assign_districts(tlat, tlon, district_index)
                    if d:
                        r.update(d)
                        pflag(r, "6 District mapping", "fixed",
                              f"Assigned Senate {d['Senate_District']}, "
                              f"Assembly {d['Assembly_District']}, "
                              f"Council {d['Council_District']}")
                    else:
                        pflag(r, "6 District mapping", "annotated",
                              "Point fell outside all district polygons")
                else:
                    pflag(r, "6 District mapping", "annotated",
                          "Districts unresolved (no boundary file loaded)")
        else:
            if r.get("__needs_city__"):
                pflag(r, "3 Verification", "segregated", r["__city_err__"])
            if r.get("__needs_zip__"):
                pflag(r, "3 Verification", "segregated", r["__zip_err__"])
            if not r.get("__needs_city__") and not r.get("__needs_zip__") \
                    and require_geocode and geocode_available:
                pflag(r, "12 Geolocation", "segregated", note)

    # ---- Verification status + split into clean vs review -------------------
    clean_rows, review_rows = [], []
    for r in transformed:
        if r["__errors__"]:
            r["Verification_Status"] = V_REVIEW
        elif r["__geo_status__"] in ("exact", "fuzzy"):
            # A weak or fuzzy match is not labeled as fully verified.
            conf = r.get("Geocode_Confidence", "")
            if r["__geo_status__"] == "fuzzy" or conf == "Low":
                r["Verification_Status"] = V_LOWCONF
            else:
                r["Verification_Status"] = V_VERIFIED
        else:
            r["Verification_Status"] = V_UNVERIFIED
        (clean_rows if not r["__errors__"] else review_rows).append(r)

    # ---- Per-file quality + PII report (scenario #5 / #11 / #13) ------------
    quality = _build_quality(transformed, file_mappings)
    for q in quality:
        pii = "PII (names present)" if q["carries_pii"] else "de-identified"
        audit.add(q["file"], -1, "<file>",
                  f"[13 PII | annotated] File classified: {pii}")
        audit.add(q["file"], -1, "<file>",
                  f"[5 Quality | annotated] {q['clean']}/{q['total']} clean "
                  f"({q['clean_rate']:.0f}%); top issue: {q['top_issue']}")

    return {
        "transformed": transformed,
        "clean": clean_rows,
        "review": review_rows,
        "audit": audit,
        "geocode_available": geocode_available,
        "district_available": district_available,
        "quality": quality,
        "schema": schema,
    }


def _build_quality(transformed, file_mappings):
    """Per-file quality metrics: clean rate, top failure reason, PII presence."""
    per_file = defaultdict(list)
    for r in transformed:
        per_file[r["__source_file__"]].append(r)
    out = []
    for fname, rows in per_file.items():
        total = len(rows)
        clean = sum(1 for r in rows if not r["__errors__"])
        reasons = defaultdict(int)
        for r in rows:
            for e in r["__errors__"]:
                reasons[re.split(r":|across merge", e)[0].strip()] += 1
        top = max(reasons.items(), key=lambda kv: kv[1])[0] if reasons else "none"
        mapping = file_mappings.get(fname, {})
        carries_pii = bool(mapping.get("First_Name") or mapping.get("Last_Name"))
        out.append({
            "file": fname,
            "total": total,
            "clean": clean,
            "review": total - clean,
            "clean_rate": (clean / total * 100) if total else 0,
            "top_issue": top,
            "carries_pii": carries_pii,
        })
    return out


# ==============================================================================
#  SECTION 7.  EXPORT BUILDERS  (in-memory strings only)
# ==============================================================================

def clean_rows_to_dataframe(clean_rows, schema=None, include_enrichment=True,
                            columns=None) -> pd.DataFrame:
    """
    Build the clean-export DataFrame using the active schema's LABELS as headers.
    Known roles pull from the record; custom fields pull from __custom__.
    Enrichment columns (coordinates, verification, districts, lineage) are
    appended unless disabled. `columns`, if given, filters/orders the output.
    """
    schema = schema or DEFAULT_SCHEMA
    field_cols = [f["label"] for f in schema]
    enrich = ENRICHMENT_COLUMNS if include_enrichment else []
    # Optional Geosupport fields the user appended (union across rows, stable order).
    extra_cols, seen_extra = [], set()
    for r in clean_rows:
        for k in r.get("__gde_extra__", {}):
            if k not in seen_extra:
                seen_extra.add(k)
                extra_cols.append(k)
    all_cols = field_cols + [c for c in enrich if c not in field_cols] + \
        [c for c in extra_cols if c not in field_cols and c not in enrich]
    if columns is not None:
        all_cols = [c for c in all_cols if c in columns]

    rows = []
    for r in clean_rows:
        row = {}
        for f in schema:
            label, role = f["label"], f["role"]
            row[label] = (r.get("__custom__", {}).get(label, "")
                          if role == "custom" else r.get(role, ""))
        for c in enrich:
            if c == "Source_File":
                row.setdefault(c, r["__source_file__"])
            elif c == "Source_Row":
                row.setdefault(c, r["__source_row__"])
            else:
                row.setdefault(c, r.get(c, ""))
        for k, v in r.get("__gde_extra__", {}).items():
            row.setdefault(k, v)
        rows.append(row)

    if not rows:
        return pd.DataFrame(columns=all_cols)
    df = pd.DataFrame(rows)
    existing = [c for c in all_cols if c in df.columns]
    return df[existing]


def review_rows_to_dataframe(review_rows) -> pd.DataFrame:
    """Build the manual-review DataFrame: provenance, reason, flags, original data."""
    if not review_rows:
        return pd.DataFrame(
            columns=["Source_File", "Source_Row", "Error_Reason", "Scenario_Flags"]
        )
    rows = []
    for r in review_rows:
        base = {
            "Source_File": r["__source_file__"],
            "Source_Row": r["__source_row__"],
            "Error_Reason": "; ".join(r["__errors__"]),
            "Scenario_Flags": "; ".join(
                sorted({f["scenario"] for f in r.get("__flags__", [])})
            ),
        }
        for k, v in r["__original__"].items():
            if str(k).startswith("__"):
                continue   # working columns the tool added, not the source's
            base[f"orig::{k}"] = v
        rows.append(base)
    df = pd.DataFrame(rows)
    lead = ["Source_File", "Source_Row", "Error_Reason", "Scenario_Flags"]
    ordered = lead + [c for c in df.columns if c not in lead]
    return df[ordered]


# Export formats offered to the user.
EXPORT_FORMATS = ["CSV (.csv)", "Excel (.xlsx)", "JSON (.json)"]


def serialize_output(df: pd.DataFrame, fmt: str):
    """Serialize a DataFrame to the chosen format. Returns (data, mime, extension)."""
    if fmt.startswith("Excel"):
        buf = io.BytesIO()
        with pd.ExcelWriter(buf, engine="openpyxl") as writer:
            df.to_excel(writer, index=False, sheet_name="Data")
        return (buf.getvalue(),
                "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                "xlsx")
    if fmt.startswith("JSON"):
        return df.to_json(orient="records", indent=2), "application/json", "json"
    return df.to_csv(index=False), "text/csv", "csv"


def build_clean_csv(clean_rows, schema=None) -> str:
    """Backward-compatible CSV string of the clean export (used by tests)."""
    return clean_rows_to_dataframe(clean_rows, schema).to_csv(index=False)


def build_review_csv(review_rows) -> str:
    """Backward-compatible CSV string of the manual-review export."""
    return review_rows_to_dataframe(review_rows).to_csv(index=False)


def build_quality_csv(quality) -> str:
    """Per-file data-quality report (scenario #5 / #11 / #13)."""
    cols = ["file", "total", "clean", "review", "clean_rate", "top_issue",
            "carries_pii"]
    if not quality:
        return pd.DataFrame(columns=cols).to_csv(index=False)
    df = pd.DataFrame(quality)[cols].copy()
    df["clean_rate"] = df["clean_rate"].map(lambda x: f"{x:.1f}%")
    df = df.rename(columns={
        "file": "Source_File", "total": "Total_Rows", "clean": "Clean_Rows",
        "review": "Review_Rows", "clean_rate": "Clean_Rate",
        "top_issue": "Top_Issue", "carries_pii": "Carries_PII",
    })
    return df.to_csv(index=False)


# ==============================================================================
#  SECTION 8.  STREAMLIT USER INTERFACE
# ==============================================================================

def guess_mapping(columns):
    """
    Heuristic auto-mapping so the dropdowns start on sensible defaults.

    Three rules make this safe.

    A column the source actually provides beats a column a prepare step made
    from another one. Splitting "Address Line 1" produces an "_zip" column, but
    if the file also has a real "Zip" column, that one is the ZIP: the derived
    one is only filled where a ZIP happened to be jammed into the street, and
    is blank everywhere else. Preferring it once sent every ZIP in a file to
    review as missing.

    The exception is the street itself: the derived "_street" beats the jammed
    column it was split from, because the jammed column still holds the unit
    and city and would defeat the split.

    Matching is exact, then whole-token; a raw substring test is deliberately
    not used, because it matched 'id' inside 'Name_middle'. A column named as an
    identifier or code is never taken as the program, because a program count
    needs names, not numbers.
    """
    cols = [str(c) for c in columns]
    lowered = {c.lower(): c for c in cols}
    derived_cols = {c for c in cols if re.search(
        r"_(street|address2|city|state|zip|first|middle|last|mi)$", c.lower())}

    def toks(name):
        """The words in a column name, lower case."""
        return [t for t in re.split(r"[^a-z0-9]+", str(name).lower()) if t]

    def has_run(hay, needle):
        """Whether one word list appears inside another, in order."""
        if not needle or len(needle) > len(hay):
            return False
        return any(hay[i:i + len(needle)] == needle
                   for i in range(len(hay) - len(needle) + 1))

    def derived(suffix):
        """The column a tidy-up step made for this role, if any."""
        for lc, orig in lowered.items():
            if lc.endswith(suffix):
                return orig
        return ""

    def find(*candidates, skip_derived=True, avoid_tokens=()):
        """A column the source provides, by exact name then by whole token."""
        pool = [(lc, o) for lc, o in lowered.items()
                if not (skip_derived and o in derived_cols)]
        avoid = set(avoid_tokens)
        for cand in candidates:                      # exact name
            for lc, orig in pool:
                if lc == cand and not (avoid & set(toks(lc))):
                    return orig
        for cand in candidates:                      # whole-token match
            ct = toks(cand)
            for lc, orig in pool:
                if has_run(toks(lc), ct) and not (avoid & set(toks(lc))):
                    return orig
        return ""

    def real_or_derived(suffix, *candidates):
        """The source's own column when it has one, else the derived one."""
        return find(*candidates) or derived(suffix)

    id_words = ("id", "identifier", "code", "number", "num", "no", "key", "uid")

    return {
        "First_Name": derived("_first") or find(
            "first_name", "f_name", "firstname", "first", "givenname", "given"),
        "Middle_Initial": derived("_middle") or derived("_mi") or find(
            "middle_initial", "m_name", "mi", "middle"),
        "Last_Name": derived("_last") or find(
            "last_name", "l_name", "lastname", "last", "familyname", "family"),
        "Client_ID": find("eto_client_id", "client_id", "ehr_id",
                          "patientnumber", "patient_number", "system_id",
                          "uid", "pid", "id"),
        # the split street beats the jammed column it came from
        "Address_1": derived("_street") or find(
            "address_1", "addr1", "address_line", "street", "full_address",
            "address"),
        "Address_2": real_or_derived("_address2",
                                     "address_2", "addr2", "apt", "unit", "suite"),
        # a real City, State or Zip column beats one made by a split
        "City": real_or_derived("_city", "city", "location.city", "borough"),
        "State": real_or_derived("_state", "state", "st"),
        # a ZIP the person calculated from the address is chosen on purpose
        "Zip": find("zip_calculated", skip_derived=False)
               or real_or_derived("_zip", "zip", "zipcode", "zip_code",
                                  "location.zip", "postal", "postalcode"),
        # a program is a name; a column named as an identifier is not it
        "Program": find("program_name", "programname", "program", "program_type",
                        "program_area", "service_area", "svc_area",
                        "service_type", "svc_type", "service", "svc",
                        "activity", "activity_name", "enrollment_type",
                        "project_name", "service_category", "program_category",
                        "prog", "prog_name", avoid_tokens=id_words),
    }


def auto_prep_ops(df):
    """
    Detect common staging needs: a jammed address column and a jammed full-name
    column. Returns an ordered list of prep operations to apply automatically.

    An address is treated as jammed when it carries more than a street: a
    trailing ZIP, an embedded unit such as Apt 3L, or a city and state tacked on
    the end. Detecting only trailing ZIPs missed the very common case of a unit
    jammed into the street with the ZIP held in its own column.

    A name column is only split when it names a PERSON. Headers such as
    "Program name" or "Site name" are deliberately left alone.
    """
    ops = []
    already_split = {"first_name", "last_name", "firstname", "lastname", "f_name",
                     "l_name", "given", "givenname", "family", "familyname",
                     "surname", "middle_initial", "mi"}

    # Words that mean a "name" column names a thing, not a person.
    not_a_person = {
        "program", "service", "site", "org", "organization", "agency",
        "provider", "company", "business", "school", "project", "event",
        "file", "report", "group", "team", "department", "dept", "location",
        "facility", "vendor", "funder", "grant", "contract", "activity",
        "class", "course", "product", "type", "category", "status", "office",
        "borough", "city", "county", "district", "region", "table", "sheet",
        "form", "field", "column", "fund", "unit", "center", "clinic",
        "hospital", "shelter", "building", "property", "landlord", "employer",
    }

    unit_re = (r"(?i)(?:^|[\s,])(?:apt|apartment|ste|suite|unit|fl|floor|rm|room|"
               r"bldg|building|ph|penthouse|bsmt|basement|lobby|mezzanine|rear|"
               r"front|#)\s*[\w\-]*")
    state_re = r"(?i)(?:^|[\s,])(?:NY|N\.Y\.|New York)\s*(?:\d{5}|$)"

    def _tokens(name):
        return [t for t in re.split(r"[^a-z0-9]+", str(name).lower()) if t]

    # ---- jammed address ----------------------------------------------------
    # A column that IS the unit line, such as Address 2 holding "Apt 7D" on
    # every row, contains unit words but is not a jammed address, and splitting
    # it produces an empty street. Both its name and its values are checked.
    unit_col_names = {"address_2", "address2", "addr2", "apt", "apartment",
                      "unit", "suite", "floor", "address_line_2", "addressline2"}
    has_unit_col = any(re.sub(r"[^a-z0-9]", "", str(c).lower())
                       in {n.replace("_", "") for n in unit_col_names}
                       for c in df.columns)

    best_addr, best_score, best_why = None, 0.0, ""
    for c in df.columns:
        if re.sub(r"[^a-z0-9]", "", str(c).lower()) in \
                {n.replace("_", "") for n in unit_col_names}:
            continue
        vals = df[c].astype(str)
        nonempty = vals[vals.str.strip() != ""]
        if len(nonempty) == 0:
            continue
        looks_addr = (float(nonempty.str.contains(r"\d").mean()) > 0.5 and
                      float(nonempty.str.contains(r"[A-Za-z]").mean()) > 0.5)
        if not looks_addr:
            continue
        # values that are only a unit, with no street before it, are the unit
        # line rather than a jammed address
        only_unit = float(nonempty.str.match(
            r"(?i)^\s*(?:#|" + unit_re.split("(?:")[1].split(")")[0] + r")\b").mean())
        has_street = float(nonempty.str.match(r"^\s*\d+[\w-]*\s+\S").mean())
        if only_unit > 0.6 and has_street < 0.3:
            continue
        zip_frac = float(nonempty.str.contains(r"\d{5}\s*$", regex=True).mean())
        unit_frac = float(nonempty.str.contains(unit_re, regex=True).mean())
        state_frac = float(nonempty.str.contains(state_re, regex=True).mean())
        comma_frac = float(nonempty.str.contains(",").mean())

        reasons = []
        if zip_frac > 0.30:
            reasons.append(f"{zip_frac * 100:.0f}% end in a ZIP")
        # When the file has its own unit column, a unit in the street is
        # compared with it during processing, where a disagreement is caught.
        # Splitting it out here would drop one of the two without a word.
        if unit_frac > 0.15 and not (has_unit_col and zip_frac <= 0.30
                                     and state_frac <= 0.30):
            reasons.append(f"{unit_frac * 100:.0f}% carry a unit such as Apt or Fl")
        if state_frac > 0.30:
            reasons.append(f"{state_frac * 100:.0f}% end in a state")
        if comma_frac > 0.50 and (state_frac > 0.15 or zip_frac > 0.15):
            reasons.append(f"{comma_frac * 100:.0f}% contain a comma")
        if not reasons:
            continue

        # rank by how much extra is jammed in, ZIP weighted highest
        score = zip_frac * 1.0 + unit_frac * 0.8 + state_frac * 0.6
        # a column named like an address wins ties
        if any(t in ("address", "addr", "street", "location") for t in _tokens(c)):
            score += 0.25
        if score > best_score:
            best_score, best_addr, best_why = score, c, "; ".join(reasons)
    if best_addr:
        ops.append({"type": "split_jammed", "column": best_addr,
                    "why": best_why})

    # ---- jammed person name -------------------------------------------------
    for c in df.columns:
        toks = _tokens(c)
        cl = str(c).lower()
        if "name" not in toks and not any(t.endswith("name") for t in toks):
            continue
        if cl in already_split or (set(toks) & not_a_person):
            continue
        vals = df[c].astype(str)
        nonempty = vals[vals.str.strip() != ""]
        if len(nonempty) == 0:
            continue
        frac_multi = float(nonempty.str.split().apply(
            lambda t: 2 <= len(t) <= 4).mean())
        frac_alpha = float(nonempty.str.contains(
            r"^[A-Za-z ,.\'\-]+$", regex=True).mean())
        if frac_multi > 0.6 and frac_alpha > 0.6:
            ops.append({"type": "split_name", "column": c,
                        "why": f"{frac_multi * 100:.0f}% hold two to four "
                               "name parts in one value"})
            break
    return ops


def render_prep_ui(fname, raw_df):
    """
    Render the per-file staging controls and return the prepared DataFrame.
    Operations are stored in session state so they persist across reruns and are
    re-applied deterministically to the freshly-parsed frame.
    """
    prep_key = f"prep::{fname}"
    ops = st.session_state.setdefault(prep_key, [])

    st.caption(
        "Optional. Clean and split columns so they map one-to-one below. "
        "Original columns are never removed."
    )

    # Columns as they exist after the ops staged so far (lets you split a split).
    current_df = apply_prep_ops(raw_df, ops)
    current_cols = list(current_df.columns)

    if ops:
        st.markdown("**Staged operations**")
        for i, op in enumerate(list(ops)):
            c1, c2 = st.columns([8, 1])
            c1.write(f"{i + 1}. {describe_op(op)}")
            if c2.button("Remove", key=f"rm::{fname}::{i}"):
                ops.pop(i)
                st.rerun()

    st.markdown("**Add an operation**")
    op_type = st.selectbox(
        "Type", ["Clean columns", "Split by delimiter", "Split jammed address",
                 "Split jammed name"],
        key=f"optype::{fname}",
    )

    if op_type == "Clean columns":
        cols = st.multiselect("Columns to clean", current_cols, key=f"clcols::{fname}")
        case = st.selectbox(
            "Case",
            ["none", "Smart Title (names)", "Smart Title (address)",
             "UPPERCASE", "lowercase", "Title Case (basic)"],
            key=f"clcase::{fname}",
            help="Smart Title preserves O'Brien, St. Claire, O Toole, Van Helsing, "
                 "McMahon and DiNapoli. Basic Title Case is the naive version.",
        )
        sanitize = st.checkbox(
            "Sanitize junk characters", key=f"clsan::{fname}",
            help="Removes control/zero-width characters, converts smart quotes and "
                 "dashes to plain ASCII, and collapses doubled punctuation. Keeps "
                 "apostrophes, periods, hyphens and spaces exactly as entered.",
        )
        strip_punct = st.checkbox(
            "Strip leading/trailing punctuation", key=f"clpunct::{fname}"
        )
        if st.button("Add clean step", key=f"addcl::{fname}", disabled=not cols):
            ops.append({"type": "clean", "columns": cols, "case": case,
                        "sanitize": sanitize, "strip_punct": strip_punct})
            st.rerun()

    elif op_type == "Split by delimiter":
        col = st.selectbox("Column", current_cols, key=f"sdcol::{fname}")
        dlabel = st.selectbox(
            "Delimiter", list(DELIMITERS) + ["Custom..."], key=f"sddelim::{fname}"
        )
        delim = (st.text_input("Custom delimiter", key=f"sdcustom::{fname}")
                 if dlabel == "Custom..." else DELIMITERS[dlabel])
        maxsplit = st.number_input(
            "Max splits (0 = split on every delimiter)", min_value=0, value=0,
            step=1, key=f"sdmax::{fname}",
        )
        names = st.text_input(
            "New column names (comma-separated, optional)", key=f"sdnames::{fname}"
        )
        if st.button("Add split step", key=f"addsd::{fname}",
                     disabled=not (col and delim)):
            ops.append({"type": "split_delim", "column": col, "delimiter": delim,
                        "maxsplit": int(maxsplit),
                        "names": names.split(",") if names else None})
            st.rerun()

    elif op_type == "Split jammed address":
        col = st.selectbox("Address column", current_cols, key=f"sjcol::{fname}")
        st.caption(
            "Splits an address like '123 Main St Apt 4 Brooklyn NY 11201' into "
            "<col>_street / _address2 / _city / _state / _zip. The apartment, "
            "suite, floor, or unit goes into _address2. Rows that are already "
            "clean keep the street and leave the new columns blank."
        )
        if col and col in current_df.columns:
            vals = current_df[col].astype(str)
            jammed = int(vals.str.contains(r"\d{5}\s*$", regex=True).sum())
            st.caption(
                f"Heads-up: {jammed:,} of {len(vals):,} values in '{col}' look "
                "jammed (end in a ZIP). Only those will explode into new columns."
            )
        if st.button("Add jammed-split step", key=f"addsj::{fname}", disabled=not col):
            ops.append({"type": "split_jammed", "column": col})
            st.rerun()

    else:  # Split jammed name
        col = st.selectbox("Name column", current_cols, key=f"sncol::{fname}")
        st.caption(
            "Splits a single name field into <col>_first / _middle / _last. "
            "Handles 'Last, First M' and 'First M Last'; middle is kept only "
            "when present and reduced to an initial."
        )
        if st.button("Add name-split step", key=f"addsn::{fname}", disabled=not col):
            ops.append({"type": "split_name", "column": col})
            st.rerun()

    prepared = apply_prep_ops(raw_df, ops)
    st.markdown("**Preview (prepared)**")
    st.dataframe(prepared.head(5), use_container_width=True)
    return prepared


def _pf(name, status, detail):
    """One preflight result. status is 'ok', 'warn', or 'fail'."""
    return {"name": name, "status": status, "detail": detail}


def check_reference_quality(path=None):
    """
    Judge a gazetteer file on its own internal consistency: does the city it
    records for each row agree with the borough its ZIP belongs to? Real NYC
    address data agrees almost always. A high disagreement rate means the file
    is demo data or is not trustworthy as a geocoding reference.

    Returns (status, detail).
    """
    path = path or GEOCODE_FILE
    if not os.path.exists(path):
        return "fail", f"{path} not found; the gazetteer fallback cannot run"
    try:
        checked = disagree = 0
        with open(path, newline="", encoding="utf-8-sig") as fh:
            for row in csv.DictReader(fh):
                low = {str(k).strip().lower(): v for k, v in row.items()}
                zc = clean_cell(low.get("zip", ""))
                city = clean_cell(low.get("city", "") or low.get("borough", ""))
                if not zc or not city:
                    continue
                boro = borough_from_zip(zc[:5])
                if not boro:
                    continue
                checked += 1
                if boro.lower() != city.lower():
                    disagree += 1
        if not checked:
            return "warn", (f"{path}: could not cross-check any rows "
                            "(no usable ZIP and city columns)")
        pct = disagree / checked * 100
        if pct >= 25:
            return "fail", (
                f"{path}: {disagree:,} of {checked:,} rows ({pct:.0f}%) record a "
                "city that contradicts their own ZIP. This is demo or unreliable "
                "data. Replace it with real NYC address points, or install "
                "Geosupport, before processing real client data."
            )
        if pct >= 5:
            return "warn", (
                f"{path}: {disagree:,} of {checked:,} rows ({pct:.0f}%) have a "
                "city that disagrees with their ZIP. Worth investigating."
            )
        return "ok", (f"{path}: {checked:,} rows cross-checked, "
                      f"{pct:.1f}% city and ZIP disagreement")
    except Exception as exc:
        return "warn", f"{path}: could not be checked ({exc})"


def preflight_checks():
    """
    Run environment and configuration diagnostics. Returns a list of results.
    Nothing here raises: a failed check is reported, not thrown, so this can
    always be shown to an operator or pasted into a support request.
    """
    import platform
    import struct
    import sys

    out = []

    # ---- Python itself ------------------------------------------------------
    bits = struct.calcsize("P") * 8
    ver = sys.version_info
    detail = (f"Python {ver.major}.{ver.minor}.{ver.micro} ({bits}-bit) on "
              f"{platform.system()} {platform.release()}  |  {sys.executable}")
    if ver < (3, 9):
        out.append(_pf("Python version", "fail", detail + "  |  3.9 or newer required"))
    elif ver >= (3, 14):
        out.append(_pf("Python version", "warn", detail +
                       "  |  very new; if packages misbehave, 3.11 or 3.12 is safer"))
    else:
        out.append(_pf("Python version", "ok", detail))

    # ---- Required and optional packages -------------------------------------
    for mod, required in (("pandas", True), ("numpy", True), ("streamlit", True),
                          ("openpyxl", True), ("lxml", True), ("thefuzz", False)):
        try:
            m = __import__(mod)
            v = getattr(m, "__version__", "installed")
            out.append(_pf(f"Package: {mod}", "ok", str(v)))
        except Exception as exc:
            out.append(_pf(f"Package: {mod}", "fail" if required else "warn",
                           f"not importable ({exc})"))

    out.append(_pf(
        "Module: table_detect",
        "ok" if table_detect is not None else "warn",
        "loaded; multiple tables per sheet will be detected" if table_detect
        else "not found; each file will be read as a single table"))

    # ---- Geosupport ---------------------------------------------------------
    geofiles = os.environ.get("GEOFILES", "")
    out.append(_pf("GEOFILES environment variable",
                   "ok" if geofiles else "warn",
                   geofiles or "not set; Geosupport cannot locate its data files"))

    try:
        import geosupport as _gs
        out.append(_pf("Package: python-geosupport", "ok",
                       getattr(_gs, "__version__", "installed")))
        try:
            g = _gs.Geosupport()
            res = g.address(house_number=125, street_name="Worth St",
                            borough_code="MN")
            lat = ""
            for k, v in res.items():
                if isinstance(k, str) and "latitude" in k.lower() and v:
                    lat = str(v).strip()
                    break
            if lat:
                out.append(_pf("Geosupport engine", "ok",
                               f"working; test address returned latitude {lat}"))
            else:
                out.append(_pf("Geosupport engine", "warn",
                               "loaded but the test address returned no coordinates"))
        except Exception as exc:
            msg = str(exc)
            hint = ""
            if "nycgeo" in msg.lower() or "locate" in msg.lower():
                hint = ("  |  add the Geosupport 'bin' folder to PATH and set "
                        "GEOFILES to its 'fls' folder, then open a new terminal")
            elif "126" in msg or "module could not be found" in msg.lower():
                hint = ("  |  the DLL was found but a dependency did not load; "
                        f"confirm the Geosupport build is {bits}-bit to match Python")
            out.append(_pf("Geosupport engine", "warn",
                           f"not usable: {msg[:160]}{hint}"))
    except Exception:
        out.append(_pf("Package: python-geosupport", "warn",
                       "not installed; the app will use the CSV gazetteer instead"))

    # ---- Local reference data ----------------------------------------------
    status, detail = check_reference_quality()
    out.append(_pf("Gazetteer reference file", status, detail))

    if os.path.exists(DISTRICT_FILE):
        try:
            with open(DISTRICT_FILE, encoding="utf-8") as fh:
                feats = json.load(fh).get("features", [])
            n = len(feats)
            pts = sum(len(f.get("geometry", {}).get("coordinates", [[]])[0])
                      for f in feats if f.get("geometry"))
            if n <= 10 or pts <= 100:
                out.append(_pf("District boundary file", "fail",
                               f"{DISTRICT_FILE}: only {n} features and {pts} "
                               "boundary points. This is placeholder geography, "
                               "not real districts. Replace it with official NYC "
                               "boundaries, or install Geosupport."))
            else:
                out.append(_pf("District boundary file", "ok",
                               f"{DISTRICT_FILE}: {n} features"))
        except Exception as exc:
            out.append(_pf("District boundary file", "warn",
                           f"{DISTRICT_FILE}: could not be read ({exc})"))
    else:
        out.append(_pf("District boundary file", "warn",
                       f"{DISTRICT_FILE} not found; districts come from "
                       "Geosupport only"))

    # ---- What this means in practice ---------------------------------------
    gde_ok = any(c["name"] == "Geosupport engine" and c["status"] == "ok"
                 for c in out)
    ref_bad = any(c["name"] == "Gazetteer reference file" and c["status"] == "fail"
                  for c in out)
    if gde_ok:
        verdict = ("ok", "Geosupport will be used. This is the authoritative "
                         "NYC geocoder and is the correct setup for real data.")
    elif ref_bad:
        verdict = ("fail", "Geosupport is not available and the local reference "
                           "data is not trustworthy. Results would be wrong. Do "
                           "not process real client data until one of these is "
                           "fixed.")
    else:
        verdict = ("warn", "Geosupport is not available, so the CSV gazetteer "
                           "will be used. It is less accurate: it matches text "
                           "within a ZIP and cannot validate an address.")
    out.append(_pf("Geocoding backend in use", verdict[0], verdict[1]))
    return out


def preflight_report_text():
    """Plain-text diagnostics, suitable for pasting into a support request."""
    lines = [f"Preflight report  {datetime.now(timezone.utc):%Y-%m-%d %H:%M UTC}",
             "=" * 62]
    for c in preflight_checks():
        lines.append(f"[{c['status'].upper():<4}] {c['name']}: {c['detail']}")
    return "\n".join(lines)


def render_preflight():
    """Show the diagnostics panel with a copyable report."""
    checks = preflight_checks()
    fails = sum(1 for c in checks if c["status"] == "fail")
    warns = sum(1 for c in checks if c["status"] == "warn")
    if fails:
        head = f"System check: {fails} problem(s) need attention"
    elif warns:
        head = f"System check: {warns} item(s) to review"
    else:
        head = "System check: everything looks correct"

    with st.expander(head, expanded=bool(fails)):
        icon = {"ok": "OK", "warn": "CHECK", "fail": "PROBLEM"}
        for c in checks:
            line = f"**{icon[c['status']]}**  {c['name']}: {c['detail']}"
            if c["status"] == "fail":
                st.error(line)
            elif c["status"] == "warn":
                st.warning(line)
            else:
                st.caption(line)
        st.text_area(
            "Copy this if you need support", preflight_report_text(),
            height=150,
            help="Paste this into an email or message. It contains no client "
                 "data, only version and configuration details.",
        )


def is_corrections_frame(df) -> bool:
    """
    True when a parsed upload is a re-imported Manual_Review_Needed file: it has
    the Source_File and Source_Row lineage columns plus at least one orig::
    column. Such a file is a set of fixes to apply, not a data source.
    """
    cols = set(map(str, df.columns))
    return ("Source_File" in cols and "Source_Row" in cols
            and any(str(c).startswith("orig::") for c in df.columns))


def _corr_value(v) -> str:
    """Normalize a corrections cell: None and pandas NaN artifacts become ''."""
    if v is None:
        return ""
    s = str(v)
    return "" if s.strip().lower() in ("nan", "none") else s


def parse_corrections_frame(df, corr_name):
    """
    Turn a corrections file into a list of pending patches:
        {"src": table key, "row": 0-based row, "values": {column: new value},
         "from": corrections file name}
    Returns (pending, problems). Rows with unreadable lineage are skipped and
    reported, never guessed.
    """
    pending, problems = [], []
    orig_cols = [c for c in df.columns if str(c).startswith("orig::")]
    for pos, row in df.iterrows():
        try:
            src = str(row["Source_File"]).strip()
            r = int(float(str(row["Source_Row"]).strip()))
        except Exception:
            problems.append(
                f"{corr_name}: line {int(pos) + 2} has an unreadable "
                "Source_File or Source_Row and was skipped"
            )
            continue
        values = {str(c)[len("orig::"):]: _corr_value(row[c]) for c in orig_cols}
        if src and values:
            pending.append({"src": src, "row": r, "values": values,
                            "from": corr_name})
        else:
            problems.append(
                f"{corr_name}: line {int(pos) + 2} has no source reference or "
                "no orig:: values and was skipped"
            )
    return pending, problems


def apply_corrections(frames, pending):
    """
    Apply pending patches to the frames they reference, in place. A value is
    only written when it differs from what is there. Columns that do not exist
    in the frame yet are carried forward (they may exist after the prepare
    step, so this is called once before prep and once after).

    Returns (changed, still_pending, problems) where changed maps
    (table key, row) -> {"from": corrections file, "cols": set of column names}.
    """
    changed, still, problems = {}, [], []
    for item in pending:
        src, r = item["src"], item["row"]
        if src not in frames:
            still.append(item)
            continue
        df = frames[src]
        if not (0 <= r < len(df)):
            problems.append(
                f"{item['from']}: correction for '{src}' row {r} is out of "
                "range and was skipped"
            )
            continue
        remaining = {}
        for col, val in item["values"].items():
            if col in df.columns:
                ci = df.columns.get_loc(col)
                old = _corr_value(df.iat[r, ci])
                if old != val:
                    df.iat[r, ci] = val
                    entry = changed.setdefault(
                        (src, r), {"from": item["from"], "cols": set()})
                    entry["cols"].add(col)
            else:
                remaining[col] = val
        if remaining:
            still.append({**item, "values": remaining})
    return changed, still, problems


def tables_from_upload(up):
    """
    Find the separate tables inside one uploaded file.

    Grid formats (.xlsx, .csv, .tsv) are scanned across every sheet, so tables
    laid out side by side or stacked are returned separately. JSON and XML are
    already structured, so they come back as a single table. Falls back to
    reading the whole file as one table when detection is unavailable.
    """
    name = up.name
    ext = name.lower().rsplit(".", 1)[-1]
    if table_detect is not None and ext in ("xlsx", "csv", "tsv"):
        raw = up.getvalue()
        if ext == "xlsx":
            found = table_detect.detect_in_excel(io.BytesIO(raw), source=name)
        else:
            text = raw.decode("utf-8-sig", errors="replace")
            found = table_detect.detect_in_delimited(text, source=name)
        if found:
            return found
    df = read_uploaded_file(up)
    if table_detect is not None:
        return [table_detect.table_from_dataframe(df, source=name)]
    return [_WholeFile(name, df)]


class _WholeFile:
    """Minimal stand-in used only when the detection module is unavailable."""

    synthetic = True

    def __init__(self, name, df):
        self.source = self.key = self.label = name
        self._df = df
        self.headers = [str(c) for c in df.columns]
        self.kind, self.reason = "unknown", "table detection unavailable"
        self.has_header = True
        self.a1_range = ""

    n_rows = property(lambda self: len(self._df))
    n_cols = property(lambda self: len(self.headers))
    fill_rate = property(lambda self: 1.0)
    empty_columns = property(lambda self: [])
    sensitive_columns = property(lambda self: [])
    suggested_include = property(lambda self: True)

    def to_dataframe(self):
        """The block as a table, with the chosen header row as column names."""
        return self._df


def render_table_selection(uploads, guided):
    """
    Show every table found in the uploaded files and let the person choose which
    ones to include in the compiled dataset. A re-uploaded Manual_Review_Needed
    file is recognized as a corrections file and returned separately rather
    than treated as a data source. Returns (frames, corrections) where frames is
    {table_key: DataFrame} and corrections is a list of (file name, DataFrame).
    """
    frames, multi, corrections = {}, [], []

    for up in uploads:
        # A corrections file is a set of fixes, not a source table.
        try:
            probe = read_uploaded_file(up)
            if is_corrections_frame(probe):
                corrections.append((up.name, probe))
                st.info(
                    f"**{up.name}** was recognized as a corrections file "
                    f"({len(probe):,} rows). Its fixes will be applied to the "
                    "matching rows of the original sources before processing, "
                    "and those rows are re-validated and geocoded like any "
                    "other. Make sure the original source files are uploaded "
                    "alongside it."
                )
                continue
        except Exception:
            pass
        try:
            tables = tables_from_upload(up)
        except Exception as exc:
            st.error(f"Could not read **{up.name}**: {exc}")
            continue
        if len(tables) == 1:
            t = tables[0]
            frames[t.key] = t.to_dataframe()
            st.caption(
                f"{up.name}: one table, {t.n_rows:,} rows and {t.n_cols} columns."
            )
        else:
            multi.append((up.name, tables))

    if not multi:
        return frames, corrections

    for fname, tables in multi:
        n_rec = sum(1 for t in tables if t.kind == "records")
        st.warning(
            f"**{fname}** contains {len(tables)} separate tables. They are "
            "separated by blank rows or columns, so they are different datasets "
            "and must not be merged into one. Choose which to include below. "
            f"{n_rec} look like client records."
        )

        for i, t in enumerate(tables, 1):
            default = t.suggested_include
            head = (f"Table {i}: {t.label}  ({t.n_rows:,} rows x {t.n_cols} cols)"
                    f"  |  {t.kind}")
            with st.expander(head, expanded=(len(tables) <= 4)):
                c1, c2 = st.columns([1, 3])
                with c1:
                    include = st.checkbox(
                        "Include this table", value=default,
                        key=f"tblsel::{t.key}",
                        help="Recommended for tables that look like client "
                             "records. You decide; nothing is included on its own.",
                    )
                with c2:
                    st.caption(
                        f"Classified as **{t.kind}** because it {t.reason}. "
                        f"Cells filled: {t.fill_rate * 100:.0f}%."
                        + ("" if t.has_header else
                           " No header row was found, so columns are numbered.")
                    )
                    if t.empty_columns:
                        st.caption("Completely empty columns: "
                                   + ", ".join(t.empty_columns))
                    if t.sensitive_columns:
                        st.caption(
                            "Sensitive fields present: "
                            + ", ".join(f"{c} ({w})" for c, w in t.sensitive_columns)
                            + ". Leave them unmapped to keep them out of the output."
                        )
                preview = t.to_dataframe()
                st.dataframe(preview.head(8), use_container_width=True,
                             hide_index=True)
                if include:
                    frames[t.key] = preview

    if not frames:
        st.info("Select at least one table to continue.")
    return frames, corrections


def render_gde_fields_selector(gde):
    """
    Grouped checkbox selector for optional Geosupport data points to append to
    the clean output. Returns the list of selected field labels.
    """
    selected = []
    with st.expander("Additional Geosupport data points (optional)", expanded=False):
        if gde is None:
            st.info(
                "These come from Geosupport Desktop Edition. They will become "
                "selectable once GDE is active (see the sidebar). Latitude, "
                "Longitude, and the Senate, Assembly, and Council districts are "
                "always included."
            )
            return []
        st.caption(
            "Tick any extra fields to append to the Final Clean export. Each is "
            "returned by Geosupport for the matched address. Coordinates and the "
            "three legislative districts are already included by default."
        )
        for category, fields in GDE_FIELD_CATALOG.items():
            st.markdown(f"**{category}**")
            cols = st.columns(3)
            for i, (label, _kw, _ex) in enumerate(fields):
                with cols[i % 3]:
                    if st.checkbox(label.replace("_", " "), key=f"gde_field::{label}"):
                        selected.append(label)
        if selected:
            st.caption(f"{len(selected)} extra field(s) will be added to the output.")
    return selected


def render_schema_editor():
    """
    Editable master-schema table. Defaults to the standard schema. The user can rename
    labels, change type/length, toggle required, add custom passthrough fields
    (new rows), or remove fields. Built-in roles keep their NYC-specific logic.
    Returns the active schema (also stored in session state).
    """
    if "schema" not in st.session_state:
        st.session_state["schema"] = [dict(f) for f in DEFAULT_SCHEMA]
    nonce = st.session_state.get("schema_nonce", 0)

    with st.expander("Master schema  ·  fields, labels, types, lengths", expanded=False):
        st.caption(
            "Defaults to the standard schema. Rename labels, change type or max "
            "length (0 = unlimited), toggle required, add custom fields (new rows), "
            "or delete rows. Built-in roles keep their geocoding and validation; "
            "new rows are custom passthrough fields."
        )
        if st.button("Reset to default"):
            st.session_state["schema"] = [dict(f) for f in DEFAULT_SCHEMA]
            st.session_state["schema_nonce"] = nonce + 1
            st.rerun()

        table = pd.DataFrame([{
            "Role": f["role"], "Label": f["label"], "Type": f["dtype"],
            "Length": int(f["length"]), "Required": bool(f["required"]),
        } for f in st.session_state["schema"]])

        edited = st.data_editor(
            table, num_rows="dynamic", use_container_width=True, hide_index=True,
            key=f"schema_editor_{nonce}",
            column_config={
                "Role": st.column_config.TextColumn(
                    "Role", disabled=True,
                    help="Built-in semantic role. Blank on new rows = custom field."),
                "Label": st.column_config.TextColumn("Label (output header)", required=True),
                "Type": st.column_config.SelectboxColumn(
                    "Type", options=["str", "int", "decimal", "date", "bool"], required=True),
                "Length": st.column_config.NumberColumn(
                    "Max length (0 = unlimited)", min_value=0, step=1),
                "Required": st.column_config.CheckboxColumn("Required"),
            },
        )

        new_schema, seen = [], set()
        for _, row in edited.iterrows():
            label = str(row.get("Label") or "").strip()
            if not label or label in seen:
                continue
            seen.add(label)
            role = str(row.get("Role") or "").strip()
            if role not in MASTER_COLUMNS:
                role = "custom"
            new_schema.append({
                "role": role,
                "label": label,
                "dtype": (row.get("Type") or "str"),
                "length": int(row.get("Length") or 0),
                "required": bool(row.get("Required")),
            })
        if new_schema:
            st.session_state["schema"] = new_schema
        return st.session_state["schema"]


def main():
    """The Streamlit interface, kept as the engine's original front end."""
    st.set_page_config(
        page_title="Crosswalk (Offline)", layout="wide",
        initial_sidebar_state="collapsed",
    )

    st.title("Crosswalk")
    st.caption(
        "Air-gapped PII/PHI processing. No external API calls. "
        "Geocoding uses a local reference file only."
    )

    # Workflow mode. Guided hides the advanced panels and auto-detects common
    # fixes; Advanced exposes the full schema editor, Geosupport field picker,
    # manual prep builder, and export options.
    mode = st.radio(
        "Workflow mode", ["Guided", "Advanced"], horizontal=True,
        help="Guided is a streamlined path for nontechnical users. Advanced gives "
             "full control over schema, prep, and export.",
    )
    guided = (mode == "Guided")

    # System check. Shown before any work so a misconfigured machine, or
    # untrustworthy reference data, is caught before real data is processed.
    render_preflight()

    # Persist results across reruns.
    if "results" not in st.session_state:
        st.session_state["results"] = None

    # ---- Sidebar: settings + reference-file status --------------------------
    with st.sidebar:
        st.header("Settings")
        jitter_enabled = st.checkbox(
            "Apply privacy jitter to coordinates", value=True,
            help="Shifts each stored coordinate 150 to 250 feet in a random "
                 "direction so the exported point is never the exact residence. "
                 "District assignment always uses the true coordinate, so turning "
                 "this off does not change which districts are assigned. Turn it "
                 "off only when you need exact coordinates for a trusted, secure "
                 "use.",
        )
        jitter_seed = st.number_input(
            "Jitter seed (reproducibility)", value=1337, step=1,
            disabled=not jitter_enabled,
        )
        if not jitter_enabled:
            st.caption("Jitter is off: exported coordinates will be exact.")

        # Preferred backend: Geosupport Desktop Edition (local). Falls back to
        # the CSV gazetteer + GeoJSON districts when GDE is not installed.
        gde, gde_meta = load_geosupport()
        geocode_index, geo_meta = load_geocode_index(GEOCODE_FILE)

        if gde is not None:
            st.success(
                "Geocoder: **Geosupport Desktop Edition** (local, offline). "
                "Coordinates and districts come straight from GDE."
            )
            require_geocode = st.checkbox(
                "Require successful geocoding for Final Clean", value=True,
                help="If on, validated rows GDE cannot resolve are routed to "
                     "Manual Review.",
            )
        elif geocode_index is not None:
            st.info(f"Geocoder: CSV gazetteer fallback ({gde_meta}).")
            st.success(
                f"Reference loaded: {geo_meta['rows']:,} points "
                f"across {geo_meta['zips']:,} ZIPs."
            )
            require_geocode = st.checkbox(
                "Require successful geocoding for Final Clean", value=True,
                help="If on, validated rows that cannot be matched locally are "
                     "routed to Manual Review.",
            )
        else:
            st.warning(
                f"No geocoder available. {gde_meta} {geo_meta}\n\nThe pipeline "
                "will still validate and clean data; geocoding will be skipped."
            )
            require_geocode = False
        st.caption(f"Fuzzy backend: **{FUZZ_BACKEND}**")

        st.divider()
        district_index, dist_meta = load_district_index(DISTRICT_FILE)
        if gde is not None:
            st.success("Districts: assigned by Geosupport (no boundary file needed).")
        elif district_index is not None:
            st.success(f"District boundaries loaded: {dist_meta['features']} areas.")
        else:
            st.info(
                "No district source. Senate/Assembly/Council columns will be "
                "blank and each geocoded row annotated 'unresolved'. Install "
                f"Geosupport, or drop a '{DISTRICT_FILE}' GeoJSON beside app.py."
            )

    # ---- Step 1: upload ------------------------------------------------------
    st.subheader("1. Upload source files")
    uploads = st.file_uploader(
        "Upload one or more EHR exports (.csv, .tsv, .xlsx, .json, .xml)",
        type=["csv", "tsv", "xlsx", "json", "xml"],
        accept_multiple_files=True,
    )

    if not uploads:
        st.info("Upload at least one file to begin.")
        return

    # Find the separate tables inside each file and let the person choose which
    # ones to compile. A file holding a single table is used automatically, and
    # a re-uploaded Manual_Review_Needed file comes back as corrections.
    file_frames, corrections_files = render_table_selection(uploads, guided)

    corr_pending, corr_problems = [], []
    for corr_name, corr_df in corrections_files:
        p, probs = parse_corrections_frame(corr_df, corr_name)
        corr_pending.extend(p)
        corr_problems.extend(probs)

    if not file_frames:
        if corrections_files:
            st.warning(
                "Corrections were uploaded but no source tables are selected. "
                "Upload the original source files alongside the corrections so "
                "the fixes have rows to apply to."
            )
        return

    # Phase 1: apply corrections to the raw source columns. Columns that only
    # exist after the prepare step are carried forward and applied in phase 2.
    corrections_changed = {}
    if corr_pending:
        ch, corr_pending, probs = apply_corrections(file_frames, corr_pending)
        corrections_changed.update(ch)
        corr_problems.extend(probs)

    # ---- Filename version / redundancy markers (scenario #14 / #8) ----------
    flagged_names = []
    for fname in sorted({k.split(" :: ")[0] for k in file_frames}):
        low = re.sub(r"[^a-z0-9 ]", " ", fname.lower())
        tokens = set(low.split())
        hits = [m for m in VERSION_MARKERS if m in tokens or m in low]
        if hits:
            flagged_names.append((fname, hits))
    if flagged_names:
        msg = "  \n".join(
            f"**{f}** contains version/redundancy markers: {', '.join(h)}"
            for f, h in flagged_names
        )
        st.warning(
            "These filenames suggest non-canonical or duplicate exports. Confirm "
            "you are using the source of truth before merging:  \n" + msg
        )

    # ---- Master schema (Advanced only; Guided uses the default schema) -------
    if guided:
        schema = DEFAULT_SCHEMA
    else:
        schema = render_schema_editor()

    # ---- Optional Geosupport data points (Advanced only) --------------------
    gde_extra_fields = [] if guided else render_gde_fields_selector(gde)

    # ---- Step 2: prepare ----------------------------------------------------
    prepared_frames = {}
    if guided:
        # Auto-detect and apply common fixes; no manual builder.
        st.subheader("2. Automatic cleanup")
        for fname, df in file_frames.items():
            ops = auto_prep_ops(df)
            prepared_frames[fname] = apply_prep_ops(df, ops)
            if ops:
                done = "; ".join(describe_op(o) for o in ops)
                st.success(f"{fname}: {done}.")
            else:
                st.info(f"{fname}: no jammed columns detected; using as-is.")
    else:
        st.subheader("2. Prepare each file (clean & split columns)")
        st.caption(
            "Optional staging so columns line up one-to-one before mapping. New "
            "columns are added; nothing is removed, so no data is lost."
        )
        for fname, df in file_frames.items():
            with st.expander(f"{fname}  ·  prepare  ·  {len(df):,} rows",
                             expanded=False):
                prepared_frames[fname] = render_prep_ui(fname, df)

    # Phase 2: apply any corrections that target columns created by the prepare
    # step (for example a split street column), then report the outcome.
    if corr_pending:
        ch2, corr_pending, probs2 = apply_corrections(prepared_frames, corr_pending)
        for key, entry in ch2.items():
            merged = corrections_changed.setdefault(
                key, {"from": entry["from"], "cols": set()})
            merged["cols"].update(entry["cols"])
        corr_problems.extend(probs2)

    if corrections_files:
        if corrections_changed:
            st.success(
                f"Corrections applied to {len(corrections_changed):,} row(s). "
                "Those rows are re-validated and geocoded like any other, so "
                "the final export is one combined file."
            )
        missing_srcs = sorted({i["src"] for i in corr_pending
                               if i["src"] not in prepared_frames})
        if missing_srcs:
            st.warning(
                "Some corrections reference sources that are not uploaded and "
                "were skipped: " + ", ".join(missing_srcs[:6])
            )
        leftover_cols = sorted({c for i in corr_pending
                                if i["src"] in prepared_frames
                                for c in i["values"]})
        if leftover_cols:
            st.caption(
                "Corrected columns that do not exist in the current sources "
                "were ignored: " + ", ".join(leftover_cols[:8])
            )
        if corr_problems:
            st.warning("  \n".join(corr_problems[:8]))

    corrections_meta = {
        key: (entry["from"], sorted(entry["cols"]))
        for key, entry in corrections_changed.items()
    } or None

    # ---- Step 3: column mapping ---------------------------------------------
    st.subheader("3. Map each file's columns to the master schema")
    if not guided:
        st.caption(
            "Map each schema field to a source column. Leave a field as "
            "'(none)' if the source has no such column. City and State can be "
            "left unmapped when they are embedded in the address or are always NY."
        )

    file_mappings = {}
    all_mapped_ok = True

    for fname, df in prepared_frames.items():
        with st.expander(f"{fname}  ·  {len(df):,} rows  ·  {len(df.columns)} columns",
                         expanded=True):
            st.dataframe(df.head(5), use_container_width=True)
            base_guess = guess_mapping(list(df.columns))
            lower_cols = {c.lower(): c for c in df.columns}
            options = ["(none)"] + list(df.columns)

            mapping = {}
            grid = st.columns(3)
            for i, fld in enumerate(schema):
                role, label = fld["role"], fld["label"]
                key = role if role in MASTER_COLUMNS else label
                # Guess: known roles use the heuristic; custom fields match by label.
                if role in MASTER_COLUMNS:
                    default = base_guess.get(role, "")
                else:
                    default = lower_cols.get(label.lower(), "")
                with grid[i % 3]:
                    idx = options.index(default) if default in options else 0
                    choice = st.selectbox(
                        label, options, index=idx, key=f"{fname}::{key}"
                    )
                    mapping[key] = "" if choice == "(none)" else choice
            file_mappings[fname] = mapping

            # Required-to-map = required schema fields, minus City/State (which
            # are derivable/defaulted).
            missing = []
            for fld in schema:
                if not fld["required"] or fld["role"] in ("City", "State"):
                    continue
                key = fld["role"] if fld["role"] in MASTER_COLUMNS else fld["label"]
                if not mapping.get(key):
                    missing.append(fld["label"])
            if missing:
                all_mapped_ok = False
                st.error(
                    "Please map all required columns. Missing: " + ", ".join(missing)
                )

    # ---- Step 4: run ---------------------------------------------------------
    st.subheader("4. Run the pipeline")
    if st.button("Process & validate", type="primary", disabled=not all_mapped_ok):
        if not all_mapped_ok:
            st.error("Resolve the mapping warnings above before processing.")
        else:
            with st.spinner("Cleaning, validating, de-duplicating, geocoding..."):
                st.session_state["results"] = run_pipeline(
                    prepared_frames, file_mappings, require_geocode,
                    geocode_index, jitter_seed, district_index, gde, schema,
                    gde_extra_fields, jitter_enabled, corrections_meta,
                )

    results = st.session_state["results"]
    if not results:
        return

    # ---- Step 4: dashboard ---------------------------------------------------
    st.subheader("5. Review dashboard")
    total = len(results["transformed"])
    n_clean = len(results["clean"])
    n_review = len(results["review"])

    m1, m2, m3, m4 = st.columns(4)
    m1.metric("Total input rows", f"{total:,}")
    m2.metric("Successfully mapped", f"{n_clean:,}")
    m3.metric("Need manual review", f"{n_review:,}")
    rate = (n_clean / total * 100) if total else 0
    m4.metric("Clean rate", f"{rate:.1f}%")

    # Lossless assertion shown to the operator.
    if n_clean + n_review == total:
        st.success(
            f"Lossless check passed: {n_clean:,} clean + {n_review:,} review "
            f"= {total:,} input rows. No row was dropped."
        )
    else:
        st.error("Lossless check FAILED -- counts do not reconcile.")

    # Verification-status breakdown (scenario #3 / #16).
    v_counts = defaultdict(int)
    for r in results["transformed"]:
        v_counts[r.get("Verification_Status", V_REVIEW)] += 1
    v1, v2, v3, v4 = st.columns(4)
    v1.metric("Verified (high confidence)", f"{v_counts[V_VERIFIED]:,}")
    v2.metric("Verified (low confidence)", f"{v_counts[V_LOWCONF]:,}")
    v3.metric("Unverified (not matched)", f"{v_counts[V_UNVERIFIED]:,}")
    v4.metric("Needs review", f"{v_counts[V_REVIEW]:,}")
    if v_counts[V_LOWCONF]:
        st.caption(
            "Low-confidence matches were geocoded but from a weak or fuzzy match. "
            "They are not labeled fully verified. Check them in the review view "
            "or the Geocode_Confidence column before relying on their districts."
        )

    # Possible-duplicate summary (shown, never merged).
    dup_groups = {r["Possible_Duplicate"] for r in results["transformed"]
                  if r.get("Possible_Duplicate")}
    dup_rows = sum(1 for r in results["transformed"] if r.get("Possible_Duplicate"))
    if dup_groups:
        st.warning(
            f"{len(dup_groups)} possible duplicate group(s) covering {dup_rows} "
            "records were found and marked in the Possible_Duplicate column. They "
            "were NOT merged or removed. Only records with an identical Client ID "
            "are de-duplicated automatically; everything else is left for a person "
            "to confirm."
        )

    if not results["geocode_available"]:
        st.info(
            "Geocoding was skipped because no local reference file was loaded. "
            "Place a valid 'nyc_address_points.csv' beside app.py to enable it."
        )
    if not results.get("district_available"):
        st.info(
            "District columns are blank because no boundary file was loaded. "
            f"Drop a '{DISTRICT_FILE}' GeoJSON beside app.py to assign Senate, "
            "Assembly, and City Council districts."
        )

    # Error breakdown. Guided shows just the essentials; Advanced adds the
    # per-file quality report and the audit trail.
    if guided:
        tab_err, tab_clean = st.tabs(["Rows needing review", "Clean preview"])
        tab_quality = tab_audit = None
    else:
        tab_err, tab_quality, tab_audit, tab_clean = st.tabs(
            ["Rows needing review", "Data quality by file", "Audit trail",
             "Clean preview"]
        )

    with tab_err:
        if n_review == 0:
            st.success("No rows require manual review.")
        else:
            # Bucket review rows by each distinct error category. A row with more
            # than one problem appears under every category it triggers, so each
            # tab is a complete list of that specific problem.
            buckets = defaultdict(list)
            for r in results["review"]:
                seen_cats = set()
                for e in r["__errors__"]:
                    cat = re.split(r":|across merge", e)[0].strip()
                    if cat not in seen_cats:
                        seen_cats.add(cat)
                        buckets[cat].append(r)

            ordered = sorted(buckets.items(), key=lambda kv: -len(kv[1]))
            st.caption(
                f"{n_review:,} rows need review, grouped into {len(ordered)} "
                "problem types. Each tab lists every row with that problem."
            )

            tab_labels = [f"{cat}  ({len(rows)})" for cat, rows in ordered]
            error_tabs = st.tabs(tab_labels)
            for (cat, rows), etab in zip(ordered, error_tabs):
                with etab:
                    st.markdown(f"**{cat}** - {len(rows):,} rows")
                    grid_rows = []
                    for r in rows[:1000]:
                        detail = "; ".join(
                            e for e in r["__errors__"]
                            if re.split(r":|across merge", e)[0].strip() == cat
                        )
                        grid_rows.append({
                            "Source_File": r["__source_file__"],
                            "Source_Row": r["__source_row__"],
                            "Client_ID": r["Client_ID"] or "(missing)",
                            "First_Name": r["First_Name"],
                            "Last_Name": r["Last_Name"],
                            "Address_1": r["Address_1"],
                            "City": r["City"],
                            "Zip": r["Zip"],
                            "Problem_Detail": detail,
                        })
                    st.dataframe(
                        pd.DataFrame(grid_rows), use_container_width=True,
                        hide_index=True,
                    )
                    if len(rows) > 1000:
                        st.caption(f"Showing the first 1,000 of {len(rows):,} rows.")

    if not guided:
        with tab_quality:
            st.caption(
                "Per-file quality surfaces recurring upstream problems (scenario "
                "#5, #11) and which files carry PII (scenario #13)."
            )
            q = results.get("quality", [])
            if q:
                qdf = pd.DataFrame(q)
                qdf["clean_rate"] = qdf["clean_rate"].map(lambda x: f"{x:.1f}%")
                qdf = qdf.rename(columns={
                    "file": "Source_File", "total": "Total", "clean": "Clean",
                    "review": "Review", "clean_rate": "Clean_Rate",
                    "top_issue": "Top_Issue", "carries_pii": "Carries_PII",
                })
                st.dataframe(qdf, use_container_width=True, hide_index=True)

        with tab_audit:
            audit_df = results["audit"].as_dataframe()
            st.caption(
                f"{len(audit_df):,} transformation events recorded "
                "(IDs only -- no names or full addresses)."
            )
            if len(audit_df):
                st.dataframe(audit_df.head(1000), use_container_width=True,
                             hide_index=True)
            else:
                st.write("No transformations were required.")

    with tab_clean:
        if n_clean:
            preview_cols = MASTER_COLUMNS + [
                "Latitude", "Longitude", "Verification_Status",
                "Senate_District", "Assembly_District", "Council_District",
            ]
            clean_df = pd.DataFrame(
                [{c: r.get(c, "") for c in preview_cols} for r in results["clean"]]
            )
            st.dataframe(clean_df.head(500), use_container_width=True,
                         hide_index=True)
        else:
            st.write("No clean rows yet.")

    # ---- Step 5: secure export ----------------------------------------------
    st.subheader("6. Secure export")
    st.caption("Files are generated in memory and only leave the app when you click.")

    result_schema = results.get("schema", DEFAULT_SCHEMA)
    full_clean_df = clean_rows_to_dataframe(results["clean"], result_schema)

    if guided:
        # One-click CSV. No format or column pickers.
        out_fmt = "CSV (.csv)"
        chosen_cols = list(full_clean_df.columns)
    else:
        opt1, opt2 = st.columns([1, 2])
        with opt1:
            out_fmt = st.selectbox("Output format", EXPORT_FORMATS, index=0)
        with opt2:
            chosen_cols = st.multiselect(
                "Columns to include in the clean export",
                list(full_clean_df.columns),
                default=list(full_clean_df.columns),
            )

    clean_df = clean_rows_to_dataframe(
        results["clean"], result_schema, columns=chosen_cols
    )
    review_df = review_rows_to_dataframe(results["review"])
    clean_data, clean_mime, clean_ext = serialize_output(clean_df, out_fmt)
    review_data, review_mime, review_ext = serialize_output(review_df, out_fmt)

    # Guided shows the two files a caseworker needs; Advanced adds the audit log
    # and quality report.
    n_buttons = 2 if guided else 4
    btn_cols = st.columns(n_buttons)
    with btn_cols[0]:
        st.download_button(
            f"Final_Clean_Mapped.{clean_ext}",
            data=clean_data,
            file_name=f"Final_Clean_Mapped.{clean_ext}",
            mime=clean_mime,
            disabled=(n_clean == 0),
        )
    with btn_cols[1]:
        st.download_button(
            f"Manual_Review_Needed.{review_ext}",
            data=review_data,
            file_name=f"Manual_Review_Needed.{review_ext}",
            mime=review_mime,
            disabled=(n_review == 0),
        )
    if not guided:
        with btn_cols[2]:
            st.download_button(
                "Secure_Audit_Log.txt",
                data=results["audit"].as_secure_text(),
                file_name="Secure_Audit_Log.txt",
                mime="text/plain",
            )
        with btn_cols[3]:
            st.download_button(
                "Data_Quality_Report.csv",
                data=build_quality_csv(results.get("quality", [])),
                file_name="Data_Quality_Report.csv",
                mime="text/csv",
            )


if __name__ == "__main__":
    main()
