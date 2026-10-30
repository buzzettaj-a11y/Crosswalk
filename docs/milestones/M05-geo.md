# M05 Placing addresses, districts and the privacy offset

## Goal

Place each standardized address with NYC Geosupport when it is installed, or with an exact-match reference file when it is not. Assign State Senate, Assembly and City Council districts from the true point. Build the data for the two map files, Map_Counts (small cells blanked) and Map_Points (a moved point per building, keyed by the install secret). Propose ZIP, city and state fills from the row's own street, with evidence that tells the truth about its source. Tell the rest of the app which backend and release are in use, and whether the run is a practice run. Every test runs on a fake backend, because Geosupport is not available in the cloud.

## Spec sections

- 6.6 (P-GEO-1 to P-GEO-9, and P-GEO-4a for the practice reference), the whole step. 5.1 (the address key feeds person keys), 7.4 (location confidence), 9.1 (the Map_Counts and Map_Points rows), 14 (Geosupport is not bundled, its release is shown).
- 2 (H3, H8, H9), 12.1 layer 4 (the guard allows the Geosupport DLLs), 17 (Q3).
- Audit findings closed: B-17, B-18, B-19, B-34, B-35, B-45, B-46, A-14, C-10, C-25.
- Fix plan items: 4.4 (replace the jitter) and 5.3 (gate the sample reference, record the Geosupport release). Where the fix plan and the spec differ, the spec wins.

## Depends on

- M00: the guard (`install_for_app`, `DPAPI_DLL_NAMES`, `GEOSUPPORT_SYMBOLS`), the copy registry, and the `wholecount.dev` printer (`emit`, `CountLabel`).
- M01: `InstallSecret` and `SecretStore`, `tests/support/secrets.py` (`TEST_SECRET`), and `session/keys.py`, whose `person_key` takes the address key built here. M05 builds no secret store and no DPAPI code.
- M03: `engine/geo/zips.py` and `nyc_zips.csv`. M04: `StdRow`, `LocationStatus`/`location_for` (its `to_place` rows are the ones looked up). Write one adapter, `to_query(row) -> AddressQuery`. Do not edit M04 files.

## Branch

`build/m05-geo`, created from the latest `main`.

## Read first

All paths are under `legacy/`. Read to learn the rule, then write it fresh.

- `app.py:1816` `load_geocode_index`, `1883` `_norm_addr` (it expands types and directions, which is right, but the caller used fuzzy matching, which is wrong), `1915` `geocode_record` (fuzzy accept at `ADDRESS_FUZZ_THRESHOLD`, line 253, is B-17).
- `app.py:1902` `jitter_point` and `248-256` (`FEET_PER_DEG_LAT`, the seed). Do not keep the constants or the shared `random.Random` (B-18, B-45, C-25).
- `app.py:1968` `load_district_index`, `2005` `_extract_polygons`, `2020` `_point_in_ring`, `2036` `assign_districts`. The first two return different shapes, which is the C-10 crash. The last treats every ring as solid (B-19).
- `app.py:2081` `_strip_gde_ignore_words`, `2152` `load_geosupport`, `2171` `_split_house_street`, `2192` `_extract_geosupport_fields` (tolerant key matching, worth porting), `2239` `_confidence_from_grc` (it calls GRC 01 "Medium"; this spec says Low), `2250` `geocode_with_gde`. `app.py:2480-2600` for the order of lookup and district assignment.
- `fill_missing.py`: `ZipFinder` (42), `propose_city` (142), `propose_for_row` (191). The text "is only in" is the B-34 problem.
- `docs/audit/B-scripts/_refdata.py`, `b15_geocode_fuzzy.py`, `b16_jitter_districts.py`, `b17_districts.py`, `b25_district_holes.py`.
- `docs/context/docs/crosswalk-fix-plan.md` 4.4 (line 537, the `stable_offset` and `move_point` code) and 5.3 (line 641).

## What to build

