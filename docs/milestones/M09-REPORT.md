# M09 report

## Questions for Joe

One needs your call. The rest are the readings the milestone asked me to state, and the default is built in each case.

1. **A practice run writes eight files, not seven.** SPEC 9.1 lists ten files. A practice run leaves out Map_Counts and Map_Points, which leaves eight: the five data files, Data_Quality_Report and the two logs. The milestone says seven, but I couldn't find which file it meant to drop, so I kept all eight. If one more should go in practice runs, tell me which.
2. **In a practice run, the internal log's first line is the practice line**, ahead of the warning line.
3. **CSV cells starting with `=`, `+`, `-` or `@` aren't altered.** In Excel every cell is stored as text, so none of them runs as a formula.
4. **Run_ID isn't defined in the spec**, so it's derived from the included tables' keys and the install secret.
5. **The review file has blank `Corrected_<Field>` columns** for each field that failed on some row. A row fills only the columns for fields that failed on it.
6. **My definitions of four things:**
   - `Source_File` is the file name with no folder, plus " / " and the sheet for a workbook sheet.
   - `Duplicate_In_File` is Yes for any row in a copy group or same-ID group, whatever was decided.
   - `Possible_Duplicate_Of` lists the other members' record keys.
   - The most complete record is the one with the most non-blank mapped fields, with ties going to the smallest record key.
7. **Source letters in `Source_Records` and in the legend follow the order files were added.** Everything else is the same whatever the order.
8. **The people files and the maps count open copy groups and open pairs as separate people.** That's the high end of the range, and the receipt says so when pairs are open.
9. **Log lines from before a resume aren't saved.** A resumed log starts with `RESUME`, followed by one `DECISION` line per restored decision with its saved time and reviewer.
10. **The table of decisions by reviewer is in the internal log only.**
11. **Files are never overwritten without a yes.** `download` raises `WouldOverwrite` and writes nothing.
12. **`Counted_Not_Mapped` is added to the quality report.**
13. **Excel passwords aren't built.** That needs `msoffcrypto-tool`, which isn't approved.

Choices made on the most conservative reading:
- **A corrections row can partly apply.** A changed locked cell, or a correction to a field that didn't fail, is refused on its own and never read as a value. The row's other corrections still apply once its signature and originals check out. That's what A-10 asks: the Zip correction applies while the Last_Name edit is refused and named. A missing or wrong signature, a changed original, or an unknown record refuses the whole row.
- **Saved progress uses a checksum so its errors can be told apart.** A saved file is `WCS1`, then the SHA-256 of the DPAPI blob, then the blob. A checksum mismatch reads as `damaged`. A good checksum that DPAPI won't open reads as `other_user`.
- **The session ID for saved progress is a hash of the session's start time from the injected clock**, so nothing random is used.
- **Saved set-ups decode only from an allow-list of classes.** Those are the schema, fields, date settings and tidy-up steps. Anything else is refused as `unknown_value`.
- **The privacy offset is listed as applied on every real run.** It's never listed for a practice run, which writes no map files.

Changes to earlier milestones' code, each small:
- `AuditEntry` gains a `fingerprint` slot, used on `FILE_ADDED` in the internal log only.
- `Session` keeps `audit_log` as `(time, entry)` pairs, and `audit` is now a view over it. `History.undo` logs `UNDO` with the undone decision IDs. Every command and undo calls `Session.autosave()`.
- `tools/make_example_data.py` adds the remaining file counts to `EXPECTED.json`'s `outputs` section: review counted-yes rows, Unique_Clients, Unique_Clients_By_Program and Data_Quality_Report. Its note asked for that. The five example files didn't change.

## What was built

- **Engine, under `engine/outputs/`:**
  - `view.py`: `OutputView`, `OutRow` and `ExportSettings`
  - `columns.py`: `FileId`, the column lists and `chip_columns`
  - `tables.py`: one function per file
  - `review_file.py`: `run_id`, `row_signature`, `share_key` and the review layout
  - `corrections_in.py`: `read_corrections`
  - `audit_text.py`: `EVENT_SLOTS` and both log renderers
  - `summary_doc.py`: `SummaryDoc`, `build_summary` and `render_summary_html`
  - `receipt.py` and `folders.py`
  - `writer.py`: the CSV, Excel and JSON encoders, atomic writes and `write_text`
