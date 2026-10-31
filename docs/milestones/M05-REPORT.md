# M05 report

## Questions for Joe

Two need something from you. The other three are the ones the milestone asked me to state, and need nothing.

1. **How should the app read your Geosupport release?** The installed wrapper, python-geosupport 1.1.0, has no way to report it. I read the wrapper's `Geosupport` class and its `__init__.py`. The only version it carries is its own (`__version__ = "1.1.0"`). Function 1B's output has no release field either. So the app reads the release from the install folder's name, like `Geosupport Desktop Edition 25C`, and stores `unknown` when the name doesn't hold one.
   - **The catch:** the default install folder, `C:\Program Files\Geosupport Desktop Edition`, has no release in its name. On a default install, `geo-status` will show `release_known 0`, and the stale-release warning can't fire.
   - **What I need:** the full folder name of your install, and whether the install folder holds a file that names the release (a readme or version file). If one does, I'll read it in M06's branch or a small follow-up. Until then, `unknown` is never treated as stale.
2. **The district files weren't built.** This session can't reach NYC Planning or NYC Open Data. Both returned 403 through the cloud proxy, the same block as the ZIP table in M03.
   - **What's there now:** `tools/make_district_files.py` is written. It never downloads anything. It reads three boundary files saved by hand into `tools/data/districts/` and writes `senate.geojson`, `assembly.geojson` and `council.geojson` into `wholecount/engine/geo/data/districts/`, with the source and date in each. That folder holds a `README.txt` saying so.
   - **Until the files exist:** rows placed by a reference file get no districts, and the pre-run sentence `geo.preflight.no_district_files` says so. Rows placed by Geosupport take their districts from Geosupport, so on your machine this only matters without Geosupport.
   - **Two ways to fix it, either works:**
     - Allow `s-media.nyc.gov` and `data.cityofnewyork.us` under Network access in this environment's settings. The steps are at https://code.claude.com/docs/en/cloud-environments#network-access. I'd then save the three GeoJSON downloads and run the tool.
     - Download the State Senate, State Assembly and City Council district files (clipped to shoreline, GeoJSON) from NYC Planning yourself, save them as the names in the tool's `SOURCES` list, and run `python tools/make_district_files.py`.
3. **Practice runs.** SPEC 9.1 settles this. Map_Counts, Map_Points and the district columns aren't written in a practice run. `PlacementResult.practice` is true when the backend is the sample reference, and M09 leaves those files out. Nothing to ask.
4. **The offset key uses the ZIP the backend returned** (OFF-1). The key is the house number and street from the query, plus the ZIP Geosupport or the reference returned for the building, else the typed ZIP, else `-`. That way a row with a blank ZIP and a row with a typed ZIP at one building share one moved point. This is my reading of "address key" in P-GEO-7.
5. **Small-cell blanking can be undone by subtraction.** If a printed total sits next to a row of district counts with one cell blanked, the blank can be worked out. The spec asks only for blanking per cell, so that's what's built. A complementary-suppression rule would be a spec change.

