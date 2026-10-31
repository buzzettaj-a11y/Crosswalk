# M03 report

## Questions for Joe

1. **The NYC ZIP table comes from a copy of NYC Health's list, not the original.** The milestone's first-choice source is `https://www.nyc.gov/assets/doh/downloads/pdf/ah/zipcodetable.pdf`. This cloud session's network policy blocks nyc.gov, and it also blocks NYC Open Data and census.gov, so I couldn't fetch the original or a second list to cross-check against. The one public list I could reach is a copy of the same table, with the same Borough, Neighborhood and ZIP columns. It sits in a public GitHub repository, and its URL and retrieval date are in every row's `source` cell. It has 178 ZIPs. The two ZIPs the spec names that it lacks, 11690 and 11696, are added and cited to `SPEC.md P-STD-3`. Nothing was typed from memory.
   - **What I'd check:** the copy seems to lack some residential ZIPs, for example 10069, 10282 and 11109. Clients there would come out "Outside NYC, not mapped" in M04. They'd still be counted, but not mapped.
   - **Two ways to fix it, either works:**
     - Allow `www.nyc.gov` (and, for a cross-check, `data.cityofnewyork.us`) under Network access in this environment's settings: the cloud environment menu in the session title bar, then Edit. The steps are at https://code.claude.com/docs/en/cloud-environments#network-access.
     - Save the PDF's text as a CSV with Borough, Neighborhood and ZIP columns into `tools/data/`, and add it to `SOURCES` in `tools/make_zip_table.py`.

     Either way, rerunning the script cross-checks every source and reports any ZIP that one list has and another lacks.
   - **Default until then:** keep the copy, because M04 and later need a table to run.

The decisions the milestone asked me to log:
2. **Extra list entries beyond the spec's lists:**
   - credentials `msw`, `dds` and `jd`
   - suffixes `vii` to `x` and `5th`, because B-12 asks for II to X and 2nd to 5th
   - the compound given name `mary jane`, for B-11
3. **Position rules for the words that can be two things:**
   - `Sr` at the start, with at least two words after it, is the title Sister. Anywhere else it's a suffix.
   - `Fr` is a title only at the start.
   - `DO` and `NP` are credentials only at the end of a name with two words before them, or after a comma, so `Anh Do` stays a first and last name.
   - A lone `I` is a suffix at the end of a name with no comma and three or more words (`John Smith I`). It's a middle initial in `Smith, John I`.
4. **The wording of `name_extra_tokens`** is "Name has extra words: check them." The spec gives no title for it, so this is plain wording.
5. **`Lower` and `Top Floor` are units**, as B-10 asked. So are `Upper`, `Ground` and the other standalone words in `settings/address_words.toml`.
6. **Other state codes stay in the city text.** The splitter reads only NY as a state. `9 Elm St, Newark, NJ 07102` gives the city `Newark, NJ`, and M04 reads the state from there or from the State column. A two-letter capitalized state code right before a ZIP is never read as a street type, so `Hartford CT 06103` doesn't end the street at "Court".
7. **How the ZIP source was chosen:** see question 1.

Choices on the most conservative reading:
- **A borough name is read as the city even with no ZIP or state.** In `123 Main St - Apt 4 - Brooklyn`, `Brooklyn` is the city. Any other leftover text goes to `extra`, with the location reason `address_extra_text`.
- **Leftover address text that's too long to be a city.** With commas, the trailing segments, up to three words, are the city, and earlier leftovers are extra. Without commas, leftovers of more than three words all go to extra. Nothing is dropped.
- **A one-word name goes to first name.** M04 then flags the missing surname.
- **`Fontaine,`, with a comma and nothing after it, is a surname with a blank first name.**
- **`split_name` takes a `form`:** `auto` (a comma means Last, First), `last_first` or `first_last`, so the operator can say which order the column uses.
- **Particles are lowercase except as the first word**, as the spec says. So `MARY ST CLAIR` re-cases to `Mary st Clair`. If you'd rather `St` keep its capital in casing, it's a one-line change.
- **A middle-initial value that doesn't start with a letter gives blank,** with the note `middle_initial_dropped`.
- **Address and name splits that find nothing are amber** with `split_found_nothing`, beside the milestone's `split_found_no_delimiter`, `clean_changed_nothing` and `no_lookup_available`.
- **The mapper scores a step's column by its suffix.** A calculated ZIP fills Zip, a cleaned column scores as its source column does, and any other derived column is scored by its own name. That's the M02 rule with the names this milestone makes.
- **The example data plan's `map.after_steps`** now names the real split columns, for example `Name_first` and `Full_Address_street`, and lists the two proposed steps. I changed the plan in the script and regenerated.
- **The word-conservation test** ignores separators, a stripped country, and the last four digits of a nine-digit ZIP, because the note `zip_had_9_digits` records those.

## What was built

- **P-PREP-1, P-STD-1 casing.**
  - `engine/prepare/casing.py`: `title_name` and `title_address`. Mixed case is kept, and the module covers Mc, the Mac list, O' and D', hyphens, particles and the exceptions table.
  - The clean step in `steps.py`: case modes, junk removal and edge punctuation.
- **P-PREP-2.** The delimiter step: named or numbered outputs, `maxsplit`, a custom delimiter, and amber when no row holds the delimiter.
- **P-PREP-3.**
  - `engine/prepare/address.py`: `parse_address`, following the seven rules, and `split_trailing_unit`.
  - `settings/address_words.toml`: street types, fixed streets, unit words, standalone units, countries, boroughs and state codes.
- **P-PREP-4.**
  - `engine/prepare/names.py`: `parse_name` and `middle_initial`.
  - `settings/names.toml`: the lists, the Mac names, the middle-initial stop list and the casing exceptions.
