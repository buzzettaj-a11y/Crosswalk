# M04: Standardizing fields and checking rows

## Goal

Write the standard form of every field into the output columns, keep the value as entered beside it, and give each row two statuses, a count status and a location status (P-VAL-1). A row counts on person data alone (P-VAL-2). An address problem stops a row from being mapped, never from being counted. Placeholders, names, ZIPs, cities, states, units, dates and typed custom fields each get a written rule. Nothing is guessed, joined or overwritten. A value that cannot be made standard stays as entered, and the row gets a reason.

## Spec sections

- SPEC 4.1 ("required for mapping"), 6.4 (P-STD-1 to P-STD-8), 6.5 (P-VAL-1 to P-VAL-4), P-READ-3 (the unreadable-character reason), P-MAP-5 and P-MAP-6 (the date order and the two-digit rule arrive as inputs), 13.1 (`tests/golden/CHANGES.md`), H3, H4, H6 and H8.
- Audit: B-01, B-03, B-04, B-05, B-13, B-14, B-15, B-16, B-25, B-26, B-27, B-28, B-31, B-41, B-43, B-44, A-11. B-24 gets a rule test for its second half.

## Depends on

M03 merged (`engine/prepare/` casing, `parse_address`, `split_trailing_unit`, `middle_initial`, `engine/reasons.py` with `Reason(id, severity, flag)`, `engine/geo/zips.py` with `nyc_zips.csv`, and `tests/golden/CHANGES.md`). M02 (schema flags, `TableMapping`, `fill_default`, `DateDecision`, `DateFieldSetting`, `TwoDigitRule`). M01 (`LoadedTable`, its cell metadata and the progress sink).

## Branch

`build/m04-standardize`

## Read first

- `SPEC.md` 6.4, 6.5, P-READ-3, 6.10 steps 4 and 5, 13.1 and H6. Findings in `docs/audit/B-values.md`: B-01 (line 91), B-03 (138), B-04 (159), B-05 (178), B-13 (333), B-14 (352), B-15 (370), B-16 (388), B-25 (575), B-26 (593), B-27 (610), B-28 (627), B-31 (683), B-41 (876), B-43 (908), B-44 (923). A-11 is in `docs/audit/A-claims.md` line 156 and has no script, so build it from the finding and `docs/audit/A-fixtures/misplaced.csv`. Use `canary_clients.csv` for the H8 test. Inputs are in `docs/audit/B-scripts/` (`b01_cleaning.py`, `b02_placeholders_rows.py`, `b03_zip.py`, `b04_city_zip.py`, `b07_address_pipeline.py`, `b08_city_fuzzy.py`, `b10_name_case.py`, `b11_dates.py`, `b12_dob_pipeline.py`, `b24_invisible.py`, `b32_summary_row.py`, `b33_table_coverage.py`).
- `legacy/app.py` (reference only): `CITY_ALIASES` :207, `NULL_SENTINELS` :242, `NEIGHBORHOOD_TO_BOROUGH` :300, `clean_cell` :353, `normalize_zip` :685, `borough_from_zip` :730, `normalize_state` :791, `normalize_city` :804, `normalize_name` :846, `parse_date_value` :1289, `normalize_typed_value` :1337, `_validate_field_value` :1379, `SUMMARY_WORDS` :1393, `is_summary_row` :1398, `transform_row` :1429 (name, ZIP, city and state logic at :1571 to :1671).
- `legacy/tools/make_proof_workbook.py`: sheets 01 to 08 (lines 92 to 218), 11 to 13 (290 to 349) and 17 (412 to 429), with each row's `want=` values.
- Old behavior to not repeat. A block of ZIPs 11351 to 11697 counted as Queens (:748). A fuzzy city fold at 80 percent (:840). An unrecognized city replaced by the ZIP's borough (:1640). A blank state set to NY with no ZIP check (:795). A two-digit year pivot fixed at 25 (:1316). Day and month swapped silently (:1319). Any five digits read as an Excel date (:1300). `\d` accepting digits of every script (:717). Null markers blanking real names (:242). A summary word in either name cell setting the row aside (:1414). Any address problem keeping a row out of the count.

## What to build

All under `wholecount/engine/standardize/` unless noted. The engine stays free of Qt and session. No module here may call `date.today()` or `datetime.now()`; `today` is always a parameter (H3). There is no fuzzy matching anywhere.

### 1. Model, statuses and reasons (`model.py`, `engine/reasons.py`)

