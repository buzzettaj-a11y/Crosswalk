# M01: Reading files and finding tables

## Goal

Read the six file formats into a grid of cleaned text, find the tables and header rows inside each file, and account for every non-empty row in every file (H4). A bad file never blocks the others. The install secret is made at first launch behind a `SecretStore`. Every table gets its stable key, and every row a record key hashed with that secret, so a re-export keeps the keys of rows that did not change. Sensitive columns are dropped at load, by name or by their values. Nothing in the app can print a client value from this milestone on, because the progress type cannot hold a free string (H8). This milestone also builds the example data every later milestone runs on (P-GEO-4a): five made-up files in `wholecount/sample_data/`, a seeded script that makes them, and the expected counts beside them.

## Spec sections

- SPEC 5.1 (keys, as rewritten in v1.1), 6.1 (P-READ-1 to P-READ-10), 4.3 (letters, display only), 11.6.2 and 11.6.3 (progress types), P-GEO-4a (example data), H4 (the first balance), H8, H9 (the install secret), H10.
- Audit: B-02, B-24, A-09, A-13, C-23. Fix plan 4.1 and 5.4, where SPEC 5.1 and P-READ-9 say how they land.

## Depends on

M00 merged. This milestone uses the copy registry, the guard tests, the layering test and the guard's DPAPI constants (`DPAPI_DLL_NAMES`, `DPAPI_SYMBOLS`) from M00.

## Branch

`build/m01-reading`

## Read first

- `SPEC.md` 5.1, 6.1, 11.6.3, H4, H8, H9 and H10. `docs/context/docs/crosswalk-fix-plan.md` 4.1 (line 451, the SSN check) and 5.4 (line 660, the secret and keys); the spec wins where they differ. Then the findings: `docs/audit/A-claims.md` A-09 (line 124) and A-13 (line 181), `docs/audit/B-values.md` B-02 (line 117) and B-24 (line 556), `docs/audit/C-counts.md` C-23 (line 385).
- Fixtures: `docs/audit/A-fixtures/blankline.csv` and the input in `docs/audit/C-scripts/s28_blank_rows.py`.
- `legacy/table_detect.py` (reference only): `_to_text` :60, `_is_blank` :76, `_split_region` :120, `_detect_header` :169, `_unique_headers` :193, `_classify` :208 with the hint sets at lines 22 to 50, `DetectedTable` :240, `detect_in_grid` :341, `frame_from_block` :367, `table_from_dataframe` :389, `detect_in_excel` :403, `detect_in_delimited` :417, `header_looks_wrong` :436.
- `legacy/app.py`: `read_uploaded_file` :1170 (JSON and XML flattening at 1194 to 1223), `tables_from_upload` :3421, `_SAFE_XML_PARSER` :82, `clean_cell` :353, `DELIMITERS` :865.
- `legacy/tests/test_table_detect.py` for the layout cases, `legacy/tools/make_proof_workbook.py` lines 486 to 515 (sheets 19 and 20), and `legacy/sample_data/` (five files, 266 data rows). The legacy samples are for reading tests only (P-GEO-4a). Three of them have no Client_ID or date of birth, so they can't show counting. `legacy/tools/make_sample_data.py` shows the shapes the new example data keeps.
- Four things in the legacy code to not repeat. `tables_from_upload` decodes with `errors="replace"` (:3437). `_BLANK_TOKENS` treats NULL, N/A and a dash as blank for layout, so a row of dashes vanishes. `frame_from_block` drops the rows above the header without counting them. The table key includes the A1 range, which shifts when rows are added. Row IDs built from a range and a row number break on every re-export (fix plan 5.4).

## What to build

### 1. Settings, progress and letters

- `wholecount/settings/loader.py`: `load(name) -> dict`, reading `wholecount/settings/<name>.toml` through `importlib.resources` with `tomllib`.
- `settings/sensitive_columns.toml`, matched on whole words of the header, never on substrings. Date of birth is deliberately absent, because it is a built-in field.
  ```toml
  [phrases]
  ssn = ["ssn", "social security"]
  medicaid = ["medicaid"]
  gender = ["gender", "sex"]
  race = ["race", "ethnicity"]
  religion = ["religion"]
  health = ["diagnosis", "hiv"]
  immigration = ["immigration"]
  ```
