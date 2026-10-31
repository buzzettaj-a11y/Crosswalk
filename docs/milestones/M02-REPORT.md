# M02 report

## Questions for Joe

None block the milestone. These are the decisions the milestone asked me to log, then the choices I made where the text left room.

Decisions the milestone named:
1. **Ties become questions.** When two columns score the same for a field, neither is assigned. The table gets a `MappingQuestion`, and the open question blocks Process the way a missing required column does. So the result never depends on which column comes first.
2. **A split replaces the column it came from.** When a tidy-up step splits the column the mapping chose, for example `Full_Address`, the split's street, city and ZIP replace it. A split of any other column fills a field only when no real column scores for that field, or when the operator picks it.
3. **"Service Provider" is not a program.** `service` alone is a program synonym, but `provider` isn't an allowed extra word, so `Service Provider` scores nothing for Program. `Service Date` is denied by its date word. Neither header maps Program, in either order.
4. **`load_files` now takes a `LetterBook`.** Letters come from the batch's book, so a re-added file gets its letter back and a released letter is never reused. A test loads the five example files after three letters were used and released. The letters come out D to H, and every key is unchanged.
5. **The date decision's state names** are `not_needed`, `resolved`, `ask_no_evidence` and `ask_both_ways`. An operator answer keeps the state and sets `answered`, so the screen can still say why it asked.
6. **Mailing losing to Home, and a calculated ZIP winning over a real one,** come from P-MAP-8. `test_P_MAP_8_weights.py` pins both weights.

Choices on the most conservative reading:
- **How headers are split into words.** Headers split on punctuation, at lowercase-to-uppercase changes (`FirstName`) and at letter-to-digit changes (`Address1`). Synonyms are split the same way, so `PatientNumber` and `patient_number` compare equal.
- **"address" is an allowed extra word for address fields.** That lets a JSON key like `address.city` fill City. It can't push a column into the wrong address field, because the field's own word still has to be there.
- **A derived column is scored by its suffix.** M03 will name split columns after their source plus `_first`, `_last`, `_street`, `_zip` and so on, so a derived column scores 90 for the field its suffix names and nothing else. The suffix list is in `settings/mapping.toml` under `derived_suffix`, so M03 can change it there.
- **A blocked table with no Client_ID and no date of birth** gets one `ProcessBlock` with `field="Client_ID"` and `also="Date_of_Birth"`, so it names both fields.
- **A custom field that's required but not `needed_to_count`** gives a `MappingWarning` with the kind `custom_required_no_column`, never a block.
- **The two-digit-year question** reads "Two-digit years up to 26 mean the 2000s, otherwise the 1900s." Writing 20NN with the number as an int would print 205 for a pivot of 5.
- **The date-order question** carries its three counts in the same sentence.
- **`col_address2_mostly_streets` is a check, not a problem.** Warnings never block anyway.
- **Fixed a mistake in my M01 plan.** The example CSV's `Full_Address` is a synonym for Address_1, so it maps there before any step, and the plan had said it would be unmapped. The mapper is right per the spec, so I changed the plan in the script and regenerated `EXPECTED.json`, as the milestones prescribe. The section is now `map.auto`, the name this milestone's golden test reads. The generator also now keeps the workbook untouched when its cells haven't changed, so regenerating doesn't churn the .xlsx in git.
- **`dev columns` maps only included tables.** At load, the example workbook's `Clients` table is unticked until its header row is chosen, so the dev command prints nothing for it. Windows check 9 below says what to expect.

## What was built

- **SPEC 4.1.** `engine/schema.py` has `FieldType`, `Field`, `Schema` and `default_schema()`, with the 11 fields and their flags. It also covers custom field validation, Client_ID made optional, Date_of_Birth disabled, and the round trip.
- **SPEC 4.2, 4.3.** `engine/systems.py` has `SourceSystem`, `default_systems`, `group`, `rename`, `system_for` and `LetterBook`.
- **P-MAP-1, P-MAP-3, P-MAP-8.** `engine/mapping.py` has `ColumnRef`, `ColumnProfile`, `profile_columns`, `name_score`, `auto_map` with global assignment and questions, the derived-column rules, and `TableMapping.with_choice`. The word lists are in `settings/mapping.toml`.
- **P-MAP-2, P-MAP-7.** Also in `engine/mapping.py`:
  - `check_field`, with 24 reason IDs, each with a sentence under `mapping.check.*`
  - `better_column` and `check_mapping`
  - `process_blocks`, with the kinds `missing_required` and `ssn_shaped_id`
  - `mapping_warnings`
