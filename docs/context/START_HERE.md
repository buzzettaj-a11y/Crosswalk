# Crosswalk project package

Everything from the Crosswalk project on claude.ai, packed for a rebuild in Claude Code. Packed on 2026-10-30.

**In the Wholecount repo, read `SPEC.md` first.** This package is background, and the spec wins wherever they differ. The product is now called Wholecount, stage 02 is now "Your columns," and the old build's source is in `legacy/` at the repo root. Paths below are relative to this folder (`docs/context/`).

This package holds the specs, decisions, design and reference docs.

## Read in this order

1. `PROJECT_CONTEXT.md` in this folder. What Crosswalk is, the rules that can't break, how it got here, where it stands, and what's still open.
2. `project-docs/build-brief.md`. The job for the front end rebuild: what stays, what goes, the frame, the nine stages, acceptance.
3. `project-docs/crosswalk-redesign-decisions.md`. Every design decision so far, plus the feature ledger (what's drawn, what moved, what still needs a home).
4. `design/style-guide/README.md`. The source of truth for the look. Color rule, type, components, wording.
5. `design/board-images/`. One PNG per board, so you can see each screen without the design tool.
6. `docs/crosswalk-described-for-an-ai.md`. The full behavior spec of the engine: schema, stages, parsing, geocoding, duplicates, identity, programs, review, outputs, audit, architecture.
7. `docs/crosswalk-fix-plan.md`. The security and data-handling plan, in seven phases, with a scorecard.

The two Excel docs are reference only. They're useful when you need to check what a rule does by hand.

## What's in here

| Path | What it is | Where it came from |
| --- | --- | --- |
| `PROJECT_CONTEXT.md` | History, hard rules, current state, open decisions | Written for this package from the project's chats and docs |
| `project-docs/build-brief.md` | Build brief for the cockpit front end | Project doc `claude/build-brief.md` |
| `project-docs/crosswalk-redesign-decisions.md` | Redesign decisions and feature ledger | Project doc `claude/crosswalk-redesign-decisions.md` |
| `design/style-guide/README.md` | Style guide v1.2.1, the authority on the look | [Crosswalk style guide](https://claude.ai/artifact/Pp4gkW8gT8TRbBW2fFdEQN) |
| `design/style-guide/tokens.json` | Colors, type styles, spacing, radius, layout sizes | Same |
| `design/style-guide/tokens.css` | The same tokens as CSS custom properties | Generated from `tokens.json` for this package |
| `design/style-guide/components/` | README and preview HTML for Buttons, Callouts, Cover, Ledger, SourceMark, StageStrip, Tags, TwoStepHeader | Same |
| `design/boards/*.dc.html` | The 14 boards from the design canvas, as HTML | [Crosswalk workflow redesign](https://claude.ai/artifact/EKVnK1eqjASbvb877gbQnd) |
| `design/boards/canvas.json` | Board titles, sizes and order on the canvas | Same |
| `design/board-images/*.png` | Each board rendered at its own size | Rendered for this package |
| `docs/crosswalk-described-for-an-ai.md` | Full behavior spec | [Crosswalk, described for an AI](https://claude.ai/artifact/HKvuyHEB6YL6FxcepCwRKG) |
| `docs/crosswalk-fix-plan.md` | Security and data-handling fix plan | [Crosswalk fix plan](https://claude.ai/artifact/AqvQQKwRxxWztmmv2owtpg) |
| `docs/excel-runbook.md` | Doing a full batch by hand in Excel, step P1 to P14 | [Crosswalk by hand: the Excel runbook](https://claude.ai/artifact/RwXuMuNzzyWMyUJxDs4jQV) |
| `docs/excel-runbook-reference.md` | The runbook's Reference tab: named patterns, formulas, lookup tables, nicknames, program words, all copied from the app's code | Same, second tab |
| `docs/doing-what-crosswalk-does-in-excel.md` | Simplified Excel tutorial on fake data | [Doing what Crosswalk does, in Excel](https://claude.ai/artifact/QykTaXpnhxv91ND4SgcpKN) |

## The boards

The build brief names boards by stage (for example `design/boards/01-add-your-files.html`). Those names came from an earlier handoff zip. Here they keep the names the design canvas uses. This table maps them.

| File | Board | Use |
| --- | --- | --- |
| `Main.dc.html` | Today, and where it bites | Diagnosis of build 11. Context only |
| `A_Three_Acts.dc.html` | A, three acts | Direction explored, not chosen |
| `B_Worklist.dc.html` | B, worklist, not wizard | Direction explored, not chosen |
| `C_Cockpit.dc.html` | C, cockpit | **The chosen direction** |
| `D_By_Exception.dc.html` | D, by exception | Direction explored, not chosen |
| `C1_Files.dc.html` | 01 Add your files | Build to this (brief's `01-add-your-files.html`) |
| `C1b_Tidy_By_Rule.dc.html` | 03 Tidy up, grouped by rule | Build to this |
| `C1c_Tidy_By_Source.dc.html` | 03 Tidy up, grouped by source | Build to this |
| `C2_Matching.dc.html` | 04 Match your columns | Build to this |
| `C2b_Program_Names.dc.html` | 05 Programs | Build to this |
| `C3_Fix_Groups.dc.html` | 07 Fix problems, step 1 | Build to this (brief's `07-fix-problems-step-1-causes.html`) |
| `C4_Fix_Queue.dc.html` | 07 Fix problems, step 2 | Build to this |
| `C5_Results.dc.html` | 08 Results | Build to this |
| `C6_Narrow_1280.dc.html` | 1280 wide, ledger as a band | Build to this for widths under 1360 |

Stages 02 Set up your columns, 06 Process and 09 Download aren't drawn. The build brief and the feature ledger specify them in words.

Notes on the boards:

- The boards are plain HTML with inline styles inside `<x-dc>` tags from the design tool. They open in a browser as is. The `support.js` they reference belongs to the design tool and isn't needed to read them.
- They load Archivo from Google Fonts. The PNGs were rendered offline, so they show the system fallback font. The app has to bundle Archivo locally in `ui/fonts/` because it runs with no network (build 12 already did this).
- The earlier boards (01, 04, 07, 08) still use blue where the style guide now says green or amber. The style guide wins. See "Color pass, still to apply" in the decisions doc.

## The code

The source isn't in this package, and nothing in Google Drive matches it. These are the last bundles the project's chats produced, all on 2026-09-29:

- `Crosswalk-build-12.zip`. The cockpit front end built to the brief and boards, with the speed fix and Archivo bundled. From the chat [Redesigning Crosswalker application](https://claude.ai/chat/cce707ef-99d8-4574-bdaf-79a0f6f303f3).
- `Crosswalk.zip` and `Crosswalk_Documentation.zip`. The rename to Crosswalk and the American spelling pass across code and docs. From the [Main Development Thread](https://claude.ai/chat/8ccd2537-04bb-4770-b62e-6ad009582ce9).
- `crosswalk-handoff.zip`. The earlier handoff with `spec/SCREENS.md`, `spec/API.md`, `spec/DECISIONS.md`, `spec/FEATURE_CHECKLIST.md` and the original `design/` folder. The build brief points at those spec files, and they're not in this package.

The chats don't make it certain which of the first two is newest. The right one has the stage strip and ledger in `ui/` and uses `crosswalk_server.py`, not `crosswalker_server.py`. If both exist, diff them before starting.