- `settings/table_hints.toml` with `person`, `address` and `summary` word lists, moved from the legacy hint sets.
- `wholecount/engine/letters.py`: `letter_for_index(i)` gives A to Z, then AA, AB and on.
- `wholecount/engine/progress.py` (SPEC 11.6.3). `Step` enum (the 16 distinct step names in the 11.6.2 table, from Reading files to Protecting the backup), `Unit` enum, frozen `SourceRef(letter, file_name)` and `StepRef(step)`, `ProgressMessage(message_id, params)`. `params` is a dict whose values may be only `SourceRef`, `StepRef` or `int` (not `bool`). Anything else, and a `params` that isn't a dict, raises `TypeError`. These names are the only definitions. M08, M10 and M13 import them and never define a second progress type or step list. `ProgressSink` has `begin`, `advance`, `end` and `cancelled`. Also `NullSink` and `RecordingSink`, plus `render(message)`, which looks the text up in the copy registry.
- Copy entries under `progress.*` for each step name and for "Reading {source}". Also `read.encoding_note` with the exact P-READ-2 sentence and claim `CL-READ-ENCODING-01`, and `read.accounting_line` with claim `CL-READ-ACCOUNTING-01`. Add `read.unreadable.<reason_id>` text for each reason below.

### 2. Model (`engine/read/model.py`)

- `CellMeta(kind, number_format)`. Sparse, kept only for numeric and date `.xlsx` cells. `kind` is `number` or `date`.
- `Grid(sheet, rows, meta, hidden=False, fixed_header=None)`. `rows` is rectangular cleaned text. Row `i` is file row `i + 1`. For CSV the number is the record number, as Excel shows it. JSON and XML set `fixed_header` (their keys), and each record is a row, numbered from 1.
- `Block(r0, r1, c0, c1)`, `BlockInfo(block, rows, included, continuation)`.
- `LoadedTable`: `key`, `letter`, `sheet`, `blocks`, `header_row` (1-based inside the first block, 0 for none), `header_is_virtual`, `raw_headers`, `headers` (made unique, blank ones become `Column_N`), `rows`, `row_numbers`, `row_block`, `meta`, `record_keys`, `kind` (`records`, `summary`, `unknown`), `kind_reason` (an ID), `included`, `suggested_header_row`, `header_warning` (an ID), `above_header_rows`, `empty_columns`, `sensitive_dropped` (header texts only).
- `ReadFile`: `name`, `extension`, `fingerprint`, `size`, `encoding`, `encoding_samples`, `grids`, `clean_counts`, `replacement_chars`.
- `UnreadableFile(reason_id)` with reasons `unsupported_type`, `unreadable_encoding`, `bad_workbook`, `bad_json`, `bad_xml`, `empty_file` and `blocked_by_guard`.

### 3. Text, cleaning and readers (`engine/read/`)

- `text.py`, P-READ-2. Remove a leading UTF-8 BOM, decode as strict UTF-8, then strict Windows-1252, else raise `unreadable_encoding`. Python's cp1252 leaves bytes 0x81, 0x8D, 0x8F, 0x90 and 0x9D undefined, so a file holding them is unreadable. Never pass `errors="replace"`. On the Windows-1252 path keep up to five cells that contain a non-ASCII letter as `encoding_samples`. Count any U+FFFD already in the decoded text into `replacement_chars` and leave it in the cell. P-READ-3 gives such a row the review reason "Value has an unreadable character", naming the field. M04 raises it from the cell text, because the reasons registry starts in M03.
- Delimiters: `.csv` comma, `.tsv` tab, `.txt` by the highest consistent count over the first 20 non-blank lines among comma, tab, semicolon and pipe, ties going to that order. Parse with `csv.reader` over `io.StringIO(text, newline="")`.
- `clean.py`, P-READ-3. `clean_cell(text) -> (text, CleanCounts)`. Remove U+200B, U+200C, U+200D, U+2060, U+FEFF, U+00AD and C0 controls, counting each group. Tab, CR, LF, NBSP and other Unicode spaces become one space, then runs collapse and the ends are trimmed. Remove one leading apostrophe when something follows it. NUL and other controls do not become spaces. Do not change case, digits or punctuation.
- `xlsx.py`. `openpyxl.load_workbook(fileobj, read_only=True, data_only=True)`. Read every sheet, hidden ones too (set `hidden`). Cell text rules, in a tested function `cell_text(value, number_format)`: `None` is empty; `bool` is `TRUE` or `FALSE`; an integer or integral float is an integer string, left-padded with zeros when the format is all zeros (`00000`); other floats use their shortest form, or fixed decimals for formats like `0.00`; dates and datetimes are ISO (`2024-03-15`, or with ` HH:MM:SS` when a time is present); times are `HH:MM:SS`. Record `CellMeta` for numeric and date cells only.
- `structured.py`. JSON via `json.load` with `parse_int=str` and `parse_float=str`, so number literals stay as typed. A top-level list is the records, an object with exactly one list value uses that list, otherwise the object is one record. Nested objects flatten to dotted keys (`location.city`), lists of scalars join with `; `, `null` is empty, `true` and `false` stay words. XML via lxml with `etree.XMLParser(no_network=True, resolve_entities=False, load_dtd=False, dtd_validation=False, huge_tree=False)` over a `BytesIO`. Records are the root's children, leaf elements flatten to dotted paths, attributes become `path@name`. Headers are the union of keys in first-seen order, and a missing key is an empty cell.
- `reader.py`, P-READ-10: `read_path(path, sink, keep=frozenset()) -> ReadFile`. It accepts only a `pathlib.Path` (a `str` raises `TypeError`), opens and reads the file itself, takes the SHA-256 of the bytes, and hands only `BytesIO` or `StringIO` objects to the parsers. It catches the guard's `OfflineViolation` for a network path and reports `blocked_by_guard`.

