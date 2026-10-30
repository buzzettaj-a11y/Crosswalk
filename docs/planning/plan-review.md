# Plan review: SPEC 1.1 and milestones M00 to M15

Reviewed 2026-10-30 against `SPEC.md` 1.1, `CLAUDE.md`, `docs/milestones/README.md`, the sixteen milestone files and the finding headers in `docs/audit/A-claims.md`, `B-values.md` and `C-counts.md`.

What was checked by running code, so Joe does not have to: every known-answer vector in the plan was recomputed and matches. That covers the M01 header signature, table key, record keys and person keys, the M05 offset vectors, the M06 master IDs, the M09 run ID, signature and shareable hash, and the M13 backup blob. The M06 C-01 scores, the M07 B-40 pair counts (7 and 27), the M08 R and S fixture numbers in both states, the M08 C-03 ranges and the M13 calibration arithmetic were worked by hand and match. All 101 audit IDs have a named test file somewhere in the plan.

Findings use the IDs B (Blocker), S (Should fix) and M (Minor). Line numbers are for the files as they stand today.

---

## Blocker

### B1. M00's A-20 test fails on files M00 itself must create

- **Where:** `docs/milestones/M00-foundation.md:135`, against `:53`, `:56` and `:61`.
- **What's wrong:** M00:135 says `test_A20_no_launchers.py` checks for "No word `pip`, `streamlit`, `fastapi`, `uvicorn` or `webbrowser` in `wholecount/` or `tools/`." But M00:53 builds `tools/offline_rules.py` "as in R6", and R6's `FORBIDDEN_MODULES` contains `"webbrowser"` (research line 652). M00:61 builds the guard "from R2", whose deny list names `"webbrowser"` (research line 444). M00:56 builds `tools/offline_scan.py` from R6's checks, whose pattern contains `webbrowser`. So `make test` cannot be green in M00 as specified.
- **Fix:** Make the word check look only at import statements and calls, found by AST, or exempt `tools/offline_rules.py`, `tools/offline_scan.py` and `wholecount/guard/` the way R6 already exempts `offline_guard.py`.

### B2. M00's copy lint fails on M00's own milestone file

- **Where:** `docs/milestones/M00-foundation.md:133` against `:83`.
- **What's wrong:** M00:133 says `tests/copy/test_lint.py` rejects "no spelling from `us_spelling.txt`, in every copy text and in `docs/milestones/*.md`". M00:83 writes out the list itself: "(colour, behaviour, favour, honour, centre, organisation, organise, recognise, analyse, programme, licence, catalogue, defence, cheque, grey)". A scan of all 17 milestone files finds this line as the only hit, so `make copy` goes red on day one. Code has been told not to edit the plan to get around it.
- **Fix:** Replace the list at M00:83 with a pointer to `wholecount/copy/us_spelling.txt`. The other option is to have the lint skip text inside backticks and parentheses that quote the list.

### B3. M14's A-20 test forbids URLs and `pip` that earlier milestones are told to write

- **Where:** `docs/milestones/M14-build-install.md:159`.
- **What's wrong:** M14:159 says: "No `pip`, `curl`, ... or URL in `installer/`, `build/`, `wholecount/` or any script under `tools/` except `signing.json` (its timestamp address) and `tools/sandbox`." Earlier milestones require all of these:
  - `tools/offline_rules.py` (M00, R6) holds `URL_ALLOW_PREFIXES = ("http://schemas.openxmlformats.org/", ...)`.
  - `build/spec_lists.py` (M14:62) carries R4's `DEV_ONLY` list, which contains `"pip"`.
  - M03:107 has `tools/make_zip_table.py` cite `https://www.nyc.gov/assets/doh/...`. The same line says "Put the URL and retrieval date in each `source` value" of `wholecount/engine/geo/data/nyc_zips.csv`.
  - M05:163 has `tools/make_district_files.py` build the district files from NYC Planning and Open Data, citing source and date.
  - M10:75 puts a `SOURCE.txt` "giving the source address" in `wholecount/ui/theme/fonts/`.
- **Fix:** Limit the test to `installer/`, `build/wholecount.spec`, `build/rthook_offline.py`, the shipped `wholecount/**/*.py` and the PowerShell scripts. Then either move every provenance URL into `licenses/` notices or allowlist the named data and dev-tool files explicitly.

### B4. The example data cannot run under the 1.1 count rule, but four milestones assume it runs from start to Download

- **Where:**
  - SPEC 4.1 (line 277) and P-VAL-2 (line 485).
  - `M02-columns.md:127`.
  - `M11-stages-01-05.md:45`.
  - `M12-stages-06-09.md:5`.
  - `M14-build-install.md:77`.
  - `M15-acceptance.md:73-75`.
  - The Windows checks in M12 step 1, M14 step 5 and M15 step 3.
- **What's wrong:**
  - **The data.** `legacy/sample_data/clinic_export.csv` has only `Name,Full_Address`. `portal_export.json` has Name, Address, City, State and Zip_Code. `state_export.xml` has Name, Address_1, Address_2, City, State and Zip_Code. None of the three has a Client_ID or a date of birth, and together they hold 157 of the 266 rows.
  - **The rule.** SPEC 277 says "A table that maps neither blocks Process for that table." P-VAL-2 requires "a Client_ID or a valid date of birth" on each row.
  - **The plan already sees it.** M02:127 records "The only blockers are First_Name, Last_Name and Client_ID", and no later milestone clears Client_ID.
  - **What happens on a run.** The fast path is held (M11:45). Making Client ID optional still leaves 157 rows `no_identifier`, which puts batch confidence at Low (at most 109 of 266) and holds Download until the Low tick. "Auto-maps" also leaves First_Name and Last_Name unmapped in three files unless the proposed split steps are applied.
  - **Where it breaks.** M14:77's self-check `pipeline.sample` ("adds the five example files, includes the tables, auto-maps, runs with no geocoder, and compares ... counts"), M15's `drive.py fast_path(files)` and `test_sample_both_routes.py`, and Joe's "Press `Try example data`, `Process everything`, then Download" all fail as written.
- **Fix:** Joe decides before M11, choosing one of two options:
  - Ship new made-up example files with a Client_ID or date of birth on every row, generated by a committed script into `wholecount/sample_data/`.
  - Write the exact steps into M11, M12, the M14 self-check and M15 `drive.py`: accept the proposed steps, make Client ID optional and tick Low. Pin the resulting counts.