```
wholecount/engine/addresskey.py       normalize_street(), address_key() (M06 uses it)
wholecount/engine/geo/types.py        AddressQuery, GeoResult, Districts, LocationOutcome
wholecount/engine/geo/backend.py      GeoBackend, select_backend(), NoBackend, preflight(), GeoPreflight
wholecount/engine/geo/geosupport.py   GeosupportBackend (python-geosupport imported lazily), release parsing
wholecount/engine/geo/reference.py    ReferenceBackend (exact only), suggest(), reference folder loading
wholecount/engine/geo/fake.py         FakeGeoBackend (tests and dev only)
wholecount/engine/geo/districts.py    DistrictIndex, point in polygon with holes
wholecount/engine/geo/offset.py       stable_offset(), move_point(), PrivacyOffset
wholecount/engine/geo/mapdata.py      build_map_counts(), build_map_points()
wholecount/engine/geo/fill.py         propose_fills()
wholecount/engine/geo/place.py        place_rows(), outcome_for()
wholecount/guard/config.py            add discover_geosupport_dirs()
wholecount/settings/geo.toml, privacy.toml
tests/fixtures/geo/                   fake_gazetteer.csv, fake_queries.csv, refdata_b17.csv, districts_donut.geojson
wholecount/sample_data/sample_reference.csv   the practice reference for the example data (P-GEO-4a), written by tools/make_example_data.py
tools/make_district_files.py          dev-time builder for the real district files
```

### The sample reference (P-GEO-4, P-GEO-4a)

- Extend M01's `tools/make_example_data.py` so it also writes `wholecount/sample_data/sample_reference.csv` in the reference format below. Its first line is `#wholecount-sample`. It covers every example address the plan places, at made-up points inside the city, and leaves out the few the plan marks as not found. It has no other addresses.
- The script also fills the `locations` section of `EXPECTED.json`. That's the location split (mapped high, mapped low, and counted not mapped with its five reasons) for a practice run with this reference and for a run with no backend. Regenerate the files and keep `--check` passing.
- `refdata_b17.csv` under `tests/fixtures/geo/` holds the `_refdata.py` rows for the audit tests. It's a test fixture, never the practice reference.

### addresskey.py

`normalize_street(text) -> str` and `address_key(house_number, street, zip5) -> str`. The key is `"<house>|<street>|<zip5>"`, with a blank ZIP written as `-`. Each rule is a test named `test_ADDR_n`.

1. ADDR-1. Fold accents, lower case, drop `. , '`, treat `-` between letters as a space, collapse spaces. A hyphen inside a house number stays (`42-09`).
2. ADDR-2. Drop ordinal suffixes from numbers: `45th` becomes `45`. `45th St` and `45 St` share a key.
3. ADDR-3. Expand directions (n, s, e, w) and types (st, ave, av, rd, blvd, dr, ln, ct, pl, ter, pkwy, hwy, sq, cir, expy, plz) to full words.
4. ADDR-4. `st` is the type only when it is the last token. Elsewhere it is `saint` (`St Marks Pl` becomes `saint marks place`).
5. ADDR-5. The type stays in the key, so `45 Park Ave` and `45 Park Pl` differ. `W 45th St` and `West 45th Street` match. Spelled-out ordinals (`Fifth Avenue`) are not converted, so the fallback will not match them to `5 Ave`. Geosupport handles those. (C-24, P-ID-5.)
6. ADDR-6. Units are never in the key. The caller passes Address_1 after the unit was moved out.

### Types

```python
@dataclass(frozen=True)
class AddressQuery:  house_number: str; street: str; borough_or_zip: str       # "11201" or "Brooklyn"
@dataclass(frozen=True)
class Districts:     senate: str | None; assembly: str | None; council: str | None
@dataclass(frozen=True)
class GeoResult:
    confidence: Literal["high", "low", "not_placed"]
    reason: str                       # one of GEO_REASONS
    latitude: float | None            # the TRUE point, in memory only
    longitude: float | None
    borough: str | None               # New York, Brooklyn, Queens, Bronx, Staten Island
    zip5: str | None                  # the building's ZIP as the backend knows it
    districts: Districts | None
    census_tract: str | None          # only when the run asks for it (GeoOptions.extra_fields)
    source: Literal["geosupport", "reference", "reference_sample", "fake", "none"]
    grc: str | None
@dataclass(frozen=True)
class LocationOutcome:
    kind: Literal["mapped", "not_mapped"]
    confidence: Literal["high", "low"] | None
    reason: Literal["no_fixed_address", "outside_nyc", "address_problem", "not_found", "no_geocoder"] | None
    filled: bool                      # a fill from the row's own address was accepted (P-VAL-1)
class GeoBackend(Protocol):
    name: str; release: str           # "25C", a reference file's row count, "unknown", or "" for fake
    def lookup(self, house_number: str, street: str, borough_or_zip: str) -> GeoResult: ...
```

