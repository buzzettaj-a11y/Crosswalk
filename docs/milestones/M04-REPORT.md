# M04 report

## Questions for Joe

1. **Proof sheet 08, NJ and CT: the milestone and the spec disagree, and I followed the spec.** The milestone's list of changed answers says sheet 08's NJ and CT rows become "accepted, outside NYC, no review." But those rows keep the sheet's base ZIP, 11201, which is an NYC ZIP. P-STD-5 says another state beside an NYC ZIP is the location problem "State and ZIP disagree," never "Outside NYC," because one of the two is a typo. So both rows are counted, not mapped, and carry `state_zip_disagree`. The case the milestone describes, another state with a ZIP outside NYC, is counted and outside NYC with no problem, and `test_P_STD_5_state.py` covers it (`Newark, NJ 07102`). `tests/golden/CHANGES.md` records the spec's answer.

The decisions the milestone asked me to log:
2. **The flag table** is exactly the one in the milestone.
   - `holds_count`: `name_missing`, `no_identifier` and `needed_field_failed`.
   - `location`: the eleven address kinds, with M03's `address_extra_text`.
   - `soft`: the fifteen soft kinds, every date reason among them.

   `test_P_VAL_3_reasons_registry.py` pins it, and it will accept M06's same-ID conflict kind when that arrives.
3. **The name rule wins over `none` and `nil`.** In First_Name and Last_Name, `Na`, `Nan`, `None` and `Nil` are kept with `name_may_be_placeholder`. Only the dashes, `?`, `NULL`, `N/A`, `#N/A` and `(null)` blank a name.
4. **Placeholder words beyond the spec's lists:** the spreadsheet error strings (`#REF!`, `#VALUE!`, `#NAME?`, `#DIV/0!`, `#NULL!`, `#NUM!`), `<NA>`, `undefined` and `xxx`. A marker also matches with one trailing punctuation mark removed, so `TBD.` and `#REF!` match.
5. **One placeholder can give two reasons.** `Unknown` in Address_1 gives `placeholder_in_value`, which is soft and says what was there. The blank it leaves then gives `address_part_missing`, which is a location reason and says what's missing.
6. **Housing words count in all five address fields.** A housing word as the whole text of Address_1, Address_2, City, State or Zip sets "No fixed address," blanks that cell, and notes it. Such a row also gets no fills from its ZIP and no reason for a blank address part, so its location is simply "No fixed address."
7. **Address_2 can hold text that isn't a unit.** When Address_1 ends in a unit and Address_2 holds something else, like `c/o Jane Doe`, both are kept as written and the row gets M03's `address_extra_text`.
8. **A unit moves into a blank Address_2.** When Address_1 ends in a unit and Address_2 is blank, the unit moves to Address_2, with the note `unit_moved`.
9. **Numeric ZIP cells with nine digits fail.** Only text cells reduce a ZIP+4. A numeric cell holding nine digits gives `zip_not_valid`.
10. **Date reasons are soft.** They never hold the count by themselves. A row with no Client_ID still needs a valid date of birth to count, and a date that failed any check isn't valid. `dob_age_over_115` is the exception: it's flagged, but the date stays valid.
11. **There's no serial-number path.** M01 already turned real Excel date cells into ISO text. Five digits in a date field are never converted. They get `date_excel_number`, with the date they would be as a suggestion.
12. **Floral Park is left out of the neighborhood list,** because a Nassau County village shares the name.

Choices on the most conservative reading:
- **Other spreadsheet error strings in a name cell are kept as the name,** for example `#REF!`. The spec's list of what blanks a name is exact.
- **A Client_ID that is itself a summary word doesn't count as person data.** The example workbook's `Total` row has "Total" in the Client ID column and the row count in Program. It's set aside as a summary row. `Sokha Sum` with an ID is still a person.
- **A blank state beside a ZIP that isn't valid gives `address_incomplete`,** the same as having no ZIP at all, since neither can place the address.
- **`RowInput` carries a tidy-up step's reasons and notes** (`step_reasons` and `step_notes`). The milestone's field list didn't include them, but M03's `name_order_unclear`, `name_extra_tokens`, `address_extra_text` and `zip_had_9_digits` need a way onto the row.
- **`dev standardize` has a `--choose-suggested-header` option.** It applies a table's suggested header row the way an operator would on Show data. Without it, the example workbook's `Clients` table stays unticked and prints nothing.
- **I fixed the example plan where it was wrong.** The placeholder street `Unknown` also leaves the city, ZIP and state blank, so it plans three reasons, not two. The plan now keeps decision reasons and notes apart. I changed the plan in the script and regenerated, as the milestones prescribe.

