# M06 Copies and the same person across files

## Goal

Find copies inside one file and conflicting uses of one Client ID inside one source system. Then work out which counted records across files are the same person, over every counted row whether or not its address was placed. The only joins made without asking are the three named reasons in P-ID-3 (`same_system_id`, `four_exact_facts` and `earlier_batch`), and the matcher returns the reason as a value. Every other likely pair is a proposal with plain evidence, including people who moved and have no date of birth. A name-based person key never joins rows by itself (SPEC 5.1). Open copy groups keep their rows counted and widen the range (P-VAL-3, SPEC 7.2). A person is identified by a person key, so a master ID survives a re-export and deciding one pair renumbers nobody else. Decisions on pairs are stored per pair of person keys with the reviewer's name. This milestone is engine only. Commands, the audit lines and the screens come later.

## Spec sections

- 5.1 (person key, including the rule that a name-based key never joins by itself), 5.3 (master IDs), 6.5 P-VAL-3 (open copy groups don't hold the count), 6.7 (P-DUP-1 to P-DUP-6), 6.8 (P-ID-1 to P-ID-7, with `earlier_batch` in P-ID-3), 7.2 (copy groups widen the range), 8.7 (the reviewer on every decision, data side only), and H5, H6, H8, H12.
- Audit findings closed: C-01, C-02, A-05, B-36, B-37, B-38, B-39, B-47, C-17, C-20, C-21, C-24.
- Fix plan items: 5.2 (find people who moved, built into P-ID-1), 5.1 step 6 (identity over every counted row), and the engine half of 5.4 (master IDs from person keys, plus the `known` hook that M13 fills).

## Depends on

- M05: `wholecount/engine/addresskey.py` (`address_key`, which keeps the street type; this is the C-24 fix).
- M01: `engine/fold.py` (`fold`, which keeps letters and digits only) and `session/keys.py` (`person_key`). The engine takes keys as strings. Tests build them with `keys.person_key(TEST_SECRET, ...)`. The engine never imports `session`.
- M04: standardized values, ISO dates, and the count status that tells which rows are counted.
- M00: the copy registry.

## Branch

`build/m06-people`, created from the latest `main`.

## Read first

All paths are under `legacy/`.

- `identity.py`: `NICKNAME_GROUPS` (line 43, 92 groups), `SURNAME_PARTICLES` and `SUFFIXES` (144 to 148), `_fold` (151), `given_keys` (159), `surname_tokens` (174), `parse_dob` (191), `compare_dob` (238), `PersonRecord` (255), `blocking_keys` (298), `WEIGHTS` and `PROPOSE_THRESHOLD` (352 to 361), `score_pair` (364), `_is_auto` (436; the bug is line 442, `pts >= same_system_id`), `resolve` (472), `_headline` (586).
- `dedupe_rules.py`: `_norm` (23), `find_groups` (52), `apply_rule` (74), `group_id` (104; it hashes the key only, which is B-38), `proposals` (110), `apply_decisions` (143; `copies:N` is a position, which is C-08).
- `app.py:1759` (`dup_key` ignores DOB and middle initial, B-37), `app.py:2386` to `2417` (the same-ID check across all files, B-36 and C-17). `crosswalk_server.py:2356` `_person_records`, `2391` `_resolve_identity`.
- Audit inputs: `docs/audit/C-scripts/fixtures.py` (the 12-row fixture), `s02_identity_auto.py`, `s21_client_id_scope.py`, `s24_id_reuse_e2e.py`, `s27_master_id_stability.py`, `s26_identity_decision_audit.py`, and `docs/audit/A-fixtures/household.csv`.
- `docs/context/docs/crosswalk-fix-plan.md` 5.2 (line 617) and 5.4 (line 660, for the known-master idea only).

## What to build

```
wholecount/engine/names.py            words(), surname_tokens(), given_keys(), suffix_of()
wholecount/engine/data/nicknames.toml the 92 groups, ported from legacy identity.py:43
wholecount/engine/copies.py           P-DUP: find_copies(), apply_copy_decision(), key_modes()
wholecount/engine/identity.py         P-ID: resolve(), master_id(), score_pair(), score_from_codes()
wholecount/settings/identity.toml     weights, bands, limits
tests/fixtures/people/                fixture builders (see Tests to write)
```

If M04 already made a folding or title-case helper, reuse it and add only the new functions to `names.py`.

### names.py (P-DUP-6)

- Whole-value equality uses M01's `fold` (`José Núñez` equals `Jose Nunez`, `O'Brien` equals `OBrien`, `Ana-Maria` equals `Ana Maria`). `words(text)` is the same fold but keeps single spaces between words, for tokenizing.
- `surname_tokens(last) -> frozenset[str]` as the legacy function: drop suffix words (`jr sr ii iii iv v 2nd 3rd`), particles (the P-PREP-4 list plus the legacy `SURNAME_PARTICLES`) and one-letter tokens, and keep every token of a double surname. If nothing is left, keep the particles.
- `suffix_of(last) -> str`. The generational suffix at the end of the surname text, else empty. A tidy-up column `<name>_suffix` (P-PREP-4) wins when the caller provides one.
- `given_keys(first) -> frozenset[str]`: the first word plus `g<id>` for each nickname group it belongs to. A test asserts 92 groups and that `bob` and `robert` share one.

### copies.py (P-DUP)

```python
@dataclass(frozen=True)
class CopyRow:   record_key; table_key; system; client_id; first; middle_initial; last; dob; address_key; program
                 values: tuple[tuple[str, str], ...]          # every mapped field, standardized
@dataclass(frozen=True)
class CopyGroup: group_id; kind: Literal["identical", "possible", "same_id_different"]
                 rule_id; members: tuple[str, ...]; evidence: tuple[str, ...]     # record keys sorted, codes only
CopyDecision = KeepOne(kept) | NotCopies | DifferentPeople | ApprovedAsEntered
def find_copies(rows, tables: Mapping[str, TableInfo], rule=None) -> list[CopyGroup]
def apply_copy_decision(group, decision) -> CopyOutcome        # kept, set_aside, counted, verdict_pairs
def key_modes(groups, decisions, split_rows=()) -> Mapping[str, Literal["details", "row"]]
```

`TableInfo` has `has_dob_column` and `system`. A row set aside earlier (a summary row) is not passed in.

- DUP-1 (P-DUP-1). Rows in one table with every `values` pair equal are `identical`. The legacy `dup_key` omitted DOB, middle initial and custom fields. This one uses all of them (B-37).
- DUP-2 (P-DUP-2). Rows in one table group when folded surname, given name (equal or in one nickname group) and DOB all match. In a table with no DOB column, folded surname, given name and the full `address_key` must match. A blank DOB in a table that has a DOB column does not match anything, so it does not group (a reading; log it). Name alone, or name and ZIP, never groups (B-47). `CopyRule` refuses a rule without surname, given name and one of `dob`, `address_key`, `client_id`. Rows with different non-blank Program values are never grouped, because they are one person's separate enrollments (C-17). A group of all-identical rows is `identical`, else `possible`. A row is in one group.
- DUP-3 (P-DUP-3). For each (system, non-blank Client_ID) with two or more rows, if surname, given name (equal or in one nickname group, as P-ID-3 allows) and DOB agree for every pair (DOB compared only when both have one), nothing is raised, and the rows are one person record (ID-0). Otherwise make one `same_id_different` group of all rows with that ID in that system. The same ID in two systems is never looked at (B-36, C-17).
- DUP-4 (P-DUP-4). `identical` groups allow `KeepOne`. `possible` groups allow `KeepOne` and `NotCopies`. `same_id_different` groups allow `DifferentPeople` and `ApprovedAsEntered`. `apply_copy_decision` refuses anything else with `Unresolvable(code)`, and refuses `KeepOne` when the kept key is not a member. `KeepOne` keeps one row and sets the rest aside with `copy_of`. `NotCopies` and `DifferentPeople` count every member and return a `different` verdict pair for each pair of members (so identity never proposes them again). `ApprovedAsEntered` counts every member and returns no verdict (P-DUP-3). `NotCopies` is refused with `same_person_key` only when members share a person key built from a Client_ID (one ID, one name, one DOB). Members that share a name-based key (no Client_ID) can always be marked `NotCopies` (SPEC 5.1). While a group is open its rows stay counted (P-VAL-3). The group widens the range (ID-9) and holds Finish review (M08), but it never makes a row `not_counted_yet`.
- DUP-5 (P-DUP-5). `group_id` is the first 12 hex of SHA-256 over `kind` and the sorted member record keys joined with U+001F. A new member changes it, so an old decision no longer matches (B-38).
- DUP-6 (P-DUP-6). Every comparison folds names first.
- DUP-7 (person keys after a decision). Rows of a decided `same_id_different` group no longer share a person key. `key_modes` tells the caller (M08) how to key them: `details` means the key built without the Client_ID (system, given, surname, DOB), and `row` means a key made from the record key alone (`person_key(secret, "row", client_id=record_key)`), used only for rows in `split_rows` whose details keys would still be equal. `key_modes` also returns `row` for every row whose name-based person key (no Client_ID) another counted row shares, unless a decision made them one person record (SPEC 5.1). A row whose name-based key is its own keeps it, so its master ID stays stable across batches. Without a decision any other row uses the default key.

### identity.py (P-ID)

```python
@dataclass(frozen=True)
class PersonRow:   record_key; person_key; system; client_id; first; last; dob; address_key; unit; zip5; program
@dataclass(frozen=True)
class Evidence:    code: str; params: tuple[tuple[str, int | str], ...] = ()
@dataclass(frozen=True)
class AutoJoin:    pair: tuple[str, str]; reason: Literal["same_system_id", "four_exact_facts", "earlier_batch"]; evidence: tuple[Evidence, ...]
@dataclass(frozen=True)
class Proposal:    pair; score: int; band: Literal["likely", "possible"]; evidence; cautions; features: tuple[Evidence, ...]; found_via: tuple[str, ...]
@dataclass(frozen=True)
class PairVerdict: a; b; verdict: Literal["same", "different"]; decision_id; reviewer; inherited: bool = False    # a < b, person keys
@dataclass(frozen=True)
class KnownMaster: master_id; created_at; linked_at; how: Literal["derived", "same_system_id", "four_exact_facts", "reviewer"]   # from the saved crosswalk (M13); linked_at is when this key was linked to the master
@dataclass(frozen=True)
class IdentityResult:
    master_of: Mapping[str, str]            # person key to master ID
    master_of_record: Mapping[str, str]     # record key to master ID
    groups: Mapping[str, tuple[str, ...]]   # master ID to person keys
    auto_joins; proposals; settled: int; low: int; low_master_of: Mapping[str, str]
    refused: tuple[PairVerdict, ...]; merged: tuple[tuple[str, str], ...]; skipped_buckets: int
    released: tuple[tuple[str, str], ...]   # (person key, saved master ID) that left a tool-made saved link (ID-8)
    compared: frozenset[tuple[str, str]] | None
def master_id(person_key) -> str                # "M-" + sha256(person_key.encode()).hexdigest()[:10]
def score_pair(a, b, rare: bool, weights) -> Score                # points, evidence, cautions
def score_from_codes(codes, weights) -> int                       # the same sum, from stored evidence (M13)
def resolve(rows, verdicts=(), known=None, settings=None, keep_compared=False, open_copy_groups=()) -> IdentityResult
                                                # open_copy_groups: record keys of each open identical or possible group
```

A person record is every row that shares a person key. Its facts come from the row with the most non-blank values among first, last, dob, address key and ZIP, ties to the smallest record key. Evidence codes: `dob_exact`, `dob_swapped`, `dob_one_digit`, `dob_differs`, `surname_exact`, `surname_part`, `names_swapped`, `given_exact`, `given_nickname`, `given_initial`, `address_exact`, `zip_only`, `same_system_id`, `same_system_id_differs`, `suffix_differs`, `rare_name`. The engine returns codes. The registry holds the plain sentences (P-ID-2), each with a claim test.

- ID-0 (P-ID-3, SPEC 5.1, ID-merge). Rows that share a person key built from a Client_ID are one person record. When such a record holds two or more rows, `resolve` lists one `same_system_id` `AutoJoin` per extra row, as record key pairs, so Results can show it. It re-checks that names (nicknames allowed) and DOB agree and raises `InconsistentInput` if they don't, which means a caller skipped DUP-3. A name-based person key, built without a Client_ID, never joins rows by itself. The caller keys every row that shares one with DUP-7's `row` mode, so `resolve` never sees two undecided rows under one name-based key. If it does, it raises `InconsistentInput`. Such rows in one table are a copy group (DUP-2). In different tables they meet as candidates (ID-1) and become a proposal, or an automatic join only when a P-ID-3 reason holds. Only a decision makes them one record.
- ID-1 (P-ID-1). Candidates over every counted row, mapped or not, from four block key families, each a combination of two facts. K1 surname with DOB. K2 surname with `address_key`. K3 given key with DOB. K4 surname with given key alone (fix plan 5.2). K1 and K3 each come in three forms (exact DOB, birth year, month and day) so swapped digits still meet. Every key also has a swapped-name form. Add one more key, `id:<system>|<client_id>`, so same-ID person records are always compared (ID-5). Drop the legacy lone `dob` and lone `addr` keys. Skip a bucket of more than `max_bucket` records and count it in `skipped_buckets`. The audit gets the count, never the bucket.
- ID-2 (P-ID-2). Score is the sum of `weights` over the evidence codes, so `score_from_codes` replays a stored pair when a weight changes (M13). `dob_swapped` and `dob_one_digit` both use `dob_near`. No address counts as `address_exact` unless the full `address_key` is equal, street type and ZIP included (C-24). `suffix_differs` is a caution and changes no points.
- ID-3 (P-ID-3). Three named reasons, returned as values and never computed from a score. `same_system_id` is ID-0. `four_exact_facts` is DOB exact, folded surname exact, folded given name exact, `address_key` exact, unit equal when both have one, and suffix equal. All four facts must be present. `earlier_batch` exists only with the saved crosswalk on (ID-6 and ID-8). A pair that scores 100 or more and meets none of them is a proposal. A test builds one.
- ID-4 (P-ID-4). Every other pair at or above `possible_min` is a proposal, Likely from `likely_min`, else Possible. Below `possible_min` is not shown. Twins, and a parent and child with the same name, come out as proposals.
- ID-5 (P-DUP-3, C-02). Two person records in one system with the same non-blank Client_ID and different person keys exist only because a reviewer decided a same-ID conflict. They are always candidates. With no `different` verdict they are a Possible proposal even under `possible_min`, with evidence `same_system_id_differs`. This reads P-DUP-3 as "at least Possible". Both C-02 fixtures end the same way.
- ID-6 (P-ID-6). `verdicts` are per pair of person keys. A `same` verdict joins. A `different` verdict is a cannot-link, including through a third record. A union refused for that reason is returned in `refused`, never dropped. A batch verdict beats an `inherited` one on the same pair. An inherited `same` verdict (from the saved crosswalk, M13) is not applied as a plain verdict. It becomes an `earlier_batch` `AutoJoin`, listed on Results with a split action (P-ID-3), and a batch `different` verdict on that pair splits it. An inherited `different` verdict is a cannot-link like a batch one. Order of work is fixed: batch `same` verdicts, then automatic joins sorted by (reason, pair), each skipped if it would break a cannot-link.
- ID-7 (P-ID-7). A `different` verdict splits a `four_exact_facts` join. A `same_system_id` join is one person record, so splitting it is the DUP-7 route: `DifferentPeople` on its rows with `split_rows`, then resolve again. Test both.
- ID-8 (5.3, C-20). A group's master ID is `master_id` of its smallest person key. Merging two groups keeps the smaller key's ID. With `known` (M13), a group that holds known person keys takes the master ID with the earliest `created_at`, ties to the smaller ID, and the other known IDs are returned in `merged` as (old, new). Groups with no known key use the derived ID.
  - **Two groups that resolve to one saved master.** Each `KnownMaster` carries `how`, the way the saved link was made. Two groups in this batch that aren't joined by this batch's evidence but hold person keys resolving to the same saved master are handled by `how`. When a person made that link (`reviewer`), the groups are joined as an `earlier_batch` `AutoJoin` with a split action (P-ID-3). When the tool made it (`same_system_id`, `four_exact_facts` or `derived`) and its reason no longer holds, they stay two groups.
  - **Which group keeps the ID.** The group holding the key with the earliest `linked_at`, ties to the smaller person key, keeps the saved master ID. The other takes its derived ID, and its keys are returned in `released`.
  - **Uniqueness.** Two groups never share a master ID, and deciding one pair renumbers nobody else.
- ID-9 (counts). `settled` is the number of groups. `low` is the number after also uniting every proposal and every open copy group in `open_copy_groups` that doesn't break a cannot-link (SPEC 7.2). `low_master_of` is that grouping, so M08 can compute the low ends of Goal 1 and Goal 2 from one union (C-12).
- ID-10 (fix plan 5.2, P-ID-1). A name signature is folded surname tokens plus given key. A signature is rare when no more than `rare_name_max_count` person records in the batch share it. A pair found only through K4 is a candidate only when its signature is rare, and then gets `rare_name_bonus` and the evidence `rare_name`. A pair found through any other key gets no bonus. Common names stay apart. Exact given names are needed, so a nickname pair with no other evidence scores 60 and is not shown.
- ID-11 (C-21, H8). `PairVerdict.audit_fields(master_before, master_after)` returns the decision ID, the reviewer, the verdict word and both master IDs, and nothing else. M08 adds the covered record keys and writes the line.
- ID-12 (for M13). `settings` can lower `possible_min` for one run (calibration uses 40). With `keep_compared`, `compared` holds every candidate pair, so a known pair that never met can be counted. A below-line pair then appears in `proposals` with `features` set.
- ID-13 (P-VAL-3, SPEC 7.2). Pairs inside one copy group are left to P-DUP. While the group is open, identity neither joins nor proposes its members with each other, and `low` unites them (ID-9). After `NotCopies` they carry a `different` verdict. After `KeepOne`, only the kept row is passed in.

### settings/identity.toml

```toml
[weights]            # starting values are the legacy ones; the calibration (M13) measures them later
dob_exact = 42
dob_near = 26        # day and month swapped, or one digit apart
dob_differs = -20
last_exact = 30
last_overlap = 24
last_swapped = 20
first_exact = 26
first_nick = 22
first_initial = 8
addr_exact = 30
zip_only = 6
same_system_id = 100 # sort order only; never a reason to join
rare_name_bonus = 8
rare_name_max_count = 3

[bands]
possible_min = 62    # the legacy PROPOSE_THRESHOLD
likely_min = 90      # new; chosen so every pair in the C-01 fixture is Likely

[limits]
max_bucket = 150
```

## Tests to write

Rule tests in `tests/rules/test_P_DUP.py` (`test_P_DUP_1_...` to `_6_`, plus `test_DUP_7`) and `tests/rules/test_P_ID.py` (`test_P_ID_1_...` to `_7_`, plus `test_ID_0`, `_5`, `_8` to `_13`). Unit tests in `tests/unit/test_names.py` (fold cases, 92 groups) and `test_settings_identity.py`. Audit tests in `tests/audit/`, each with a line in `tests/audit/INDEX.md`.

- `test_C01_auto_join_score.py`. Build the 12 records of `docs/audit/C-scripts/fixtures.py`. Files A and B are two systems with Client_ID, First_Name, Last_Name, DOB, Address, City, State, Zip, Program. A holds A1 Maria Rodriguez 1985-03-14 100 Grand Concourse 10451; A2 Jordan Smith 2015-06-01 10 Oak St 11201; A3 Robert Smith 1962-03-14 20 Elm St 11201; A4 Ana Perez 1990-05-06 7 Elm St 10013; A5 Luis Diaz 1980-02-02 123 45th St 11377; A6 Carlos Vega 1975-01-01 5 A St 10001. B holds B1 Maria Rodriguez (same); B2 Jaden Smith 2015-06-01 10 Oak St; B3 Robert "Smith Jr" 1992-03-14 20 Elm St; B4 Ana Perez 1990-06-05 7 Elm St; B5 Luis Diaz 1980-02-02 123 45th Ave 11377; B6 Elena Vega 1999-09-09 6 B St 10001. Asserted:
  - Exactly one automatic join, A1 with B1, reason `four_exact_facts`, score 128.
  - Exactly four proposals, all Likely. A2 with B2 scores 102 (`dob_exact`, `surname_exact`, `address_exact`). A3 with B3 scores 112 with `dob_one_digit` and the caution `suffix_differs`. A4 with B4 scores 112 with `dob_swapped`. A5 with B5 scores 104 with `zip_only` and no `address_exact`. None carries `rare_name`, because each was found through a DOB or address key (ID-10).
  - A6 with B6 is not shown (score 16). `settled` 11, `low` 7, so the screen says "7 to 11 until 4 pairs are decided". The truth for the fixture is 10 people, inside the range.
  - The audit's own numbers (7 to 10, 3 open, 2 joins) assume the old address key. With the street type kept (C-24) the Luis Diaz pair is a proposal, so this test expects 7 to 11, 4 open, 1 join. P-ID-4 says the spec's rules decide the numbers. The report says so.
  - A second test builds a pair that scores 100 or more without meeting either reason (same name, DOB and ZIP, different streets; Bill and William Smith with the same DOB and ZIP scores 100) and asserts a proposal.
- `test_C02_same_system_id.py`. Fixture 1 (`s24`): system one.csv, rows (77, Ana Perez, 1990-05-06, 7 Elm St, 11201), (77, Beth Perez, 1994-09-09, 55 Oak Ave, 11201), (78, Carl Ng, 1970-01-01, 1 Pine St, 11201). `find_copies` returns one `same_id_different` group. Before a decision the rows are not passed to `resolve`. After `ApprovedAsEntered`, key them with `key_modes`: no automatic join, one Possible proposal with `same_system_id_differs`, `settled` 3, `low` 2. After `DifferentPeople` instead: no proposal, `settled` 3, `low` 3. Fixture 2 (`s21` case c): 500 Maria Lopez 100 Grand Concourse Bronx 10451, no DOB, and 500 Maria Garcia 5 Main St Brooklyn 11201. `settled` is 2, `low` is 1 after approval and 2 after the different-people decision. Fixture 3: same ID, same name and DOB, different addresses gives one person record, an automatic join `same_system_id`, no group.
- `test_A05_same_id_merge.py`. `household.csv`: H100 Hector Ballpeen and H100 Hortense Ballpeen at 5 Gumdrop Ln 11201, plus H200 Ada Lovelace. They are never joined without asking. After `ApprovedAsEntered`, `settled` 3 and `low` 2. The export-side count of 2 people that the audit showed cannot happen.
- `test_B36_same_id_across_files.py`. A.csv `1001 Maria Lopez` and B.csv `1001 John Chen`: no group, no join, no proposal. Two rows in A.csv with 1001 and different people: one `same_id_different` group.
- `test_B37_identical_record.py`. Same ID, name, address, ZIP and program, with DOB `1990-03-04` against `1955-09-09`: not `identical`, and DUP-3 makes a `same_id_different` group. Middle initial `A` against `B`: not identical. Two fully equal rows: `identical`, rule `P-DUP-1`.
- `test_B38_saved_copy_decision.py`. Rows 1 and 2 grouped, `KeepOne(row 1)`. Add row 3 with the same key. The `group_id` differs, so the old decision does not match, and the group comes back undecided with three members.
- `test_B39_accent_folding.py`. Seven rows in one table: Maria Garcia, MARIA GARCIA and María García at 10 Main St 11201; Pat O'Brien and Pat OBrien at 5 Elm St 11201; Wei Li and Li Wei at 7 Oak Ave 11201 (no DOB column). Groups are the three Garcias and the two O'Briens. Wei Li and Li Wei are not grouped. Across files, `Maria Garcia`/`María García`, `Pat OBrien`/`Pat O'Brien`, `Ana Maria Lopez`/`Ana-Maria Lopez` and `Jose Nunez`/`José Núñez`, each with a different ID, the same address and no DOB, become one Possible proposal (86 or more).
- `test_B47_default_copy_rule.py`. Two `Maria Garcia` rows, different IDs and addresses, same ZIP, no DOB column: not grouped. Same address: grouped as `possible`. `CopyRule(fields=("surname","given","zip"))` raises. Rows with different Programs are not grouped.
- `test_C17_client_id_scope.py`. Three systems of 20 clients numbered 1 to 20, 60 different people (the `s21` generator): no groups, no proposals, `settled` 60. Enrollment file: IDs 7, 8, 9 twice each with the same person and different Program: no group, three `same_system_id` automatic joins, `settled` 3.
- `test_C20_master_id_stability.py`. 30 records forming 20 people with 4 open proposals. Record the master IDs, apply one `same` verdict, resolve again. Only the two merged groups can change, and one of the two old IDs survives. Shuffling the input order gives the same `master_of`. Vectors from M01's person keys: `064ab600...45d2af` gives `M-a7e53489dc`, and `1479425d...f96c6` gives `M-10438b4e7e`. A `known` map with two earlier IDs puts the older one on the merged group and returns the other in `merged`. A re-export with a reordered file gives equal master IDs.
- `test_C21_identity_verdict_audit.py`. `audit_fields` for `same` and `different` returns only the decision ID, reviewer, verdict word and master IDs. A scan for every name, street and date in the fixture finds nothing.
- `test_C24_address_key.py`. `123 45th St` and `123 45th Ave` differ and give no `address_exact`. `45 Park Ave` and `45 Park Pl` differ. `W 45th St` and `West 45th Street` match, so Luis Diaz at `12 W 45th St` against `12 West 45th Street`, same name and DOB, is an automatic join by `four_exact_facts`.
- `test_P_ID_1_people_who_moved.py` (fix plan 5.2). Priya Venkataraman, one person in two files at different addresses and ZIPs. With the same DOB the pair is a Likely proposal (98). With no DOB in either file and a rare name it is a Possible proposal (30 + 26 + 8 = 64) found via K4 only. With the name Maria Rodriguez on four person records in the batch and no DOB, the records stay apart and no proposal exists. With exactly three such records the signature is still rare and a proposal exists. `Bob Smith` with `Robert Smith`, no DOB, different addresses, is not shown (60).
- `test_ID_0_name_key_never_joins.py` (SPEC 5.1, H5). Two counted rows with no Client_ID, the same folded name and DOB, in two tables of one system, at different addresses. `key_modes` gives both the `row` mode, they're two person records, they meet as one Likely proposal (98), and there's no `AutoJoin`. The same two rows in one table form a `possible` copy group, `NotCopies` is accepted (not refused with `same_person_key`), and afterward they're two records with a `different` verdict. Two rows sharing a Client_ID-based key are still one record, and `NotCopies` on them is still refused. `resolve` given two undecided rows under one name-based key raises `InconsistentInput`.
- `test_ID_8_earlier_batch.py` (P-ID-3). (a) An inherited `same` verdict between two person keys in this batch gives one `earlier_batch` `AutoJoin`, and `settled` drops by 1. A batch `different` verdict on that pair splits it. (b) Two groups whose keys resolve through `known` to one saved master with `how="reviewer"` are joined as `earlier_batch`. (c) The same with `how="four_exact_facts"`, where the four facts no longer agree, stays two groups. The key with the earliest `linked_at` keeps the saved ID, the other gets its derived ID and appears in `released`, and the two master IDs differ.
- `test_ID_13_copy_groups.py` (P-VAL-3, SPEC 7.2). Two counted rows in one table that form an open `possible` copy group, passed in `open_copy_groups`, give no proposal and no join between them. `settled` counts them as two and `low` as one. After `NotCopies` (a `different` verdict), `low` counts two.

Property tests in `tests/invariants/test_identity_properties.py` (hypothesis):

- Determinism. Shuffling rows or verdicts gives equal `master_of`, `auto_joins`, `proposals`.
- Every `AutoJoin.reason` is one of the three names, and `earlier_batch` appears only when `known` or an inherited verdict is given. No pair scoring 100 or more joins unless it meets a reason. Rows that share only a name-based key are never one record without a decision.
- Range. `low <= settled`. A `same` verdict on a proposal lowers `settled` by exactly 1 and leaves `low`. A `different` verdict leaves `settled` and never lowers `low`.
- Master IDs are unique per group. Adding a record that shares nothing changes no existing ID. A cannot-link is never violated.
- `score_from_codes(evidence codes)` equals the score for any generated pair.
- `fold` is idempotent, and `address_key` is stable under case, spacing, punctuation and ordinal changes.

Copy and offline checks. Add the registry sentences for every evidence code and every cause title (copies, same ID), each with a claim test. `make offline` stays green with no new imports.

## Done when

- [ ] Every rule ID above has a named test. Every audit ID in Spec sections has its own test file and a line in `tests/audit/INDEX.md`.
- [ ] The C-01 fixture gives 1 join, 4 proposals, 7 to 11, and the report explains the difference from the audit's 7 to 10.
- [ ] `grep` finds no score threshold used to decide a join in `engine/identity.py`.
- [ ] The 92 nickname groups are in `nicknames.toml`, and the master ID vectors pass.
- [ ] No new dependency outside the approved set.
- [ ] The report's Questions for Joe list. (1) ID-5, the Possible floor after "approved as entered". (2) A blank DOB in a table with a DOB column does not group. (3) `NotCopies` also stores a `different` verdict, so a reviewer is not asked again by identity. (4) `likely_min` is 90. (5) The block keys are P-ID-1's four plus `id:`, and K1 and K3 also match on birth year and on month and day. (6) The `row` key mode for splitting identical rows and for rows that share a name-based key. (7) Rows with no Client_ID in different tables can still join by `four_exact_facts`, since that's a named reason and not the shared key on its own. (8) After a tool-made saved link stops holding, the key linked first keeps the saved master ID.
- [ ] `make test`, `make offline` and `make copy` are green, with counts in the report.
- [ ] The report is written, the branch is pushed, the pull request is opened, and work has stopped.

## Windows checks for Joe

Run from the repo with the branch checked out. Dev commands print counts through the M00 printer and never a name. Add the labels below to `CountLabel`.

1. `.venv\Scripts\activate`, then `python -m pytest -q`. Expect no failures, and the test count in the report.
2. `python -m wholecount.dev people-demo`. It builds the 12-record fixture in memory. Expect `automatic_joins 1`, `joins_four_exact_facts 1`, `joins_same_system_id 0`, `proposals_likely 4`, `proposals_possible 0`, `people_low 7`, `people_high 11`, `master_ids_unique 1`. If `people_high` is 10 or `automatic_joins` is 5, something regressed.
3. `python -m wholecount.dev people-check --csv "C:\path\to\one_file.csv" --system A` on a real export, with `--first --last --dob --client-id --address --zip` if your column names differ. Expect `rows_read`, `copy_groups`, `copy_groups_identical`, `copy_groups_possible`, `copy_groups_same_id_different`, and `proposals 0` for a single file. It writes nothing. Compare the copy group counts to what you expect from that file.
4. Run it with two files (`--csv a.csv --csv b.csv --system A --system B`). Expect `automatic_joins`, `proposals_likely`, `proposals_possible`, `name_only_proposals`, `people_low` and `people_high`. Most cross-file matches should be proposals for you to decide, so `automatic_joins` should be small next to the number of people you expect in both files. If your files carry no date of birth, expect `name_only_proposals` above 0 only for rare names.
5. Run step 4 twice. The two outputs are identical, line for line.

## Out of scope

- Commands, undo, the "No longer apply" list, decision IDs, reviewer prompts and sign-offs, and audit lines (M08 and M09). This milestone returns plain results and `audit_fields`.
- Goal 1 and Goal 2, "without a program", and DOB coverage (M08). This milestone returns `settled`, `low` and `low_master_of`.
- The saved crosswalk store and carrying decisions into later batches (M13). `known` and `inherited` are the only hooks.
- The calibration sampling, labeling and thresholds (M13). `score_from_codes`, `features` and `compared` are what it reads.
- Screens for causes, the compare view and the same-person list (M10 to M12). Writing Duplicate_In_File and Possible_Duplicate_Of (M09).