`GEO_REASONS`. The engine returns only the code. Add one sentence per code to the copy registry, each with a claim test (H11). The sentences say "Geosupport matched the building" and the like, as 7.4 does.

| Code | Confidence | Used when |
| --- | --- | --- |
| `matched_building` | high | Geosupport GRC 00, or an exact reference hit |
| `matched_with_warning` | low | GRC 01 |
| `house_out_of_range` | low | GRC 01 and the message says out of range |
| `matched_street_only` | low | used by the fake to test the Low path |
| `not_found` | not_placed | no match, or any other GRC |
| `reference_ambiguous` | not_placed | the reference holds two points for one key more than 100 ft apart |
| `no_backend` | not_placed | no Geosupport and no real reference |

`outcome_for(location, result, filled) -> LocationOutcome` turns M04's `LocationStatus` and a `GeoResult` into the P-VAL-1 location status. LOC-1: a `not_mapped` location keeps its reason. LOC-2: `to_place` with `no_backend` gives `not_mapped` with `no_geocoder`. LOC-3: any other `not_placed` result gives `not_found`. LOC-4: high and low give `mapped` with that confidence. If M04's type already carries these fields, extend it and list the change in the report.

### Backends and preflight (P-GEO-1 to P-GEO-4)

- `select_backend(geosupport, reference, allow_sample=False) -> GeoBackend`. Order is Geosupport, then a real reference, then `NoBackend`. It never returns the fake, and it refuses a sample reference unless `allow_sample`. Tests pin all four branches.
- `GeosupportBackend.discover(environ) -> (backend | None, reason)`. Find the install through `GEOFILES` and `C:\Program Files\Geosupport Desktop Edition`. Import `geosupport` only inside this function. Smoke test one address as `load_geosupport` did. Find how the installed wrapper reports its release (inspect the `Geosupport` class for a version attribute or method). If it cannot, read it from the install folder name. If you cannot tell, store `"unknown"` and put that question first in the report.
- `discover_geosupport_dirs(environ, exists) -> tuple[str, ...]` in `guard/config.py`, standard library only. `install_for_app()` calls it when no folders are passed, so the guard stays the first statement of `__main__.py` and `dev.py`, and it allows any DLL inside those folders. M00 already allows crypt32 and kernel32.
- Lookup is Function 1B with house number, street name, and borough code or ZIP. Port the tolerant key matching. GRC 00 gives High, GRC 01 gives Low, anything else or a `GeosupportError` gives Not placed. Districts come from the Geosupport result. If it has none, leave them `None` and do not fall back to polygons for a Geosupport row. Read the census tract only when asked.
- `ReferenceBackend.from_path(path)`. Header names are case-insensitive. Accept `house_number` (also `hnum`, `housenum`), `street` (also `street_name`, `stname`), `zip` (also `zipcode`), `borough` (also `boro`), `latitude`, `longitude`. Lookup is a dict hit on `address_key` and nothing else. No fuzziness (P-GEO-3, B-17). Two points more than 100 ft apart for one key give `reference_ambiguous`. Within 100 ft, High at the first row's point.
- `ReferenceBackend.suggest(query)` returns up to three near matches for Fix problems. Use `difflib.SequenceMatcher` on alphabetic words, after requiring the house number, every number in the street name, and the street type to be equal. Threshold `suggest_ratio` 0.80. A suggestion is data for a person and never feeds coordinates or districts. `123 Fultin St` suggests `123 Fulton St` (0.833). `111 Main St` suggests nothing.
- The real reference file lives in `<data dir>\reference\` (`%LOCALAPPDATA%\Wholecount\reference\`, or `WHOLECOUNT_DATA_DIR` off Windows; reuse M01's data folder function or move it to `wholecount/paths.py` with no change). `load_folder(dir)` takes the one `.csv` there. Two or more files give `several_reference_files` and no backend, because guessing which to use would change results. `docs/REFERENCE_DATA.md` is M15.
- The sample file is `wholecount/sample_data/sample_reference.csv`. It carries `#wholecount-sample` as its first line, and its SHA-256 is in `SAMPLE_REFERENCE_HASHES` (the script prints the hash after a regeneration, and `--check` fails while they differ). `is_sample` is set on either. It's for tests and "Try example data" only (P-GEO-4). A sample dropped into the reference folder is still a sample and is refused for a batch of the operator's own files.
- `preflight(environ, data_dir, today) -> GeoPreflight(backend, release, release_stale, reference_kind, reference_rows, district_files, can_place)`. `release_stale` is true when the release is more than four quarters behind `today` (fix plan 5.3; the release `25C` is year 2025, quarter 3; `today` is always a parameter, H3). `can_place` is false with no Geosupport and no real reference, and then Process runs without placing and every counted row reads Not mapped, no geocoder. M08's `Session.preflight()` wraps this, and M10 shows it. The release goes to both audit logs and the printable page (M09).
- `GeoOptions(extra_fields: frozenset[str] = frozenset())` holds the run's optional Geosupport fields. Its default comes from `geo.toml` `extra_fields` (empty), and `"census_tract"` is the only value used now. M08's `run_settings` supplies it (M12 shows the switch). With it empty, `GeoResult.census_tract` is `None` and `build_map_counts` writes no tract rows.
- `place_rows(rows, backend, districts, options: GeoOptions, sink) -> PlacementResult` looks up only the rows M04 marks `to_place`, skips the rest, and returns one `GeoResult` per record key. It places rows that are not yet counted too, so a later decision does not need a new lookup (the step is a pure function of the row, H13). It reports at least per 200 rows with a `ProgressMessage`. `PlacementResult.practice` is true when the backend is a sample reference. One failing row never changes another row's result (B-45).

