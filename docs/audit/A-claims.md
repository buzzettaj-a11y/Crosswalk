# Agent A: claims audit of Crosswalk (what the product says versus what the code does)

Scope: false or overstated claims in the UI, help text, launcher messages and docs. The old code was not changed. Every runtime proof below ran against a fresh copy of `.../scratchpad/src/Crosswalk` (copies named `src/agentA-*`), driven in process through FastAPI's `TestClient` or by running `launch.py` for real.

How to rerun any proof:

```
cd /tmp/claude-0/-home-claude/ec68250d-d5ac-549e-8d94-20759c381437/scratchpad
. venv-old/bin/activate
rm -rf src/agentA-t3 && cp -r src/Crosswalk src/agentA-t3
python audit/A-scripts/<script>.py $PWD/src/agentA-t3      # a05 and a10 take extra arguments, see the script header
```

Scripts are in `audit/A-scripts/`, fixtures in `audit/A-fixtures/`, saved outputs in `audit/A-out/`. All 10 project test suites pass (1,233 checks), which is why none of the problems below were caught: the tests check the sample files, where names never sit in the wrong column and nothing is split by a blank line.

Count: 25 findings. High 10, Medium 10, Low 5.

Line references are to files under `.../scratchpad/src/Crosswalk/` unless a path says otherwise. "Spec" means `.../scratchpad/pkg/Crosswalk-Project/docs/crosswalk-described-for-an-ai.md`.

---

## High

### A-01. An unmapped SSN or date-of-birth column is written into the review export
- Severity: High
- Claim: `ui/app.js:1102-1103`: "Unmapped columns never enter the output. A date of birth or SSN column left unmapped stays out of every export."
- Reality: The review file (`Manual_Review_Needed.csv`) carries an `orig::<column>` copy of every source column, mapped or not, for every row that lands in review (`app.py:2711`, `base[f"orig::{k}"] = v`). An SSN column the user deliberately left unmapped is exported in full for those rows.
- Proof: `audit/A-scripts/a19_unmapped.py` (fixture `ssn_unmapped.csv`, 3 rows, SSN and Phone columns left unmapped, one row missing its ZIP). Output (`audit/A-out/a19_out.txt`):
  ```
  SSN / Phone mapped to anything? False
  clean              contains unmapped SSN/phone values: []
  review             contains unmapped SSN/phone values: ['219-09-9999', '555-0102']
     header: Source_File,Source_Row,Resolution_Status,Error_Reason,Scenario_Flags,orig::Client_ID,...,orig::SSN,orig::Pho...
  ```
- Rewrite requirement: Decide per column whether an unmapped column may travel with a review row. If the review file needs the original row to be re-uploadable, say so on the Map screen ("unmapped columns are kept in the review file only") or let the user mark a column as "never export". Never claim "every export" unless a test greps every export for an unmapped canary column.

### A-02. The "IDs only, no names, no addresses" audit log echoes raw cell values, including names and addresses
- Severity: High
- Claim: `app.py:1275` (first lines of the downloaded log): "This log references system IDs only. No client names or full street addresses are included." Same promise at `crosswalk_server.py:967` (rail stamp "AUDIT / IDs only, no PII"), `ui/app.js:2244` ("Nothing here is client data."), `ui/app.js:2297` ("No names, no addresses."), `ui/help.json:61` ("never a name, address or value, so it can be read and shared safely"), `app.py:4106`, `README.md:1082`, `docs/TECHNICAL.md:32`, Spec line 26 ("Never a name, address or value").
- Reality: Validation messages quote the offending cell. Whatever sits in the wrong column (a name in State, a name in ZIP, a street in City) is written verbatim into the audit log, the Audit trail screen and the "safe to share" download. Typed text in a date column is quoted too.
- Proof: `audit/A-scripts/a08_audit_leak.py` (fixture `misplaced.csv`, five fictitious rows). Output from `/api/audit/text`:
  ```
  [misplaced.csv :: A1:H6 | ID M003 | src-row 2] [3 Verification | segregated] State is not NY: 'Marigold Thistlewood'
  [misplaced.csv :: A1:H6 | ID M004 | src-row 3] [3 Verification | segregated] Invalid ZIP Code format: Ignatius Wobblesworth
  ```
  The canary session (`audit/A-out/disk/Secure_Audit_Log.txt` lines 65-67) also holds `DOB is not a date that can be read ('not-a-real-date-ZORP')`, `City: fuzzy-matched 'Brookln'->'Brooklyn'` and `Unrecognized City: 'Gotham'`. `a02_grep_canaries.sh` finds 3 canary lines in that log.
- Rewrite requirement: The audit stores identifiers, row numbers, column names and reason codes only. Messages shown to the reviewer may quote a value; the audit copy must not. Add a test that loads a file with a name in State, ZIP and DOB and greps the audit text, the Audit screen and the summary for it.