### 4. Tables (`engine/read/tables.py`, P-READ-4 to P-READ-6)

- `split_blocks(grid)`: recurse on fully blank rows, then fully blank columns, as `_split_region` did. A cell is blank only when its text is empty.
- A block with fewer than 2 rows that is not a continuation is not a table. It is listed as a non-table block and counted (`non_table`).
- Header: `detect_header(block)` as `_detect_header`. Port `header_looks_wrong` to return reason IDs (`header_row_empty`, `header_mostly_blank`, `header_looks_like_data`, `header_duplicate_name`, `header_same_shape_as_row_below`, `header_row_below_is_better`, `no_header_but_row_looks_like_names`). Never switch the header silently. When a better row is found, set `suggested_header_row` and `header_warning`. `rebuild_with_header(table, row)` is the pure function Show data will call.
- Classify with `_classify` and `settings/table_hints.toml`. Defaults (P-READ-4): records included, summary and unknown unticked. An unticked table is counted as left out.
- Continuation (P-READ-5): a block with the same column count and first column as the nearest records block above it, whose first row is neither `_detect_header` nor name-like, joins that table as a continuation. It is included with it, and can be unticked on its own through `BlockInfo.included`.

### 5. Accounting (`engine/read/accounting.py`, P-READ-7, H4)

- `FileAccounting(non_empty_rows, shared_rows, header, above_header, included, excluded, non_table)` with `balanced()` meaning `header + above_header + included + excluded + non_table == non_empty_rows + shared_rows`.
- Side-by-side tables share file rows, so one file row can be counted once per block. `shared_rows` is the extra count: block rows summed, minus distinct non-empty rows. H4 names the header row and P-READ-7 names rows above it, so count both. Also expose `cells_in_blocks == non_empty_cells`, the cell-partition invariant.
- `rows_left_out` is `excluded + non_table`. A nonzero value is a warning the screen must show (C-23).

### 6. The install secret, keys and loader (`session/`, SPEC 5.1 and H9)