- `RowInput(record_key, table_key, row_number, values, kinds, address_text, unmapped, defaults_used)`. `values` maps each schema field key to its cleaned text. `kinds` maps a field key to `number` or `date` from M01's cell metadata, else absent. `address_text` is `AddressText(city, state, zip)`, read-only evidence for B-27. `unmapped` is `UnmappedHint(summary_word, numbers_only)`, two booleans that hold no text. `defaults_used` lists field keys filled by a P-MAP-4 default.
- `StdValue(value, entered, suggestions)`, frozen. `entered` is the text before this step touched it (H6, A-11). `suggestions` is up to two strings kept in memory only. When a field fails its check, `value == entered`.
- `StdRow(record_key, table_key, row_number, values, place, no_fixed_address, outside_nyc, reasons, notes, fills, set_aside_reason)`. `outside_nyc` is set by a valid ZIP that is not in the NYC list, or by a US state other than NY when the ZIP is not an NYC ZIP. A non-NY state beside an NYC ZIP is the location problem `state_zip_disagree`, never `outside_nyc` (P-STD-5). `reasons` and `notes` are tuples of `ReasonRef(reason_id, field)`, sorted by schema position, then ID. `fills` holds `FillRef(field, kind)` with kind `zip` or `default`. The properties `count_status` and `location` call the two functions below.
- `CountStatus` is `counted_passed`, `counted_approved`, `counted_corrected`, `not_counted_yet` or `set_aside` (P-VAL-1). `count_status_for(row, approved=False, corrected=False)`: a `set_aside_reason` gives `set_aside`. A reason flagged `holds_count` gives `not_counted_yet` unless the row is approved or corrected. Then `counted_corrected`, then `counted_approved`, then `counted_passed`. Soft and location reasons never change the count status. M08 supplies the two flags.
- `LocationStatus(kind, reason, problems, filled)` from `location_for(row)`. `kind` is `not_mapped` or `to_place`. For `not_mapped`, `reason` is the first that applies of `no_fixed_address`, `outside_nyc` or `address_problem`, and `problems` lists the location reason IDs. `to_place` means the standard address goes on to M05, which sets mapped high, mapped low, not found, or filled from the row's own address. `filled` is true when a `zip` fill was recorded. A per-source default changes neither status and is only audited (P-VAL-1). The location applies to counted rows, and the function is pure so M08 can ask after a decision.
- `audit_events(row) -> list[AuditEvent(record_key, field, rule_id, reason_id)]`. IDs only (H8). Every standardization, fill and default use produces one event.
- Reasons, added to the M03 registry with `flag` set. SPEC P-VAL-3 makes this list binding. A reason holds the count only when it makes a P-VAL-2 condition fail. M06 adds one more `holds_count` kind, the open same-ID conflict. Open copy groups never hold the count (P-VAL-3). Their rows stay counted, and M06 and M08 treat the group as a cause that widens the range, with no `holds_count` flag. Decision reasons need a `copy/problems.toml` entry (`title`, `means`, `check`, `excel`). Notes do not. These sentences state computed facts, so they take no claim ID. Spec titles are exact, and the rest use plain wording.
  - `holds_count`: `name_missing` (f), `no_identifier` ("no Client_ID and no valid date of birth"), `needed_field_failed` (f).
  - `location`: `address_part_missing` (f), `zip_not_valid` ("ZIP is not a valid ZIP"), `zip_unicode_digits`, `city_not_recognized` ("City not recognized: check it"), `city_zip_disagree` ("City and ZIP disagree"), `state_not_recognized` ("State not recognized"), `state_zip_disagree` ("State and ZIP disagree"), `address_incomplete` ("Address incomplete"), `address_text_disagrees` (f), `units_differ` ("Two different units"). M03's `address_extra_text` is also `location`.
  - `soft`: `placeholder_in_value` (f, "Placeholder in place of a value"), `name_may_be_placeholder` ("Name may be a placeholder"), `digits_in_name`, `unreadable_character` (f, "Value has an unreadable character"), `date_not_readable` (f), `date_impossible` (f), `date_order_unclear` (f), `date_both_ways` (f, "Dates in this column are written both ways"), `date_two_digit_year` (f, "Two-digit year: check the century"), `date_excel_number` (f, "Looks like an Excel date number"), `dob_out_of_range`, `dob_age_over_115`, `value_wrong_type` (f), `value_too_long` (f), `required_field_blank` (f).
  - Notes: `blank_marker`, `no_fixed_address`, `zip_outside_nyc`, `state_outside_nyc`, `zip_plus4_reduced`, `zip_zero_restored`, `name_recased`, `middle_initial_reduced`, `middle_initial_dropped`, `city_standardized`, `city_filled_from_zip`, `state_standardized`, `state_filled_from_zip`, `address_place_moved`, `unit_moved`, `unit_deduplicated`, `date_standardized`, `value_standardized`, `default_used`.
  - `tests/fixtures/std_problem_rows.py` maps every decision reason above, and M03's, to a `RowInput` that triggers it. M08 reuses it.

### 2. Placeholders (`placeholders.py`, P-STD-2)

