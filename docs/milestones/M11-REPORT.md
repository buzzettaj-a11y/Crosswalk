# M11 report

## Questions for Joe

Nothing blocks. Three gaps in earlier milestones came up, and I left the engine as it is for each one:

1. **The calculated ZIP step never gets a lookup during Process.** `engine/pipeline.prepare` runs the tidy-up steps without a resolver. So a Calculate the ZIP step always ends with "no lookup available," even with Geosupport or a reference file present.
   - The Tidy up form still names the real backend, as the milestone asks.
   - Passing the backend in is plumbing rather than a rule change, but it changes what Process produces.
   - Should I wire it in M12?
2. **Process's own fast-path check never sees an SSN-shaped Client ID.** `session/runner.fast_path` calls `process_blocks` without the column profiles.
   - The window doesn't use that path. Its holds and the blocked band read the survey, which passes the profiles and the source defaults, so the SSN block and the defaults both work on screen.
   - Should `runner.fast_path` get the same arguments in M12?
3. **Date order and the two-digit year rule apply only to Date_of_Birth during Process.** The runner reads `date_orders` for that field alone.
   - Match your columns stores the answer for custom date fields too, so it's kept, but Process ignores it until the runner reads it.

Readings I took. The default is built in each case.

4. **Command names.** M08 has one `SetupChange(section, key, value)` for set-up edits, so most of the milestone's intents use it.

   | Milestone intent | What fires |
   | --- | --- |
   | `SetHeaderRow`, `IncludeTable` | `SetupChange("tables", (file, index, "header_row" or "included"), value)` |
   | `SetSourceSystem`, `RenameSystem` | `SetupChange("systems", ("member" or "name", file), value)`, in a new `systems` set-up section |
   | `RemoveSource` | `SetupChange("sources", path, False)` |
   | `AddStep`, `RemoveStep`, `RestoreStep` | `SetupChange("steps", (file, index), steps)` |
   | `EditCustomField`, `ResetSchema`, `SetClientIdRequired` | `SetupChange("schema", "schema", schema)` |
   | `SetMapping` | `SetupChange("mappings", (file, index, field), column)` |
   | `SetDefault`, `SetProgramDefault` | `SetupChange("defaults", (file, index, field), value)` |
   | `SetDateOrder`, `SetTwoDigitRule` | `SetupChange("date_orders", (file, index, field), DateFieldSetting)` |
   | `SetProgramColumn` | A Program mapping change, plus `program_columns` set to `none` for "(no program column)" |
   | `ConfirmProgramGroup`, `SplitProgramGroup`, `SplitProgramName`, `RenameProgramGroup` | `DecideProgramGroup` with `confirm`, `split`, `merge` or `rename` |

   Seven new commands, so `ALL_COMMANDS` grows from 17 to 24:
   - `AddSources`: one Undo takes back a whole add
   - `UseExampleData`
   - `SetKeepSensitive`
   - `ConfirmTable`
   - `ConfirmStage`: Continue on Tidy up
   - `LoadSetup`
   - `WithdrawProgramDecision`: the `undo` link on one group, and Start again from the proposal
5. **The survey.** `session/survey.py` runs the engine's read, find tables, tidy, match, check and standardize steps on the set-up as it stands. Stages 01 to 05 read it.
   - It's cached by its own inputs only, so a review decision never re-reads a file.
   - It runs on the main thread when a set-up change makes it stale. Adding files and Process run on the worker.
   - On a 19,000-row batch a set-up change could pause the window for a second or two. Please time it in the Windows checks (step 10 below).