- `session/dpapi.py`: `protect(data) -> bytes` and `unprotect(blob) -> bytes` for the current Windows user, through `ctypes` (`CryptProtectData`, `CryptUnprotectData` and `LocalFree`, with library and symbol names from `guard/config.py`). The `DATA_BLOB` handling sits in small functions that take the library objects as arguments, so Linux tests pass fakes. `unprotect` raises `DpapiError` for a damaged blob or another Windows user, and never returns partial data. `tests/support/fake_dpapi.py` is the Linux double (reversible, keyed per instance, a flipped byte fails). M05 and M09 reuse both.
- `session/secret_store.py`: a `SecretStore` protocol (`load() -> bytes | None`, `save(secret)`). `DpapiSecretStore(dir)` writes `protect(secret)` to `<dir>\key.bin`. `FileSecretStore(dir)` is the Linux test double. It keeps the bytes as they are, says `INSECURE = True`, and is never the Windows choice. `default_store(platform=sys.platform, env=os.environ)` picks DPAPI on `win32`, with `dir` `%LOCALAPPDATA%\Wholecount`, and the file double elsewhere, with `dir` from `WHOLECOUNT_DATA_DIR`.
- `get_or_create_secret(store) -> (InstallSecret, created)`. It makes 32 bytes with `secrets.token_bytes(32)` when the store is empty, at first launch. A store that holds something unreadable raises `SecretUnreadable` and never makes a new secret, because that would change every key. `InstallSecret` hides its bytes from `repr`, and only `keys.py` reads them. The secret is never shown, logged or exported. The backup file is M13.
- `engine/fold.py`: `fold(text)` for P-DUP-6. NFKD, drop combining marks, casefold, then keep only letters and digits, so `José` equals `Jose` and `O'Brien` equals `OBrien`. M06 reuses it.
- `session/keys.py`, SPEC 5.1. Every function that involves client data takes the secret.
  - `normalize_file_name(name)`: lowercase, no folder, each run of spaces and punctuation becomes one underscore, ends trimmed. The extension stays, so `Clinic Export.csv` is `clinic_export_csv` (log this reading of "file name").
  - `source_fingerprint(bytes)`: SHA-256 hex. `header_signature(cells)`: first 8 hex of SHA-256 over the cell texts joined with U+001F.
  - `file_keys(files)`: files in add order, each `(name, fingerprint)`. The second and later files with the same normalized name get `~` plus the first 6 hex of their fingerprint. A file with the same name and the same fingerprint as an earlier one is skipped as `duplicate_file` (M08 owns replacing a file).
  - `table_key(file_key, sheet, signature)` is `file_key :: sheet-or-"data" :: signature`. The letter is not part of it. Two tables in one file with one key get ` #2` after the sheet part, in discovery order. Block ranges are not part of it.
  - `record_keys(secret, table_key, rows)`: first 20 hex of HMAC-SHA256 over `"\x1f".join([table_key, *cells, str(occurrence)])`. The cells are the row's texts as read and cleaned (P-READ-3), before any column is dropped. Log this reading of "raw cell texts".
  - `person_key(secret, system, client_id=None, given=None, surname=None, dob=None, address_key=None)`: full HMAC-SHA256 hex over the parts joined with U+001F. `system` is lowercased and trimmed, and `client_id` is trimmed. With a Client_ID the parts are `system, client_id`. Without one they are `system, given, surname, dob`, and when `dob` is also empty the parts are `system, given, surname, "", address_key`. The caller passes folded names and the address key (M05 builds the key). Identity uses it later.
- Known answers, with the secret `bytes(range(32))`. Header `["Name","Full_Address"]` gives signature `3380a5d7`. File `clinic_export.csv` gives table key `clinic_export_csv :: data :: 3380a5d7`. The row `["Ada Sample","125 Worth St Apt 4B New York NY 10013"]` gets `7533705e667f8cf12288` as occurrence 0 and `93babd9489a6553c3676` as occurrence 1. With the collision suffix `~a1b2c3` in the file key, occurrence 0 is `0d61d191dda29d77ca6f`. With the secret `bytes(range(32, 64))`, occurrence 0 is `4a69e20c55510cc8bfa2`. Person key for system `Clinic Export ` and Client_ID ` C-1001 ` is `064ab6000867a82fc1aae7bbbbf3d62558904674cd07672d911107e7ea45d2af`. With no Client_ID, given `ada`, surname `sample` and dob `1990-04-03` it is `1479425de31cd50ffc98c3d015fb5f7ea08fe5c57c8c2981b4f43ee0f12f96c6`. With no dob and address key `45 park ave 10013` it is `f8250bc7f0a1e6406e1ad2e301bc7f5b819bc99a0c88dd01b175e0c094b758ac`.
- Occurrences are counted over all the table's data rows, ticked or not, so ticking a continuation block never changes another row's key. Keys are hashed over the full cleaned rows before sensitive columns are dropped, so keep or drop never changes a key.
- `load_files(paths, sink, secret, keep=frozenset()) -> LoadResult`. Each file is read independently (A-13). It returns one `FileOutcome` per file (`ok`, `unreadable` or `duplicate_file`, with a reason ID, fingerprint, table count, accounting) plus the tables. Only readable files take a letter, in order added, and the letter is display only. Sequence per file: read, build tables, compute keys, drop sensitive columns, set `read_file.grids = []`.
- Sensitive columns (P-READ-9, H10): `drop_sensitive(table, keep)` removes matching columns from `rows` and `meta`, and records the header texts in `sensitive_dropped`. A value from a dropped column must not stay reachable after load. A column is also listed and dropped whatever its name when more than half of its non-blank values look like Social Security numbers (fix plan 4.1). `ssn_shaped(value)` is true for `###-##-####`, or for nine digits with area not 000, 666 or 9xx, group not 00 and serial not 0000. `looks_like_ssn_column(values)` applies the half rule. Both live in `engine/read/sensitive.py`, so M02 reuses them for P-MAP-7. `LoadedTable` gets `sensitive_by_values` (a count). The check runs at load, before the grid is released.