`settings/placeholders.toml`, starting contents (spec lists first, then the additions to log):
```toml
[every_field]
words = ["null", "n/a", "#n/a", "(null)", "none", "nil", "#ref", "#value", "#name", "#div/0", "#null", "#num", "<na>", "undefined"]
marks = ["-", "--", "?"]
[identifier_and_address]
words = ["0", "00", "000", "unknown", "unk", "refused", "declined", "tbd", "same", "see above", "na", "n.a.", "xxx"]
[name_kept]
words = ["na", "nan", "none", "nil"]
[housing]
words = ["homeless", "shelter", "street", "no fixed address", "nfa", "undomiciled"]
```
- Field classes. Name: First_Name, Middle_Initial, Last_Name. Identifier: Client_ID. Address: Address_1, Address_2, City, State, Zip (SPEC 4.1). Everything else uses `every_field` only.
- `marker(field, text)` matches the whole cell, ignoring case and outer spaces. It compares the text as typed, then with one trailing punctuation mark removed, so `TBD.` and the spreadsheet error strings match with their usual trailing marks. `is_blank(field, text)` is true for an empty cell or a blanking marker, and is what M02's `fill_default` receives, bound to the field with `functools.partial`. Text inside a longer value never matches, so `123 Unknown Ave` and `10 Street Rd` stay.
- A marker from `every_field` blanks the value with the note `blank_marker`. A marker from `identifier_and_address` blanks it and records the soft decision `placeholder_in_value` in Client_ID, Address_1, City, State and Zip, and only a note in Address_2. The blank then raises its own reason in section 9 (`no_identifier` or `address_part_missing`), so one placeholder can give two reasons with two jobs.
- In First_Name and Last_Name the `name_kept` words are not blanked. The value is kept and the row gets the soft reason `name_may_be_placeholder`. The dashes, `?`, `n/a`, `NULL` and `#N/A` still blank a name. Middle_Initial keeps M03's stop list instead. The spec lists `none` and `nil` in both lists, so the name rule wins (log it).
- A housing word as the whole text of any address field sets `no_fixed_address`, blanks that cell and adds the note `no_fixed_address`. The row's location is `not_mapped` with reason `no_fixed_address`, it gets no `address_part_missing`, and it still counts when it passes the count checks.
- Any mapped value holding U+FFFD gets `unreadable_character` naming the field, and the value stays as it is (P-READ-3).

### 3. Names and middle initial (`names.py`, P-STD-1)

- First_Name and Last_Name: trim, collapse spaces, then M03's `title_name`, which re-cases only all-upper or all-lower values. A changed value adds `name_recased`. Mixed case is kept exactly. No tidy-up step is needed for this.
- Digits in either name add `digits_in_name`. `St. John` and `Smith III` pass.
- Middle_Initial goes through M03's `middle_initial`, which reduces a word from a split's `_middle` column to its letter. A full name reduced to a letter adds `middle_initial_reduced`. A stop-list word gives blank and `middle_initial_dropped`.
- Client_ID, Program and Address_2 are trimmed and placeholder-checked only. Address_1 casing is not changed.

### 4. ZIP (`zipcode.py`, P-STD-3)

`standardize_zip(text, kind, nyc) -> ZipResult(value, reason, notes, suggestions, outside_nyc)` in this order.
1. Blank gives blank. The missing part is raised in section 9.
2. From a numeric cell (`kind == "number"`), a digits-only value with 3 or 4 digits is padded to five (`7030` becomes `07030`, note `zip_zero_restored`). A numeric cell with one digit, two digits or more than five digits is not padded and gives `zip_not_valid`. Text cells are never padded.
3. Any digit outside 0 to 9 gives `zip_unicode_digits`, even full-width digits. The NFKC reading goes in `suggestions` when it is exactly five ASCII digits.
4. `^[0-9]{5}$` is accepted. In a text cell, `^[0-9]{5}-[0-9]{4}$` and `^[0-9]{9}$` give the first five (`zip_plus4_reduced`). Anything else gives `zip_not_valid`.
5. A five-digit ZIP not in `nyc_zips.csv` keeps its value, sets `outside_nyc` and adds the note `zip_outside_nyc`. This covers 07030, 11550, 11580, 12345, 99999 and 00000. It is a location status, not a problem.

### 5. City and state (`place.py`, `engine/geo/places.py`, P-STD-4 and P-STD-5)

`settings/places.toml`: `[aliases]` (the 24 spellings from `CITY_ALIASES`, key lower case, value a borough), `[neighborhoods]` (the 114 from `NEIGHBORHOOD_TO_BOROUGH`, plus the missing names listed in B-28 and Marble Hill as New York), `[allowed_pairs]` with `"New York" = ["10463"]`, and `[states]` (the 50 states, DC, Puerto Rico, the Virgin Islands, Guam, American Samoa and the Northern Mariana Islands, by name and two-letter code). Leave out Floral Park, because a Nassau village shares the name, and report it. Boroughs are written New York, Brooklyn, Queens, Bronx and Staten Island.

