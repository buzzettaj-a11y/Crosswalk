# M07 report

## Questions for Joe

Nothing blocks. These are the four points the milestone asked me to raise. The default is built in each case.

1. **Spellings that differ only by case, like `youth` and `Youth`, are proposals you have to confirm.** That's what P-PROG-3 says. So the fast path stops at Programs for them too. Is that what you want, or should case-only variants group without asking?
2. **`more_words` accepts only `development` as an extra ending word.** `Workforce` and `Workforce Development` are proposed. `Workforce` and `Workforce Training` aren't. More words can go into `ending_ok` in `settings/programs.toml` once you've seen real lists.
3. **A name is in at most one proposal.** So when `Workforce`, `Workforce Dev.`, `Workforce Development` and `WFD` are all present, `WFD` can be left out of the group, because it doesn't pair with `Workforce` by itself. You can still merge it in on the Programs screen.
4. **`ESL` and `English as a Second Language` aren't proposed.** The initials rule needs every word to give at least one letter, and three letters can't cover the five words (four without "a"). The audit has no case for it, so it isn't in the test file either way.

Choices made on the most conservative reading:
- **A proposal is settled once any decision touches one of its names.** So a `split` on an unconfirmed proposal turns it down.
- **`confirm` takes its names out of any group they were in.** `merge` joins whole groups.
- **A label that collides is refused with `label_taken`**, whether it comes from a `rename` or from a `confirm` that carries a label. A refused `confirm` still groups its names under the computed label.
- **Inherited decisions apply first**, so a batch decision on the same names wins. A group is `from_earlier_batch` only when no batch decision touched it.
- **`programs-check` counts a proposal under every reason its pairs carry.** So the four reason counts can add up to more than `proposals`.

Interface notes for M08 and M11:
- `TableProgram` gains `values`, which holds the row count for each name in a column. A column table's names have to come from somewhere, and the milestone's sketch had no field for them.
- `build_program_map` takes `not_in_goal2` from `program_sources`, so the map carries that list.
- `pair_reason(a, b)` and `label_of` are public, for the proposal card and the property tests.

## What was built

- **P-PROG-1 to P-PROG-6, PROG-2b to PROG-9.** `engine/programs.py`:
  - `program_sources`, `pair_reason`, `propose_groups` and `build_program_map`
  - `canonical_program`, `fast_path_gate`, `people_without_program` and `audit_fields`
  - the data types, including `Group.from_earlier_batch` and `ProgramDecision.inherited`
- **Settings.** `settings/programs.toml`, with the word lists, short forms and the 0.86 cutoff.
- **Copy.** The four reason sentences, the held caption with its count, the "not in Goal 2" sentence and the "a proposal changes no count" line, each with a claim test.
- **Dev commands.** `programs-demo` and `programs-check`.

## Tests

| Command | Result |
| --- | --- |
| `make test` | 1783 passed |
| `make offline` | 60 passed |
| `make copy` | 331 passed |

`make test` and `make copy` include this report's own lint test.

New test files:
- `tests/rules/test_P_PROG.py`: P-PROG-1 to P-PROG-6, PROG-2b, PROG-2c, PROG-2d, PROG-7 to PROG-9, and the grep test that no code outside `build_program_map` writes an alias entry
- `tests/unit/test_programs_settings.py` and `tests/unit/test_dev_programs.py`
- `tests/invariants/test_programs_properties.py` (hypothesis)
- `tests/fixtures/programs/b40_pairs.csv`: 7 pairs proposed, 27 kept apart

Audit IDs closed:

| ID | Severity | Test |
| --- | --- | --- |
| B-20 | High | `tests/audit/test_B20_unconfirmed_proposals.py` |
| B-40 | Medium | `tests/audit/test_B40_program_proposals.py` |
| C-05 | High | `tests/audit/test_C05_fast_vs_staged.py` |
| C-13 | Medium | `tests/audit/test_C13_ungroup_own_name.py` |
| C-19 | Medium | `tests/audit/test_C19_without_program.py` |

## Done list

- [x] Every rule ID has a named test, and each of the five audit findings has its own test file.
- [x] `tests/audit/INDEX.md` has a `done` line for B-20, B-40, C-05, C-13 and C-19.
- [x] Every pair in `b40_pairs.csv` behaves as listed, and the three chains give no three-name group.
- [x] No code outside `build_program_map` writes an alias entry, and no function other than `build_program_map` constructs a `ProgramMap`. Grep and AST tests check both.
- [x] No new dependency. `difflib` and `unicodedata` are standard library.
- [x] The report's Questions for Joe list covers the four points.
- [x] `make test`, `make offline` and `make copy` are green, with the counts above.
- [x] This report is written, the branch is pushed, and the pull request is open.

## Windows checks

Run from the repo with the branch checked out. Nothing here prints a client value.

- [ ] 1. `.venv\Scripts\activate`, then `python -m pytest -q`. Expect no failures and the test count above.
- [ ] 2. `python -m wholecount.dev programs-demo`. It runs the made-up B-40 names. Expect `pairs_that_should_match 7`, `pairs_matched 7`, `pairs_that_should_not_match 27`, `pairs_left_alone 27` and `chains_grouped 0`.
- [ ] 3. `python -m wholecount.dev programs-check --csv "C:\path\to\your_file.csv" --column Program`, using a real file and its program column. Expect only counts: `distinct_names`, `proposals`, `proposals_same_name`, `proposals_initials`, `proposals_nearly_same`, `proposals_more_words`, `names_left_alone` and `rows_without_program`. It prints no program names. Compare `distinct_names` to what you see when you filter that column in Excel, and the proposal count to the number of near-duplicate spellings you expect.
- [ ] 4. Run the same command on two files at once (`--csv a.csv --csv b.csv --column Program`). Expect `distinct_names` to equal the number of different spellings across both files.
- [ ] 5. Run step 3 twice. Expect identical output both times.

## Screens

None. M07 is engine only.

## Not done

Nothing.