### 7. Fixtures and the dev command

- Copy `legacy/sample_data/*` to `tests/data/legacy_sample/` and the audit fixture to `tests/data/audit/`, unchanged. The legacy samples are used only by reading tests (P-GEO-4a).

### 8. Example data (P-GEO-4a)

- `tools/make_example_data.py` writes the five example files and `EXPECTED.json` into `wholecount/sample_data/`. It's a dev tool that never ships. The files it writes do ship (M14). It takes `--seed` (default `20261030`), `--out` (default `wholecount/sample_data`) and `--check`. It uses `random.Random(seed)`, the standard library, openpyxl and lxml only. Names and streets come from fixed lists in the script. Names are made up, and streets are real NYC street names with plausible house numbers. No value comes from a real person.
- The five files keep the shapes the old samples tested. Name them `example_clinic.csv`, `example_housing.xlsx`, `example_partner.tsv`, `example_portal.json` and `example_state.xml`.
  - **The CSV** has jammed names (`Last, First M`) and jammed addresses in one column each, plus a Client_ID column.
  - **The workbook** has a `Clients` sheet with two title lines above the header row, so the header needs choosing (P-READ-6). It also has a `Notes` sheet of a few text lines that isn't records, and one `Total` row under the client list.
  - **The TSV** is saved as Windows-1252, with a few accented names, so the encoding callout shows (P-READ-2). It also has one column headed `SSN` holding made-up values in the `9xx-xx-xxxx` form, which is dropped at load (P-READ-9).
  - **The JSON** is nested (`{"export": {"clients": [...]}}`, with an `address` object per client).
  - **The XML** has one element per client.
- About 250 to 300 data rows in all. Every row has a Client_ID or a date of birth, except twelve rows with neither, spread over the files, which come out `no_identifier` and show the count rule. The plan also holds:
  - a few rows with a blank first or last name
  - identical copies and possible copies inside one file
  - one same-ID conflict, and one person enrolled twice under one ID in two programs
  - people who appear in two or three files: some meet `four_exact_facts`, some are Likely proposals (a nickname, swapped birth-date digits), and one rare name moved address
  - program names spelled two ways (one `same_name` proposal and one `initials` proposal)
  - one file with no program column, which is not in Goal 2
  - addresses that are placeholders, no fixed address, outside NYC, a ZIP+4, a ZIP with letters, and a blank ZIP that a lookup can fill
- `EXPECTED.json` is written from the plan, never from a run. Its sections are:
  - `files`: per file the format, encoding, tables (sheet, kind, included), rows included, excluded, non-table, header and above the header, the non-empty rows, and the sensitive columns dropped. M01 checks this section.
  - `map`: per table, the field each column maps to before the tidy-up steps and after the proposed steps, and the Process blockers in each case (M02 and M03).
  - `standardize`: per table, counted, not counted yet and set aside before copies and identity, and the reason ID of every planned problem row by file and row number (M04).
  - `people`: the planned copy groups, same-ID conflicts, automatic joins by reason, and proposals by band (M06).
  - `programs`: the names, the planned proposals with their reason codes, and the tables not in Goal 2 (M07).
  - `decisions`: the decisions an acceptance run takes, which program groups it confirms, which copy groups and pairs it decides, and how (M15).
  - `counts`: rows received, counted, not counted yet and set aside, Goal 1 and Goal 2 low and high, per program, before any decision and after the planned decisions (M08).
  - `locations`: the location split per backend, filled in by M05 when it adds the sample reference.
  - `outputs`: the row count of each file in a practice run and in a no-geocoder run (M09).