- **P-PREP-5.** `engine/prepare/calc_zip.py`: the `ZipResolver` protocol, `valid_existing` and `calculate`, with the five note IDs.
- **Steps.** `engine/prepare/steps.py` has:
  - `Step`, `apply_steps`, `PreparedTable` with `column_refs()`, `PreparedColumn` and `StepResult`
  - amber results, and removing and restoring steps
  - `propose_steps`, which skips other people's columns and unit lines
  - `source_cells_changed`
- **P-VAL-3.** `engine/reasons.py`, the reason registry with severities and flags. Its three decision reasons have `problems.toml` entries.
- **P-STD-3, the ZIP table only.** `tools/make_zip_table.py` (with `--check`), `tools/data/`, `engine/geo/data/nyc_zips.csv` and `engine/geo/zips.py`.
- **Dev command.** `python -m wholecount.dev tidy`. The printer also accepts registered reason IDs, a closed set.

## Tests

| Command | Result |
| --- | --- |
| `make test` | 843 passed |
| `make offline` | 55 passed |
| `make copy` | 127 passed |

`make test` and `make copy` include this report's own lint test.

New test files:
- `tests/audit/`: `test_B06_calculated_zip.py`, `test_B07_nine_digit_zip.py`, `test_B08_street_keeps_concourse.py`, `test_B09_spaced_hyphen_house_number.py`, `test_B10_trailing_segment_kept.py`, `test_B11_particles_and_double_surnames.py`, `test_B12_titles_and_suffixes.py`, `test_B23_end_to_end.py`, `test_B29_unit_then_city.py`, `test_B30_lone_letter_units.py`, `test_B32_extra_name_tokens.py`, `test_B33_middle_initial_placeholders.py`, `test_B42_rear_and_front.py`
- `tests/rules/`: `test_P_PREP_1_clean.py` (with the B-43 inputs through `title_name`), `test_P_PREP_2_split_delim.py`, `test_P_PREP_3_jammed_address.py`, `test_P_PREP_4_jammed_name.py`, `test_P_PREP_5_calculated_zip.py`, `test_steps_model.py`, `test_reason_flags.py`, `test_tokens_are_never_dropped.py`
- `tests/golden/`: `test_proof_09_jammed_address.py` (14 rows), `test_proof_10_jammed_name.py` (6 rows), `CHANGES.md`, `test_changes_log.py`, `test_example_data_steps.py`
- `tests/unit/test_nyc_zip_table.py`
- Support: `tests/support/zips.py` (the dict-backed resolver) and `tests/support/tables.py`

Audit IDs closed:

| ID | Severity | Test |
| --- | --- | --- |
| B-06 | High | `tests/audit/test_B06_calculated_zip.py` |
| B-07 | High | `tests/audit/test_B07_nine_digit_zip.py` |
| B-08 | High | `tests/audit/test_B08_street_keeps_concourse.py` |
| B-09 | High | `tests/audit/test_B09_spaced_hyphen_house_number.py` |
| B-10 | High | `tests/audit/test_B10_trailing_segment_kept.py` |
| B-11 | High | `tests/audit/test_B11_particles_and_double_surnames.py` |
| B-12 | High | `tests/audit/test_B12_titles_and_suffixes.py` |
| B-29 | Medium | `tests/audit/test_B29_unit_then_city.py` |
| B-30 | Medium | `tests/audit/test_B30_lone_letter_units.py` |
| B-32 | Medium | `tests/audit/test_B32_extra_name_tokens.py` |
| B-33 | Medium | `tests/audit/test_B33_middle_initial_placeholders.py` |
| B-42 | Low | `tests/audit/test_B42_rear_and_front.py` |

B-23 also gained `test_B23_end_to_end.py`, the chain test this milestone asked for.

On the example files, the clinic CSV gets the two proposed splits and then maps all 11 fields with no blocks. The other four tables need no step. No source cell changes.

## Done list

- [x] `make test`, `make offline` and `make copy` are green: 843, 55 and 127 passed.
- [x] B-06, B-07, B-08, B-09, B-10, B-11, B-12, B-29, B-30, B-32, B-33 and B-42 each have a passing test and a `done` line in `tests/audit/INDEX.md`.
- [x] Both proof sheet golden tests pass, `tests/golden/CHANGES.md` lists sheet 10 row 3, and no step ever changes a source cell.
- [ ] **`nyc_zips.csv` built from the cited source and cross-checked. Partly done.** It's built from a public copy of the cited source, with its URL and date in each row. The cross-check couldn't run, because no second source was reachable. Question 1 covers both. The ZIP-table tests run and pass against this table, so they aren't marked pending.
- [x] No new dependency. The locks are unchanged.
- [x] The decisions are logged above.
- [x] This report is written, the branch is pushed, and the pull request is open.

## Windows checks

- [ ] 1. `py -3.12 -m venv .venv`
- [ ] 2. `.venv\Scripts\activate`
- [ ] 3. `pip install --require-hashes --no-deps -r requirements-dev.lock`
- [ ] 4. `python -m pytest -q`. All pass.
- [ ] 5. `python -m wholecount.dev tidy "C:\path\to\a real export.xlsx"` with a list that has one combined name column or one combined address column. Expect a proposed step for it (`steps_proposed` above 0), `columns_added` above 0, and `source_cells_changed 0`.
- [ ] 6. Look at the `rows_flagged` lines, which show each reason ID. A list with notes like "c/o" in addresses should show `address_extra_text`, and a list with three-word names should show `name_order_unclear`. A flagged count that looks too high or too low is the thing to tell me about.

The dev command prints counts and reason IDs only. It never shows a client value.

## Screens

None. M03 has no UI.

## Not done

- **The ZIP table's cross-check against a second source.** No second source was reachable from this session. See question 1.