---

## Should fix

### S1. M04's state rules contradict SPEC P-STD-5 and M04's own notes

- **Where:** `M04-standardize.md:35`, `:41`, `:103` and `:182`, against SPEC 449 and 451.
- **What's wrong:** M04:103 says "A blank state with no ZIP gives `address_part_missing`" and "A non-NY state beside an NYC ZIP follows P-STD-5 and the row is outside NYC (log it)." M04:35 says "`outside_nyc` is set by ... a US state other than NY." The spec says the opposite: "Another state written beside an NYC ZIP gives the location problem 'State and ZIP disagree,' not 'Outside NYC'" (SPEC 449), and "A blank state with no ZIP gives the location problem 'Address incomplete.'" (SPEC 451). The notes at M04:144-145 agree with the spec. But `state_zip_disagree` and `address_incomplete` are missing from the reason list at M04:41, which P-VAL-3 makes binding, and M04:182 still asks Code to log the outside-NYC reading.
- **Fix:** Rewrite M04:35, :41 and :103 to match the notes:
  - Add both reasons as `location` reasons.
  - Set `outside_nyc` from a non-NY state only when the ZIP is not an NYC ZIP.
  - Drop the non-NY state item from M04:182.

### S2. M02's body still has the 1.0 required-field rules

- **Where:** `M02-columns.md:34`, `:38` and `:90`, against SPEC 277-278 and M02:105-106.
- **What's wrong:**
  - **Custom fields.** M02:38 says "A required custom field with no column blocks Process (SPEC 4.1 is silent on a missing column, so this is the cautious reading; log it)." SPEC 1.1 is not silent: "A required custom field with no column blocks Process only if it's marked 'needed to count.'" M02:106 agrees with the spec.
  - **Client_ID.** M02:34 ("`required` ...: First_Name, Last_Name and Client_ID") and M02:90 (`missing_required`) never mention that a Date_of_Birth column also meets the Client_ID requirement, which SPEC 277 and M02:105 require.
- **Fix:** Edit M02:34, :38 and :90 to state the 1.1 rules, and remove the "SPEC 4.1 is silent" item from the decisions to log.

### S3. Open copy groups "hold the count" in M08, which P-VAL-2 and P-VAL-3 do not allow, and M04's test pins the opposite

- **Where:** `M08-session-counts.md:84`, `:203` and `:245`. `M04-standardize.md:168`. SPEC 489 and 501.
- **What's wrong:**
  - **M08.** M08:84 says "an open copy group and an open same-ID conflict make it `not_counted_yet`". The base state at M08:203 counts both R07 rows, R09 and R10 as not counted.
  - **The spec.** A row counts when "It isn't a confirmed copy" (SPEC 489), and "Only a missing name, a missing identifier ..., a field marked 'needed to count' that fails, and an open same-ID conflict hold the count" (SPEC 501). SPEC 8.1 and 8.4 still put copies under the "Holding the count" tab, so the spec is split and M08 picks one side.
  - **M04's test.** M04:168 asserts "only `name_missing`, `no_identifier` and `needed_field_failed` hold the count". That fails as soon as M06 or M08 adds the same-ID kind, or the copy kind, to `problems.toml`.
- **Fix:** Get Joe's ruling before M08 and make SPEC P-VAL-2/P-VAL-3 and M08 say the same thing. Change M04's test to "exactly these three, plus the kinds M06 and M08 add".

### S4. A person key built without a Client_ID joins rows silently (H5 risk)

- **Where:** `M06-people.md:110` and `:74`. SPEC 314-317. H5 (SPEC 103).
- **What's wrong:**
  - **The rule.** M06:110 says "Rows with one person key are one person record." Only a key built from a Client_ID produces an `AutoJoin` that Results lists. Without a Client_ID the key is `system | given | surname | dob` (SPEC 315, M01:94).
  - **Across tables.** Two counted rows in two tables of one system, with no Client_ID and the same folded name and date of birth, become one person. Results lists no join and offers no split. H5 requires "Every automatic join is listed on Results with its reason and a 'These are different people' action."
  - **Inside one table.** DUP-4 at M06:74 refuses `NotCopies` with `same_person_key`, so a reviewer can never record two people.