- A later milestone that gets a different number from its section finds out why. If the code is wrong, fix the code. If the plan is wrong, change the plan in the script, regenerate the files, and list the change and its reason in the report. Nobody edits `EXPECTED.json` by hand.
- `--check` regenerates into a temporary folder and compares. The text files and `EXPECTED.json` must be byte-identical, and the workbook must match cell by cell (openpyxl writes times into the zip). It prints counts only.
- `python -m wholecount.dev read <path> [<path> ...]`. Per file, headed by its letter, print only counts: `tables_found`, `tables_included`, `rows_included`, `rows_excluded`, `rows_non_table`, `rows_header`, `rows_above_header`, `rows_shared`, `non_empty_rows`, `balanced` (1 or 0), `continuation_blocks`, `sensitive_columns_dropped`, `sensitive_columns_by_values`, `read_as_windows_text` (1 or 0), `invisible_characters_removed`. Overall: `files_read`, `files_unreadable`, `files_duplicate`. No file names, headers or values. It keys rows with a throwaway secret made in memory for the run, so it writes nothing to disk.
- `python -m wholecount.dev secret` uses `default_store()` and prints `install_secret_created` (1 or 0), `install_secret_present` (1), `install_secret_bytes` (32), `store_is_dpapi` (1 or 0) and `stored_blob_is_larger_than_secret` (1 or 0). It never prints the secret. This is the one dev command that writes a file, and it is the install secret H9 allows.

## Tests to write

Tests first. Name audit tests as shown and record each in `tests/audit/INDEX.md`.

- `tests/audit/test_B02_cp1252_names.py`. The cp1252 bytes of `José Núñez`, `Zoë Müller`, `Ana Peña`, `Renée O'Brien` in a CSV read back exactly, `encoding` is `windows-1252`, `encoding_samples` is no more than five and holds `José`. `test_B02_undecodable_bytes_rejected`: bytes `b"A,B\n\x81,\x8d\n"` raise `unreadable_encoding`. `test_B02_no_replacement_character_in_any_cell`.
- `tests/audit/test_B24_invisible_characters.py`. `Ana\u200b` becomes `Ana`; `\ufeffAna`, `An\u00ada` and `Ana\x00` become `Ana`; `A1\u200b` and `A1` read equal; `'07030` is `07030`; `'Ana` is `Ana`; `'0012345` is `0012345`. Counts per group are correct. A cell holding only NBSP is empty.
- `tests/audit/test_A09_rows_outside_tables.py`. Fixture `blankline.csv` gives one primary block plus one continuation: 5 data rows included, balance true. With the continuation unticked: 2 included, 3 excluded, `rows_left_out` 3, the 6 non-empty rows still add up.
- `tests/audit/test_A13_bad_file_does_not_block.py`. A good CSV, a `.docx` renamed, a truncated `.xlsx`, a CSV with byte 0x81, and a second good CSV. The two good files load with letters A and B, the three bad ones come back unreadable with reason IDs, and no exception escapes.
- `tests/audit/test_C23_blank_line_and_comma_row.py`. Input from `s28_blank_rows.py` (header, A1, blank line, a row of commas, A2, A3). By default (P-READ-5) all 3 rows are included. With the continuation unticked, 3 rows received, 1 included, 2 excluded, `rows_left_out` 2 and the balance holds.
- Tests keep a fixed `TEST_SECRET = bytes(range(32))` in `tests/support/secrets.py` and never touch the real store.
- Rule tests, one file per rule group under `tests/rules/`:
  - `test_P_READ_1_formats.py`. All six formats load. A CSV `07030` and `00501` keep their zeros. `.xlsx` cases: numeric ZIP 7030 with format `00000` reads `07030` with `CellMeta(number)`; a real date cell reads ISO with `CellMeta(date)`; a numeric 32874 in General format stays `32874` and is not a date. JSON numbers stay as typed. XML attributes are kept.
  - `test_P_READ_2_encodings.py` (BOM, UTF-8, the sample limit, a literal U+FFFD counted but left in the cell), `test_P_READ_3_invisible.py` (each group counted, and tab, CR, LF and NBSP each collapse to one space), `test_P_READ_4_blocks.py` (the legacy cases: single table, side by side at A1:B3 and D1:G3, stacked, offset B2:D3, headerless numeric, duplicate headers, a column headed `NULL` does not split the table, one-cell notes become non-table blocks), `test_P_READ_5_continuation.py` (joins, a repeated header row does not join, different width does not join, unticking), `test_P_READ_6_headers.py` (each warning ID, no silent switch, `rebuild_with_header`), `test_P_READ_7_accounting.py` (side-by-side shared rows, header and above-header counts, the sheet 19 and 20 layouts), `test_P_READ_8_bad_files.py`, `test_P_READ_9_sensitive.py` (listed names, the drop, `keep`, DOB not dropped, whole-word only, and a `gc.get_objects()` scan finding no str or bytes holding a sentinel from a dropped column; a column headed `Notes` whose values are mostly `078-05-1120` or `219099999` is dropped by its values; `000123456`, `666451234`, `900123456`, `123-45-678` and ten-digit phone numbers are not SSN-shaped; a column at exactly half SSN-shaped is kept; `ssn_unmapped.csv` still drops `SSN`), `test_P_READ_10_no_urls.py` (a `str` path raises, XXE and an external DTD in an XML file load nothing and open no socket when run in a guarded `python -I` subprocess).
