# M13 Matching calibration, the saved crosswalk and install secret backup

## Goal

Add the three things that make Wholecount remember and prove its matching. The first is a backup and restore of the install secret, protected by a passphrase, using the standard library only. The second is the saved crosswalk, a small SQLite file of keyed hashes, master IDs and decisions that is off until the organization turns it on, so a person keeps one master ID across batches and decided pairs are not asked again. The third is matching calibration, where two staff label a sample of pairs on the client's own computer and the tool reports how often Same was right in each score band, how many known pairs were never compared, and which proposal line catches at least 98% of true matches. This milestone is the engine and the Settings screens. It changes no matching weight and no rule. Nothing here may put a name, address, Client_ID value or date into the crosswalk, the labeled store, the audit or a log (H8, H9).

## Spec sections

- 5.1 (the Backup bullet), 5.3 (master IDs with the crosswalk), 8.8 (calibration), 10.5 (the saved crosswalk), 7.4 (the calibration line in the detail view), 9.3 (the methods note), 6.8 P-ID-3 (the `earlier_batch` reason) and P-ID-4 (the calibration floor), 11.6.2 (the backup action), and H3, H5, H8, H9 (thresholds live in `prefs.json`), H12.
- Fix plan items: 5.4 (crosswalk, with step 1's backup), 5.6 (calibration). The README lists these two as this milestone's closes. Where the fix plan and the spec differ, the spec wins. The fix plan keys links by record key and the spec by person key. The fix plan's `CW0004821` IDs become the spec's `M-` IDs.

## Depends on

M12 (and through it M10 and M11: the frame, `Drawer`, `HeldAction`, `confirm`, `GridView`, `SessionBridge`, `JobRunner`, the compare widget). M01 (`InstallSecret.mac`, `SecretStore`, `dpapi`, `keys.person_key`). M06 (`resolve` with `known`, `settings`, `keep_compared`; `PairVerdict.inherited`; `KnownMaster`; `score_pair`; `score_from_codes`). M07 (`ProgramDecision.inherited`, PROG-9). M08 (`Counts.matched_from_earlier`, `BatchConfidence.calibration`, `NoLongerApply`, STALE-1, the `dob_now_differs` reason code). M09 (`CalibrationNote` slot in the summary, `prefs.json`, the audit event table, `folder_warning`, the save path, `write_outputs`).

## Branch

`build/m13-calibration-crosswalk`, created from the latest `main`.

## Read first

The old build has no crosswalk, backup or calibration. Nothing to port.

- `docs/context/docs/crosswalk-fix-plan.md` 5.4 (line 660, the tables and the test) and 5.6 (line 736).
- `docs/audit/C-scripts/fixtures.py` and `s01` to `s05` (the 12-record C-01 fixture and its truth of 10 people). `docs/audit/C-counts.md` C-20.
- The code earlier milestones built: M01 `session/keys.py`, `secret_store.py`, `dpapi.py`. M06 `identity.py`, `settings/identity.toml`. M08 `session/staleness.py`, `commands.py`, `decisions.py`. M09 `session/store.py` (the pattern for an encrypted file, `WCS1`) and `engine/outputs/audit_text.py`. M12 `ui/stages/review/compare.py` and `nolonger.py`.
- `docs/context/design/style-guide/` for the Settings screens. There is no board for them.

## What to build

```
wholecount/engine/secretbackup.py            make_backup(), read_backup(), BackupError
wholecount/engine/calibration/sample.py      CalPair, band_of(), draw_sample()
wholecount/engine/calibration/labels.py      LabelSet, settle(), Settlement
wholecount/engine/calibration/measure.py     measure(), suggest_line(), joins_check(), known_pairs_check()
wholecount/engine/calibration/regression.py  regression_check()
wholecount/engine/calibration/note.py        CalibrationNote
wholecount/engine/crosswalk/schema.py        SCHEMA, open_db(), CrosswalkOrphaned
wholecount/engine/crosswalk/store.py         CrosswalkStore (all SQL lives here)
wholecount/engine/crosswalk/apply.py         load_known(), inherited_verdicts(), inherited_programs(), commit()
wholecount/session/backup.py                 BackupSecret, RestoreSecret
wholecount/session/crosswalk.py              TurnOnCrosswalk, ForgetCrosswalk, hooks in runner.py
wholecount/session/calibration.py            CalibrationSession, draft and labeled stores, thresholds
wholecount/ui/settings/                      drawer.py  secret.py  crosswalk.py  matching.py  label.py  thresholds.py
wholecount/settings/calibration.toml         floor, bands, sample sizes, targets
```

### Install secret backup and restore (5.1)

- BAK-1 (format). `make_backup(secret, passphrase, salt=None) -> bytes` returns 84 bytes: `b"WCB1"`, a 16-byte salt (from `secrets.token_bytes` unless a test passes one), the 32-byte ciphertext, a 32-byte tag. Derive `dk = hashlib.scrypt(NFKC(passphrase).encode(), salt=salt, n=2**15, r=8, p=1, maxmem=2**26, dklen=64)`. Then `enc_key = dk[:32]` and `mac_key = dk[32:]`. The keystream is `hashlib.shake_256(b"wholecount-secret-backup-v1" + enc_key).digest(32)`, the ciphertext is the secret XOR the keystream, and the tag is HMAC-SHA256 of `mac_key` over `magic + salt + ciphertext`. Standard library only (`hashlib`, `hmac`, `secrets`, `unicodedata`).
- BAK-2 (known answer). Secret `bytes(range(32))`, passphrase `correct horse battery staple`, salt `bytes(range(16))` gives the blob `57434231000102030405060708090a0b0c0d0e0f819956c362b0ba0d33e90b391c32960f1e927297476698fb8341002bde214ca8fc435e355253a2ec4c73060ea9261179f015affbf30b6c477b3938d53fbba454`. The ciphertext is `819956c362b0ba0d33e90b391c32960f1e927297476698fb8341002bde214ca8` and the tag is `fc435e355253a2ec4c73060ea9261179f015affbf30b6c477b3938d53fbba454`.
- BAK-3 (restore). `read_backup(blob, passphrase) -> bytes` checks the length and magic (`not_a_backup`), then compares the tag with `hmac.compare_digest` before it decrypts. A wrong passphrase and a damaged file both raise `wrong_passphrase_or_damaged`, because they cannot be told apart. Nothing partial is returned.
- BAK-4 (commands). `BackupSecret(passphrase, again, path)` refuses `passphrase_mismatch`, an empty passphrase, or one under `backup_passphrase_min` (12 characters, a choice to log). It checks `folder_warning` (M09) and asks for the amber confirmation. It runs in a `JobRunner` job, because scrypt can pass 300 ms (H14). The audit gets `SECRET_BACKUP` with the reviewer and time and nothing else. `RestoreSecret(path, passphrase, typed)` reads the file, compares it with the current secret, and says "This is the same secret. Nothing changed." when equal. When it differs, the screen first says plainly that saved progress and the saved crosswalk made with the current secret will stop working, and the typed word `replace` is needed. Then it calls `SecretStore.save`. The secret never reaches a log, message, `repr` or dev output.

### The saved crosswalk (10.5, 5.3, H9)

- XW-1 (off by default). The crosswalk is on exactly when `%LOCALAPPDATA%\Wholecount\crosswalk.db` exists. `TurnOnCrosswalk(reviewer)` creates it and writes `CROSSWALK_ON` with the reviewer and time. `ForgetCrosswalk(typed)` needs the registry word `forget`, deletes the file, and writes `CROSSWALK_FORGET`. Neither goes on the undo stack, and both say so on screen. Both mark `identity` and `programs` stale (add the crosswalk to the `identity` fingerprint in STALE-1).
- XW-2 (the file). `sqlite3` from the standard library, `PRAGMA journal_mode=DELETE` and `foreign_keys=ON`, so no `-wal` or `-shm` file is ever left (H9). `user_version = 1`.

```sql
CREATE TABLE meta(key TEXT PRIMARY KEY, value TEXT NOT NULL);      -- format, created_at, created_by, secret_check
CREATE TABLE person(master_id TEXT PRIMARY KEY, created_at TEXT NOT NULL, created_by TEXT NOT NULL, first_batch TEXT NOT NULL);
CREATE TABLE person_key(person_key TEXT PRIMARY KEY, master_id TEXT NOT NULL REFERENCES person,
  how TEXT NOT NULL CHECK(how IN ('derived','same_system_id','four_exact_facts','reviewer')), decided_by TEXT NOT NULL, decided_at TEXT NOT NULL);
CREATE TABLE pair_verdict(key_a TEXT NOT NULL, key_b TEXT NOT NULL, verdict TEXT NOT NULL CHECK(verdict IN ('same','different')),
  decided_by TEXT NOT NULL, second_reviewer TEXT, decided_at TEXT NOT NULL, PRIMARY KEY(key_a, key_b), CHECK(key_a < key_b));
CREATE TABLE program_group(group_id TEXT PRIMARY KEY, kind TEXT NOT NULL, label TEXT, members TEXT NOT NULL, decided_by TEXT NOT NULL, decided_at TEXT NOT NULL);
CREATE TABLE merged_into(old_master TEXT PRIMARY KEY, new_master TEXT NOT NULL, merged_at TEXT NOT NULL);
```

  `members` holds sorted program names joined with U+001F. Keys are the 64-hex person keys of 5.1 and master IDs are `M-` plus 10 hex (never reused, since each comes from a person key). `meta.secret_check` is the first 16 hex of `mac(b"crosswalk|check")`. The file holds no name, address, Client_ID value or date of birth. The dates in it are the times of decisions.
- XW-3 (a wrong secret). On open, a `secret_check` that differs raises `CrosswalkOrphaned`. The run then ignores the crosswalk and writes nothing to it, the pre-run summary says "The saved crosswalk was made with a different install secret, so it is not used.", and Settings says plainly that losing the secret orphans it and that restoring the backup brings it back.
- XW-4 (each batch, reading). Before step 9 of 6.10, `load_known(store, person_keys)` returns the `KnownMaster` for each person key present, following `merged_into` to the final master (stop at 20 hops and raise on a loop). `inherited_verdicts` returns a `PairVerdict(inherited=True)` for each saved pair whose two person keys are both in the batch, with the saved reviewer. `inherited_programs` returns `ProgramDecision(inherited=True)` for saved groups with at least one name in the batch. Each `KnownMaster` carries the key's `how` and its `decided_at` as `linked_at` (M06). M06 ID-6 and ID-8 and M07 PROG-9 already apply them, and a batch decision beats an inherited one. A join a person made in an earlier batch comes back as an `earlier_batch` automatic join, listed on Results with a split action (P-ID-3). A link the tool made comes back only if its reason still holds.
- XW-5 (new evidence). An inherited `same` verdict, or a reviewer-made saved link that would give an `earlier_batch` join, is not applied, and goes to the No longer apply list with `dob_now_differs`, when `score_pair` on the two current person records gives the evidence `dob_differs`. The pair is then an ordinary proposal if it scores high enough. A `different` verdict is never lapsed by new evidence, which is the conservative reading (log it). The saved row stays in the file.
- XW-6 (writing, at Download). `commit(store, view, reviewer, time)` runs once, right after M09's `session.export.download()` succeeds, and never in a practice run. In one transaction it inserts new `person` and `person_key` rows (`how` is the join reason, or `reviewer` for a decided pair, or `derived`). It points merged person keys at the winning master with the `how` of the decision that merged them, and writes `merged_into`. It points each key in `IdentityResult.released` at its new master with `how = 'derived'`. It also writes this batch's pair verdicts and program decisions (a newer decision for a pair replaces the older row). Only counted rows' person keys are written. A failure rolls back, leaves the files in place, and the receipt says "The saved crosswalk wasn't updated." The audit gets `CROSSWALK_UPDATED` with counts. Committing at Download rather than at each run is a choice to log. `first_batch` is `"B-" + the first 10 hex of mac(b"batch|" + the sorted source fingerprints)`, so the same files processed again are the same batch.
- XW-7 (idempotent). After a commit the stored crosswalk fingerprint in `Results` is refreshed, so nothing shows out of date, and Process again on the same files gives the same digest and counts. `Counts.matched_from_earlier` is the number of counted master IDs whose `first_batch` is not this batch (None while the crosswalk is off or orphaned). Results shows "N people were matched from earlier batches." (a claim test).
- XW-8. Master IDs: with a known person key, the ID is the saved one, except a key M06 released because a tool-made link no longer holds (ID-8). Otherwise it is M06's derived `M-` ID (5.3). A run with the crosswalk off gives the derived IDs, and so does a run after Forget.

### Matching calibration (8.8, fix plan 5.6)

`settings/calibration.toml`: `floor = 40`, `band_edges = [40, 62, 80, 100]`, `per_band = 100`, `joins_sample = 200`, `recall_target_pct = 98`, `joins_target_tenths = 995`, `possible_min_lowest = 40`, `known_pairs_advice = 50`.

- CAL-1 (pass and sample). `calibration_pass(rows, mac, weights)` calls M06 `resolve` on a copy with `possible_min = floor`, no verdicts, no `known` and `keep_compared=True`. It touches no decision, count, stale flag or undo entry, and the floor is never reported (H5). `band_of(score)` gives the four bands. `draw_sample(proposals, joins, per_band, mac)` takes up to `per_band` pairs from each band and up to `joins_sample` automatic joins. Order is by `sha256(seed + pair_id)`, where `pair_id` is the first 12 hex of SHA-256 over the two sorted person keys and `seed` is `mac(b"calibration|" + the SHA-256 of the sorted pair IDs)`. A band with fewer pairs gives all of them. The same batch gives the same sample whatever the row order. There is no `random` in `engine/`.
- CAL-2 (labeling). `CalibrationSession.label(reviewer, pair_id, Same | Different | Unsure)`. The two labelers need different names after trim and casefold (`labeler_same_person`). A labeler sees only their own labels until both call `finish(reviewer)` (`labels_hidden` otherwise). Each labeler is shown the two records and not the score, band or evidence, so the number cannot lead them (log it). After both finish, `disagreements()` lists every pair whose labels differ, Unsure against Same included. `settle(pair_id, label)` is made by both together. A pair that is Unsure for both, or stays Unsure after settling, is dropped. A draft with labels and pair IDs only is saved after each label to `calibration\draft.wcl` (encrypted like the labeled store) and removed when the calibration is saved. A draft for a different batch is refused (`draft_for_other_batch`).
- CAL-3 (known pairs). `KnownPairEntry(system_a, client_id_a, system_b, client_id_b)` becomes two person keys at once with `keys.person_key`. The Client_ID values stay in memory only for the screen and are never saved or logged. `known_pairs_check(entries, compared)` returns `not_in_batch`, `compared` (with each pair's score) and `never_compared`. The last is the number the spec asks for.
- CAL-4 (measures, all exact). Counts only, with `fractions.Fraction` where a ratio is needed. For each band: `population` (pairs in the batch), `labeled` (Same or Different), `same`. The rate is `same / labeled`, and a band with no labels is `band_unmeasured`. Estimated true matches in band b are `population_b * same_b / labeled_b`. `caught(L)` is the same sum using only labeled Same pairs scoring at least `L`. `recall(L) = caught(L) / estimated true total`. `suggest_line(...)` is the largest `L` in `[floor, 200]` with `recall(L)` at least 98%. Also report the estimated true matches missed at the line now in force. True matches here are pairs scoring at least the floor that are not automatic joins. Pairs under the floor are not measured, and the note says so. `joins_check(n, wrong)` is confirmed when `n > 0` and `wrong * 1000 <= n * (1000 - 995)`. The result always shows `n`, since a small sample is a weak confirmation (a question for Joe).
- CAL-5 (store). `calibration\labeled.wcl` is `WCL1` plus `dpapi.protect(json)`. The JSON holds, per settled pair, the two person keys, the evidence codes with integer parameters only (string parameters are dropped), the score at labeling time, the band, the label, and both labelers' names. It also holds the band populations, the join sample counts, the known-pair results as person keys with `compared` and score, `calibrated_at`, `weights_digest` (SHA-256 of the weights as canonical text), and the baseline rates. No name, address, ID or date. A new calibration adds its pairs, and a pair labeled again replaces the older label.
- CAL-6 (regression). `regression_check(store, weights, line)` re-scores every stored pair with `score_from_codes` and returns the rates before (the stored baseline) and after as integer pairs: Same pairs caught over all Same pairs, and Same pairs over all pairs at or above the line. `dropped` is true when either ratio is lower now (cross-multiplied). Settings runs it on demand and also after a weights file changes.
- CAL-7 (thresholds). `SetThresholds(possible_min, likely_min)` is entered in Settings, saved to `prefs.json` (two integers, the reviewer and the time), which H9 names as the home for thresholds, and must satisfy `possible_min_lowest <= possible_min < likely_min <= 200`. It marks `identity` stale, and writes `THRESHOLD_SET` once per number with the reviewer. A run reads them over `identity.toml`. They apply to this computer, not to one batch.
- CAL-8 (note). `Session.calibration_note() -> CalibrationNote | None` carries the date, per-band rates (`labeled`, `same`), the join result, the line in force, the recall at that line and `matches_weights`. M08's detail view shows one line from it. M09's methods note shows all of it. When `matches_weights` is false both say the rates were measured with earlier weights.

### Audit events (add to M09's `EVENT_SLOTS`, both logs)

`CROSSWALK_ON`, `CROSSWALK_UPDATED` (counts), `CROSSWALK_FORGET`, `SECRET_BACKUP`, `SECRET_RESTORE`, `CALIBRATION` (both labelers' names, counts of pairs, labels and joins), `THRESHOLD_SET`. Each carries the reviewer and time and no value. `THRESHOLD_SET` uses the `field_name` slot for the line's name and the `count` slot for its value.

### Settings screens (`ui/settings/`)

There is no board. Use the style guide and the M10 and M12 widgets. The `Settings` link and `SettingsDrawer` already exist from M10 (SPEC 11.3). M13 adds four cards to that drawer and no link.

1. **Install secret.** "Back up the install secret" and "Restore the install secret". Text says the backup goes somewhere the organization controls, and that losing the secret orphans the saved crosswalk and saved progress. The passphrase dialog asks twice and shows nothing. The folder callout of M09 shows for synced folders.
2. **Saved crosswalk.** Off by default, with one paragraph on what it stores (keyed hashes, master IDs, decisions, never names, addresses, IDs or dates) and what it needs (the data agreements, the secret backup). "Turn on" records the reviewer and time. When on, it shows since when and by whom, and counts of people, pairs and program groups. "Forget the saved crosswalk" asks for the typed word. An orphaned file shows the amber text of XW-3.
3. **Matching lines.** The proposal line and Likely line as number boxes with the current and the suggested value, and "Save" (`SetThresholds`). "Check saved labels" runs the regression and shows Same caught and precision, before and after, with a tag for dropped.
4. **Measure matching.** Opens `MatchingWindow`, a modal 1,100 by 720 window. It is held with a caption until a non-practice run has finished. Steps: Draw (counts per band and "Pairs per band", default 100, from 3 to 200), Label (the compare widget from M12, buttons Same, Different and Unsure with keys S, D and U, a progress bar, the labeler's name, "Hand over to the second labeler"), Settle (the disagreements), Known pairs (a grid of system and Client_ID for each side, with a note that about 50 is useful), Results (a band table, joins, known pairs, the suggested line, "Save these labels"). Calibration runs as M10's `calibrate` action (Matching people across files, Drawing pairs), and the backup as M10's `backup` action (Protecting the backup, SPEC 11.6.2). Both are already in `jobs/steps.py` and M01's `Step` enum, so add no step.

The screens read the session through `SessionBridge` only. The labeling screen shows client values from memory and never writes them. Progress messages hold counts only. M13 also adds the line "matched from earlier batches" to Results, a "from an earlier batch" note on inherited pair and program tags, and the `dob_now_differs` sentence to the No longer apply list (a few lines in M12's modules, listed in the report).

### Notes from the spec review (SPEC 1.1)

- The Settings link and drawer already exist from M10. Add this milestone's sections to `SettingsDrawer`, and don't add a second link.
- Fill M10's `FrameView.data_notes` when the crosswalk is on. That covers the line on each stage's data line and the paragraph in the Your data drawer, saying what crosswalk.db holds and that it holds no names, addresses, IDs or dates. Register each sentence with a CL- claim ID, and give each a claim test in `tests/copy/`.
- The SPEC section 11.8 data lines and the Your data drawer mention the crosswalk only while it's on. Test it both ways.

## Tests to write

Rule tests in `tests/rules/test_backup.py` (`BAK_1` to `BAK_4`), `tests/rules/test_crosswalk.py` (`XW_1` to `XW_8`) and `tests/rules/test_calibration.py` (`CAL_1` to `CAL_8`).

Backup.
- BAK-2 known answer, exact blob, ciphertext and tag. A round trip with a random salt, and two backups of one secret differ but both restore. A wrong passphrase, a one-byte change in each of the four regions, a short blob and an extra byte all raise the right code. NFKC: a composed and a decomposed `é` passphrase both restore. A passphrase under 12 characters and mismatched entries are refused. A static test finds `compare_digest`, `hashlib.scrypt` and `shake_256`, and no import outside the standard library. The blob never contains the secret bytes. After a restore, M01's record key known answer holds (`7533705e667f8cf12288` for `bytes(range(32))`). Restoring over a different secret needs `replace`. The audit line holds no secret and no passphrase.

Crosswalk. Fixtures in `tests/fixtures/crosswalk/`: `batch1_a.csv` and `batch1_b.csv` (the 12 C-01 records), `batch2_c.csv` (five new people, one a deliberate near-copy of an existing person: same surname, date of birth and address, a nickname for the given name, which scores as a Likely proposal and not a join) and `truth.txt` (which of the four batch 1 proposals are the same person).
- `test_xw_two_batches.py` (the fix plan test). Batch 1 with the crosswalk on, decide the four proposals to match the fixture's truth of 10 people, download. Batch 2 is the same files with rows shuffled plus `batch2_c.csv`. Every earlier master ID is unchanged. Exactly one pair is open, the near-copy. No earlier decided pair is asked again. The pairs decided the same come back as `earlier_batch` joins on Results, each with a split action and the earlier-batch note, and the pairs decided different are not proposed. Goal 1 is 10 plus 5. `matched_from_earlier` is 10. Shuffle again: nothing changes. A third batch with the near-copy decided same keeps its earlier ID.
- `test_xw_merge.py`. Two people with separate masters in batch 1 are decided the same in batch 2. The master with the earlier `created_at` wins, `merged_into` has the old ID, batch 3 resolves both person keys to the winner and lists them as one `earlier_batch` join, and the audit has `CROSSWALK_UPDATED`.
- `test_xw_new_evidence.py`. A saved `same` pair whose date of birth now differs is listed with `dob_now_differs`, is not joined, and is a proposal if the score allows. A saved `different` pair whose four facts now agree stays split.
- `test_xw_earlier_batch.py` (P-ID-3, M06 ID-8). (a) A pair joined by a person in batch 1 is an `earlier_batch` join in batch 2, listed with its reason. Pressing `These are different people` on it splits it, and the next commit stores the `different` verdict. (b) A pair the tool joined in batch 1 by `four_exact_facts`, whose address differs in batch 2, isn't joined. The key linked first keeps the saved master ID, the other gets its derived ID, the two master IDs differ, and after the commit the second key points at its new master. (c) With the crosswalk off, no join has the reason `earlier_batch`.
- `test_xw_programs.py`. A program group confirmed in batch 1 shows `from_earlier_batch` in batch 2. A batch `split` wins.
- `test_xw_privacy.py` (H9). Read the raw bytes of `crosswalk.db` for every name, street, ZIP, date and Client_ID in the fixtures. No hit. Key columns match the hex and `M-` patterns. After a commit the folder holds only `crosswalk.db`. The saved progress file holds no crosswalk row.
- `test_xw_orphaned.py`. Open the file under another secret: `CrosswalkOrphaned`, the run derives IDs, nothing is written, and the pre-run text appears. Restore the backup and it works.
- `test_xw_practice_and_off.py`. A full session with the crosswalk off creates no file. A practice run never reads or writes it. Turn on writes `CROSSWALK_ON` with the reviewer and time. Forget with the wrong word does nothing, with the right word deletes the file, marks identity stale, and later runs equal a run that never had a crosswalk.
- `test_xw_commit.py`. A forced SQL error rolls back with the file unchanged and the receipt note. Download then `session.stale` is empty and Process again gives the same digest and `matched_from_earlier`. Master IDs with the crosswalk off equal M06's `M-` known answers (`M-a7e53489dc`, `M-10438b4e7e`).
- `tests/invariants/test_crosswalk_properties.py` (hypothesis). For random shuffles and added subsets, the master ID of every person already in the crosswalk never changes, and the commit is idempotent.

Calibration. `tests/fixtures/calibration/make_population.py` builds 1,000 person rows in two systems with known true matches and degraded copies across all four bands. It may use `random.Random(7)`, since it is test code. The engine uses none.
- `test_cal_sample.py`. At most 100 per band, bands exact at 39/40, 61/62, 79/80 and 99/100, the same draw twice, the same draw with rows shuffled and with another `PYTHONHASHSEED`, a different draw under another secret, joins capped at 200, a thin band returns all its pairs. After a calibration pass, a normal run shows no pair under 62 and no changed decision, count, stale flag or undo entry.
- `test_cal_labels.py`. Same name refused (also with different case and spacing). Labels hidden until both finish. The disagreement list is exact. Settling closes it. Unsure for both, and Unsure after settling, are dropped. A draft restores. A draft for another batch is refused.
- `test_cal_measure.py` (hand-computed). Populations 100, 50, 20, 10 for bands 40 to 61, 62 to 79, 80 to 99 and 100 or more, with four labeled pairs each. Scores and Same labels: band 1 has 45 no, 50 no, 55 yes, 60 no. Band 2 has 63 no, 68 yes, 72 yes, 77 yes. Band 3 has 82, 88, 91 and 97, all yes. Band 4 has 101, 105, 112 and 128, all yes. Estimated true matches are `185/2`. Caught at 62 is `135/2`, so recall is `27/37`. The suggested line is 55. Missed at the line in force (62) is 25. A band with no labels is `band_unmeasured`. `joins_check` is confirmed at 200 joins with 1 wrong, not confirmed with 2 wrong, and `no_joins` at 0. Known pairs: 50 entered, 44 compared, 4 never compared, 2 not in the batch.
- `test_cal_store.py`. The stored JSON holds no fixture name, street, ID or date and no string parameter. A flipped byte is refused. A second calibration adds pairs and the newer label wins.
- `test_cal_regression.py`. Unchanged weights give `dropped` false. Lowering `dob_exact` from 42 to 10 gives true. A change that helps gives false.
- `test_cal_thresholds.py`. Bad ranges refused, the audit lines hold the reviewer, and identity goes stale.
- `test_cal_note.py`. The note feeds the detail line and the methods note, and says earlier weights when `matches_weights` is false.
- UI tests under `tests/ui/`. The footer link opens the drawer. Held captions. The label view never shows a score, band or evidence. Keys S, D and U. The progress bar reaches the total. Layout at 1280, 1366, 1440 and 1920. Progress messages hold counts only. The static `RunHold` test covers the new controls.
- `tests/copy/` claim tests for the crosswalk contents sentence, the orphaned sentence, "matched from earlier batches", the Forget and replace confirmations, the passphrase text, and the calibration sentences.

## Done when

- [ ] Every rule ID above has a named test. The two fix plan tests (5.4 and 5.6) are the tests named above and are green.
- [ ] The known-answer backup blob matches, and restore with the wrong passphrase or any damaged byte is refused.
- [ ] The two-batch test passes with the numbers above, and no earlier master ID changes in any property run.
- [ ] No name, address, ID or date is in `crosswalk.db`, `labeled.wcl`, `draft.wcl`, `prefs.json`, either audit log or any message (the scan tests pass).
- [ ] `grep` finds no `random` and no clock call in `engine/` or `session/` outside injected clocks, and no file opened for writing outside `store.py`, `crosswalk/store.py`, `calibration.py` and `backup.py`.
- [ ] No new dependency. `sqlite3`, `hashlib`, `hmac`, `secrets`, `unicodedata` and `fractions` only.
- [ ] `make test`, `make offline` and `make copy` are green, with counts in the report. `make screens` renders the Settings drawer in three states and the matching window at Draw, Label and Results, at 1440 and 1280, into `docs/milestones/screens/M13/`.
- [ ] The report's Questions for Joe list. (1) The crosswalk commits at Download. (2) A `different` verdict is never lapsed by new evidence, and a `same` verdict lapses only on a differing date of birth. (3) Labelers do not see the score. (4) A 99.5% join check from 200 joins is weak, and no interval is used. (5) The 12-character minimum for the backup passphrase. (6) A key whose tool-made saved link no longer holds gets a new master ID, and the key linked first keeps the saved one (M06 ID-8). (7) The calibration draft `draft.wcl` is an extra encrypted file in the calibration folder beside the labeled pairs H9 lists. (8) Which date of birth conflicts count (only `dob_differs`). (9) The crosswalk is not undoable. (10) The same names make the same batch ID, so processing the same files twice is one batch.
- [ ] The report is written, the branch is pushed, the pull request is opened, and work has stopped.

## Windows checks for Joe

Run from the repo with the branch checked out. Dev commands print counts and fixed labels only, through the M00 printer. Add the labels to `CountLabel`. The made-up CSV files named below are in the repo under `tests/fixtures/`.

1. `.venv\Scripts\activate`, then `python -m pytest -q`. Expect no failures.
2. `python -m wholecount.dev backup-demo`. Expect `backup_bytes 84`, `known_answer_matches 1`, `restore_ok 1`, `wrong_passphrase_refused 1`, `one_changed_byte_refused 1`, `files_written 0`.
3. Run `python -m wholecount`. Open Settings from the ledger footer. Under Install secret choose Back up, pick a folder in Documents, and type a passphrase twice. In Explorer the file is 84 bytes. In Notepad it is unreadable. Try a OneDrive folder and expect the amber callout. Choose Restore, try a wrong passphrase (refused), then the right one. Expect "This is the same secret. Nothing changed."
4. Under Saved crosswalk, expect Off. Turn it on. Add `tests/fixtures/crosswalk/batch1_a.csv` and `batch1_b.csv`. Process, answer the four pairs as `tests/fixtures/crosswalk/truth.txt` says (which are Same and which are Different), and Download to a temporary folder. Start over. Add the same two files and `batch2_c.csv`. Process. Expect Results to say 10 people were matched from earlier batches, and Fix problems to show one open pair.
5. `python -m wholecount.dev crosswalk-check`. Expect `people`, `person_keys`, `pair_verdicts`, `program_groups` and `merged` counts, `cell_values_found 0`, `wal_files 0`. Open `%LOCALAPPDATA%\Wholecount\crosswalk.db` in Notepad and confirm you see no names.
6. In Settings, choose Forget the saved crosswalk, type a wrong word (nothing happens), then `forget`. Expect the file gone and the stage strip to show Process as out of date.
7. Add `tests/fixtures/calibration/people_a.csv` and `people_b.csv` and Process. In Settings choose Measure matching. Set Pairs per band to 5. Enter the name Joe, label every pair, hand over, enter a second name, and label them again. Settle the disagreements. In Known pairs, enter the three pairs listed in `tests/fixtures/calibration/known_pairs.txt`. Expect the Results step to show a rate per band and a suggested line. Save.
8. `python -m wholecount.dev calibration-check`. Expect `labeled_pairs` above 0, `cell_values_found 0`, `regression_dropped 0`. Run it with `--weights-change dob_exact=10` and expect `regression_dropped 1`.
9. In Settings, Matching lines, set the proposal line to 70 and Save. Expect Process to show out of date. Set it back to 62.
10. Open the printable summary and confirm the methods note shows the measured rates and today's date. Open `calibration\labeled.wcl` in Notepad and expect unreadable binary.

## Out of scope

- Excel passwords (fix plan 4.3 step 5, not approved).
- Changing any matching weight or rule. Calibration measures them. A change to `identity.toml` is a separate request after Joe and the client agree the lines.
- Moving the crosswalk between computers, exporting or importing it, or reading it in any other program.
- Labeling more than once a year on a schedule, or reminders to do so.
- Machine rules and data agreements with St. Nicks (fix plan phase 7).
- Anything about the install secret beyond backup and restore (M01 owns its creation and storage).