- **Fix:** Treat a shared name-based key as one person record only after a copy decision. Until then, key each row separately (DUP-7's `row` mode) and let P-ID propose the pair. The other option is for Joe to approve a third named join reason, listed on Results with a split action.

### S5. Saved masters from the crosswalk can merge two groups with no join reason in this batch

- **Where:** `M06-people.md:118` (ID-8), `M13-calibration-crosswalk.md` XW-4 and XW-8, SPEC 334 and 606.
- **What's wrong:** M06:118 says "a group that holds known person keys takes the master ID with the earliest `created_at`". Neither M06 nor M13 says what happens when two groups in this batch hold person keys that resolve to the same saved master. That happens, for example, when someone moved in one system and no longer meets `four_exact_facts`. Goal 1 counts master IDs (SPEC 606), so the two collapse into one person with no listed join. The M06 property "Master IDs are unique per group" also breaks.
- **Fix:** Add a rule to ID-8 and XW-4: list the case as a join with a named reason (for example `earlier_batch`) and a split action, or give the second group a new ID and add a No longer apply entry. Add a test for it.

### S6. Practice runs leave out Map_Counts and the district columns, which the spec says are always written

- **Where:** `M09-outputs.md:69`, `M12-stages-06-09.md:155` and `M15-acceptance.md:75`, against SPEC 518 and 766.
- **What's wrong:** M09:69 says "Map_Counts, Map_Points and the three district columns are not written". M12 and M15 build on that reading. The spec says "| Map_Counts | Always |" and "Map_Counts is always written", and P-GEO-4 asks only for PRACTICE marking. All three milestones log this as a question, but their tests bake the answer in.
- **Fix:** Get Joe's answer to M05's question (1) before M09. Then change either SPEC 9.1 and P-GEO-6, or M09, M12 and M15 together.

### S7. M11 encrypts the set-up export, which the spec and M09 say is plain JSON

- **Where:** `M11-stages-01-05.md:36`, against SPEC 847 and `M09-outputs.md:114`.
- **What's wrong:** M11:36 says "`Export to a file` and `Import from a file` (both through the Windows file dialog, encrypted file)". SPEC 847 says "Exported as plain JSON". M09:114 says `export_setup` "writes plain JSON, because DPAPI output cannot move to another computer."
- **Fix:** Change M11:36 to "plain JSON file" and add the SPEC 10.3 contents note to the export screen.

### S8. M13 adds a thresholds file that H9 does not allow

- **Where:** `M13-calibration-crosswalk.md:89` and `:151` (question 7), against SPEC 136 (H9).
- **What's wrong:** M13:89 says thresholds are "saved to `calibration\thresholds.json`". H9 says prefs.json "holds settings only: ... thresholds and the window size ... It keeps no other files."
- **Fix:** Store the two numbers, the reviewer and the time in `prefs.json`. Drop `thresholds.json` from M13's files, scans and questions.

### S9. M10 and M13 each say the other one adds the Settings link

- **Where:** `M10-window.md:19`, `:138`, `:249` and `:308`. `M13-calibration-crosswalk.md:98`, `:109` and `:151`. SPEC 909.
- **What's wrong:**
  - **M10.** M10:19 says M13 "adds the Settings link to the footer", M10:138 says "M13 adds one more footer link, `Settings`", and Out of scope (M10:308) lists "the Settings footer link (M13)". M10:249, in the notes, says "The ledger footer has a Settings link from this milestone on."
  - **M13.** M13:98 says "M13 adds one `Settings` link to the ledger footer", and question (6) says "which the frame did not have". M13:109 says "The Settings link and drawer already exist from M10."
  - **The spec.** SPEC 909: "M10 builds it with the saved-progress switch, the reviewer name and the system check table."
- **Fix:** Delete the M13 sentence at M10:19, the Settings clause at M10:138 and M10:308, the link sentence at M13:98, and question (6) at M13:151.

### S10. M01 and M10 define `ProgressMessage` and the step IDs differently

- **Where:** `M01-reading.md:47`. `M10-window.md:191`, `:195` and `:267`. `M13-calibration-crosswalk.md:103`.
- **What's wrong:**
  - **M01.** `ProgressMessage(message_id, params)`, where `params` "is a dict". `StepRef(step)`. A `Step` enum of "the 15 distinct step names". `render(message)`.
  - **M10.** `ProgressMessage(id, params)`, `StepRef(step_id)` and `copy.render(id, params)`. Its test calls `ProgressMessage("x", ("Jane Doe",))` with a tuple, which raises AttributeError, not TypeError, against M01's dict. `jobs/steps.py` lists 14 step IDs, with one `count` for both "Counting and balancing" and "Counting".
  - **M13.** M13:103 says "Add the `calibrate` and `backup` step IDs", but M10 made `calibrate` an action, and no backup action exists in SPEC 11.6.2.
- **Fix:** Have M10 reuse M01's names (`message_id`, dict params, `StepRef(step)`, the `Step` enum) and pass a dict in its test. Key `jobs/steps.py` on the `Step` enum. Define `backup` as a new action with one step, and add it to SPEC 11.6.2.

### S11. M09 puts a session call inside the engine

- **Where:** `M09-outputs.md:43` and `:72`, against `M00-foundation.md:127` and SPEC 251.
- **What's wrong:** `write_outputs()` lives in `wholecount/engine/outputs/writer.py`, and M09:72 says it "calls `Session.download_gate()` first". M00's layering test forbids `wholecount/engine` importing `wholecount.session`, and SPEC 251 says "The engine never sees the session."
- **Fix:** Check `download_gate()` in `session/export.py` and pass the engine writer plain inputs. The other option is to move `write_outputs` into `session/`.

### S12. Fix problems needs engine output that no milestone builds

- **Where:** `M12-stages-06-09.md:87`, `:92`, `:97` and `:103`, against `M08-session-counts.md:86`.
- **What's wrong:** M12:87 says "A kind is the engine's `Cause.kind`". M12:103 needs "the engine's sentence, such as `City reads from REGION, which is blank on these rows, while BOROUGH is filled on all 1,842.`", and the cross-file note at M12:97 needs a count of people in other files. M08's `Cause` has "a count, a title key, its allowed actions, and `routed`". It has no `kind`, and no milestone builds a mapping diagnosis. M12:271 rules out engine work.
- **Fix:** Add `Cause.kind`, a `diagnose_mapping()` rule built on M02's `better_column` and a `people_in_other_files` count to M08, with tests.

### S13. M08's A-06 test describes a case that 1.1 no longer produces

- **Where:** `M08-session-counts.md:220`.
- **What's wrong:** M08:220 says "`final` is false with one row not counted yet and no pair open (the `household.csv` case with H300 left in review)". H300 is `Zed,Nobody,22 Missing Zip St,Brooklyn,NY,,Workforce`. It has a name and a Client_ID, so under P-VAL-2 it is counted with a location problem, which the same test says "leaves it true". The H100 conflict in that file gives two rows not counted, not one.
- **Fix:** Use a row with a blank First_Name for the not-counted case. Keep H300 as the "location problem alone" case, after the H100 conflict is decided.

### S14. The bulk-accept note puts free text into the audit log, which the spec allows only for Set aside (H8 risk)

- **Where:** `M08-session-counts.md:95` and `:97`, `M12-stages-06-09.md:100`, against SPEC 672 and 732.
- **What's wrong:** M08 adds "`AcceptProof(typed_count, reason_code, note)`" and says "A note goes into the `note` slot". M12:100 gives Accept a 120-character Other note. SPEC 8.7 says the reviewer "picks a reason from the fixed list". SPEC 8.1 allows an Other note only for "Set all aside". H8 has no free-text category, so a typed client name could reach the internal log.
- **Fix:** Remove the note from bulk accept, or have Joe approve it in SPEC 8.7 and H8 first.

### S15. M15's independent check expects columns M09 does not write

- **Where:** `M15-acceptance.md:77`, against `M09-outputs.md:60-62` and SPEC 772.
- **What's wrong:** M15:77 checks "that the record keys in `Unique_Clients` are exactly the record keys of `Final_Clean_Mapped`". M09's binding Unique_Clients columns hold `Source_Records` as "`letter :: Source_File :: Source_Row`" and no record keys. The 40-line pandas join check also needs each row's source system, and Final_Clean_Mapped has no System column.
- **Fix:** Compare `Source_Records` with Final_Clean_Mapped's letter, file and row, or add `Record_Keys` and `System` to M09's column lists now.

### S16. The example files and the sample reference are never put in the package, and the bundle filter misses three formats

- **Where:** `M11-stages-01-05.md:46` and `:168`, `M15-acceptance.md:24`, `M14-build-install.md:66`, `:77` and `:147`.
- **What's wrong:**
  - **Where the files are.** M11 loads "the five sample files" from no stated place. Its Windows check and M15:24 assume `wholecount/sample_data/`. M01:102 copies them only to `tests/data/sample/`, and M05 keeps the sample reference at `tests/fixtures/geo/sample_reference.csv`.
  - **The bundle.** M14:66 ships "Nothing from `tests/`", and its `collect_data_files` filter takes only toml, csv, geojson, json, ttf and txt. The `.xlsx`, `.tsv` and `.xml` examples would be left out, so the frozen `readers.*` and `data.sample_reference` self-checks fail.
- **Fix:** Have M11 (or M05) create `wholecount/sample_data/` holding the five files and the sample reference, and add `**/*.xlsx`, `**/*.tsv` and `**/*.xml` to M14:66.

### S17. The progress prototype is not where Code can read it

- **Where:** `M10-window.md:7` and `:32`, `M12-stages-06-09.md:26`, SPEC 927.
- **What's wrong:** M10:7 says "The prototype is `progress-confidence.html` in the planning scratchpad, and its markup and copy are the reference for everything below." The file is not in the repo, the local git has no branches (no `prototype/run-progress`), and a cloud session cannot open a claude.ai artifact.
- **Fix:** Commit the prototype HTML under `docs/context/design/` before M10, or state that the milestone text is complete and the prototype is optional.

### S18. Building the ZIP table can stall M03 with no way forward

- **Where:** `M03-tidy-up.md:107-109`.
- **What's wrong:**
  - **The required ZIPs may not be in the source.** M03:109 requires "11690 to 11697 are Queens". M03:107 says the first-choice source lists "11691 and 11697 under Queens", and M03:108 says "Never type the list from memory."
  - **The sandbox may not manage the sourcing.** Both source lists are online, and the step needs a local PDF text tool that the sandbox may not have.
  - **"Stop" halts everything.** "If no source can be reached, stop" holds up the other eleven audit fixes in M03 as well.
- **Fix:** Let Joe drop source extracts into `tools/data/`. Name which source wins for the ZIPs SPEC P-STD-3 requires (the spec can be the cited authority for those). Let the rest of M03 continue with only the ZIP-table test pending.

### S19. M11 asks for a claim test of a sentence that is false under M04

- **Where:** `M11-stages-01-05.md:68`.
- **What's wrong:** M11:68 says "`A blank required field sends the row to Fix problems.`" and "Each sentence is a claim with an engine-level test." Under M04, a blank Client_ID with a valid date of birth raises nothing and the row counts clean. H11 needs every claim to be true, so the test cannot pass as worded.
- **Fix:** Reword it, for example: "A row with no name, or with neither a Client ID nor a date of birth, goes to Fix problems and is not counted yet."

---

## Minor

### M1. Stale milestone pointers for the backup, the crosswalk, DPAPI and the M13 order

- **Where:** `M00-foundation.md:54`, `:164` and `:166`. `M01-reading.md:86` and `:161`. `M15-acceptance.md:13`.
- **What's wrong:**
  - M00:54 says "`sqlite3` (the saved crosswalk, M08) and ... `hashlib.scrypt` (the install secret backup, M08 and M09)", and M00:166 says "The scrypt backup format and the saved crosswalk (M08 and M09)". M00:164 says "DPAPI use (M08 and M09)", but M01 builds DPAPI.
  - M01:86 says "The backup file is M09", and M01:161 defers backup and crosswalk to M08 and M09. The README and M13 put all of them in M13.
  - M15:13 says "The README lists M13 ... after this milestone", which is false.
- **Fix:** Point each of these at M13 (backup, crosswalk) or M01 (DPAPI), and delete the M15 sentence.

### M2. M09's prefs.json question rests on a false premise

- **Where:** `M09-outputs.md:111`.
- **What's wrong:** M09:111 calls prefs.json "a question for Joe, since H9 lists no preferences file". SPEC 136 (H9) lists `prefs.json`.
- **Fix:** Cite H9 and drop the question.

### M3. Write targets outside H9's list

- **Where:** `M10-window.md:74`, `M11-stages-01-05.md:84`.
- **What's wrong:** M10:74 says that if a font fails, the app "writes an H8-safe line to the log". M09 says the package has no file log, so "the log" is undefined. M11:84 keeps the Group by choice "in the app settings file", which is not one of the settings H9 lists for prefs.json.
- **Fix:** Say "the in-memory run log" in M10. Add the Group by choice to H9's prefs list, or keep it in memory.

### M4. Dev-command output won't match M00's line regex

- **Where:** `M04-standardize.md:140`, against `M00-foundation.md:130`.
- **What's wrong:** M04's dev command prints "one `reason <id> <count>` line per reason ID". That does not match M00's `^[a-z_]+( [A-Z]+)? [0-9,]+$`, and unlike M02:101, M04 doesn't say to update the test.
- **Fix:** Tell M04 to widen the test's regex and the scope type to the closed set of reason IDs.

### M5. Two excepthooks and two error-text helpers

- **Where:** `M09-outputs.md:120`, `M10-window.md:197`, `M14-build-install.md:80`.
- **What's wrong:** M09 builds `errors.install_excepthook()` and `safe_error_text()`, which returns the class name, module and line. M10 builds `error_code()`. M14 builds `crash.py`, which "installs `sys.excepthook`".
- **Fix:** Have M14 extend M09's `errors.py` with M10's `error_code`, so only one hook exists.

### M6. M12 names a claims file M00 never built

- **Where:** `M12-stages-06-09.md:188`.
- **What's wrong:** M12:188 registers claims "in `wholecount/copy/claims.py`". M00 stores claims as a `claim` field in `wholecount/copy/en.toml`.
- **Fix:** Point M12 at M00's format.

### M7. M10 builds the QSS at a different time than the spec says

- **Where:** `M10-window.md:60`, against SPEC 889.
- **What's wrong:** M10 says `build_qss` "runs when the app starts (cached) and nothing generated is committed". SPEC 889 says "at build time".
- **Fix:** Make the two say the same thing.

### M8. M11 cites a function M03 doesn't define

- **Where:** `M11-stages-01-05.md:90`.
- **What's wrong:** M11:90 says "Dry-run sentences come from M03's `step_preview`." M03 defines `apply_steps` and `propose_steps`, not `step_preview`.
- **Fix:** Name the real function, or add `step_preview` to M08's session layer.

### M9. M11 asks for a kernel32 change that M00 already made

- **Where:** `M11-stages-01-05.md:56`.
- **What's wrong:** M11:56 says to "add `kernel32` to the guard's ctypes allowlist". M00:63 already has `DPAPI_DLL_NAMES = ("crypt32", "kernel32")`.
- **Fix:** Delete the M11 instruction.

### M10. M11's Windows check doesn't match the sample data

- **Where:** `M11-stages-01-05.md:170` and `:176`.
- **What's wrong:** M11 expects "Five files and nine tables" and tells Joe to pick up "`Res. Svcs`". The workbook has one sheet, M01's golden test finds five record tables, and no sample file contains "Res. Svcs".
- **Fix:** Rewrite the check from the real sample data, after B4 is settled.

### M11. The quality report has a file-name column that M09's A-03 test can be read to forbid

- **Where:** `M09-outputs.md:130`, against `:68`.
- **What's wrong:** M09:130 says "The summary and the quality report hold no Client_ID ... Unticked, no file name". The quality report has a `Source_File` column (M09:68).
- **Fix:** Limit the file-name clause to the summary.

### M12. M06's same-ID rule leaves out the nickname P-ID-3 allows

- **Where:** `M06-people.md:73`.
- **What's wrong:** DUP-3 checks that "surname, given name and DOB agree". P-ID-3 allows "given name (or nickname)". Bob and Robert Smith with one ID and one date of birth would be a conflict under DUP-3 and a join under ID-0.
- **Fix:** Say in DUP-3 whether nicknames agree.

### M13. The A-20 row can't match a single README milestone

- **Where:** `M00-foundation.md:136`.
- **What's wrong:** The INDEX test requires "the milestone matches the README table". The README lists A-20 under both M00 and M14.
- **Fix:** Allow a list in the INDEX test, or name one owner.

### M14. Hard-rule tests aren't where SPEC 13.2 wants them

- **Where:** SPEC 1106. `M15-acceptance.md:95`.
- **What's wrong:** SPEC 13.2 says "Each hard rule H1 to H16 has a named test module in `tests/invariants/` or `tests/offline/`." The planned tests for H7, H10, H11, H14, H15 and H16 live in `tests/audit`, `tests/rules`, `tests/copy` and `tests/ui`. M15's final check only confirms the named modules exist.
- **Fix:** Add thin `tests/invariants/test_hNN_*.py` modules, or relax SPEC 13.2.

### M15. M14's socket self-check conflicts with the build and the static scan

- **Where:** `M14-build-install.md:77`.
- **What's wrong:** M14 wants "`guard.denies_socket` (a connect attempt ... raises the guard's error)". The frozen build excludes `socket`, so the attempt raises ImportError, and an `import socket` in `wholecount/selfcheck.py` fails M00's static import scan.
- **Fix:** Have the check raise the audit event (`sys.audit("socket.connect", ...)`) or attempt the import through `importlib`, and expect the guard's error or an ImportError.