Choices made on the most conservative reading:
- **The B-17 test asks each near address against a reference holding only its neighbor.** The milestone says to use `refdata_b17.csv` (the audit's `_refdata.py` rows), but three of the asks it lists, `1 Main St`, `1 Avenue U` and `40 W 100 St`, are rows in that file, so against the whole file they're correct exact hits. The audit script ran each ask against a one-row reference, so the test does the same. The asks with no near row in the file also run against the whole file.
- **`GEOFILES` set to an empty value turns Geosupport off** for that window, even when the default folder exists. Windows check 5 relies on it.
- **Every fill needs an exact High answer.** A Low Geosupport match (GRC 01) proposes nothing. FILL-CITY-1 also looks up the house number, street and ZIP and needs a High hit before it proposes the ZIP's borough, because P-GEO-9 allows proposals only through Geosupport or the exact reference. The fake backend proposes nothing.
- **A lookup that raises is that row's `not_found`.** It never stops the run or touches another row (B-45).
- **The reference answers by ZIP, or by borough when the ZIP is blank** (P-GEO-3 says "the ZIP or borough"). A reference row with no borough gets one from the NYC ZIP table.
- **A reference file that can't be read** (a missing column, bad encoding) gives `reference_unreadable` and no backend.
- **A sample is found by its first line or its SHA-256.** A copy with the marker line removed is no longer the registered file, so it reads as a real reference. A sample renamed in the folder is still caught.
- **Geosupport district numbers lose leading zeros** (`047` becomes `47`), so they compare with the district files' numbers.
- **The fill sentence** reads "In the reference I have, the file you added with 2,310,442 addresses, 85 Montague St in Brooklyn is in ZIP 11201." That keeps both the milestone's required phrase and its example.

Found while checking each commit:
- **An M04 property test failed on some random draws, and it's already on main.** `test_restandardizing_accepted_values_changes_nothing` feeds a row's standardized values back in. When a housing word like "Homeless" sits in State, M04 blanks it and marks the row "no fixed address" in its note. Fed back in, the blank State no longer says so, and City and State fill from the ZIP. I narrowed the property to skip rows with no fixed address and left M04's code alone. **For M08:** re-standardizing must start from the entered values plus decisions, never from standardized values, or these rows would lose their status.

Changes to earlier milestones' files, each small:
- `wholecount/paths.py` is new and holds M01's data folder function, unchanged. `default_store` now calls it.
- `InstallSecret.mac(message)` is new: HMAC-SHA256 under the secret. It returns a digest, never the bytes.
- `install_for_app()` now finds the Geosupport folders itself when none are passed, through `discover_geosupport_dirs` in `guard/config.py` (standard library only).
- `emit()` in `dev.py` takes `grouped=False`, so `release_year` prints 2025, not 2,025.
- M04's `LocationStatus` is unchanged. The P-VAL-1 status is the new `LocationOutcome` in `geo/types.py`.

## What was built

- **5.1 the address key.** `engine/addresskey.py`: `normalize_street`, `normalize_house`, `address_key` and `split_house_street` (ADDR-1 to ADDR-6).
- **P-GEO-1, P-GEO-2.** `engine/geo/types.py` (`AddressQuery`, `GeoResult`, `Districts`, `LocationOutcome`, `GEO_REASONS`). `engine/geo/geosupport.py`: `GeosupportBackend.discover` imports python-geosupport inside the function, finds the install, smoke-tests 125 Worth St, and parses the release. Lookup is Function 1B, with the old adapter's tolerant key matching written fresh.
- **P-GEO-3.** `engine/geo/reference.py`: exact lookup on the address key, `reference_ambiguous` past 100 ft, `suggest()` with `difflib` at 0.80, and `load_folder`.
- **P-GEO-4, P-GEO-4a, fix plan 5.3.** `engine/geo/backend.py`: `select_backend`, `NoBackend`, `GeoOptions`, `release_stale` and `preflight`. `tools/make_example_data.py` writes `sample_data/sample_reference.csv` (270 made-up points, three planned addresses left out) and fills the `locations` section of `EXPECTED.json`. The five example files are unchanged.
- **P-GEO-5.** `engine/geo/districts.py`: `DistrictIndex.from_files`, holes, MultiPolygons, boundary points inside, smallest number wins, bounding box first. `tools/make_district_files.py` and the districts `README.txt`.
- **P-GEO-6, P-GEO-7.** `engine/geo/offset.py` (`stable_offset`, `move_point`, `PrivacyOffset`) and `engine/geo/mapdata.py` (`build_map_counts`, `build_map_points`). `settings/geo.toml` and `settings/privacy.toml`.
- **P-GEO-8, P-VAL-1.** `engine/geo/place.py`: `to_query`, `place_rows`, `building_key`, `outcome_for` and the audit entries, which hold IDs and counts only.
- **P-GEO-9.** `engine/geo/fill.py`: `propose_fills` with the four FILL rules, evidence for the screen, and a hashed `basis`.
- **Tests and dev only.** `engine/geo/fake.py`, the fixtures in `tests/fixtures/geo/`, and `tests_windows/landmarks.csv`.
- **12.1 layer 4.** `discover_geosupport_dirs`. The wrapper loads `<install>\bin\nycgeo.dll` by its full path when it's given the install folder, which is what `discover` does, so the DLL falls inside the allowed folder.
- **Copy.** Sentences for the seven reason codes, the location labels, the moved-point note, the five pre-run lines, the fill evidence, the audit line and "fewer than 11", each fact with a claim test.
- **Dev commands.** `geo-status`, `geo-check`, `offset-demo` and `map-demo`. `offset-demo` uses two throwaway secrets and never reads or writes the install secret.

## Tests

| Command | Result |
| --- | --- |
| `make test` | 1575 passed |
| `make offline` | 60 passed |
| `make copy` | 283 passed |

`make test` and `make copy` include this report's own lint test. `tests_windows/test_geosupport_real.py` runs only on Windows with Geosupport, outside `make test`.

New test files:
- `tests/rules/`: `test_ADDR.py` (ADDR-1 to ADDR-6) and `test_P_GEO.py` (P-GEO-1 to P-GEO-9, P-GEO-4a, DIST-1 to DIST-5, OFF-1 to OFF-5 and the golden vectors, MAP-1 to MAP-3, FILL-ZIP-1, FILL-CITY-1, FILL-CITY-2, FILL-STATE-1)
- `tests/unit/`: `test_backend_selection.py` (with `test_no_fake_import_in_package`), `test_preflight.py`, `test_outcome_for.py` (LOC-1 to LOC-4), `test_map_counts.py`, `test_fake_backend_fixture.py`, `test_example_data_reference.py`, and a `mac` test in `test_secret_store.py`
- `tests/offline/test_guard_geosupport_dirs.py`: a real shared library copied under a fake Geosupport folder loads, and the same file elsewhere is denied, in a fresh `python -I` subprocess
- `tests/copy/test_geo_copy.py`
- `tests/invariants/test_geo_properties.py` (hypothesis)
- `tests_windows/test_geosupport_real.py`
- Support: `tests/support/geo.py` and `tests/support/example.py`
- Changed: `tests/invariants/test_standardize_properties.py` skips rows with no fixed address in the restandardize property (see above)

Audit IDs closed:

| ID | Severity | Test |
| --- | --- | --- |
| A-14 | Medium | `tests/audit/test_A14_seed_printed.py` |
| B-17 | High | `tests/audit/test_B17_fuzzy_geocode.py` |
| B-18 | High | `tests/audit/test_B18_privacy_offset.py` |
| B-19 | High | `tests/audit/test_B19_district_holes.py` |
| B-34 | Medium | `tests/audit/test_B34_fill_proposals.py` |
| B-35 | Medium | `tests/audit/test_B35_verified_label.py` |
| B-45 | Low | `tests/audit/test_B45_early_failure_offset.py` |
| B-46 | Low | `tests/audit/test_B46_district_note.py` |
| C-10 | High | `tests/audit/test_C10_gazetteer_crash.py` |
| C-25 | Low | `tests/audit/test_C25_shared_stream.py` |

On the example data with the practice reference, the counted rows split 263 mapped high, 3 not found, 3 address problem, 1 no fixed address and 1 outside NYC, matching `EXPECTED.json` file by file. With no backend, the 266 rows to place read "no geocoder".

## Done list

- [x] Every rule ID has a named test, and every audit ID has a test file named for it and a `done` line in `tests/audit/INDEX.md`.
- [x] The step runs end to end on the fake backend, a real-format reference, the practice reference and a missing backend with no crash (C-10).
- [x] B-18 part (e) passes: 300 clients at one address share one moved point.
- [x] No `random` import under `wholecount/engine/geo/`. No `1337` or `seed` there, in any settings file, in the copy registry or in audit text.
- [x] No new dependency. `python-geosupport` is imported only inside `GeosupportBackend.discover`. M00's `app_imports.py` also imports it, but only to prove under the guard that the wrapper pulls in no network module.
- [x] The guard change is tested in both directions.
- [x] The report starts with Questions for Joe and covers the five points.
- [x] `make test`, `make offline` and `make copy` are green, with the counts above.
- [x] This report is written, the branch is pushed, and the pull request is open.

## Windows checks

Run from the repo with the branch checked out. Nothing below prints a client value.

- [ ] 1. `.venv\Scripts\activate`, then `python -m pytest -q`. Expect no failures. `tests_windows/test_geosupport_real.py` now runs instead of skipping.
- [ ] 2. `python -m wholecount.dev geo-status`. Expect `backend_geosupport 1` and `can_place 1`. If `release_known` is 0, send me the folder name of your Geosupport install (question 1).
- [ ] 3. `python -m wholecount.dev geo-check`. It runs 12 public landmark addresses. Expect `looked_up 12`, `placed_high 12`, `placed_low 0`, `not_placed 0`, `districts_filled 12`. A Low or Not placed here is a finding about a spelling in `tests_windows/landmarks.csv`, not a fault on your machine. Copy the lines into the pull request.
- [ ] 4. `python -m wholecount.dev geo-check --csv "C:\path\to\your_file.csv" --house House --street Street --zip Zip`, with your own file and column names. Expect only counts. Compare `not_placed` to what you expect.
- [ ] 5. `set GEOFILES=` for this window only, then run `geo-status`. Expect `backend_geosupport 0`, `backend_none 1`, `can_place 0`. Close the window afterward.
- [ ] 6. Make `%LOCALAPPDATA%\Wholecount\reference\` and copy your real address points CSV there. Run `geo-status` with Geosupport off as in step 5. Expect `reference_real 1`, `reference_rows` close to your file's row count, `can_place 1`. Replace it with a copy of `wholecount\sample_data\sample_reference.csv`. Expect `reference_sample 1` and `can_place 0`. Remove the file afterward.
- [ ] 7. `python -m wholecount.dev geo-status --today 2027-12-01`. Expect `release_stale 1` for any release from 2026 or earlier, once the release is known.
- [ ] 8. `python -m wholecount.dev offset-demo`. Expect `same_offset_second_run`, `distance_in_range`, `one_building_one_point` and `other_secret_differs` to be 1, and `distance_feet` between 150 and 250.
- [ ] 9. `python -m wholecount.dev map-demo`. Expect `cells_blanked` above 0 and `rows_with_a_name 0`.

## Screens

None. M05 has no UI.

## Not done

- **The district files.** No source was reachable from this session. See question 2.
- **Reading the Geosupport release from anything but the folder name.** See question 1.
