# M02: Fields, source systems and matching columns

## Goal

Define the fields every file maps onto, group files into source systems, and match each table's columns to fields by meaning rather than by file order. Check every mapped column against its values, support per-table defaults, and work out each table's date order and two-digit-year rule from evidence and the operator's answers. Block Process for a missing counting field or an identifier column full of Social Security numbers. Nothing in this milestone changes a cell value.

## Spec sections

- SPEC 4.1 (canonical fields and what "required for mapping" means), 4.2 (source systems), 4.3 (letters), 6.2 (P-MAP-1 to P-MAP-8), H6 (defaults never replace a value).
- Audit: B-21, B-22, B-23, B-48, B-49. Fix plan 4.1 step 4 (P-MAP-7).

## Depends on

M01 merged. It uses `LoadedTable`, `settings/loader.py`, `letter_for_index`, `engine/read/sensitive.py` (`looks_like_ssn_column`) and the dev command from M00 and M01.

## Branch

`build/m02-columns`

## Read first

- `SPEC.md` 4.1 to 4.3, 6.2 and 17. Then the findings: `docs/audit/B-values.md` B-21 (line 486), B-22 (510), B-23 (531), B-48 (986) and B-49 (1005). The inputs are in `docs/audit/B-scripts/b21_mapping.py`, `b22_mapping_check.py` and `b36_mapping_end_to_end.py`.
- `legacy/app.py` (reference only): `guess_mapping` :2767 (its docstring explains the precedence rules), `REQUIRED_FIELDS` :134, `DEFAULT_SCHEMA` :144, `get_schema` :174, `schema_required_roles` :183, `MIN_MAPPED_FIELDS` :200, and the name and address word lists in `auto_prep_ops` :2867 for the deny words.
- `legacy/column_check.py`: `check_field` :62 (every per-field check to port), `ROLE_WORDS` :239, `better_column` :258, `check_mapping` :311.
- `legacy/crosswalk_server.py`: `_guess_for` :282 and `_match_custom` :298. The raw substring match (`key in ck or ck in key`) is the cause of B-22. Do not reproduce it.
- `wholecount/sample_data/` from M01. Its five example files are the golden inputs, and the `map` section of its `EXPECTED.json` holds the expected answers. The legacy samples in `tests/data/legacy_sample/` are for reading tests only.

## What to build

### 1. Schema (`engine/schema.py`, SPEC 4.1)

- `FieldType` (`text`, `whole_number`, `decimal`, `date`, `yes_no`), frozen `Field(key, label, type, required, required_for_mapping, needed_to_count, default, max_length, builtin, enabled)`, and `Schema` (ordered fields).
- `default_schema()` returns the 11 canonical fields in this order with these flags (SPEC 4.1).
  - `required` (a column must exist, or Process is blocked): First_Name, Last_Name and Client_ID. Client_ID's requirement is met when the table maps either Client_ID or Date_of_Birth (SPEC 4.1), so a table blocks on it only when it maps neither, and the block names both fields.
  - `required_for_mapping` (needed to place the address, never to count): Address_1, City, State and Zip. A missing address column does not block Process (P-VAL-2).
  - Neither flag: Middle_Initial (one letter), Address_2, Program, Date_of_Birth.
  - Date_of_Birth is built in and enabled by default. The operator may disable it. Built-in fields can't be removed or retyped.
- The operator may make Client_ID optional for the batch (`schema.with_required`). That only removes the column requirement. The count rule still needs a Client_ID or a valid date of birth on each row (M04). Custom fields have a unique key matching `^[A-Za-z][A-Za-z0-9_]{0,39}$` (case-insensitive, no clash with a built-in), a type, an optional default kept as text, a maximum length of 1 to 1,000 or none, a `required` flag, and a `needed_to_count` flag, off by default. A required custom field with no column blocks Process only when it's marked `needed_to_count` (SPEC 4.1). Otherwise Match your columns shows a warning, and M04 gives every row of that table a soft reason. A `needed_to_count` field holds the count when it is missing or fails (M04), and a required field that is not marked that way never does. Defaults are validated against the type in M04.
- `to_dict` and `from_dict` round-trip. They will feed saved set-ups later.

### 2. Source systems and letters (`engine/systems.py`, SPEC 4.2 and 4.3)

