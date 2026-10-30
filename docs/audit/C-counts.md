# Crosswalk audit C: counting and state logic

Scope: Goal 1 (unique clients), Goal 2 (unique clients per program), the row balance, review decisions, undo, sessions, exports and the audit trail of the existing Python app. The old code was not fixed. Everything below was run against a copy (`scratchpad/src/agentC`), driven through FastAPI `TestClient` against `crosswalk_server.api`, the same way the existing tests do.

Totals: 27 findings. High 11, Medium 13, Low 3.

Severity as briefed: High = wrong Goal 1 or Goal 2, broken balance, wrong auto-link, or a decision applied to the wrong row. Medium = a screen number that disagrees with an export, or stale state the user can see. Low = cosmetic. The scale does not name crashes. I rated a crash High when it blocks a screen or an output the workflow needs (C-09, C-10, C-11) and said so in each.

## How to reproduce

```
cd /tmp/claude-0/-home-claude/ec68250d-d5ac-549e-8d94-20759c381437/scratchpad/audit/C-scripts
. /tmp/claude-0/-home-claude/ec68250d-d5ac-549e-8d94-20759c381437/scratchpad/venv-old/bin/activate
python s10_stale_identity_rerun.py        # any script named in a Proof line
```

Logs of every run quoted below are in `C-scripts/out/<script>.txt`. Harness notes: `cwlib.py` holds the helpers; `counts_line()` prints what the Results screen shows (cached identity); `counts_line(True)` clears the identity cache first, which is how a from-scratch computation is obtained. Where a number is stale because of the cache (C-03, C-04), both are shown.

## Index

| ID | Sev | Title |
|---|---|---|
| C-01 | High | Any pair scoring 100 or more is joined automatically, and no screen lists the joins |
| C-02 | High | The same-system identifier rule contradicts the ID-conflict review and depends on coincidence |
| C-03 | High | Process leaves the cached identity in place, so Goal 1, Goal 2 and Unique_Clients describe the previous run |
| C-04 | High | Undo does not refresh identity: Goal 1, Goal 2 and Unique_Clients keep the undone rows |
| C-05 | High | The fast path never builds the program-name map, so Goal 2 is higher than the same files give stage by stage |
| C-06 | High | A corrections file is applied by row position and overwrites other people when the source is re-ordered |
| C-07 | High | Process, Preview and the fast path silently discard all review decisions; resume says they were restored |
| C-08 | High | "Keep this copy" is stored as a row number, so after a re-export the opposite row is kept |
| C-09 | High | The review screen returns 500 whenever a required field is blank (crash) |
| C-10 | High | Process fails with TypeError whenever an address is found in the gazetteer (crash) |
| C-11 | High | Manual_Review_Needed cannot be exported when any summary row exists (crash) |
| C-12 | Medium | Goal 2 has no range while pairs are open |
| C-13 | Medium | Taking a program name out of a group does nothing when it is the group's own name |
| C-14 | Medium | Undo removes only the last group decision; row decisions cannot be undone and are left behind |
| C-15 | Medium | Manual_Review_Needed also lists set-aside rows, so the three files add up to more than the input |
| C-16 | Medium | "Keep one per program" marks clean rows removed; they stay in Final_Clean_Mapped and the audit says they were set aside |
| C-17 | Medium | Client_ID duplicates are checked across all files, not within one file, so unrelated systems flood review |
| C-18 | Medium | Set-up changes after a run leave Results, exports and audit disagreeing, and nothing says the results are out of date |
| C-19 | Medium | "Without a program" counts records but says persons |
| C-20 | Medium | Master_ID renumbers when any identity verdict changes |
| C-21 | Medium | Identity verdicts (same person / different people) are not in the audit trail |
| C-22 | Medium | The audit trail carries values: unit numbers, cities and ZIP codes |
| C-23 | Medium | Rows in a table the tool left out are invisible to the balance, which cannot fail |
| C-24 | Medium | The address key ignores street type, so "address matches" is stated for different streets |
| C-25 | Low | Jitter comes from one shared stream: any change moves other rows, and one address gets different points |
| C-26 | Low | The Download screen has no chip for Resolution_Status, which the clean file carries |
| C-27 | Low | Row order of Final_Clean_Mapped and Manual_Review_Needed follows upload order |

---

## High

### C-01. Any pair scoring 100 or more is joined automatically, and no screen lists the joins
- Severity: High
- Steps: Upload two files (`fixtures.py`: 12 rows, 10 real people, including twins Jordan and Jaden Smith at one address, Robert Smith and Robert Smith Jr at one address, Ana Perez with day and month swapped in the DOB, two Luis Diaz on 45th St and 45th Ave). Map DOB as a custom field. Process. Open Results.
- Got: Goal 1 = 7, Goal 2 = 9, 0 open pairs, and the green band "Nothing is left to decide, so this count is final. 5 link(s) were joined on evidence that could not reasonably be coincidence". Five pairs were joined without asking: twins (102 points, evidence "date of birth, surname, address"), Jr and Sr (112), Luis Diaz (128), plus Maria Rodriguez (128) and Ana Perez (112), which are right. No screen lists the five pairs or lets a person split one. At unit level, other auto-joins by score: same name and DOB, different street, same ZIP (104); Bill and William, same DOB, same ZIP, different street (100); DOB year typo (112).
- Expected: The spec ("Joining without asking") allows an automatic join in exactly two cases: the same identifier in one system, or date of birth exact AND surname AND given name AND address all present. Twins (given names differ), Jr and Sr (DOB differs), swapped DOB, and "different street, same ZIP" are not either case, so they must be proposals. With the spec's own test applied in memory (`s32`), the same files give Goal 1 settled 10, range 7 to 10, 3 open pairs for a person to decide. Truth for the fixture is 10 people and 11 person-program pairs.
- Where: `identity.py:436-448` `_is_auto`, line 442 `if pts >= WEIGHTS["same_system_id"]: return True`. `score_pair` returns the constant 100 for a same-system identifier (`identity.py:374-377`), and the threshold test was evidently meant to catch only that; any pair whose weights add to 100 or more passes it. `resolve` joins on it at `identity.py:522`. The false reassurance is `ui/app.js:2123-2125`.
- Proof: `s02_identity_auto.py`, `s03_identity_e2e.py`, `s32_expected_with_strict_rule.py`.
  ```
  s02  TWINS: Jordan/Jaden Smith same DOB same address   pts=102 auto=True people=1 open_proposals=0 truth=2 people
  s02  JR/SR: Robert Smith 1962-03-14 vs Jr 1992-03-14   pts=112 auto=True people=1 open_proposals=0 truth=2 people
  s02  same name+DOB, different street, same ZIP         pts=104 auto=True people=1 open_proposals=0
  s03  G1 settled=7 low=7 high=7 open=0 | G2=9 ...       truth: 10 people
  s03  Goal 1 reported: {'count': 7, 'open': 0, 'auto': 5, 'confirmed': 0}
  s32  as shipped          : G1 settled=7 low=7 high=7 open=0 | G2=9
  s32  spec rule in memory : G1 settled=10 low=7 high=10 open=3 | G2=12
  ```
  (One of the Jr/Sr cases only reaches 112 because 1962 and 1992 differ by one digit; 1958 vs 1985 scores 66 and is correctly only a proposal. So the loophole fires by accident of the dates.)
