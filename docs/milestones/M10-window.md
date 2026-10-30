# M10: The window

## Goal

Build the frame every stage lives in, so M11 and M12 only have to fill the body. That means the theme from tokens, the bundled Archivo font, the top bar, the stage strip with live captions, the run ticker, the ledger (column and band), held controls, the Undo control, the "Your data" drawer, the per-stage data line, the confidence section, the progress plumbing (worker thread, `ProgressSink` adapter, cancel) and accessibility. Stage bodies are placeholders in this milestone. The frame must already behave correctly at 1280, 1366, 1440 and 1920 wide, and `make screens` must render it.

The progress and confidence design is the prototype Joe approved (variant C ticker on every stage, plus variant B run panel on Process). The prototype is `docs/context/design/prototype/progress-confidence.html` in this repo (open it in a browser and use the arrows in its bottom bar), and its markup and copy are the reference for everything below. The milestone text is complete without it (SPEC 11.6), so where the two differ, this file wins. M12 builds the Process panel itself, using the `StepList` widget built here.

## Spec sections

11.1 to 11.4 and 11.6 to 11.9. Also H4, H8, H13, H14, H15 and H16 (section 2), 3.2 and 3.4 (threads, commands, Undo label), 7.1 to 7.4 (what the ledger shows, both balances), 8.5 (Undo), 8.7 (the reviewer's name in the footer), P-GEO-4 (PRACTICE, the reference file in the system check), 10.4 (stale captions) and 12.6 (the network drive note stays with M11). Sections 8.8 and 10.5 appear here only as empty slots that M13 fills.

## Depends on

- M00 for the repo, the Makefile, the copy registry and its lint, the guard, and the claim test helpers.
- M08 for `Session`, commands with `label` and `invalidates`, `staleness.py`, counts, `balance_lines`, `Locations`, `SetReviewer`, confidence, and `Results.practice`.
- M09 for saved progress (`session/store.py`) and the audit trail.
- M05 for the preflight (backend name, Geosupport release and `release_stale`, reference kind and row count).
- M13 builds after this milestone. It adds its sections to the Settings drawer this milestone builds and fills the slots named in Out of scope.

Names below follow SPEC 3.3. If an earlier milestone used a different name, use the real one and list the difference in the report. `ProgressSink`, `ProgressMessage(message_id, params)`, `SourceRef(letter, file_name)`, `StepRef(step)` and the `Step` enum come from M01's `wholecount/engine/progress.py`. Import them and define no second copy.

## Branch

`build/m10-window`

## Read first

- `SPEC.md` sections 11, 7 and 8.7, then H8, H13 to H16.
- `docs/context/design/style-guide/README.md`, `tokens.json`, and every `components/*/README.md`.
- Boards (HTML and PNG). The frame is identical on all of them. Use `C_Cockpit`, `C1_Files.dc.html` for the strip, ledger and footer, `C6_Narrow_1280.dc.html` for the band, the top bar Close button and the narrow strip, `C3_Fix_Groups.dc.html` for the ledger with numbers.
- The prototype, `docs/context/design/prototype/progress-confidence.html`. Read the `.ticker`, `.dropdown`, `.step`, `.log`, `.ack`, `.drawer`, `.flow` and `.never` styles and the `ledger()`, `ticker()`, `confBlock()` and `drawer()` functions.
- `docs/audit/A-claims.md` entries A-16, A-19, A-21 and A-23.
- `legacy/ui/app.js` functions `renderRail`, `vCheck` (the system check table) and `vResume` for features that need a home. Reference only.

## What to build

### 1. Files
```
wholecount/ui/theme/tokens.json        copy of the style guide tokens, name changed to Wholecount
wholecount/ui/theme/build_qss.py       tokens to QSS (pure function, plus a CLI that writes build/theme.qss)
wholecount/ui/theme/apply.py           apply_theme(app): fonts, palette, QSS
wholecount/ui/theme/fonts/             Archivo-Regular.ttf, Archivo-SemiBold.ttf, Archivo-ExtraBold.ttf, OFL.txt, SOURCE.txt
wholecount/ui/frame/stages.py          STAGES registry, the one list of stages
wholecount/ui/frame/view.py            FrameView snapshot and build_view(session)
wholecount/ui/frame/captions.py        stage_state() and stage_caption() for all nine stages
wholecount/ui/frame/window.py          MainWindow and the compact switch
wholecount/ui/frame/topbar.py  strip.py  ticker.py  ledger.py  band.py  drawers.py  stage_head.py  close.py  a11y.py
wholecount/ui/jobs/runner.py  sink.py  model.py  steps.py     progress plumbing
wholecount/ui/widgets/held.py  callout.py  tag.py  source_mark.py  dataline.py  confidence.py
wholecount/ui/widgets/steplist.py  help.py  saved_progress_card.py  style.py
tools/screens.py  tools/screen_fixtures.py
tests/ui/  tests/copy/  (see Tests to write)
```

The UI reads the session only through `build_view(session) -> FrameView`, a frozen dataclass snapshot, and changes it only through `SessionBridge` (below). Tests build a `FrameView` directly, so most frame tests need no engine.

### 2. Theme
- `tokens.json` is copied from the style guide. A test compares every color value with `docs/context/design/style-guide/tokens.json`, so the two cannot drift.
- `build_qss.py` is a pure function `build_qss(tokens) -> str`. It runs when the app starts (cached) and nothing generated is committed. SPEC 11.2 allows startup or build time, and a test checks that the QSS applied to the running `QApplication` equals `build_qss` of the shipped `tokens.json`. `python -m wholecount.ui.theme.build_qss --out build/theme.qss` writes the text for inspection.
- Widgets get styled through dynamic properties, never inline colors. Set them with `style.set_prop(widget, "kind", "primary")`, which sets the property and re-polishes the widget. The properties are:

| Property | Values | Used on |
| --- | --- | --- |
| `kind` | `primary`, `secondary`, `quiet`, `held` | `QPushButton`. Quiet also takes `tone` of `nav` (blue-500) or `lesser` (ink-2). |
| `callout` | `needs`, `decided`, `wrong`, `ink` | `QFrame`. A white card with a 3px top rule in blue-500, green-500, amber-500 or ink. Borders blue-300, green-300, amber-300, line. |
| `tag` | `needs`, `confirmed`, `wrong`, `neutral` | `QLabel`. `needs` is solid blue-500 with white text. The others follow `Tags/README.md`. |
| `state` | `current`, `done`, `nothing`, `later` | strip items. Plus `stale` as a separate boolean property. |
| `role` | `kicker`, `h2`, `count-lg`, `count`, `count-row`, `body`, `row-title`, `note`, `caption`, `micro`, `strip-kicker`, `stage-name`, `column-head` | `QLabel`. One rule per type style in `tokens.json`, with size, weight, letter spacing and color. |
| `tone` | `muted`, `ink-2`, `amber`, `blue` | `QLabel`, for text color only. |
| `held` | `true` | any control covered by the run hold (section 10). |

- Rules the QSS must follow, each with a test. No `border-radius` other than 0. No `box-shadow`, gradient or `rgba(`. Every color in the output is one of the token values or `#ffffff`. No red. Borders are 1px, except 3px on the top or bottom only (never left or right). Every interactive class has a `:focus` rule that shows a 2px blue-500 border without changing the widget's size, and a `:hover` rule. Buttons have `min-height: 36px`.
- `fonts.py` loads the three TTFs with `QFontDatabase.addApplicationFont` after the `QApplication` exists, checks each returns a valid id, and builds the family list `Archivo, Segoe UI, sans-serif`. If a font fails to load, the app still starts, adds an H8-safe line naming the font file to the in-memory run log (no file is written, H9), shows `fonts.archivo` as failed in the system check, and uses Segoe UI. Never reference a font by URL or from the network.
- Get the static TTFs from the Archivo project (SIL OFL 1.1) once, commit them with `OFL.txt` and a `SOURCE.txt` giving the source address and SHA-256 of each file. M14's A-20 test allowlists that `SOURCE.txt` by name as provenance. If the cloud session cannot fetch them, stop and put the question at the top of the report. Do not substitute another font.
- The app font is Archivo at a 13px pixel size, set once in `apply_theme`. Use pixel sizes everywhere.
- Archivo must not be fetched from Google Fonts anywhere. A static test greps `wholecount/` and `tools/` for `fonts.googleapis`.

### 3. The window shell and the stage registry
- `stages.py` defines `STAGES`, a tuple of nine `Stage(id, number, technical, plain, subtitle_id)` in the order of SPEC section 1. IDs are `sources`, `schema`, `prepare`, `map`, `programs`, `run`, `review`, `summary`, `export`. Plain names come from the copy registry. Everything that shows a stage name or number reads this one list. That includes the strip, every stage header, the saved progress card, the audit and the receipt. Nothing else may contain a stage name or `of 09` as a literal (A-19, A-21).
- `MainWindow(QMainWindow)` holds a vertical stack. Top bar (48px). Stage strip. Run ticker (34px, hidden when idle). Ledger band (44px, narrow mode only). Then a horizontal split of the ledger column (280px, wide mode only) and the stage area. The stage area is a `QScrollArea` with the horizontal bar off and a vertical bar only when needed. Content padding is space-6 (24px) at the sides and space-5 (20px) top and bottom.
- Minimum window size is 1280 by 720. The window opens at 1440 by 980 when the screen allows it, and otherwise at the screen's available size.
- `compact` is true when the window is narrower than 1360. `resizeEvent` calls `apply_mode(compact)`. It hides the ledger column and shows the band, moves Close Wholecount into the top bar, switches the strip to its compact style, and re-parents the one `LedgerPanel` widget into the Details drawer when the drawer is opened. There is only ever one `LedgerPanel` instance. Crossing the breakpoint in either direction keeps scroll positions, the open drawer, and every held state.
- Stage bodies are produced by `StageRegistry.build(stage_id) -> QWidget`. In M10 each returns a placeholder (the `StageHead`, the `DataLine`, and one note) so the frame can be shown. M11 and M12 register the real bodies. Opening a different stage starts it at the top. A stage the operator comes back to keeps its grid scroll positions, which is the grid's job (SPEC 11.4).
- `SessionBridge(QObject)` is the only thing the UI uses to touch the session. `dispatch(command) -> CommandResult`, `undo()`, and `start_job(job)`. It emits `changed` after a command or undo has re-derived everything downstream (SPEC 8.5), and `stale_changed(set)`. Widgets redraw from a fresh `FrameView` on `changed`, never from partial state.
- `StageHead(stage_id, actions=[], empty=False)` is the one function that builds every stage header, including empty states (A-21). It shows the kicker `STAGE 07 OF 09 · REVIEW` (10px, 800, 0.14em), the plain name at h2, the one-line subtitle in muted body, and the action area at the right. The action area holds `HeldAction` widgets (section 10). The count in the kicker is `len(STAGES)`.

### 4. Top bar
- 48px, ink fill, on-dark text, 20px side padding. A 12px blue-500 square, the wordmark `WHOLECOUNT` (14px, 800, 0.06em) read from `brand.PRODUCT_NAME`, then at the right the status line (11.5px, on-dark-muted): `Offline`, the backend, and when progress was last saved.
- Backend text, from the preflight. `Geosupport Desktop Edition 24B on this computer` (release read from the install, with `, more than a year old` in amber-700 when `release_stale`). `Address reference file, exact matches only`. `Addresses will not be placed`. The release also goes to both audit logs (M09 writes it).
- PRACTICE. When `FrameView.practice` is true (example data is loaded, or the run used the sample reference, P-GEO-4) the bar shows a solid amber `PRACTICE` tag beside the wordmark, and the ledger's This batch section says `Practice run. Example data, not for reporting.` (claim `CL-PRACTICE-01`). The bar is on every stage, so every screen carries it.
- Saved text. `progress saved just now`, `progress saved 2 min ago`, `progress saved 3 h ago`, `saved progress is off`, `nothing to save yet`. A 30 second timer refreshes the relative time. The time comes from the session store, not the clock at the moment of drawing.
- Under 1360 wide the bar also shows `Close Wholecount` as a bordered quiet button (transparent, 1px #605d5d border, on-dark text, 11.5px, 800, 36px tall), and the word `Offline` becomes `Offline, nothing leaves this computer`. The second change is there so the trust statement is visible without opening a drawer at 1280 (A-23). Report it as an addition to SPEC 11.3.
- There is no confidence chip in the top bar. The prototype's variant C has one, but SPEC 11.3 does not list it and SPEC 7.4 and 11.7 put confidence in the ledger, the Process callout and Download's held caption. Report it as a difference from the prototype.

### 5. Stage strip
- `StageStrip` holds nine `StageItem` widgets (stretch 1 each) and one `UndoItem` (fixed 176px, 150px when compact) after a 1px line-soft divider. Height is the `strip-height` token (64px) and grows to fit a wrapped name when compact. It never scrolls and has no scroll area.
- `StageItem` is a `QPushButton` whose three child labels ignore the mouse. It paints its own 3px bottom rule in `paintEvent`, because QSS cannot draw a partial fill. Lines are the strip-kicker (`07 REVIEW`, 9px, 800, 0.1em), the stage name (12px, 800, 11.5px when compact, word wrap on, up to two lines) and the caption (10.5px, elided, full text in the tooltip and in `accessibleDescription`).
- States, from `Stage strip` in the style guide. Current is blue-100 fill, blue-500 rule, blue-700 name and caption. Done with work is an ink rule. Nothing to decide is a line-2 rule. Not yet has no rule and a muted name. Set `aria-current` equivalent with `accessibleName` ending in `, current stage`.
- Stale. A stale stage keeps its state but its caption becomes `out of date` in amber-700 (copy `strip.cap.stale`). The strip never says a count for a stale stage.
- Run underline. While a job runs, a stage that owns running steps paints its rule as a track (line-soft) with a blue-500 fill from the left, as the prototype's variant C does. The fraction comes from `ProgressModel.stage_fraction(stage_id)`. Owners are `prepare` for tidying, `run` for reading, checking and placing, `review` for copies, and `summary` for matching and counting. When the job ends the rule goes back to its state color.
- Clicking an item calls `window.go_to(stage_id)`. Navigation is never held, and no stage is locked. A stage that cannot show results (Results and Download while stale) shows its held caption inside its own body.
- `accessibleName` of an item is `Stage 07, Fix problems, 1,232 rows open` plus `, current stage` or `, out of date` when they apply.

### 6. Captions and states for all nine stages
`captions.py` has `stage_state(stage_id, view) -> StageState` and `stage_caption(stage_id, view) -> Caption(copy_id, params, tone)`. They read only `FrameView`, so M11 and M12 don't touch them. The starting text is below. `n` values are formatted with thousands separators. A caption is data. A fixed phrase appears only when there is nothing to count.

| Stage | Caption by case | State rule |
| --- | --- | --- |
| sources | none yet `no files yet`. Otherwise `{files} files, {tables} tables`. | done once a table is included, else later. Current wins. |
| schema | `nothing to decide` when the schema is the default. `{n} custom fields` when it was changed. | nothing, or done when changed |
| prepare | no steps `no steps yet`. Steps proposed and not yet kept `{n} steps proposed`. After Continue `{n} steps kept`. When any step changed nothing, add `, {m} do nothing` in amber. | done with work, or nothing when there are no steps |
| map | `{m} of {t} tables confirmed`. When any column looks wrong, `{k} look wrong` in blue-700 with weight 600. | done when all confirmed |
| programs | `{n} programs to confirm` while groups are unconfirmed. `{n} programs, confirmed` after. `no program column` when no table has one. | done, or nothing when no table has a program column |
| run | `ready to run` before. `running` while a run goes. `done in {secs} s` after. `out of date` when stale. | done after a run |
| review | before a run `not run yet`. After, `{n} rows open`. When none, `all decided`. | done when no rows are open, or after `FinishReview` |
| summary | before a run `not run yet`. `{n} pairs open`, with `, {g} copy groups` when copy groups are open. With none open but rows not counted yet, `{k} not counted yet`. When all are zero, `final`. | done when final |
| export | before a run `not run yet`. `held, confidence is Low` while the Low tick is missing. `{n} files ready`. | done after a download this session |

Undo item. Line one `UNDO`. Line two is the label of the top command on the undo stack, as `Command.label` gives it (for example `Set 96 summary rows aside`), blue-500, 12px, 800, elided, full text in the tooltip. Line three is `takes back one change`. With an empty stack, line two reads `Nothing to undo` in muted and the item is held. Clicking calls `bridge.undo()`. The item is held during a run (section 10).

### 7. Run ticker
- `RunTicker` is 34px tall, white, 1px line bottom border, 20px side padding. It is hidden until a job starts and stays after it finishes until the next job or Start over. A 2px blue-500 bar runs along its bottom edge, width equal to `ProgressModel.overall_fraction()`. The bar's width never decreases.
- While running, left text `Step {i} of {n} · {step name} · {done} of {total}` (12px, 800, tabular figures) and, beside it, the message in muted 12px, elided, from the latest `ProgressMessage`, for example `Looking up addresses, [A] clinic_export.csv`. A source reference draws as the 14px ink source mark and the file name. At the right, `All steps` (quiet nav) and `Cancel` (quiet lesser).
- After a run, `Last run finished in 30.5 s` and `7 steps, nothing written to disk`, then `Show the log`. When saved progress is on, the second text ends `except your saved decisions, encrypted`. Actions other than Process read `{action} finished in {secs} s` and `{n} steps`. After a cancel it reads `Run cancelled. Nothing changed.`
- The dropdown is a child frame of the central widget, raised over the content and positioned under the ticker, so it never pushes the layout down. It is 560px wide at most, with a 3px blue-500 top rule, and shows a `StepList` (running) or the log (finished). Escape or a click outside closes it. It must not take focus away from the stage unless opened by keyboard.
- The log lists every step with its duration and what it found. Durations come from `time.monotonic()` and are rounded to tenths. Found text is the step's closing `ProgressMessage`, for example `6,084 passed, 1,232 need a decision, 96 set aside`.
- `StepList` and `StepRow` are shared widgets. A row has the step name (800), a count `852 of 6,084` (muted, tabular), a 4px bar (line-soft track, blue-500 fill, ink when done) and a one-line message (11.5px, muted, elided). Waiting rows show `waiting` and a muted name. Finished rows show the found message. M12 mounts the same widget on Process.
- Respect reduced motion. There is no animation in the ticker beyond the bar width, and the bar width is set directly. Do not add easing.

### 8. Ledger
- `LedgerPanel` is a 280px white column with a 1px line right border. Padding 18px, sections 16px apart. Each section has a kicker (9.5px, 800, 0.14em, uppercase, muted) and a 1px line-soft rule above it, except the first. The kicker of The two counts is blue-500, and it is the only blue kicker.
- Sections in order. This batch. Where they stand. Stage sections (a slot, section 8a). The two counts. Confidence in this batch. Locations. Then the footer on bg-surface with a 1px line top border.
- Before a run each section says in one sentence what it does not know yet. The starting text is in the copy table. While a run goes, Where they stand and The two counts say `Being worked out now. The numbers fill in when the run finishes.` They never show half a count.
- Where they stand after a run shows the 10px stacked bar (counted ink, not counted yet blue-500, set aside line-2, 1px line border), three rows (Counted, Not counted yet in blue-700, Set aside) with tabular figures, and the first equation from `FrameView.balance_lines`, `{counted} + {not_counted_yet} + {aside} = {received}. The three add up to the rows received.` The UI never builds an equation itself (A-22). If the engine's balance check fails, show `The numbers do not add up. Counts are held until this is fixed.` in amber, show the numbers, and show no counts anywhere (H4).
- The two counts show the count at 28px. Goal 1 reads `5,940` with `unique clients, a range to 5,954 until 14 pairs are decided`. When copy groups are open too, the end reads `until 14 pairs and 3 copy groups are decided` (SPEC 7.2). Goal 2 uses the same form. When `FrameView.is_final` is true the sub line is `unique clients, final`. Otherwise add the settled-so-far sentence from SPEC 7.2 beneath, for example `Settled for the rows counted so far. 1,232 rows aren't counted yet.` The word `final` appears only when `is_final` is true (no pairs or copy groups open and no rows not counted yet, M08 COUNT-2), and the engine computes it, never the UI. Location problems never stop it. When Results is stale, both counts are replaced by `Out of date. Process again.` (H13).
- Locations carries the second equation. Rows `Mapped, high confidence` (ink), `Mapped, low confidence` (amber) and `Counted but not mapped` (amber outline). Under the last, its breakdown in muted rows, each shown only above zero: `No fixed address`, `Outside NYC`, `Address problem`, `Not found`, `No geocoder` (P-VAL-1, Q1). Then the equation from `balance_lines`, `{high} + {low} + {not_mapped} = {counted}. The three add up to the rows counted.` and `A weak match is never labeled fully verified.` Before a run, `Addresses are not placed yet.` These rows describe the map only. No count anywhere depends on them (P-VAL-2).
- Footer. The system check line (quiet nav, 12px, 800) reads `This computer is ready for real data` when the preflight is clean and `Addresses will not be placed on this computer` in amber when no real backend is present. It opens the system check drawer (section 12). Then `What happens to your data` (quiet nav). Then the trust sentence in micro muted: `Nothing leaves this computer. Client data is written only to the files you download.` and, only when saved progress is on, `Your decisions are saved, encrypted, never the data.` (SPEC 11.3). Then the reviewer line `Reviewer: {name}` with a quiet `Change`, which opens a small dialog with one `QLineEdit` and fires `SetReviewer(name)` (SPEC 8.7). The dialog shows M08's refusal reason. Before Fix problems has asked, the line reads `Reviewer: not asked yet`. Then `Close Wholecount` (secondary, 36px) and `Start over` (quiet lesser). In compact mode Close lives in the top bar and the footer keeps the others. `Change` registers with `RunHold`. The footer also holds the `Settings` link this milestone builds (see the notes from the spec review). M13 adds sections to that drawer and no link.
- **8a. Stage sections.** `LedgerPanel.set_stage_section(widget | None)` puts a section under Where they stand. M10 builds the three the boards show as widgets that read `FrameView`. Tidy up (Proposed by the tool, Added by you in green-700, Removed, Do nothing here in amber-700, and the note `Steps add columns. Nothing is removed or overwritten.`). Match your columns (Confirmed `2 of 5`, Required fields set, Look wrong in blue-700). Programs (Files with a program column, Names found, Counted as programs, Groups to confirm in blue-700, Confirmed by you, and, when a preview exists, the preview's two counts marked `from the preview` with `Preview taken at {time}, before your last change. Refresh it below.` in amber-700 when stale). Showing these three belongs to the stage that is open.
- **8b. The band.** `LedgerBand` is 44px, white, with 1px line borders top and bottom. Four groups with 1px line-soft dividers, each a 9px kicker and a 12.5px line. BATCH `7,412 rows in · 5 files`. STANDING `6,084 counted · 1,232 not yet · 96 aside`. COUNTS (blue-500 kicker) `5,940 people to 5,954 · 7,106 by program`. LOCATED `5,802 high · 198 low · 84 not mapped`. Before a run each group shows its short pre-run phrase. A `Details` quiet link at the right opens the drawer. Text is elided, never wrapped, and the band never grows past 44px.
- **8c. The Details drawer.** A `Drawer` is an overlay frame, a child of the central widget, with a scrim of ink at 35 percent opacity (the one allowed use of alpha, drawn in `paintEvent`, not QSS). Details opens from the left edge, 320px wide, and holds the same `LedgerPanel`. Escape and the scrim close it. Focus moves into the drawer on open and returns to `Details` on close. Tab does not leave the drawer while it is open.

### 9. Confidence on screen (ledger section and shared block)
- `ConfidenceBlock(view, full: bool)` is one widget used in the ledger, in the popover and, from M12, in the Process callout. It shows the kicker `Confidence in this batch`, the level word (18px, 800; ink for High, amber-700 for Medium and Low), the reason sentence from the engine in `note` size and ink-2, and the link `How this is worked out`.
- The reason sentence is built by `engine/confidence.py` (M08) from the three measures. The UI does not build it. For example `6,084 of 7,412 rows are counted, and 14 possible same-person pairs are still open.` The level word and the sentence read together as `Medium. 6,084 of 7,412 rows...`. When nothing was looked up the reason is the engine's `Addresses weren't placed, so confidence can't be High.`
- `How this is worked out` opens a popover (not a drawer) over the ledger with the three measures. Each row has the measure's name, its value, and a muted line saying what High needs and what makes it Low, for example `6,084 of 7,412. High needs 95%. Under 80% is Low.` Rows that miss High show the value in amber-700. The third measure reads `not available` when nothing was looked up. The numbers on the screen come from `settings/confidence.toml` through `FrameView.confidence.thresholds`, never from literals in the widget. A test changes the toml values and sees the text change.
- Calibration slot. When `FrameView.confidence.calibration` is not None, the popover adds one line with the measured rates and the calibration date (SPEC 7.4, 8.8). M13 supplies the value and its copy. M10 builds the slot and tests it with a fake value.
- There are no percentages in the headline and no letter grades. Percentages appear only inside the three measure rows.
- Low. A checkbox row `I have seen that confidence is Low. Download waits for this tick, and the tick goes to the audit log with the time.` sits in a blue-100 box with a blue-300 border, in the ledger section and in the popover. Ticking calls `bridge.dispatch(AcknowledgeLowConfidence())` (M08/M09 own the command and the audit entry). The tick resets whenever the level is recomputed. The widget just mirrors `FrameView.confidence.acknowledged`.
- Before a run the section reads `Worked out from the checks once the run finishes. It says why, in one line.`
- Colors follow SPEC 7.4. Never green for confidence. The only blue is the tick box and links.

### 10. Held controls and the run hold
- `HeldAction(QWidget)` holds a `QPushButton` and a caption label under it. `set_label(copy_id)`, `set_kind("primary" | "secondary" | "quiet")`, `set_hold(reason: HoldReason | None)`. With a hold, the button gets `kind="held"` (bg-surface fill, muted text, line-2 border), clicks do nothing, it stays focusable, and its `accessibleDescription` is the caption, so a screen reader says what releases it. It is never `setEnabled(False)`. The caption is 11.5px muted, always visible while held, and gone when released. `HoldReason(copy_id, params)`.
- Several holds can apply. The run hold wins. Otherwise show the first hold in the order the stage listed them.
- `RunHold` is a controller that every data-changing control registers with (`RunHold.register(widget, group="data")`). `HeldAction`, `QCheckBox`, `QComboBox`, `QLineEdit` and Undo can register. While a job runs it sets `held=true`, disables editing (not focus) and shows the caption `Held until the run finishes. A change now would not apply to this run.` (`hold.run`). Navigation, scrolling, `Show data`, help buttons, `What happens to your data` and the system check line never register. A static test lists every widget class in `wholecount/ui` that fires a command and fails if one is neither registered nor on a short allowlist with a reason.
- Releasing is by the job's `finished`, `cancelled` or `failed` signal, and the controller restores each control to the hold it had before, not to unheld.

### 11. Close Wholecount and Start over
- `Close Wholecount` asks for confirmation when a batch is in memory. Text `Close Wholecount? The files you added and every result are cleared from this computer's memory.` and, when saved progress is on, `Your decisions and set-up stay in saved progress for 7 days.` or, when it is off, `Nothing is kept.` Buttons `Close Wholecount` and `Keep working`. With no batch it closes at once.
- `Start over` asks `Start over? This clears the batch from memory and deletes its saved progress.` with `Start over` and `Keep working`. Downloaded files are never touched. Log the delete-saved-progress choice as a conservative reading in the report.
- Wholecount closes only when the operator closes it or the operating system ends it. There is no timer, no heartbeat and no idle limit (A-16). Closing the window with the title bar behaves exactly like the Close button. A running job is cancelled first, with the same confirmation text plus `The run in progress will be cancelled.`

### 12. The "Your data" drawer and the system check drawer
- `YourDataDrawer` opens from the right, 520px wide at most, from the ledger footer link. Title kicker `Your data`, h2 `What happens to your data` (21px). Then the three-box diagram from the prototype. Box one `Your files`, `Opened once when you add them. Wholecount never changes them.` An arrow label `read into memory`. Box two, with a 2px ink border, `Memory on this computer`, `Every step works here: tidying, checking, placing, matching, counting. Nothing is sent anywhere. Closing Wholecount clears it.` An arrow label `only when you press Download`. Box three `The files you download`, `Written to the folder you pick. The receipt lists each one and where it went.`
- A `Saved progress` paragraph with a real switch (`QCheckBox` styled as a switch, 36px target) labeled `Save my progress on this computer`. Text `Saved progress holds your decisions and set-up, never rows, and is encrypted for your Windows account. It is deleted after 7 days.` Turning it off asks `Turn off saved progress? What is saved now is deleted, and nothing new is saved.` and, on yes, calls the store (M09) to delete and stop. The switch state is an app setting stored under `%LOCALAPPDATA%\Wholecount\` (no client data). A line under it says `Saved progress is on.` or `Saved progress is off.` and `Last saved {when}.`
- A `Never` box (bg-surface) with the four lines from SPEC 11.8. `Sent over the internet. Wholecount cannot connect to it.` `Shown to or decided by AI. There is none in Wholecount.` `Written to a log. Neither audit log holds a name, address, date or ID from your files.` `Kept after you close, unless you saved progress.`
- Extra paragraphs. `YourDataDrawer` and `DataLine` take `FrameView.data_notes`, a tuple of copy IDs, and draw each one after the Saved progress paragraph (drawer) or at the end of the Writes part of the stage it names (line). The tuple is empty unless M13 puts something in it, which it does only while the saved crosswalk is on. Nothing about the crosswalk is written here, so nothing untested can be claimed.
- `SystemCheckDrawer` opens from the footer's system check line. It is the legacy `vCheck` table rebuilt. Columns `CHECK`, `STATUS` (tag), `DETAIL`. Rows come from `session.preflight()` (M05) plus these, each H8-safe. Geosupport found (with release, amber when `release_stale`), address reference file (`{file name}, {n} rows`, or `sample file, practice only`, or `two files in the folder, none used`, or `none`, from M05's `reference_kind` and `reference_rows`, never a row), install secret present (the key file opens, the value is never shown), saved progress store writable, DPAPI round trip, Archivo font loaded, offline guard installed, Windows version. No row claims the firewall rule is present, because the app cannot read it without a subprocess. Below the table, a `Support report` box with `Copy report` (version and configuration only, never client data). The report text is built from the same rows and tested against H8.
- Each drawer closes with Escape, the Close button, and the scrim. `Close` is a text button, not an icon.

### 13. The per-stage data line
- `DataLine(stage_id)` is a bordered white strip under the stage subtitle, 12px, `ink-2`, with three parts laid out in a wrapping row (`Reads`, `Changes`, `Writes`, each label 800 in ink). It sits in `StageHead`, so every stage has it. Registry keys are `dataline.<stage>.reads`, `.changes`, `.writes`.
- When saved progress is on, every Writes part whose base text starts `nothing to disk` ends with `, except your saved decisions, encrypted` (key `dataline.saved_suffix`, SPEC 11.8). That covers stages 01 to 07. It re-renders when the switch changes. The `data_notes` slot of section 12 adds anything else, such as the crosswalk, only when it applies.

| Stage | Reads | Changes | Writes |
| --- | --- | --- | --- |
| sources | the files you add, once | nothing in your files | nothing to disk |
| schema | nothing from your files | only the list of fields | nothing to disk |
| prepare | the tables you included | nothing in your files. Steps add new columns in memory | nothing to disk |
| map | column names and sample values | nothing in your files | nothing to disk |
| programs | the program columns you chose | nothing in your files | nothing to disk |
| run | the tables you included | nothing in your files | nothing to disk until you download |
| review | the rows that need a decision | only what you decide, and it goes to the audit log | nothing to disk |
| summary | the counted rows | nothing | nothing until you save the printable page |
| export | the results | nothing | only the files you choose, in the folder you pick |

- Every one of the 27 parts has a claim ID (`CL-DATALINE-<STAGE>-<PART>`, for example `CL-DATALINE-SOURCES-READS`) and a test (section Tests). The text above is the starting wording and must read in plain words exactly as in SPEC 11.8.

### 14. Progress plumbing
- `jobs/steps.py` holds all nine action step lists of SPEC 11.6.2 as data. Every step is a member of M01's `Step` enum (16 names), so the code base has one list of steps. The short IDs used below map onto it:
  - `read`, `tables`, `tidy`, `check`, `place`, `copies` and `people`
  - `count_balance` (Counting and balancing) and `count` (Counting)
  - `lookup`, `write` and `reapply`
  - `corr_read` (Reading the corrections file) and `corr_check` (Checking signatures and originals)
  - `draw` (Drawing pairs) and `protect` (Protecting the backup)
- The action IDs, with their steps where the name doesn't say:
  - `add_files` (read, tables) and `process` (the seven steps ending in count_balance)
  - `preview` (check, people, count), `look_up` and `download`
  - `resume` (read, reapply) and `corrections` (corr_read, corr_check, reapply)
  - `calibrate` (people, draw) and `backup` (protect)
- Each step has a name copy ID, a unit (`tables`, `rows`, `addresses`, `checks`, `files`, `pairs`), a stage owner and a weight. The corrections steps belong to `review`. The `calibrate` and `backup` steps have no stage owner, so no underline fills. M12 mounts the corrections job, and M13 the calibrate and backup jobs, all from these lists. Weights come from the prototype's measured log (2.1, 1.4, 3.0, 18.6, 0.9, 4.2, 0.3 seconds, which is 30.5 s) and are normalized to sum to 1 inside each action. The new steps have no measured log, so give them equal weights and say so in the report.
- `Job` is a protocol with `action_id`, `steps`, `run(sink) -> result` (runs on the worker, never touches the session or Qt), and `apply(session, result)` (runs on the main thread inside one command, so one Undo takes back the whole job and every derived result updates together). Engine functions are pure, so a cancelled job simply drops its result and the session is exactly as before (SPEC 11.6.1).
- `JobRunner(QObject)` owns one `QThread` at a time. `start(job)` returns False if a job is running. `cancel()` sets the flag that `ProgressSink.cancelled()` reads, and `SessionBridge.cancel_job()` forwards to it. Signals `step_begun(step_id, index, count, total, unit)`, `progressed(snapshot)`, `step_ended(step_id, found: ProgressMessage, seconds)`, `finished(outcome)`, `cancelled()`, `failed(error_id)`. The worker is a `QObject` moved to the thread. No client value crosses the signal boundary, only ints, step IDs and `ProgressMessage`.
- `QtProgressSink` implements the engine's `ProgressSink`. `advance` stores the latest state under a lock and posts a snapshot when 100 ms have passed since the last post. A runner timer (250 ms, on the GUI thread) re-posts the latest snapshot if nothing was posted in that time, so the elapsed time and the screen reader stay current while a long step is quiet. `cancelled()` reads a flag set by the `Cancel` link. The clock is injected (`time.monotonic` by default) so tests can fake it.
- `ProgressMessage(message_id, params)` is M01's frozen type, used as it is. `params` is a dict whose values may be only `int` (not `bool`), `SourceRef(letter, file_name)` and `StepRef(step)`, and anything else, including `str` or a `params` that isn't a dict, raises `TypeError`. `message_id` must exist in the registry. Rendering goes through M01's `render(message)`, which formats counts with thousands separators. The UI draws a `SourceRef` as the mark and the escaped file name. The message shows in the ticker, the `StepList` and the log, and nowhere else.
- `ProgressModel` (GUI side) never lets a step's count or fraction go down and never lets a total shrink below the count. `overall_fraction()` and `stage_fraction(stage_id)` are monotonic. An empty step (total 0) goes straight to full when it ends.
- Failure. A job that raises shows `Something went wrong in {step name}. Nothing was changed.` and an error code `E-` plus six hex characters of a hash of the exception type, file and line, made by the pure function `error_code(exc) -> str` in `ui/jobs/runner.py` (M12 and M14 reuse it). The exception's message text is never shown or logged, because libraries put cell values in them (H8). The log line holds the type name, the stack frames' file, function and line, and the code.
- Accessibility. `a11y.announce(text)` updates a visually hidden live-region label (`accessibleName`) and sends a `QAccessibleEvent` name-changed event. It is called when a step begins and when a job ends or fails, never on every count.

### 15. Help buttons
`HelpButton(help_id)` is a 36px quiet button with the visible text `?` and accessible name `Help: {title}`. It opens a small popover with `help.<id>.title`, `.purpose` and `.how`. M10 builds the widget, the popover and the registry convention (`help.stage.<stage>` and `help.el.<element>`). Each stage milestone adds the entries for what it builds, taken from `legacy/ui/help.json` and rewritten to be true. M15 generates the guide from the same keys. Help stays live during a run.

### 16. Saved progress card (closes A-19)
`SavedProgressCard(entry)` shows `Saved {when}`, `stopped at {plain stage name}`, `{n} files` and `{k} decisions`. The stage name comes from `STAGES` using the stage ID stored in the saved entry (M09 stores the ID, not a number). It never shows `in progress`. M11 mounts it on Add your files with the Resume action.

### 17. `tools/screens.py` and `make screens`
- Renders offscreen to `build/screens/{NN}-{stage}-{width}.png` at 1440 by 980 and 1280 by 900 with `window.grab()`. `tools/screen_fixtures.py` builds a deterministic `FrameView` from the board numbers (7,412 rows, 6,084 counted, 1,232 not counted yet, 96 aside, 5,940 to 5,954 and 7,106, 14 pairs, locations 5,802 high, 198 low and 84 not mapped, which add up to 6,084).
- M10 renders these frames. Idle before a run for each stage at both widths. Running (ticker, dropdown open on Placing addresses) at both widths. After a run with Medium confidence, log open. Low confidence with the tick missing. Stale. A practice run (the PRACTICE tag). Held Undo and a held button during a run. The Details drawer at 1280. The Your data drawer at 1440. The system check drawer. Commit the 1440 idle frame of stage 07, the two running frames, the Low frame, the practice frame and the three drawers to `docs/milestones/screens/M10/`.
- The tool must be deterministic. Fixed clock, no animation, no network, fonts only from the bundle.
- `python -m tools.screens --demo-run [--practice]` opens the real window with the fixture view and a fake job that runs the seven process steps over about 30 seconds (cancel works, nothing is read or written). Joe uses it in the Windows checks. It lives under `tools/`, so it never ships.

### 18. Copy registry entries (starting text, plain words)
Use M00's format. Every user-facing string in this milestone is in the registry. The claim column is the claim ID that needs a test.

| ID | Starting text | Claim |
| --- | --- | --- |
| `top.offline` | Offline | `CL-OFFLINE-01` |
| `top.offline.narrow` | Offline, nothing leaves this computer | `CL-OFFLINE-01` |
| `top.saved.just_now` | progress saved just now | `CL-SAVED-TIME-01` |
| `top.saved.off` | saved progress is off | `CL-SAVED-OFF-01` |
| `strip.undo.kicker` / `.empty` / `.caption` | UNDO / Nothing to undo / takes back one change | `CL-UNDO-ONE-01` |
| `strip.cap.stale` | out of date | `CL-STALE-CAPTION-01` |
| `top.practice` / `ledger.batch.practice` | PRACTICE / Practice run. Example data, not for reporting. | `CL-PRACTICE-01` |
| `ledger.batch.empty` | No files yet. Add your files to begin. | |
| `ledger.standing.before` | Not processed yet. Nothing has been cleaned, checked or placed. | |
| `ledger.standing.sum` | {counted} + {not_counted_yet} + {aside} = {received}. The three add up to the rows received. | `CL-BALANCE-01` |
| `ledger.loc.sum` | {high} + {low} + {not_mapped} = {counted}. The three add up to the rows counted. | `CL-BALANCE-LOC-01` |
| `ledger.counts.before` | Unique clients, and unique clients by program. Both fill in when the run finishes. | |
| `ledger.counts.range` | unique clients, a range to {hi} until {pairs} pairs are decided | `CL-RANGE-01` |
| `ledger.counts.final` | unique clients, final | `CL-FINAL-01` |
| `ledger.counts.settled` | Settled for the rows counted so far. {n} rows aren't counted yet. | `CL-FINAL-01` |
| `ledger.counts.stale` | Out of date. Process again. | `CL-STALE-COUNTS-01` |
| `ledger.conf.before` | Worked out from the checks once the run finishes. It says why, in one line. | |
| `ledger.loc.before` | Addresses are not placed yet. | |
| `ledger.loc.weak` | A weak match is never labeled fully verified. | `CL-LOC-VERIFIED-01` |
| `ledger.foot.trust` | Nothing leaves this computer. Client data is written only to the files you download. | `CL-TRUST-OFFLINE-01`, `CL-TRUST-DISK-01` |
| `ledger.foot.trust.saved` | Your decisions are saved, encrypted, never the data. | `CL-TRUST-SAVED-01` |
| `ledger.foot.reviewer` | Reviewer: {name} / Reviewer: not asked yet | |
| `ledger.foot.check.ok` / `.warn` | This computer is ready for real data / Addresses will not be placed on this computer | `CL-CHECK-READY-01` |
| `hold.run` | Held until the run finishes. A change now would not apply to this run. | `CL-HOLD-RUN-01` |
| `ticker.after.disk` | nothing written to disk | `CL-TICKER-DISK-01` |
| `close.confirm` / `start.confirm` | see section 11 | `CL-CLOSE-CLEARS-01`, `CL-START-DELETES-01` |
| `data.never.log` | Written to a log. Neither audit log holds a name, address, date or ID from your files. | `CL-AUDIT-NOCELLS-01` |

The data line texts in section 13 and the caption forms in section 6 are registry entries too.

### Notes from the spec review (SPEC 1.1, section 11.3)

- The ledger footer has a Settings link from this milestone on. It opens `SettingsDrawer`, built like `YourDataDrawer`, with three sections:
  - the saved-progress switch, the same control as the one in the Your data drawer, bound to one setting
  - the reviewer name, with the Windows login as the default
  - the system check table

  M13 adds the secret backup, the saved crosswalk and Measure matching as further sections, and adds no link. Settings are stored in `%LOCALAPPDATA%\Wholecount\prefs.json` (SPEC H9).
- Add `test_settings_drawer.py`. The link opens the drawer, the three sections draw, toggling saved progress updates the footer trust sentence, and prefs.json holds no client value.

## Tests to write

All UI tests use `QT_QPA_PLATFORM=offscreen` and `pytest-qt`. Put them in `tests/ui/` unless noted. Name each audit test after its ID in `tests/audit/` and record it in `tests/audit/INDEX.md`.

- **Theme.** Token colors match the style guide file. Every color in `build_qss()` output is a token value. No `border-radius` above 0, no shadows, no gradients, no red hue. Every interactive class has `:focus`. `Archivo` is in `QFontDatabase.families()` after `apply_theme`, with styles for weights 400, 600 and 800. A static test finds no `fonts.googleapis` or `http` literal in `wholecount/ui`.
- **Contrast.** `theme.TEXT_PAIRS` lists every text and background pair used. A test computes the ratio for each and requires 4.5, or 3.0 for text at 24px and above.
- **Layout widths.** `tests/ui/test_layout_widths.py`, parametrized over 1280, 1366, 1440 and 1920 and over all nine stages, each with a long caption set and a maximal `FrameView` (five-digit counts, a 40 character file name). Assert no horizontal scrollbar is visible on the stage area, `window.minimumSizeHint().width() <= width`, every visible child's right edge is inside the window, the strip has no scroll area, and the strip's items show their name fully (label size hint height fits). At 1280 the ledger column is hidden, the band is 44px and the top bar shows Close. At 1366 the column is 280px and the band is hidden. Crossing the breakpoint in both directions keeps the open drawer and the scroll offset.
- **Strip.** Four states and stale for each of the nine stages, caption text for every row of the section 6 table including the empty cases, tooltip equals the full caption, accessible names. Undo label equals the top command's `label`, and the strip shows `Nothing to undo` when the stack is empty. Clicking Undo calls the bridge once.
- **Ledger.** Every section's before-run sentence. Counts show ranges and `final` only when `is_final`, and a fixture with pairs closed but rows not counted yet shows the settled sentence and not `final`. Where they stand and Locations print the two equations from `FrameView.balance_lines` and no widget builds an equation (A-22). A `FrameView` whose balance fails shows the error and no counts. A stale `FrameView` never shows a number in the counts. Each Locations breakdown row appears only when above zero, and a fixture with 6,084 counted and 84 not mapped still shows 6,084 counted in Where they stand (location problems never change the count). The three stage sections render from a `FrameView`.
- **Held states.** A held button has `kind="held"`, its caption is visible, its click does not fire the bridge, and it is focusable and described. `RunHold` holds every registered control during a job, leaves navigation, Show data, help and the Your data link live, and restores each control's earlier hold. The static scan test from section 10.
- **Progress.** With a fake engine job and a fake clock. The bar never moves backward over a shuffled sequence of `advance` calls. 1,000 `advance` calls in 50 ms produce at most two posts. Calls 20 ms apart produce a post about every 100 ms and no gap over 250 ms. A quiet step still produces heartbeats. `ProgressMessage("x", {"who": "Jane Doe"})` raises `TypeError`, and so do a tuple for `params`, and `True` or a `float` as a value. No rendered message, log line or error text contains any value from the test data, including when the job raises `ValueError("Jane Doe, 209 Joralemon St")` (H8). Cancel mid-step leaves a deep hash of the session unchanged and shows `Run cancelled. Nothing changed.` One Undo after a finished job takes back the whole job. Only one `QThread` is ever alive. The announce spy fires once per step and not per count.
- **Confidence.** The block for High, Medium and Low from `FrameView`, with ink and amber colors. Changing a threshold in a temporary `confidence.toml` changes the measure text. The third measure reads `not available` for a no-geocoder fixture, and its reason is the engine's. The popover adds the calibration line only when `calibration` is set (a fake value). The Low tick calls the bridge and is unchecked after the level is recomputed. No `%` in the headline. No green anywhere in the block.
- **Your data and system check.** The three boxes and four Never lines in order. The switch calls the store and shows the confirmation. A `data_notes` entry draws in the drawer and at the end of the stage's Writes part, and an empty tuple draws nothing. The reference row shows a file name and row count for a real fixture, the sample wording for a sample, and no row value ever. A stale release is amber. The support report text contains no value from the test data.
- **Footer and PRACTICE.** `Reviewer: not asked yet` before a name is set, and `Change` fires `SetReviewer` once with the typed name and shows M08's refusal for an empty one. The PRACTICE tag and the ledger line show exactly when `FrameView.practice` is true, on all nine stages, and never for a real batch (`CL-PRACTICE-01`).
- **Data line claims.** `tests/copy/test_dataline_claims.py` has one test per part, 27 in all, each decorated with the claim ID. They drive the session (no screens needed) with the fake backend. Examples. Adding files leaves every source file's bytes unchanged and writes nothing to disk (a write spy on `open`, `os.replace` and `Path.write_*`, with saved progress off). With saved progress on, the only writes are under the temp sessions folder and the written bytes contain no cell value or file name. The Process claim `nothing to disk until you download` is the same spy across a full run. The Fix problems claim `only what you decide, and it goes to the audit log` checks the audit has an entry for each decision and the rows not decided are unchanged. The Results claim checks `Changes nothing` by comparing `Session` state before and after building the stage. The Download claim checks only the chosen files appear in the picked folder.
- **Other claims.** One test each for `CL-OFFLINE-01`, `CL-TRUST-OFFLINE-01`, `CL-TRUST-DISK-01` and `CL-TRUST-SAVED-01`, `CL-BALANCE-01`, `CL-BALANCE-LOC-01`, `CL-RANGE-01`, `CL-FINAL-01`, `CL-STALE-COUNTS-01`, `CL-HOLD-RUN-01`, `CL-UNDO-ONE-01`, `CL-LOC-VERIFIED-01`, `CL-AUDIT-NOCELLS-01`, `CL-CLOSE-CLEARS-01`, `CL-START-DELETES-01`, `CL-TICKER-DISK-01` and `CL-SAVED-TIME-01`. Each test proves the behavior, not the text. The disk claim drives a full session under a write spy. The only paths written are the download folder, the sessions and set-ups folders, the key file and the switches file, and no written byte holds a cell value. The saved claim runs with saved progress on and finds decisions and no values in the saved bytes. The sentence appears only while saved progress is on.
- **A-16** (`test_A16_no_auto_close.py`). Advance a fake clock by 10 minutes with the event loop running and the window stays open. A static scan finds no `QTimer` or thread that calls `close`, `quit` or `exit`, no heartbeat and no idle constant. Closing from the button and from the title bar run the same code path, and the confirmation names what is lost and what stays (claim `CL-CLOSE-CLEARS-01`).
- **A-19** (`test_A19_saved_card_stage.py`). For each of the nine stage IDs, the card's text contains that stage's plain name from `STAGES`, never `in progress`, and the first stage and the last stage are not shifted.
- **A-21** (`test_A21_stage_header.py`). For each stage, normal and empty, the kicker is `STAGE {n} OF 09 · {TECHNICAL}` with the right number. A static scan finds no `of 0` or `of 7` or `of 9` literal outside `stages.py` and the copy file, and no stage plain name literal outside the copy registry.
- **A-23** (`test_A23_trust_and_close_visible.py`). At 1280, 1366, 1440 and 1920 with no hover and no focus, the Close Wholecount button is visible and inside the window, and the trust sentence is visible in the ledger footer (wide) or in the top bar (narrow). The test does not call `enterEvent` or any hover helper.
- **Accessibility.** Every visible `QAbstractButton`, `QComboBox` and `QLineEdit` is 36px or taller. Every button with no text has an accessible name. Tab visits every interactive widget in each placeholder stage, in reading order, and `focusPolicy` is never `NoFocus` on one. The drawers trap Tab and return focus on close.
- **Parity ledger seed.** Create `tests/ui/test_feature_ledger.py` with the table form (`FEATURES = [(feature, milestone, screen, widget)]`) and add every frame feature from the decisions doc ledger (undo, close, start over, saved progress line, system check, the trust sentence, help buttons, the band and Details). M11 and M12 add the rest. A feature with no widget fails.

## Done when

- [ ] Everything in What to build exists and the frame shows all nine placeholder stages.
- [ ] Every test above is written, was seen to fail first, and passes.
- [ ] `make test`, `make offline` and `make copy` are green, with counts written in the report.
- [ ] `make screens` runs. PNGs are committed under `docs/milestones/screens/M10/`.
- [ ] The report lists each difference from the boards and the prototype, each conservative reading, and the additions to the spec (top bar wording under 1360) and the missing confidence chip. Step weights for the new steps are equal, and the report says so.
- [ ] `docs/milestones/M10-REPORT.md` is written, the branch is pushed, a pull request is open, and work has stopped.

## Windows checks for Joe

Run from source. In PowerShell, `cd` to the repo, then `py -3.12 -m venv .venv`, `.venv\Scripts\activate`, `pip install --require-hashes --no-deps -r requirements-dev.lock`, then `python -m wholecount`.

1. The window opens in under 3 seconds with Archivo text, not Segoe UI. Compare a heading with the board PNG. Letters should look the same width.
2. The top bar is dark with a blue square, `WHOLECOUNT`, and a status line at the right. Maximize the window. Close Wholecount is in the ledger footer at the bottom left.
3. Drag the window narrower than 1360 pixels. The left column turns into a thin band under the strip, Close Wholecount appears in the top bar, and nothing scrolls sideways. Use the Details link and confirm the full column slides over from the left and Escape closes it.
4. Click each of the nine stages. Each shows its header (`STAGE 03 OF 09 · PREPARE`), a Reads, Changes, Writes line and a placeholder. The current stage has a blue underline and a pale blue fill.
5. Click `What happens to your data`. Check the three boxes and the Never list read in plain words. Turn Saved progress off, confirm, and turn it on again.
6. Click the system check line in the ledger footer. The table says whether Geosupport is found. If Geosupport is installed it should show its release.
7. Use the developer fixture (`python -m tools.screens --demo-run`, or add `--practice` to see the PRACTICE tag on every stage) to watch a simulated run. The ticker appears under the strip, the stage underlines fill as steps run, and `All steps` opens a list that covers the content without moving it. Try Cancel and confirm the numbers return to how they were. During the run, click a held button. Nothing happens, and the caption under it says what releases it.
8. Leave the window open for 5 minutes. It must stay open.
9. Press Tab repeatedly and confirm a visible blue outline moves through every control, including the Details link and Undo.

## Out of scope

- The real stage bodies (M11 and M12). Placeholders only.
- The run panel on Process, the pre-run summary, and the Process confidence callout (M12). Only the shared `StepList` and `ConfidenceBlock` are built here.
- The Download hold that reads the Low tick (M12). The widget and the command hook are here.
- The secret backup, saved crosswalk and Measure matching sections of the Settings drawer (M13), the saved crosswalk and its data-line text (M13, through `data_notes`), and the calibration numbers (M13, through `confidence.calibration`).
- Any engine rule. If a number the frame needs is missing from the session, add it to `FrameView` and ask M08's `Session` for it. Do not compute rules in the UI.
- The user guide and generated help text (M15). The installer, signing and the bundle (M14). The font files must still be found through a single `resource_path()` helper that M14 can point at the bundle.