- **Session:**
  - `export.py`: `build_view`, `download` behind the gate, `save_summary` and the event builder
  - `store.py`: saved progress, set-ups, `prefs.json`, purge, and set-up export and import
  - `resume.py`: `resume` and `ResumePlan`
- **`wholecount/errors.py`:** `safe_error_text` and `install_excepthook`.
- **Settings and copy:** `settings/limits.toml`, plus the status words, file notes, log lines, summary, receipt, corrections refusals, folder callout, disk-write lines and the error sentence, each fact with a claim test.
- **Dev commands:** `dpapi-roundtrip`, `outputs-demo`, `folder-check`, `corrections-demo` and `saved-progress-demo`.

On the R and S fixture (with `Fay Gíl` and `00123`):

| State | Clean | Review | Set aside | Unique_Clients | By program |
| --- | --- | --- | --- | --- | --- |
| Base | 13 | 8 | 1 | 11 | 11 |
| Decided | 14 | 0 | 3 | 13 | 13 |

The example data with its planned decisions gives every row count in `EXPECTED.json`, in both the practice run and the no-geocoder run.

## Tests

| Command | Result |
| --- | --- |
| `make test` | 2194 passed |
| `make offline` | 60 passed |
| `make copy` | 474 passed |

`make test` and `make copy` include this report's own lint test. `tests_windows/test_dpapi_store_real.py` runs only on Windows.

New test files:
- `tests/rules/`: `test_outputs.py` (OUT-1 to OUT-14, SUM-1 to SUM-3), `test_review_file.py` (REVF-1 to REVF-5), `test_audit_logs.py` (AUD-1 to AUD-7), `test_store.py` (STORE-1 to STORE-8)
- `tests/outputs/`: `test_map_files.py`, `test_practice_runs.py`, `test_example_data_outputs.py`, `test_folder_warning.py`, `test_review_file_signature.py`, `test_shareable_log.py`, `test_xlsx_text_cells.py`, `test_receipt_and_gate.py` (the receipt and the held download), `test_setup_import.py`, `test_writes_only_in_three_files.py`
- `tests/invariants/test_outputs_properties.py`, `tests/copy/test_outputs_copy.py` and `tests/unit/test_dev_outputs.py`
- `tests_windows/test_dpapi_store_real.py`
- Fixtures and support: `tests/fixtures/outputs/fixture.py`, `tests/support/outputs.py`, `review.py`, `files_run.py` and `example_session.py`

The store error and purge cases are in `test_store.py` (STORE-4 and STORE-5).

Audit IDs closed:

| ID | Severity | Test |
| --- | --- | --- |
| A-01 | High | `tests/audit/test_A01_unmapped_columns.py` |
| A-02 | High | `tests/audit/test_A02_audit_has_no_values.py` |
| A-03 | High | `tests/audit/test_A03_summary_counts_only.py` |
| A-04 | High | `tests/audit/test_A04_disk_writes.py` |
| A-08 | High | `tests/audit/test_A08_resume_restores_all.py` |
| A-10 | High | `tests/audit/test_A10_no_typed_values.py` |
| A-15 | Medium | `tests/audit/test_A15_no_value_logs.py` |
| A-24 | Low | `tests/audit/test_A24_no_audit_cap.py` |
| C-06 | High | `tests/audit/test_C06_corrections_file_level.py`, with M08's test |
| C-11 | High | `tests/audit/test_C11_every_row_kind_exports.py` |
| C-22 | Medium | `tests/audit/test_C22_audit_tokens.py` |
| C-26 | Medium | `tests/audit/test_C26_chips_equal_columns.py` |
| C-27 | Low | `tests/audit/test_C27_stable_order.py` |

**C-11's summary row.** The audit expected the summary row in the review file. P-VAL-3 sets summary rows aside, so it's listed in Set_Aside_Records and never in the review file, and the test checks that.

## Done list

- [x] Every rule ID has a named test, and every audit ID has its own file and a line in `tests/audit/INDEX.md`.
- [x] Every file writes from the R and S fixture in CSV, Excel and JSON, in both states, with the counts above.
- [x] The log, disk-write and output scans find no fixture value, and the shareable log holds no file name or Client_ID.
- [x] No file log handler, and no file writes outside `writer.py`, `store.py` and `errors.py`. M01's `secret_store.py` writes `key.bin`, and `dev.py` is a developer tool. `test_writes_only_in_three_files.py` checks it.
- [x] No new dependency. `openpyxl`, `hashlib`, `hmac` and `json` only.
- [x] The report's Questions for Joe list covers the thirteen points, plus the eight-file practice count.
- [x] `make test`, `make offline` and `make copy` are green, with the counts above.
- [x] This report is written, the branch is pushed, and the pull request is open.

