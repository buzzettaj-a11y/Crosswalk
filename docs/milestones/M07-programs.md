# M07 Programs

## Goal

Decide which program each table feeds, propose which spellings of a program name are the same program, and keep every proposal inert until a person confirms it. Goal 2 counts one person once per program as grouped, so the grouping must be right, must not depend on which screen was opened, and must not merge Level 1 with Level 2. This milestone is engine only. The Programs screen comes in M11.

## Spec sections

- 6.9 (P-PROG-1 to P-PROG-6), 6.10 steps 10 and 12, and 7.2 for "without a program".
- 8.7 and 10.5 only as hooks. Every decision carries the reviewer's name (M08 wraps it), and program groups are one of the things the saved crosswalk re-applies (M13). Both need `ProgramDecision` to hold plain strings and an `inherited` flag, which PROG-9 adds.
- Audit findings closed: B-20, B-40, C-05, C-13, C-19.
- The ledger and Results wording for "not in Goal 2" is M08 and M12. This milestone returns the data.

## Depends on

- M04 for the Program field and per-source defaults (P-MAP-4).
- M06 for `IdentityResult.master_of_record` (record key to master ID, built from person keys). Only `people_without_program` reads a master mapping.
- M00 for the copy registry.

## Branch

`build/m07-programs`, created from the latest `main`.

## Read first

All paths are under `legacy/`.

- `program_names.py`: the constants `NOISE` (35), `STEM` (41), `SIMILAR_ENOUGH = 86` (47), `_fold` (50), `_key` (65), `_initial_forms` (82), `_is_acronym_of` (108), `_starts_the_same` (134), `suggest_groups` (150 to 222), `build_alias_map` (222), `apply_aliases` (231).
- `crosswalk_server.py`: `_program_group_state` (2321; it writes the alias map straight from the proposals, which is B-20), `programs_group` (3179; the label stays when a name is pulled out, which is C-13), `programs_preview` (3393), `express_run` (1705; it never calls `_program_group_state`, which is C-05), `_summary_payload` (2521; counts records where it says persons, which is C-19).
- `app.py:1740` to `1755`, the "agreed name" text that claimed an agreement nobody made.
- Audit inputs: `docs/audit/B-values.md` B-20 and B-40, `docs/audit/C-scripts/s12_fast_vs_staged.py`, `s22_remaining_probes.py` (part A), `s11_goal2_edges.py` (case f).

## What to build

### Files

```
wholecount/engine/programs.py        names, proposals, the program map, the fast-path gate
wholecount/settings/programs.toml    word lists and the similarity cutoff
tests/fixtures/programs/             name lists for B-40 (see Tests to write)
```

If M02 or M04 already made a per-table program summary, call it instead of rebuilding it.

### Data types

```python
@dataclass(frozen=True)
class TableProgram:     table_key: str; source: Literal["column", "default", "none"]; column: str | None; default: str | None; rows: int
@dataclass(frozen=True)
class ProgramName:      name: str; rows: int; tables: tuple[str, ...]          # name as entered, trimmed
@dataclass(frozen=True)
class Proposal:         proposal_id: str; members: tuple[str, ...]; label: str
                        reasons: tuple[tuple[str, str, str], ...]              # (name_a, name_b, reason code)
@dataclass(frozen=True)
class ProgramDecision:  kind: Literal["confirm", "split", "merge", "rename"]; members: tuple[str, ...]; label: str | None
                        inherited: bool = False      # re-applied from the saved crosswalk (M13)
@dataclass(frozen=True)
class ProgramMap:       groups: tuple[Group, ...]            # confirmed only
                        alias: Mapping[str, str]             # raw name to label, confirmed groups only
                        unconfirmed: tuple[Proposal, ...]
                        not_in_goal2: tuple[tuple[str, int], ...]   # (table_key, rows)
                        not_applied: tuple[tuple[ProgramDecision, str], ...]   # decision, reason code
```