### A-03. The "counts only, never client records" printable summary carries a Client ID and the source file names
- Severity: High
- Claim: `crosswalk_server.py:2712-2714` (footer of the page): "No client data left this machine. This page contains counts only, never client records, so it is safe to share." Also `ui/app.js:2329-2331`, `ui/help.json:52`, `docs/USER_GUIDE.md:99`, `docs/VIDEO_SCRIPT.md:139`, `docs/cheatsheets/01_the_two_counts.md:7`.
- Reality: The "By source file / Most common problem" column prints `top_issue` as free text (`crosswalk_server.py:2599`). When the most common problem is a Client ID conflict, the message contains the ID (`app.py:2413`). The `Source files:` line (`crosswalk_server.py:2708`) prints raw upload file names, which users often name after a person or a program. The same `top_issue` text goes into `Data_Quality_Report.csv`.
- Proof: `audit/A-scripts/a09_topissue.py` (fixture `idconflict.csv`, two different people sharing the ID `SSN-123-45-6789`). Output:
  ```
  idconflict.csv :: A1:H4,3,1,2,33.3%,Same Client ID 'SSN-123-45-6789' used by records with different data; review required (not merged),True
  printable summary lines mentioning the ID: "Same Client ID 'SSN-123-45-6789' used by records with different data; review required (not merged)"
  ```
  The first line is `Data_Quality_Report.csv`; the second is the text of the printable page. Both carry the ID.
- Rewrite requirement: The shareable page may contain integers and fixed phrases from a closed list (reason codes), never free text built from data. Show source file names only if the user ticks "include file names". A test must grep the page for every ID, name and value in the fixture.

### A-04. Disk-write claims are false: saving to disk starts at the first upload and is on by default
- Severity: High
- Claim: `ui/index.html:22`: "Nothing is being written to disk." (shown while processing). `ui/help.json:36`: "all on this computer, with nothing written to disk." `crosswalk_server.py:2829` (goodbye page): "Nothing else was written to this computer." `START HERE.txt:43-44`: "writes nothing to disk unless you download a file yourself." Spec line 28: "Processing holds everything in memory." `app.py` docstring: "Nothing is written to disk". `README.md:636`: "client data is never written to disk unless you export it." Also Spec line 26 and `ui/app.js:402`, `help.json:119`: saved set-ups and sessions "hold no client data".
- Reality: `_autosave()` (`crosswalk_server.py:171`) is on by default (`S["autosave"] = True`, line 119) and is called from `upload` (line 1427), so the first file added creates `sessions/<id>.json`. Each later action rewrites it (15 writes in the test session). The file holds the file names, the row ids of every decided row (`file :: range||row number`), and every value a reviewer typed (`queue_edits`). Separately, the launcher writes `launch-log.txt`, `.installed` and `crosswalk.pid`, and Python writes `__pycache__/*.pyc`. The close-app dialog (`ui/app.js:2873`) says "your progress on this batch is saved", which contradicts the goodbye page. `sessions_store.py:17-23` and `README.md:640` admit the typed values; the UI, START HERE and the spec do not.
- Proof: `strace -f` on the full driver session (`a01_disk_session.py`; trace in `audit/A-out/strace_disk.txt`). The only files the server opened for writing were `sessions/s20261030-154813.json(.tmp)` (15 times), `setups/Audit Run.json` and `.pyc` files. The session file after a typed correction:
  ```
  "queue_edits": {"legacy_export.xlsx :: Sheet1 :: A1:I58||9": {"City": "Brooklyn", "Zip": "11201"}}
  "sources": ["canary_clients.csv", "clinic_export.csv", "legacy_export.xlsx", ...]
  ```
  `a02_grep_canaries.sh` finds no canary names in the session or set-up file (the whole-row claim holds); the typed-value claim does not.
- Rewrite requirement: Either write nothing until the user presses an explicit "Save progress" (default off), or say plainly on the first screen and in START HERE: "Saved progress is written to the sessions folder as you work; it holds file names, row numbers and any value you type." Remove "Nothing is being written to disk" from every busy screen. See the Disk writes table below.

### A-05. Two different people with the same Client ID are merged into one client, while the product says "never merged"
- Severity: High
- Claim: `crosswalk_server.py:403`: "The same ID carries different records. Never merged on a guess." `app.py:2413`: "...used by records with different data; review required (not merged)". `ui/help.json:114`: "The engine joins records on its own only where coincidence is not a reasonable explanation." `ui/app.js:2114`: "The tool never merges people on a guess." Spec line 24 and `docs/TECHNICAL.md:30`: "The engine collapses records only where the same identifier appears with identical data."
- Reality: `identity.score_pair` returns 100 for two records with the same ID in the same system before it compares any data (`identity.py:374-376`). If a reviewer accepts the ID-conflict group "as entered" (offered on the group), the identity engine then fuses the records.
- Proof: `audit/A-scripts/a03_final_and_idmerge.py` (fixture `household.csv`: H100 Hector Ballpeen and H100 Hortense Ballpeen). Output (`audit/A-out/a03_out.txt`):
  ```
  {'ok': True, 'outcome': '2 accepted as entered'}
  Master_ID,First_Name,Last_Name,...,Source_Client_IDs,Source_Rows
  M000001,Hector,Ballpeen,5 Gumdrop Ln,11201,Elder Care,1,household.csv,2,H100,household.csv :: A1:H5||0; household.csv :: A1:H5||1
  ```
  Two people, one master record, `Source_Record_Count` 2. Hortense disappears from both counts.
