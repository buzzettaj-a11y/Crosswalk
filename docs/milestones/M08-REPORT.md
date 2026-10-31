# M08 report

## Questions for Joe

Nothing blocks. These are the seven readings the milestone asked me to state, and the default is built in each case.

1. **A count is never final while a copy group is open.** SPEC 7.2 names open pairs. An open copy group also leaves the count as a range, so I treat it the same way.
2. **"Joins more than 5 records" counts rows.** A "same person" decision needs a second reviewer when the merged group would hold more than 5 rows.
3. **The second sign-off also applies to approving more than 200 rows from the queue**, not only to accepting a whole cause.
4. **The accept reasons and the set-aside reasons are my wording.** Accept: `checked_sample`, `matches_source`, `expected_in_this_file`, `other`. Set aside: `not_a_client`, `test_record`, `duplicate_other_system`, `out_of_scope`, `other`. The labels are in `wholecount/copy/reasons.toml`.
5. **The sentence for "a geocoder is set up but nothing was looked up" is my own:** "No counted address could be looked up, so confidence can't be High." The no-geocoder sentence is the spec's.
6. **A corrected row that still fails stays not counted yet**, with its new reasons.
7. **Adapters in `engine/pipeline.py`.** I didn't edit any earlier module to fit. The adapters are:
   - `located`: M04's `LocationStatus` and M05's `GeoResult` into the row outcome
   - `copy_rows` and `copy_row`: standardized rows into M06's `CopyRow`
   - `person_row` and `person_key_for`: rows into M06's `PersonRow`, keyed the way `key_modes` says
   - `table_programs`: each table's program source for M07
   - `restandardize`: re-running P-STD and P-VAL on one row for an accepted fill or a correction

Choices made on the most conservative reading:
- **An approval never closes an open same-ID conflict.** Only "different people" or "approved as entered" closes it. Before this fix, approving every open row in one step closed the conflict too, and two different people under one Client ID reached identity as one record. A test covers it now.
- **Confirming a program group recomputes at once**, because it's a decision (CMD-2). The C-18 test needs a change that leaves programs stale, so its program case uses a `program_columns` set-up change instead.
- **A set-up change still waiting for Process keeps everything after it stale.** A later decision doesn't quietly run it.
- **Two decisions on one pair that disagree: "different" wins.** That's the M06 rule, unchanged.
- **Accepted fills and corrections apply first in the replay**, because they change a row's text. The other decisions apply after them.
- **Reading files and choosing tables happen in `session/runner.py`, not the engine pipeline.** Record keys need the install secret, and the engine never imports `session`.
- **Loading is cached by the sources fingerprint. Every later step re-runs**, because each is pure and fast on these sizes. STALE-3 keeps the last three results, and an undo that restores the fingerprints brings one back without a run.
- **The R and S fixture uses an exact reference backend, not the fake.** M05 makes fill proposals only from Geosupport or a reference, and the decided state needs the R13 fill.
- **`session-check --shuffle-rows` shuffles the rows in memory.** Writing a shuffled copy would put client rows on disk (H9). `session-demo` writes its made-up fixture to a temporary folder and removes it.

Changes to earlier tests, each small:
- `tests/unit/test_std_problem_rows.py` leaves out `same_id_conflict`. That reason comes from the copy step, and `tests/fixtures/session/problem_rows.py` covers it.
- `tests/unit/test_dev_counts_only.py` allows digits in a dev label after the first letter, because this milestone's labels include `goal1_low` and `step_1_tenths`.
- `tests/copy/lint.py` now also lints `wholecount/copy/reasons.toml`, which uses `label` rather than `text`.

## What was built

- **Engine.**
  - `engine/review.py`: `RowOutcome`, causes in three tabs with kinds, `finish_gate`, `keep_one_per_program`, `diagnose_mapping` and `people_in_other_files`
  - `engine/counts.py`: `Counts`, `Range`, `Locations`, the balance with its three checks, and `balance_lines`
  - `engine/confidence.py`: batch, match and location confidence
  - `engine/corrections.py`: corrections matched by record key
  - `engine/pipeline.py`: steps 2b to 10 and the adapters
  - `engine/outputs/audit_entry.py`: `AuditEntry` with typed slots, and `KeyedHash`
  - `engine/reasons.py` registers `same_id_conflict`, with its `problems.toml` entry