### M16. M05's "no seed anywhere" clashes with later milestones

- **Where:** `M05-geo.md:263`.
- **What's wrong:** M05:263 says "No `1337` or `seed` anywhere under `wholecount/`." M08:94 implements the spec's pick "seeded by the decision ID", and M13:83 uses a variable named `seed`. If Code turns the M05 line into a static test, later milestones fail it.
- **Fix:** Narrow the line to `wholecount/engine/geo/`, settings, copy and audit text, which is what test_B18 (d) already checks.

### M17. Milestones that need the internet have no stated fallback

- **Where:** `M00-foundation.md:46` and `:99-100`, `M14-build-install.md:15`.
- **What's wrong:** M00 needs PyPI for `pip-compile` and installs, and Python 3.12. M14 needs a GitHub remote with Actions and `gh` auth. Neither says what to do if the sandbox can't reach them.
- **Fix:** Add "If PyPI, Python 3.12 or GitHub Actions can't be reached, stop and put the question at the top of the report."

---

## Coverage of spec sections and P-rules

Every P-rule ID in SPEC 6 is built and has a test in the milestone that owns it:

| Rules | Milestone |
| --- | --- |
| P-READ-1 to 10 | M01, plus M04 for the second half of P-READ-3 |
| P-MAP-1 to 8 | M02 |
| P-PREP-1 to 5 | M03 |
| P-STD-1 to 8 and P-VAL-1 to 4 | M04 |
| P-GEO-1 to 9 | M05 (`test_P_GEO.py`, `_1_` to `_9_`), plus M08 for P-GEO-8 through Process |
| P-DUP-1 to 6 and P-ID-1 to 7 | M06 |
| P-PROG-1 to 6 | M07 |
| P-REV-6 | M08 and M09 |

