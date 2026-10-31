# M12 report

## Questions for Joe

Nothing blocks. Writing the tests turned up four bugs in earlier milestones, and I fixed each one. I need your OK on the first, because it changes how M08's staleness works.

1. **Changing a download setting no longer makes the results out of date.** In M08, the `exports` node took the export settings as its own input. M12 stores the Download switches in that set-up section, so ticking `Write Map_Points` marked everything as out of date. Download was then held until a new run.
   - **The fix.** `Session.stale` now covers the result nodes only. Download always builds its files from the current results with the current settings, so a changed switch has nothing to hold.
   - **What's kept.** `Session.stale_nodes` still includes `exports`, and every command still declares it.
   - **Four earlier tests changed.** They used an export setting as their example of a stale change, and now use an extra Geosupport field instead. They are `tests/rules/test_counts.py` (STALE-4), `tests/outputs/test_receipt_and_gate.py`, `tests/audit/test_C18_stale_after_setup_change.py` and `tests/invariants/test_staleness.py`.
   - **A new test** checks that an export setting marks only `exports`, and holds neither the counts nor Download.
   - Is that reading right? The other choice is to keep the switches somewhere other than the set-up, which would leave them out of saved set-ups.
2. **The Other note never reached the internal audit log.** `SetAsideRows` kept the note on its own command entry, and M09's `build_events` never read it.
   - The note now rides on each set-aside decision as `detail` and goes on that decision's log line.
   - The shareable log still drops it, as M09's slot rules say.
3. **"No longer apply" crashed on four lapse reasons.** `file_removed`, `group_changed`, `row_set_aside` and `dob_now_differs` had no sentence.
   - I added one sentence each.
   - A test now checks that every lapse reason and every decision kind has copy.
4. **The corrections result had nowhere to show.** The job finished, but no drawer read its result. It now opens a drawer:
   - first `{a} rows accepted, {b} refused. {c} of the accepted rows now count.`
   - then one line per refused row, `Row {line}: {reason}`

Readings I took. The default is built in each case.

5. **The fourth corrections refusal.** M09 sent `unknown_record` to the "has changed" sentence. On screen it reads `This row is not in this batch.`, as the milestone lists.
   - `field_not_failing` and `other_column_changed` both use `{column} did not fail, so it can't be corrected here.`
   - The three file-level refusals (not a review file, a duplicate record, a set-aside row) keep M09's sentences.
6. **Only Map_Points has a switch.** The other nine files are always written and carry `ALWAYS WRITTEN`.
   - A bug was fixed along the way. Once Map_Points was ticked, its checkbox disappeared, so it couldn't be turned off.
   - In a practice run the box shows and is held, with the practice sentence as its reason.
7. **A third place for the Low tick.** The Download stage shows the confidence block with its tick, so the held caption isn't a dead end. SPEC 7.4 and 11.7 list only the ledger and Process.
8. **A second sign-off on queue approvals over 200 rows.** Approving more than 200 rows from step 2 asks for a second reviewer's name, the same rule as Accept all as they are.
9. **No per-file bars during Download.** M09's writer writes all the files in one call, so the `download` job shows its steps and not one bar per file.
   - Cancel works only until the writer starts. After that the files finish, and the receipt lists them all.
   - The writer's temporary names already keep a half-written file out of the folder.
   - One bar per file needs the writer to report each file. That's a small M09 change. Should I make it?
10. **The corrections job runs two of its three steps on the worker.** Re-applying decisions happens when the result is applied on the main thread, so the third step has no bar of its own.
11. **The backend line uses `frame.backend_kind(backend)`,** not `backend.describe()`. No backend has `describe()`. `backend_kind` reads the backend's name, so it matches the system check.
12. **Fewer files than the milestone's layout.** The milestone lists twelve files for `review/` and several each for the other stages. I kept what goes together in one file:
    - `review/` has `body.py`, `dialogs.py`, `queue.py` and `record.py`
    - `run/`, `summary/` and `export/` have `body.py` each
13. **One button reworded.** `Compare the {g}` read "Compare the 1" for one group. It's now `Compare the groups ({g})`.
14. **Dialogs get the card background.** One added QSS rule, `QDialog { background: bg-card }`. Without it a dialog grabbed for the screens was see-through, and it would show the system color on Windows.
15. **The top bar says "Addresses will not be placed" during a practice run.** That's M10's preflight line, and it's true for a real run on this machine. In a practice run, the sample file does place addresses. Should the top bar say so when example data is loaded?

