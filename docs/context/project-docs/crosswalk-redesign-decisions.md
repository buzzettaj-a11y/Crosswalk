# Crosswalk redesign, decisions so far

Last updated 2026-09-29, against build 11. Two artifacts hold the work: the design canvas "Crosswalk workflow redesign" (artboards) and the "Crosswalk style guide" design system (tokens, color rule, components). The style guide is the source of truth for the look. When the look changes, the style guide changes in the same pass, and this doc records the decision.

## Direction

Cockpit (option C). Keep every stage. Stage strip pinned across the top. A permanent ledger down the left holding rows in, where they stand, the two counts, and location confidence. No hover menu.

## Settled

- The product is Crosswalk, in every artboard, the canvas title, the style guide, this doc and the codebase. The codebase rename was done on 2026-09-29: file names, the server module, the launchers, the tests, the documents and the interface all say Crosswalk. Spelling is American throughout.
- Nine stages, matching build 11: Add your files, Set up your columns, Tidy up, Match your columns, Programs, Process, Fix problems, Results, Download. A stage with nothing to decide is marked as such, never hidden or merged.
- One vocabulary. Plain names, technical name in small caps beside it. The Guided and Advanced toggle goes.
- Programs is its own stage between Match your columns and Process, as build 11 has it, with three numbered sections: which column holds the program in each file, which names are the same program, and a preview of the counts. On top of the build, Continue to Process is held until every group the tool put together has been confirmed or split, and every confirmation, split and rename goes to the audit log with the names involved. The earlier plan to make this step 2 of Match your columns is dropped.
- Below 1360px wide the ledger becomes a one-line band under the stage strip. Nothing scrolls sideways at 1280 or above. With nine stages the two longest names may wrap to two lines in the strip under 1360; the strip grows, it never scrolls.
- Tidy up: Add a step sits at the top as a builder (pick the rule, then the source and its options). Five rules: calculate the ZIP from the address, clean columns, split by a delimiter, split a jammed address, split a jammed name. The steps list groups by rule, by source, or by who added it, with a toggle. A source can appear under several rules. Rows inside a group keep the order they run in. A step that changed nothing is an amber row. Add a step is always visible, and build 11 made it so too.
- Color carries meaning or is not used. Blue = needs you (actions, links, where you are, open rows). Green = a person decided (confirmed, added by you, approved). Amber = looks wrong (the tool read the data and it does not fit). Gray = settled and out of the way. A row that passed every check is ink, not green. No red. Sources are identified by a letter mark, never a color.
- Square, flat, one pixel. Zero radius everywhere. A 3px rule on the top or bottom marks state, never on the left.

## What build 11 added, and where it lives in the redesign

- Programs as a stage. Drawn as 05 Programs. The column per source is set on the stage itself with sample names and a codes-not-names warning, the grouping uses the build's pick-up-and-click with count on its own and put it back, and the preview card shows both goals and a per-program table, marked out of date after any change. The ledger shows the preview's two counts as provisional while the stage is open.
- Calculated column, the ZIP the address points to. Drawn as the first rule card on Tidy up with its form (street, optional city or borough, optional existing ZIP, only-blanks or every row, new column name), and as a step row reporting rows that got a ZIP, kept theirs, or could not be placed. Match your columns notes that a calculated column is chosen for ZIP by itself.
- Grids keep their scroll position and page across a redraw. A rule in the style guide, no drawing needed.
- Unit designators in every shape people type. Engine only. No design change.

## Changed inside the frame

- The system check is a status line at the foot of the ledger, not a stage.
- The fast path is the first thing on Add your files, called Do the whole thing now.
- Fix problems lost its five-number strip. The ledger carries those numbers.
- Within-file duplicates and the cross-file note are entries in the same ranked list as every other cause.
- Results lost its right sidebar for the same reason.
- Undo lives in the top strip and names what it takes back.

## Feature ledger

Nothing was removed on purpose. Status of each existing feature against the drawn screens:

Kept and drawn: fast path with its blockers and warnings, example data, drop and browse, corrections file recognition, include and exclude tables, header row warning, show data, tidy-up steps with origin, remove and restore, add a step for all five rule types with every option (columns, case, junk, edge punctuation, delimiter, custom delimiter, max splits, new names, street, city, existing ZIP, mode, calculated column name), per-table column matching with the column check and one-click fix, blocked run band, confirm and next table, fill a field for this source only, unmapped columns stay out of exports, program column per source with samples and warning, program name groups with rename, pick up, move, count on its own, put back and start again, the preview of the counts with refresh and out-of-date state, grouped decisions with per-group actions, accept all as they are, send to row by row, preview, fill from street, the matching diagnosis with one-click fix, cross-file note, finish review, the queue with status filter, problem and source facets, search, page size, select page and all matching, bulk approve, reject, remove, pending, keep one per program, set a field on all selected, the record panel with meaning, original row, unmatched columns, shared identifier context, suggestion, approve, reject, set aside, open the source file, the two counts with range, open pairs, program bars, person table, print page, undo, close, start over, saved progress line.

Moved, not drawn yet: the system check table (opens from the ledger line), the header row picker (opens from show data), the fill lookup list (opens from look up all), the side by side duplicate compare (opens from compare), the proposals screen for open pairs (opens from decide them now), keep this row for possible duplicates, per-row fill, resume notice, sorting on tables.

Stages not drawn yet: Set up your columns, Process, Download.

Needs a home: two of the three Advanced-only controls still do, editing the schema and choosing export columns. Adding a tidy-up step now has one.

## Color pass, still to apply

The color rule is drawn on the Tidy up and Programs boards and in the style guide. The earlier cockpit boards still use blue for everything. Once the rule is approved they get: green confirmed and decided tags on Fix problems, amber on the column check callouts in Match your columns and on the header row tag in Add your files, and the ledger's Tidy up and Matching lines in the matching hues.

## Open

- The Streamlit app. If it stays at feature parity, every screen is built twice.
- The stage headers in the current build read "Stage 04 of 07" while the rail lists eight. Fix in the build whatever else happens.