- Rewrite requirement: A shared ID is evidence to propose a link, never grounds to merge when other fields disagree. Same-ID with different first names must show up as an open pair with its evidence, or stay two people. Add a regression test with this exact fixture.

### A-06. "Nothing is left to decide, so this count is final" appears while a client is still in review
- Severity: High
- Claim: `ui/app.js:2122`: "Nothing is left to decide, so this count is final." `crosswalk_server.py:2636-2637` (printable page): "Every proposed link has been decided, so these counts are final." `docs/USER_GUIDE.md:201`: "The counts are final when none are open."
- Reality: "Final" is computed from open identity pairs only (`open == 0`). Rows still waiting in review are not in the clean list, so those people are in neither count.
- Proof: `a03_final_and_idmerge.py`, same run as A-05. After the ID-conflict group is accepted, the missing-ZIP row (H300, Zed Nobody) is still in review:
  ```
  goal1 {'count': 2, 'low': 2, 'high': 2, 'open': 0, 'auto': 1, 'confirmed': 0} goal2 2 rows {'input': 4, 'clean': 3, 'review': 1, 'aside': 0}
  printable says final: True    ("Every proposed link has been decided, so these counts are final.")
  ```
  The file holds 4 people. The screen says 2 and "final": Hector and Hortense are fused (A-05), and Zed is still in review, so he is in neither count.
- Rewrite requirement: A count is final only when no pair is open and no row is undecided. Otherwise label it "provisional, N rows still in review". The printable page must carry the same wording.

### A-07. "Preview the counts" silently deletes every review decision and typed correction
- Severity: High
- Claim: `ui/app.js:1358` (button tooltip): "Process the files with the programs as they stand now and show the two counts. Takes a moment; nothing is decided." `ui/help.json:94`: "refresh as often as you like."
- Reality: `programs_preview` runs `S["actions"] = []` and `S["queue_edits"] = {}` before re-processing (`crosswalk_server.py:3402-3403`). Anyone who goes back to Programs after reviewing loses all group decisions, row decisions and typed corrections, with no warning, and the counts change.
- Proof: `audit/A-scripts/a07_resume_preview.py`, test T1 (`audit/A-out/a07_out.txt`):
  ```
  BEFORE preview: actions = 2 | rows {'input': 266, 'clean': 266, 'review': 0, 'aside': 0} | goal1 265 goal2 52
  AFTER  preview: actions = 0 | tallies: {... 'undecided': 10, 'decided': 0 ...}
     rows {'input': 266, 'clean': 256, 'review': 10, 'aside': 0} | goal1 256 goal2 52
  ```
- Rewrite requirement: A preview must be a read-only calculation on a copy of the state. If a change really does force a re-run, say "This clears your N review decisions" and ask first.

### A-08. "Saved progress" does not restore identity decisions or program grouping, and the next Process wipes the rest
- Severity: High
- Claim: `ui/app.js:556-559`: "Your schema, staging steps, mapping and review decisions are saved as you work, so a closed window does not lose them... resuming asks for the same files again and reattaches your decisions to them." `START HERE.txt:46-47`: "closing the window does not lose your decisions." `ui/app.js:2872-2873`: "your progress on this batch is saved so you can pick it up next time."
- Reality: `SAVED_KEYS` (`sessions_store.py:38-45`) has no `id_decisions`, `program_groups` or `program_aliases`. Resume restores the review `actions`, but pressing Process runs `S["actions"] = []` (`crosswalk_server.py:1652-1653`), which every user must do after re-uploading files. The "Goal 1" decisions (same person or different) and the program groups are gone with no message.
- Proof: `a07_resume_preview.py`, test T2:
  ```
  BEFORE close: goal1 {'count': 261, 'low': 251, 'high': 261, 'open': 11, 'auto': 1, 'confirmed': 6} goal2 51
  saved file has id_decisions: False | program_groups: False | program_aliases: False
  after resume: id_decisions 0 | program_aliases 0 | actions 2
  after Process: actions 0 | queue_edits 0
  AFTER resume + Process: rows {'input': 266, 'clean': 256, 'review': 10, 'aside': 0} goal1 {'count': 256, 'low': 244, 'high': 256, 'open': 14, 'auto': 0, 'confirmed': 0}
  ```
- Rewrite requirement: Save and restore every decision that changes a count (identity pairs, program groups, queue edits, group decisions), and make "Process" after resume replay them instead of clearing them. After resume, show "N decisions restored, M could not be matched to a row" with the unmatched ones listed.