Still open from earlier milestones:
- **M09 question 1.** A practice download writes 8 files. Windows check 9 below expects `Download 7 files`.
- **The three M11 questions.** The calculated ZIP lookup during Process, `runner.fast_path` without profiles, and date settings for custom date fields.

Claims reused from earlier milestones, tested here only as shown on screen:
- `outputs.practice.no_maps`
- `outputs.folder_callout`
- the receipt notes `outputs.note.*`
- the Data_Quality_Report sentence (M09's claim ID)
- `map.fewer_than`

One thing to know about how this milestone was tested. The claim test (`tests/copy/test_claims_have_tests.py`) failed first and listed every new claim until each one had its test. The stage widget tests were written after the stages, not before. Each claim test drives the behavior rather than reading the string, and the four bugs above came from that.

## What was built

- **Process** (`ui/stages/run/body.py`):
  - the holds in order (no table, a blocker, an SSN-shaped ID, programs to confirm)
  - the four pre-run lines
  - run settings with the extra Geosupport fields only
  - the run panel with cancel and failure states, the folded finish line and its log
  - the confidence callout, and what the run found, with both balances and the per-table view
- **Fix problems** (`ui/stages/review/`):
  - the reviewer prompt and the two-step header, plus the three tabs and the cause cards with their actions
  - Accept all as they are (five sample rows, typed count, reason, second reviewer over 200), Set all aside with the fixed reasons and the 120-character Other note
  - the preview drawer, the fill preview, and the matching diagnosis with `Match it and process again`
  - Compare, no longer apply, and the corrections file with its result drawer
  - the queue with filters, search, page size, select page and all matching, and the four bulk actions
  - the record panel, with unmatched columns on screen only and `Open the source file`
- **Results** (`ui/stages/summary/body.py`):
  - the status callout, both goals with ranges, and the pair list with bands and decisions
  - automatic joins with split, programs, locations with the no-address breakdown, and the person table
  - the printable page with the file names tick, saved as PDF or web page
- **Download** (`ui/stages/export/body.py`):
  - the holds from `download_gate`, the balance band and the Low block
  - formats, the ten files, exact coordinates, Map_Points, column chips and set-ups
  - the folder flow with the synced-folder and replace questions, the download job, the receipt and the footer
- **Session layer.**
  - `session/pages.py`, `session/reviewer_view.py` and `session/corrections_view.py`
  - the M12 additions to `session/frame.py`
- **Shared widgets:** `tonetag.py`, `bars.py`, `pagebar.py` and `confirm.py`.
- **Shell open:** `ui/shell.py` opens a source file only if it's in this batch, after a confirm.
- **Screens.** `tools/screens.py` renders the M12 frames.

## Tests

| Command | Result |
| --- | --- |
| `make test` | 3753 passed |
| `make offline` | 60 passed |
| `make copy` | 1576 passed |

New test files:
- `tests/ui/test_m12_process.py`: holds in order, the four backend lines, reads once and changes nothing, the map line and small cells, no writes during a run, cancel, a failure with a canary value, and what the run found
- `tests/ui/test_m12_review.py`:
  - the reviewer on both logs, the finish hold, location rows that count, and a preview that changes nothing
  - the Other note in the internal log only, the keep-one plan, the fill preview, and both corrections refusals with a reversed file
  - no longer apply, unmatched columns in no file or log, opening the source file, and every lapse reason with a sentence
- `tests/ui/test_m12_results.py`: final and the settled sentence, people without a program, rows without an address, nothing called verified, and no digits while stale
- `tests/ui/test_m12_export.py`: the Low hold, the band against the files, the receipt and footer, exact coordinates, moved points through the UI, and the practice Map_Points hold
- `tests/ui/test_m12_static.py`: only the allowed free-text boxes, the Other note's limits, and no offset, seed or unplaced setting
- `tests/ui/test_feature_ledger.py`: the M12 rows

## Done list

- [x] The four stages are built to sections 1 to 4 and registered in `ui/stages/__init__.py`.
- [x] Every test above passes. The claim test failed first. See the note at the end of Questions for Joe about the widget tests.
- [x] `make test`, `make offline` and `make copy` are green, with the counts above.
- [x] `make screens` renders the four stages at 1440 and 1280, before a run and after a sample run, Process mid-run, Fix problems step 2, the bulk accept dialog and the Results pair list. The PNGs are in `docs/milestones/screens/M12/`.
- [x] This report lists the readings the milestone names: one switch only, the third Low tick, the second sign-off and the fourth refusal. The differences from the boards are below.
- [x] This report is written, the branch is pushed, and the pull request is open.

## Windows checks

Run from source (`.venv\Scripts\activate`, then `python -m wholecount`), with the five example files loaded by `Try example data`. This is a practice run, and `wholecount\sample_data\EXPECTED.json` holds the numbers to expect.

- [ ] 1. On Process, read the four lines of the summary. Compare the backend line with the system check. Press `Process everything`, and while it runs click through the other stages. The ticker follows you and data controls say they are held.
- [ ] 2. Run it again and press `Cancel` about halfway. The notice says nothing was changed and the ledger is as before. Run it to the end. Read the confidence callout, both equations, and `Show the log`. The counts and both equations match the `counts` section of `EXPECTED.json`.
- [ ] 3. Open Fix problems. Type your name when asked and compare the tabs with `C3_Fix_Groups.png`. Press `Look up all` on the ZIP cause, read the list, press `Cancel`, and confirm nothing moved. Run it again and press `Apply`.
- [ ] 4. Press `Accept all as they are` on one cause. Read the five rows, type the wrong number, then the right one, pick a reason and accept. Press Undo and confirm the cause is open again.
- [ ] 5. Open step 2. Filter by problem, tick the page, press `Set aside`, and read the reasons offered. Open one row. Compare the panel with `C4_Fix_Queue.png`, open the unmatched columns and press `Open the source file`.
- [ ] 6. Press `Compare the groups` on the copies cause. Pick a different row to keep and find the other row under Set aside.
- [ ] 7. On Results, press `Decide them now`. Decide one pair each way and watch Goal 1 move. Press Undo. Open `Show them` under Joined without asking and split one. Find `Counted, no usable address` and its breakdown.
- [ ] 8. Press `Open a page to print or hand on`. Save a PDF to the Desktop with the file names tick off, then on. Confirm there are counts and no person names or IDs. Save the web page and open it in your browser.
- [ ] 9. On Download, check that Map_Counts and Map_Points say they aren't written in a practice run. The button reads `Download 8 files` until M09 question 1 is settled.
  - Switch one file to JSON and another to Excel, and switch off two columns. The button stays live, because a download switch changes no result (question 1).
  - Press Download into a folder inside OneDrive. Read the amber question, then choose another folder.
  - Read the receipt and check the folder has exactly those files, each starting `PRACTICE_`. Open `Unique_Clients` and `Manual_Review_Needed`.
- [ ] 10. Download again to the same folder and read the replace question. Open one downloaded Excel file, leave it open, and download with replace. That file's row says it is open in another program.
- [ ] 11. Resize under 1360 pixels wide on each of the four stages and press Tab through each. Nothing scrolls sideways and every control shows an outline.

## Screens

Committed in `docs/milestones/screens/M12/`, each at 1440 and 1280:
- `m12-06-run-before`, `m12-06-run-running` and `m12-06-run-after`
- `m12-07-review-before`, `m12-07-review-after` (step 1), `m12-07-review-step2` (with a record open) and `m12-07-review-accept`
- `m12-08-summary-before`, `m12-08-summary-after` and `m12-08-summary-pairs`
- `m12-09-export-before` and `m12-09-export-after`

Differences from boards C3 to C6:
- **No Reject and no set-a-field.** Reviewers can't type values (H6, H7, Q7).
- **Fix problems has a Location tab, counted and set-aside views, and a tab for rows to look at.** The boards show one list.
- **Results adds the pair list, the joins list and the printable page drawer.**
- **Fix problems has no ledger section of its own,** as the milestone says.
- **The accept dialog frame is drawn by the screens tool.** A dialog is its own window, so the tool paints it centered over a dimmed frame.

## Not done

- One bar per file during Download (question 9).