6. **Step dry runs come from the survey.** The milestone describes a separate `preview_steps` job; they're computed in the survey instead. A removed step is previewed on its own with `session.survey.preview_step`. So the "Checking..." text has no slow case to cover.
7. **Adding files reads every file in the batch again,** the earlier ones too, so letters and record keys stay the same. Within one add, each file is read once, and Process reuses that load.
8. **A corrections file is recognized from that same load,** by the Record_Key, Run_ID and Signature headers. It's never added as a source, and nothing from it is kept but its name.
9. **Dropping an SSN-shaped Client ID column ends its keep.** Such a column is only present because it was kept at load, so "Drop this column" fires `SetKeepSensitive(column, False)` and the file is read again without it.
10. **Sample values for an SSN-shaped column are never shown,** not even under its combo on Match your columns.
11. **Systems.** A file joins another file's system, or keeps its own. A system change marks Process and everything after it out of date.
12. **Three sentences reworded.** M05's B-34 test forbids "only in" anywhere in the registry, so "only inside one system" became "within one system" in the systems card, the Client_ID handling line and the Client_ID note.
13. **An M08 copy bug, fixed.** `commands.program_rename` didn't take the name count its command passes, so the Undo label crashed after a rename. It reads "Rename a program group of {count} names" now.
14. **The Tidy up group-by choice is a view choice in `prefs.json`,** through a new `Store.set_pref`. It holds no client data.
15. **Confirmed tables and the kept-steps flag are view facts on the session.** They change no result and aren't in saved progress.
16. **Split a jammed address names its columns after the source column.** The milestone's "Start the new column names with" box isn't there, because M03's step has no prefix option. The form lists the fixed names.

Changes to earlier tests:
- `tests/rules/test_counts.py` counts 24 commands, not 17.
- `tests/invariants/test_staleness.py` covers the new `systems` section.
- `tests/ui/test_held.py` allowlists `ui/jobs/actions.py`. Those are jobs, not widgets.
- `tests/ui/test_accessibility.py` treats a spin box as one control.
- `tests/ui/test_feature_ledger.py` gains the M11 rows.

## What was built

- **Shared pieces.** `ui/widgets/grid.py` (`GridView`, `RowsModel`, `Pager`, `GridStates`), `ui/widgets/preview.py` (`DataPreview` with the header-row picker), `ui/widgets/setups.py` (`SetupsPanel`) and `ui/stages/_common.py`.
- **Add your files (11.5, 5.1, 6.1, 10.2, 12.6).**
  - The resume card with Resume and Delete saved progress
  - The fast path card and its holds
  - The drop zone, with drag and drop (A-18), Browse and Try example data
  - Notices: unreadable files, encoding samples, sensitive columns dropped at load, a network drive, a corrections file and a changed file on resume
  - The source systems card and the table list with tags and Show data
  - Rows accounted for, and saved set-ups
- **Your columns (4.1).** The fields grid with custom field editing, add a field with its checks, reset, How a row is tested, and Test fit by source.
- **Tidy up (6.3).** The five rule cards with every option, the step list in three groupings with origin tags, remove and restore, and amber do-nothing rows.
- **Match your columns (6.2).** The blocked run band (missing required fields and SSN-shaped IDs), the column check callout, the tables list and the field grid with samples and one-click fixes, date order, the two-digit year rule, confirm and next table, fill a field for one source, and the unmapped columns line.
- **Programs (6.7).** Program columns per source with the codes warning and one name for a whole file, name groups with pick up, move, count on its own, put back, rename, confirm, keep separate and undo, and the preview with its out-of-date state.
- **Session.**
  - `survey.py`, `setups.py`, `schema_edit.py`, `steps_edit.py` and `map_edit.py`
  - More in `frame.py`
  - The `systems` set-up section, and `system_names` in the runner
  - `keep_sensitive` in the load cache key and the tables fingerprint
  - The seven new commands
- **Jobs.** `ui/jobs/actions.py`: `AddFilesJob`, `ProcessJob`, `PreviewJob` and `ResumeJob`.
- **Copy.** Every sentence on the five stages, plus `help.stage.*` for each.

## Tests

| Command | Result |
| --- | --- |
| `make test` | TEST_COUNT passed |
| `make offline` | OFFLINE_COUNT passed |
| `make copy` | COPY_COUNT passed |

New test files:
- `tests/ui/test_m11_sources.py`, `tests/ui/test_m11_schema_prepare.py`, `tests/ui/test_m11_map_programs.py` and `tests/ui/test_m11_frame.py`
- `tests/audit/test_A18_drop_files.py`
- `tests/support/m11.py`

Every new claim has a behavior test. That includes the fast path holds, rows accounted for, example data and PRACTICE, sensitive columns, corrections, drop, systems, resume, the schema rules, tidy-up ZIP and removed steps, and the Match and Programs sentences.

Audit IDs closed:

| ID | Severity | Test |
| --- | --- | --- |
| A-18 | Medium | `tests/audit/test_A18_drop_files.py` |

## Done list