### Fake backend and fixtures

`FakeGeoBackend(gazetteer_csv)` is for tests and `wholecount.dev` only. Columns are `house,street,zip,borough,lat,lon,senate,assembly,council,tract,grc`. It matches on `address_key` exactly. `grc` 01 gives Low with `matched_with_warning`, 00 gives High, no match gives `not_found`. A test greps the package for imports of it outside `dev.py`.

```
house,street,zip,borough,lat,lon,senate,assembly,council,tract,grc
100,W 10 St,10011,New York,40.7350,-73.9990,47,66,3,0077,00
1,Main St,11201,Brooklyn,40.7000,-73.9900,10,20,30,0001,00
11,Main St,11201,Brooklyn,40.7040,-73.9800,11,21,31,0002,00
1,Avenue V,11223,Brooklyn,40.5950,-73.9600,22,46,47,0003,00
100,W 40 St,10025,New York,40.7540,-73.9860,47,75,3,0004,00
123,Fulton St,11201,Brooklyn,40.6920,-73.9870,26,52,33,0005,00
123,Fulton Ave,11201,Brooklyn,40.6800,-73.9800,26,52,33,0006,00
5,Beach 9 St,11691,Queens,40.6020,-73.7500,10,23,31,0007,00
1010,Grand Concourse,10452,Bronx,40.8300,-73.9230,32,77,16,0008,00
85,Montague St,11201,Brooklyn,40.6940,-73.9930,26,52,33,0009,00
118-19,Queens Blvd,11375,Queens,40.7200,-73.8300,11,28,29,0010,00
7,St Marks Pl,10003,New York,40.7290,-73.9890,27,74,2,0011,00
77,Warning Pl,11201,Brooklyn,40.6900,-73.9900,26,52,33,0012,01
```

`fake_queries.csv` has columns `case,house_number,street,borough_or_zip,expect_confidence,expect_reason,expect_lat,expect_lon,expect_districts,audit_id`. `test_fake_backend_fixture` asserts these cases.

- Exact: `100 W 10 St 10011` is high, `matched_building`, 40.7350 and -73.9990, 47/66/3. So is `100 West 10 Street` with `New York`.
- `1 Main St 11201` is high with 10/20/30. `11 Main St 11201` is high with 11/21/31. Districts follow the address (B-17).
- Not placed, `not_found`, no coordinates (B-17): `111 Main St 11201`, `40 W 100 St 10025`, `1 Avenue U 11223`, `12 W 40 St 10025`, `123 Fultin St 11201`, `5 Beach 19 St 11691`, `9999 Broadway New York`.
- `123 Fulton Ave 11201` is high at 40.6800 and -73.9800, not the Fulton St point (C-24). `77 Warning Pl 11201` is low. `7 St Marks Pl 10003` and `118-19 Queens Blvd 11375` are high.

### Districts (P-GEO-5, B-19, C-10)

`DistrictIndex.from_files(paths)` is the only loader and returns one shape. Input is GeoJSON, with properties from any subset of `senate_district`, `assembly_district`, `council_district` and Polygon or MultiPolygon geometry. It merges any number of files. `assign(lat, lon) -> Districts`.

