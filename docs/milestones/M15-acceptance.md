# M15: Docs, help, acceptance and performance

## Goal

Close the rewrite. Every sentence a person reads, in the app and in the docs, comes from or is checked against the code. The five example files go through all nine stages by both routes and give the same exports. The 19,000-row set runs inside the budgets of SPEC 15 on Joe's machine. Every High and Medium audit finding has a passing test, every hard rule has its tests, and every feature in the ledger has a home. After this merge there is nothing left on the list except what Joe chooses to change.

## Spec sections

13.5, 15, 12.5, 13.3, 13.4, 13.2, 7.3 (both balances), 9.1 and 9.3 (the file list and the printed page, for the guide), 11.8 (the guide's "what happens to your data" text), P-GEO-4 (practice runs and the reference folder), 17 (Q3), 18 (glossary). Audit A-25 and any finding still open when this milestone starts. Hard rules H11 and H16 for every document.

## Depends on

All of M00 to M14. M13 (calibration, the saved crosswalk and the secret backup) merges before this milestone, as the README orders them, so its guide section, help entries, feature rows and claim rows are covered here too. Read the `Questions for Joe` and `Not done` sections of every earlier report first, and the merged versions of `tests/audit/INDEX.md`, `tests/HARD_RULES.md` and `tests/ui/test_feature_ledger.py`. M14 supplies the installer, the Windows workflow and `docs/IT_TRUST.md`.

## Branch

`build/m15-acceptance`

## Read first

- `SPEC.md` 13.2 to 13.5, 15, 12.5, 11.8, 17, 18, and `docs/milestones/README.md`.
- `docs/audit/A-claims.md` A-25 (line 314), and `docs/audit/AUDIT.md` for the counts of High and Medium findings.
- `docs/research/offline-enforcement.md` Open risks (line 1058). SPEC 12.5 says the README carries them as written there.
- The earlier reports, `tests/audit/INDEX.md`, `tests/HARD_RULES.md`, `tests/ui/test_feature_ledger.py`, `wholecount/copy/` and the sample data under `wholecount/sample_data/`.
- Legacy references only. `legacy/docs/USER_GUIDE.md` (for topics, not wording), `legacy/docs/TECHNICAL.md` (the source of A-25), `legacy/tools/make_sample_data.py`, `legacy/proof/Proof_Workbook.xlsx`.
- `docs/context/docs/crosswalk-described-for-an-ai.md` for the plain meaning of each rule when you write the guide.

## What to build

### 0. Take stock before writing anything

Run these three checks first and put the lists at the top of the report. Fix what is left, or say why a Low item stays.

- Rows in `tests/audit/INDEX.md` that are not `done`.
- Rows in `tests/HARD_RULES.md` that are not `done`.
- Rows in the three feature tables (M10, M11, M12) and in the decisions doc that have no test in `test_feature_ledger.py`.

### 1. Help and the user guide, generated from the copy registry

- Complete the help entries. `help.stage.<stage_id>` for all nine stages, each with `title`, `purpose` and `how`. `help.el.<name>` for every element that has a `HelpButton` (confidence, same-person matches, program groups, moved points and small counts, record keys, the two balances, counted but not mapped, set aside and its reasons, reviewer names and the second sign-off, and each other one M10 to M12 placed). One `how` is at most three sentences in plain words. Write them from the code's real behavior and the rules, then give each factual sentence a claim ID and a test (H11).
- The guide is built from the registry by one function, `wholecount/copy/guide.py: build_guide() -> Guide`, a list of sections with text. Two writers use it. `wholecount/ui/widgets/guide.py` draws it in the app, and `tools/make_docs.py` writes `docs/USER_GUIDE.md`. The app and the file cannot differ because nothing else writes either.
- Sections, in this order.
  1. What Wholecount does, with the two counts in plain words.
  2. Before you start. What to gather, the file types it reads, Geosupport or a reference file, how many files a batch usually is.
  3. The nine stages, in order. For each, the help text, the data line (Reads, Changes, Writes), what you will decide, what a held button means on that stage, and a screen image (the guide file only, from `make screens`). Fix problems also covers the reviewer name, the three tabs, the bulk accept checks and the second sign-off.
  4. Reading the results. Ranges, when a number is final, High, Medium and Low, Certain, Likely and Possible, why green is never confidence, and the two balances (rows received = counted + not counted yet + set aside, and counted = mapped + counted but not mapped). A person with no usable address is counted and is not on the map.
  5. The output files, nine by default, ten with Map_Points, and seven in a practice run (no map files, SPEC 9.1), each with its columns in plain words, the three formats, who each audit log is for, the PRACTICE marking, and the warning for synced and network folders.
  6. What happens to your data, from the `Your data` page text and its Never list. The install secret and, if M13 has merged, the saved crosswalk appear here as files and options in plain words.
  7. Words used, from SPEC 18, stored as `glossary.*` entries.
  8. If something goes wrong. Error codes, held buttons, a file that will not read, no Geosupport, the Windows firewall note.
  9. What you should see with the example data. The table counts, Goal 1, Goal 2 and both balances for the five example files, read from `wholecount/sample_data/EXPECTED.json` so a test can prove them (below). It says the example run is marked PRACTICE and writes no map files.
- `GuideDialog` is a modal 920 by 700 dialog with a contents list on the left and a read-only `QTextBrowser` on the right. Links inside the guide jump to anchors, and `setOpenLinks(False)` and `setOpenExternalLinks(False)` are set, so nothing can open outside the app. Open it from a quiet `Open the user guide` link at the bottom of the `Your data` drawer (M10) and from F1. Escape closes it. It has no screenshots, because the images belong to the file.
- `make docs` regenerates `docs/USER_GUIDE.md` and `docs/guide/img/` (a copy step over `make screens` output at 1440 wide). `make docs-check` fails when the committed files differ from what the generator writes. Add it to `ci.yml`.

### 2. README and the doc reference check (A-25)

- `README.md` at the repository root, in this order. What Wholecount is, in three sentences. Install (the installer, and `docs/IT_TRUST.md` for IT). Run from source (the commands of `CLAUDE.md`). Build and release (`make bundle`, `tools\release.ps1`, `docs/SIGNING.md`). Tests (`make test`, `make offline`, `make copy`, `make screens`, `make perf`, `make docs-check`). Where things are, as a table of paths and one line each. The guarantees, as a table of guarantee, layer, and the test file that proves it (the five layers of SPEC 12.1 and the no-AI rule). Licenses (`licenses/` and the Qt notice).
- **What cannot be guaranteed.** This section holds the four sentences of SPEC 12.5 as written there, then the other open risks of the research in plain words, each in one or two sentences. Native code is outside the audit hook. The Geosupport DLL's own behavior is unknown until its import table has been read (say what Joe's check found). Hash pins prove the same bytes as before, not safe bytes. A deny list of AI package names is incomplete, so the exact allowed list is the real control, and "no AI" says nothing about how the code was written. Say what the Windows CI and Sandbox runs have now shown and what they have not.
- `tools/check_doc_refs.py` and `tests/audit/test_A25_doc_refs.py`. The checker reads `README.md` and `docs/*.md` (not the subfolders `milestones`, `audit`, `research`, `context` and `planning`, which are other people's records). It finds every backticked reference and checks it against the repository: a path with a known extension or a slash exists, `make <target>` is a target in the `Makefile`, `python -m <module>` is a module, a dotted name under `wholecount.` is a function, class or module found by parsing the source with `ast` (importing could run code), and an image link points at a file. References in angle brackets or braces, Windows paths with `%` and commands of other programs are skipped. The negative control is a temp document naming a script that is not there and a function that is not there, the two kinds of miss in A-25.

### 3. REFERENCE_DATA.md (SPEC 17, Q3)

`docs/REFERENCE_DATA.md`, for the operator and for IT. Read each source page with WebFetch and write what it says. Anything you cannot read is marked **Unconfirmed**. It covers four things.

- **Geosupport Desktop Edition.** What it is, who publishes it, where to download it (name the page and publisher, and give the address only after reading it), that the client installs it, that `GEOFILES` and the standard install path are searched, and how the release shows in the top bar and the audit. Say what the installer's Geosupport page means.
- **An address reference file.** Without Geosupport, addresses are placed only by exact match against a file the operator adds. None is bundled. Name NYC's address points dataset, where to get it, the columns M05's `ReferenceBackend.from_path` reads (`house_number`, `street`, `zip`, `borough`, `latitude`, `longitude`, with the accepted aliases it lists), and the step to rename headers in Excel if the download uses other names. Say plainly that near matches are only suggestions and never get coordinates.
- **Where the file goes.** SPEC P-GEO-4 and M05 settle it, so this milestone builds no code for it. Wholecount reads the one `.csv` in `%LOCALAPPDATA%\Wholecount\reference\`. Two files there mean none is used, and the document says what the system check then shows. The repo's sample file is refused for a batch of the operator's own files, even when copied there, and the document says so. The operator makes the folder, because Wholecount writes nothing until asked (H9). M10's system check already shows the file name and row count, and M05 tests the cases. A doc test makes the folder path in the document equal the path constant in the source.
- **Bundled data.** The ZIP table and district files, their sources and dates (from M05's `SOURCE.txt`), and how to rebuild them (`tools/make_district_files.py`, `tools/make_zip_table.py`).

### 4. Acceptance (SPEC 13.5, `tests/acceptance/`)

- The expected numbers are in `wholecount/sample_data/EXPECTED.json`, written by M01's `tools/make_example_data.py` from its plan (P-GEO-4a). There's no second copy under `tests/`. The acceptance tests read its `files`, `counts`, `decisions`, `locations` and `outputs` sections. `locations` holds the split (mapped high, mapped low, counted but not mapped with its five reasons) for a practice run with the sample reference and for a run with no backend. Goals and the first balance must not depend on the backend (P-VAL-2), and a test checks that.
- If a number here disagrees with a run, find out why. Fix the code if it's wrong. If the plan is wrong, change it in the script, regenerate, and list the change in the report. Never edit `EXPECTED.json` by hand, and never take a number from a run you didn't look at.
- A small helper, `tests/acceptance/drive.py`, runs a batch through the same session calls the stages use, with a fixed clock and a fixed reviewer name, on the five example files in `wholecount/sample_data/`. It runs with the sample reference (a practice run) by default, or with no backend. It has two routes.
  - `fast_path(files)` does what Add your files' fast path does. When the fast path stops at Programs, it confirms or splits the groups as the `decisions` section of `EXPECTED.json` says and runs again.
  - `by_stage(files)` makes every call in stage order, confirming each stage as a person would.
  - Both routes take the same decisions from `decisions` (program groups, copy groups, same-ID conflicts and pairs), each at the point its route asks for it.
- `test_sample_both_routes.py` (SPEC 13.5). Both routes download to temp folders. Every file except the two audit logs must be byte-identical. Each audit log, the internal and the shareable, must be identical once timestamps and the route-only events are removed. The route-only event codes are listed in the test with a reason each, such as the confirmations a person makes stage by stage. If any other line differs, the test fails and names the line's event code. The report lists the codes.
- `test_practice_run.py` (P-GEO-4). The example data runs by both routes with the sample reference. Every file name starts `PRACTICE_`, every data file's first column is `PRACTICE`, both logs open with the practice line, no map file or district column is written, and the printed page opens with the practice line. A batch of the operator's own files refuses the sample reference. The numbers in the guide's example section equal this run.
- `test_ui_walkthrough.py`. One pytest-qt test builds the real window offscreen and drives the nine stages through their own widgets (the same buttons a person presses), with file dialogs stubbed to fixed paths and the reviewer prompt answered with the fixed name. It ends with a receipt whose files match the session route's. It proves the stage bodies, the bridge and the engine agree.
- `test_independent_counts.py`. Reads only the downloaded files with pandas and imports nothing from `wholecount`. It checks that the three row files add up (clean rows, plus review rows marked Counted No, plus set-aside rows, equal rows received, C-15), that counted equals mapped plus counted but not mapped in `Data_Quality_Report.csv`, that the rows of `Unique_Clients` equal the high end of Goal 1 on Results, and Goal 1 itself when no pair or copy group is open, that the (`Source_File`, `Source_Row`) pairs inside `Unique_Clients`' `Source_Records` (each `letter :: Source_File :: Source_Row`, with the letter dropped) are exactly the (`Source_File`, `Source_Row`) pairs of `Final_Clean_Mapped` with none twice, that the distinct (master ID, program) rows equal Goal 2, that each program name in `Unique_Clients_By_Program` appears among its records' programs, and that the three row files add up to rows received. It also holds a 40-line pandas implementation of the two automatic join reasons of P-ID-3 that apply with the saved crosswalk off (same Client ID inside one system with the facts agreeing, and the four exact facts) over `Final_Clean_Mapped`. `Final_Clean_Mapped` has no system column, so the test reads each file's system from the `files` section of `EXPECTED.json`, which is plain JSON and imports nothing. The number of people it finds equals the high end of the Goal 1 range. With every open pair and copy group decided as different, Goal 1 equals it exactly.
- `test_determinism.py`. Two runs of the same inputs in a different file order give identical data files (C-27) and identical counts.
- `tools/make_large_set.py --seed 20261030 --rows 19000 --files 15 --out DIR` writes the 19,000-row set. It is deterministic. Fifteen files across CSV, TSV, XLSX, JSON and XML, with a mix of source systems, programs spelled several ways, nicknames, swapped birth-date digits, copies inside files, a few headers in odd places, and addresses on real NYC street names with plausible house numbers so Geosupport can place most of them. It also writes `truth.json` with counts only (people planted, programs, copies). Names come from lists in the script, never from real people. `tests/acceptance/test_large_set.py` runs it on the fake geocoder and checks the balance, determinism, that Goal 1 falls between the planted people and the planted people plus the planted ambiguous pairs, and that no run step reports a negative or missing count.

### 5. Performance (SPEC 15)

- `tests/perf/budgets.toml` holds the table of SPEC 15 as numbers. Seven rows: start to first screen 3000 ms, add 15 files 10000 ms, process with Geosupport 90000 ms, redraw of any click that starts no job 200 ms, preview the counts 10000 ms, download all output files 10000 ms, memory 1536 MB.
- `python -m wholecount.dev perf --set DIR` runs the 19,000-row set through the real calls. It adds the files, includes and maps, runs Process with whatever backend exists, previews the counts, downloads the default files to a temp folder it removes, switches through all nine stages three times and keeps the slowest redraw, and reads the peak memory. On Windows memory comes from `K32GetProcessMemoryInfo` in `kernel32` (already on the guard's list), and on Linux from `resource.getrusage`. Output goes through the counts-only printer with integer labels (`add_files_ms`, `process_ms`, `preview_ms`, `download_ms`, `redraw_max_ms`, `peak_memory_mb`, `rows`, `files`). It also prints the backend as a fixed word (`geosupport`, `reference`, `none`, `fake`).
- `tools/perf/measure_startup.ps1` starts the installed `Wholecount.exe`, waits for its main window, and prints the elapsed milliseconds. It runs five times and prints the median. It starts a process, so it is a Windows script for Joe, never part of the app.
- `tools/perf_report.py` compares an output with `budgets.toml` and writes `perf-report.txt` as a plain table of budget, measured, and `ok` or `over`. A run on the fake geocoder is labeled as such and is never accepted as the Geosupport row.
- `make perf` runs the dev command and the report. In `ci.yml` a non-blocking job runs it on the fake geocoder and compares with `tests/perf/baseline.json`. It writes a job summary and a warning annotation when any step is more than 1.5 times its baseline. It never fails the run (SPEC 15 says regression alarm, not pass or fail).
- When a real number is over budget, run `cProfile` on the fake-geocoder run, list the five slowest functions in the report, and fix them if the fix is local and safe. Do not change a budget, and do not skip a rule to go faster (H3, H4). If it cannot be fixed here, the report says which budget is over, by how much, and what the profile points at.
- After Joe runs `make perf` and the startup script on his machine with Geosupport installed, he pastes both outputs on the pull request. Record them in `docs/PERFORMANCE.md` in a follow-up commit on the same branch before merge: his Windows build, CPU, memory, Geosupport release, each measured value against its budget. Leave the Geosupport rows `not yet measured` until then. The Linux numbers go in a separate table with their label.

### 6. Final ledgers

- `tests/ui/feature_ledger.toml` joins the three tables from M10, M11 and M12 with the decisions doc's feature ledger, the build brief and `legacy/tests/test_parity.py`. One row per feature with `stage`, `widget` (an `objectName` found in the built stage), `source`, and `status` (`built` or `dropped`). A dropped row names the SPEC section or hard rule that drops it. `test_feature_ledger_complete.py` builds each stage with a populated `FrameView`, finds each widget, and checks that every row of the decisions doc's "Kept and drawn" list is present. A missing feature fails.
- `tests/audit/test_index_final.py`. Every High and Medium ID in `docs/audit/*.md` is in `INDEX.md` with status `done` and a test file that exists and is collected by `pytest --collect-only`. The count of High and Medium rows equals the count in the audit files. Every Low row is `done` or has a reason of at least a sentence. A `done` row whose test is skipped or xfail on Linux and Windows fails. Print the counts in the report.
- `tests/invariants/test_hard_rules_final.py`. All sixteen rows of `HARD_RULES.md` are `done` with at least one test each, wherever it lives (SPEC 13.2), every module named exists, and each is collected.
- `make docs-check` and the doc reference check run in `ci.yml`.

### 7. The last report

`M15-REPORT.md` follows the README format and adds three things at the top of `What was built`.

- The stock-take lists from section 0, with what closed each item.
- A table of the audit index by severity and status, and of the hard rules by status, copied from the final run of the two tests.
- The performance table (Linux fake-geocoder numbers, and Joe's numbers once he pastes them), and the profile of any row that is over.

It also lists the questions earlier reports left open that are still open, so Joe sees every decision still waiting for him in one place.

## Tests to write

Write each failing test first. Each doc check has a negative control that feeds it a bad input and asserts it is caught.

- **Help.** `tests/ui/test_help_complete.py`. A static scan finds every `HelpButton("id")` in `wholecount/ui`. Each id has `title`, `purpose` and `how` in the registry, no `help.*` entry is unused, every stage has `help.stage.<id>`, and each `how` is three sentences or fewer.
- **Guide.** `tests/ui/test_guide.py`. `build_guide()` has the nine sections in order and nine stage subsections in `STAGES` order. `docs/USER_GUIDE.md` equals what `tools/make_docs.py` writes now. The app's guide and the file have the same headings. `GuideDialog` has links off and no `http` in its text, Escape closes it, and F1 and the `Your data` link both open it. The guide text has no em dash, emoji, exclamation mark or British spelling (`tests/copy` lint scope now covers `README.md`, `docs/USER_GUIDE.md`, `docs/REFERENCE_DATA.md`, `docs/IT_TRUST.md` and `docs/SIGNING.md`).
- **Guide claims.** `tests/acceptance/test_guide_example_numbers.py` (claim `CL-GUIDE-EXAMPLE-01`). The numbers in the guide's example section, both balances included, equal the counts of the practice run of the example files and the `counts` section of `wholecount/sample_data/EXPECTED.json`. Change one number in a temp copy and the test fails.
- **New copy claims.** `tests/acceptance/test_claims_v11.py` walks the claim registry and checks that each claim added by M10 to M12 for version 1.1 has a test that drives the behavior and not the string. The names below are those in M10 and M12, and the real ones win where M09 registered a sentence first: `CL-TRUST-SAVED-01`, `CL-PRACTICE-01`, `CL-BALANCE-LOC-01`, `CL-NOADDR-COUNTED-01`, `CL-LOC-COUNTS-01`, `CL-REVIEWER-LOGGED-01`, `CL-NOTE-INTERNAL-01`, `CL-UNMATCHED-SCREEN-01`, `CL-COORDS-INTERNAL-01`, `CL-SMALLCELL-01` and `CL-RUN-MAPS-01`. A claim whose test only reads the text fails, and so does a registry claim with no test.
- **README.** `tests/unit/test_readme.py`. The four sentences of SPEC 12.5 appear as written. Every test file named in the guarantees table exists. Each guarantee row names a layer of SPEC 12.1.
- **A-25.** `tests/audit/test_A25_doc_refs.py`. The checker passes on the real docs and fails on a temp doc with a missing script name and a missing function name. It does not import any module it checks.
- **Reference file.** `tests/unit/test_reference_doc.py`. The folder path in `docs/REFERENCE_DATA.md` equals the source constant, the document names the aliases M05 accepts, and it says the sample file is refused. A negative control changes the path in a temp copy.
- **Acceptance.** The test files in section 4, each seen to fail first (for example by changing a program group between routes, and by deleting a row from one export).
- **Final ledgers.** The three tests in section 6, each with a negative control on a copy of the ledger, the index and the hard rules file.
- **Perf.** `tests/perf/test_perf_harness.py` runs the dev command on a 600-row set and checks it prints only the fixed labels with integer values, never a string value, and that the report marks a fake-geocoder run as such. `tests/perf/test_budgets.py` checks the seven rows of `budgets.toml` equal the table in SPEC 15 by parsing the spec.
- **Regressions from earlier milestones.** Re-run the whole suite on Windows through the workflow. Any test that was skipped on Linux only because a Windows part was missing now runs there.

## Done when

- [ ] `make test`, `make offline`, `make copy` and `make docs-check` are green on Linux, and the Windows workflow is green with no unexpected skips. Counts are in the report.
- [ ] Both routes through the example files give the same exports, as section 4 states, and the independent pandas check agrees with Results.
- [ ] The 19,000-row set runs on the fake geocoder in CI inside the alarm, and `make perf` has been run on Joe's machine with Geosupport. `docs/PERFORMANCE.md` has his numbers against every budget, or the report says which are over and what the profile shows.
- [ ] `tests/audit/INDEX.md` has no High or Medium row that is not `done`, and the report prints the High, Medium and Low counts. `tests/HARD_RULES.md` has sixteen `done` rows.
- [ ] `README.md`, `docs/USER_GUIDE.md` and `docs/REFERENCE_DATA.md` exist, the README has the SPEC 12.5 sentences, and A-25 has a passing test and a `done` line.
- [ ] `make screens` is committed under `docs/milestones/screens/M15/` for the guide images, and `docs/guide/img/` is regenerated.
- [ ] The report lists the route-only audit event codes, every spec difference, every question for Joe, and anything left, with the reason. It says whether M13 had merged and what it added to the guide.
- [ ] `docs/milestones/M15-REPORT.md` is written, the branch is pushed, the pull request is open, and work has stopped.

## Windows checks for Joe

Use the final installer from the pull request's workflow run, and the CI certificate steps from M14 (trust the `.cer`, and remove it afterward). The performance steps need Geosupport Desktop Edition installed, which your machine has.

1. Install the final installer. Start Wholecount from the Start menu, open `What happens to your data` in the ledger footer, and press `Open the user guide`. Read the contents list, then sections 1, 3 and 9. Press F1 on a different stage and confirm it opens at the same guide.
2. On each stage press the `?` button and compare the popover with the guide. The wording should match.
3. Run the example data by the fast path. The top bar shows PRACTICE. Compare Goal 1, Goal 2 and both balances with section 9 of the guide. Download, and check there are seven files and every file name starts `PRACTICE_`. Press Start over, then run it again stage by stage, confirming each stage. Compare again. The numbers and the downloaded files should match the first run. If you have a way to compare files, compare them (`fc /b` in Command Prompt).
4. Open `README.md` on the repository page or in Notepad. Read What cannot be guaranteed. Tell Claude Code anything that is unclear or that you disagree with.
5. Open `docs\REFERENCE_DATA.md`. Follow the Geosupport section on your machine and check that each statement is true there. Then make the folder `%LOCALAPPDATA%\Wholecount\reference\`, download NYC's address points file as the page says, rename its headers if the page tells you to, and put it in the folder. Open the system check line in the ledger footer and confirm it names the file and shows a row count. If the dataset needs steps the page does not describe, say so.
6. Performance. In the repository folder, with the venv active: `python tools\make_large_set.py --seed 20261030 --rows 19000 --files 15 --out C:\WholecountPerf`, then `python -m wholecount.dev perf --set C:\WholecountPerf --report perf-report.txt`. It takes a few minutes. Then `powershell -File tools\perf\measure_startup.ps1`. Copy both outputs into a comment on the pull request. Close other programs first, and do not touch the machine while it runs.
7. Repeat the Windows Sandbox check from M14 with the final installer, and press through the example data to Download.
8. Resize the window to 1280, 1366, 1440 and as wide as the screen allows, on any three stages. Nothing scrolls sideways.
9. Last, read the report's `Questions for Joe`, answer each one on the pull request, and merge when you are satisfied.

## Out of scope

- New features, new rules, new screens, and any change to a budget or a hard rule. If a number is over budget, the report says so and Joe decides.
- Moving to Azure Artifact Signing, auto-update, other platforms and other languages.
- Rebuilding the legacy slide deck, video script and cheat sheets. Only the user guide replaces `legacy/docs`.
- Recording audio or screenshots of the real data. Guide images come from `make screens` on the example data.
- Editing `SPEC.md`, `CLAUDE.md` or `docs/milestones/README.md`. If one is wrong, put the question at the top of the report.
