# M10 report

## Questions for Joe

Nothing blocks. These are the readings I made, the additions to the spec, and the differences from the prototype. The default is built in each case.

1. **Claim IDs are one per entry.** The milestone shares some claim IDs across entries. The registry holds one claim per entry and checks they're unique, so I numbered the extra ones:
   - `CL-OFFLINE-02` for `top.offline` and `CL-OFFLINE-03` for the narrow wording. `CL-OFFLINE-01` stays on M00's entry.
   - `CL-PRACTICE-01` for the tag and `CL-PRACTICE-02` for the ledger line.
   - `CL-FINAL-01` for "unique clients, final", `CL-FINAL-02` for the settled sentence and `CL-FINAL-03` for Goal 2's final line.
   - `CL-CHECK-READY-01` for the ready line and `CL-CHECK-READY-02` for the warning.
   - The footer's trust sentence is two entries, `ledger.foot.trust_offline` (`CL-TRUST-OFFLINE-01`) and `ledger.foot.trust_disk` (`CL-TRUST-DISK-01`), drawn as one sentence.
2. **Addition to SPEC 11.3: the top bar under 1360 wide.** It shows Close Wholecount, and Offline becomes "Offline, nothing leaves this computer," so the trust statement is visible at 1280 without opening a drawer (A-23).
3. **Difference from the prototype: no confidence chip in the top bar.** SPEC 11.3 doesn't list it, and SPEC 7.4 and 11.7 put confidence in the ledger, the Process callout and Download's held caption.
4. **Step weights.** Process uses the prototype's measured log (30.5 s). The other eight actions have no measured log, so their steps have equal weights.
5. **Two units added to M01's `Unit` enum: `TABLES` and `CHECKS`.** The milestone's units include tables and checks, which M01 didn't have. No second enum exists.
6. **The UI reaches the engine only through the session layer.** That's the layering rule from M00. So:
   - `session/progress.py` re-exports M01's progress types and defines nothing.
   - `session/frame.py` hands FrameView the engine's numbers, equations and reason sentence.
   - `JobCommand`, the one command a finished job runs inside, lives in `session/commands.py`.
7. **Two small engine additions.**
   - `engine/counts.ledger_lines` gives the ledger's form of the two equations, so the engine still builds every equation (A-22).
   - `confidence_reason` is split out of `confidence_sentence` in `summary_doc.py`, so the screen and the printable page share one sentence.
8. **Saved progress now stores the stage ID.** M09 didn't keep it, and the card needs it (A-19). `Session.stage` is set when the window changes stage, and the snapshot carries it.
9. **Start over deletes this session's saved progress only.** Other saved sessions and every downloaded file stay.
10. **While a run goes, all four result sections say "Being worked out now."** The milestone names Where they stand and The two counts. Confidence and Locations follow the same rule, so no half result shows anywhere.
11. **When any node is stale, all four result stages show as out of date together.** Those are Process, Fix problems, Results and Download, and their ledger sections say "Out of date. Process again." That's the most conservative reading of H13.
12. **Goal 2's sub line names the goal.** It reads "unique clients by program, a range to 7,121 until 14 pairs are decided," in the same form as Goal 1.
13. **The settled sentence shows only when rows aren't counted yet.** With rows all counted but pairs still open, the range line already says why the count isn't final.
14. **If the key file can't be read, the window still opens.** Saved progress stays off for that run, and the system check row says the key won't open. Keys made then wouldn't match the real ones, so nothing is saved.
15. **Closing lets go of the session,** and the app quits when its last window closes. With saved progress off, closing writes nothing.
16. **`python -m wholecount` now opens the window.** `python -m wholecount --version` prints the version line, and M00's entry test uses that flag now.
17. **Held Undo shows its reason to a screen reader, not on screen.** The strip has no room for a caption line under Undo, so the reason is its accessible description. A held button in a stage shows its caption on screen.
18. **Letter spacing is set on the font, not in QSS.** Qt's style sheets don't support letter spacing.

