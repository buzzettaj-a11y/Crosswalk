# M01 report

## Questions for Joe

None block the milestone. These are the decisions the milestone asked me to log, then the choices I made where the text left room.

Decisions the milestone named:
1. **File names keep their extension in the key.** `Clinic Export.csv` is `clinic_export_csv`, so a CSV and a workbook with the same name get different table keys.
2. **Record keys hash the cleaned cell texts.** That's the row as read and cleaned (P-READ-3), before any column is dropped. Keeping or dropping a sensitive column never changes a key.
3. **The person key joins its parts with U+001F.** With no Client_ID and no date of birth, the date slot stays in the key as an empty part before the address key, so a name with an address can never collide with a name with a date.
4. **The same file added twice is skipped as `duplicate_file`.** Same normalized name and same fingerprint. M08 owns replacing a file.
5. **SSN by values needs more than half.** A column at exactly half SSN-shaped values is kept.
6. **The secret's Linux double keeps the bytes in the clear.** `FileSecretStore` says `INSECURE = True` and is never chosen on Windows. Off Windows it lives in `WHOLECOUNT_DATA_DIR`, or `~/.wholecount` when that isn't set.
7. **Header rows and rows above the header are both counted** in the file accounting, as H4 and P-READ-7 name them.
8. **Only readable files take a letter.** A bad file between two good ones leaves no gap: the good ones are A and B.
9. **A leading apostrophe is removed from any text,** not just numbers, as long as something follows it.
10. **Spec tension: two files with one name make add order matter.** The second file with a normalized name takes `~` and six hex of its fingerprint, so whichever is added second gets the suffix. Everything else about the keys ignores add order. `test_two_files_with_one_name_are_the_stated_exception` pins it.

Choices on the most conservative reading:
- **A table with no header row isn't counted until someone picks one.** The example workbook's `Clients` sheet has two title lines, so no header is detected. The table comes in as `unknown`, unticked, with the warning `no_header_but_row_looks_like_names` and row 3 suggested. Its rows count as excluded until the operator chooses row 3. Guessing the header would be a silent switch, which P-READ-6 forbids. `EXPECTED.json` records the planned choice under `decisions.header_rows` and the counts after it under `files.example_housing.xlsx.after_header_choice`.
- **Choosing a header recomputes the table's kind and default tick.** After choosing row 3, `Clients` becomes `records` and ticked.
- **JSON wrappers.** The spec's rule is that a list is the records, an object with exactly one list value uses that list, and anything else is one record. The example's `{"export": {"clients": [...]}}` has no list at the top, so I added one step: an object whose only value is another object is looked into. Lists of objects inside a record flatten with 1-based numbers, like `programs.1.name`.
- **XML details.** Attributes on the record element itself become `@name`. A leaf that repeats is joined with `; `.
- **JSON and XML blank records** split the records into runs, and the later runs join the first as continuations.
- **A table with no header row gets its signature from the generated `Column_N` names.**
- **A second accounting claim.** Side-by-side tables share file rows, and the one-line sentence can't say that truthfully. So `read.accounting_line_shared` (claim `CL-READ-ACCOUNTING-02`) adds the shared count. Both claims have tests.
- **`read_path` takes only the path.** The milestone's signature also passed a progress sink and the keep set. The loader reports progress and applies the keep set, so the reader doesn't need either.
- **An integral number in a `0.00` format reads as an integer** (`5`, not `5.00`), because the milestone's rule puts integers first.
- **DPAPI under the guard.** Plain ctypes calls raise no audit event, so DPAPI works under the guard. It reads results by slicing the blob pointer, never with `ctypes.string_at`, which the guard denies. `tests_windows/test_dpapi_roundtrip.py` proves it on Windows.

**On writing tests first.** As in M00, I wrote each module's tests right after its code, not strictly before. I kept the negative controls. The memory scan for dropped values has its own control, which finds every value of a column that was kept on purpose.

**The example data plan beyond `files`.** M01 checks only the `files` section. The other sections are the plan's best reading of rules later milestones build, and a few are knowingly partial:
- `map.after_steps` names the source column of each split field, because M03 names the new columns.
- `outputs` has only the three row files, because M09 defines the rest.
- `locations` is empty until M05.