- **Session.**
  - `session/state.py`: `Setup`, `Results` with `digest()`, `Session` with `counts()`, `download_gate()` and `preflight()`
  - `session/commands.py`: the 17 commands and `History`, the one undo stack
  - `session/decisions.py`: `Decision`, `DecisionStore` and replay with `NoLongerApply`
  - `session/reviewer.py`: reviewer names, `sample_rows`, `check_accept` and `decisions_by_reviewer`
  - `session/staleness.py`: the node graph and fingerprints
  - `session/runner.py`: `process`, `run`, `fast_path`, `preview_counts`, `recompute_from` and `causes_for`
  - `session/keys.py` gains `value_hash`
- **Settings and copy.** `settings/confidence.toml`, `settings/review.toml`, `copy/reasons.toml`, and the counts, balance, confidence, review and command-label sentences, each fact with a claim test.
- **Dev commands.** `session-demo` and `session-check`.

On the R and S fixture, the base state gives:
- 17 received, 13 counted, 3 not counted yet, 1 set aside
- Goal 1 and Goal 2 both 9 to 11, with Housing 3 to 4, Youth 3 to 4 and Workforce 3
- 10 of 12 looked-up addresses placed High
- Low confidence, with the parts the milestone lists, and the four plus one causes

The decided state gives 14 counted and 3 set aside, ranges of 11 to 13, 12 of 14 placed High with 1 filled, and Medium confidence. Two "different" verdicts give final 13 to 13. The C fixture gives 9 to 13 and 12 to 15, then 7 to 11 and 9 to 12 after excluding C.csv.

## Tests

| Command | Result |
| --- | --- |
| `make test` | 2027 passed |
| `make offline` | 60 passed |
| `make copy` | 408 passed |

`make test` and `make copy` include this report's own lint test.

New test files:
- `tests/rules/`: `test_P_REV.py`, `test_counts.py` (COUNT, CONF, CMD and STALE), `test_reviewers.py`, `test_reviewer_default.py`, `test_8_7_bulk_accept.py`, `test_8_4_finish_review.py`, `test_REV_2_cause_kinds.py`, `test_CONF_74.py`, `test_P_VAL_2_address_plays_no_part.py`, `test_P_GEO_8_through_process.py`, `test_dob_coverage.py`
- `tests/invariants/`: `test_balance.py`, `test_undo_roundtrip.py`, `test_determinism.py`, `test_record_key_stability.py`, `test_ranges.py`, `test_staleness.py`
- `tests/session/`: `test_decisions_hold_no_cell_values.py`, `test_audit_entry_slots.py`, `test_cancel_leaves_session.py`, `test_counts_refuse_when_unbalanced.py`, `test_fast_path_equals_staged.py`, `test_no_random_or_clock.py`
- `tests/copy/test_counts_copy.py` and `tests/unit/test_dev_session.py`
- Fixtures and support: `tests/fixtures/session/r_fixture.py`, `tests/fixtures/session/problem_rows.py` and `tests/support/session.py`

Audit IDs closed:

| ID | Severity | Test |
| --- | --- | --- |
| A-06 | High | `tests/audit/test_A06_final_wording.py` |
| A-07 | High | `tests/audit/test_A07_preview_is_read_only.py` |
| A-12 | Medium | `tests/audit/test_A12_goal2_range_wording.py` |
| A-22 | Low | `tests/audit/test_A22_one_equation.py` |
| C-03 | High | `tests/audit/test_C03_process_stale_identity.py` |
| C-04 | High | `tests/audit/test_C04_undo_refresh.py` |
| C-06 | High | `tests/audit/test_C06_corrections_by_record_key.py` |
| C-07 | High | `tests/audit/test_C07_decisions_survive.py` |
| C-08 | High | `tests/audit/test_C08_keep_copy_after_reexport.py` |
| C-09 | High | `tests/audit/test_C09_every_problem_kind_opens.py` |
| C-12 | Medium | `tests/audit/test_C12_goal2_range.py` |
| C-14 | Medium | `tests/audit/test_C14_one_undo_stack.py` |
| C-15 | Medium | `tests/audit/test_C15_three_files_partition.py` |
| C-16 | Medium | `tests/audit/test_C16_keep_one_per_program.py` |
| C-18 | Medium | `tests/audit/test_C18_stale_after_setup_change.py` |

## Done list

- [x] Every rule ID has a named test. Every audit ID has its own file and a `done` line in `tests/audit/INDEX.md`.
- [x] The R and S fixture gives the milestone's numbers in both states, and the C fixture gives its ranges.
- [x] No code path shows counts or passes the download gate while a node is stale or a balance fails. `Session.counts()` raises, and `download_gate()` holds.
- [x] No decision or audit entry holds a cell value. The scan test passes, and a correction's text stays in memory.
- [x] No `random` and no clock call in `engine/` or `session/`, apart from the one injected default clock in `Session`. `test_no_random_or_clock.py` checks it.
- [x] No new dependency.
- [x] The report's Questions for Joe list covers the seven points.
- [x] `make test`, `make offline` and `make copy` are green, with the counts above.
- [x] This report is written, the branch is pushed, and the pull request is open.

## Windows checks

Run from the repo with the branch checked out. The commands print counts and fixed labels only.

- [ ] 1. `.venv\Scripts\activate`, then `python -m pytest -q`. Expect no failures and the test count above.
- [ ] 2. `python -m wholecount.dev session-demo`. It runs the made-up R and S fixture and prints a block after each step, each starting with `stage`.
  - Stage 0, the base state: `received 17`, `counted 13`, `not_counted_yet 3`, `set_aside 1`, `goal1_low 9`, `goal1_high 11`, `goal2_low 9`, `goal2_high 11`, `open_copy_groups 2`, `confidence_level 1` (1 is Low, 2 Medium, 3 High), `balance_ok 1`.
  - Stage 1, after the five decisions: `counted 14`, `not_counted_yet 0`, `set_aside 3`, `goal1_low 11`, `goal1_high 13`, `confidence_level 2`.
  - Stage 2, after two "different" verdicts: `goal1_low 13`, `goal1_high 13`, `final 1`.
  - Then it undoes every step and prints the earlier blocks in reverse.
- [ ] 3. `python -m wholecount.dev session-check --csv "C:\path\a.csv" --csv "C:\path\b.csv"` on two of your real exports. It uses Geosupport or your reference file if either is set up. Expect:
  - `balance_ok 1`
  - `received`, `counted`, `not_counted_yet`, `set_aside`
  - `mapped`, `counted_not_mapped` and its five reasons
  - `goal1_low`, `goal1_high`, `goal2_low`, `goal2_high`, `open_pairs`, `confidence_level` and `dob_coverage_pct`
  - `step_1_tenths` to `step_4_tenths` for the four steps the runner times: reading files, finding tables, checking rows and placing addresses

  Check that `received` equals the non-empty data rows in the two files, and that `counted_not_mapped` is plausible for your address data.
- [ ] 4. Run step 3 again. Expect identical lines apart from the step times.
- [ ] 5. Run step 3 with `--shuffle-rows`. Expect identical counts. Nothing depends on row position.
- [ ] 6. Run step 3 with `--exclude-last`. It drops the second file. Expect numbers equal to running the first file alone.
- [ ] 7. Run step 3 with `--decide-approve-all --process-twice`. Expect `decisions_kept` equal to `decisions_made` and `no_longer_apply 0`. Rows whose only open problem is a shared Client ID aren't approved, because that takes its own decision.

## Screens

None. M08 is engine and session only.

## Not done

Nothing.