Reason codes: `same_name`, `initials`, `nearly_same`, `more_words`. The engine returns only codes. The copy registry holds one sentence for each, and the proposal card shows it (P-PROG-2: "The screen states the reason for each proposal"), each with a claim test.

### Functions

```python
def program_sources(tables: Sequence[TableProgram]) -> tuple[list[ProgramName], list[tuple[str, int]]]
def propose_groups(names: Sequence[ProgramName], settings=None) -> list[Proposal]
def build_program_map(names, proposals, decisions: Sequence[ProgramDecision]) -> ProgramMap
def canonical_program(raw: str, pm: ProgramMap) -> str          # the raw name unless a confirmed group holds it
def fast_path_gate(pm: ProgramMap) -> Proceed | StopAtPrograms   # StopAtPrograms.unconfirmed is a count
def people_without_program(master_of_record: Mapping[str, str], record_program: Mapping[str, str | None]) -> int   # keys are record keys
def audit_fields(decision: ProgramDecision) -> dict               # kind, program names, label; no client data
```

`build_program_map` is the only code that builds the map. The staged route, the fast path and the preview all call it (C-05).

### Rules

- PROG-1 (P-PROG-1). A table has one program source. A column wins over a default. A table with neither goes to `not_in_goal2` with its row count. Blank cells in a table with a column are rows without a program, not a program.
- PROG-2 (P-PROG-2). A pair of names is proposed when one of these holds, tried in this order. Fold names with NFKD, lower case, `&` to `and`, punctuation to spaces.
  1. `same_name`: the keys are equal. The key is the folded tokens minus the `noise` words, with each short form in `stems` expanded (dev to development), sorted. `Workforce Dev.` and `Workforce Development`, `youth` and `Youth`, `Summer Youth Employment` and `Summer Youth Employment Program` qualify.
  2. `initials`: one name is written in capitals as typed (2 to 6 letters, dots allowed) and its letters line up, in order, with the words of the other name. Each word contributes a chunk of one or more letters that begins with the word's first letter and is a subsequence of the word. `WFD` matches `Workforce Development` and `Workforce Dev.`. `SYEP` matches `Summer Youth Employment Program`. The other name needs at least two words. Try the full word list and the list minus noise words.
  3. `nearly_same`: the keys have a `difflib.SequenceMatcher` ratio of at least `similarity` (0.86), and the pair is not vetoed.
  4. `more_words`: after dropping noise, the shorter name's tokens are the start of the longer name's tokens, the shorter name's first token has at least 4 letters, and every extra word is in `ending_ok` (only `development`). `Workforce` and `Workforce Development` qualify.
