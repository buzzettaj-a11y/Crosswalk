# M03: Tidy-up steps

## Goal

Build the five tidy-up rules (clean columns, split by a delimiter, split a jammed address, split a jammed name, calculated ZIP), the step model around them, and the proposals that suggest them. Steps only add columns and never change a source cell (H6). Along the way, build the pieces M04 needs early: name casing, the NYC ZIP table and the middle-initial rule.

## Spec sections

- SPEC 6.3 (P-PREP-1 to P-PREP-5). Also P-STD-1 (casing only) and P-STD-3 (the ZIP table only), because P-PREP-1 and P-PREP-5 need them. M04 consumes both and finishes the rest. P-STD-2 (the meaning of soft) and P-VAL-3 (the three flags) for `Reason`. SPEC 13.1 for `tests/golden/CHANGES.md`.
- Audit: B-06, B-07, B-08, B-09, B-10, B-11, B-12, B-29, B-30, B-32, B-33, B-42.

## Depends on

M02 merged (mapping, `ColumnRef` with `derived` and `derived_from`). M01 for `LoadedTable`.

## Branch

`build/m03-tidy-up`

## Read first

- `SPEC.md` 6.3, P-STD-1, P-STD-2 (the soft definition only), P-STD-3, P-VAL-3, 13.1 and H6. Then the findings in `docs/audit/B-values.md`: B-06 (line 198), B-07 (220), B-08 (237), B-09 (254), B-10 (271), B-11 (289), B-12 (311), B-29 (647), B-30 (663), B-32 (702), B-33 (719), B-42 (891). Inputs are in `docs/audit/B-scripts/` (`b05_address_split.py`, `b06_address_cities.py`, `b07_address_pipeline.py`, `b09_names.py`, `b26_calc_zip.py`, `b27_name_split_api.py`).
- `legacy/app.py` (reference only): `_ZIP_TAIL_RE` :401, `_UNIT_DESIGNATOR` :416, `_UNIT_TAIL_RE` :420, `_split_unit` :433, `_normalize_separators` :463, `tidy_fragment` :478, `split_jammed_address` :496, `split_jammed_name` :597, `normalize_middle_initial` :661, `_UNIT_WORDS` :753, `_looks_like_unit` :774, `DELIMITERS` :865, `_MAC_NAMES` :881, `_SMART_MAP` :890, `smart_title_name` :927, `smart_title_address` :950, `sanitize_special` :955, `op_clean` :993, `op_split_delim` :1012, `op_split_jammed` :1035, `op_split_name` :1049, `op_calc_zip` :1067, `apply_prep_ops` :1113, `describe_op` :1134, `auto_prep_ops` :2867.
- Proof workbook, sheets 03, 09 and 10: `legacy/tools/make_proof_workbook.py` lines 135, 220 and 270 hold each row's input and its `want=` values (the workbook file only shows the Expected text).
- Old behavior to not repeat. The no-comma path guesses the city from the last 1 to 3 words against a table, so `Grand Concourse` loses its last word (:567). A spaced dash becomes a comma even inside a house number (:473). The last comma segment becomes the city even when it is not one (:538). A unit segment swallows the city. Three-token names make the second token a middle initial. Titles and suffixes become names. The calculated ZIP keeps any five leading digits (:1087).

## What to build

### 1. Steps (`engine/prepare/steps.py`)