Matching is exact after lower-casing, trimming and collapsing spaces. Let `Z` be the ZIP's borough when the ZIP is in the NYC list. Outside-NYC rows keep the city as written (SPEC 4.1).

| City as typed | ZIP and state | Outcome |
| --- | --- | --- |
| blank | NYC ZIP | City is `Z`, note `city_filled_from_zip`, fill kind `zip` |
| blank | none, invalid or outside NYC | stays blank, `address_part_missing` |
| borough, alias or listed neighborhood | NYC ZIP, same borough as `Z` | City is the borough, `city_standardized` if the text changed |
| same | NYC ZIP, other borough, pair not allowed | as entered, `city_zip_disagree`, suggestion `Z` |
| borough or alias | outside-NYC ZIP | as entered, `city_zip_disagree` (P-STD-3) |
| neighborhood only | outside-NYC ZIP | as entered, not folded, no reason (B-05) |
| listed names | no valid ZIP, state blank or NY | folded to the borough |
| listed names | typed state is another US state | as entered, not folded |
| anything else | NYC ZIP | as entered, `city_not_recognized`, suggestion `Z` |
| anything else | no valid ZIP, state blank or NY | as entered, `city_not_recognized` |
| anything else | outside-NYC ZIP or another US state | as entered, no reason |

- State: NY, N.Y., ny., New York and New York State give NY (`state_standardized` if the text changed). Any other US state or territory, by name or code, becomes its code. Beside a ZIP that is valid and not an NYC ZIP, or with no ZIP, it sets `outside_nyc` and adds the note `state_outside_nyc`. Beside an NYC ZIP it gives the location problem `state_zip_disagree` with the state kept as entered, and it never sets `outside_nyc`, because one of the two is a typo (P-STD-5). A blank state with an NYC ZIP gives NY (`state_filled_from_zip`, fill kind `zip`). A blank state with a non-NYC ZIP, or any value that is not a US state, gives `state_not_recognized`. A blank state with no ZIP gives `address_incomplete` (P-STD-5), and no `address_part_missing` for State.
- B-27. `AddressText` comes from `parse_address` on the typed Address_1, or from the unmapped sibling columns of a split step when Address_1 is derived. When both sides have a value and they differ after standardizing, add `address_text_disagrees` for City, State or Zip, with the text's value in `suggestions`. `Bklyn` against `Brooklyn` agrees. Nothing is filled from the text.
- B-28. If the Address_1 value ends in 1 to 3 words that are a listed neighborhood or alias, and what remains starts with a house number and ends in a street-type word from `settings/address_words.toml`, move those words to `place` (`Address_1_place`) and add `address_place_moved`. `100 Jamaica Ave` and `1010 Grand Concourse` stay whole. The place never sets City.

### 6. Units in both lines (`units.py`, P-STD-8)

`reconcile_units(address_1, address_2, words) -> UnitResult(address_1, address_2, reason, note)` uses M03's `split_trailing_unit`. If Address_1 has no trailing unit, nothing changes. Otherwise:
- Address_2 blank: the unit moves to Address_2 (SPEC 4.1, proof sheet 11 rows 3 and 5 to 7), note `unit_moved`.
- Address_2 holds a unit: normalize both by dropping unit words, `#`, punctuation and spaces and comparing case-insensitively. `Apt 2A`, `#2A` and `2A` match. If they match, Address_1 loses its copy and Address_2 stays exactly as typed (`unit_deduplicated`). If they differ, keep both as written and add `units_differ`.
- Address_2 holds something that is not a unit, such as `c/o Jane Doe`: keep both as written and add M03's `address_extra_text` (log it).

### 7. Dates (`dates.py`, P-STD-6)

`DateContext(order, state, answered, pivot)` is built from M02's `DateDecision` and `DateFieldSetting` by `date_context(decision, setting)`. `parse_date(text, kind, ctx, today, dob) -> DateParse(iso, reason, readings)` writes `YYYY-MM-DD` with the note `date_standardized` when the text changed.
- A date cell (`kind == "date"`) is already ISO and is accepted. M01 has turned real Excel dates into ISO text, so no serial path exists here.
- A text or numeric value of exactly five digits, such as `12345`, `00000` or `99999`, gets `date_excel_number` and is never converted. `suggestions` holds the date it would be. Serials 1 to 59 count from 1899-12-31, 60 has no date, and 61 and up count from 1899-12-30. Zero has no suggestion. Any other digits-only string or `32874.0` gives `date_not_readable` (B-16).
- ISO `yyyy-mm-dd`, with `-`, `/` or `.`, needs no order. `a<sep>b<sep>y` uses the same separator twice, with a 4-digit or 2-digit year.
- Order (P-MAP-5). A part over 12 settles the order of that value. Equal parts (`03/03/1990`) read without an answer. With `state` of `ask_both_ways` and no answer, every non-ISO value gets `date_both_ways`. With `ask_no_evidence` and no answer, a value whose parts are both 12 or less and differ gets `date_order_unclear`. Once an order is in force, a value that cannot be read that way gets `date_both_ways` in a both-ways column and `date_impossible` in any other. There is no silent swap.
- A two-digit year is never guessed. With no pivot the row gets `date_two_digit_year` and `readings` holds both ISO dates (19yy and 20yy, whichever are real). With `pivot` NN (P-MAP-6), yy up to NN is 20yy and anything above is 19yy. There is no other rule.
- A shape that is not a real calendar date gets `date_impossible`. Any other shape gets `date_not_readable`.
- Date_of_Birth only: after `today` or before 1900-01-01 gives `dob_out_of_range`. An age over 115 in completed years gives `dob_age_over_115` and is still a valid date of birth. Limits live in `settings/standardize.toml` (`earliest_year = 1900`, `max_age = 115`).