- `SourceSystem(system_id, display_name, letters)`. `default_systems(files)` makes one system per file, named by the file name without its extension. `group(systems, letters)` merges systems, and `rename` edits a display name. The grouping only records which files share an identifier space. P-DUP-3 and P-ID-3 use it later.
- `LetterBook`: `assign(fingerprint, name)` returns the next letter, returns the same letter for a file with the same fingerprint, and never reuses a letter released in the batch. Letters are display only and are not part of any key (SPEC 5.1). Change M01's `load_files` to take a `LetterBook` instead of numbering from zero, and update its tests, including the key stability tests, which must still pass with letters in any order.

### 3. Mapping (`engine/mapping.py`, P-MAP-1 and P-MAP-3)

- Types: `ColumnRef(index, name, derived=False, derived_from=None, derived_kind=None)`, `ColumnProfile` (filled share, distinct count, shares that are date-shaped, numeric, unit-like, street-like and SSN-shaped, and up to three sample values for the screen), `FieldAssignment(field, column, score, alternatives)`, `MappingQuestion(field, candidates)` and `TableMapping(table_key, assignments, questions, checks)`.
- `profile_columns(table, derived)` and `auto_map(schema, profiles) -> TableMapping`. Scoring is by name only (P-MAP-1), over normalized header tokens.
  - 100 for an exact field name or label, 90 for an exact synonym, 60 for a contiguous run of the field's phrase tokens where every other word is an allowed extra.
  - A word in the deny group for the field excludes the column outright. A mailing or billing word subtracts 40 from address fields, so Mailing loses to Home but is still offered when it is the only address column, and shows in `alternatives` (P-MAP-8: "lose to" is a penalty, not an exclusion).
  - A bare word like `last` or `first` matches only as the whole header, never inside a longer one.
  - A trailing `2`, `line 2` or `address2` means Address_2 and excludes the column from Address_1 (B-49).
  - Date-named headers never fill name fields or Program. A header with an ID word never fills Program, and a header with a program, case, household, parent or provider word never fills Client_ID (B-22).
- Value rules: a column whose non-blank values are at least 60 percent date-shaped (any of ISO, `m/d/y`, `d.m.y`, `m-d-yy`) never fills Program.
- Assignment is global, not first-come. One column fills one role. A column goes to the field that scores it highest. When two columns tie at the top for one field, assign neither and add a `MappingQuestion`, so the result never depends on column order. The questions block Process the way an unmapped required field does.
- P-MAP-3. A derived column may fill a field only when the table has no real column that scores for it, or when it was derived from the very column the real mapping chose for that field (a split of the chosen column replaces it, as in the old build). Otherwise it is only available as an operator pick, `TableMapping.with_choice(field, column)`. The old build also let a calculated ZIP column win Zip ahead of a real one because the operator added that step on purpose. Keep that for `derived_kind == "calculated"`, because a person made it on purpose (P-MAP-8).
- `settings/mapping.toml`, starting contents. Complete every field's lists from the legacy candidate lists in `guess_mapping`.
  ```toml
  [allowed_extras]
  all = ["client", "patient", "participant", "consumer", "resident", "member", "legal", "current", "primary"]
  address = ["home", "residential", "residence", "street", "of", "the"]
  [deny]
  person_fields = ["emergency", "contact", "guardian", "parent", "caseworker", "staff", "employer", "landlord", "provider", "referral", "spouse", "partner", "kin", "teacher", "doctor", "physician", "counselor", "supervisor", "manager", "worker"]
  address_fields = ["emergency", "contact", "employer", "work", "birth", "previous", "prior", "former", "school", "landlord", "provider", "agency", "site"]
  name_fields = ["visit", "visited", "seen", "date", "time", "dob", "birth", "created", "updated", "modified"]
  client_id = ["program", "case", "household", "parent", "provider", "site", "grant", "contract", "agency", "enrollment", "service", "order"]
  program = ["id", "identifier", "code", "number", "num", "no", "key", "uid", "date", "start", "end", "time"]
  [penalty]
  mailing = ["mailing", "billing"]
  [synonyms]
  First_Name = ["first_name", "firstname", "f_name", "first", "given_name", "given", "forename"]
  Last_Name = ["last_name", "lastname", "l_name", "last", "surname", "family_name", "family"]
  Client_ID = ["client_id", "eto_client_id", "ehr_id", "patientnumber", "patient_number", "system_id", "participant_id", "uid", "pid", "id"]
  Address_1 = ["address_1", "addr1", "address", "street", "full_address", "address_line", "street_address"]
  Address_2 = ["address_2", "addr2", "address_line_2", "street_address_2", "apt", "unit", "suite"]
  Date_of_Birth = ["dob", "date_of_birth", "birth_date", "birthdate", "birthday"]
  [phrases]
  First_Name = [["first", "name"], ["given", "name"]]
  Last_Name = [["last", "name"], ["family", "name"]]
  Address_1 = [["street", "address"], ["address", "line", "1"], ["address"]]
  ```