The required sections each have a home:

| Section | Built and tested in |
| --- | --- |
| 5.1 keys and backup | M01, M13 |
| 5.3 master IDs | M06, M13 |
| 7.4 confidence | M08, M10, M12 |
| 8.6 corrections | M08, M09, M12 |
| 8.7 reviewers and bulk accepts | M08, M12 |
| 8.8 calibration | M13 |
| 9.1 to 9.4 outputs, logs, printable page, receipt | M09, M12 |
| 10.1 to 10.3 saved progress, resume, set-ups | M09, M11 |
| 10.4 staleness | M08 |
| 10.5 saved crosswalk | M13 |
| 11.3 frame | M10 |
| 11.6 to 11.8 progress, confidence on screen, data clarity | M10, M12 |
| 12.1 to 12.4 offline layers and tests | M00, M14 |
| 12.5 what can't be guaranteed | M15 |
| 12.6 open-file allowance | M00, M12 |
| 13.2 hard rule tests | M00 onward (location gap: M14 above) |
| 13.3 audit regression | every milestone |
| 13.4 parity checklist | M10 to M12, M15 |
| 13.5 acceptance | M15 (blocked by B4) |
| 13.6 Windows | M14 |
| 14 packaging and signing | M14 |

The gaps are the ones listed above:
- 13.2's test location (M14).
- Settings ownership for 11.3 (S9).
- The practice-run reading of 9.1 (S6).
- The two P-STD-5 reasons (S1).
- The example data for 13.5 (B4, S16).

