# M13 report

## Questions for Joe

Nothing blocks. The milestone asks me to list ten readings, and I built the default in each case:

1. **The crosswalk is written at Download, not at each run.** It's written once, right after a download succeeds, and never in a practice run. A run only reads it.
2. **New evidence lapses a saved `same` verdict, and never a `different` one.** A saved `same` verdict, or a person-made saved link, is set aside when the two records now give `dob_differs`. A saved `different` verdict always holds. That's the conservative reading.
3. **Labelers don't see the score, band or evidence.** They see the two records only, so the number can't lead them.
4. **The join check is weak.** 99.5% from 200 joins confirms with at most 1 wrong. No interval is used, and the result always shows how many joins were sampled.
5. **The backup passphrase needs at least 12 characters.** It's set as `backup_passphrase_min` in `settings/privacy.toml`.
6. **A tool-made saved link that no longer holds gets split.** The key linked first keeps the saved master ID, and the other gets its own derived ID (M06 ID-8). The next commit points that key at its new master.
7. **`calibration\draft.wcl` is an extra file.** It's encrypted like `labeled.wcl` and holds labels and pair IDs only. It's removed when the labels are saved.
8. **Only `dob_differs` counts as a date of birth conflict.** A swapped day and month, or one digit off, doesn't lapse anything.
9. **The crosswalk isn't on the undo stack.** Turning it on and forgetting it say so on screen.
10. **One question: is a batch's ID built from file contents or file names?** XW-6 says "the sorted source fingerprints," which are file contents, and that's what's built. The done list says "the same names make the same batch ID." With contents, the same files read again are one batch, but a re-export with shuffled rows is a new batch. Should it be names instead?

Other readings, each built as described:

11. **Restoring a different secret makes every result out of date.** The secret's fingerprint is now part of the `sources` node, because every key changes with it.
12. **The crosswalk's part of the identity fingerprint is the file's size and change time,** not its contents. That's cheap to check on every view. A commit refreshes the stored fingerprint, so a download never makes results look out of date.
13. **The thresholds' part of the identity fingerprint is the two saved lines.** Saving them in Settings marks identity and everything after it out of date.
14. **The orphaned sentence is a fifth pre-run line on Process.** It shows only when the crosswalk is orphaned.
15. **Known pairs use the system name as it appears on Add your files.** By default that's the file name without its extension, and the Client_ID is typed as it appears in the file. Both turn into person keys at once and are never kept.
16. **The second labeler starts only after the first one finishes.** A third name is refused.
17. **No Results pair card carries an "earlier batch" tag.** An inherited `same` comes back as an `earlier_batch` join, listed with its reason and a split button. An inherited `different` is never proposed, so there's no card for it. Program groups from an earlier batch carry `FROM AN EARLIER BATCH` on Programs.
18. **The near-copy in `batch2_c.csv` is "Charlie Vega", a copy of Carlos Vega.** "Bob Smith" for Robert Smith Sr also proposed against Robert Smith Jr, which would have left two open pairs.
19. **In the two-batch test, Goal 1 reads 14 to 15.** The milestone's "10 plus 5" is the high end. The low end is 14 while the near-copy pair is open.
20. **The labeling view is a two-column grid,** not M12's compare widget. That widget shows the differing fields in bold, which would hint at the evidence.
21. **`calibration-check` reads `labeled.wcl` through DPAPI, so it works on Windows only.** On Linux the tests check it with nothing saved.
22. **One earlier test changed.** `tests/outputs/test_writes_only_in_three_files.py` now allows `backup.py` and `calibration.py` to write, as the milestone's done list says.

## What was built

- **Install secret backup** (`engine/secretbackup.py`, `session/backup.py`):
  - the 84-byte `WCB1` file and the known answer
  - restore with the typed word
  - `InstallSecret.backup()` and `same_as()`, so the bytes never leave the class unencrypted