- `Step(step_id, kind, params, origin, removed)`. `kind` is `clean`, `split_delim`, `split_address`, `split_name` or `calc_zip`. `origin` is `proposed` or `added`. A removed step is kept and can be restored.
- `apply_steps(table, steps, resolver=None) -> PreparedTable`. Steps run in the listed order and may read an earlier step's output. Each output column is `PreparedColumn(name, values, step_id, source_column, kind)`. Names are made unique against existing columns. `PreparedTable.column_refs()` gives M02 the `ColumnRef`s with `derived`, `derived_from` and `derived_kind` (`split`, `clean` or `calculated`).
- Per-row flags are reason IDs in `engine/reasons.py` (`Reason(id, severity, flag)`). Severity `decision` puts the problem on Fix problems. Severity `note` is audit only and gets no `problems.toml` entry. `flag` is one of `holds_count`, `location` or `soft` (P-VAL-3, one flag per kind), and notes have none. A soft reason does not block counting, and its likely action is "Accept all as they are" (P-STD-2). Add the reasons below and a `copy/problems.toml` entry (`title`, `means`, `check`, `excel`) for each decision reason. Tidy-up reasons are `location` or `soft` and never `holds_count`, because none of them makes a P-VAL-2 condition fail. An address problem from a tidy-up step stops a row from being mapped, never from being counted.
  - `address_extra_text` ("Address has extra text: check it") is `location`. `name_order_unclear` ("Name has three or more words: check which is the surname") and `name_extra_tokens` ("Name has extra words: check them") are `soft`. The titles for the first two are the spec's. The third is plain wording to log.
  - Notes: `zip_had_9_digits`, `zip_found`, `zip_kept`, `zip_not_worked_out`, `no_street` and `no_lookup_available`. The calculated-ZIP notes sit in `<name>_note` cells and the others in the audit.
- A step that changed nothing returns `amber=True` with an `amber_reason` ID (for example `split_found_no_delimiter`, `clean_changed_nothing`, `no_lookup_available`).
- Output names follow the old build so the mapper's derived-column rule works. Address: `<col>_street`, `_address2`, `_city`, `_state`, `_zip`, `_extra`. Name: `_first`, `_middle`, `_last`, `_title`, `_credential`, `_suffix`, `_extra`. Clean: `<col>_clean`. Delimiter: the given names, else `<col>_1`, `<col>_2`.
- `propose_steps(table, mapping)` ports the detection in `auto_prep_ops`, with the same thresholds, and with these changes. It proposes only for the column the M02 mapper chose for the client's own name or address, or for an unmapped column. It never proposes for a header holding a `person_fields` or `address_fields` deny word from `settings/mapping.toml` (this is the proposal half of B-23). It leaves alone a column that is only a unit line.

### 2. Clean and delimiter steps (P-PREP-1, P-PREP-2) and casing (P-STD-1)

- Clean params: `columns`, `case` (`none`, `title_name`, `title_address`, `upper`, `lower`), `strip_junk` (the `sanitize_special` rules) and `strip_edge_punctuation`. Trim and collapse spaces always. Output goes to `<col>_clean`.
- `engine/prepare/casing.py`: `title_name(value)` and `title_address(value)`. A value is re-cased only when it has letters and all of them are upper case or all lower case. Mixed case is kept exactly.
  - `Mc` applies to all-caps values of four or more letters. `Mac` applies only to the known list in `settings/names.toml`. `O'` and `D'` capitalize the next letter, and a curly apostrophe is treated like a straight one and kept as typed. Hyphenated parts are cased separately. A particle in the list below stays lower case unless it is the first word. An exceptions table maps all-caps spellings to exact forms.
  - Worked cases: `MCMAHON` gives `McMahon`, `MCE` gives `Mce`, `MACARTHUR` gives `MacArthur`, `MACHADO` gives `Machado`, `O’BRIEN` gives `O’Brien`, `D'ANGELO` gives `D'Angelo`, `SMITH-JONES` gives `Smith-Jones`, `DE LA CRUZ` gives `De la Cruz`, `DINAPOLI` gives `DiNapoli`, `DEJESUS` gives `DeJesus`, `LEBRON` gives `LeBron`. `DiNapoli`, `LaGuardia` and `mELINDA` are kept.
- Delimiter params: `column`, `delimiter` (comma, tab, pipe, semicolon, colon, space, slash, or a custom string), `maxsplit` (0 for all) and `names`. Parts are trimmed, short rows pad with blanks. Amber when no row contains the delimiter.

### 3. Jammed address (P-PREP-3), `engine/prepare/address.py`