1. DIST-1. Ring 0 is the outer boundary and later rings are holes. A point is inside a polygon when it is inside ring 0 and inside no hole. A MultiPolygon holds a point when any member does.
2. DIST-2. A boundary point counts as inside. When several features of one kind hold the point, return the smallest number, compared as integers.
3. DIST-3. Bounding box first, then ray casting. No third-party geometry library.
4. DIST-4. Coordinates are GeoJSON order, longitude then latitude.
5. DIST-5. Districts always come from the true point, never the moved one (P-GEO-5).

`districts_donut.geojson` is the `b25_district_holes.py` data. District 1 is the square (-74.0, 40.60) to (-73.90, 40.80) with a hole (-73.97, 40.68) to (-73.93, 40.72). District 2 fills the hole. `tools/make_district_files.py` builds the real files from NYC Planning and Open Data into `wholecount/engine/geo/data/districts/`, citing source and date. The app never imports `tools/`. If the cloud cannot reach the source, write the tool, leave a `README.txt` there, and put the question first in the report. With no files, districts are `None` and the pre-run text says so.

### Map data (P-GEO-6, 9.1)

`settings/privacy.toml` holds `small_cell_max = 10`. M09 writes the files. This milestone builds the rows and never writes a file.

```python
@dataclass(frozen=True)
class MapEntry:     unit: str; program: str; districts: Districts; tract: str | None   # unit is the master ID, passed by M09
@dataclass(frozen=True)
class MapCountRow:  program: str; district_type: Literal["council", "assembly", "senate", "census_tract"]; district: str; count: int | None
def build_map_counts(entries, small_cell_max) -> list[MapCountRow]
```

- MAP-1. One row per (program, district type, district) that has at least one distinct unit. A count from 1 to `small_cell_max` is `None`, which the writer shows as "fewer than 11". A count of 0 has no row. Census tract rows exist only when some entry carries a tract. Rows sort by program, district type (council, assembly, senate, census tract), then district as an integer where it is one.
- MAP-2. A row holds no unit, name, address, ID or point. Entries whose district is `None` add nothing for that type.
- MAP-3. `build_map_points(entries, mac) -> list[MapPoint(program, latitude, longitude)]` takes `MapPointEntry(program, address_key, latitude, longitude)` with the true point and returns the moved point. It sorts by program, latitude, longitude, never by person, so row order links nothing.

### Privacy offset (P-GEO-6, P-GEO-7)

`mac` is a callable `bytes -> bytes`, HMAC-SHA256 under the install secret. The engine never sees the secret bytes (H9). If M01's `InstallSecret` has no such method, add `InstallSecret.mac(message)` and list the one-method change in the report. The two functions are the fix plan's, with `"offset|" + address key` in place of the master ID.

```python
def stable_offset(mac, address_key, min_ft=150.0, max_ft=250.0):
    d = mac(b"offset|" + address_key.encode())
    u1 = int.from_bytes(d[:8], "big") / 2**64
    u2 = int.from_bytes(d[8:16], "big") / 2**64
    return min_ft + (max_ft - min_ft) * u1, 2 * math.pi * u2        # (feet, bearing in radians)
def move_point(lat, lon, dist_ft, bearing):
    m = dist_ft * 0.3048
    return (lat + m * math.cos(bearing) / 111_320, lon + m * math.sin(bearing) / (111_320 * math.cos(math.radians(lat))))
```

- OFF-1. The key is the address key of the building: house number and street from the query and the ZIP the backend returned (`GeoResult.zip5`, else the typed ZIP, else `-`). Using the returned ZIP means a row with a blank ZIP and a row with a typed ZIP at one building share a point. Log this reading of "address key".
- OFF-2. Every client at one building gets the same moved point. Averaging clients, rows or quarters returns the moved point, never the true one (B-18, C-25).
- OFF-3. No `random`, no seed, no seed setting, and no `1337` anywhere. A point depends only on its own address key and the secret, so a failed row moves nothing else (B-45).
- OFF-4. One installation always gives one point per building. Another installation gives a different one (H3).
- OFF-5. The audit records only that the offset was applied. Neither the secret nor any offset reaches a log (A-14, H8).

Golden vectors, with `TEST_SECRET` (`bytes(range(32))`) and these true points:

- `100|west 10 street|10011` at (40.7350, -73.9990) gives 172.6566 ft, bearing 0.400361, point (40.7354354, -73.9987568).
- `1|main street|11201` at (40.7000, -73.9900) gives 219.2855 ft, bearing 2.221391, point (40.6996364, -73.9893698).
- `11|main street|11201` at (40.7040, -73.9800) gives 197.7307 ft, bearing 5.418447, point (40.7043513, -73.9805434).
- With `bytes(range(32, 64))`, the first key gives 182.2046 ft, bearing 2.198796, point (40.7347069, -73.9984672).

### Fill proposals (P-GEO-9, B-34)

`propose_fills(row, backend, reference) -> list[FillProposal]`. A proposal has `field`, `value`, `rule_id`, `source` (`geosupport` or `reference`), `source_detail` (the release, or the reference row count), `evidence` and `basis` (`f"{rule_id}|{source}|{sha256(value)[:8]}"`). `evidence` is `FillEvidence(house_number, street, came_from_kind, came_from)`, for the screen only. It never reaches a log or saved progress. `basis` holds a short hash of the value, because saved progress holds no cell values (H9).

- FILL-ZIP-1. ZIP is blank, and house number, street and borough resolve to exactly one ZIP by exact match. Propose it.
- FILL-CITY-1. City is not recognized (P-STD-4) and the ZIP is in the NYC list. Propose the ZIP's borough. The typed city is never replaced without a person accepting (B-31).
- FILL-CITY-2. City and ZIP are both blank, and an exact lookup in each borough returns High in exactly one. Propose that borough.
- FILL-STATE-1. State is blank or not recognized, the ZIP is blank or not valid, and an exact lookup by house number, street and the row's borough returns High. Propose `NY`. Nothing is proposed when the ZIP is valid and outside NYC, or the typed state is another US state.
- No proposal from a fuzzy match, from a street name without a house number, or when two answers come back. No proposal when the ZIP is valid and outside NYC.
- Sentences come from the registry, with codes and parameters only, such as "In the reference file you added (2,310,442 addresses), 85 Montague St is in ZIP 11201." The wording is "in the reference I have", never "is only in". Each has a claim test.

### Settings

`geo.toml`: `suggest_ratio = 0.80`, `reference_ambiguous_ft = 100`, `offset_min_ft = 150`, `offset_max_ft = 250`, `progress_every_rows = 200`, `release_stale_quarters = 4`, `extra_fields = []`. `privacy.toml`: `small_cell_max = 10`.

### Dev commands

Add to `wholecount/dev.py`, printing through M00's `emit` and adding these labels to `CountLabel`. Output is counts only.

- `geo-status [--today YYYY-MM-DD]`: `backend_geosupport`, `backend_reference`, `backend_none`, `release_known`, `release_year`, `release_quarter`, `release_stale`, `reference_real`, `reference_sample`, `reference_rows`, `district_files`, `can_place`.
- `geo-check [--csv PATH --house COL --street COL --zip COL]`: `looked_up`, `placed_high`, `placed_low`, `not_placed`, `districts_filled`. With no file it runs the 12 landmarks in `tests_windows/landmarks.csv`.
- `offset-demo`: `same_offset_second_run`, `distance_in_range`, `distance_feet`, `one_building_one_point`, `other_secret_differs`.
- `map-demo`: `cells_total`, `cells_blanked`, `rows_with_a_name` (always 0).

## Tests to write

Rule tests go in `tests/rules/test_P_GEO.py` (`test_P_GEO_1_...` to `_9_`) and `tests/rules/test_ADDR.py`. One test per ADDR, DIST, LOC, MAP, OFF and FILL rule ID. Audit tests go in `tests/audit/` with a line each in `tests/audit/INDEX.md`.