Changes to earlier tests, each small:
- `tests/outputs/test_writes_only_in_three_files.py` allows `build_qss.py`, whose CLI writes the theme text for inspection and never client data.
- `tests/unit/test_layout.py` no longer expects `wholecount/ui/theme` and `wholecount/ui/stages` to be empty, because M10 fills them.
- `tests/unit/test_dev_counts_only.py` runs `python -m wholecount --version`.
- `tests/rules/test_store.py` expects the saved snapshot's new `stage` key (question 8).
- `tests/unit/test_makefile.py` no longer treats `make screens` as a stub, and checks that it runs the tool offscreen.
- `tests/copy/test_registry.py` gains a check that no copy table mixes `text` with subtables. I hit that while writing this milestone's entries: the registry silently dropped the subtables.

One thing to know about how this milestone was tested. The claim test (`tests/copy/test_claims_have_tests.py`) failed first and listed every new claim until each one had its test. The UI widget tests were mostly written right after their widgets, not before. Where a check could pass by accident, it has a negative control.

## What was built

- **Theme (SPEC 11.2).**
  - `ui/theme/tokens.json`, `build_qss.py` (a pure function plus a CLI) and `apply.py`
  - The bundled Archivo Regular, SemiBold and ExtraBold, with `OFL.txt` and `SOURCE.txt`
  - `resource_path()` finds the font files, and `TEXT_PAIRS` lists the contrast pairs
- **Frame (SPEC 11.1, 11.3, 11.4).**
  - `stages.py` with `STAGES`, `view.py` with `FrameView` and `build_view`, and `captions.py`
  - `window.py` with the compact switch at 1360, plus `topbar.py`, `strip.py`, `ticker.py`, `ledger.py`, `sections.py`, `band.py`, `drawers.py`, `stage_head.py`, `close.py`, `a11y.py` and `bridge.py`
  - `ui/stages/__init__.py` with the stage registry and placeholder bodies
- **Progress (SPEC 11.6).** `ui/jobs/steps.py` holds the nine action step lists on M01's `Step` enum. The rest of `ui/jobs/` is `model.py`, `sink.py` (`QtProgressSink`) and `runner.py` (`JobRunner` and `error_code`).
- **Widgets.** `held.py` (`HeldAction`, `HoldReason`, `RunHold`), `callout.py`, `tag.py`, `source_mark.py`, `dataline.py`, `confidence.py`, `steplist.py`, `help.py`, `saved_progress_card.py` and `style.py`.
- **App entry.** `ui/app.py` builds the session, store, preflight and window. `__main__.py` opens it.
- **Tools.** `tools/screens.py` and `tools/screen_fixtures.py`, with `make screens` and `python -m tools.screens --demo-run [--practice]`.
- **Copy.** The window's sentences in `copy/en.toml`, including the 27 data-line parts, each fact with a claim test.

## Tests

| Command | Result |
| --- | --- |
| `make test` | 2872 passed |
| `make offline` | 60 passed |
| `make copy` | 843 passed |

New test files:
- `tests/ui/`:
  - `test_theme.py`, `test_contrast.py`, `test_captions.py`, `test_strip.py` and `test_ledger.py`
  - `test_held.py`, `test_progress.py`, `test_confidence_block.py`, `test_drawers.py` and `test_settings_drawer.py`
  - `test_footer_and_practice.py`, `test_layout_widths.py`, `test_accessibility.py` and `test_feature_ledger.py`
  - `test_view.py` and `test_screens_tool.py`
  - The fixtures are in `tests/ui/conftest.py`
- `tests/copy/test_dataline_claims.py` has the 27 data-line parts, one test each. `tests/copy/test_frame_claims.py` covers disk, network, AI, saved progress and Start over.
- `tests/support/write_spy.py`

Audit IDs closed:

| ID | Severity | Test |
| --- | --- | --- |
| A-16 | Medium | `tests/audit/test_A16_no_auto_close.py` |
| A-19 | Medium | `tests/audit/test_A19_saved_card_stage.py` |
| A-21 | Low | `tests/audit/test_A21_stage_header.py` |
| A-23 | Low | `tests/audit/test_A23_trust_and_close_visible.py` |