## Windows checks

Run from the repo with the branch checked out. The dev commands print counts and fixed labels only.

- [ ] 1. `.venv\Scripts\activate`, then `python -m pytest -q`. Expect no failures. `tests_windows/test_dpapi_store_real.py` now runs.
- [ ] 2. `python -m wholecount.dev dpapi-roundtrip`. Expect `dpapi_round_trip 1`, `changed_byte_detected 1`, `files_written 0`.
- [ ] 3. `python -m wholecount.dev outputs-demo --state base --out "C:\temp\wc_demo_base"`. It writes the made-up fixture with the data files in Excel and acknowledges the Low confidence first. Expect `clean_rows 13`, `review_rows 8`, `set_aside_rows 1`, `unique_clients_rows 11`, `by_program_rows 11`, `files_written 9`.
- [ ] 4. `python -m wholecount.dev outputs-demo --state decided --out "C:\temp\wc_demo_decided"`. Expect `clean_rows 14`, `review_rows 0`, `set_aside_rows 3`, `unique_clients_rows 13`.
- [ ] 5. Open each Excel file. Check:
  - no repair prompt, and the header you expect
  - `Gíl` intact and `00123` with its zeros
  - every cell shows as text, none as a formula
  - in Map_Counts, small cells read "fewer than 11"

  Then double-click a CSV. Accents should show correctly, and Excel will drop the zeros from `00123`, so open it in Notepad to confirm the zeros are in the file.
- [ ] 6. Open `Internal_Audit_Log.txt` and `Shareable_Audit_Log.txt` in Notepad.
  - Internal: the warning first line, a legend of file names, decision lines, and a reviewer table at the end.
  - Shareable: no file names, no row numbers, and different record keys.
  - Search both for `Oak` and `Lee`. Expect none.
- [ ] 7. `python -m wholecount.dev outputs-demo --state base --map-points --exact-coordinates --out "C:\temp\wc_demo_maps"`. Open Map_Points and confirm there are no names. Open Final_Clean_Mapped and confirm Latitude, Longitude and the column note.
- [ ] 8. `python -m wholecount.dev outputs-demo --state base --practice --out "C:\temp\wc_demo_practice"`. Expect `files_written 8` (question 1). Every file name starts with `PRACTICE_`, the first column is `PRACTICE`, no map files or district columns are written, and the receipt says why.
- [ ] 9. `python -m wholecount.dev folder-check --path "C:\Users\you\OneDrive\x"` prints `folder_warning 1`. A plain Documents path prints `folder_warning 0`.
- [ ] 10. `python -m wholecount.dev corrections-demo --out "C:\temp\wc_review"` writes the review file.
  - In Excel, type `11201` in `Corrected_Zip` for the R13 row and save.
  - Run `python -m wholecount.dev corrections-demo --out "C:\temp\wc_review" --apply "C:\temp\wc_review\Manual_Review_Needed.xlsx"`. Expect `corrections_accepted 1`, `corrections_refused 0`.
  - Change a name cell on that row and apply again. Expect `corrections_accepted 1`, `corrections_refused 1`, `refused_other_column 1`. The Zip correction still applies and the name edit is refused on its own.
- [ ] 11. `python -m wholecount.dev saved-progress-demo`. Expect `file_bytes` above 0, `decrypts_for_this_user 1`, `cell_values_found 0`. Open `%LOCALAPPDATA%\Wholecount\sessions\demo.wcs` in Notepad and expect unreadable binary. Then:
  - `--resume`: expect `decisions_restored 5`, `no_longer_apply 0`.
  - `--age-days 8 --purge`: expect `deleted 1`.
  - `--clean`.
- [ ] 12. Open the printable summary with Wi-Fi off. M12 adds the screen that saves it. Until then, a test renders it from the fixture, and `wholecount.session.export.save_summary` writes it. Expect "Counts only.", both balance lines and the confidence sentence, and no Master IDs.

## Screens

None. M09 is engine and session only.

## Not done

- **Excel passwords** (fix plan 4.3 step 5). They need a dependency that isn't approved.