- `test_B17_fuzzy_geocode.py`. A reference from `tests/fixtures/geo/refdata_b17.csv` (the `_refdata.py` rows). Ask `111 Main St` (reference has `11 Main St`), `1 Main St`, `1 Avenue U` (reference has Avenue V), `40 W 100 St` (reference has `100 W 40 St`), `100 W 100 St`, `12 W 40 St`, `45 Beach 90 St`. Each is `not_placed`, `not_found`, no coordinates, no districts. `suggest()` for `123 Fultin St` returns `123 Fulton St`. For `111 Main St` it returns nothing.
- `test_B18_privacy_offset.py`. (a) The golden vectors. (b) 400 distinct address keys: every haversine distance is within 150 to 250 ft (tolerance 0.5 ft), identical on a second run, identical with the rows shuffled. (c) An attacker who subtracts the old `random.Random(1337)` jitter in row order is left with a median error above 100 ft. (d) The text `1337` and the word `seed` appear in no settings file, copy string or audit text. (e) 300 clients at one address in `build_map_points`: one distinct moved point, 150 to 250 ft from the door, the same in a different row order, the same across four runs, different under another secret, and the centroid of the 300 points is the moved point, not the door.
- `test_B19_district_holes.py`. Donut fixture. (-73.95, 40.70) returns district 2. (-73.99, 40.62) returns district 1. A point on the shared edge of two adjacent squares returns the smaller district. A MultiPolygon with two parts and one hole.
- `test_B34_fill_proposals.py`. `85 Montague St`, city `Hoboken`, ZIP `07030` gives no proposal. `999 Montague St`, Brooklyn, blank ZIP, against a reference without that number gives none. `1 Avenue U`, city `Brookline`, blank ZIP gives none. `85 Montague St`, blank ZIP, Brooklyn, with the exact row in the reference gives FILL-ZIP-1 `11201`, source `reference`, with evidence naming the house number, street and borough. A blank state with an exact High lookup gives FILL-STATE-1 `NY`. The registry text has no "is only in".
- `test_B35_verified_label.py`. Only `high` reads "Mapped, high confidence" and "Verified". A Low result never does, and no setting changes that. Confidence and reason are present on every result.
- `test_B45_early_failure_offset.py`. Place 400 rows. Make row 0 fail. Every other row's `GeoResult` and moved point equals the run where row 0 passed.
- `test_B46_district_note.py`. A point 5 ft inside district A, 40 install secrets: the district is A every time and the moved point is in B for at least one. The registry sentence about moved points exists with a claim test (M09 writes it on the Map_Points notes and the receipt).
- `test_A14_seed_printed.py`. Run the geo step on 20 rows. Scan every `GeoResult`, the audit entries and the progress messages for the secret (hex and raw), `1337` and `seed`. None. The audit entry names the backend, the release and "privacy offset applied".
- `test_C10_gazetteer_crash.py`. Run `place_rows` once per source: the fake, a reference from `refdata_b17.csv` with the donut file, the practice reference `wholecount/sample_data/sample_reference.csv` with `allow_sample=True`, and a reference with no district files. Each placed row gets coordinates, and districts when files exist. The loader returns a `DistrictIndex` in every case.
- `test_C25_shared_stream.py`. Place and offset 33 rows. Change the ZIP of one. The other 32 moved points are identical. Two records at one building share one moved point, 150 to 250 ft from the true point.

Other tests.

- `tests/unit/test_backend_selection.py` (the four branches, sample refused, fake never selected) and `test_no_fake_import_in_package`.
- `tests/unit/test_example_data_reference.py`. `wholecount/sample_data/sample_reference.csv` loads, is marked as a sample, and places every example address `EXPECTED.json` says it places. `tools/make_example_data.py --check` still passes.
- `tests/unit/test_preflight.py`. A copy of `wholecount/sample_data/sample_reference.csv` in the reference folder is `sample` and not placed. Two files give `several_reference_files`. `25C` is stale on 2026-10-01 and not on 2026-09-30. `unknown` is not stale. A missing folder gives `none`.
- `tests/unit/test_outcome_for.py` (LOC-1 to LOC-4) and `test_map_counts.py`: cells of 1, 10, 11 and 0, program and district sorting, census tract rows only when present, no field named like a name, ID or point, and a change to `small_cell_max` changes the blanking.
- `tests/unit/test_fake_backend_fixture.py` (every row of `fake_queries.csv`) and `tests/offline/test_guard_geosupport_dirs.py` (a DLL under a fake Geosupport folder loads and another is denied, in a fresh `python -I` subprocess).
- `tests/copy/`: claim tests for each location reason, the moved-point note, fill evidence, the sample refusal, the no-geocoder line and the stale-release warning.
- `tests/invariants/test_geo_properties.py` (hypothesis). For any secret and address key the distance is 150 to 250 ft and `apply` is deterministic. Changing other rows never changes one row's point. A point is inside a random polygon with a hole exactly when it is inside the outer ring and outside the hole. `address_key` is stable under case, spacing, punctuation and ordinal changes, and differs when the type, a street number or the house number changes. Small-cell blanking never leaves a count of 1 to 10.
- `tests_windows/test_geosupport_real.py`, skipped unless Geosupport is found. It runs `landmarks.csv` and expects High, and reads the release.