- Rewrite requirement: An automatic join must be a named reason returned by the matcher (`same_system_id` or `four_exact_facts`), never a score threshold. Every automatic join must be listed on a screen with its evidence and a "these are different people" action. Test: load `fixtures.py`; assert twins, Jr/Sr and swapped-DOB pairs are proposals, Goal 1 is shown as 7 to 10 with 3 open, and the screen lists the 2 automatic joins by name.

### C-02. The same-system identifier rule contradicts the ID-conflict review and depends on coincidence
- Severity: High
- Steps A (`s24`): One file, Client_ID 77 on Ana Perez (b. 1990, 7 Elm St) and Beth Perez (b. 1994, 55 Oak Ave, same ZIP), plus Carl Ng. Process. In the review group "One identifier used for records that do not match" press accept all. Open Results.
- Steps B (`s21`, case c): One file, Client_ID 500 on "Maria Lopez, Bronx 10451" and "Maria Garcia, Brooklyn 11201", no DOB. Process, accept all.
- Got A: the tool first says the two rows "do not match", the reviewer lets them in as entered, then identity joins them anyway on "the same one.csv identifier 77" (100 points). Goal 1 = 2, 0 open, and no screen shows the join. The only way out is the API (`/api/identity/decide` with `different` gave Goal 1 = 3); the UI never calls it for an automatic join.
- Got B: the same situation with different fields, and Goal 1 = 2 with no join and no proposal. The pair is never scored because it shares no blocking key, so the "decisive" same-identifier rule never runs.
- Expected: One answer for both: a reused identifier in one system is either always a join or always a question to a person, and the reviewer's ID-conflict decision must reach the identity step. The spec says the identifier is "decisive on its own" at 100 points, and also (Tier 1) that the same identifier with different data is "an integrity problem, not a safe merge".
- Where: `identity.py:374-377` (rule), `identity.py:300-345` `blocking_keys` has no key for Client_ID so the rule only runs when another key coincides, `identity.py:493-505` (only blocked pairs are scored), `crosswalk_server.py:2356-2388` `_person_records` (system = file name before " :: "), `app.py:2389-2413` (Tier 1).
- Proof: `s24_id_reuse_e2e.py`, `s21_client_id_scope.py`.
  ```
  s24  after Process : G1 settled=1 ... rows={'input': 3, 'clean': 1, 'review': 2, 'aside': 0}
  s24  reviewer accepts : G1 settled=2 low=2 high=2 open=0 | G2=2   (truth: 3 people)
  s24  auto_links : [(('one.csv :: A1:I4||0', 'one.csv :: A1:I4||1'), 100, ['the same one.csv identifier 77'])]
  s24  API-only 'different' -> G1 settled=3
  s21c after the reviewer accepts them as entered: G1 settled=2 ... open=0   (no pair offered either)
  ```
- Rewrite requirement: Index same-system identifier pairs directly (by system and ID), do not rely on blocking. Decide one policy (recommended: a reused ID is strong evidence that goes to a person as a proposal) and feed the ID-conflict verdict into it. Test: s24 and s21c fixtures must give the same kind of outcome (both proposals, or both joined), and accepting the ID group must never produce a join the reviewer cannot see.

### C-03. Process leaves the cached identity in place, so Goal 1, Goal 2 and Unique_Clients describe the previous run
- Severity: High
- Steps: Messy 3-file fixture, Process, open Results (identity is computed and cached). On Sources exclude C.csv. Process again. Open Results. (`s10`)
- Got: rows received 78, clean 70, but Goal 1 = 70 and Goal 2 = 84, the numbers of the first run that still included C.csv. Unique_Clients covers 86 source rows while Final_Clean_Mapped has 70, so people from the excluded file are in the exports.
- Expected: Goal 1 = 55, Goal 2 = 69 (a from-scratch computation of the same state), Unique_Clients covering 70 rows.
- Where: `crosswalk_server.py:830-846` `_run_thread` and `1641-1660` `run_start` and `1705-1727` `express_run` never reset `S["identity"]`; `_resolve_identity` (`:2391-2404`) returns the cache until something clears it; only `_recompute` (`:857`) and the decision handlers do.
- Proof: `s10_stale_identity_rerun.py`
  ```
  A. first run         : G1 settled=70 ... G2=84 ... rows={'input': 94, 'clean': 86, 'review': 8}
  B. C.csv excluded + Process again: G1 settled=70 ... G2=84 ... rows={'input': 78, 'clean': 70, 'review': 8}
      FAIL -> COUNTED ROWS: Unique_Clients covers 86 source rows but Final_Clean_Mapped has 70
  C. same state, identity recomputed from scratch: G1 settled=55 ... G2=69 ...
  ```
- Rewrite requirement: Identity is a pure function of (accepted rows, identity verdicts), stored with the run it came from and recomputed when either changes; there is no separate cache to forget. Test: Process, read counts, change the inputs, Process, assert the counts and the Unique_Clients rows equal a fresh process of the same inputs.