Each later milestone checks its own section and changes the plan in the script if it's wrong.

## What was built

- **SPEC 11.6.2, 11.6.3.** `engine/progress.py`: the 16 step names, units, `SourceRef`, `StepRef`, `ProgressMessage` (which takes only those two types and `int`), `ProgressSink`, `NullSink`, `RecordingSink` and `render`.
- **SPEC 4.3.** `engine/letters.py`.
- **Settings.** `settings/loader.py`, `sensitive_columns.toml`, `table_hints.toml`.
- **P-READ-1 to P-READ-3, P-READ-8, P-READ-10.** `engine/read/` holds `model.py`, `text.py` (strict UTF-8, then strict Windows-1252), `clean.py`, `xlsx.py` (`cell_text` and cell formats), `structured.py` (JSON and XML, with lxml's network, entities and DTDs off) and `reader.py` (takes only a `pathlib.Path`).
- **P-READ-4 to P-READ-6.** `engine/read/tables.py`: splitting blocks, `detect_header`, `header_looks_wrong` returning reason IDs, `classify`, continuations and `rebuild_with_header`.
- **P-READ-7, H4.** `engine/read/accounting.py`: `FileAccounting` with shared rows and the cell-partition check.
- **P-READ-9, H10.** `engine/read/sensitive.py`: `ssn_shaped`, `looks_like_ssn_column`, whole-word names and `drop_sensitive`.
- **SPEC 5.1, H9.** In `session/`:
  - `dpapi.py`
  - `secret_store.py`: `SecretStore`, `DpapiSecretStore`, `FileSecretStore`, `default_store`, `get_or_create_secret` and `InstallSecret`
  - `keys.py`: file names, fingerprints, signatures, file keys, table keys, record keys and person keys
  - `loader.py`: `load_files`, `FileOutcome` and `LoadResult`
- **P-DUP-6.** `engine/fold.py`.
- **Copy.** Every step name, the reading lines, the encoding note (`CL-READ-ENCODING-01`), the two accounting lines (`CL-READ-ACCOUNTING-01` and `-02`), and one sentence per unreadable reason.
- **P-GEO-4a.** `tools/make_example_data.py` and `wholecount/sample_data/`, which holds five files and `EXPECTED.json`, 287 rows in all.
- **Dev commands.** `python -m wholecount.dev read` and `secret`, counts only.

## Tests

| Command | Result |
| --- | --- |
| `make test` | 416 passed |
| `make offline` | 55 passed |
| `make copy` | 72 passed |
| `tools/make_example_data.py --check` | `files_differing 0` |

New test files:
- `tests/rules/`: `test_P_READ_1_formats.py`, `test_P_READ_2_encodings.py`, `test_P_READ_3_invisible.py`, `test_P_READ_4_blocks.py`, `test_P_READ_5_continuation.py`, `test_P_READ_6_headers.py`, `test_P_READ_7_accounting.py`, `test_P_READ_8_bad_files.py`, `test_P_READ_9_sensitive.py`, `test_P_READ_10_no_urls.py`
- `tests/audit/`: `test_B02_cp1252_names.py`, `test_B24_invisible_characters.py`, `test_A09_rows_outside_tables.py`, `test_A13_bad_file_does_not_block.py`, `test_C23_blank_line_and_comma_row.py`
- `tests/golden/`: `test_proof_19_20_tables.py`, `test_legacy_samples_read.py`, `test_example_data.py`
- `tests/unit/`: `test_keys.py`, `test_person_key.py`, `test_fold.py`, `test_letters.py`, `test_secret_store.py`, `test_dpapi_marshalling.py`
- `tests/invariants/`: `test_key_stability.py`, `test_row_accounting_h4.py`, `test_read_determinism.py`, `test_h08_progress_message.py`, `test_h09_secret_not_leaked.py`
- `tests_windows/test_dpapi_roundtrip.py`
- Support: `tests/support/` gained `secrets.py`, `fake_dpapi.py`, `files.py`, `grids.py` and `load.py`. `tests/data/` holds the legacy samples and two audit fixtures, copied unchanged.

Audit IDs closed:

| ID | Severity | Test |
| --- | --- | --- |
| B-02 | High | `tests/audit/test_B02_cp1252_names.py` |
| B-24 | Medium | `tests/audit/test_B24_invisible_characters.py` |
| A-09 | High | `tests/audit/test_A09_rows_outside_tables.py` |
| A-13 | Medium | `tests/audit/test_A13_bad_file_does_not_block.py` |
| C-23 | Medium | `tests/audit/test_C23_blank_line_and_comma_row.py` |

The legacy samples read 62, 52, 57, 50 and 45 rows, 266 in all. The clinic table key is `clinic_export_csv :: data :: 3380a5d7`. Every known-answer key vector in the milestone matches.

The example data, from `EXPECTED.json`:

| File | Table rows at load | Notes |
| --- | --- | --- |
| `example_clinic.csv` | 60 included | Jammed names and addresses |
| `example_housing.xlsx` | 0 included, 73 excluded | After choosing row 3: 66 rows plus the `Total` row, 2 above the header, `Notes` left out |
| `example_partner.tsv` | 55 included | Windows-1252, `SSN` dropped |
| `example_portal.json` | 55 included | Nested |
| `example_state.xml` | 50 included | No program column |

The plan's counts:
- **Before any decision:** Goal 1 is 259 to 264 and Goal 2 is 218 to 220, with 3 open pairs and 2 open copy groups.
- **After the planned decisions:** Goal 1 is 261 and Goal 2 is 219.

## Done list

- [x] `make test`, `make offline` and `make copy` are green: 416, 55 and 72 passed.
- [x] B-02, B-24, A-09, A-13 and C-23 each have a passing test and a `done` line in `tests/audit/INDEX.md`.
- [x] Both golden tests and the legacy reading test pass, and the legacy samples total 266 rows.
- [x] `wholecount/sample_data/` holds the five example files and `EXPECTED.json`, the example data test passes, and `--check` passes.
- [x] The three key tests pass, and every known-answer vector matches:
  - Add order changes no key.
  - A re-export with one changed row keeps every other record key.
  - Two secrets give different keys.
- [x] No new dependency. The locks are unchanged.
- [x] The decisions are logged above, and so is the add-order tension for two files with one name.
- [x] This report is written, the branch is pushed, and the pull request is open.

## Windows checks

- [ ] 1. `py -3.12 -m venv .venv`
- [ ] 2. `.venv\Scripts\activate`
- [ ] 3. `pip install --require-hashes --no-deps -r requirements-dev.lock`
- [ ] 4. `python -m pytest -q`. All pass.
- [ ] 5. `python -m wholecount.dev read "C:\path\to\a real export.xlsx"` with one of your own client lists. For each file it prints a letter and counts, never names or values. Check that `rows_included` plus 1 for the header matches the used rows Excel shows, that `balanced` is 1, and that `rows_excluded` and `rows_non_table` are what you expect.
- [ ] 6. Run it on a CSV saved from Excel with "CSV (Comma delimited)" that has accented names. Expect `read_as_windows_text 1`.
- [ ] 7. Run it on a file with a blank line in the middle of the list. Expect `continuation_blocks 1`, and every row counted as included.
- [ ] 8. Run it on a file with a Social Security or Medicaid column. Expect `sensitive_columns_dropped` above 0. If you have an ID column that is nine digits, check whether `sensitive_columns_by_values` took it for Social Security numbers, and tell me if that was wrong.
- [ ] 9. `python -m wholecount.dev read wholecount\sample_data\example_housing.xlsx`. Expect `tables_found 2`, `tables_included 0`, `rows_header 0`, `rows_above_header 0`, `rows_excluded 73` and `balanced 1`, which is what `EXPECTED.json` lists before the header row is chosen. Open the five files in `wholecount\sample_data\` in Excel or Notepad and confirm the people look made up.
- [ ] 10. `python -m wholecount.dev secret`. The first run prints `install_secret_created 1` and `store_is_dpapi 1`. A second run prints `install_secret_created 0`. Open `%LOCALAPPDATA%\Wholecount\key.bin` in Notepad. Expect unreadable binary, and `stored_blob_is_larger_than_secret 1`. Don't delete the file, because later milestones use the same secret.

The dev command prints counts only. It never shows a client value.

## Screens

None. M01 has no UI.

## Not done

Nothing.