## Done when

- [ ] Every rule ID above has a named test, and every audit ID in Spec sections has a test file named for it and a line in `tests/audit/INDEX.md`.
- [ ] The step runs end to end on the fake backend, a real-format reference and a missing backend with no crash (C-10).
- [ ] B-18 part (e) passes: 300 clients at one address share one moved point.
- [ ] No `random` import under `wholecount/engine/geo/`. No `1337` or `seed` under `wholecount/engine/geo/`, in any settings file, in the copy registry or in audit text (the scope of `test_B18` part d). Later milestones use the word seed for other things, such as the reproducible sample in SPEC 8.7, and that's allowed.
- [ ] No new dependency outside the approved set. `python-geosupport` is imported only inside `GeosupportBackend.discover`.
- [ ] The guard change is tested in both directions.
- [ ] The report starts with Questions for Joe, and includes these. (1) SPEC 9.1 now settles practice runs. Map_Counts, Map_Points and the district columns aren't written, `PlacementResult.practice` is provided, and M09 leaves them out. Nothing to ask. (2) The offset key uses the ZIP the backend returned. (3) Small-cell blanking per row can be undone by subtracting from a printed total. The spec asks for nothing more. (4) The district files, if the cloud could not fetch them. (5) How the Geosupport wrapper reports its release.
- [ ] `make test`, `make offline` and `make copy` are green, with the counts written in the report.
- [ ] The report is written, the branch is pushed, the pull request is opened, and work has stopped.

## Windows checks for Joe

Run from the repo with the branch checked out. Nothing below prints a client value.

1. `.venv\Scripts\activate`, then `python -m pytest -q`. Expect no failures. `tests_windows/test_geosupport_real.py` now runs instead of skipping.
2. `python -m wholecount.dev geo-status`. Expect `backend_geosupport 1`, `release_known 1`, a `release_year` and `release_quarter` that match your install (25C is year 2025, quarter 3), and `can_place 1`. If `release_known` is 0, tell Claude Code the folder name of your Geosupport install.
3. `python -m wholecount.dev geo-check`. It runs 12 public landmark addresses. Expect `looked_up 12`, `placed_high 12`, `placed_low 0`, `not_placed 0`, `districts_filled 12`. A Low or Not placed here is a finding about a spelling in `tests_windows/landmarks.csv`, not a fault on your machine. Copy the lines into the pull request.
4. `python -m wholecount.dev geo-check --csv "C:\path\to\your_file.csv" --house House --street Street --zip Zip`, with your own file and column names. Expect only counts. Compare `not_placed` to what you expect.
5. Set `GEOFILES` to an empty value for this window only (`set GEOFILES=`) or rename the Geosupport folder, then run `geo-status`. Expect `backend_geosupport 0`, `backend_none 1`, `can_place 0`. Put it back.
6. Make `%LOCALAPPDATA%\Wholecount\reference\` and copy your real address points CSV there. Run `geo-status` with Geosupport off. Expect `reference_real 1`, `reference_rows` close to your file's row count, `can_place 1`. Replace it with a copy of `wholecount\sample_data\sample_reference.csv` from the repo. Expect `reference_sample 1` and `can_place 0`. Remove the file afterward.
7. `python -m wholecount.dev geo-status --today 2027-12-01`. Expect `release_stale 1` for any release from 2026 or earlier.
8. `python -m wholecount.dev offset-demo`. Expect all five lines to be 1, and `distance_feet` between 150 and 250.
9. `python -m wholecount.dev map-demo`. Expect `cells_blanked` above 0 and `rows_with_a_name 0`.

## Out of scope

- Writing any file with coordinates or counts (M09 writes Map_Counts, Map_Points and the optional exact coordinates). This milestone builds their rows.
- The install secret, its DPAPI store and its backup (M01 and M13). PRACTICE in file names, first rows and the printable page (M09).
- The screens for location confidence, Look up all N and the system check (M10 to M12). M05 provides the codes, the preflight and the copy entries.
- Counting locations for the ledger and batch confidence (M08). M05 returns the per-row outcome.
- `docs/REFERENCE_DATA.md` (M15). Bundling district files into the installer (M14).