### 4. Column check (`engine/mapping.py`, P-MAP-2)

- `check_field(field, profile) -> FieldCheck(status, reason_id, params, better)` with `status` of `ok`, `check` or `problem`. Port every `check_field` rule to a reason ID, with its numbers as `int` params, and register each sentence under `copy/mapping.check.*`. These sentences state computed facts about the data, so they take no claim ID.
- Add the four spec checks: `col_program_looks_like_dates` (US and other date shapes, not only ISO), `col_program_looks_like_codes`, `col_address1_mostly_units`, `col_address2_mostly_streets` (at least 50 percent street-shaped, with more than 5 values), and `col_name_mostly_one_value` (more than 10 values and one value above 80 percent).
- `better_column` as the old build did (the candidate passes its check, fills at least half the rows, and rescues at least 2 rows or 25 percent of the rows), but candidates now come from the scoring above instead of `ROLE_WORDS`. A warning offers the one-click fix `with_choice`. A warning never blocks.
- `process_blocks(schema, mappings, defaults, profiles) -> list[ProcessBlock(table_key, field, kind)]`, the one function Process and the fast path ask. They name each table and field. Only fields with `required` can block, so a table with no address column still runs (P-VAL-2).
  - `missing_required`: First_Name or Last_Name with no column, Client_ID when the table maps neither Client_ID nor Date_of_Birth (one block naming both), or a `needed_to_count` custom field with no column. A field with an open question counts as having no column. A default for that table that supplies the field clears the block.
  - `ssn_shaped_id` (P-MAP-7, fix plan 4.1): a column mapped to Client_ID where `looks_like_ssn_column` is true (more than half of its non-blank values, M01's rule). A default does not clear it. Copy `map.block.ssn_shaped_id`: "These identifiers look like Social Security numbers. Map a different identifier, or drop this column." It states a computed fact, so it takes no claim ID.

### 5. Defaults and date order (P-MAP-4 and P-MAP-5)

- `engine/defaults.py`. `SourceDefault(table_key, field, value)`, `default_for(...)`, and `fill_default(entered, default, is_blank) -> DefaultUse(value, used)`. It never replaces a value the file supplied. M04 passes the placeholder-aware `is_blank`. The caller records each use by record key and field for the audit.
- `engine/dateorder.py`, P-MAP-5 and P-MAP-6. `DateOrder` (`month_first`, `day_first`), `DateEvidence(month_first_only, day_first_only, either, other)`, `collect_evidence(values, meta)`, `decide(evidence, answer) -> DateDecision(order, state)` and `DateFieldSetting(order, pivot)`.
  - Count `m/d/y`, `d/m/y` and dotted or dashed forms with the same separator twice. A second part over 12 with a first part up to 12 is month first only, and the reverse is day first only. Both parts up to 12 is `either`, including equal parts like `03/03/1990`. Both over 12 is `other`. ISO forms and `.xlsx` date cells are skipped.
  - `state` is one of `not_needed` (no value needs an order), `resolved` (the unambiguous values agree, so that order is used and shown), `ask_no_evidence` (none are unambiguous, but `either` is above 0) or `ask_both_ways` (the column holds both kinds). An operator answer settles any of them. Until answered, M04 sends ambiguous values to review in `ask_no_evidence`, and every non-ISO value to review in `ask_both_ways`. After an answer, only values that contradict the chosen order stay in review.
  - Copy `map.date_order_question`: "This table writes dates as month/day or day/month?", with the counts passed in as ints. Copy `map.date_both_ways`: "Dates in this column are written both ways," shown beside the same question.
  - `TwoDigitRule(pivot)` is the P-MAP-6 rule, "Two-digit years up to NN mean 20NN, otherwise 19NN," with `pivot` from 0 to 99. `suggest_pivot(field_key, today)` returns `today.year % 100` for Date_of_Birth and none for any other field. `today` is always a parameter. The rule and the order answer are stored per table and date field in `DateFieldSetting`, which feeds the session's `date_orders`. Without a rule, M04 sends two-digit years to review (P-STD-6). `rule_needed(values, meta)` is true only when the column holds a non-ISO date with a two-digit year, so a table of four-digit years never asks. Copy `map.two_digit_rule_question` with the suggested NN passed as an int.
- Extend the dev printer's scope type so it also accepts the built-in field names (a closed set), and update the M00 test. `python -m wholecount.dev columns <path> [...]` prints, per table (`A.1`, `A.2`, headed by letter and table number), `fields_mapped`, `required_unmapped` with one line per built-in field name, `questions_open`, `checks_ok`, `checks_check`, `checks_problem`, `date_questions`, `date_both_ways`, `ssn_shaped_ids` and `process_blocked` (1 or 0).

### Notes from the spec review (SPEC 1.1, section 4.1)

- Client_ID's column requirement is met when a table maps either Client_ID or Date_of_Birth. `process_blocks` blocks a table only when it maps neither, and names both fields in one block. Add `test_P_MAP_client_id_or_dob.py`: a table with only Date_of_Birth mapped isn't blocked, and a table with neither is.
- A required custom field with no column blocks Process only when it's marked `needed_to_count`. Otherwise Match your columns shows the warning `custom_required_no_column`, and M04 gives every row of that table the soft reason "Required field has no column." Add both cases to `test_schema.py`.

## Tests to write

- `tests/audit/test_B21_first_match_by_position.py`. Emergency-contact name columns before the client's: First_Name maps to `First Name`. `Provider First Name` loses to `Client First Name`. `Mailing *` before `Home *`: all four address fields map to Home, and Mailing appears in `alternatives`. `Place of Birth City` before `City of Residence`: City maps to the latter. Each case is run in three column orders and must give the same mapping by name.
- `tests/audit/test_B22_program_date_and_id.py`. `Program Start Date` holding `03/04/2024` leaves Program unmapped. A column named `Program` that holds US dates is rejected by its values. `Service Date` before `Service Provider` never maps the date. A file whose only ID-like column is `Program ID` leaves both Client_ID and Program unmapped. With no date of birth column either, `process_blocks` gives one `missing_required` block naming Client_ID and Date_of_Birth, and no column fills two roles.
- `tests/audit/test_B23_split_does_not_hijack.py`. Real `First Name` and `Last Name` plus a derived pair from `Caseworker Name`: the real ones win. Real `Street Address` plus a derived street from `Employer Address`: the real one wins. With no real name columns the derived pair is offered. A split of the chosen address column replaces that column. An operator pick of any derived column is honored.
- `tests/audit/test_B48_last_visit.py` (`[First Name, Last Visit, Surname]` maps `Surname`; `Forename` and `Surname` alone map both names) and `tests/audit/test_B49_address_line_2.py` (`[Address Line 2, Address Line 1]` and `[Street Address 2, Street Address]` map each role once).
- Rule tests under `tests/rules/`.
  - `test_P_MAP_1_auto_mapping.py`: the tiers, each deny group, bare words matching only whole headers, a tie giving a question and no assignment, and a Hypothesis property that shuffling the columns never changes the mapping by name when no tie exists.
  - `test_P_MAP_2_column_check.py`: every ported check and the four new ones with the input and the expected `reason_id`, `better_column` suggesting `Zip` when the mapped column is blank, and `process_blocks` blocking on a missing required field while a warning does not.
  - `test_P_MAP_3_derived_columns.py`, `test_P_MAP_4_defaults.py` (supplied value kept, blank filled, a default supplies a required field) and `test_P_MAP_5_date_order.py`.
  - `test_P_MAP_6_two_digit_rule.py`, `test_P_MAP_7_ssn_client_id.py` and `test_P_MAP_8_weights.py`.
- `test_P_MAP_5_date_order.py` cases (the evidence half of B-13; M04 closes the rest). `[13/04/1990, 03/04/1990]` gives `resolved`, day first. `[03/04/1990]` alone gives `ask_no_evidence`. `[04/13/1990, 13/04/1990]` gives `ask_both_ways`, shows both counts and carries `map.date_both_ways`. All-ISO gives `not_needed`. An operator answer settles `ask_no_evidence` and `ask_both_ways`. Each case is run in three row orders with the same state.
- `test_P_MAP_6_two_digit_rule.py`. `suggest_pivot("Date_of_Birth", date(2026, 10, 30))` is 26, and any other field gives none. `TwoDigitRule(pivot=26)` is stored per table and date field, so two tables hold different pivots. A pivot below 0 or above 99 is refused. `rule_needed` is true only when the column holds a non-ISO date with a two-digit year, so a table of four-digit years never asks. The question copy takes NN as an int and is checked in `tests/copy/`.
- `test_P_MAP_7_ssn_client_id.py` (fix plan 4.1). A Client_ID column of 60 percent `123-45-6789` values gives `ssn_shaped_id`, naming the table and field and no value. Exactly half does not block, and more than half does. A default for Client_ID does not clear it. Remapping to another column, or dropping the column, clears it. The same digits in a column the operator mapped to Program never block. Run the check with the same values in three orders.
- `test_P_MAP_8_weights.py`. Mailing loses to Home in every column order and is offered when it is the only address set. A `calculated` derived ZIP wins Zip over a real `ZipCode` column, and a `split` ZIP taken from some other column does not. These pin the two weights the spec names, so a later change to either fails here.
- `tests/unit/test_schema.py` (the table in SPEC 4.1; the three flags, with First_Name, Last_Name and Client_ID `required` and Client_ID met by Date_of_Birth, Address_1, City, State and Zip `required_for_mapping`, and a table with no address columns not blocked; custom field validation including `needed_to_count`; round trip; Client_ID optional; Date_of_Birth enabled) and `tests/unit/test_systems.py` (one system per file, default names, grouping, `LetterBook` reuse and no reuse after release).
- `tests/golden/test_example_data_mapping.py`. The five example files in `wholecount/sample_data/`, with the workbook's header row chosen as `EXPECTED.json` says. For every table, the auto-mapping (before any tidy-up step) equals `map.auto` in `EXPECTED.json`, field by field, and `process_blocks` equals the blockers listed there. The jammed-name CSV has First_Name and Last_Name unmapped until M03's split step. Every table maps Client_ID or Date_of_Birth, so no Client_ID block appears. A missing City, State or Zip never appears in the list. The `map.after_steps` half is M03's.

## Done when

- [ ] `make test`, `make offline` and `make copy` are green, with the counts in the report.
- [ ] B-21, B-22, B-23, B-48 and B-49 each have a passing test and a line in `tests/audit/INDEX.md`. P-MAP-6, P-MAP-7 and P-MAP-8 have rule tests.
- [ ] The mapping golden test passes for all five example files, and the shuffle property test passes.
- [ ] No new dependency outside the approved set.
- [ ] The report lists the decisions logged above: ties become questions, a derived column replacing the column it came from, the `Service Provider` reading, the change to `load_files`, and the `DateDecision` state names. Mailing losing and the calculated ZIP precedence now come from P-MAP-8, so the report cites the spec for them.
- [ ] `docs/milestones/M02-REPORT.md` is written, the branch is pushed, the pull request is open, and work has stopped.

## Windows checks for Joe

1. `py -3.12 -m venv .venv`
2. `.venv\Scripts\activate`
3. `pip install --require-hashes --no-deps -r requirements-dev.lock`
4. `python -m pytest -q`. All pass.
5. `python -m wholecount.dev columns "C:\path\to\a real export.xlsx"` with one of your own client lists. Each table prints as `A.1`, `A.2` and so on. Check that `fields_mapped` is close to the number of columns you would map by hand, and that `required_unmapped` lists only fields you agree are missing (for example First_Name when the file has one combined Name column).
6. Try a file whose first columns are an emergency contact or a mailing address. Expect the client's own columns to be the ones mapped.
7. Try a file with dates written like 03/04/1990. Expect `date_questions 1` unless the file also has a date such as 13/04/1990 that settles the order. A file that writes some dates each way should print `date_both_ways 1`.
8. Try a file whose identifier column is a Social Security number. Expect `ssn_shaped_ids 1` and `process_blocked 1`.
9. Run it on the five files in `wholecount\sample_data\`. Expect `process_blocked 1` only for the jammed-name CSV (First_Name and Last_Name, closed by M03's split step), as the `map` section of `EXPECTED.json` says.

The dev command prints counts and built-in field names only. It never shows a client value or a column header.

## Out of scope

- Creating derived columns, tidy-up steps and proposals (M03). The tests here build derived `ColumnRef`s by hand.
- Changing any value, placeholders, standardizing, parsing dates, applying the two-digit rule, row checks (M04). This milestone only counts date evidence and stores the operator's order and rule.
- Counting a row, the count rule and the location status (M04). `needed_to_count` is a flag here and takes effect there.
- The Your columns and Match your columns screens, the one-click fix button and the date-order question dialog (M11).
- Saving set-ups (M08 and M09).
