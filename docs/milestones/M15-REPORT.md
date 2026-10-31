# M15 report

## Questions for Joe

New in M15:

1. **One decision takes about 9 s on 19,000 rows, and the budget for a click is 200 ms.** I fixed what was local (see Performance below), which took it from about 33 s. What's left is identity, programs and the counts re-running over the whole batch on the main thread, so the window waits. Getting under 200 ms needs identity to rerun only the people a decision touches, or each decision to run as a job with its own progress line. Both change how decisions flow, so I didn't do either. Which do you want, or do you accept the wait for batches this size?
2. **The Download stage takes about 3.5 s to draw on 19,000 rows** (budget 200 ms), because it builds the export plan to show each file's rows. It's built once per change now, not twice per visit. A cheaper count would mean a second path to the row numbers beside the writer's, which I didn't want. Is the wait acceptable on that one stage?
3. **Two runs with files added in a different order give the same rows in the same order, but not byte-identical files.** SPEC 4.3 gives each file a letter in the order it was added, and SPEC 9.1 prints that letter in Source_Letter, the quality report's Table column and Source_Records. So those cells differ. `tests/acceptance/test_determinism.py` removes the letters and then requires every file to be identical; Final_Clean_Mapped and Set_Aside_Records, which have no letter, are byte-identical. This is M09 question 7 again. If C-27 should mean byte-identical, letters would have to follow file names, not add order, which changes SPEC 4.3.
4. **Your Windows check 3 says seven files.** A practice run writes eight (M09 question 1), and the guide says eight because it counts them from the writer.
5. **The NYC pages couldn't be read from this session.** `www.nyc.gov` and `data.cityofnewyork.us` aren't in its allowed network list. So `docs/REFERENCE_DATA.md` marks the Geosupport page, the address points dataset's title, address and column names **Unconfirmed**, and gives no web addresses. Your Windows check 5 is where those get confirmed. If you allow those two hosts in the environment's network settings, I can read the pages and fill them in.
6. **Two bugs found by the acceptance tests, both fixed.** The Download button's job never committed the saved crosswalk (only the session's `download()` did), and opening Show data on any table with a header warning crashed on a missing copy entry. Details under What was built.

Still open from earlier reports, all in one place:

- **M14.** Q1 the publisher name on the signature (now "Joe Buzzetta"), Q2 per-machine installs only, Q3 the Windows job's cost, Q4 please start the Windows workflow once. It hasn't run yet, so nothing Windows-only has been seen to pass.
- **M13 Q10.** Is a batch's ID built from file contents or file names?
- **M12.** Q1 (download settings no longer make results stale), Q9 (no per-file bars during Download), Q15 (the top bar says "Addresses will not be placed" during a practice run).
- **M11.** Q1 the calculated ZIP step gets no lookup during Process, Q2 Process's fast-path check never sees an SSN-shaped Client ID, Q3 date order and the two-digit rule apply only to Date_of_Birth.
- **M09.** Q1 eight practice files, not seven. Q7 letters follow add order (question 3 above).
- **M07 Q1.** Spellings that differ only by case are proposals you confirm.
- **M05.** Q1 how to read your Geosupport release, Q2 the district files weren't built (no files ship).
- **M04 Q1.** NJ and CT on proof sheet 08: the milestone and the spec disagree, and I followed the spec.
- **M03 Q1.** The NYC ZIP table comes from a copy of NYC Health's list.
- **M00 Q1.** Files on a network share can't be opened in Excel.

## What was built

### Stock-take (section 0), and what closed each item

- **Audit index rows not `done`:** one, A-25 (Low). Closed by `tools/check_doc_refs.py` and `tests/audit/test_A25_doc_refs.py`.
- **Hard rules not `done`:** twelve rows were `partial` and H14 read "arrives in M10". All sixteen are `done` now, with the tests M10 to M14 added named in `tests/HARD_RULES.md`.
- **Features with no ledger test:** the decisions doc's "Moved, not drawn yet", "Stages not drawn yet" and "Needs a home" items, and M13 and M14's additions, had no row. `tests/ui/feature_ledger.toml` now has 116 rows, and `tests/ui/test_feature_ledger_complete.py` finds every built one in the window.

### Final tables, from the last run of the two tests

| Severity | done | pending |
| --- | --- | --- |
| High | 44 | 0 |
| Medium | 40 | 0 |
| Low | 17 | 0 |

| Hard rules | done |
| --- | --- |
| H1 to H16 | 16 of 16 |

### Performance (SPEC 15)

Linux, fake geocoder, 19,000 rows in 15 files. Your Windows numbers go in `docs/PERFORMANCE.md` once you paste them.

| Action | Budget | Measured | Status |
| --- | --- | --- | --- |
| Start to first screen | 3,000 ms | needs Windows | not measured |
| Add 15 files | 10,000 ms | 3,135 ms | ok |
| Process | 90,000 ms | 31,573 ms | not accepted (fake geocoder) |
| Slowest stage switch | 200 ms | 3,534 ms | over |
| One decision | 200 ms | 9,141 ms | over |
| Preview the counts | 10,000 ms | 8,653 ms | ok |
| Download | 10,000 ms | 3,155 ms | ok |
| Peak memory | 1,536 MB | 411 MB | ok |