- PROG-2b (the one more rule). A veto applies to rules 3 and 4. Take the tokens, after noise and stems, that appear in one name and not the other. If any token holds a digit, is a single letter, or is in `meaning_words`, the pair is not proposed. This is what keeps Level 1 from Level 2, Cohort 2023 from Cohort 2024, Section B from Section C, and Youth Services from Youth Employment. A short form of the same word is never in the difference, because stems are expanded first.
- PROG-2c (no chains). A proposal is a set where every pair of members passed PROG-2. Build sets greedily: sort names by (rows descending, name), start a set with the first unused name, and add a later name only if it pairs with every member. A name is in at most one proposal. Sets of one are not proposals. A prototype of these rules reproduced every case in B-40.
- PROG-2d (label). A set's label is its member with the most rows, then the longest name, then the first in alphabetical order. The label is always computed from the current members, and no two groups may share a label or take the name of a program outside the group (a `rename` that collides is refused with `label_taken`).
- PROG-3 (P-PROG-3, B-20). Only `confirm` and `merge` decisions create entries in `groups` and `alias`. A `Proposal` with no decision lands in `unconfirmed` and changes nothing. `canonical_program` of a name outside a confirmed group returns the name as entered. The map holds two lists, proposed and confirmed, and they are never mixed.
- PROG-4 (P-PROG-4, C-05). `fast_path_gate` returns `StopAtPrograms(unconfirmed=n)` when `unconfirmed` is not empty, else `Proceed`. It never builds groups on its own. The staged route and the fast path give equal `ProgramMap` values for the same names and decisions.
- PROG-5 (P-PROG-5, C-13). A `split` decision takes one name out of its group, including the label name. The group's label is recomputed with PROG-2d. A group left with one member dissolves, and its remaining name stands alone. Counts must change: a person who appears under both spellings counts under both.
- PROG-6 (P-PROG-6). `audit_fields` returns the decision kind, the program names involved and the label. Program names are not client data. It never returns row counts per person or any cell from a person row.
- PROG-7 (decisions survive, H12). A decision whose member names are not all present in the current `names` is still applied to the members that are present, if at least two remain. Otherwise it goes to `not_applied` with reason `names_gone`. M08 shows that list under "No longer apply".
- PROG-8 (C-19). `people_without_program` counts master IDs none of whose records has a program, after the map. A person with a program on any record is not counted. Only counted rows are passed in (P-VAL-2), whether or not they are mapped.
- PROG-9 (10.5 hook). A decision with `inherited=True` applies exactly like one made in this batch, for the members that are present, and a batch decision on the same names wins. `ProgramMap` marks a group `from_earlier_batch` when only inherited decisions confirmed it, so Results can say so. An inherited decision whose members are all gone is dropped without a `not_applied` entry, since it was never made in this batch.

### settings/programs.toml

```toml
similarity = 0.86
caps_min_letters = 2
caps_max_letters = 6
noise = ["program","programs","prog","service","services","svc","svcs","department","dept","division","div",
         "unit","team","office","initiative","project","the","of","and","for","a","an","client","clients",
         "participant","participants","general"]    # a trailing single "a" is kept (Class A)
ending_ok = ["development"]
meaning_words = ["youth","senior","seniors","adult","adults","child","children","family","families","employment",
                 "housing","education","health","mental","tenant","tenants","immigration","legal","food",
                 "benefits","veterans","women","men","teen","teens","early"]
[stems]            # short form = full word
dev = "development"
admin = "administration"
mgmt = "management"
svcs = "services"
res = "resident"
comm = "community"
educ = "education"
empl = "employment"
trng = "training"
asst = "assistance"
hsg = "housing"
wf = "workforce"
```

## Tests to write

Rule tests in `tests/rules/test_P_PROG.py`, one case per rule ID above (`test_P_PROG_1_...`, `test_PROG_2c_no_chains`, and so on). Unit tests in `tests/unit/test_programs_settings.py` (the file loads, no word is in both `noise` and `meaning_words`).

Audit tests in `tests/audit/`, each with a line in `tests/audit/INDEX.md`.

