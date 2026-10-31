# M06 report

## Questions for Joe

Nothing blocks this milestone. These are the eight readings the milestone asked me to state. Tell me if you want any changed.

1. **The Possible floor after "approved as entered" (ID-5).** Two records in one system with one Client ID and different person keys exist only because a reviewer kept them apart as entered. With no "different" verdict on the pair, they're always compared and shown as at least a Possible proposal, with the evidence "same Client ID in the same system, but the details differ", even when their score is under the line. I read P-DUP-3 as "at least Possible". After "different people" they're never proposed.
2. **A blank date of birth in a table that has a date of birth column groups with nothing (DUP-2).** Without that rule, two rows with the same name and no dates would group on name alone, which B-47 forbids.
3. **"Not copies" also stores a "different" verdict.** So identity never asks the reviewer about the same pair again.
4. **`likely_min` is 90.** It's new, and chosen so every pair in the C-01 fixture is Likely. The calibration in M13 measures it.
5. **The block keys are P-ID-1's four, plus `id:`.** K1 surname with DOB, K2 surname with address, K3 given name with DOB, K4 surname with given name. K1 and K3 also match on birth year and on month and day, so a swapped day and month or a one-digit year typo still meet. Every key has a swapped-name form. The old lone DOB and lone address keys are gone.
6. **The `row` key mode.** It covers two cases. Rows split by a decision whose details would still give them one key get a key made from the record key alone. So does every counted row with no Client ID whose name-based key another counted row shares. That's how SPEC 5.1's "a name-based key never joins by itself" holds.
7. **Rows with no Client ID in different tables can still join by `four_exact_facts`.** That's a named reason in P-ID-3, not the shared key on its own.
8. **When a tool-made saved link stops holding, the key linked first keeps the saved master ID.** The other group takes its derived ID, and its keys are listed in `released`. A link a reviewer made still joins, as `earlier_batch` with a split action.

**The C-01 numbers differ from the audit's.** The audit counted 7 to 10 people, 3 open pairs and 2 automatic joins. Its old address key dropped the street type, so Luis Diaz at 123 45th St and at 123 45th Ave looked like one address and joined. With the type kept (C-24), that pair is a proposal. So the fixture gives 7 to 11 people, 4 open pairs and 1 join. P-ID-4 says the spec's rules decide the numbers. The fixture's true count, 10, is inside the range.

Choices made on the most conservative reading:
- **Two batch verdicts on one pair that disagree: "different" wins**, so a conflict never joins anyone. M08 replaces a decision instead of stacking it, so this should only matter if a caller makes a mistake.
- **DUP-3 looks at every row with one Client ID across all tables of one system.** Rows in a same-ID group are left out of the identical and possible copy checks, so a row is in one group.
- **A row joins a possible copy group only if every program in the group agrees** (blank allowed). So a chain through a blank program never mixes two enrollments.
- **`four_exact_facts` compares the whole folded given name and the surname without its suffix.** It also needs equal suffixes, and equal units when both rows have one.
- **A person record's facts come from its most complete row.** Ties go to the smallest record key.
- **A saved master link joins two groups when either key was linked by a reviewer.** The anchor is the key linked first.
- **Proposals are left out between two records that are already in one group.**
- **Evidence carries codes only, never parameters**, so nothing from a row reaches a proposal's data (H8).

Interface notes for M08, each a small addition to the milestone's sketch:
- `AutoJoin.pair` holds record keys for `same_system_id`, as ID-0 asks, and person keys for the other two reasons.
- `CopyOutcome.verdict_pairs` holds record key pairs. The caller turns them into `PairVerdict`s once the rows are keyed.
- `key_modes` takes the counted rows as `rows`, because finding shared name-based keys and equal details keys needs them.
- `CopyGroup` has `same_client_id`, which `NotCopies` checks. `split_group(record_keys)` builds the group that ID-7 splits.
- The nickname groups live in `wholecount/engine/data/nicknames.toml`, a new data package.

## What was built

- **P-DUP-6, names.** `engine/names.py`: `words`, `given_keys`, `same_given`, `surname_tokens`, `suffix_of` and `surname_core`. It reuses M01's `fold`. The 92 nickname groups are ported as data into `engine/data/nicknames.toml`.
- **P-DUP-1 to P-DUP-5, DUP-7.** `engine/copies.py`: `find_copies`, `CopyRule`, `apply_copy_decision` with the four decisions and `Unresolvable`, `group_id`, `key_modes` and `split_group`.
- **P-ID-1 to P-ID-7, ID-0 to ID-13.** `engine/identity.py`:
  - `resolve`, `score_pair`, `score_from_codes`, `master_id`, `block_keys` and `four_exact_facts`
  - the result types, including `PairVerdict.audit_fields` and the `known`, `inherited`, `keep_compared` and `open_copy_groups` hooks