The first full run had the Download stage at 27.7 s, Download at 12.5 s and a decision at about 33 s. Four fixes, each tested to give the same results:

- `engine/confidence.py: master_match_confidences` works out every person's match confidence in one pass. The old per-person rule scanned every proposal and record for each person.
- `session/pages.py: export_plan` is reused while the results, the download settings, the log and the reviewer are the same.
- `session/runner.py` reuses tidying, matching, standardizing, placing and the copy search when a decision re-runs the batch, the way loading was already reused. Process always runs every step.
- `engine/names.py` keeps recent answers of its pure name helpers in a bounded in-memory cache.

The five slowest functions in one decision now: `identity.resolve` (8.2 s, 3.2 s in its own loop), `pipeline.copy_row` (2.3 s), `identity.score_pair` (2.1 s), `pipeline.person_row` (1.3 s), `addresskey.address_key` (1.0 s), all under the profiler.

### By section

- **1. Help and the guide.** Help entries for all nine stages and every `HelpButton`, each with claim tests. `wholecount/copy/guide.py: build_guide()` builds the guide from the registry. `GuideDialog` draws it in the app (F1 and the Your data link), with links off. `tools/make_docs.py` writes `docs/USER_GUIDE.md` and its nine images, and `make docs-check` fails when they're out of date. M13 had merged, so the guide covers calibration, the saved crosswalk and the key backup.
- **2. README and A-25.** `README.md` in the milestone's order, with the guarantees table and the four SPEC 12.5 sentences, then the research's other open risks in plain words. `tools/check_doc_refs.py` checks every file, make target, module and `wholecount.` name the docs cite, by parsing, never importing. `make docs-check` runs it.
- **3. Reference data.** `docs/REFERENCE_DATA.md`: Geosupport, the reference file and its accepted headers, where it goes, and the bundled ZIP table and district files. The NYC pages are Unconfirmed (question 5).
- **4. Acceptance.** `tests/acceptance/drive.py` runs the example batch by the fast path or stage by stage through the same session calls and jobs the stages use. Both routes download byte-identical data files. The audit logs match once timestamps and these route-only events are removed:
  - `SETUP_CHANGE` with `prepare_confirmed`: Tidy up's Continue, which the fast path skips
  - `SETUP_CHANGE` with `table_confirmed`: Match your columns' Confirm, once per table
  
  The UI walkthrough presses each stage's own buttons in the real window and downloads the same data files. The independent check reads the files with pandas only. The large set runs 19,000 rows on the fake geocoder.
- **5. Performance.** `tests/perf/budgets.toml`, `python -m wholecount.dev perf --set DIR [--fake] [--report PATH]`, `tools/perf_report.py`, `tools/perf/measure_startup.ps1`, `make perf`, a CI job that can't fail the run, `tests/perf/baseline.json` and `docs/PERFORMANCE.md`.
- **6. Final ledgers.** The feature ledger, `tests/audit/test_index_final.py`, `tests/invariants/test_hard_rules_final.py` and `tests/acceptance/test_claims_v11.py`.

### Fixes the acceptance tests found

- **The Download button never committed the saved crosswalk.** Its job wrote the files and logged them, but only the session's `download()` ran the commit. Both routes now end in `session/frame.py: log_download`, which commits and adds the "crosswalk wasn't updated" note when the commit rolls back. Test: `tests/ui/test_download_job_crosswalk.py`.
- **Show data crashed on any header warning.** The copy had three reasons whose codes the engine never gives. All seven engine codes have a sentence now. Test: `tests/ui/test_header_reasons.py`.
- **The guide called a setter the offline scan forbids** (`setOpenExternalLinks(False)`), which was already off by default. Removed.

### Spec differences and conservative readings

- **EXPECTED.json records each file's source system.** The independent check needs it, because Final_Clean_Mapped has no system column. Added in `tools/make_example_data.py` and regenerated; nothing else in the file changed.
- **The independent check keeps open copy groups apart.** SPEC 7.2's high end treats them as different people, so the pandas side doesn't join two members of an open copy group. With everything decided as different, the two agree exactly.
- **Finish review stays held in the acceptance runs.** The plan leaves 15 rows not counted yet, so Finish review is held by design, and Download doesn't need it.
- **The feature ledger uses `code:` paths** for parts that only exist once opened (dialogs, the queue, the record panel), and objectNames for the rest.

## Tests

- `make test`: 4,374 passed and 11 skipped, in 13 min 37 s. The skips are the bundle tests, which need a built folder (CI builds it and runs them with WHOLECOUNT_REQUIRE_BUNDLE), and four Windows-only PE checks.
- `make offline`: 72 passed.
- `make copy`: 1,843 passed.
- `make docs-check`: the guide is current and 0 doc references are missing.