`parse_address(raw, words) -> AddressParts(street, unit, city, state, zip, extra, notes)`. Every input token ends up in exactly one part, so nothing is dropped. The rules, applied in this order:

1. Strip a trailing country (`USA`, `US`, `United States`) and stray end punctuation. Join a leading house-number range (`117 - 19`) into `117-19` before treating any spaced dash, slash, semicolon, colon or pipe between words as a comma (B-09). `c/o` is not a separator.
2. ZIP tail. Five digits, or nine with or without a dash, preceded by a non-digit or the start, at the end. A nine-digit tail keeps the first five and adds the note `zip_had_9_digits` (audit only, not review). A tail of any other digit length is not a ZIP (B-07).
3. State tail. Only NY is read as a state (P-STD-5): `NY`, `N.Y.`, `New York` or `New York State` directly before a peeled ZIP, or at the end with no ZIP. Another state code stays in the text, so `St`, `CT` and `PL` can never be taken as a state. M04 reads other states from the State column.
4. Street end. With commas, the first segment holds the street. Without, find the last street-type word from `settings/address_words.toml` (St, Ave, Blvd, Pkwy, Concourse and the rest, plus a directly following directional) or a fixed street (`Avenue of the Americas`, `Grand Concourse`, `Broadway`, `Bowling Green`). `Avenue U` and `Avenue 4` end after the letter or number. If nothing is found and a ZIP or state was peeled, the last one to three words are a city only when they are a borough name or alias. The city is read only from after the street end (B-08).
5. Units, read after the street end. Unit words (Apt, Apartment, Unit, Ste, Suite, Fl, Floor, Rm, Room, Bldg, `#`, and the standalone words Rear, Front, Basement, Bsmt, Lower, Upper, Top, Ground, Lobby, Penthouse, Mezzanine) with the designator shapes of `_UNIT_DESIGNATOR`, `APT18L`, `Apt#: 11T`, `Apt. 10 R` and `4th Fl`. A lone letter or letter and number counts after a unit word, after `#` or as its own comma segment (B-30). A digit and letter token such as `14A` or `5C` right after the street end is a unit. Standalone words are units only after the street end, with or without a comma (B-42), so `88 Front St` is whole. A unit word must be followed by a designator, so `10 Apartment Way` is whole.
6. A unit followed by city text splits at the designator: `Apt 3 Brooklyn` gives unit `Apt 3` and city `Brooklyn` (B-29).
7. What is left after the street and units, up to three words, is city text whatever it is, but only when a ZIP or state was peeled. M04 decides whether the city is recognized. Anything else, such as `c/o Jane Doe`, goes to `extra` with the decision reason `address_extra_text` (B-10). If everything is a unit, keep the original in `street`.

| Input | street | unit | city | state | zip | extra |
| --- | --- | --- | --- | --- | --- | --- |
| `117 - 19 45th Ave, Flushing, NY 11355` | `117-19 45th Ave` | | Flushing | NY | 11355 | |
| `1010 Grand Concourse NY 10452` | `1010 Grand Concourse` | | | NY | 10452 | |
| `123 Main St, Brooklyn, NY 112011234` | `123 Main St` | | Brooklyn | NY | 11201 | |
| `123 Main St, Apt 3 Brooklyn NY 11201` | `123 Main St` | `Apt 3` | Brooklyn | NY | 11201 | |
| `123 Main St, c/o Jane Doe` | `123 Main St` | | | | | `c/o Jane Doe` |
| `85-10 Forest Pkwy Woodhaven NY 11421` | `85-10 Forest Pkwy` | | Woodhaven | NY | 11421 | |
| `100 Avenue U` | `100 Avenue U` | | | | | |
| `9 Elm St, Newark, NJ 07102` | `9 Elm St` | | `Newark, NJ` | | 07102 | |