## What was built

- **SPEC 6.5, P-VAL-1.** `engine/standardize/model.py`:
  - the input types `RowInput`, `AddressText` and `UnmappedHint`
  - the result types `StdValue`, `StdRow`, `ReasonRef` and `FillRef`
  - `CountStatus` with `count_status_for`, and `LocationStatus` with `location_for`
  - `AuditEvent` and `audit_events`, which carry IDs only
- **P-STD-2.** `placeholders.py` (`marker` and `is_blank`) and `settings/placeholders.toml`.
- **P-STD-1.** Name casing, digits in names and the middle initial, in `rows.py`, using M03's `title_name` and `middle_initial`.
- **P-STD-3.** `zipcode.py`, with `standardize_zip` and `ZipResult`.
- **P-STD-4, P-STD-5, B-27, B-28.** `place.py` has `standardize_city_state`, `text_disagreements` and `move_place`. `engine/geo/places.py` and `settings/places.toml` hold 24 aliases, 126 neighborhoods, the allowed pair and 56 states.
- **P-STD-8.** `units.py`: `reconcile_units`, `unit_key` and `is_unit`.
- **P-STD-6.** `dates.py`: `DateContext`, `date_context`, `parse_date`, `excel_serial` and `dob_check`. The limits are in `settings/standardize.toml`.
- **P-STD-7.** `typed.py`: `standardize_typed` and `validate_default`.
- **P-VAL-4.** `summary.py`.
- **P-VAL-2 and the order.** `rows.py`, with `standardize_row`, `standardize_table` (which reports progress) and `TableOptions`.
- **Inputs.** `inputs.py`: `build_inputs`.
- **P-VAL-3.** All the M04 reasons in `engine/reasons.py`, and a `problems.toml` entry for each decision reason.
- **Dev command.** `python -m wholecount.dev standardize`, with `--today`, `--date-order`, `--two-digit-pivot` and `--choose-suggested-header`.

## Tests

| Command | Result |
| --- | --- |
| `make test` | 1,396 passed |
| `make offline` | 55 passed |
| `make copy` | 243 passed |

`make test` and `make copy` include this report's own lint test.

New test files:
- `tests/audit/`: `test_B01_placeholders.py`, `test_B03_nassau_zips.py`, `test_B04_non_nyc_zip.py`, `test_B05_non_nyc_place_names.py`, `test_B13_day_month_order.py`, `test_B14_two_digit_year.py`, `test_B15_future_dob.py`, `test_B16_five_digits_not_a_date.py`, `test_B25_name_placeholders.py`, `test_B26_unicode_zip.py`, `test_B27_address_text_disagrees.py`, `test_B28_place_stays_out_of_street.py`, `test_B31_unrecognized_city_kept.py`, `test_B41_marble_hill.py`, `test_B43_name_case.py`, `test_B44_summary_surnames.py`, `test_A11_original_kept.py`
- `tests/rules/`: `test_P_STD_1_names.py` through `test_P_STD_8_units.py`, `test_P_READ_3_unreadable_character.py`, and `test_P_VAL_1_statuses.py` through `test_P_VAL_4_summary_rows.py`
- `tests/invariants/`: `test_standardize_properties.py` (Hypothesis) and `test_h8_standardize.py`
- `tests/unit/`: `test_places_settings.py` and `test_std_problem_rows.py`
- `tests/golden/`: `test_proof_01_08_values.py`, `test_proof_11_unit_in_both_lines.py`, `test_proof_12_13_required_digits.py`, `test_proof_17_field_types.py` and `test_example_data_standardize.py`. `CHANGES.md` gained 12 rows.
- Fixtures and support: `tests/fixtures/std_problem_rows.py` (M08 reuses it) and `tests/support/std.py`

Audit IDs closed:

| ID | Severity | Test |
| --- | --- | --- |
| B-01 | High | `tests/audit/test_B01_placeholders.py` |
| B-03 | High | `tests/audit/test_B03_nassau_zips.py` |
| B-04 | High | `tests/audit/test_B04_non_nyc_zip.py` |
| B-05 | High | `tests/audit/test_B05_non_nyc_place_names.py` |
| B-13 | High | `tests/audit/test_B13_day_month_order.py` |
| B-14 | High | `tests/audit/test_B14_two_digit_year.py` |
| B-15 | High | `tests/audit/test_B15_future_dob.py` |
| B-16 | High | `tests/audit/test_B16_five_digits_not_a_date.py` |
| B-25 | Medium | `tests/audit/test_B25_name_placeholders.py` |
| B-26 | Medium | `tests/audit/test_B26_unicode_zip.py` |
| B-27 | Medium | `tests/audit/test_B27_address_text_disagrees.py` |
| B-28 | Medium | `tests/audit/test_B28_place_stays_out_of_street.py` |
| B-31 | High | `tests/audit/test_B31_unrecognized_city_kept.py` |
| B-41 | Low | `tests/audit/test_B41_marble_hill.py` |
| B-43 | Low | `tests/audit/test_B43_name_case.py` |
| B-44 | Low | `tests/audit/test_B44_summary_surnames.py` |
| A-11 | Medium | `tests/audit/test_A11_original_kept.py` |