---

## Coverage table: hard rules and High or Medium audit findings

### Hard rules

| Rule | Milestone | Tests | Note |
| --- | --- | --- | --- |
| H1 | M00, M14 | `tests/offline/test_guard_runtime.py`, `test_static_scan.py`, `test_import_graph.py`; `tests/bundle/test_bundle.py`; `tests_windows/test_firewall_probe.py` | |
| H2 | M00, M14 | `tests/offline/test_lockfile.py`, `test_static_scan.py::test_no_model_files_in_repo`; `tests/bundle/test_bundle.py::test_no_model_or_pickle_files_in_output_folder` | |
| H3 | M01, M08, M15 | `tests/invariants/test_read_determinism.py`, `tests/invariants/test_determinism.py`, `tests/acceptance/test_determinism.py` | |
| H4 | M01, M08 | `tests/invariants/test_row_accounting_h4.py`, `tests/invariants/test_balance.py`, `test_counts_refuse_when_unbalanced.py` | |
| H5 | M06 | `tests/invariants/test_identity_properties.py`, `tests/audit/test_C01_auto_join_score.py` | name-based key gap, S4; crosswalk gap, S5 |
| H6 | M03, M04 | `tests/rules/test_steps_model.py`, `tests/invariants/test_standardize_properties.py`, `tests/audit/test_A11_original_kept.py` | |
| H7 | M09, M12 | `tests/audit/test_A10_no_typed_values.py`; M12 QLineEdit allowlist static test (file not named) | not in invariants or offline (M14) |
| H8 | M01, M04, M09, M10 | `tests/invariants/test_h08_progress_message.py`, `tests/invariants/test_h8_standardize.py`, `tests/audit/test_A02_audit_has_no_values.py`, `test_C22_audit_tokens.py` | accept note risk, S14 |
| H9 | M01, M09, M13 | `tests/invariants/test_h09_secret_not_leaked.py`, `tests/audit/test_A04_disk_writes.py`, `test_xw_privacy.py` | thresholds file, S8 |
| H10 | M01, M09 | `tests/rules/test_P_READ_9_sensitive.py`, `tests/audit/test_A01_unmapped_columns.py` | not in invariants or offline (M14) |
| H11 | M00 | `tests/copy/test_claims_have_tests.py` | false claim, S19 |
| H12 | M01, M08 | `tests/invariants/test_key_stability.py`, `test_record_key_stability.py`, `tests/audit/test_C07_decisions_survive.py`, `test_C08_keep_copy_after_reexport.py` | |
| H13 | M08 | `tests/audit/test_C18_stale_after_setup_change.py`, `tests/invariants/test_staleness.py` | |
| H14 | M10, M12 | `tests/ui` Progress tests (file not named) | not in invariants or offline (M14) |
| H15 | M08, M10 | `tests/rules/test_CONF_74.py`, M10 confidence threshold test | not in invariants or offline (M14) |
| H16 | M00 | `tests/copy/test_lint.py` | fails on M00 file as written, B2 |

### High and Medium audit findings

All tests are in `tests/audit/` unless a path is given.