Also export `split_trailing_unit(text, words) -> (street, unit | None)`. It is rules 4 and 5 applied to an Address_1 value with no city, state or ZIP, and M04 uses it for P-STD-8 (proof sheet 11). `67 Franklin Avenue Apt. 10 R`, `25 Tom Street APT18L`, `67 Jill Ave Apt#: 11T` and `123 Main St Apt 2A` give a unit, and `10 Apartment Way`, `88 Front St` and `100 Avenue U` give none.

### 4. Jammed name (P-PREP-4), `engine/prepare/names.py`

`parse_name(raw, words) -> NameParts(first, middle, last, title, credential, suffix, extra, notes)`. Every token lands in one part. `settings/names.toml` holds the lists (starting contents below).

- Remove a nickname in parentheses or quotes, and any token beyond the shape, into `extra` with `name_extra_tokens` (B-32).
- Title tokens at the start go to `title`, with or without a period. Credentials at the end go to `credential`. Generational suffixes go to `suffix` wherever they sit: at the end, before a comma (`Smith Jr, John`), as their own segment (`Smith, Jr., John`), or leading the part after the comma (`Smith, III John`). Suffixes count only at the end of a token list, so `Martin V Buren` keeps V as a middle initial. None of the three ever becomes a first, middle or last name.
  - Position decides the words that can be two things. `Sr` at the start with at least two tokens after it is the title Sister, and anywhere else it is a suffix. `Fr` is a title only at the start. `DO` and `NP` are credentials only at the end of a name with at least two tokens before them, or after a comma, so `Anh Do` stays first and last. A lone `I` is a suffix at the end of a comma-less name of three or more tokens (`John Smith I`), and a middle initial in `Smith, John I`. Log the `I` reading.
- With a comma, the part before it is the surname, whole, including particles, hyphens and two words. After it, the first token is the first name (two tokens when they are a listed compound such as `Maria Elena`), then a single letter is the middle initial, and anything else goes to `extra` with `name_extra_tokens`. A third segment goes to `extra`.
- Without a comma, a listed particle chain directly before the final word joins the surname. Two words give first and last. Three or more head words: a listed compound first name stays together, then a single letter is the middle initial. Any other shape of three or more words is split as First, Middle, Last, with the first word as the first name, the last word as the surname and every word between them in `middle`, and sets the soft reason `name_order_unclear`. Every word is kept and nothing is dropped. `Ana Garcia Lopez` gives `Ana`, `Garcia`, `Lopez`.
- `middle_initial(value) -> (initial, note)`: a real name or letter gives its first letter in upper case. The stop list (`NMI`, `NMN`, `no`, `none`, `unknown`, `n/a`, `na`, suffixes, `.`, `(none)`) and non-letters give blank (B-33). The `_middle` column from a split keeps the whole word, and M04's Middle_Initial step reduces it.
- The reason title is now the spec's own, "Name has three or more words: check which is the surname," so the old title gap is closed.
  ```toml
  titles = ["mr", "mrs", "ms", "miss", "mx", "dr", "rev", "fr", "sr", "hon"]
  credentials = ["md", "do", "phd", "edd", "esq", "rn", "lpn", "np", "lcsw", "lmsw", "msw", "dds", "jd", "cpa"]
  suffixes = ["jr", "sr", "i", "ii", "iii", "iv", "v", "vi", "vii", "viii", "ix", "x", "2nd", "3rd", "4th", "5th"]
  particles = ["de la", "van der", "de", "del", "della", "di", "da", "do", "dos", "du", "van", "von", "la", "le", "st", "bin", "ibn", "al"]
  compound_given = ["mary ann", "mary jane", "jose luis", "juan carlos", "maria elena"]
  mac_names = ["macdonald", "macarthur", "mackenzie", "macmillan", "macgregor", "macleod", "macintosh", "macintyre", "macneil", "macpherson", "macdougall", "mackay", "maclean", "macknight"]
  [casing_exceptions]
  DINAPOLI = "DiNapoli"
  DEJESUS = "DeJesus"
  LEBRON = "LeBron"
  ```
  The lists above are the spec's lists in P-PREP-4 plus the extras the audit cases need. Those extras are `msw`, `dds` and `jd`, the suffixes `vii` to `x` and `5th` (B-12 asks for II to X and 2nd to 5th), and the compound `mary jane` (B-11). Log them.