- **Saved crosswalk:**
  - `engine/crosswalk/schema.py`, `store.py` (all SQL) and `apply.py`
  - `session/crosswalk.py` with turn on, forget, the state, the fingerprint, the batch ID and the commit after download
  - the runner hooks for known masters, inherited verdicts and programs, the lapse on new evidence, and `matched_from_earlier`
  - the receipt note when a commit rolls back
- **Calibration:**
  - `engine/calibration/` (`sample`, `labels`, `measure`, `regression`, `note`)
  - `session/calibration.py` with the labelers, the draft and labeled stores, known pairs, the report, the regression run, the note, and `SetThresholds` into `prefs.json`
  - `settings/calibration.toml`
- **Settings** (`ui/settings/`):
  - the four cards in M10's drawer: Install secret, Saved crosswalk, Matching lines and Measure matching
  - the `MatchingWindow` with Draw, Label, Settle, Known pairs and Results
  - the `LabelView`, with S, D and U keys
- **The rest of the window:**
  - the crosswalk data note on Download's data line and the Your data paragraph, shown only while it's on
  - the orphaned pre-run line
  - the earlier-batch tag on Programs
  - the calibration line in the confidence detail and the methods paragraph on the printable page
- **Jobs.** `BackupJob` (`backup`) and `CalibrateJob` (`calibrate`), on M10's existing steps.
- **Audit.** Seven events in both logs: `CROSSWALK_ON`, `CROSSWALK_UPDATED`, `CROSSWALK_FORGET`, `SECRET_BACKUP`, `SECRET_RESTORE`, `CALIBRATION` and `THRESHOLD_SET`.
- **Dev commands.** `backup-demo`, `crosswalk-check` and `calibration-check`, with their labels in `CountLabel`.
- **Fixtures.**
  - `tests/fixtures/crosswalk/`: `batch1_a.csv`, `batch1_b.csv`, `batch2_c.csv` and `truth.txt`
  - `tests/fixtures/calibration/`: `make_population.py` writes `people_a.csv`, `people_b.csv` and `known_pairs.txt`

## Tests

| Command | Result |
| --- | --- |
| `make test` | 3959 passed |
| `make offline` | 60 passed |
| `make copy` | 1700 passed |

New test files:
- **Backup.** `tests/rules/test_backup.py` covers BAK-1 to BAK-4: the known answer, any changed byte, NFKC, the refusals, the record key after a restore, and `backup-demo`.
- **Crosswalk** (`tests/rules/`):
  - `test_xw_two_batches.py`, the fix plan test
  - `test_xw_merge.py`, `test_xw_new_evidence.py`, `test_xw_earlier_batch.py` and `test_xw_programs.py`
  - `test_xw_privacy.py`, `test_xw_orphaned.py`, `test_xw_practice_and_off.py` and `test_xw_commit.py`
  - `tests/invariants/test_crosswalk_properties.py` (hypothesis)
- **Calibration** (`tests/rules/`):
  - `test_cal_sample.py`, `test_cal_labels.py` and `test_cal_measure.py` (the hand-computed case)
  - `test_cal_store.py`, `test_cal_regression.py`, `test_cal_thresholds.py` and `test_cal_note.py`
- **Static and dev.** `tests/rules/test_m13_static.py` and `tests/rules/test_m13_dev.py`.
- **UI.** `tests/ui/test_m13_settings.py` covers the cards, the matching window end to end, held controls, widths 1280 to 1920, the data notes both ways, and every claim on these screens.

## Done list

- [x] Every rule ID has a named test. The two fix plan tests are `test_xw_two_batches.py` (5.4) and the calibration tests (5.6), and both are green.
- [x] The known-answer backup blob matches, and a wrong passphrase or any damaged byte is refused.
- [x] The two-batch test passes, and no earlier master ID changes in any property run.
- [x] No name, address, ID or date is in `crosswalk.db`, `labeled.wcl`, `draft.wcl`, `prefs.json` or either audit log, and the scan tests pass.
- [x] No `random` and no clock call in `engine/` or `session/` outside the injected clock, and no file is opened for writing outside the allowed modules (`test_m13_static.py`, `test_writes_only_in_three_files.py`).
- [x] No new dependency. Only `sqlite3`, `hashlib`, `hmac`, `secrets`, `unicodedata` and `fractions` are used.
- [x] `make test`, `make offline` and `make copy` are green, with the counts above. `make screens` renders the drawer in three states and the matching window at Draw, Label and Results, at 1440 and 1280.
- [x] Questions 1 to 10 above are the milestone's list.
- [x] This report is written, the branch is pushed, and the pull request is open.