- [x] The five stages are built to sections 1 to 5 and register with `StageRegistry`.
- [ ] Every test above was seen to fail first, then passes. They all pass. The claim check failed first and listed every new claim, and the A-18, held-state and width tests found real bugs before they passed. Most stage tests were written right after their stage, not before.
- [x] `make test`, `make offline` and `make copy` are green, with the counts above.
- [x] `make screens` renders all five stages at 1440 and 1280, fresh and populated with the five example files. The 20 PNGs are in `docs/milestones/screens/M11/`.
- [x] Differences from the boards are listed below.
- [x] This report is written, the branch is pushed, and the pull request is open.

## Windows checks

Run from source (`.venv\Scripts\activate`, then `python -m wholecount`) with the five example files from `wholecount\sample_data\`. Keep `wholecount\sample_data\EXPECTED.json` open in Notepad to compare.

- [ ] 1. On Add your files click `Try example data`.
  - Five files appear, with the tables `EXPECTED.json` lists under `files`. The workbook's `Notes` sheet is left out.
  - The top bar shows an amber PRACTICE tag.
  - The rows-accounted-for card shows the same numbers as `EXPECTED.json`. Compare with `C1_Files.png`.
  - The header row tag is amber.
- [ ] 2. Drag and drop.
  - Open File Explorer, select two of the example files and drag them onto the window.
  - The drop zone turns blue while you hold them over it. Drop, and they're added.
  - Now drag the same files onto a text box on another stage. Nothing should be inserted.
- [ ] 3. Click `Show data` on the example workbook, whose header row needs choosing. Change the header row and watch the columns change. Close it.
- [ ] 4. Open `Your columns`. Add a custom field called `Notes_Code` of type whole number. Try the name `Notes Code` and read the message. Remove it.
- [ ] 5. Open `Tidy up`. Switch Group by to Rule, Source and Who added it. Add a Clean columns step, then remove and restore it. Compare with `C1b` and `C1c`.
- [ ] 6. Open `Match your columns`.
  - Find the amber callouts and press the blue button inside one.
  - Open `Fill a field for this source only`.
  - Check the date order question appears for a date column.
  - On a date field pick `Use a rule`, type 26, and read the example line.
  - From a test file of your own, map a Client_ID column that holds nine-digit numbers like 123-45-6789. Confirm Process is blocked with the Social Security sentence.
- [ ] 7. Open `Programs`.
  - Pick up one of the program names `EXPECTED.json` lists under `programs` as a planned proposal, click its group, and confirm.
  - Confirm that `Continue to Process` is gray with a caption until every group is decided.
  - Press `Refresh the preview`.
- [ ] 8. Press Tab through each stage and confirm every control gets an outline.
- [ ] 9. Resize under 1360 pixels wide on each stage. Nothing scrolls sideways.
- [ ] 10. With a real batch of about 19,000 rows, change one column match on Match your columns. Note how long the window takes to redraw (question 5).

## Screens

Committed in `docs/milestones/screens/M11/`, `m11-{NN}-{stage}-{fresh|populated}-{width}.png` for each of the five stages:
- [`m11-01-sources-populated-1440.png`](screens/M11/m11-01-sources-populated-1440.png)
- [`m11-02-schema-populated-1440.png`](screens/M11/m11-02-schema-populated-1440.png)
- [`m11-03-prepare-populated-1440.png`](screens/M11/m11-03-prepare-populated-1440.png)
- [`m11-04-map-populated-1440.png`](screens/M11/m11-04-map-populated-1440.png)
- [`m11-05-programs-populated-1440.png`](screens/M11/m11-05-programs-populated-1440.png)
- The fresh frames and the 1280 frames sit beside them.

Differences from the boards:
- **Add your files has cards the boards don't draw:** the source systems card, rows accounted for, the notices, the resume card and saved set-ups.
- **Your columns has no board.** It follows the Tidy up cards.
- **Held controls show their caption under the button,** at least 220px wide, so it never wraps to a sliver.
- **The rule cards are buttons with a 3px top rule.** The selected one is blue, as the board shows.
- **The checkbox shows a solid fill when ticked rather than a drawn check mark.** A check mark would need an image file in the style sheet.

## Not done

- **A set-up's optional note isn't kept.** M09's `Store.save_setup` takes a name only. The note field is on screen and is ignored. I'll add it with Download's set-ups in M12 unless you'd rather drop the field.
- **`GridState` is kept for each stage and grid, but Show data opens at the top each time.** Only one grid exists so far, and it's in a drawer.
