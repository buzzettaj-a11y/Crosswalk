# M08 Session, decisions, undo, staleness, counting and confidence

## Goal

Build the layer that turns the engine steps into one working state. Every change is a command with apply, undo, a plain label, an H8-safe audit entry and a list of what it makes stale. Every decision carries the reviewer's name, and a bulk accept needs a typed count, a reason and sometimes a second reviewer. Decisions are keyed by record key (pairs by person key) and replay after every run. One undo stack covers every kind of change. A dependency graph marks results out of date at once. A row counts on its person data alone, whether or not its address was placed, and two balances must hold before any count is shown. Count Goal 1 and Goal 2 with ranges, and compute batch, match and location confidence from `settings/confidence.toml`. This milestone is engine and session only. The screens come in M10 to M12, and the files, the audit text and saved progress come in M09.

## Spec sections

- 3.4 (Session and commands), 5.2 (decisions), 6.5 (P-VAL-1 to P-VAL-3 as they land in counting, including open copy groups staying counted), 6.10 (pipeline order), 7 (all of it), 8.1, 8.3, 8.4 (Finish review), 8.5 (Undo), 8.7 (reviewers and bulk accepts, the engine side), 10.4 (staleness), and H4, H5, H7, H8, H12, H13, H15.
- Audit findings closed: C-03, C-04, C-06, C-07, C-08, C-09, C-12, C-14, C-15, C-16, C-18, A-06, A-07, A-12, A-22.
- Fix plan items: 5.1 steps 6 to 8 (identity over counted rows, two balances, "Counted, no usable address"), 5.2 step 5 (DOB coverage), 5.7 steps 1 to 4 (engine side). Where the fix plan and the spec differ, the spec wins.

## Depends on

M00 (copy registry, `ProgressMessage` if M00 made it), M01 to M07. Before you write anything, list what earlier milestones already built under `wholecount/session/` and `wholecount/engine/pipeline.py`, `progress.py`, `counts.py`, `confidence.py`. Extend those files. If one is missing, create it as specified here. The pieces to wire are M04's `CountStatus` and `LocationStatus`, M05's `outcome_for`, `place_rows` and `preflight`, M06's `resolve`, `key_modes` and `PersonRow`, M07's `build_program_map` and `fast_path_gate`, and M01's `keys`. If a signature does not fit, write a thin adapter inside `pipeline.py` and list each adapter in the report. Do not edit the earlier modules to fit.

## Branch

`build/m08-session-counts`, created from the latest `main`.

## Read first

All paths are under `legacy/`.

- `crosswalk_server.py`: `_snapshot` (147) and `_undo_last` (161, the old undo that only pops group actions, C-14), `_autosave` (171), `_rid` (336, a row id from file, range and row number, C-08), `_classify` (456, groups by cause), `_replay` (655), `_tallies` (681), `_export_sets` (863), `_reconciliation` (880, compares a list with itself so it cannot fail), `_clean_df` (893), `_review_df` (909, returns review plus aside, C-15), `_apply_group_decision` (1892), `review_undo` (1955), `queue_action` (1970), `queue_keep_one` (1998), `queue_keep_one_per_program` (2028, C-16), `queue_bulk` (2084), `run_start` (1641, clears decisions, C-07), `express_run` (1705), `sessions_resume` (2226), `_person_records` (2356, takes only the clean side), `_resolve_identity` (2391, the cache behind C-03), `_unique_clients_df` (2449), `_unique_by_program_df` (2483), `_summary_payload` (2521), `programs_preview` (3393, clears decisions, A-07), `identity_decide` (3451).
- `app.py:3349` `parse_corrections_frame` and `3381` `apply_corrections` (row-position addressing, C-06). `audit_trail.py` (`decision_lines` with the 2,000 cap, A-24), `sessions_store.py` (`SAVED_KEYS`), `setups.py`.
- `docs/audit/C-scripts/s06_sequence_decisions.py`, `s07_keep_one.py`, `s08_corrections.py`, `s09_corrections_shifted.py`, `s10_stale_identity_rerun.py`, `s12_fast_vs_staged.py`, `s16_sessions_changed_file.py`, `s18_stale_after_setup_change.py`, `s20_undo.py`, `s30_decisions_wiped.py`, `s34_undo_stale.py`, and `invariants.py` (the cross-checks to port).
- `docs/context/docs/crosswalk-fix-plan.md` 5.1 (line 598) and 5.7 (line 757).

## What to build

```
wholecount/engine/progress.py        ProgressSink, ProgressMessage (spec 11.6.3) if not already built
wholecount/engine/pipeline.py        the twelve steps of 6.10, each a pure function of its inputs
wholecount/engine/review.py          row outcomes, causes, applying decisions, keep-one rules, finish gate
wholecount/engine/corrections.py     apply_corrections() on verified corrections (C-06)
wholecount/engine/counts.py          Goal 1, Goal 2, ranges, both balances, locations
wholecount/engine/confidence.py      batch, match and location confidence
wholecount/engine/outputs/audit_entry.py   AuditEntry, its typed slots and KeyedHash (M09 writes the lines)
wholecount/session/state.py          Session (3.4), Results (derived, versioned, digest())
wholecount/session/commands.py       Command protocol, History (the one undo stack), every command
wholecount/session/decisions.py      Decision, DecisionStore, replay, NoLongerApply
wholecount/session/reviewer.py       reviewer name, sample_rows(), check_accept(), second sign-off
wholecount/session/staleness.py      the graph, fingerprints, StaleResults
wholecount/session/runner.py         run(), fast_path(), preview_counts(), recompute_from()
wholecount/session/keys.py           add value_hash(secret, field, text) -> KeyedHash
wholecount/settings/confidence.toml, review.toml;   wholecount/copy/reasons.toml gets an [accept] list
```