New test files: `tests/acceptance/` (`drive.py`, `conftest.py`, `test_sample_both_routes.py`, `test_practice_run.py`, `test_independent_counts.py`, `test_determinism.py`, `test_ui_walkthrough.py`, `test_large_set.py`, `test_claims_v11.py`, `test_guide_example_numbers.py`), `tests/perf/test_budgets.py`, `tests/perf/test_perf_harness.py`, `tests/audit/test_A25_doc_refs.py`, `tests/audit/test_index_final.py`, `tests/invariants/test_hard_rules_final.py`, `tests/ui/test_feature_ledger_complete.py`, `tests/ui/test_help_complete.py`, `tests/ui/test_guide.py`, `tests/ui/test_download_job_crosswalk.py`, `tests/ui/test_header_reasons.py`, `tests/copy/test_help_claims.py`, `tests/copy/test_guide_claims.py`, `tests/unit/test_readme.py`, `tests/unit/test_reference_doc.py`, `tests/unit/test_recompute_reuse.py`, `tests/unit/test_master_confidences.py`, `tests/unit/test_export_plan_reuse.py`.

Audit IDs closed: A-25, `tests/audit/test_A25_doc_refs.py`.

## Done list

- [x] `make test`, `make offline`, `make copy` and `make docs-check` are green on Linux. **The Windows workflow hasn't run** (M14 question 4), so "green with no unexpected skips" on Windows is open.
- [x] Both routes give the same exports as section 4 states, and the independent pandas check agrees with Results.
- [ ] The 19,000-row set runs on the fake geocoder in CI inside the alarm: yes, once CI runs the new job. `make perf` on your machine with Geosupport is open, and two budgets are over on Linux (questions 1 and 2).
- [x] `tests/audit/INDEX.md` has no High or Medium row that isn't `done`: High 44, Medium 40, Low 17, all done. `tests/HARD_RULES.md` has sixteen `done` rows.
- [x] `README.md`, `docs/USER_GUIDE.md` and `docs/REFERENCE_DATA.md` exist, the README has the SPEC 12.5 sentences, and A-25 has a passing test and a `done` line.
- [x] `make screens` is committed under `docs/milestones/screens/M15/`, and `docs/guide/img/` is regenerated.
- [x] The report lists the route-only audit event codes, every spec difference, every question for you, and anything left.
- [x] This report is written, the branch is pushed and the pull request is open.

## Windows checks

Copied from the milestone. Use the installer from the pull request's workflow run.

- [ ] 1. Install the final installer. Start Wholecount from the Start menu, open `What happens to your data` in the ledger footer, and press `Open the user guide`. Read the contents list, then sections 1, 3 and 9. Press F1 on a different stage and confirm it opens at the same guide.
- [ ] 2. On each stage press the `?` button and compare the popover with the guide. The wording should match.
- [ ] 3. Run the example data by the fast path. The top bar shows PRACTICE. Compare Goal 1, Goal 2 and both balances with section 9 of the guide. Download, and check every file name starts `PRACTICE_` (there are eight, question 4). Press Start over, then run it again stage by stage, confirming each stage. Compare again. The numbers and the downloaded files should match the first run, apart from the two audit logs (`fc /b` in Command Prompt).
- [ ] 4. Open `README.md`. Read What cannot be guaranteed. Tell me anything that's unclear or that you disagree with.
- [ ] 5. Open `docs\REFERENCE_DATA.md`. Follow the Geosupport section on your machine and check each statement. Then make `%LOCALAPPDATA%\Wholecount\reference\`, download NYC's address points file, rename its headers if needed, and put it in the folder. Open the system check line in the ledger footer and confirm it names the file and shows a row count.
- [ ] 6. Performance. In the repository folder, with the venv active: `python tools\make_large_set.py --seed 20261030 --rows 19000 --files 15 --out C:\WholecountPerf`, then `python -m wholecount.dev perf --set C:\WholecountPerf --report perf-report.txt`. Then `powershell -File tools\perf\measure_startup.ps1`. Paste both outputs on the pull request.
- [ ] 7. Repeat the Windows Sandbox check from M14 with the final installer, and press through the example data to Download.
- [ ] 8. Resize the window to 1280, 1366, 1440 and as wide as the screen allows, on any three stages. Nothing scrolls sideways.
- [ ] 9. Read Questions for Joe, answer each one on the pull request, and merge when you're satisfied.

## Screens

`docs/milestones/screens/M15/` holds the nine frames the guide uses, from `make screens` on the example data, at 1440 and 1280 wide. The guide's images in `docs/guide/img/` are the 1440 copies, and `make docs` regenerated them byte for byte. No stage changed its layout in M15; the stage heads gained their `?` buttons, which are in these frames.

## Not done

- Your Windows numbers in `docs/PERFORMANCE.md`, which need your machine with Geosupport.
- The Windows workflow run and the Sandbox check, which need you to start them.
- The two budgets that are over on Linux (questions 1 and 2).
- The NYC page details in `docs/REFERENCE_DATA.md` (question 5).