### A-09. Rows outside the included tables vanish from every output while the page says "Every row is accounted for"
- Severity: High
- Claim: `crosswalk_server.py:2643,2649-2651` (printable page): "Rows received ... The books balance: ... = N rows received. Every row is accounted for." `ui/app.js:1453-1454`: "N clean + N to fix = N rows received. Every row is accounted for." `ui/app.js:2288-2290` (Set_Aside_Records): "copies, summary rows and anything excluded, each with the reason. Nothing is deleted; this is where it went." `ui/app.js:2306-2307`: "The server asserts this and fails loudly if it ever breaks." Spec line 23: "refuses to report counts that do not add up."
- Reality: `input` is `len(res["transformed"])` (`crosswalk_server.py:884`), and the assertion compares three slices of that same list, so it cannot fail. Anything dropped before the pipeline (a table excluded on the Sources screen, or the part of a file after a blank line) never enters `transformed`, so it is counted nowhere and is not in the set-aside file.
- Proof: `a06_upload.py` test T5 and `audit/A-out/a20_excluded.txt` (fixture `blankline.csv`: U1, U2, blank line, U3, U4, U5):
  ```
  table blank.csv :: A1:H3 rows 2 kind records included True
  table blank.csv :: A5:H7 rows 3 kind unknown included False | no recognizable person, address, or aggregate headers
  printable 'Rows received': 2
  printable books-balance line: The books balance: 2 + 0 + 0 = 2 rows received. Every row is accounted for.
  clean / review / aside / unique_clients / audit mention U3/U4/U5 or Gamma/Delta/Epsilon: []   (all five empty)
  summary rows: {'input': 2, ...} | goal1: 2 | unique clients in the file: 5
  ```
- Rewrite requirement: Reconcile against the number of data rows in the files as uploaded, not against the pipeline's own list. Every row of every included or excluded table must end in clean, review, set aside or a visible "excluded table (N rows)" line. Treat a blank line inside a CSV as a blank line, not a table boundary, unless the user chooses otherwise.

### A-10. "A reviewer cannot type a new value into a cell" is false, and the output calls the edited row "Passed every check"
- Severity: High
- Claim: Spec line 27: "A reviewer cannot type a new value into a cell." `docs/TECHNICAL.md:33`: "No per-value editing in the app." `ui/app.js:2008-2012`: "Values are never edited here one by one." `ui/help.json:47` and `docs/USER_GUIDE.md:91`: "Values are never edited one by one here." Spec line 25 and `docs/TECHNICAL.md:31`: "The value as entered stays on the row and in the audit."
- Reality: The queue accepts free text for any schema field on one row (`/api/queue/action` with `edits`, `crosswalk_server.py:1969-1990`) and on many rows at once (`ui/app.js:1792-1797`, "Set a field on all selected ... To this value ... Apply and re-check"). The only check is the normal format validation, so any valid-looking value passes. The clean export labels such a row "Passed every check" (`crosswalk_server.py:902-903`, only "kept as entered" rows get another label), and the audit records the column names but neither the old nor the new value.
- Proof: `audit/A-scripts/a12_typed_edit.py` (fixture `household.csv`):
  ```
  fields the screen offers for 'Set a field on all selected': ['First_Name', 'Middle_Initial', 'Last_Name', 'Client_ID', 'Address_1', 'Address_2', 'City', 'State', 'Zip', 'Program']
  typed Zip=11201 and Last_Name=Somebodyelse -> {'ok': True, 'status': 'corrected', 'errors': []}
  clean row: H300 Zed Somebodyelse 11201 | Passed every check
  ```
  Audit line for that row (checked separately): `[15 Corrections | annotated] Values replaced from corrections file 'in-app review' (columns: Last_Name, Zip); re-validated like any other row`. Neither "Nobody" nor "Somebodyelse" appears anywhere in the audit text.
- Rewrite requirement: Decide the rule and write it once. If typed edits are allowed, say so, label edited rows "Corrected by reviewer", and log field, old value hash or old value, and new value in a separate access-controlled change log. If not allowed, remove the free-text path from the API as well as the screen.

---

## Medium

### A-11. "The value as entered stays on the row and in the audit" is false when the engine overwrites City
- Severity: Medium
- Claim: Spec line 25: "Every tidy-up step adds columns and never overwrites. The value as entered stays on the row and in the audit." `docs/TECHNICAL.md:31`: "Originals preserved."
- Reality: When City is wrong and the ZIP is valid, the pipeline replaces City and logs only the new value. The original is in no output file for clean rows (the `orig::` columns exist only on review rows).
- Proof: `audit/A-out/a13_origvalue.txt` (fixture `misplaced.csv`, M001 has City "Zebulon Quillfeather", M002 has City "742 Evergreen Terrace", ZIP 11201):
  ```
  'Zebulon Quillfeather': in clean export=False review=False aside=False audit=False
  '742 Evergreen Terrace': in clean export=False review=False aside=False audit=False
  clean row M001 City = Brooklyn | Passed every check
  ```
  Audit line: `City set to 'Brooklyn' from ZIP 11201`.
- Rewrite requirement: Keep an original-value column (or a change log keyed by row id) for every field the engine changes, and keep it out of the shareable audit (see A-02). Do not overwrite a non-blank value that disagrees with the ZIP without a flag.

### A-12. Goal 2 is shown as one number while it can still move
- Severity: Medium
- Claim: `ui/app.js:2114-2118` and `crosswalk_server.py:2632-2635`: only "the first count is between X and Y"; "Deciding them closes the range." Goal 2 is shown as a single number with no caveat.
- Reality: Goal 2 depends on the same open pairs.
- Proof: `audit/A-scripts/a16_goal2_range.py` (sample files, 17 open pairs, `audit/A-out/a16_out.txt`):
  ```
  BEFORE deciding any open pair: goal1 {'count': 265, 'low': 251, 'high': 265, 'open': 17, ...} | goal2 shown as one number: 52
  AFTER every open pair is decided 'same': goal1 {'count': 251, ...} | goal2 51
  AFTER every open pair is decided 'different': goal1 {'count': 265, ...} | goal2 52
  ```