### Decisions (5.2, 8.7, H12)

```python
@dataclass(frozen=True)
class Decision:
    decision_id: str                 # "D-" + sha256(kind, sorted record_keys, basis)[:10]
    kind: Literal["approve", "set_aside", "accept_fill", "keep_one", "not_copies", "different_people",
                  "approved_as_entered", "pair", "program", "correction", "route"]
    record_keys: tuple[str, ...]     # sorted
    person_keys: tuple[str, ...]     # a pair decision holds the two person keys, sorted
    basis: str                       # kind-specific, no cell values
    made_at: str                     # ISO time, UTC, from an injected clock
    reviewer: str                    # on every decision (8.7)
    second_reviewer: str | None
    detail: tuple[tuple[str, str], ...]   # reason code, kept record key, verdict word, field names, typed count
```

- `basis` examples. `accept_fill`: the M05 `FillProposal.basis`. `keep_one`, `not_copies`, `different_people`, `approved_as_entered`: the M06 `group_id`. `pair`: a hash of the two sorted evidence code lists. `program`: the sorted program names. `correction`: the corrections file fingerprint. `route`: the reason ID.
- A decision never stores a cell value. A test serializes every decision made in the R fixture and scans for all its names, streets, dates and ZIPs.
- `DecisionStore.replay(outcomes, groups, ...)` applies decisions after the checks and copy step (step 8). It returns the new outcomes and a list of `NoLongerApply(decision, reason)`. Reason codes are `record_gone`, `person_gone`, `basis_changed`, `group_changed`, `file_removed`, `names_gone`, `row_set_aside`, and `dob_now_differs` (M13). Lapsed decisions stay in the store and apply again if their records return. Fix problems lists them. They are never dropped silently.
- A decision applies only to rows that still hold the reason it resolves (H12). A row cannot be approved twice.

### Row outcomes and review (engine/review.py)

```python
@dataclass(frozen=True)
class RowOutcome:
    record_key; table_key; row_number
    count_status: CountStatus                  # M04: counted_passed, counted_approved, counted_corrected, not_counted_yet, set_aside
    location: LocationOutcome | None           # M05; counted rows only
    reasons: tuple[str, ...]                   # open reason IDs, each flagged holds_count, location or soft (P-VAL-3)
    set_aside_reason: str | None; kept_record_key: str | None
```

- A row counts when its count status is one of the three counted values (P-VAL-2). Open `holds_count` reasons and an open same-ID conflict make it `not_counted_yet`. An open copy group doesn't (P-VAL-3). Its rows stay counted, and the group widens the Goal 1 and Goal 2 ranges (COUNT-1). Location and soft reasons never change the count status. Address fields play no part: no address, a Hoboken ZIP and a Geosupport miss all count.
- REV-1. `approve` closes the row's open reasons and sets `counted_approved`. `set_aside` takes a reason code from `copy/reasons.toml` (`not_a_client`, `test_record`, `duplicate_other_system`, `out_of_scope`, `other`). The engine adds `summary_row` and `copy_of` itself. `accept_fill` closes the reasons the fill covers, re-runs P-STD and P-VAL on the row, and marks the location filled. `keep_one` counts the kept row and sets the rest aside with `copy_of` and the kept key. `not_copies` and `different_people` count every member and add a `different` verdict for each pair. `approved_as_entered` counts every member (M06 DUP-4, ID-5). Nothing is addressed by position.
- REV-2. `causes(outcomes, groups, routed) -> list[Cause]` groups open rows by reason ID into the three tabs of 8.1 (affects the counts, location, worth a look), largest first, ties by reason ID. Affects the counts holds every `holds_count` reason, the same-ID conflicts and the open copy groups (SPEC 8.1). A cause has a count, a title key, its allowed actions, `routed`, `tab` and `kind`. A row with two reasons appears in two causes and is counted once in `open_rows`.
  - `kind` is one of `fill_from_street`, `mapping_diagnosis`, `no_address`, `copies`, `same_id`, `settled`, `note` and `other`. It's the value M12 picks the actions by. `fill_from_street` is a location cause where M05's `propose_fills` has at least one proposal for its rows. `no_address` is a cause where every address field is blank. `settled` is a set of rows the engine set aside (summary rows). `note` is the cross-file note.
  - `diagnose_mapping(cause, table_mapping, profiles) -> MappingDiagnosis | None` gives a cause the `mapping_diagnosis` kind when every row in it comes from one table, the field it names is blank on those rows, and M02's `better_column` finds a column that is filled on them. `MappingDiagnosis(table_key, field, column_now, column_better, rows_fixed)` holds names and counts only. The registry builds the sentence ("City reads from REGION, which is blank on these rows, while BOROUGH is filled on all 1,842."), so the column names come from the session and never a literal.
  - `people_in_other_files(identity) -> int` counts master IDs whose counted records come from two or more source files. It feeds the cross-file note ("{n} people also appear in another file. Nothing needs doing.").