- `tests/golden/test_proof_19_20_tables.py`. Type the two grids from `make_proof_workbook.py` lines 486 to 515 as literals. Sheet 19 finds 2 tables, the client list is the only `records` and included. Sheet 20 finds one block with `suggested_header_row == 3` and a warning, and after `rebuild_with_header(table, 3)` there are 3 data rows, 2 above the header, and the balance holds.
- `tests/golden/test_legacy_samples_read.py` (reading only). Data rows read from `tests/data/legacy_sample/`: clinic CSV 62, partner TSV 52, legacy XLSX 57, portal JSON 50, state XML 45, total 266, all tables `records`, all included, all balanced, no sensitive columns. The clinic table key is `clinic_export_csv :: data :: 3380a5d7`.
- `tests/golden/test_example_data.py`. Load the five files in `wholecount/sample_data/`. Every number in the `files` section of `EXPECTED.json` matches: tables and their kinds, the workbook's header row needing a choice (a `header_warning` and `suggested_header_row`), the `Notes` sheet unticked as not records, the Windows-1252 read, the `SSN` column dropped, and every file balanced. `tools/make_example_data.py --check` passes.
- `tests/unit/test_keys.py`. Every known-answer vector above, occurrence counting, a changed cell changes the key, keep or drop gives equal keys, ticking a continuation changes no key, the ` #2` rule, `normalize_file_name` cases (`Clinic Export (Q3).csv` is `clinic_export_q3_csv`, `C:\x\A  B.xlsx` is `a_b_xlsx`), the `~` suffix on the second and later files with one name, and `duplicate_file`. `test_letters.py` covers A, Z, AA, AZ, BA.
- `tests/invariants/test_key_stability.py`, SPEC 5.1.
  - Load the five example files in every order (Hypothesis permutations). Every table key and record key is the same. Only the letters change.
  - Re-export a file with one cell changed in one row, and another row added at the top. Every other row keeps its record key, and the changed row gets a new one.
  - Two different secrets give different record keys for every row, and neither key set contains the other.
  - Two files with one name are the stated exception, since the second takes the `~` suffix. A test pins this and notes it.
- `tests/unit/test_person_key.py`: the vectors, trimming and case of the system and Client_ID, no Client_ID falling back, both fallbacks, and a different system giving a different key. `test_fold.py`: `José`, `O'Brien`, `Mary-Ann`, `VAN BUREN` and a combining accent.
- `tests/unit/test_secret_store.py` and `test_dpapi_marshalling.py`: first call creates 32 bytes and a second returns the same; an unreadable store raises `SecretUnreadable` and makes nothing; `InstallSecret` is not in `repr`; the file double is chosen off Windows and DPAPI on `win32` (patch `platform`); the fake `crypt32` sees `CryptProtectData` input and output blobs, `LocalFree` is called, and a flipped byte raises `DpapiError`. `tests_windows/test_dpapi_roundtrip.py` runs the real calls under `install_for_app` with no violations, and skips off Windows.
- `tests/invariants/test_row_accounting_h4.py`. Hypothesis over random grids: every non-empty cell is in exactly one block, and `balanced()` holds. `test_read_determinism.py` reads the same bytes twice and gets equal keys and counts. `test_h08_progress_message.py`: `ProgressMessage` rejects `str`, `bool`, `float` and `None`, every `message_id` the loader uses exists in the registry, and the loader never puts a cell value into a message. `test_h09_secret_not_leaked.py`: the secret's hex and raw bytes appear in no dev output, message or repr, and `key.bin` written by the Windows store is not the plain secret (checked with the fake DPAPI).
- Copy: the two M01 claims each have a marked test, so `make copy` stays green.