- Rewrite requirement: Compute and show a low-high range for Goal 2 as well, and apply the same "provisional" label as Goal 1.

### A-13. A bad file in a multi-file upload returns 500, drops the remaining files, and the screen says nothing
- Severity: Medium
- Claim: `ui/app.js:654`: "Drop files here, or browse" (multi-file input, `id="filepick" multiple`); the audit's `Files loaded: N` (`audit_trail.py:32`).
- Reality: `upload` ingests files in a loop with no per-file error handling (`crosswalk_server.py:1421-1427`). The first unreadable file raises, the rest are never read, the browser handler ignores the response (`ui/app.js:3088-3092`: `await fetch(...); return load("sources")`), and the failed file stays in `S["uploads"]`, so it is listed as loaded and `/api/source/file` serves it.
- Proof: `a06_upload.py` T4 (`audit/A-out/a06_out.txt`):
  ```
  HTTP 500 Internal Server Error
  tables loaded: ['first_ok.csv']
  uploads recorded (audit 'Files loaded'): ['Smith J intake.docx', 'first_ok.csv']
  source download route serves the failed file: 200
  ```
  `third_ok.csv` is neither loaded nor mentioned. Related, not a claim defect: re-uploading a file under the same name adds a second table instead of replacing the first (T3: tables `[('export.csv :: A1:H3', 2), ('export.csv :: A1:H5', 4)]`, 6 rows counted).
- Rewrite requirement: Process each file independently, report one line per file ("loaded: 2 tables", "could not read: reason"), only list files that were read, and treat a same-name re-upload as a replace with a confirmation.

### A-14. The "Privacy jitter" can be undone by anyone who has the seed, and the tool prints the seed in the "safe to share" audit
- Severity: Medium
- Claim: `ui/app.js:1435`: "Privacy jitter: 150 to 250 ft, stored points only." Spec line 22: "no randomness except the privacy jitter, which is seeded (default seed 1337)."
- Reality: `jitter_point` makes two `random.Random(seed)` draws per geocoded row in row order (`app.py:2326,2503`). With the seed (shown in the Run screen and in the audit log, `audit_trail.py:70`: `jitter=True, seed=1337`) and the row order, the offsets can be subtracted exactly. The default seed is the same on every install.
- Proof: function-level, using the shipped `jitter_point` and the reference file's true points (`audit/A-out/a11b_out.txt`):
  ```
  exported 40.697765,-73.787188 -> recovered 40.698334,-73.787029 | true 40.698334,-73.787029 | error 0.000 ft
  exported 40.721377,-73.769864 -> recovered 40.721817,-73.769517 | true 40.721817,-73.769517 | error 0.000 ft
  ```
  An end-to-end run could not be done: the shipped sample reference (`nyc_address_points.csv`) is synthetic and its city/ZIP pairs disagree with the validator (for example ZIP 10305 listed under Queens), so the pipeline sends those rows to review and geocodes none of the sample files ("Verified 0, Not matched 257" on the printable page).
- Rewrite requirement: Draw jitter from a fresh random source per run (secrets/os.urandom) and never record the seed with the output. If reproducibility is required, make it an explicit "reproducible test run" mode with a warning that it is not private. Describe it as "reduces precision", not "privacy".

### A-15. `launch-log.txt` is described as "start-up only, no client data"; under the double-click launcher it logs the whole session, including uploaded file names
- Severity: Medium
- Claim: `START HERE.txt:36-37`: "If you need to report a problem, send the file launch-log.txt from this folder. It records what happened during start-up and contains no client data."
- Reality: When started by `Crosswalk.vbs` (pythonw, no console), `_LogStream` (`launch.py:36-62`) sends everything the server prints to stderr into the log, for as long as the tool runs. An unreadable upload produces a 500 and a full traceback that ends with the file name. The log also records the Python path and install folder. `access_log=False`, so request paths and queries are not logged (confirmed).
- Proof: `audit/A-scripts/a10_pythonw_log.py` (closes fds 1 and 2 so `sys.stdout` is `None`, as under pythonw; `audit/A-out/a10_pythonw_log.txt`):
  ```
  upload Smith Maria 123-45-6789 intake.docx -> HTTP 500
  ... ValueError: Unsupported file type: Smith Maria 123-45-6789 intake.docx
  ```
  This is a faithful emulation of the stream setup, not a run under real Windows pythonw.
- Rewrite requirement: Log start/stop events only and a per-error code, never exception text built from user input. Say "may contain file names and folder paths" in START HERE, and have the report button mask them.