| ID | Severity | Milestone | Test | Note |
| --- | --- | --- | --- | --- |
| A-01 | High | M09 | `test_A01_unmapped_columns.py` | |
| A-02 | High | M09 | `test_A02_audit_has_no_values.py` | |
| A-03 | High | M09 | `test_A03_summary_counts_only.py` | M11 |
| A-04 | High | M09 | `test_A04_disk_writes.py` | |
| A-05 | High | M06 | `test_A05_same_id_merge.py` | |
| A-06 | High | M08 | `test_A06_final_wording.py` | fixture case wrong, S13 |
| A-07 | High | M08 | `test_A07_preview_is_read_only.py` | |
| A-08 | High | M09 | `test_A08_resume_restores_all.py` | |
| A-09 | High | M01 | `test_A09_rows_outside_tables.py` | |
| A-10 | High | M09 | `test_A10_no_typed_values.py` | |
| A-11 | Medium | M04 | `test_A11_original_kept.py` | |
| A-12 | Medium | M08 | `test_A12_goal2_range_wording.py` | |
| A-13 | Medium | M01 | `test_A13_bad_file_does_not_block.py` | |
| A-14 | Medium | M05 | `test_A14_seed_printed.py` | |
| A-15 | Medium | M09 | `test_A15_no_value_logs.py` | |
| A-16 | Medium | M10 | `test_A16_no_auto_close.py` | |
| A-17 | Medium | M14 | `test_A17_no_process_killing.py`, `tests_windows/test_uninstall_closes_only_wholecount.py` | |
| A-18 | Medium | M11 | `test_A18_drop_files.py` | |
| A-19 | Medium | M10 | `test_A19_saved_card_stage.py` | |
| A-20 | Medium | M00, M14 | `test_A20_no_launchers.py`, `test_A20_installer_offline.py` | both fail as written, B1 and B3 |
| B-01 | High | M04 | `test_B01_placeholders.py` | |
| B-02 | High | M01 | `test_B02_cp1252_names.py` | |
| B-03 | High | M04 | `test_B03_nassau_zips.py` | |
| B-04 | High | M04 | `test_B04_non_nyc_zip.py` | |
| B-05 | High | M04 | `test_B05_non_nyc_place_names.py` | |
| B-06 | High | M03 | `test_B06_calculated_zip.py` | |
| B-07 | High | M03 | `test_B07_nine_digit_zip.py` | |
| B-08 | High | M03 | `test_B08_street_keeps_concourse.py` | |
| B-09 | High | M03 | `test_B09_spaced_hyphen_house_number.py` | |
| B-10 | High | M03 | `test_B10_trailing_segment_kept.py` | |
| B-11 | High | M03 | `test_B11_particles_and_double_surnames.py` | |
| B-12 | High | M03 | `test_B12_titles_and_suffixes.py` | |
| B-13 | High | M02, M04 | `tests/rules/test_P_MAP_5_date_order.py`, `test_B13_day_month_order.py` | |
| B-14 | High | M04 | `test_B14_two_digit_year.py` | |
| B-15 | High | M04 | `test_B15_future_dob.py` | |
| B-16 | High | M04 | `test_B16_five_digits_not_a_date.py` | |
| B-17 | High | M05 | `test_B17_fuzzy_geocode.py` | |
| B-18 | High | M05 | `test_B18_privacy_offset.py` | |
| B-19 | High | M05 | `test_B19_district_holes.py` | |
| B-20 | High | M07 | `test_B20_unconfirmed_proposals.py` | |
| B-21 | High | M02 | `test_B21_first_match_by_position.py` | |
| B-22 | High | M02 | `test_B22_program_date_and_id.py` | |
| B-23 | High | M02, M03 | `test_B23_split_does_not_hijack.py`, `test_B23_end_to_end.py` | |
| B-24 | Medium | M01, M04 | `test_B24_invisible_characters.py`, `tests/rules/test_P_READ_3_unreadable_character.py` | |
| B-25 | Medium | M04 | `test_B25_name_placeholders.py` | |
| B-26 | Medium | M04 | `test_B26_unicode_zip.py` | |
| B-27 | Medium | M04 | `test_B27_address_text_disagrees.py` | |
| B-28 | Medium | M04 | `test_B28_place_stays_out_of_street.py` | |
| B-29 | Medium | M03 | `test_B29_unit_then_city.py` | |
| B-30 | Medium | M03 | `test_B30_lone_letter_units.py` | |
| B-31 | Medium | M04 | `test_B31_unrecognized_city_kept.py` | |
| B-32 | Medium | M03 | `test_B32_extra_name_tokens.py` | |
| B-33 | Medium | M03 | `test_B33_middle_initial_placeholders.py` | |
| B-34 | Medium | M05 | `test_B34_fill_proposals.py` | |
| B-35 | Medium | M05 | `test_B35_verified_label.py` | |
| B-36 | Medium | M06 | `test_B36_same_id_across_files.py` | |
| B-37 | Medium | M06 | `test_B37_identical_record.py` | |
| B-38 | Medium | M06 | `test_B38_saved_copy_decision.py` | |
| B-39 | Medium | M06 | `test_B39_accent_folding.py` | |
| B-40 | Medium | M07 | `test_B40_program_proposals.py` | |
| C-01 | High | M06 | `test_C01_auto_join_score.py` | |
| C-02 | High | M06 | `test_C02_same_system_id.py` | |
| C-03 | High | M08 | `test_C03_process_stale_identity.py` | |
| C-04 | High | M08 | `test_C04_undo_refresh.py` | |
| C-05 | High | M07 | `test_C05_fast_vs_staged.py` | |
| C-06 | High | M08, M09 | `test_C06_corrections_by_record_key.py`, `test_C06_corrections_file_level.py` | |
| C-07 | High | M08 | `test_C07_decisions_survive.py` | |
| C-08 | High | M08 | `test_C08_keep_copy_after_reexport.py` | |
| C-09 | High | M08 | `test_C09_every_problem_kind_opens.py` | |
| C-10 | High | M05, M08 | `test_C10_gazetteer_crash.py`, `tests/rules/test_P_GEO_8_through_process.py` | |
| C-11 | High | M09 | `test_C11_every_row_kind_exports.py` | |
| C-12 | Medium | M08 | `test_C12_goal2_range.py` | |
| C-13 | Medium | M07 | `test_C13_ungroup_own_name.py` | |
| C-14 | Medium | M08 | `test_C14_one_undo_stack.py` | |
| C-15 | Medium | M08 | `test_C15_three_files_partition.py` | |
| C-16 | Medium | M08 | `test_C16_keep_one_per_program.py` | depends on the S3 ruling |
| C-17 | Medium | M06 | `test_C17_client_id_scope.py` | |
| C-18 | Medium | M08 | `test_C18_stale_after_setup_change.py` | |
| C-19 | Medium | M07 | `test_C19_without_program.py` | |
| C-20 | Medium | M06 | `test_C20_master_id_stability.py` | |
| C-21 | Medium | M06 | `test_C21_identity_verdict_audit.py` | |
| C-22 | Medium | M09 | `test_C22_audit_tokens.py` | |
| C-23 | Medium | M01 | `test_C23_blank_line_and_comma_row.py` | |
| C-24 | Medium | M06 | `test_C24_address_key.py` | |

Nothing is MISSING. All 84 High and Medium findings have a named test. Of those, A-20 has two tests that fail as written (B1, B3), and A-06 has a test whose described case doesn't arise under 1.1 (S13).

---

## Resolution

Applied on 2026-10-30 against the updated SPEC.md. Only files in `docs/milestones/` (M00 to M15) were edited. SPEC.md, CLAUDE.md and `docs/milestones/README.md` were left alone. The coverage tables above show the plan before these fixes. Since then the two A-20 tests can pass as written, and the A-06 test describes a 1.1 case.

### Blockers

- **B1:** M00's `test_A20_no_launchers.py` now checks imports and calls by AST and ignores strings and comments. It exempts `tools/offline_rules.py`, `tools/offline_scan.py` and `wholecount/guard/`, and has a negative control.
- **B2:** M00 section 7 now points at `wholecount/copy/us_spelling.txt` and writes no British words.
- **B3:** M14's `test_A20_installer_offline.py` now scans only these:
  - `installer/`
  - `build/wholecount.spec` and `build/rthook_offline.py`
  - the shipped `wholecount/**/*.py`
  - the PowerShell scripts

  A second pass checks every other file against a named provenance allowlist: `tools/make_zip_table.py`, the `nyc_zips.csv` source column, `tools/make_district_files.py`, `tools/offline_rules.py`, `build/spec_lists.py`, the fonts `SOURCE.txt`, `signing.json` and `tools/sandbox/`. M03 and M10 point at it.
- **B4:** example data now follows P-GEO-4a in every milestone:
  - **M01** builds `tools/make_example_data.py` (seeded, with `--check`), the five example files in `wholecount/sample_data/`, and `EXPECTED.json` with one section per milestone. Legacy samples move to `tests/data/legacy_sample/` for reading tests only.
  - **M02, M03 and M04** add golden tests on the example files against `EXPECTED.json`.
  - **M05** writes `sample_reference.csv` into `wholecount/sample_data/` and fills `locations`.
  - **M09, M11, M12, M14 and M15** read `EXPECTED.json` in their tests and in every Windows check that uses example data.