## Done when

- [ ] `make test`, `make offline` and `make copy` are green, with the counts in the report.
- [ ] B-02, B-24, A-09, A-13 and C-23 each have a passing test and a line in `tests/audit/INDEX.md`.
- [ ] Both golden tests and the legacy reading test pass, and the legacy samples total 266 rows.
- [ ] `wholecount/sample_data/` holds the five example files and `EXPECTED.json`, the example data test passes, and `tools/make_example_data.py --check` passes.
- [ ] The three key tests pass: add order changes no key, a re-export with one changed row keeps every other record key, and two secrets give different keys. Every known-answer vector matches.
- [ ] No new dependency outside the approved set.
- [ ] The report lists the decisions logged above: the file name keeping its extension, record keys over cleaned cell texts, the U+001F joiner and the empty dob slot in the person key, `duplicate_file`, the half-of-values SSN threshold, the Linux file double for the secret, the header and above-header counts, letters only for readable files, and leading apostrophe removed from any text. It also names the spec tension that two files with one name make add order matter for the `~` suffix.
- [ ] `docs/milestones/M01-REPORT.md` is written, the branch is pushed, the pull request is open, and work has stopped.

## Windows checks for Joe

1. `py -3.12 -m venv .venv`
2. `.venv\Scripts\activate`
3. `pip install --require-hashes --no-deps -r requirements-dev.lock`
4. `python -m pytest -q`. All pass.
5. `python -m wholecount.dev read "C:\path\to\a real export.xlsx"` with one of your own client lists. For each file it prints a letter and counts, never names or values. Check that `rows_included` plus 1 for the header matches the used rows Excel shows, that `balanced` is 1, and that `rows_excluded` and `rows_non_table` are what you expect.
6. Run it on a CSV saved from Excel with "CSV (Comma delimited)" that has accented names. Expect `read_as_windows_text 1`.
7. Run it on a file with a blank line in the middle of the list. Expect `continuation_blocks 1`, and every row counted as included.
8. Run it on a file with a Social Security or Medicaid column. Expect `sensitive_columns_dropped` above 0. If you have an ID column that is nine digits, expect `sensitive_columns_by_values` to say whether it was taken for Social Security numbers, and tell me if it was wrong.
9. `python -m wholecount.dev read wholecount\sample_data\example_housing.xlsx`. Expect `tables_found`, `tables_included`, `rows_header` and `rows_above_header` to be what `wholecount\sample_data\EXPECTED.json` lists for that file (the `Notes` sheet is found and left out), and `balanced 1`. Open the five files in `wholecount\sample_data\` in Excel or Notepad and confirm the people look made up.
10. `python -m wholecount.dev secret`. The first run prints `install_secret_created 1` and `store_is_dpapi 1`. A second run prints `install_secret_created 0`. Open `%LOCALAPPDATA%\Wholecount\key.bin` in Notepad. Expect unreadable binary, and `stored_blob_is_larger_than_secret 1`. Do not delete the file, because later milestones use the same secret.

The dev command prints counts only. It never shows a client value.

## Out of scope

- Mapping columns, defaults and date order (M02). Tidy-up steps and the ZIP table (M03). Placeholders, standardizing and row checks (M04).
- Any screen, including the Add your files stage and its callouts (M11). Only the reason IDs and copy entries exist now.
- Replace-on-re-add of a same-name file and its confirmation (M08). The fingerprint is stored so M08 can use it.
- The install secret backup and restore and the saved crosswalk (M13), and master IDs (M06). The person key is built and tested here, but identity (M06) is what uses it. The per-row reason for an unreadable character (M04).
- Corrections files (M09). Saved progress and resume (M08 and M09).
