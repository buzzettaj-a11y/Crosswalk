# Build brief: Crosswalk, new front end on the existing engine

## The job

Replace the front end of the current app (`current-app/ui/`) with a new one built to the boards in `design/boards/` and the rules in `design/style-guide/`. Keep every capability the current app has. Keep the engine exactly as it is. Adjust the server only to feed the new front end.

The design is called the cockpit. Its idea in one line: the stages are pinned across the top, the numbers never leave the left, and every screen shows only its own work.

## What stays

- The engine and every module around it. Their behavior is validated by `tests/test_proof.py` against `proof/Proof_Workbook.xlsx`, twenty sheets, one per thing the tool does. That is the definition of correct.
- The server, `crosswalk_server.py`, as the API. Its routes are listed in `spec/API.md`. Add to it; do not rewrite it.
- Sessions and saved progress, the seven day clean-up, the heartbeat and the self-closing behavior.
- The launchers (`Crosswalk.vbs`, `Crosswalk.command`, `Crosswalk.sh`, `launch.py`, `run_crosswalk.bat`).
- The sample data, the proof workbook, the tools that generate them, the reference CSV and GeoJSON, and `START HERE.txt`.
- All nine test files. Extend them for anything new; never weaken one.

## What goes

- The hover rail. Replaced by the pinned stage strip.
- Guided and Advanced. One vocabulary. Every control that Advanced used to gate is simply visible on its stage.
- The per-stage stat strips (Process, Fix problems, Results sidebar). The ledger carries those numbers.
- The system check as a stage. It is a status line at the foot of the ledger that opens the full check table.
- The Streamlit interface as a maintained surface. `app.py` stays because it is the engine. The Streamlit screens inside it are not part of this build and do not need to match. This is a recommendation; see Open decisions.

## The frame

Three fixed parts on every stage, then the stage's own content. See `design/boards/01-add-your-files.html` for the pre-run state and `07-fix-problems-step-1-causes.html` for the post-run state.

**Top bar.** 48px, ink, wordmark CROSSWALK, then on the right: offline, geocoder backend, when progress was last saved. Under 1360 wide, Close Crosswalk moves here as a bordered quiet button.

**Stage strip.** Nine items plus Undo, pinned. Each item is three lines: number and technical name, plain name, and a live caption saying what the stage holds right now. Four states: current, done with work, nothing to decide, not yet. The caption is data from the server, never a fixed string. Undo names the decision it takes back. Under 1360, names drop to 11.5px, Undo to 150px, and the two longest names may wrap to a second line. The strip never scrolls.

**Ledger.** A 280px column down the left at 1360 wide and up. This batch (files, tables, rows). Where they stand (a stacked bar and clean, still open, set aside, with the line under it saying the three add up to rows received). The two counts (with the range until open pairs are decided). Locations (high, low, not matched). A footer with the system check line, the trust sentence, Close and Start over. Before a run each section says in one sentence what it does not know yet. Some stages add a section of their own: Tidy up (proposed, added by you, removed, do nothing), Match your columns (tables confirmed, required set, look wrong), Programs (files with a column, names found, groups to confirm, and the preview's counts marked provisional).

Under 1360 the ledger becomes a 44px band under the strip with the same numbers in four groups and a Details link that opens the full column as a drawer. Content takes the full width. Nothing scrolls sideways at 1280 or above; `tests/test_layout.py` checks this and must stay green.

## Rules that cut across every stage

- **Color.** The style guide is the authority; the Tidy up and Programs boards follow it, the earlier boards predate it and still show blue where green or amber belongs. Blue is needs you: primary buttons, links, where you are, open rows, callouts that ask for a decision. Green is a person decided: confirmed, added by you, approved. Amber is looks wrong: a column that does not fit its field, a header row that looks like a title, a source with no program column, a step that changed nothing. Gray is settled and out of the way. A row that passed every check is ink, not green. Inside an amber callout the button is still blue. No red anywhere.
- **Source marks.** A 16px ink square with a white letter, A onward in the order files were added, the same letter for the same source on every stage. Never a color per source.
- **Held controls.** A Continue that cannot go yet is gray with a caption under it saying what releases it. Never a bare disabled button.
- **Two-step header.** Fix problems only: step 1 the causes, step 2 row by row, with live counts in both cells. Programs uses numbered section heads instead.
- **Callouts.** White card, 3px top rule in the hue that says what kind of thing it is, title, one line, and the action on the right.
- **Undo.** One control, in the strip, naming the last change or decision. Review's undo and the set-up undo are both reached from it.
- **Wording.** Plain first. A problem says what it means and what to check. A count says what it counts. Every correction says it goes to the audit log. Numbers with thousands separators. American spelling. No emoji, no exclamation marks.
- **Grids.** Every grid remembers its scroll position and page across a redraw. Opening a different stage starts at the top.
- **Busy.** Every request shows itself. The thin bar at the top with the engine's own phase and progress stays exactly as the current app does it.

## The stages

Full detail per stage is in `spec/SCREENS.md`. In short:

1. Add your files. The fast path is the first thing on the screen, called Do the whole thing now. Then drop or browse, example data, the table list with include ticks, kinds, PII tags, the header row warning, Show data.
2. Set up your columns. The schema table, always editable. No mode switch. Not drawn; specified.
3. Tidy up. Add a step at the top as a builder with five rule cards. The step list grouped by rule, by source, or by who added it. Drawn twice, once per grouping.
4. Match your columns. Per-table matching with the column check and one-click fixes. Continue to Programs.
5. Programs. Three numbered sections: which column per file, which names are one program, preview the counts. Continue is held until every group the tool proposed is confirmed or split.
6. Process. Settings, the run, the result summary. Not drawn; specified.
7. Fix problems. Step 1 the causes, one ranked list including within-file duplicates and the cross-file note. Step 2 the queue with filters, selection, batch actions, and the record panel.
8. Results. The two goals, open pairs, where the people are, each person's programs, the printable page.
9. Download. Format, the seven files, the balance line, choose columns. Not drawn; specified.

## API work

Most of what the new front end needs already exists. `spec/API.md` lists the sixty routes and the additions: per-stage state and caption for the strip, the ledger block, the programs confirmation gate, structured counts on tidy-up steps, and the ledger's provisional counts from a programs preview. Keep `/api/ui` as the single call that returns everything a screen needs; add to its `chrome`.

## The name

Done on 2026-09-29. The product is Crosswalk everywhere: file names, the server module `crosswalk_server.py` and the tests that import it, the launchers, `START HERE.txt`, the window title, the wordmark, the close button and every document. Spelling is American throughout.

## Acceptance

- Every line in `spec/FEATURE_CHECKLIST.md` is ticked with the screen it lives on.
- All nine tests pass, including `test_parity.py` and `test_layout.py` at 1280, 1366, 1440 and 1920.
- The five sample files go through all nine stages by hand, once through the fast path and once stage by stage, and the two counts on Results match `tests/test_identity.py`'s expectations for the sample data.
- Every board in `design/boards/` is matched by the built screen at 1440 wide: same regions, same order, same copy where the copy is fixed, live numbers where the board shows numbers.
- Every string in the build uses the name Crosswalk and American spelling.

## Open decisions for Joe

- Streamlit. This brief recommends keeping `app.py` as the engine and dropping the Streamlit screens as a maintained interface. `test_parity.py` still asserts the new front end offers every Streamlit capability, so nothing is lost silently. If Streamlit must stay current, every screen is built twice.
- Stage 02's plain name. At 1280 wide, Set up your columns wraps to two lines in the strip. A shorter plain name would keep the strip one line tall. Joe's wording; Joe's call.