### C-04. Undo does not refresh identity: Goal 1, Goal 2 and Unique_Clients keep the undone rows
- Severity: High
- Steps: Messy fixture, Process, accept all on the ID-conflict group, press Undo. (`s34`, `s06`)
- Got: rows go back (clean 86, review 8) but Goal 1 stays 71 and Goal 2 86. Unique_Clients covers 88 source rows while Final_Clean_Mapped has 86.
- Expected: Goal 1 = 70, Goal 2 = 84, exactly the numbers before the decision. The spec says undo is a pop.
- Where: `crosswalk_server.py:1955-1966` `review_undo`: `S["identity"]` is cleared only through `_recompute()`, and only in the one case where the popped decision is an approved `conflict` group.
- Proof: `s34_undo_stale.py`, `s06_sequence_decisions.py`
  ```
  0 after Process                   : G1 settled=70 ... G2=84 ... clean 86
  1 after 'accept all' on idconflict: G1 settled=71 ... G2=86 ... clean 88
  2 after Undo, as the screen shows : G1 settled=71 ... G2=86 ... clean 86
  2 same state, computed from scratch: G1 settled=70 ... G2=84 ... clean 86
  s06 [1u] FAIL -> COUNTED ROWS: Unique_Clients covers 88 source rows but Final_Clean_Mapped has 86
  ```
- Rewrite requirement: Same as C-03: derived counts must follow the state, not a cache. Test: for every decision type (group, row, bulk, keep one, identity verdict, program grouping), apply then undo, and assert the counts and all seven exports are byte-identical to the state before.

### C-05. The fast path never builds the program-name map, so Goal 2 is higher than the same files give stage by stage
- Severity: High
- Steps: Two files; A.csv has Ana in "Workforce Development" and Bo in "Youth", B.csv has Ana in "Workforce Dev." and Bo in "youth". Run once stage by stage (opening the Programs screen as the UI does), once with `POST /api/express/run`. (`s12`)
- Got: staged Goal 2 = 2; fast Goal 2 = 4. Unique_Clients_By_Program has 2 rows staged and 3 fast (Ana split across two spellings). Final_Clean_Mapped loses the "Group 1 / Group 2" Possible_Duplicate labels on the fast path because the program is part of the person key. The audit lacks the "Program names grouped:" section. The same gap exists for any run where the Programs screen was not opened: Goal 2 = 5 instead of 3 (`s11` case e); opening the screen and running again gives 3.
- Expected: The two paths produce identical numbers and files (the spec says the fast path "keeps the tidy-up steps and the column matching the tool proposed", i.e. the same result). On the 266-row sample files they do match (see "Checked and correct"), because those spell programs consistently.
- Where: `crosswalk_server.py:2321-2353` `_program_group_state` is the only builder of `S["program_aliases"]` and is called only from the Programs endpoints; `:818` passes `S["program_aliases"] or None` to the pipeline; `express_run` (`:1705-1727`) never calls it.
- Proof: `s12_fast_vs_staged.py`, `s12b_audit_diff.py`, `s11_goal2_edges.py`
  ```
  == program spellings
     staged: G1 settled=2 ... G2=2 ...
     fast  : G1 settled=2 ... G2=4 ...
     Unique_Clients_By_Program  identical=False   -M000001,Workforce Dev.,Ana,...,A.csv; B.csv,A1; B1,2
                                                  +M000001,Workforce Dev.,Ana,...,B.csv,B1,1
                                                  +M000001,Workforce Development,Ana,...,A.csv,A1,1
  s11 (e) Programs screen never opened: G2=5 ... per-program: {'Housing': 1, 'Workforce Dev.': 1, 'Workforce Development': 1, 'Youth': 1, 'youth': 1}
  ```