### Should fix

- **S1:** M04 changes these:
  - It sets `outside_nyc` from a non-NY state only when the ZIP isn't an NYC ZIP.
  - It adds `state_zip_disagree` and `address_incomplete` to the binding reason list.
  - It rewrites the state bullet and the address check, and updates the B-44 and P-STD-5 tests.
  - It drops the logged decision.
- **S2:** M02 sections 1 and 4 now state the Client_ID-or-DOB rule and the `needed_to_count` rule. The B-22 and schema tests follow.
- **S3:** open copy groups now stay counted and widen the range:
  - **M08** keeps their rows counted and adds `open_copy_groups` to `Counts`, COUNT-1 and COUNT-2. A range is never final, which is logged as question (1). The tab is renamed Affects the counts.
  - **The R fixture** base state is recomputed: 13 counted, 3 not counted yet, Goal 1 and Goal 2 9 to 11, and Housing 3 to 4. The C-12 and C-16 tests, A-06 and `session-demo` are updated to match.
  - **M04's** P-VAL-3 test allows M06's same-ID kind and never a copy kind.
  - **M06** adds ID-13 and `open_copy_groups` to `resolve`.
  - **M09's** base numbers become 13 clean and 11 people.
  - **M10 and M12** wording now covers open copy groups.
- **S4:** M06 changes ID-0, DUP-4 and DUP-7 so a name-based key never joins rows on its own. Those rows use the `row` key mode, and `NotCopies` is allowed on them. `test_ID_0_name_key_never_joins.py` is added, and M08's runner applies the key modes.
- **S5:** the `earlier_batch` reason is now built and tested:
  - **M06** adds `earlier_batch` to `AutoJoin`, `how` and `linked_at` to `KnownMaster`, and `released` to `IdentityResult`. Rules ID-6 and ID-8 apply them, with `test_ID_8_earlier_batch.py`.
  - **M13** follows in XW-4, XW-5, XW-6 and XW-8, with `test_xw_earlier_batch.py`.
  - **M12** shows the third join reason.
- **S6:** practice runs now match SPEC 9.1 everywhere:
  - **M09** changes OUT-7 and OUT-10 and adds the copy `outputs.practice.no_maps`.
  - **M12** changes the Download list, its chips and tests, and Windows check 9.
  - **M15** changes guide section 5.
  - **M05** marks question (1) as settled.
- **S7:** M11's `SetupsPanel` exports plain JSON with the contents note.
- **S8:** M13 CAL-7 stores thresholds in `prefs.json`. The scans and questions follow.
- **S9:** M10 builds the Settings link and drawer, with Depends on, the footer and Out of scope corrected. M13 adds cards only and drops question (6).
- **S10:** M01's progress types are now the only ones:
  - **M01** holds the single `ProgressMessage`, `StepRef(step)` and the 16-name `Step` enum.
  - **M10** reuses them, keys `jobs/steps.py` on the enum, adds the `backup` action, and passes a dict in its test.
  - **M13** adds no step.
- **S11:** M09 OUT-13 moves the gate into `session/export.py` `download()`, and the engine writer takes plain inputs. M13 commits after `download()`.
- **S12:** M08 REV-2 adds `Cause.kind`, `tab`, `diagnose_mapping` and `people_in_other_files`, with `test_REV_2_cause_kinds.py`. M12 points at them.
- **S13:** M08's `test_A06_final_wording.py` uses an added blank-name row (H400) and keeps H300 as the location-only case.
- **S14:** M08's `AcceptProof` has no note, M12's `AcceptDialog` has no note box, and the `review.accept.note` copy row is gone.
- **S15:** M15's `test_independent_counts.py` compares the file and row pairs in Source_Records and reads each file's system from `EXPECTED.json`.
- **S16:** example data lives in `wholecount/sample_data/` from M01, and the sample reference from M05. M14 adds the `.tsv`, `.xlsx` and `.xml` patterns, checks the files ship, and takes self-check counts from `EXPECTED.json`.
- **S17:** M10 and M12 point at `docs/context/design/prototype/progress-confidence.html` and say the milestone text wins.
- **S18:** M03 cites the ZIPs the spec names to SPEC P-STD-3 and reads Joe's extracts from `tools/data/`. If sourcing fails, only the ZIP-table tests stay pending.
- **S19:** M11's claim now reads "A row with no name, or with neither a Client ID nor a date of birth, goes to Fix problems and isn't counted yet."

### Minor

- **M1:** M00, M01 and M15 now name M13 for the backup and crosswalk, and M01 for DPAPI. M15 no longer says M13 comes after it.
- **M2:** M09 STORE-3 cites H9 for `prefs.json` and drops the question.
- **M3:** a font failure in M10 goes to the in-memory run log. M11 keeps the Group by choice in `prefs.json` as a view choice (H9).
- **M4:** M04 widens M00's dev-output test for `reason <id> <count>` lines.
- **M5:** M09's `install_excepthook()` is the only hook, and M14's `crash.py` extends it.
- **M6:** M12 registers claims in M00's `en.toml` format.
- **M7:** M10 cites SPEC 11.2 and adds a test that the QSS in use matches the tokens.
- **M8:** M11 adds `session.preview_step`, built on M03's `apply_steps`.
- **M9:** M11 notes `kernel32` is already allowed and drops the guard change.
- **M10:** M11's Windows checks use the example files and `EXPECTED.json`.
- **M11:** M09's A-03 test limits the file-name clause to the summary.
- **M12:** M06 DUP-3 accepts nicknames.
- **M13:** M00's INDEX test and `INDEX.md` let A-20 list M00 and M14.
- **M14:** M00's `HARD_RULES.md` text and M15's final test follow the relaxed SPEC 13.2.
- **M15:** M14's socket self-check raises the audit event instead of importing `socket`.
- **M16:** M05 narrows the "no seed" check to the geo engine, settings, copy and audit text.
- **M17:** skipped, because Joe is adding it to the README.

### Left open

- SPEC.md line 562 still heads P-ID-3 with "Joining without asking happens for two named reasons only". CLAUDE.md line 25 still says "the two named reasons in P-ID-3". H5 and the P-ID-3 list now give three. Both files were outside the edit scope.