### 5. Calculated ZIP (P-PREP-5), `engine/prepare/calc_zip.py`

- `ZipResolver` protocol: `zip_for(street, borough_or_city) -> str | None`, exact matches only. M05 supplies the Geosupport and reference implementations. Tests use a dict-backed double kept under `tests/support/`.
- Params: `street_col`, optional `city_col` and `zip_col`, `mode` (`blanks` or `all`) and the column `name` (default `Zip_calculated`). Output: the ZIP column and `<name>_note` holding a reason ID per row (`zip_found`, `zip_kept`, `zip_not_worked_out`, `no_street`, `no_lookup_available`). Counts for the step row: found, kept, not worked out.
- In `blanks` mode an existing ZIP is kept only when it is five ASCII digits, or ZIP+4 reduced to five, and is in the NYC table. Anything else is not kept and is looked up from the street. A resolver answer outside the NYC table is discarded. When nothing works the cell is blank with `zip_not_worked_out` ("No ZIP could be worked out"), never the first five digits of anything (B-06).

### 6. NYC ZIP table (P-STD-3, built here for M04)

- `wholecount/engine/geo/data/nyc_zips.csv` (`zip,borough,source`) and `wholecount/engine/geo/zips.py` with `borough_for_zip`, `is_nyc_zip` and `nyc_zips()`. Boroughs are written New York, Brooklyn, Queens, Bronx and Staten Island.
- `tools/make_zip_table.py` builds the CSV from a cited public source. First choice is NYC Health's ZIP table, `https://www.nyc.gov/assets/doh/downloads/pdf/ah/zipcodetable.pdf` (undated). It lists 11004 and 11005 under Queens, 10463 under Bronx and 11691 and 11697 under Queens. Extract its text once with a local tool, commit the extract under `tools/data/`, and have the script read that file, so no PDF library is added. Put the URL and retrieval date in each `source` value. M14's A-20 test allowlists that `source` column and this script by name, as provenance.
- Cross-check the result against a second public NYC list and report any ZIP in one and not the other. Never type the list from memory.
- The ZIPs SPEC P-STD-3 names (11004 and 11005 and 11690 to 11697 in Queens, 10463 in Bronx) are cited to the spec itself when neither source lists them. Their `source` value is `SPEC.md P-STD-3`. That's the only list typed by hand.
- Joe may drop source extracts into `tools/data/` himself, and the script reads them like any other extract.
- If the cloud session can't reach a source and nothing is in `tools/data/`, don't stop the milestone. Build everything else, mark `tests/unit/test_nyc_zip_table.py` and the tests that need the full table as pending with the reason, and put the question at the top of the report. The rest of M03 is still done.
- Required by tests: 11004 and 11005 and 11690 to 11697 are Queens, 10463 is Bronx, and 11001, 11580, 07030, 12345, 99999 and 00000 are absent.

### 7. Dev command

`python -m wholecount.dev tidy <path> [...]` loads, maps, proposes and applies steps. Per table (`A.1`) it prints `steps_proposed`, `steps_amber`, `columns_added`, `rows_flagged` per reason ID, `zip_found`, `zip_kept`, `zip_not_worked_out`, and `source_cells_changed` (must be 0).

## Tests to write