## Windows checks

Run from the repo with the branch checked out.

- [ ] 1. `.venv\Scripts\activate`, then `python -m pytest -q`. Expect no failures.
- [ ] 2. `python -m wholecount.dev backup-demo`. Expect `backup_bytes 84`, `known_answer_matches 1`, `restore_ok 1`, `wrong_passphrase_refused 1`, `one_changed_byte_refused 1`, `files_written 0`.
- [ ] 3. Back up and restore.
  - Run `python -m wholecount` and open Settings from the ledger footer.
  - Under Install secret choose Back up, pick a folder in Documents, and type a passphrase twice.
  - In Explorer the file is 84 bytes. In Notepad it's unreadable.
  - Try a OneDrive folder and expect the amber callout.
  - Choose Restore, try a wrong passphrase (refused), then the right one. Expect "This is the same secret. Nothing changed."
- [ ] 4. Two batches.
  - Under Saved crosswalk, expect Off. Turn it on.
  - Add `tests/fixtures/crosswalk/batch1_a.csv` and `batch1_b.csv`, then Process.
  - Answer the four pairs as `tests/fixtures/crosswalk/truth.txt` says, and Download to a temporary folder.
  - Start over. Add the same two files and `batch2_c.csv`, then Process.
  - Expect Results to say 10 people were matched from earlier batches, and Fix problems to show one open pair (Charlie Vega and Carlos Vega).
- [ ] 5. `python -m wholecount.dev crosswalk-check`. Expect `people`, `person_keys`, `pair_verdicts`, `program_groups` and `merged` counts, `cell_values_found 0` and `wal_files 0`. Open `%LOCALAPPDATA%\Wholecount\crosswalk.db` in Notepad and confirm you see no names.
- [ ] 6. In Settings, choose Forget the saved crosswalk. Type a wrong word (nothing happens), then `forget`. Expect the file gone and the stage strip to show Process as out of date.
- [ ] 7. Measure matching.
  - Add `tests/fixtures/calibration/people_a.csv` and `people_b.csv`, then Process.
  - In Settings choose Measure matching, set Pairs per band to 5, and draw.
  - Enter the name Joe and label every pair with S, D or U. Hand over, enter a second name, and label them again.
  - Settle the disagreements.
  - In Known pairs, enter the three pairs in `tests/fixtures/calibration/known_pairs.txt` (system `people_a` or `people_b`, then the Client_ID).
  - The Results step shows a line per band and a suggested line. Save.
- [ ] 8. `python -m wholecount.dev calibration-check`. Expect `labeled_pairs` above 0, `cell_values_found 0` and `regression_dropped 0`. Run it with `--weights-change dob_exact=10` and expect `regression_dropped 1`.
- [ ] 9. In Settings, Matching lines, set the proposal line to 70 and Save. Expect Process to show out of date. Set it back to 62.
- [ ] 10. Open the printable summary and confirm the methods note shows the measured rates and today's date. Open `%LOCALAPPDATA%\Wholecount\calibration\labeled.wcl` in Notepad and expect unreadable binary.

## Screens

Committed in `docs/milestones/screens/M13/`, each at 1440 and 1280:
- `m13-settings-off`, `m13-settings-on` and `m13-settings-orphaned`, with the drawer scrolled to M13's cards
- `m13-matching-draw`, `m13-matching-label` and `m13-matching-results`

There is no board for these screens. They use the style guide and the M10 and M12 widgets. A dialog is its own window, so the screens tool paints the matching window centered over a dimmed frame.

## Not done

- An "earlier batch" tag on Results pair cards (question 17). No inherited pair reaches the pair list.