- `test_B20_unconfirmed_proposals.py`. Three files with programs `Workforce Dev.` (5 rows), `Workforce Development` (9), `Youth Services` (9), `Youth Employment` (7), `Level 1` (4), `Level 2` (3). Run `propose_groups` and `build_program_map` with no decisions. One proposal exists (the two Workforce names, reason `same_name`). `alias` is empty and `groups` is empty. `canonical_program` returns every name unchanged. `fast_path_gate` stops with `unconfirmed=1`. Add one `confirm` decision. Only that group is in `alias`, and the label is `Workforce Development`. Youth and Level names still stand alone. `audit_fields` of the decision names the two programs and the kind, and nothing else.
- `test_B40_program_proposals.py`. A fixture list in `tests/fixtures/programs/b40_pairs.csv` with columns `a,b,expect`. For each pair, `propose_groups` on exactly those two names (one row each) returns a proposal or not.
  - Proposed: `Workforce Dev.` with `Workforce Development` (`same_name`); `WFD` with `Workforce Development` (`initials`); `WFD` with `Workforce Dev.`; `SYEP` with `Summer Youth Employment Program` (`initials`); `Summer Youth Employment` with `Summer Youth Employment Program` (`same_name`); `Workforce` with `Workforce Development` (`more_words`); `youth` with `Youth` (`same_name`).
  - Not proposed: `Youth Services` with `Youth Employment`; `Youth Services` with `Youth Housing`; `Youth Employment` with `Youth Housing`; `Senior Services` with `Senior Housing`; `Senior Services` with `Senior Employment`; `Senior Housing` with `Senior Employment`; `Level 1` with `Level 2`; `Cohort 2023` with `Cohort 2024`; `Section B` with `Section C`; `ESL Level 1` with `ESL Level 2`; `ESL 1` with `ESL 2`; `Tier 1` with `Tier 2`; `3K` with `4K`; `Group A` with `Group B`; `Class A` with `Class B`; `Adult` with `Adult Day Care`; `Adult Education` with `Adult`; `Adult` with `Adult Literacy`; `Adult Education` with `Adult Literacy`; `GED` with `GED Prep`; `Health` with `Hospital Employment Assistance Linkage Training Hub`; `Pre-K` with `Pre-K Extended Day`; `Tenant Services` with `Tenant Organizing`; `Food Pantry` with `Food Stamps`; `Youth Employment` with `Youth Empowerment`; `Mental Health` with `Mental Hygiene`; `Housing Counseling` with `Housing Court`.
  - Chains: `Youth Services`, `Youth Employment`, `Youth Housing` together give no proposal that holds all three. `Senior Services`, `Senior Housing`, `Senior Employment` and `Adult Education`, `Adult`, `Adult Literacy` likewise give no proposals.
  - Every proposal carries a reason code in the four allowed values.
  - `English as a Second Language` with `ESL` is not required either way. It has no audit basis, so leave it out of the file.
- `test_C05_fast_vs_staged.py`. The `s12` fixture. A.csv has Ana Perez 1990-05-06 in `Workforce Development` and Bo Lee 1991-01-01 in `Youth`. B.csv has the same two people in `Workforce Dev.` and `youth`. Two proposals, both `same_name`. Staged route: open Programs, confirm both, build the map. Fast route: same decisions, build the map through `fast_path_gate`. The two `ProgramMap` values are equal, and `canonical_program` agrees on all four names. With no decisions, `fast_path_gate` stops with `unconfirmed=2` and the map leaves four names. The test computes distinct (person, program) pairs from hard-coded masters: 2 with the groups confirmed, 4 without. The audit's staged value was 2 and the fast value was 4. An import test shows `fast_path_gate` is the only thing the fast path calls, and that nothing else constructs a `ProgramMap`.
- `test_C13_ungroup_own_name.py`. Group `Workforce Development` (1 row) and `Workforce Dev.` (1 row), confirmed. The label is `Workforce Development` (tie on rows, longer name). Take the label name out with a `split`. The group dissolves, both names stand alone, and Ana, who appears under both, counts 2 distinct programs. Then a three-name group (`Workforce Development`, `Workforce Dev.`, `Workforce`). Take out the label name: the label is recomputed from the two left, and no group shares a label with another.
- `test_C19_without_program.py`. A.csv: Ana Lee 1990-01-01 Housing, Bo Kim 1991-02-02 Youth, Di Fox 1992-03-03 with a blank program. B.csv has no Program column and holds Ana Lee and Bo Kim again with the same facts. Records without a program: 3. `people_without_program` returns 1 (Di). People: 3. Goal 2 pairs: 2.

Other tests.