## Done list

- [x] Everything in What to build exists, and the frame shows all nine placeholder stages.
- [x] Every test above is written and passes. The claim test failed first. See the note at the end of Questions for Joe about the widget tests.
- [x] `make test`, `make offline` and `make copy` are green, with the counts above.
- [x] `make screens` runs. The milestone's PNGs are committed under `docs/milestones/screens/M10/`.
- [x] This report lists each difference from the boards and the prototype, each conservative reading, the addition to the spec (the top bar under 1360) and the missing confidence chip. The new actions' step weights are equal, and the report says so.
- [x] This report is written, the branch is pushed, and the pull request is open.

## Windows checks

Run from source. In PowerShell, `cd` to the repo, then run these four commands in order:
1. `py -3.12 -m venv .venv`
2. `.venv\Scripts\activate`
3. `pip install --require-hashes --no-deps -r requirements-dev.lock`
4. `python -m wholecount`

- [ ] 1. The window opens in under 3 seconds with Archivo text, not Segoe UI. Compare a heading with the board PNG. Letters should look the same width.
- [ ] 2. The top bar is dark with a blue square, `WHOLECOUNT`, and a status line at the right. Maximize the window. Close Wholecount is in the ledger footer at the bottom left.
- [ ] 3. Drag the window narrower than 1360 pixels.
  - The left column turns into a thin band under the strip.
  - Close Wholecount appears in the top bar.
  - Nothing scrolls sideways.
  - Use the Details link and confirm the full column slides over from the left and Escape closes it.
- [ ] 4. Click each of the nine stages. Each shows its header (`STAGE 03 OF 09 · PREPARE`), a Reads, Changes, Writes line and a placeholder. The current stage has a blue underline and a pale blue fill.
- [ ] 5. Click `What happens to your data`. Check the three boxes and the Never list read in plain words. Turn Saved progress off, confirm, and turn it on again.
- [ ] 6. Click the system check line in the ledger footer. The table says whether Geosupport is found. If Geosupport is installed it should show its release.
- [ ] 7. Watch a simulated run with `python -m tools.screens --demo-run`. Add `--practice` to see the PRACTICE tag on every stage.
  - The ticker appears under the strip, and the stage underlines fill as steps run.
  - `All steps` opens a list that covers the content without moving it.
  - Try Cancel and confirm the numbers return to how they were.
  - During the run, click the held Process button on Process. Nothing happens, and the caption under it says what releases it.
- [ ] 8. Leave the window open for 5 minutes. It must stay open.
- [ ] 9. Press Tab repeatedly and confirm a visible blue outline moves through every control, including the Details link and Undo.

## Screens

Committed in `docs/milestones/screens/M10/`:
- [`07-review-1440.png`](screens/M10/07-review-1440.png): the frame on Fix problems, before a run's body exists
- [`running-1440.png`](screens/M10/running-1440.png) and [`running-1280.png`](screens/M10/running-1280.png): a run on Placing addresses, with All steps open
- [`low-1440.png`](screens/M10/low-1440.png): Low confidence with the tick missing
- [`practice-1440.png`](screens/M10/practice-1440.png): the PRACTICE tag and ledger line
- [`drawer-details-1280.png`](screens/M10/drawer-details-1280.png), [`drawer-yourdata-1440.png`](screens/M10/drawer-yourdata-1440.png) and [`drawer-check-1440.png`](screens/M10/drawer-check-1440.png)

`make screens` also renders the idle frame of every stage at both widths, the finished run with its log, the stale frame and the held frame, in `build/screens/`.

Differences from the boards:
- **Stage bodies are placeholders.** M11 and M12 fill them.
- **There's no confidence chip in the top bar** (question 3).
- **The narrow top bar carries the full trust statement** (question 2).
- **The strip is 70px at 1280,** because "Match your columns" wraps to two lines there. It's 64px when no name wraps.
- **The Details drawer holds the same ledger column,** with its footer, inside a 320px panel.

## Not done

Nothing.