- Rewrite requirement: Program normalization is part of Process, computed from the data (plus a person's saved grouping) so no screen visit is required; fast and staged call the same function. Test: for fixtures with mixed spellings, both paths give byte-identical exports apart from timestamps; Goal 2 never depends on which screens were opened.

### C-06. A corrections file is applied by row position and overwrites other people when the source is re-ordered
- Severity: High
- Steps: Process the messy fixture, export Manual_Review_Needed, fix the blank ZIP of A900, keep the file. Next day the source system exports A.csv sorted by last name (same rows, same count, same table range). Add the files, upload the corrections file, Process. (`s09`; baseline `s29`)
- Got: 6 raw rows were overwritten with values meant for other rows (row 10 was A007 Hana Alvarez, now A010 Kira Alvarez; row 40 was A037 Rex Brown, now A900 Zed Zimmer; and so on). The original clients at those positions are gone from the data. A900 itself still sits unfixed at its new position (rows `['A900','11201']` and `['A900','']`). Counts: Goal 1 70 to 67, Goal 2 84 to 80, clean 86 to 82, review 8 to 12. The audit records "values replaced" for the rows now at positions 10 and 40 and never mentions that a different client was there.
- Got (variant, `s08` part c): the source gains one client at the top, so the table range changes (`A1:I48` to `A1:I49`); the corrections no longer match the table, are not applied, and neither the screen nor the audit says so (`audit lines for corrected rows: []`).
- Expected: Corrections apply to the row they were exported from, found by identifier (the spec: "applied as corrections by identifier"), and a correction that does not match exactly one row is reported, never applied elsewhere.
- Where: `app.py:3349-3372` `parse_corrections_frame` (address = Source_File + Source_Row), `app.py:3381-3418` `apply_corrections` (`df.iat[r, ci]` on the raw frame), `crosswalk_server.py:711` `_collect_corrections_meta_and_patch`.
- Proof:
  ```
  s29  sorted A.csv, no corrections file: G1 settled=70 ... G2=84 ... {'clean': 86, 'review': 8}
  s09  rows of the raw frame that were overwritten by the corrections file: 6
       row 40: was A037 'Rex Brown' -> now A900 Zed Zimmer zip 11201
       row 44: was A902 'Xi Xu'     -> now A003 Devi Alvarez zip 11201
  s09  summary: G1 settled=67 ... G2=80 ... rows={'input': 94, 'clean': 82, 'review': 12}
  ```
- Rewrite requirement: Key each correction by (source system, Client_ID, hash of the original values already carried in the `orig::` columns); refuse and list any correction that matches zero or several rows. Test: re-export sorted, apply the corrections file, assert only the A900 row changed, counts equal the unsorted run with the fix, and an unmatched correction appears in a visible list.

### C-07. Process, Preview and the fast path silently discard all review decisions; resume says they were restored
- Severity: High
- Steps A (`s30`): make 4 review decisions (3 group decisions, 1 row approval). Then (1) open Programs and press Preview, or (2) press Process again with nothing changed, or (3) run the fast path.
- Steps B (`s15`): same decisions plus one identity verdict and a confirmed program grouping; restart; resume the saved session; add the files again; Process.
- Got A: decisions held 4, afterwards 0 in all three cases; clean 89 back to 86, review 3 back to 8, Goal 1 72 back to 70. No warning.
- Got B: the resume reply says `{'ok': True, ..., 'decisions': 4}`; after Process there are 0. The identity verdict, program grouping and alias map and held corrections files are not saved at all (`id_decisions: 1 -> 0`, `program_groups: 4 -> None`). Resumed numbers: Goal 1 73 (range 72 to 73, 1 open) vs 74; Goal 2 88 vs 89; clean 90 vs 93; review 8 vs 3; aside 0 vs 2. The same wipe makes the corrections-file workflow (`s08`) drop every earlier decision: `actions after Process: 0`, all groups back to pending.
- Expected: The spec: "Sessions save progress between launches: the set-up and every decision". The resume docstring: "the decisions attach to the same rows". A re-run should keep every decision that still matches a row and list the ones that do not.
- Where: `crosswalk_server.py:1652` (`run_start`), `:1720` (`express_run`), `:3402` (`programs_preview`) all do `S["actions"] = []`; `sessions_store.py:39-44` `SAVED_KEYS` lacks `id_decisions`, `program_groups`, `program_aliases`, `corrections_files`; `crosswalk_server.py:2226-2250` `sessions_resume` reports `len(actions)` regardless.
- Proof: `s30_decisions_wiped.py`, `s15_sessions.py`, `s08_corrections.py`
  ```
  s30  decisions held: 4 | G1 settled=72 ... clean 89, review 3, aside 2
  s30  1. Programs screen: Preview -> True | decisions now: 0 | G1 settled=70 ... clean 86, review 8
  s30  2. Process again with no change at all -> decisions now: 0
  s30  3. Fast path again -> True | decisions now: 0
  s15  resume -> {'ok': True, 'sources': [...], 'stage': 1, 'decisions': 4}
  s15  actions after Process: 0
  s15  original: G1 settled=74 ... G2=89 ... {'clean': 93, 'review': 3, 'aside': 2}
  s15  resumed : G1 settled=73 low=72 high=73 open=1 | G2=88 ... {'clean': 90, 'review': 8, 'aside': 0}
  ```
- Rewrite requirement: Every decision is stored with a stable row key (system, Client_ID, content hash) and replayed after any re-run; the re-run reports "N kept, M no longer match a row" with the M listed. Save every decision type. Test: decide, save, restart, resume, add the same files, Process: counts and all exports equal the original; re-Process with no change keeps all decisions.

### C-08. "Keep this copy" is stored as a row number, so after a re-export the opposite row is kept
- Severity: High
- Steps: In the "Copies you confirmed" review, the reviewer keeps A950's row and sets A005's aside (`copies:47`). Save progress. The source system re-exports A.csv sorted by name (same rows, same count). Resume, add the files, Process. (`s16`, variant 2)
- Got: the group is found again (its id is a hash of the match key) with the decision `copies:47`, but the group's rows are now 8 and 9, so row 47 is not in it and the code falls back to keeping the first row: A005 is kept, A950 goes to review. The reviewer's choice is reversed with no message.
- Expected: The row the reviewer chose (A950) is kept; if it cannot be found the group goes back to undecided.
- Where: `dedupe_rules.py:166-172` (`copies:N`, N = 1-based position in the group, fallback to the first row), `dedupe_rules.py:104-107` `group_id` (stable by content, so the decision still attaches).
- Proof: `s16_sessions_changed_file.py`
  ```
  decision copies:47: A950 -> clean | A005 -> review/aside: Pending
  resume -> {'ok': True, ..., 'decisions': 0}     dup_decisions restored: {'A.csv :: A1:I48': {'8903f66758': 'copies:47'}}
  same group now shows rows: [(8, 'A005'), (9, 'A950')] | decision: copies:47
  after changed file:  A950 -> review/aside: Pending | A005 -> clean
  ```
- Rewrite requirement: Store which record was kept (system, Client_ID, content hash), not a position; an unresolvable choice leaves the group undecided and listed. Test: s16 fixture; assert A950 stays the kept row after the re-sort.

### C-09. The review screen returns 500 whenever a required field is blank (crash)
- Severity: High (the screen where every decision is made cannot open for a common data problem)
- Steps: A file where one row has a blank First_Name. Process. Open Review. (`s05`)
- Got: `GET /api/ui?screen=review -> 500`, `NameError: name 're' is not defined`. Results opens fine and reports 1 row in review that cannot be reached.
- Expected: The review screen opens and offers the "Missing First_Name" group.
- Where: `crosswalk_server.py:520` `re.match(r"Missing (\w+)", e)` in `_group_diagnosis`; `re` is not among the imports at lines 13-39.
- Proof: `s05_repro_re_missing.py`, `s33_crash_text.py`
  ```
  GET /api/ui?screen=review -> 500 Internal Server Error
  review screen: NameError name 're' is not defined
  ```
- Rewrite requirement: Every group type that can occur needs a test that opens the review screen. Test: one fixture with one row for each possible error kind; assert the review screen renders a group for each.

### C-10. Process fails with TypeError whenever an address is found in the gazetteer (crash)
- Severity: High (Process does not complete; there is no number at all)
- Steps: With the shipped gazetteer and district files in place (the normal offline set-up), upload a file with one address that the gazetteer knows. Process. (`s23`)
- Got: run status `error`: `list indices must be integers or slices, not str`. The sample files never reach it because none of their addresses is in the gazetteer (0 of 256 rows geocode, `s13`).
- Expected: The row geocodes and gets its districts.
- Where: `app.py:1968-2002` `load_district_index` returns `(features, meta)`; `crosswalk_server.py:195-203` `_load_reference` stores that tuple as `dist`; `:818` passes it on; `app.py:2036-2040` `assign_districts` iterates `features` and reads `feat["polygons"]` on the first element, a list (call at `app.py:2552`).
- Proof: `s23_gazetteer_crash.py`
  ```
  address taken from the shipped gazetteer: 05874 Nathan Hollow Brooklyn 11232
  run status: {'state': 'error', 'phase': '', 'progress': 0, 'error': 'list indices must be integers or slices, not str'}
  type of the district index the server holds: tuple
  ```
- Rewrite requirement: One loader contract with one return shape, and a test that geocodes at least one address from each reference file. Test: Process a file whose rows are drawn from the gazetteer; assert coordinates and all three districts are filled.

### C-11. Manual_Review_Needed cannot be exported when any summary row exists (crash)
- Severity: High (the corrections workflow starts from this file)
- Steps: A file with a "TOTAL" line among the data (the tool detects it and sets it aside for review). Process. Download Manual_Review_Needed. (`s22` part B)
- Got: `GET /api/export/file?which=review -> 500`, `KeyError: '__original__'`. The Download screen shows review = 1 and offers the file. Other exports work.
- Expected: A file with the summary row, reason "Summary row, not a client record".
- Where: `app.py:1508-1530` the summary-row early return builds a record without `__original__`; `app.py:2708` `review_rows_to_dataframe` reads `r["__original__"]`.
- Proof: `s22_remaining_probes.py`, `s33_crash_text.py`
  ```
  rows: {'input': 2, 'clean': 1, 'review': 1, 'aside': 0}
  export review          -> HTTP 500 Internal Server Error
  review export: KeyError '__original__'
  ```
- Rewrite requirement: Every record kind must carry its original values; the review export is tested against every kind of review row. Test: fixture with a summary row, a missing-name row, a ZIP conflict; assert the review file lists all three with their original values.

---

## Medium

### C-12. Goal 2 has no range while pairs are open
- Severity: Medium
- Steps: Process the product's 266-row sample files, open Results. (`s19`)
- Got: Goal 1 shows 244 to 256 (14 open pairs), Goal 2 shows a single 52. The printable page says only the first count is a range. Accepting all 14 pairs gives Goal 2 = 51 (Housing 15 becomes 14).
- Expected: Goal 2 shows 51 to 52 with the same caveat, since both counts depend on the same open pairs.
- Where: `identity.py:559` `pairs` is built only from settled clusters; `crosswalk_server.py:2540-2556` `_summary_payload`; `ui/app.js:2123` and the printable page text.
- Proof: `s19_ranges.py`
  ```
  open proposals: 14
  screen Goal 1: settled/high=256 low=244 | independent low=244 -> OK
  screen Goal 2: single number 52 (no range) | independent: high=52 low-if-all-accepted=51
  programs whose per-program count would change if all open pairs are accepted: {'Housing': (14, 15)}
  ```
- Rewrite requirement: Compute Goal 2's low end from the same union as Goal 1 and show it per program. Test: with N open pairs, the low end equals an independent union over all proposals; the band names both counts.

### C-13. Taking a program name out of a group does nothing when it is the group's own name
- Severity: Medium
- Steps: Programs screen: "Workforce Dev." and "Workforce Development" are grouped under "Workforce Dev.". The operator pulls "Workforce Dev." out to count it alone (the UI sends `into: "__alone__"`). Process. (`s22` part A)
- Got: both groups now carry the canonical name "Workforce Dev.", the alias map sends both spellings to it, and Goal 2 stays 1 with one program name.
- Expected: Two program names counted separately (Goal 2 = 2 for Ana, who appears under both).
- Where: `crosswalk_server.py:3179-3220` `programs_group`: it removes the variant but leaves the remaining group's `canonical` unchanged (the removed name).
- Proof: `s22_remaining_probes.py`
  ```
  groups now: [('Workforce Dev.', ['Workforce Development']), ('Workforce Dev.', ['Workforce Dev.'])]
  alias map : {'Workforce Development': 'Workforce Dev.', 'Workforce Dev.': 'Workforce Dev.'}
  after Process: G1 settled=1 ... G2=1 ... {'Workforce Dev.': 1}   (two separate names were asked for)
  ```
- Rewrite requirement: A group's label is derived from its members and must stay unique; ungrouping must change the counts. Test: group two spellings, ungroup either one, Process, assert Goal 2 counts them separately.

### C-14. Undo removes only the last group decision; row decisions cannot be undone and are left behind
- Severity: Medium
- Steps: Send the ZIP group to the queue, approve one queued row, press Undo. (`s20`)
- Got: Undo skips the row action and pops the group action. The group returns to pending while the row it created stays approved and counted (clean 87). A second Undo returns `{'ok': False}`, so the approval cannot be undone through Undo.
- Expected: Undo pops the most recent decision of any kind.
- Where: `crosswalk_server.py:1955-1966` `review_undo` loops for `type == "group"` only.
- Proof: `s20_undo.py`
  ```
  actions: [('group', 'zipbad', 'sent'), ('row', 'A.csv :: A1:I48||40', 'approved')]
  undo -> {'ok': True}   actions left: [('row', 'A.csv :: A1:I48||40', 'approved')]
  zipbad group status: pending | row ... status now: ['approved']
  second undo with only a row action left -> {'ok': False}
  ```
- Rewrite requirement: One ordered decision log; undo pops its last entry whatever its type. Test: apply 3 mixed decisions, undo 3 times, assert state equals the start after each pop in reverse.

### C-15. Manual_Review_Needed also lists set-aside rows, so the three files add up to more than the input
- Severity: Medium
- Steps: Messy fixture, set the duplicate group aside ("dupc aside"), download clean, review and set-aside files. (`s06` step 2)
- Got: Results: clean 86, review 6, aside 2 (sum 94). Files: 86 + 8 + 2 = 96 rows. The 2 set-aside rows are in both Manual_Review_Needed (status "Set aside") and Set_Aside_Records. The Download screen says Manual_Review_Needed holds `review + aside` rows, so it agrees with the file but not with Results. After further actions the gap grows (3 set aside: 86 + 8 + 3 = 97).
- Expected: Spec: Manual_Review_Needed = "every row still in review"; Set_Aside_Records = "every row set aside". Each source row in exactly one of the three files.
- Where: `crosswalk_server.py:909-920` `_review_df` returns `still + aside`; `ui/app.js:2293`.
- Proof: `s06_sequence_decisions.py`, `s08_corrections.py`
  ```
  [2 dupc aside] rows={'input': 94, 'clean': 86, 'review': 6, 'aside': 2} files(clean,review,aside)=(86, 8, 2)
      FAIL -> REVIEW FILE: 8 rows vs screen review 6
      FAIL -> THREE FILES: 86+8+2=96 vs input 94
  [3e bulk set aside all approved] ... files(clean,review,aside)=(86, 8, 3)  FAIL -> THREE FILES: 86+8+3=97 vs input 94
  ```
- Rewrite requirement: Partition: each source row appears in exactly one output file. Test: after every decision type, rows(clean) + rows(review) + rows(aside) = input and the key sets are disjoint.

### C-16. "Keep one per program" marks clean rows removed; they stay in Final_Clean_Mapped and the audit says they were set aside
- Severity: Medium
- Steps: Messy fixture, press "keep one per person per program". (`s07`)
- Got: the reply says "kept 3, set 4 row(s) aside"; the queue shows 4 "removed". Results shows aside 2. Two of the four "removed" rows (C990, A950) were clean rows and are still in Final_Clean_Mapped, but the audit says "removed (set aside, same person as ...)". Same for "keep this row" (`queue_keep_one`).
- Expected: Only rows that were in review can be resolved this way, or the action really moves clean rows to Set_Aside_Records. Either way the reply, queue, audit and files agree.
- Where: `crosswalk_server.py:1998-2025` `queue_keep_one`, `:2028-2075` `queue_keep_one_per_program` append row actions for clean rows too; `_export_sets` (`:863-877`) resolves statuses only for `res["review"]`.
- Proof: `s07_keep_one.py`
  ```
  response: {'ok': True, 'kept': 3, 'set_aside': 4, ...}
  queue says 'removed': 4 | Set_Aside_Records rows: 2
     C.csv :: A1:I17||15  id=C990 'removed' on screen, but file holds it in: Final_Clean_Mapped
     A.csv :: A1:I48||46  id=A950 'removed' on screen, but file holds it in: Final_Clean_Mapped
  audit: 2. Row C.csv :: A1:I17||15 id C990: removed (set aside, same person as ...)
  ```
  Goal 1 and Goal 2 are not affected (identity already merges these rows).
- Rewrite requirement: One definition of which state each row is in; a decision against a row either takes effect or is rejected with a reason. Test: after keep-one-per-program, every row the audit calls set aside is in Set_Aside_Records and none is in Final_Clean_Mapped.

### C-17. Client_ID duplicates are checked across all files, not within one file, so unrelated systems flood review
- Severity: Medium
- Steps A (`s21` a): three systems, each numbering its own clients 1 to 20, 60 different people. Process.
- Steps B (`s21` b): one enrollment-level file, 3 clients each on two rows (same ID, different Program).
- Got A: all 60 rows go to the "One identifier used for records that do not match" group; clean 0, Goal 1 = 0 until a person presses accept all on 60 rows. Got B: 6 of 6 rows in review; after accept all Goal 1 = 3 and Goal 2 = 6, which is right.
- Expected: The spec's Tier 1 is "the same non-blank Client_ID on rows in one file". IDs from different systems are not related; a multi-program client in one system is normal.
- Where: `app.py:2389-2392` `id_groups[r["Client_ID"]]` is keyed on the identifier alone, across every file (loop continues to `:2413`).
- Proof: `s21_client_id_scope.py`
  ```
  (a) G1 settled=0 ... rows={'input': 60, 'clean': 0, 'review': 60}   groups: [('idconflict', 60)]
  (b) rows={'input': 6, 'clean': 0, 'review': 6}                     groups: 'One identifier used for records that do not match'
  (b2) after accept all: G1 settled=3 ... G2=6 ...
  ```
- Rewrite requirement: Scope Tier 1 to (system, Client_ID) and decide explicitly how same-ID rows with a different program are treated. Test: three files numbering from 1 produce 60 clean rows; an enrollment file with 2 programs per client yields Goal 1 = 3, Goal 2 = 6 without review.

### C-18. Set-up changes after a run leave Results, exports and audit disagreeing, and nothing says the results are out of date
- Severity: Medium
- Steps: Messy fixture, Process, three group decisions, then without pressing Process: (1) exclude C.csv, (2) map Last_Name to the Address column, (3) set A.csv's header row to 2, (4) merge two program names. (`s18`)
- Got: (1) Sources says 78 rows staged; Results and Download say 94 received and clean 88; the audit set-up says "Table C.csv: not included" while Final_Clean_Mapped still holds 16 C.csv rows. (2) the audit says `Last_Name<-Address` while Final_Clean_Mapped still shows the old surnames. (3) the table list still says 47 rows, the frame has 46, Sources says 93, Results 94, and 3 held decisions now refer to row numbers that point at different clients. (4) per-program totals unchanged. No screen says "out of date, run Process".
- Expected: Each change marks the results stale (banner, exports refused or stamped) or the audit and exports describe the same run.
- Where: `crosswalk_server.py:1504` `sources_include`, `:1597` `set_header_row`, `:1620` `set_map` change inputs without touching `S["results"]` or marking it stale; only the Programs screen has a `program_preview_stale` flag.
- Proof: `s18_stale_after_setup_change.py`
  ```
  1. C.csv excluded: sources 78 rows | Results 94 | Download recon {'input': 94, 'clean': 88, ...}
     audit: 'Table C.csv :: A1:I17: not included, 16 rows'   Final_Clean_Mapped still contains C.csv rows: 16
  2. audit: 'Matching for B.csv: ... Last_Name<-Address ...'  Final_Clean_Mapped B.csv Last_Name: ['Alvarez', 'Alvarez']
  3. S['tables'] rows column still says: 47 | frame now has: 46 | actions still held: 3
  ```
- Rewrite requirement: Store a fingerprint of all inputs (included tables, header rows, mapping, defaults, program map, settings) with every result; every screen and export compares it and shows "out of date" when it differs. Test: change each input kind after a run; assert the stale marker appears and exports carry it.

### C-19. "Without a program" counts records but says persons
- Severity: Medium
- Steps: Fixture of 4 people over 3 files; one file has no program column, one row has a blank program (`s11` case f).
- Got: Results card: "3 counted person(s) have no program recorded, so they are in the first count but not the second." The 3 are records. Only Di is in Goal 1 and not Goal 2; the other two have a program elsewhere.
- Expected: 1.
- Where: `crosswalk_server.py:2534-2536` counts `r.program` empty over records; text at `ui/app.js:2159-2162`; `identity.py:560`.
- Proof: `s11_goal2_edges.py`: `(f) goal2.no_program = 3 (records without a program; people without ANY program: Di only = 1)`
- Rewrite requirement: Count people with no program anywhere, by master ID. Test: the fixture above reports 1.

### C-20. Master_ID renumbers when any identity verdict changes
- Severity: Medium
- Steps: Process the sample files, export Unique_Clients, decide one open pair "same", export again. (`s27`)
- Got: 199 of 256 source rows have a different Master_ID. Numbers are assigned in the order of each cluster's first row id, as text, so one merge shifts the rest.
- Expected: A person keeps the same Master_ID across decisions, so files from different days can be joined.
- Where: `identity.py:535-542` (`sorted(groups, key=lambda g: sorted(groups[g])[0])`, then `M{n:06d}`).
- Proof: `s27_master_id_stability.py`
  ```
  rows: 256 | Master_ID of the same source row changed after ONE 'same' verdict: 199 rows
      clinic_export.csv :: A1:B63||60 M000058 -> M000001
  ```
- Rewrite requirement: Derive the ID from the cluster's stable content (for example the lowest member key), and keep it when clusters merge by retaining the older ID. Test: one verdict changes Master_ID for only the merged people.

### C-21. Identity verdicts (same person / different people) are not in the audit trail
- Severity: Medium
- Steps: Sample files; decide one open pair "same" and one "different". Compare the audit. (`s26`)
- Got: Goal 1 moves 256 to 255, open 14 to 12; the audit text is identical (84 lines before and after) and `GET /api/audit?kind=decision` has no mention of either.
- Expected: Spec: the audit holds "every decision a person took", in order.
- Where: `crosswalk_server.py:3454-3467` `identity_decide` writes `S["id_decisions"]` only; `audit_trail.py` has no identity section.
- Proof: `s26_identity_decision_audit.py`: `audit lines before/after: 84 84 | identical text apart from timestamps: True`
- Rewrite requirement: Identity verdicts go through the same decision log as every other decision (and C-07's saving). Test: decide, read the audit, find the verdict by row identifiers.

### C-22. The audit trail carries values: unit numbers, cities and ZIP codes
- Severity: Medium
- Steps: A file with a unit conflict and a city/ZIP conflict; Process; export Secure_Audit_Log. (`s17`)
- Got: lines such as `Unit conflict: the address says 'Apt 4D' but Address_2 says 'Apt 7F'` and `City says 'Queens' but ZIP 10451 is in Bronx`. The check found 'Apt 7F' from the data inside the audit.
- Expected: Spec: "identifiers, row numbers and column names only. Never a name, address or value", "an absolute rule".
- Where: `app.py:1556-1560` (unit text), and the city/ZIP conflict message in `app.py`; messages are written to the audit verbatim.
- Proof: `s17_exports_audit.py`: `data values found inside Secure_Audit_Log, by column: {'Address_2': ['Apt 7F']}`
- Rewrite requirement: Audit messages are templates with column names only; the values stay in the review file. Test: Process a fixture whose every field has a unique token and assert none appears in the audit or the printable summary.

### C-23. Rows in a table the tool left out are invisible to the balance, which cannot fail
- Severity: Medium
- Steps: A CSV with a blank line between records (very common in exports): header, A1, blank line, a row of commas, A2, A3. Add it, Process. (`s28`, `s28b`)
- Got: the file is split at the blank line into two tables. The first (1 row) is included; the second (A2 and A3, 2 real clients, no header) is "not included" by default. Results: input 1, clean 1, "The books balance ... every row is accounted for". The express check returns ok with no warnings. Goal 1 = 1 for a file with 3 clients.
- Expected: Rows that exist in the files but are left out are counted and shown ("2 rows in 1 table not included") on Results and in the printable page.
- Where: `crosswalk_server.py:880-890` `_reconciliation` compares clean + review + aside with `len(res["transformed"])`, which equals their sum by construction, so it can never fail; `_run_thread` (`:830-846`) repeats the same test; `table_detect.py` splits on fully blank rows.
- Proof: `s28_blank_rows.py`
  ```
  tables: [{'key': 'b.csv :: A1:I2', 'rows': 1, ...}, {'key': 'b.csv :: A5:I6', 'rows': 2, 'headerRow': 0}]
  Process -> {'input': 1, 'clean': 1, 'review': 0, 'aside': 0} | Final_Clean ids: ['A1']
  express check: {'ok': True, 'blockers': [], 'warnings': [], 'tables': 1, 'rows': 1, ...}
  ```
- Rewrite requirement: Reconcile against an independent count taken at load (every data row in every file) and show left-out rows as a fourth number. Test: that file reports 3 rows received, 1 included, 2 in an excluded table, and a warning.

### C-24. The address key ignores street type, so "address matches" is stated for different streets
- Severity: Medium
- Steps: Unit-level scoring (`s02`): same name and DOB, "123 45th St" vs "123 45th Ave", same ZIP; "45 Park Ave" vs "45 Park Pl".
- Got: both have the key `45 park|10013` / `123 45th|11377`, so the engine adds 30 points and shows "address matches". 45th St and 45th Ave (and Park Ave and Park Pl) are different places. With full name and DOB this still passes the four-fact test and joins automatically, so a person never sees it.
- Expected: Street type is part of the street (or at least a mismatch is shown as a caution); evidence text matches what was compared.
- Where: `identity.py:279-286` the `re.sub` removing street, ave, road, blvd, place, ...
- Proof: `s02_identity_auto.py`
  ```
  123 45th St vs 123 45th Ave same ZIP, same name+DOB pts=128 auto=True people=1 truth=different places
  10b: addr_key ignores street type: '45 Park Ave' vs '45 Park Pl' ... addr_key a: 45 park|10013 | b: 45 park|10013
  ```
- Rewrite requirement: Normalize street types to a canonical form instead of deleting them ("st" and "street" equal, "st" and "ave" not). Test: 45th St vs 45th Ave have different keys; "W 45th St" and "West 45th Street" have the same key.

---

## Low

### C-25. Jitter comes from one shared stream: any change moves other rows, and one address gets different points
- Severity: Low
- Steps: Gazetteer addresses (C-10 worked around in memory, as noted in `s14`); fix the ZIP of one failing row; Process again. (`s14`)
- Got: the same seed gives identical coordinates across two resets (good), but after one unrelated correction 28 of 33 rows have different stored coordinates though their own data did not change. Two households at one address get different points (40.663800 / -73.914997 vs 40.663770 / -73.915092), so averaging the rows at an address pulls back toward the true point.
- Expected: A row's offset depends on the seed and the row (or address) only.
- Where: `app.py:2326` one `random.Random(jitter_seed)` consumed in row order (`:2487-2503`).
- Proof: `s14_jitter.py`: `rows whose stored coordinates changed though their own data did not: 28 of 33`
- Rewrite requirement: Derive each offset from a hash of (seed, address key) so equal addresses share a point and nothing else moves. Test: correct one row; assert all other rows' coordinates are unchanged.

### C-26. The Download screen has no chip for Resolution_Status, which the clean file carries
- Severity: Low
- Steps: Compare the Download screen's 22 column chips with the 23 columns of Final_Clean_Mapped. (`s17`)
- Got: `Resolution_Status` is in the file but has no chip; switching it off through the API does remove it.
- Expected: The screen lists every column in the file.
- Where: `crosswalk_server.py:893-906` `_clean_df` adds the column after the chip list is built; `ui/app.js` `vExport`.
- Proof: `s17_exports_audit.py`: `in file, not on screen: ['Resolution_Status']`
- Rewrite requirement: One column list drives both the screen and the file. Test: screen chips equal file columns.

### C-27. Row order of Final_Clean_Mapped and Manual_Review_Needed follows upload order
- Severity: Low
- Steps: Same three files uploaded A, B, C and then C, B, A. (`s13`, `s25`)
- Got: the two files differ byte for byte; after sorting by Source_File and Source_Row they are identical, and Unique_Clients, Unique_Clients_By_Program and Set_Aside_Records are identical in either order.
- Expected: Output order is a function of the data, not of the click order.
- Where: not traced to one line; rows are emitted in the order the tables were added.
- Proof: `s25_upload_order.py`: `clean same order: False | after sorting by ['Source_File', 'Source_Row']: differing columns = []`
- Rewrite requirement: Sort every export by a stable key. Test: two upload orders give byte-identical files.

---

## Checked and correct

- Goal 1 and Goal 2 on the 266-row sample files match an independent pandas computation from the exports: 256 and 52; per program Housing 15, Older Adult Services 13, Workforce 12, Youth 12 (`s01`).
- The low end of the Goal 1 range equals an independent union over all open proposals: 244 with 14 open pairs (`s19`).
- Only clean and approved rows are counted; in-review and set-aside rows never appear in Unique_Clients, before or after accept all and set aside (`s19`).
- Unique_Clients partitions the clean rows exactly: 256 distinct row ids, none missing, none extra, Source_Record_Count sums to 256 (`s01`).
- The on-screen balance clean + review + set aside = input holds after every step of the decision sequence (group, row, bulk, keep one, back to pending), by construction (`s06`).
- Row counts of Final_Clean_Mapped and Set_Aside_Records equal the Results screen at every step of the decision sequence, and the Download screen's reconciliation equals Results (`s06`).
- Two runs from a reset give byte-identical exports for all seven files, timestamps masked, for both the sample and the messy fixture (`s13`).
- Jitter is seeded: the same seed gives identical coordinates, a different seed different ones (`s14`, with the C-10 workaround).
- Fast path and stage by stage match byte for byte on the sample files for every export except the audit, which lacks only the "Program names grouped:" section (`s12`, `s12b`).
- Upload order does not change Master_ID assignment or the content of any export; only the row order of two files (`s13`, `s25`).
- A Tier 1 exact duplicate in one file (same ID, identical data) is set aside once and counted once (`s07`, rows A003).
- Case-only and spelling variants of a program are grouped once the Programs screen has been opened, and Goal 2 then counts them once (`s11`).
- A default program for a file without a program column is applied, and the person is then counted in Goal 2 (`s11` case d).
- An identity verdict updates the range correctly: "same" lowers settled and high, "different" closes the question (`s26`: 256 to 255, open 14 to 12).
- Excluding a table and pressing Process updates the row balance and the clean file (only the identity-derived numbers go stale; see C-03) (`s10`).
- Changing the header row re-reads the table and its columns (`probe_header.py`).
- A re-uploaded Manual_Review_Needed file is recognized as a corrections file and is not loaded as a source table (`s08`).
- Switching DOB off in the clean file removes the column and leaves Goal 1 and Goal 2 unchanged (70 and 84 before and after) (`s35`).