- **Settings.** `settings/identity.toml`, with the weights, bands and limits.
- **Copy.** Sentences for the 16 evidence codes, the three join reasons, the two bands, the three copy causes and the open-group line, each fact with a claim test.
- **Dev commands.** `people-demo` and `people-check`.

## Tests

| Command | Result |
| --- | --- |
| `make test` | 1706 passed |
| `make offline` | 60 passed |
| `make copy` | 323 passed |

`make test` and `make copy` include this report's own lint test.

New test files:
- `tests/rules/`: `test_P_DUP.py` (P-DUP-1 to P-DUP-6, DUP-7), `test_P_ID.py` (P-ID-1 to P-ID-7, ID-5, ID-9 to ID-12), `test_P_ID_1_people_who_moved.py`, `test_ID_0_name_key_never_joins.py`, `test_ID_8_earlier_batch.py`, `test_ID_13_copy_groups.py`
- `tests/unit/`: `test_names.py`, `test_settings_identity.py`, `test_dev_people.py`
- `tests/copy/test_people_copy.py`
- `tests/invariants/test_identity_properties.py` (hypothesis)
- Fixture builders: `tests/fixtures/people/builders.py`

Audit IDs closed:

| ID | Severity | Test |
| --- | --- | --- |
| A-05 | High | `tests/audit/test_A05_same_id_merge.py` |
| B-36 | Medium | `tests/audit/test_B36_same_id_across_files.py` |
| B-37 | Medium | `tests/audit/test_B37_identical_record.py` |
| B-38 | Medium | `tests/audit/test_B38_saved_copy_decision.py` |
| B-39 | Medium | `tests/audit/test_B39_accent_folding.py` |
| B-47 | Low | `tests/audit/test_B47_default_copy_rule.py` |
| C-01 | High | `tests/audit/test_C01_auto_join_score.py` |
| C-02 | High | `tests/audit/test_C02_same_system_id.py` |
| C-17 | Medium | `tests/audit/test_C17_client_id_scope.py` |
| C-20 | Medium | `tests/audit/test_C20_master_id_stability.py` |
| C-21 | Medium | `tests/audit/test_C21_identity_verdict_audit.py` |
| C-24 | Medium | `tests/audit/test_C24_address_key.py` |

## Done list

- [x] Every rule ID has a named test. Every audit ID has its own test file and a `done` line in `tests/audit/INDEX.md`.
- [x] The C-01 fixture gives 1 join, 4 proposals and 7 to 11, and this report explains the difference from the audit's 7 to 10.
- [x] No score threshold decides a join in `engine/identity.py`. `test_P_ID_3_joins_only_for_named_reasons` and `test_no_score_threshold_decides_a_join` check it.
- [x] The 92 nickname groups are in `nicknames.toml`, and the master ID vectors pass.
- [x] No new dependency.
- [x] The report's Questions for Joe list covers the eight points.
- [x] `make test`, `make offline` and `make copy` are green, with the counts above.
- [x] This report is written, the branch is pushed, and the pull request is open.

## Windows checks

Run from the repo with the branch checked out. Dev commands print counts and never a name.

- [ ] 1. `.venv\Scripts\activate`, then `python -m pytest -q`. Expect no failures, and the test count above.
- [ ] 2. `python -m wholecount.dev people-demo`. It builds the 12-record fixture in memory. Expect `automatic_joins 1`, `joins_four_exact_facts 1`, `joins_same_system_id 0`, `proposals_likely 4`, `proposals_possible 0`, `people_low 7`, `people_high 11`, `master_ids_unique 1`. If `people_high` is 10 or `automatic_joins` is 5, something regressed.
- [ ] 3. `python -m wholecount.dev people-check --csv "C:\path\to\one_file.csv" --system A` on a real export, with `--first --last --dob --client-id --address --zip` if your column names differ. Expect `rows_read`, `copy_groups`, `copy_groups_identical`, `copy_groups_possible`, `copy_groups_same_id_different`, and `proposals 0` for a single file. It writes nothing. Compare the copy group counts to what you expect from that file. It reads dates written as YYYY-MM-DD or M/D/YYYY and treats any other date as blank.
- [ ] 4. Run it with two files (`--csv a.csv --csv b.csv --system A --system B`). Expect `automatic_joins`, `proposals_likely`, `proposals_possible`, `name_only_proposals`, `people_low` and `people_high`. Most cross-file matches should be proposals for you to decide, so `automatic_joins` should be small next to the number of people you expect in both files. If your files carry no date of birth, expect `name_only_proposals` above 0 only for rare names.
- [ ] 5. Run step 4 twice. The two outputs are identical, line for line.

## Screens

None. M06 is engine only.

## Not done

Nothing.