- **P-MAP-4.** `engine/defaults.py`.
- **P-MAP-5, P-MAP-6.** `engine/dateorder.py` has `collect_evidence`, `decide`, `TwoDigitRule`, `DateFieldSetting`, `suggest_pivot` and `rule_needed`.
- **Copy.** The checks, the better-column offer, the tie question, the three block sentences, the custom-field warning, and the date and two-digit questions.
- **Dev command.** `python -m wholecount.dev columns`. The printer now also accepts a table scope like `A.1` and the built-in field names, a closed set.

## Tests

| Command | Result |
| --- | --- |
| `make test` | 581 passed |
| `make offline` | 55 passed |
| `make copy` | 109 passed |

`make test` and `make copy` include this report's own lint test.

New test files:
- `tests/audit/`: `test_B21_first_match_by_position.py`, `test_B22_program_date_and_id.py`, `test_B23_split_does_not_hijack.py`, `test_B48_last_visit.py`, `test_B49_address_line_2.py`
- `tests/rules/`: `test_P_MAP_1_auto_mapping.py` (with the shuffle property test), `test_P_MAP_2_column_check.py`, `test_P_MAP_3_derived_columns.py`, `test_P_MAP_4_defaults.py`, `test_P_MAP_5_date_order.py`, `test_P_MAP_6_two_digit_rule.py`, `test_P_MAP_7_ssn_client_id.py`, `test_P_MAP_8_weights.py`, `test_P_MAP_client_id_or_dob.py`
- `tests/unit/`: `test_schema.py`, `test_systems.py`
- `tests/golden/test_example_data_mapping.py`
- `tests/copy/test_mapping_copy.py`
- `tests/support/mapping.py`

Audit IDs closed:

| ID | Severity | Test |
| --- | --- | --- |
| B-21 | High | `tests/audit/test_B21_first_match_by_position.py` |
| B-22 | High | `tests/audit/test_B22_program_date_and_id.py` |
| B-23 | High | `tests/audit/test_B23_split_does_not_hijack.py` |
| B-48 | Low | `tests/audit/test_B48_last_visit.py` |
| B-49 | Low | `tests/audit/test_B49_address_line_2.py` |

The example files map as planned:
- The clinic CSV maps Client_ID, Address_1, Date_of_Birth and Program. It's blocked on First_Name and Last_Name until M03 splits the jammed names.
- The other four tables map 10 or 11 fields each, with no blocks.
- No table blocks on Client_ID, City, State or Zip.

## Done list

- [x] `make test`, `make offline` and `make copy` are green: 581, 55 and 109 passed.
- [x] B-21, B-22, B-23, B-48 and B-49 each have a passing test and a `done` line in `tests/audit/INDEX.md`. P-MAP-6, P-MAP-7 and P-MAP-8 have rule tests.
- [x] The mapping golden test passes for all five example files, and the shuffle property test passes.
- [x] No new dependency. The locks are unchanged.
- [x] The decisions are logged above, and the spec is cited for the two weights.
- [x] This report is written, the branch is pushed, and the pull request is open.

## Windows checks

- [ ] 1. `py -3.12 -m venv .venv`
- [ ] 2. `.venv\Scripts\activate`
- [ ] 3. `pip install --require-hashes --no-deps -r requirements-dev.lock`
- [ ] 4. `python -m pytest -q`. All pass.
- [ ] 5. `python -m wholecount.dev columns "C:\path\to\a real export.xlsx"` with one of your own client lists. Each table prints as `A.1`, `A.2` and so on. Check that `fields_mapped` is close to the number of columns you'd map by hand, and that `required_unmapped` lists only fields you agree are missing, for example First_Name when the file has one combined Name column.
- [ ] 6. Try a file whose first columns are an emergency contact or a mailing address. Expect the client's own columns to be the ones mapped.
- [ ] 7. Try a file with dates written like 03/04/1990. Expect `date_questions 1` unless the file also has a date such as 13/04/1990 that settles the order. A file that writes some dates each way should print `date_both_ways 1`.
- [ ] 8. Try a file whose identifier column is a Social Security number. Expect `ssn_shaped_ids 1` and `process_blocked 1`.
- [ ] 9. Run it on the five files in `wholecount\sample_data\` (`example_clinic.csv`, `example_housing.xlsx`, `example_partner.tsv`, `example_portal.json` and `example_state.xml`). Expect `process_blocked 1` only for the clinic CSV, which is blocked on First_Name and Last_Name until M03's split step, as the `map` section of `EXPECTED.json` says. The workbook prints no table, because its `Clients` table stays unticked until its header row is chosen.

The dev command prints counts and built-in field names only. It never shows a client value or a column header.

## Screens

None. M02 has no UI.

## Not done

Nothing.