- `test_P_PROG_1_not_in_goal2`: a table with no column and no default is listed with its row count. A table with a default counts all its rows under that default.
- `test_PROG_7_names_gone`: a confirm decision for three names where one is no longer present applies to the other two. A decision whose members are all gone appears in `not_applied` with `names_gone`.
- `test_PROG_9_inherited`: an inherited confirm for `Workforce Dev.` and `Workforce Development` makes the group confirmed with `from_earlier_batch`. A batch `split` of the same names wins. An inherited decision for names that are not in the batch changes nothing and lists nothing.
- Property tests in `tests/invariants/test_programs_properties.py` (hypothesis):
  - Shuffling the input names or their order gives the same proposals and the same labels.
  - No name is in two proposals. Every pair inside a proposal is a pair that passed PROG-2 on its own.
  - Two names that differ only by a digit, a single letter or a year are never in one proposal, for generated names built from a base name plus a suffix.
  - `canonical_program` is idempotent. Labels are unique across groups. The confirmed groups partition their members.
  - With no decisions, `alias` is empty for any input (B-20).
- `tests/copy/`: claim tests for the four reason sentences, the held caption "Continue to Process is held until every proposal is confirmed or split. 3 left." (the caption text uses a count parameter), and the "not in Goal 2" sentence.

## Done when

- [ ] Every rule ID above has a named test, and each of the five audit findings has its own test file.
- [ ] `tests/audit/INDEX.md` has a line for B-20, B-40, C-05, C-13 and C-19.
- [ ] Every pair in `b40_pairs.csv` behaves as listed, and the chains give no three-name group.
- [ ] No code outside `build_program_map` writes an alias entry. A grep test confirms it.
- [ ] No new dependency outside the approved set. `difflib` and `unicodedata` are standard library.
- [ ] The report's Questions for Joe list: (1) Case-only variants such as `youth` and `Youth` are proposals that need confirming, as P-PROG-3 says, and so the fast path stops at Programs for them. Is that the wanted behavior? (2) Short ending words other than `development` are not accepted by `more_words`. (3) A name is in at most one proposal, so `WFD` can be left out when `Workforce` is also present. (4) `ESL` and `English as a Second Language` are not proposed.
- [ ] `make test`, `make offline` and `make copy` are green, with counts in the report.
- [ ] The report is written, the branch is pushed, the pull request is opened, and work has stopped.

## Windows checks for Joe

Run from the repo with the branch checked out. Nothing here prints a client value.

1. `.venv\Scripts\activate`, then `python -m pytest -q`. Expect no failures and the test count in the report.
2. `python -m wholecount.dev programs-demo`. It runs the made-up B-40 names, which are the same names as the audit. The commands below print through the M00 printer, so add these labels to `CountLabel`. Expect `pairs_that_should_match 7`, `pairs_matched 7`, `pairs_that_should_not_match 27`, `pairs_left_alone 27` and `chains_grouped 0`.
3. `python -m wholecount.dev programs-check --csv "C:\path\to\your_file.csv" --column Program`, using a real file and its program column. Expect only counts, for example `distinct_names 18`, `proposals 3`, `proposals_same_name 2`, `proposals_initials 1`, `proposals_nearly_same 0`, `proposals_more_words 0`, `names_left_alone 12`, `rows_without_program 140`. It prints no program names, because they come from your file. Compare `distinct_names` to what you see when you filter that column in Excel. Compare the proposal count to the number of near-duplicate spellings you expect.
4. Run the same command on two files at once (`--csv a.csv --csv b.csv --column Program`). Expect `distinct_names` to equal the number of different spellings across both files.
5. Run step 3 twice. Expect identical output both times.

## Out of scope

- The Programs screen: the numbered sections, the proposal cards, the held Continue button, Preview the counts (M11). Preview must run on a copy of the state and never clear decisions (A-07), which M08 builds and tests.
- Goal 2 itself, its range, and the per-program table (M08). This milestone returns the map and `people_without_program`.
- Saving program groups in saved progress, and the "No longer apply" list (M08 and M09). The saved crosswalk's store of program groups and the choice of which to inherit (M13).
- The reviewer's name and the time on a program decision (M08's `Decision`).
- Writing the program audit lines (M08 and M09). `audit_fields` supplies the content.
- Any matching between program names and external lists.