B-24's second half also has its rule test now: `test_P_READ_3_unreadable_character.py`.

The example files, per table, after load, map, the proposed steps and standardize, with the workbook's row 3 chosen as its header:

| File | Rows | Counted | Not counted yet | Set aside | Reasons |
| --- | --- | --- | --- | --- | --- |
| `example_clinic.csv` | 60 | 56 | 4 | 0 | `no_identifier` 3, `name_missing` 1 |
| `example_housing.xlsx` | 67 | 62 | 4 | 1 (the Total row) | `no_identifier` 3, `name_missing` 1, `address_part_missing` 1 |
| `example_partner.tsv` | 55 | 53 | 2 | 0 | `no_identifier` 2 |
| `example_portal.json` | 55 | 52 | 3 | 0 | `no_identifier` 2, `name_missing` 1, `address_part_missing` 3, `placeholder_in_value` 1, `address_incomplete` 1, `zip_not_valid` 1 |
| `example_state.xml` | 50 | 48 | 2 | 0 | `no_identifier` 2 |

`no_identifier` adds up to 12, the twelve planned rows with neither a Client_ID nor a date of birth. In every table, `entered_lost` is 0.

## Done list

- [x] `make test`, `make offline` and `make copy` are green: 1,396, 55 and 243 passed.
- [x] B-01, B-03, B-04, B-05, B-13, B-14, B-15, B-16, B-25, B-26, B-27, B-28, B-31, B-41, B-43, B-44 and A-11 each have a passing test and a `done` line in `tests/audit/INDEX.md`.
- [x] Every decision reason has a `problems.toml` entry, one flag and a triggering row (`test_std_problem_rows.py`). The property test and the A-11 test show `entered` always equals the input.
- [x] A row with a name and an ID is counted whatever its address holds (`test_P_VAL_2_count_rule.py` and the property test), and the table balance property passes (H4).
- [x] `tests/golden/CHANGES.md` lists every changed sheet and row from this milestone, 12 rows.
- [x] No new dependency, and no fuzzy matching: every lookup is exact.
- [x] The decisions are logged above.
- [x] This report is written, the branch is pushed, and the pull request is open.

## Windows checks

- [ ] 1. `py -3.12 -m venv .venv`
- [ ] 2. `.venv\Scripts\activate`
- [ ] 3. `pip install --require-hashes --no-deps -r requirements-dev.lock`
- [ ] 4. `python -m pytest -q`. All pass.
- [ ] 5. `python -m wholecount.dev standardize "C:\path\to\a real export.xlsx"`. Check two sums:
  - `counted`, `not_counted_yet` and `set_aside` add up to `rows`.
  - `outside_nyc`, `no_fixed_address`, `address_problem` and `to_place` add up to `counted`.

  `entered_lost` must be 0.
- [ ] 6. Read the `reason` lines. `name_missing` and `no_identifier` are the only ones that keep a client out of the count, so they should match the blanks you know about. `city_not_recognized` should be your typos and out-of-city towns. A count that looks wrong is the thing to tell me about.
- [ ] 7. If `date_order_unclear` or `date_both_ways` appears, rerun with `--date-order month` or `--date-order day` and confirm those rows clear. If `date_two_digit_year` appears, try `--two-digit-pivot 26` and see the count change.
- [ ] 8. Run `python -m wholecount.dev standardize wholecount\sample_data\example_clinic.csv wholecount\sample_data\example_housing.xlsx wholecount\sample_data\example_partner.tsv wholecount\sample_data\example_portal.json wholecount\sample_data\example_state.xml --today 2026-10-30 --choose-suggested-header`. The `counted`, `not_counted_yet` and `set_aside` lines per table equal the `standardize` section of `EXPECTED.json` and the table above. The `reason no_identifier` lines add up to 12.

The dev command prints counts and reason IDs only. It never shows a client value.

## Screens

None. M04 has no UI.

## Not done

Nothing.