### A-16. Three different promises about how fast the tool closes itself, and the real number is 45 seconds
- Severity: Medium
- Claim: `START HERE.txt:23-24`: "The tool notices after a few minutes and closes itself." `START HERE.txt:54`: "stops the tool by itself within about a minute." `ui/app.js:3114`: "the tool is told so every half minute." `crosswalk_server.py:2768`: "every few seconds." `launch.py:418`: "silence alone is enough after a few minutes."
- Reality: The browser sends a heartbeat every 10 s (`ui/app.js:3120`), the launcher stops after `IDLE_LIMIT = 45` s of silence (`launch.py:83`) and after 15 s following a goodbye (`GRACE_AFTER_CLOSE`). A reload or a tab closed by mistake starts a 15 s countdown.
- Proof: `audit/A-scripts/a05_launch.py` (real `launch.py`, `audit/A-out/a05_idle_bye.txt`):
  ```
  IDLE: stopped 46.5s after the last heartbeat (exit code 0)
  BYE: stopped 16.3s after the goodbye (exit code 0)
  ```
- Rewrite requirement: One documented rule, one constant. If the tool stops itself while a batch is in memory, say so in the same sentence ("uploaded files are lost; saved decisions stay"). See "Unverified" below for the background-tab concern.

### A-17. The Stop scripts can kill an unrelated process and always report success
- Severity: Medium
- Claim: `Stop Crosswalk.command:9` (comment): "only a Python running this folder's launch.py, never anything else". `Stop Crosswalk.vbs:32` (comment): "any pythonw running launch.py from this folder". Both end with (`.command:11`, `.vbs:39`): "Crosswalk has been stopped. This folder can now be moved, replaced or deleted."
- Reality: The `.command` kills whatever PID is in `crosswalk.pid` (line 6) before the careful `pkill` runs. A stale pid file (left after a crash or power loss; the pid is only removed on a clean exit) can point at any process. The `.vbs` last-resort step (line 34) matches `commandline like '%launch.py%'` with no folder in the pattern, so it ends every pythonw running any `launch.py`, and it sets `stopped = True` (lines 29, 35) without checking the result. Both scripts show the success message even when nothing was running.
- Proof: stale pid test on the `.command` (Linux; copy `src/agentA-stop`):
  ```
  unrelated process: pid 10317 (sleep 300)
  crosswalk.pid (stale, left by a crash) contains: 10317
  Terminated
  Crosswalk has been stopped. This folder can now be moved, replaced or deleted.
  unrelated process 10317 was KILLED by Stop Crosswalk.command
  ```
  The `.vbs` behavior is from reading the file; it was not run on Windows.
- Rewrite requirement: Verify the pid belongs to this folder's process (name and command line) before killing, and report what actually happened ("stopped", "was not running", "could not stop").

### A-18. "Drop files here" has no drop handler
- Severity: Medium
- Claim: `ui/app.js:654`: "Drop files here, or browse". `docs/USER_GUIDE.md:35` and `ui/help.json:12`: "Drop the files in or browse for them." `docs/VIDEO_SCRIPT.md:37`: "Drop your exports in."
- Reality: There is no `dragover`, `dragenter`, `drop` or `dataTransfer` anywhere in `ui/app.js` or `ui/index.html`. The only upload path is the hidden file input (`ui/app.js:658`, handler at `ui/app.js:3088`, `#filepick`).
- Proof: `grep -n -i "dragover\|dragenter\|\"drop\"\|ondrop\|dataTransfer" ui/app.js ui/index.html` prints nothing. What the browser then does with a dropped file (typically it opens or downloads it, replacing the page) was not tested.
- Rewrite requirement: Either implement drag and drop with a visible hover state, or say "Browse for files". Add a document-level `dragover`/`drop` guard so a miss does not navigate away from the app.

### A-19. The "Saved progress" card names the wrong stage
- Severity: Medium
- Claim: `ui/app.js:544` (Saved progress list on the first screen) prints "stopped at <stage>", built by `sessions_store._describe` (`sessions_store.py:168-175`).
- Reality: `STAGE_NAMES` has 8 entries, the product has 10 stages (check plus 9). Programs and Summary are missing, so every stage from Programs on is shifted, and the last two show "in progress".
- Proof: `audit/A-out/a17_stagenames.txt` (stage set with `/api/goto`, then `/api/sessions`):
  ```
  stage 4 'Match your columns' | Saved-progress card says: 'stopped at Map, 1 source file'
  stage 5 'Programs'          | ... 'stopped at Run, 1 source file'
  stage 7 'Fix problems'      | ... 'stopped at Export, 1 source file'
  stage 9 'Download'          | ... 'stopped at in progress, 1 source file'
  ```
- Rewrite requirement: Take stage names from the one list the screens use, in the reader's current mode (Guided or Advanced).

### A-20. The legacy launchers and README contradict the "offline, first run only" story
- Severity: Medium
- Claim: `run.sh:2` and `run.bat:2`: "Install dependencies (first run) and launch the tool". `START HERE.txt:14`: "That is the only step that uses the internet." `README.md:321-323`: "The original Streamlit app remains available and unchanged via run.bat, run.sh... Both read the same engine, so results are identical." `launch.py:171`: "Install what is missing, once. Later runs skip this entirely."
- Reality: `run.sh` and `run.bat` run `pip install -r requirements.txt` on every launch (an internet call each time, and a failure when offline). The Streamlit front end has no identity engine: `app.py` never imports `identity.py` (`grep -n -i "identity\|unique" app.py` finds only two comments), so it produces no unique-client counts, which are the point of the project. `launch.py` skips the install only when no package is missing; after a Python upgrade it silently reinstalls from the internet.
- Proof: file reads: `run.sh` (`python3 -m pip install -r requirements.txt` then `streamlit run app.py`), `run.bat` (same); the grep above.
- Rewrite requirement: Ship one launcher. State plainly that any later reinstall also uses the internet, and remove the second UI or label it "cleaning only, no unique-client counts".