### 8. Typed custom fields (`typed.py`, P-STD-7)

As `normalize_typed_value`. `whole_number` needs `^-?[0-9]+$`. `decimal` drops commas, then needs `^-?[0-9]+(\.[0-9]+)?$`. `date` uses `parse_date` without the DOB checks. `yes_no` maps y, yes, true, t, 1 to `Yes` and n, no, false, f, 0 to `No`. A misfit gives `value_wrong_type` and a longer value than `max_length` gives `value_too_long`, each naming the field. A blank required field gives `required_field_blank`. `validate_default(field, text)` returns a reason ID or none, so a bad default is refused when it is saved (M02 left this here).

### 9. Row checks (`rows.py`, `summary.py`, P-VAL)

- The count checks are P-VAL-2 and nothing else. `name_missing` when First_Name or Last_Name is blank after placeholders. `no_identifier` when Client_ID is blank and Date_of_Birth is missing or not valid (a date that failed any check, including `dob_out_of_range`, is not valid). `needed_field_failed` when a custom field marked "needed to count" is blank or failed its type or length. The summary-row condition is P-VAL-4 below. The copy and same-ID conditions arrive in M06.
- Address checks only add location reasons. `address_part_missing` names Address_1, City or Zip when it is blank after fills, unless `no_fixed_address` is set. A blank State follows section 5 instead (filled, `state_not_recognized` or `address_incomplete`). Address_2 is never required. Changing any address value can never change a row's count status.
- P-VAL-4. A row is a summary row when a name cell starts with a word from `SUMMARY_WORDS` (ported with `Total`, `Subtotal`, `Sum`, `Count`, `Average`, `Mean`, `n =` and the rest) and the row has no other person data. Other person data is the other name part, Client_ID, Address_1 or Date_of_Birth. A row with no name, address, identifier or birth date, and a summary word or only numbers elsewhere, is also a summary row. The result is `set_aside_reason = "summary_row"`, no other reasons, and the values untouched. `Sokha Sum` with an ID is a person.
- `standardize_row(row_input, schema, options, today) -> StdRow` depends only on its inputs, never on other rows. Order: summary check, placeholders, unreadable characters, names, ZIP, city and state, address text and place, units, dates, typed fields, count checks. `standardize_table(...)` reports through the M01 progress sink under the step `Checking every row` at least every 200 rows, counts only.

### 10. Inputs and dev command

- `inputs.py`: `build_inputs(prepared, mapping, defaults, options) -> list[RowInput]`. It reads mapped columns, applies `fill_default` with the placeholder-aware `is_blank` and records each use, and reads unmapped cells only to set `UnmappedHint`.
- `TableOptions(date_contexts)`, one `DateContext` per date field.
- `python -m wholecount.dev standardize <path> [...] [--today YYYY-MM-DD] [--date-order month|day] [--two-digit-pivot NN]` loads, maps, applies proposed steps and standardizes. Per table (`A.1`) it prints `rows`, `counted`, `not_counted_yet`, `set_aside`, then for counted rows `outside_nyc`, `no_fixed_address`, `address_problem` and `to_place`, then `values_changed`, `entered_lost` (must be 0), and one `reason <id> <count>` line per reason ID. It never prints a value. Widen M00's `test_dev_counts_only.py` in this milestone so a line may also read `reason <reason_id> <count>`, where the reason ID is checked against the closed set in `engine/reasons.py`.

### Notes from the spec review (SPEC 1.1, P-STD-5 and P-VAL-3)

- Another state written beside an NYC ZIP is the location problem `state_zip_disagree` ("State and ZIP disagree"), not `outside_nyc`. Test: `Brooklyn, NJ 11201` is counted, with location `address_problem` and `state_zip_disagree`.
- A blank state with no ZIP is the location problem `address_incomplete` ("Address incomplete").
- The problem-kind table in this file is binding (SPEC P-VAL-3). Only `name_missing`, `no_identifier`, `needed_field_failed` and an open same-ID conflict hold the count. Open copy groups never do. Their rows stay counted, and each open group widens the Goal 1 range (SPEC 7.2). Date of birth problems are soft when the row has a Client_ID.