- `tests/audit/test_B06_calculated_zip.py`. ZIP inputs `112019`, `11201 7`, `11201-12`, `123456789012`, `1 1 2 0 1`, `11201abc`, `99999-0000`, `1120` and `07030` all give a blank calculated cell with `zip_not_worked_out`. `11201-1234` and `11201` give `11201`. A resolver answer of `07030` is discarded. A blank ZIP with a resolvable street gets the resolver's NYC ZIP.
- `tests/audit/test_B07_nine_digit_zip.py`: both forms of `123 Main St Brooklyn NY 112011234`, and `Apt 1120123 Main St` yields no ZIP.
- `tests/audit/test_B08_street_keeps_concourse.py`: `1010 Grand Concourse NY 10452`, plus `1 Brooklyn Ave Brooklyn NY 11203`, `100 Jamaica Ave Queens NY 11418`, `5 Queens Blvd Queens NY 11375`, `100 New York Ave Brooklyn NY 11216`, `9 Bronx River Ave Bronx NY 10472`, `7 Staten Island Expy Staten Island NY 10314` and `3 Flushing Ave Brooklyn NY 11205`, each with the street whole and the city after it.
- `tests/audit/test_B09_spaced_hyphen_house_number.py`: both inputs give `117-19 45th Ave`, and `123 Main St - Apt 4 - Brooklyn` still splits.
- `tests/audit/test_B10_trailing_segment_kept.py`: `, Lower` and `, Top Floor` become the unit, `, c/o Jane Doe` becomes `extra` with `address_extra_text`, and no input ends with an empty unit and an empty extra.
- `tests/audit/test_B11_particles_and_double_surnames.py`: `Maria de la Cruz`, `Martin Van Buren`, `Ludwig van Beethoven`, `Mohammed bin Salman`, `Mary Jane Watson`, `Maria E Cruz`, `de la Cruz, Maria`, `Cruz, Maria Elena`; and `Ana Garcia Lopez` and `Kim Soo Jin` set `name_order_unclear`, split as `Ana / Garcia / Lopez` and `Kim / Soo / Jin` with every word kept. The reason is `soft`, so it never holds the count, and its title is the spec's. `Mary Jane Watson` and `Maria E Cruz` do not set it.
- `tests/audit/test_B12_titles_and_suffixes.py`: all twelve audit inputs, with the suffix in `suffix` and not in the last name (the audit wanted `Smith V`, the spec wants the `<name>_suffix` column, so the spec wins). Then the words the spec adds. `Mx Alex Rivera`, `Fr. Tom Brown` and `Sr. Maria Lopez` fill `title` (Sister), `John Smith Sr` fills `suffix`, `Anh Do` is first and last, `Ann Lee, DO`, `Jo Park EdD`, `Sam Fox LPN`, `Pat Ray NP` and `Lee Cho LMSW` fill `credential`, `John Smith I` fills `suffix`, and `Smith, John I` keeps `I` as the middle initial.
- `tests/audit/test_B29_unit_then_city.py`, `test_B30_lone_letter_units.py` (`Apt B`, `Unit B`, `, B,`, `5C`, and `100 Avenue U` whole), `test_B32_extra_name_tokens.py` (`Smith, John Q Public`, `Smith, John, Mary`, `John (Jack) Smith`, `John 'Johnny' Smith`), `test_B33_middle_initial_placeholders.py` (the stop list, `Marie` gives `M`, and proof sheet 03's five cases) and `test_B42_rear_and_front.py` (all three forms give `123 Main St`, and `88 Front St` stays whole).
- Rule tests under `tests/rules/`: `test_P_PREP_1_clean.py` (each case mode, junk, edge punctuation, the B-43 inputs run through `title_name` directly, source cells unchanged; the B-43 audit test itself belongs to M04), `test_P_PREP_2_split_delim.py`, `test_P_PREP_3_jammed_address.py` (with the `split_trailing_unit` cases and the `Newark, NJ` row), `test_P_PREP_4_jammed_name.py`, `test_P_PREP_5_calculated_zip.py`, `test_steps_model.py` (order, remove and restore, amber rows, unique column names, `source_cells_changed == 0`, proposals skip a Caseworker Name and an Employer Address), `test_reason_flags.py` (each decision reason has exactly one of the three flags and a `problems.toml` entry with the four keys, notes have no flag, `address_extra_text` is `location`, `name_order_unclear` and `name_extra_tokens` are `soft`, and none is `holds_count`).
- Token conservation: `test_tokens_are_never_dropped.py` runs every address and name case in this milestone and asserts each input token appears in some output part.
- `tests/golden/test_proof_09_jammed_address.py` and `test_proof_10_jammed_name.py` port all 14 and 6 rows with their `want` values. The city is compared only as parsed, because M04 fills blanks from the ZIP. Where the spec changes a rule, the ported expectation follows the spec (SPEC 13.1). Sheet 10 row 3 expects last name `Smith` and suffix `Jr`, where the old answer key said `Smith Jr`.
- `tests/golden/CHANGES.md`, created here. A table with the columns Sheet, Row, Old expected, New expected, Rule. It lists sheet 10 row 3 (P-PREP-4) and any other row this milestone changes. M04 adds its own rows. `tests/golden/test_changes_log.py` checks that every row has all five cells and that Rule matches `P-[A-Z]+-[0-9]+`.
- `tests/unit/test_nyc_zip_table.py`: the required and absent ZIPs, five ASCII digits, unique and sorted, only the five borough names, every row has a source, and a ZIP whose source is `SPEC.md P-STD-3` is one the spec names.
- `tests/golden/test_example_data_steps.py`. On the five example files in `wholecount/sample_data/`, `propose_steps` and `apply_steps` followed by the M02 mapper give the mapping and blockers in `map.after_steps` of `EXPECTED.json`. The jammed-name and jammed-address columns of the CSV are split, and no table is left blocked on a name. `source_cells_changed` is 0.
- `tests/integration/` is not needed. Add one chain test, `test_B23_end_to_end.py`, that runs propose, apply and the M02 mapper on a file with `Caseworker Name`, `First Name` and `Last Name`, and checks the client's own columns are mapped.

## Done when

- [ ] `make test`, `make offline` and `make copy` are green, with the counts in the report.
- [ ] B-06, B-07, B-08, B-09, B-10, B-11, B-12, B-29, B-30, B-32, B-33 and B-42 each have a passing test and a line in `tests/audit/INDEX.md`.
- [ ] Both proof sheet golden tests pass, `tests/golden/CHANGES.md` lists every changed row, and no step ever changes a source cell.
- [ ] `nyc_zips.csv` is built from the cited source and cross-checked, and the report names the source, the date, any disagreement and every ZIP cited to the spec. If no source could be reached, the ZIP-table tests are marked pending, the rest of this list is done, and the question is at the top of the report.
- [ ] No new dependency outside the approved set.
- [ ] The report lists the decisions logged above: the list extras beyond the spec (`msw`, `dds`, `jd`, `vii` to `x`, `5th`, `mary jane`), the `I` and `Sr` and `DO` position rules, the wording of `name_extra_tokens`, `Lower` and `Top Floor` as units, other state codes staying in the city text, and how the ZIP source was chosen.
- [ ] `docs/milestones/M03-REPORT.md` is written, the branch is pushed, the pull request is open, and work has stopped.

## Windows checks for Joe

1. `py -3.12 -m venv .venv`
2. `.venv\Scripts\activate`
3. `pip install --require-hashes --no-deps -r requirements-dev.lock`
4. `python -m pytest -q`. All pass.
5. `python -m wholecount.dev tidy "C:\path\to\a real export.xlsx"` with a list that has one combined name column or one combined address column. Expect a proposed step for it (`steps_proposed` above 0), `columns_added` above 0, and `source_cells_changed 0`.
6. Look at `rows_flagged` per reason. A list with notes like "c/o" in addresses should show `address_extra_text`, and a list with three-word names should show `name_order_unclear`. A flagged count that looks too high or too low is the thing to tell me about.

The dev command prints counts only. It never shows a client value.

## Out of scope

- Placeholders, standardizing every field, row checks and statuses (M04). The city is only parsed here, never recognized or filled.
- Geosupport and the reference file behind the ZIP resolver (M05). Only the protocol exists now.
- The Tidy up screen, step cards and the amber row styling (M11).
- Saving steps in set-ups (M08 and M09).