---

## Low

### A-21. Two screens hard-code "Stage 0N of 07"; the real total is 09
- Severity: Low
- Claim: `ui/app.js:1058`: `header("Stage 04 of 07", "Map", ...)` and `ui/app.js:1542`: `header("Stage 06 of 07", "Review", ...)`.
- Reality: Every other screen uses `stageHead`, which prints `Stage 04 of 09` (`ui/app.js:303-307`). Review is stage 07, not 06, and both empty-state headers use the Advanced names even in Guided mode ("Map" and "Review" instead of "Match your columns" and "Fix problems").
- Proof: `audit/A-out/a17_stagenames.txt` header lines: plain stages `['Add your files', 'Set up your columns', 'Tidy up', 'Match your columns', 'Programs', 'Process', 'Fix problems', 'Results', 'Download']`; 9 entries; `ui/app.js:1058,1542` read above.
- Rewrite requirement: One function builds every stage header, empty states included.

### A-22. The "clean + review = input" promise is stated three ways and is wrong once anything is set aside
- Severity: Low
- Claim: `crosswalk_server.py:965` (stamp on every screen): "LOSSLESS / clean + review = input". `README.md:959`: "guarantees that clean plus review equals the input count." `ui/app.js:1453` (Run screen): "clean + to fix = rows received".
- Reality: The true equation has three terms (`crosswalk_server.py:881`, `ui/app.js:2304`, `docs/TECHNICAL.md:29`). The Run screen shows the numbers from the run itself and does not update after decisions.
- Proof: `audit/A-out/a15_equations.txt` after one row is set aside:
  ```
  Run screen band    -> 1 clean + 3 to fix = 4 rows received | sum = 4
  Export screen band -> {'input': 4, 'clean': 1, 'review': 2, 'aside': 1, 'kept': 0}
  Rail stamp         -> [['LOSSLESS', 'clean + review = input']]      (1 + 2 does not equal 4)
  ```
- Rewrite requirement: One equation, three terms, computed live, used everywhere.

### A-23. The "Nothing leaves this machine" note and the Close button are invisible in the default desktop layout
- Severity: Low
- Claim: `ui/app.js:251`: "Nothing leaves this machine. Exports are written only when you download them." `START HERE.txt:21`: Click "Close Crosswalk" at the bottom left of the screen.
- Reality: At widths of 981 px and up the menu starts collapsed (`UI.railOpen: false`, `ui/app.js:24`) and the CSS hides the whole footer: `.rail:not(.open) .rail-foot { opacity: 0; pointer-events: none }` (`ui/styles.css:676-679`). The note, the mode switch, Undo, Audit trail and Close are hidden until the pointer rests on the menu for 380 ms or the grip is clicked. Read from code and CSS; not rendered in a browser.
- Proof: the quoted lines and the default state.
- Rewrite requirement: Keep the privacy statement and the Close action visible without a hover, or change START HERE to describe the menu button.

### A-24. "Every ... decision a reviewer took" is capped at 2,000 rows per group
- Severity: Low
- Claim: `ui/app.js:2244`: "every decision a reviewer took, as they stand right now." `ui/app.js:2297`: "Every transformation and decision."
- Reality: `audit_trail.decision_lines` lists at most 2,000 row ids per group decision (`audit_trail.py:85-90`) and then prints "... and N more". The cap is disclosed in the file, not on the screen or in the claim.
- Proof: `audit/A-scripts/a18_audit_cap.py` (2,100 rows missing a ZIP, all accepted):
  ```
  rows accepted by the reviewer: 2100 | rows listed by ID in the audit trail: 2000
  last lines: ['     big.csv :: A1:H2101||1999 id B01999', '     ... and 100 more']
  ```
  The working case in the spec is about 19,000 rows.
- Rewrite requirement: List every row id, or store the decision as a range or a saved query that can be replayed, and say which.

### A-25. Documents name a file and a function that do not exist
- Severity: Low
- Claim: `README.md:318`: "Or run `run_crosswalk.bat` on Windows, `./run_crosswalk.sh` on Mac or Linux". `docs/TECHNICAL.md:70`: "`table_detect.detect_tables`".
- Reality: `ls` shows `run_crosswalk.bat` and `run.sh` but no `run_crosswalk.sh`. `table_detect.py` has `detect_in_grid` and no `detect_tables`. An automated check of the 355 names cited in backticks in `docs/TECHNICAL.md` found these two (plus the generic placeholder `vScreen`) as the only misses.
- Proof: `ls run_crosswalk* run.sh` prints `run.sh run_crosswalk.bat`; `grep -n "def detect" table_detect.py` prints `detect_in_grid`.
- Rewrite requirement: Generate the file and function references in the docs from the code, or test them.

---

## Checked and true