## Tests to write

- One file per audit ID in `tests/audit/`, from the finding's own inputs. Every row below has a name and an ID unless the case says otherwise.
  - `test_B01_placeholders.py`. First and Last `-` give `name_missing` and `not_counted_yet`. Client_ID `-` or `0` with no date of birth gives `no_identifier` and `not_counted_yet`, and with a valid date of birth gives `placeholder_in_value` and a counted row. Address_1 `Unknown` and `0` give `placeholder_in_value` and `address_part_missing`, and the row is still counted with an address problem. Address_2 `-` and `0` blank with no review. `TBD`, `n.a.`, `?` and `XXX` in an ID or address blank. `123 Unknown Ave` stays. `Homeless` gives `no_fixed_address`, no other address reason, and a counted row.
  - `test_B03_nassau_zips.py`. Hempstead 11550, Garden City 11530, Valley Stream 11580, Mineola 11501 with a blank state, and a blank city with 11550 are all counted with location `outside_nyc`. The typed city is kept, a blank city stays blank with `address_part_missing`, and a blank state gives `state_not_recognized` and is never set to NY. Brooklyn with 11550 gives `city_zip_disagree` and never a "Queens" claim. Far Rockaway 11691 is `to_place` with no reasons.
  - `test_B04_non_nyc_zip.py`. Brooklyn, NY with 07030, 12345, 99999 and 00000 are each counted, `outside_nyc`, with `city_zip_disagree`.
  - `test_B05_non_nyc_place_names.py`. Blank state with Chelsea 02150, Riverdale 20737, Flushing 48433, Jamaica 05343 and Brookline 02446: city unchanged, state still blank with `state_not_recognized`, counted, `outside_nyc`. Chelsea with state MA and Flushing with state MI are not folded, keep their state, and have no reasons.
  - `test_B13_day_month_order.py`. `[13/04/1990, 03/04/1990]` gives `1990-04-13` and `1990-04-03`. `[03/04/1990]` alone is `date_order_unclear`, and reads `1990-04-03` or `1990-03-04` once answered. `[04/13/1990, 13/04/1990]` gives `date_both_ways` twice, and after a month-first answer reads `1990-04-13` and keeps `date_both_ways` on the other. `03/03/1990` reads with no answer, except in a both-ways column.
  - `test_B14_two_digit_year.py`, today 2026-10-30, order answered month first. With no pivot, `1/2/26`, `5/5/26`, `12/25/26`, `1/2/24`, `1/2/25`, `1/2/45`, `1/2/70` and `1/2/15` all give `date_two_digit_year` with two readings. With the pivot from `suggest_pivot` (26), `1/2/26` gives `2026-01-02`, `1/2/27` gives `1927-01-02`, `1/2/45` gives `1945-01-02`, and `12/25/26` gives `2026-12-25` with `dob_out_of_range`. Pivot 99 reads `1/2/45` as 2045 and flags it. Pivot 0 reads `1/2/00` as 2000 and `1/2/01` as 1901. The audit wanted a plausibility guess; the spec forbids guessing and wins.
  - `test_B15_future_dob.py`, today 2026-10-30. `2026-10-30` and `1911-10-30` pass. `2026-10-31`, `2027-01-01`, `2045-01-02`, `2099-12-31`, `2100-01-01` and `03/04/2050` give `dob_out_of_range`, as does `1899-12-31`. `1900-01-01` and `1910-10-30` give `dob_age_over_115`. With a Client_ID a `dob_out_of_range` row is counted. With no Client_ID it also gets `no_identifier` and is `not_counted_yet`, while `dob_age_over_115` alone still counts.
  - `test_B16_five_digits_not_a_date.py`. `12345`, `99999`, `73051`, `60000`, `10000`, `32874` and `00000` give `date_excel_number` with the value unchanged. The suggestions are `1933-10-18`, `2173-10-13`, `2100-01-01`, `2064-04-08`, `1927-05-18` and `1990-01-01`, and `00000` has none. `32874.0` and `19900415` give `date_not_readable`. A date cell is accepted. A numeric General cell is not converted. The audit's serial column `[32874, 33000]` is refused, because the spec allows serials only from date-format cells.
  - `test_B25_name_placeholders.py`. `Na`, `Nan`, `None` and `Nil` are kept with `name_may_be_placeholder`, and the row is `counted_passed`. With `approved=True` it is `counted_approved` and the value is still `Na`. `NULL` and `-` in a name blank and give `name_missing`.
  - `test_B26_unicode_zip.py`. Full-width `１１２０１` and Arabic-Indic `١١٢٠١` give `zip_unicode_digits` with the value as entered. The first has the suggestion `11201` and the second has none. The audit would accept the full-width form; the spec wins. A numeric cell `7030` gives `07030`, text `7030` gives `zip_not_valid`, and numeric `12`, `5` and `1120134` give `zip_not_valid`.
  - `test_B27_address_text_disagrees.py`. Both audit inputs give `address_text_disagrees`, with the text's value in `suggestions`, and the row is counted. `123 Main St, Bklyn` with City Brooklyn passes.
  - `test_B28_place_stays_out_of_street.py`. Run the five audit inputs through M03's split step, the M02 mapper and this step. Streets are `85-10 Forest Pkwy`, `123 Montague St`, `123 Main St`, `123 Main St` and `123 Main St`, with unit `Apt 4B` on the last. Cities are Queens (`entered` `Woodhaven`), Brooklyn, Queens, Queens and Brooklyn (`entered` `Bklyn`). Then type the same four street-and-place texts without the ZIP and state alone in Address_1, with no split step. Each gives the bare street and `place` set to the neighborhood, and City untouched.
  - `test_B31_unrecognized_city_kept.py`. Yonkers with 10001 and Hoboken with 10001 stay as typed, with `city_not_recognized` and suggestion `New York`. The row is counted, and its location is `address_problem` listing that reason. `Brooklin` with 11201 suggests `Brooklyn`.
  - `test_B41_marble_hill.py`. Manhattan and Bronx with 10463 are `to_place` with no reasons. Brooklyn with 10463 gives `city_zip_disagree` and is counted.
  - `test_B43_name_case.py`. `MCE` gives `Mce`, `MACKENZIE` gives `MacKenzie`, `DEJESUS` gives `DeJesus`, `LEBRON` gives `LeBron`, `DINAPOLI` gives `DiNapoli` and `O’BRIEN` gives `O’Brien`. `mELINDA` and `DiNapoli` are kept.
  - `test_B44_summary_surnames.py`. `Sokha Sum`, `Sokha Mean` and `Count Basie` with an ID and no address are counted, with `address_part_missing` for Address_1, City and Zip, `address_incomplete` for State, and location `address_problem`. A row with only `Total` in a name cell, `Grand Total` in one cell, or only numbers is `set_aside` with `summary_row`.
  - `test_A11_original_kept.py`. On `misplaced.csv` all five rows are counted. M001 and M002 keep their City with `city_not_recognized` and suggestion `Brooklyn`. M003 gives `state_not_recognized`, M004 gives `zip_not_valid`, and M005 is `to_place`. `Manhattan` with 10007 gives value `New York` with `entered` `Manhattan`. For every row, `entered` equals the file text, and `audit_events` holds none of it.