- REV-3. `keep_one_per_program(selection, groups, programs)` works on selected open rows. In each open `identical` or `possible` group, per program, it keeps the member with the smallest record key and sets the rest aside. It returns `kept`, `set_aside`, `left_alone`. It touches only rows in an open copy group. It never touches a row outside one or a `same_id_different` group. Every row it sets aside really leaves the counted rows and Final_Clean_Mapped, so nothing is marked set aside while it still counts (C-16).
- REV-4. A bulk action is one command writing one decision per row (one undo step, one audit entry with a count).
- REV-5 (8.4). `finish_gate(outcomes, routed) -> FinishGate(held, left, open_rows)`. It is held while any cause in the Affects the counts tab (`holds_count` causes, same-ID conflicts and open copy groups) has open rows and is not `routed` (SPEC 8.4). `left` lists those causes with counts for the caption. When it is not held, `open_rows` is the number of `not_counted_yet` rows still open, and a nonzero value needs the confirmation "N rows are still open. They stay in the review file and aren't counted. Finish anyway?". Location and soft causes never hold it. `SendToRowByRow(reason_id)` records a `route` decision. `FinishReview(confirmed_open_rows)` is a command that stores the count and the reviewer, and goes to the audit.

### Reviewers and bulk accepts (8.7)

- `current_reviewer(getuser=getpass.getuser)` gives the default name. `SetReviewer(name)` trims it and refuses an empty name, a control character or more than `reviewer_name_max` characters. The name goes on every later decision and into the audit. Fix problems asks for it when it first opens in a session (M12).
- `sample_rows(decision_id, record_keys, n=5)` ranks keys by `sha256(decision_id + record_key)` and returns the first five, sorted. This is the "seeded by the decision ID" pick, with no `random`. The same ID always gives the same rows.
- `check_accept(group_rows, proof, second, reviewer)` raises `BulkAcceptRefused(code)`. `AcceptProof(typed_count, reason_code)` has no note, because a bulk accept takes no free text (SPEC 8.7). Codes are `count_mismatch` (the typed count is not the group's row count), `reason_missing`, `second_signoff_needed` and `second_same_person` (the second name equals the first after trim and casefold). A second reviewer is needed when the group is over `second_signoff_rows` (200). The accept reasons are the `[accept]` list in `reasons.toml`: `checked_sample`, `matches_source`, `expected_in_this_file`, `other`. Choosing `other` opens no note box.
- `AcceptGroup(reason_id, record_keys, proof, second)` runs `check_accept`, then writes one `approve` decision per row. `ApproveRows` from the queue needs the same second sign-off over 200 rows (a reading; log it). `DecidePair` with `same` needs one when the merged group would hold more than `second_signoff_join_records` (5) records, counting rows.
- The audit entry carries `typed_count`, `reason_code`, `reviewer`, `second_reviewer` and `count`, and never a `note`. Only a Set aside with the reason Other carries a note (SPEC 8.1, CMD-4).
- `decisions_by_reviewer(decisions) -> tuple[ReviewerCount(reviewer, kind, count)]`, sorted, for the table that ends the internal audit log (M09).

### Corrections (6.6 P-REV-6, C-06)

M09 owns the signed review file and verifies signatures, original values and failing fields (8.6). This milestone applies what it passes on.

```python
@dataclass(frozen=True)
class VerifiedCorrection:  record_key: str; fields: tuple[tuple[str, str], ...]     # (field, new standardized text)
def apply_corrections(corrections, records, fingerprint) -> CorrectionReport        # accepted, refused with codes
```

- A row is matched by record key, never by position or range. An unknown key is `unknown_record`, a repeated key `duplicate_in_file`, a set-aside row `row_set_aside`. Refusals come back as a list of codes and keys.
- A correction changes only fields whose text differs from the current standardized text. The new text goes through P-STD and P-VAL. A row that now counts is `counted_corrected`. A row that still fails stays `not_counted_yet` with its new reasons. This is the conservative reading.
- The text stays in memory for the session. The `correction` decision holds the record key, field names and the file fingerprint, never the text (H9). If the file is not added again after a resume, the decision lapses with `file_removed`.
- Each change makes a `CORRECTION` entry with `old_hash` and `new_hash`, which are `KeyedHash` values from `keys.value_hash(secret, field, text)`, the HMAC of `field|text` truncated to 16 hex. The type has no public constructor except that function, so a value cannot reach the log.

### Counts and the balance (7.1 to 7.3, H4, C-12, C-19)

```python
@dataclass(frozen=True)
class Range:  low: int; high: int
@dataclass(frozen=True)
class Locations:  high: int; low: int; no_fixed_address: int; outside_nyc: int; address_problem: int; not_found: int; no_geocoder: int; filled: int
@dataclass(frozen=True)
class Counts:
    goal1: Range; goal2: Range; per_program: Mapping[str, Range]; people_without_program: Range
    open_pairs: int; open_copy_groups: int; received: int; counted: int; not_counted_yet: int; set_aside: int
    locations: Locations                       # counted = high + low + the five not-mapped reasons; filled is a subset of mapped
    final: bool; not_in_goal2: tuple[tuple[str, int], ...]; dob_coverage: tuple[int, int]
    matched_from_earlier: int | None           # M13 fills it; None while the saved crosswalk is off
```

- COUNT-1. Goal 1 is `Range(identity.low, identity.settled)` over counted rows. Goal 2 is the number of distinct (master, `canonical_program`) pairs among counted rows with a program. The high end uses `master_of_record`, the low end `low_master_of`, and each program uses the same two unions (C-12). The runner passes the open `identical` and `possible` copy groups to `resolve` as `open_copy_groups`, so the low end treats each open group as one person and the high end as different people (SPEC 7.2, M06 ID-9). Both are single numbers when `open_pairs` and `open_copy_groups` are 0. Rows not counted yet and set-aside rows never enter.
- COUNT-2. `final` is true only when `open_pairs == 0`, `open_copy_groups == 0`, `not_counted_yet == 0`, no program proposal is unconfirmed, and nothing upstream is stale. A count that is still a range is never final (a reading of SPEC 7.2, which names pairs; log it). Location problems never stop it. When false, `Counts` carries the codes the copy needs, such as "Settled for the rows counted so far. 1,232 rows aren't counted yet." and the open pair count (A-06, A-12). One object feeds Results, the ledger and the printable page.
- COUNT-3. `people_without_program` comes from M07, for both unions (C-19), over counted rows only.
- COUNT-4. `dob_coverage` is counted rows with a valid DOB over counted rows (fix plan 5.2 step 5). Results shows "Date of birth on 62% of counted rows" with the warning that movers may be counted twice without it.
- COUNT-5. `Balance` holds, per table, `received`, `counted`, `not_counted_yet`, `set_aside`, `mapped` and `counted_not_mapped`, plus `excluded_rows`, `non_table_rows`, `above_header_rows`, `header_rows` and the independent `file_rows` from M01. `assert_balance` checks three things and raises `BalanceError` carrying the numbers. (1) Per table, received = counted + not counted yet + set aside. (2) Per table, counted = mapped + counted not mapped. (3) Across the batch, the table totals plus the other four places equal the non-empty rows in the files (H4, with M01's shared-row term). `balance_lines(balance)` returns the two equations every screen and file uses, rows and locations (A-22).
- COUNT-6. `Session.counts()` returns `Counts` only if the balance holds and no node is stale. Otherwise it raises `BalanceError` or `StaleResults(nodes)`. Nothing shows or writes numbers around those errors. The check runs after every run and every decision.
- `Session.preflight()` wraps M05's `preflight` for the ledger and the system check (M10). `Results.practice` is true when the run used the sample reference, and `Results.release` carries the Geosupport release for M09.

### Confidence (7.4, H15)

`settings/confidence.toml`:

```toml
[batch]
high_counted_pct = 95
high_placed_pct = 95
high_open_pairs = 0
low_pct = 80
```

- CONF-1. Three measures. `counted` over `received` (set-aside rows stay in the denominator). `open_pairs`. `placed`, the counted rows mapped High over counted rows whose address was looked up (outcome mapped, or not found). Rows with no fixed address, outside NYC, an address problem or no geocoder were not looked up. Compare percentages by cross-multiplying integers, so 95 is exact. With `received == 0` there is no confidence.
- CONF-2. High needs counted at or above 95, zero open pairs, and placed at or above 95. Low is any available percentage under 80. Medium is anything else. When nothing was looked up, `placed` is not available and the level cannot be High.
- CONF-3. `BatchConfidence(level, parts, measures, calibration)`. `parts` lists the reasons the level is not High, in this order, with any measure under 80 first: `counted_short(counted, received)`, `pairs_open(n)`, `placed_short(high, looked_up)`, `placed_unavailable_no_geocoder` ("Addresses weren't placed, so confidence can't be High."), `placed_unavailable_none_looked_up`. The registry builds the sentence, such as "Medium. 6,084 of 7,412 rows are counted, and 14 possible same-person pairs are still open." For High it names all three measures. There are no percentages in the headline. `calibration` is `None` until M13 supplies the measured rates and date for the detail view.
- CONF-4. `AcknowledgeLowConfidence` records the three measures and the time in the audit, with the reviewer. The tick is tied to `Results.version` and resets when results are recomputed. `Session.download_gate()` returns `held` with reasons `low_confidence_unacked`, `stale` or `balance_failed`, or none.
- CONF-5. Match confidence. `AutoJoin` is Certain with its reason. A decided "same" pair is Certain with `confirmed_by_person`. An open proposal keeps its band. `master_match_confidence(master_id)` gives `certain`, `likely`, `possible` (the stronger open band) or `single`.
- CONF-6. Location confidence per counted row is High, Low or Not placed with its reason code. `Locations` feeds the ledger.

### Commands (3.4, 8.5, H13)

```python
class Command(Protocol):
    label: CopyRef                     # copy registry id and int/count parameters only
    invalidates: frozenset[Node]
    def apply(self, s: Session) -> CommandResult: ...
    def undo(self, s: Session) -> None: ...
    def audit_entry(self) -> AuditEntry: ...
```

- CMD-1. The commands are `ApproveRows`, `AcceptGroup`, `SetAsideRows`, `AcceptFills`, `KeepOneInCopyGroup`, `MarkNotCopies`, `DecideSameIdConflict` (different people, or approved as entered), `KeepOnePerProgram`, `SendToRowByRow`, `ReturnToOpen`, `DecidePair`, `DecideProgramGroup`, `ApplyCorrections`, `AcknowledgeLowConfidence`, `SetReviewer`, `FinishReview`, and one generic `SetupChange(section, key, new_value)` for the set-up sections (`sources`, `tables`, `steps`, `schema`, `mappings`, `defaults`, `date_orders`, `program_columns`, `run_settings`, `export_settings`). `SetupChange` keeps the old value for undo.
- CMD-2. `History.execute(cmd)` runs `apply`, pushes it, then calls `recompute_from` for the earliest node it made stale, only when that node is `decisions` or later. Set-up changes only mark nodes stale and wait for Process (10.4). `History.undo()` pops the last command of any kind, runs its `undo`, and recomputes before returning, so the next read never sees an undone state (C-04, C-14). There is no redo, and the stack is not saved.
- CMD-3. `ReturnToOpen` removes the earlier decisions on those rows and is undoable.
- CMD-4. `AuditEntry(code, fields)` takes fields only through typed slots: `record_key`, `table_key`, `letter`, `row_number`, `field_name`, `column_name`, `rule_id`, `decision_id`, `count`, `typed_count`, `program_name`, `backend_name`, `release`, `master_id`, `reason_code`, `reviewer`, `second_reviewer`, `time_iso`, `old_hash`, `new_hash`, `file_name` (only on `FILE_ADDED`, `RUN`, `DOWNLOAD` and `CORRECTION`), and `note` (a set-aside "Other" note up to 120 characters, after the warning, and internal only). A free string cannot be passed anywhere else. M09 decides which slots each log keeps. A test lists every command and checks its entry uses only these slots.
- CMD-5. The reviewer's name is on the `Decision` and in the audit entry (H8 lists it now).

### Staleness (10.4, C-18, H13)

- STALE-1. Nodes, in order: `sources`, `tables`, `steps`, `mappings`, `standardized`, `checks`, `geo`, `copies`, `decisions`, `identity`, `programs`, `counts`, `confidence`, `exports`. `schema` feeds `mappings`, `run_settings` feeds `geo`, `export_settings` feeds only `exports`. Identity verdicts and the saved crosswalk (a constant until M13) feed `identity`. Program groups feed `programs`. Review decisions feed `decisions`. The reviewer's name and calibration runs are not nodes.
- STALE-2. Every node has a fingerprint, the SHA-256 of its own inputs and its parents' fingerprints. A result stores the fingerprints it was made from. `Session.stale` is the set of nodes whose live fingerprint differs from the stored one. Each command also declares `invalidates`, and a property test proves the declared set contains every node the fingerprints call stale.
- STALE-3. Keep the last three results by fingerprint. Undoing a set-up change that restores the live fingerprints clears the stale state without a re-run.
- STALE-4. `Session.counts()`, `download_gate()` and any export function check `stale` first. The stage strip caption and the ledger read it to say "out of date" (M10).

### Runner

- `run(session, sink)` runs 6.10 end to end. Step 6 calls M05's `place_rows`. Step 8 replays decisions by record key. Step 9 builds `PersonRow`s from counted rows only, with person keys from `keys.person_key` and `key_modes` (which also splits rows that share only a name-based key, SPEC 5.1), then calls `resolve` with the open copy groups as `open_copy_groups`. The result reports `kept` and `lapsed` counts. It never clears decisions (C-07). The new state is built beside the old one and swapped at the end, so a cancel leaves the session unchanged.
- `fast_path(session, sink)` stops with `StopAtPrograms` when M07's gate says so, blocks with a named table and field when a required field has no mapping (P-MAP-2), and otherwise calls `run`. It has no code of its own for programs or identity.
- `preview_counts(session, program_decisions) -> Counts` works on a copy. It changes no decision, stale flag or undo entry (A-07).
- Progress steps are in 11.6.2. Report at least per 200 rows with `ProgressMessage`.

## Tests to write

The R fixture lives in `tests/fixtures/session/r_fixture.py`. Columns are Client_ID, First_Name, Last_Name, DOB, Address_1, City, State, Zip, Program. File R.csv (one system) has 15 rows.

- R01 to R06 are six clean people at 10 to 20 Oak St, Brooklyn 11201: Ada Lee 1980-01-01 Housing, Ben Cruz 1981-02-02 Housing, Cara Diaz 1982-03-03 Youth, Dev Rao 1983-04-04 Youth, Eli Fox 1984-05-05 Workforce, Fay Gil 1985-06-06 Workforce (house numbers 10, 12, 14, 16, 18, 20).
- R07 Gus Hall 1986-07-07, 22 Oak St, Housing, appears twice with identical cells (an `identical` group).
- R09 Hana Ito 1987-08-08, 24 Oak St, Youth, and R10 `HANA ITO` with the same facts (a `possible` group).
- R11 Ivy Jones 1988-09-09 and R11 Jon Kane 1975-10-10, 26 and 28 Oak St, Housing (a `same_id_different` group).
- R13 Kim Lu 1989-11-11, 85 Montague St, Brooklyn, blank ZIP, Workforce (fillable to 11201).
- R14 with a blank first name, Moss, 1990-12-12, 30 Oak St, 11201, Youth.
- A summary row with First_Name `Total` and everything else blank.

File S.csv (a second system) has S1 Ada Lee 1980-01-01 10 Oak St 11201 Housing and S2 Ben Cruz 1981-02-02 99 Elm St 11201 Housing. The test gazetteer holds every R and S address except 18 Oak St and 20 Oak St.

Base state, before any decision. 17 received, 13 counted (R01 to R06, both R07 rows, R09, R10, R13, S1, S2), 3 not counted yet (both R11 rows, R14), 1 set aside. The two copy groups stay counted (P-VAL-3).
- **Joins and proposals.** S1 joins R01 (`four_exact_facts`). The two R07 rows share a Client_ID-based person key, so they're one person record with a `same_system_id` join listed. R02 and S2 form a Likely proposal (score 104). R09 and R10 are an open `possible` copy group, so identity leaves them to P-DUP (M06 ID-13), and the group widens the range.
- **Counts.** Goal 1 is 9 to 11 and Goal 2 is 9 to 11 (Housing 3 to 4, Youth 3 to 4, Workforce 3).
- **Locations.** Twelve counted addresses were looked up and 10 are High. R05 and R06 are not found, and R13 is an address problem (blank ZIP), so 10 are mapped and 3 counted not mapped.
- **Confidence.** Low, because 13 of 17 is under 80 percent. Its parts are `counted_short(13, 17)`, `pairs_open(1)` and `placed_short(10, 12)`. Both balances hold.
- **Causes.** Affects the counts shows four causes (identical copies 2, possible copies 2, same ID 2, missing name 1), and Location shows one (R13).

Decided state. Keep one of the identical pair, `not_copies` on the possible pair, `approved_as_entered` on the same-ID rows, accept the fill for R13, set R14 aside as `out_of_scope`. Now 17 received, 14 counted, 0 not counted yet, 3 set aside, and no copy group is open. Open pairs are R02 with S2 and R11 with R11 (the Possible floor). Goal 1 is 11 to 13 and Goal 2 is 11 to 13. Fourteen counted addresses were looked up, 12 are High, 2 are not found, and 1 is a filled row. Confidence is Medium, with parts `counted_short(14, 17)`, `pairs_open(2)` and `placed_short(12, 14)`. Deciding both pairs "different" gives `final` true and 13 to 13.

Rule tests in `tests/rules/test_P_REV.py` (REV-1 to REV-5, corrections cases), `tests/rules/test_counts.py` (COUNT-1 to COUNT-6, CONF-1 to CONF-6, CMD-1 to CMD-5, STALE-1 to STALE-4) and `tests/rules/test_reviewers.py`. Audit tests in `tests/audit/` each have a line in `tests/audit/INDEX.md`.

- `test_C03_process_stale_identity.py`. The C-01 fixture from M06 (A.csv, B.csv, 12 records) plus a third system C.csv: C1 Dee Wu 1988-08-08 30 Pine St Brooklyn 11201 Youth, C2 Maria Rodriguez 1985-03-14 100 Grand Concourse Bronx 10451 Workforce, C3 Evan Cole 1972-04-04 8 Birch Rd Queens 11377 Housing. With C, Goal 1 is 9 to 13 and Goal 2 12 to 15 (C2 joins Maria by `four_exact_facts`). Exclude C.csv and Process again: Goal 1 7 to 11, Goal 2 9 to 12, 12 source records in the unique-client rows, all equal to a fresh Session given the same inputs. The audit's own numbers came from the old identity rule and are not asserted.
- `test_C04_undo_refresh.py`. For every command in CMD-1, take `Results.digest()` and the counts before, apply, undo, and assert equal digests, counts and row partitions. Include the C-04 case (approve the same-ID group, then Undo).
- `test_C06_corrections_by_record_key.py`. Six rows in A.csv, one A900 Zed Zimmer with a blank ZIP. Build `VerifiedCorrection`s from the engine's review output, setting `Zip` of A900 to 11201. Case 1: the source sorted by last name, apply. Only A900 changes, to `counted_corrected`, and counts equal the unsorted run with the fix. Case 2: a new client added at the top of the file. The correction still lands on A900. Case 3: the same key twice is `duplicate_in_file`. Case 4: an unknown key is `unknown_record` and a set-aside row `row_set_aside`. A correction that leaves the row failing keeps it not counted yet. No audit entry holds a value. M09 adds the file-level cases (signature, originals, failing fields).
- `test_C07_decisions_survive.py`. Make the four decisions of the audit's `s30`. Process again with nothing changed, run `preview_counts`, and run `fast_path`. Each time `session.decisions` is unchanged, `kept` is 4, `lapsed` is 0, and counts are equal.
- `test_C08_keep_copy_after_reexport.py`. Keep the second of two identical rows. Build a new Session from the same file with rows in another order and replay. The same record is kept. If the kept record's text changes, the group id changes, the decision lapses with `group_changed`, and the group is open again.
- `test_C09_every_problem_kind_opens.py`. `tests/fixtures/session/problem_rows.py` maps every problem ID in `wholecount/copy/problems.toml` to a row that triggers it. The test fails if the mapping and the file disagree. For each kind, build the open row, call `causes()`, and require a cause in the tab its flag names (Affects the counts for `holds_count`, Location for `location`, Worth a look for `soft`) with a registry title. An open copy group and a same-ID group land in Affects the counts with the `copies` and `same_id` kinds. Include the blank First_Name row that crashed the old screen.
- `test_C12_goal2_range.py`. The base state gives Goal 2 9 to 11 and Housing 3 to 4. A test-side union-find over the open proposals and the open copy groups gives the same low end for Goal 1, Goal 2 and each program.
- `test_C14_one_undo_stack.py`. Send a group to the queue, approve one queued row, set another aside. Undo three times. After each pop the state equals the state before the matching command, in reverse. The second undo does not say "nothing to undo" while a row decision remains.
- `test_C15_three_files_partition.py`. After each command type, `partition(results)` gives three sets of record keys that follow 7.3. Clean rows are the counted rows. Review rows are every row with an open problem, each marked Counted yes or no. Set-aside rows are separate. Clean rows plus review rows marked no plus set-aside rows equal received exactly.
- `test_C16_keep_one_per_program.py`. On the base state select all open rows and run `KeepOnePerProgram`. Result `kept` 2, `set_aside` 2, `left_alone` 4 (both R11 rows, R13, R14). The two set-aside rows have `copy_of`, leave the counted rows and are absent from the clean-file partition, so counted goes from 13 to 11 and Set_Aside grows by 2. No row outside a copy group changes. The audit entry carries the same three counts.
- `test_C18_stale_after_setup_change.py`. After a run and the decided state, apply each change without Process: exclude S.csv, map Last_Name to the Address column, set the R.csv header row to 2, confirm a program group. Each time `session.stale` equals the expected downstream set, `counts()` raises `StaleResults`, `download_gate()` is held with `stale`, and undo clears it (STALE-3). `date_orders`, `defaults`, `schema` and `run_settings` get the same check.
- `test_A06_final_wording.py`. Use `household.csv` with the H100 conflict decided as different people, plus one added row, H400, with a blank first name. `final` is false, with one row not counted yet and no pair or copy group open. Set H400 aside and `final` is true, even though H300 Zed Nobody has a blank ZIP, because a location problem alone never stops it (H300 is counted). `final` is false with a pair open, and false with a copy group open. The counts carry the number of rows not counted yet.
- `test_A07_preview_is_read_only.py`. Make decisions, call `preview_counts` with a program decision, and assert decisions, stale set and undo stack are unchanged.
- `test_A12_goal2_range_wording.py`. With pairs open, Goal 2 has a range and the same caveat code as Goal 1.
- `test_A22_one_equation.py`. After every command in a sequence, the ledger lines, the printable-summary data and the Download reconciliation all come from `balance_lines`, with three terms that sum to received and a locations line that sums to counted.

Other rule and property tests.

- `test_P_VAL_2_address_plays_no_part.py` (fix plan 5.1). Proof rows for a client with no address, a client in Hoboken with ZIP 07030, and a client whose address Geosupport cannot match. All three count in Goal 1, appear under counted not mapped with reasons `address_problem`, `outside_nyc` and `not_found`, and both balances hold. With no backend every counted row reads `no_geocoder`.
- `test_P_GEO_8_through_process.py` (C-10). Run Process on the R and S fixture with the fake backend, a reference backend and no backend. No crash, and each source places at least one address. The M05 test covers `place_rows`. This covers the whole run.
- `test_CONF_74.py`. Boundaries at exactly 95 and 80 (cross-multiplied), zero open pairs, nothing looked up cannot be High and the reason is the spec sentence, the spec example sentence for 6,084 of 7,412 with 14 open pairs, the parts order with a Low measure first, no confidence when nothing was received, and the acknowledgment resetting when results change.
- `test_8_7_bulk_accept.py`. `sample_rows` returns five keys from the group, the same five for one decision ID and a different set for another, and uses no `random`. The typed count must equal the row count. A reason is required. `AcceptProof` has no note field, and choosing `other` asks for none. A group of 200 needs no second reviewer and 201 does. A second name equal to the first is refused. A pair `same` decision that would merge six rows needs a second reviewer and five does not. The audit entry holds the typed count, reason code and both names. `decisions_by_reviewer` counts by reviewer and kind.
- `test_REV_2_cause_kinds.py`. Each `Cause.kind` comes from a fixture row. A City mapped to a column that's blank on the cause's rows, with another column filled on all of them, gives `mapping_diagnosis` with both column names and `rows_fixed`, and no cell value. `people_in_other_files` on the R and S base state is 1 (Ada Lee, joined across R and S).
- `test_8_4_finish_review.py`. Held while any Affects the counts cause, an open copy group included, is open and not routed. Routing it releases the hold. Location and soft causes never hold. The confirmation count is the not-counted-yet rows only. `FinishReview` goes to the audit with the count.
- `test_reviewer_default.py`. The default is the injected `getuser` result. `SetReviewer` refuses bad names. Every decision stores the name.
- `test_dob_coverage.py`. Counted rows with a valid DOB over counted rows, and the warning code when below 100 percent.
- `tests/invariants/test_balance.py` (random command sequences on the fixtures: both table equations and the batch equation hold after each step), `test_determinism.py` (same inputs and decisions give the same digest, and shuffled rows give the same record keys, outcomes and counts), `test_record_key_stability.py`, `test_undo_roundtrip.py`, `test_ranges.py` (`low <= high`, `final` implies a single number, deciding a pair "same" lowers `high` by one and keeps `low`, and an open copy group of two separate people widens the range by one) and `test_staleness.py`.
- Other tests. `test_decisions_hold_no_cell_values.py` (H9 scan), `test_audit_entry_slots.py` (CMD-4, including `KeyedHash` having no public constructor), `test_cancel_leaves_session.py`, `test_counts_refuse_when_unbalanced.py` (a corrupted `Results` raises `BalanceError`, for each of the three checks), `test_fast_path_equals_staged.py`, and claim tests in `tests/copy/` for the final wording, the confidence sentences, the finish-review confirmation, the bulk-accept prompts and the stale caption.

## Done when

- [ ] Every rule ID above has a named test. Every audit ID in Spec sections has its own file and a line in `tests/audit/INDEX.md`.
- [ ] The R and S fixture gives the numbers above in both states, and the C fixture gives its ranges.
- [ ] No code path shows counts or writes a file while a node is stale or either balance fails.
- [ ] No decision, audit entry or saved structure holds a cell value (the scan test passes).
- [ ] `grep` finds no `random` and no clock call in `engine/` or `session/` outside injected clocks (H3).
- [ ] No new dependency outside the approved set.
- [ ] The report's Questions for Joe list. (1) A count is never `final` while a copy group is open, since it's still a range (SPEC 7.2 names pairs). (2) "Joins more than 5 records" counts rows. (3) The second sign-off also applies to a queue bulk approve over 200 rows. (4) The accept reasons list and the set-aside reason IDs are mine. (5) With a geocoder present but nothing looked up, the sentence is my own. (6) A corrected row that still fails stays not counted yet. (7) Adapters written in `pipeline.py`.
- [ ] `make test`, `make offline` and `make copy` are green, with counts in the report.
- [ ] The report is written, the branch is pushed, the pull request is opened, and work has stopped.

## Windows checks for Joe

Run from the repo with the branch checked out. The commands print through the M00 printer, so counts and fixed labels only. Add the labels to `CountLabel`.

1. `.venv\Scripts\activate`, then `python -m pytest -q`. Expect no failures and the test count in the report.
2. `python -m wholecount.dev session-demo`. It runs the made-up R, S fixture and prints a block after each step. Base state, in order: `received 17`, `counted 13`, `not_counted_yet 3`, `set_aside 1`, `goal1_low 9`, `goal1_high 11`, `goal2_low 9`, `goal2_high 11`, `open_copy_groups 2`, `confidence_level 1` (1 is Low, 2 Medium, 3 High), `balance_ok 1`. After the five decisions: `counted 14`, `not_counted_yet 0`, `set_aside 3`, `goal1_low 11`, `goal1_high 13`, `confidence_level 2`. After two "different" verdicts: `goal1_low 13`, `goal1_high 13`, `final 1`. Then it undoes every step and prints the earlier blocks in reverse.
3. `python -m wholecount.dev session-check --csv "C:\path\a.csv" --csv "C:\path\b.csv"` on two of your real exports. Expect `balance_ok 1`, `received`, `counted`, `not_counted_yet`, `set_aside`, `mapped`, `counted_not_mapped` with the five reasons, `goal1_low`, `goal1_high`, `goal2_low`, `goal2_high`, `open_pairs`, `confidence_level`, `dob_coverage_pct`, and `step_1_tenths` to `step_7_tenths` for the time each step took. Check that `received` equals the non-empty rows you see in the two files, and that `counted_not_mapped` is plausible for your address data.
4. Run step 3 again. Expect identical lines apart from the step times.
5. Run step 3 with `--shuffle-rows`. Expect identical counts. Nothing depends on row position.
6. Run step 3 with `--exclude-last`. It drops the second file and prints the counts. Expect numbers equal to running the first file alone.
7. Run step 3 with `--decide-approve-all --process-twice`. Expect `decisions_kept` equal to `decisions_made` after the second run and `no_longer_apply 0`.

## Out of scope

- The screens: Fix problems, Results, the ledger, stage captions, the Undo button, the reviewer name prompt, the typed-count dialog, the confidence callouts and the held controls (M10 to M12). This milestone returns the data and codes they show.
- The signed review file, its signature and original-value checks, writing any output file, the audit text and the two logs, the printable page, the receipt, saved progress and resume (M09).
- Matching calibration, the saved crosswalk and `matched_from_earlier` (M13). `CalibrationNote` and the `known` and `inherited` inputs are the hooks.
- Dismissing items in the "No longer apply" list.