- No page, script or style loads anything from the network: no external URLs in `ui/`; the only HTTP in Python is to 127.0.0.1 (`launch.py:235,289,335`); Streamlit usage stats are off (`.streamlit/config.toml`).
- The server binds to 127.0.0.1 only (`launch.py:393`).
- `access_log=False` and `log_config=None`: no request paths or query strings reach `launch-log.txt` (checked in the pythonw emulation).
- Exports are written only on download. In the strace of a full session, the server never opened an export file for writing; the nine files in `audit/A-out/disk/` were written by my driver.
- Nothing is written to HOME or TMPDIR (both stayed empty across the launcher runs).
- Uploaded rows are not saved: no canary name, address or ID appears in `sessions/*.json` or `setups/*.json` (the canary grep returns 0 in both).
- A headerless CSV is detected (`header row 0`, columns numbered), and saving a set-up from it leaks no values (`audit/A-out/a14_out.txt`).
- Set-up files hold column names and settings (and program names), not rows (checked on the six-file run).
- The Audit and Export screens' `orig::` instruction is accurate: the review export has `orig::` columns and re-upload is supported (see A-01 for the side effect).
- A Close from the in-app button works: `/api/quit` stops the process (`launch.py` run, exit code 0).
- Closing the window triggers `/api/bye` and the launcher stops 16.3 s later (A-16 for the wording).
- Sessions older than 7 days are purged on listing and on every save (`sessions_store.py:73-92`, by file modification time). Run: an 8-day-old session file was removed and a fresh one kept (`audit/A-out/a21_out.txt`).
- The `.command` quit-by-pattern line is folder-specific (`pkill -f "python[0-9.]* .*$(pwd)/launch.py"`); the problem is the pid-file line above it (A-17).
- All control labels named in `help.json` exist in the UI: Skip the steps, Accept all, keep this one, Copies keep the first, Different people keep all, Save set-up, Open the summary page, Fill a field for this source only, Go back to what the tool proposed, Undo the last change, Leave for later, Set aside, Approve as entered.
- No stray Crosswalk process or listener was left running after the tests.
- "Deterministic" (Spec line 22) holds for the sample set: two full runs with seed 1337 produced byte-identical clean, review, unique-clients and by-program files (SHA-256 prefixes match, `audit/A-out/a21_out.txt`). That is a statement about identical input, not about the privacy of the jitter (A-14).

## Unverified (code reading only, not proven; not counted above)

- `Crosswalk.vbs` decides "Python is installed" by whether `shell.Run "python.exe -c ..."` raises an error. On Windows machines without Python, the Microsoft Store stub for `python.exe` starts and exits without raising, which would skip the "Crosswalk needs Python" message. Needs a Windows machine to prove.
- `Stop Crosswalk.vbs` uses `wmic`, which Microsoft removed from recent Windows 11 builds. The step then fails silently and still reports success.
- Browsers throttle timers in tabs that have been hidden for several minutes (about one run per minute). With a 10 s heartbeat and a 45 s idle limit, a tab left in the background during a long review could be treated as closed and the tool could stop with the batch in memory. Needs a real browser to prove.
- Dropping a file onto the page when no handler exists (A-18): the browser's reaction, and whether the page's `pagehide` then starts the 15 s shutdown countdown, was not tested.
- macOS Terminal behavior of `Crosswalk.command` (a window stays open under `launch.py`) was not tested.

## Disk writes

Snapshot before, strace during, and file inspection after a full session (6 files uploaded including the canary file, a typed correction, queue and bulk actions, duplicate decisions, identity decisions, a set-up save, every export, the printable summary and the audit text). Canary values are fictitious names and addresses listed in `audit/A-fixtures/canary_clients.csv`.

| Path (relative to the app folder) | When written | Contains client values? |
|---|---|---|
| `sessions/<id>.json` (and `.json.tmp`, renamed) | First upload, then after every action (15 writes in the test session); on by default | No names, addresses, IDs or rows. Yes for any value a reviewer typed (`queue_edits`: City "Brooklyn", Zip "11201" in the test), plus uploaded file names and row ids (`file :: range||row`) of every decided row. Not restored on resume: identity decisions, program groups (A-08). |
| `setups/<name>.json` | Only when the user presses Save set-up | No client rows or canary values. Holds file names, column names, header rows, mapping, tidy-up steps, defaults, program names and groups, settings. Column names would be data on a file whose header row is wrongly chosen (not reproduced; a headerless file was handled correctly). |
| `launch-log.txt` | Every launch; under pythonw also all server stderr for the whole session | Not in the normal path (start, ready, stopped lines, Python path, install folder). Yes in the error path: uploaded file names inside tracebacks (A-15). No request paths. |
| `crosswalk.pid` | After the server answers; removed on clean exit | No. A stale copy is dangerous (A-17). |
| `.installed` | First successful start | No. |
| `__pycache__/*.pyc` (13 files in the test) | First import of each module | No. |
| Anything under HOME or TMPDIR | Never | Not applicable. |
| Export files (`Final_Clean_Mapped.csv` and the other six, `printable_summary.html`, audit text) | Only through the browser's download | Yes by design for clean, review, aside, unique lists. The audit text holds raw values in some lines (A-02); the review file holds unmapped columns (A-01); the printable page holds a Client ID and file names (A-03). |