- Rule tests in `tests/rules/`: `test_P_STD_1_names.py`, `test_P_STD_2_placeholders.py` (each list and field class, whole-cell only, housing words in each address field), `test_P_STD_3_zip.py` (the sheet 04 forms, numeric padding, the NYC list), `test_P_STD_4_city.py` (every table row), `test_P_STD_5_state.py` (including every state and territory code and name, `Brooklyn, NJ 11201` counted with `state_zip_disagree` and not `outside_nyc`, `Newark, NJ 07102` counted and `outside_nyc`, and a blank state with no ZIP giving `address_incomplete`), `test_P_STD_6_dates.py`, `test_P_STD_7_typed_fields.py` (including `validate_default`), `test_P_STD_8_units.py`, `test_P_READ_3_unreadable_character.py`, `test_P_VAL_1_statuses.py` (the full precedence of both functions), `test_P_VAL_2_count_rule.py` (each condition alone, address damage never changing the count status, a missing Client_ID rescued by a valid date of birth), `test_P_VAL_3_reasons_registry.py` (every decision reason has the four keys and exactly one flag, notes have none, and the `holds_count` reasons are exactly `name_missing`, `no_identifier` and `needed_field_failed` plus the same-ID conflict kind M06 adds, so the test reads M06's kind from the registry once it exists. No copy-group kind is ever `holds_count`. `state_zip_disagree` and `address_incomplete` are `location`) and `test_P_VAL_4_summary_rows.py`.
- `tests/invariants/test_standardize_properties.py`, Hypothesis. A row's result is the same alone or among other rows in any order. Re-standardizing an accepted row's values changes nothing. Every `entered` equals the input. No ZIP value holds a non-ASCII digit. A city is never changed except to its own borough. Replacing every address value with any text never changes the count status. For a table, counted plus not counted yet plus set aside equals rows, and the location kinds add up to counted (H4). No module calls the wall clock.
- `tests/invariants/test_h8_standardize.py`. Run `canary_clients.csv` through the pipeline and assert no cell text appears in any `AuditEvent` or in any dev command line.
- `tests/unit/test_places_settings.py` (24 aliases, at least 114 neighborhoods, only the five boroughs, 56 state entries) and `tests/unit/test_std_problem_rows.py` (every decision reason has a triggering row).
- `tests/golden/`. `test_proof_01_08_values.py`, `test_proof_11_unit_in_both_lines.py`, `test_proof_12_13_required_digits.py` and `test_proof_17_field_types.py` type each sheet's rows and `want=` values as literals. CLEAN means no decision reason. REVIEW means at least one, and the test names the flag the row now has. Where the spec changes a rule, the ported expectation follows the spec, and each such row is added to `tests/golden/CHANGES.md` with its sheet, row, old answer, new answer and rule. Rows to list: sheet 01 row 1 (`name_missing`), sheet 02 (re-cased with no tidy-up step), sheet 06 row 7 (`Springfield` is kept with `city_not_recognized`, P-STD-4), sheet 08 NJ and CT (accepted, outside NYC, no review, P-STD-5), sheet 11 rows 9 and 10 (counted with `units_differ` and `address_extra_text`, P-STD-8), sheet 17 rows 1 and 3 (separate tables, P-MAP-5), and every other row whose old REVIEW was for an address problem alone, which is now counted and not mapped (P-VAL-2). `test_example_data_standardize.py` runs the five example files in `wholecount/sample_data/` through load, map, proposed steps and standardize. Per table, counted, not counted yet and set aside, and the reason ID of every planned problem row by file and row number, equal the `standardize` section of `EXPECTED.json`. The twelve rows with neither a Client_ID nor a date of birth come out `no_identifier`, and the workbook's `Total` row is set aside. Print those counts in the report for Joe to read.

## Done when

- [ ] `make test`, `make offline` and `make copy` are green, with the counts in the report.
- [ ] B-01, B-03, B-04, B-05, B-13, B-14, B-15, B-16, B-25, B-26, B-27, B-28, B-31, B-41, B-43, B-44 and A-11 each have a passing test and a line in `tests/audit/INDEX.md`.
- [ ] Every decision reason has a `problems.toml` entry, one flag and a triggering row, and no step ever leaves `entered` different from the input.
- [ ] A row with a name and an ID is counted whatever its address holds, and the balance test passes (H4).
- [ ] `tests/golden/CHANGES.md` lists every changed sheet and row from this milestone.
- [ ] No new dependency outside the approved set, and no fuzzy matching.
- [ ] The report lists the decisions logged above: the flag table, the name rule winning over `none` and `nil`, the added placeholder words, a placeholder giving two reasons, all five address fields counting for housing words, Address_2 holding non-unit text, a unit moving into a blank Address_2, numeric ZIP cells with nine digits failing, date reasons being soft, no serial path, and Floral Park left out.
- [ ] `docs/milestones/M04-REPORT.md` is written, the branch is pushed, the pull request is open, and work has stopped.

## Windows checks for Joe

1. `py -3.12 -m venv .venv`
2. `.venv\Scripts\activate`
3. `pip install --require-hashes --no-deps -r requirements-dev.lock`
4. `python -m pytest -q`. All pass.
5. `python -m wholecount.dev standardize "C:\path\to\a real export.xlsx"`. Expect `counted`, `not_counted_yet` and `set_aside` to add up to `rows`, and `outside_nyc`, `no_fixed_address`, `address_problem` and `to_place` to add up to `counted`. `entered_lost` must be 0.
6. Read the `reason` lines. `name_missing` and `no_identifier` are the only ones that keep a client out of the count, so they should match the blanks you know about. `city_not_recognized` should be your typos and out-of-city towns. A count that looks wrong is the thing to tell me about.
7. If `reason date_order_unclear` or `date_both_ways` appears, rerun with `--date-order month` or `--date-order day` and confirm those rows clear. If `date_two_digit_year` appears, try `--two-digit-pivot 26` and see the count change.
8. Run it on the five files in `wholecount\sample_data\`. The `counted`, `not_counted_yet` and `set_aside` lines per table equal the `standardize` section of `EXPECTED.json`, and the `reason no_identifier` lines add up to the number `EXPECTED.json` lists, which includes the twelve rows with neither a Client_ID nor a date of birth.

The dev command prints counts and reason IDs only. It never shows a client value.

## Out of scope

- Looking up addresses, filling ZIPs from streets, districts and the privacy offset (M05). Blank ZIPs are only reported here. M05 turns `to_place` into mapped high, mapped low, not found, or filled from the row's own address.
- Copies, same identifiers and the same person across files (M06), and program names (M07). The copy and same-ID conditions of the count rule arrive there.
- Applying decisions, approve and set-aside actions, corrections files and counts (M08). Only the `approved` and `corrected` flags of `count_status_for` are defined here.
- Writing the audit and the review file (M09). This milestone returns the events and the entered values.
- The Match your columns and Fix problems screens (M11 and M12).
