# Crosswalk, project context

Written 2026-10-30 from the Crosswalk project's chats, docs and artifacts. Where this file and a source doc disagree, the source doc wins. Each section names where its facts came from.

## In short

- Crosswalk is an offline desktop tool. It merges client lists exported from many separate systems into one clean master list and produces two numbers: unique clients overall (Goal 1) and unique clients per program (Goal 2).
- It's a deterministic rules engine with a person deciding anything the rules can't settle. There's no model, no fuzzy merge and no network call in the processing path.
- The engine (`app.py` and its modules) is validated and stays as is. The current job is a new front end, called the cockpit, built to the boards and style guide in this package.
- The source code isn't in this package. See "The code" in `START_HERE.md`.

## Who it's for

Joe Buzzetta built it as a consultant. The client contact is Stephanie at St. Nicks Alliance, a New York City nonprofit whose client records live in roughly 12 to 20 systems (ETO, property management, DYCD exports, partner spreadsheets). The operator is a data or program staff member, not an engineer, who runs a batch a few times a year.

The shipped product is generic. On 2026-09-08 every St. Nicks and ETO label was taken out of the code, the UI and the README, and tests guard against them coming back. Two exceptions were kept on purpose. The auto-mapper still recognizes a column named `ETO_Client_ID` and maps it to `Client_ID` (a test fails if that's removed), and the geocoder is New York City only.

Stephanie's two goals, from her email:

- **Goal 1, unique clients across all datasets.** Count each person once, whatever systems they appear in.
- **Goal 2, unique clients by program.** Count a person once per program. In her example, Joe Smith in Workforce and Resident Services in ETO, plus Property Management externally, counts 1 for Goal 1 and 3 for Goal 2.

Sources: [Main Development Thread](https://claude.ai/chat/8ccd2537-04bb-4770-b62e-6ad009582ce9), [Generalizing application version](https://claude.ai/chat/8d8e927b-c041-4d96-a8b0-9274578870cb), `docs/crosswalk-described-for-an-ai.md`.

## Rules that can't break

These come from the "Hard rules" table in `docs/crosswalk-described-for-an-ai.md` and the rules in the build's own `CLAUDE.md`. Any rebuild has to keep every one of them.

- **Offline.** No network call in the engine or the interface, including fonts. Geocoding runs locally through NYC Geosupport Desktop Edition or a local reference file.
- **Deterministic.** Same input and settings give the same output. The only randomness is the privacy jitter, and it's seeded (default seed 1337).
- **Lossless.** Clean rows plus review rows plus set-aside rows always equal input rows. The server asserts it (`_reconciliation`). Don't weaken that assertion. Rows are set aside, never deleted.
- **Nothing merged on a guess.** Records collapse only on the same identifier with identical data in one system, or when name, date of birth and address all agree. Anything weaker goes to a person with its evidence. Fuzzy matching suggests and never merges.
- **Originals preserved.** Tidy-up steps add columns and never overwrite. Uploaded files are kept as bytes so a reviewer can open the original.
- **PII-safe audit.** The audit trail and the printable summary carry identifiers, row numbers and column names only. Saved set-ups and saved progress hold decisions, never rows.
- **No per-value editing.** A reviewer can't type a new value into a cell. Fixes come from the row's own address, a corrections file, or the source system.
- **Nothing written until asked.** Client data reaches disk only in files the operator downloads.
- **Feature parity.** The new front end has to offer everything the Streamlit screens did. `tests/test_parity.py` checks this, and removing a control must make it fail.
- **Wording.** Plain words, American spelling, numbers with thousands separators, no emoji, no exclamation marks, and no em dashes anywhere in the product or its documents.

## How the code fits together

From `docs/crosswalk-described-for-an-ai.md` ("Architecture and runtime") and the build's `CLAUDE.md`.

- `app.py` is the engine and the original Streamlit screens. Every number comes from here. Change it only when a test says it's wrong.
- `crosswalk_server.py` wraps the engine in FastAPI, bound to 127.0.0.1 only, refusing foreign Host headers, with no CORS policy. One dict `S` holds all working state. `GET /api/ui?screen=...` returns the shared chrome plus that screen's data. Every change is a POST.
- `ui/app.js` is the interface. One page, no framework, one render function per stage, one document-level click handler dispatching on `data-*` attributes. `ui/help.json` feeds the ? buttons, the user guide and the cheat sheets.
- `desktop.py` is the entry point since 2026-09-21. It runs the server in-process and draws the UI in a native window through pywebview (WebView2 on Windows, WebKit on a Mac). `--browser` opens a tab instead. `launch.py` is the browser launcher.
- `streamlit_stub.py` stands in for the two streamlit cache decorators the engine imports, so the packaged app doesn't ship streamlit.
- `Crosswalk.spec` with `build.bat`, `build.command` and `build.sh` make the standalone app through PyInstaller. Each only builds on its own platform.
- Launchers are `Crosswalk.vbs`, `Crosswalk.command`, `Crosswalk.sh` and `run_crosswalk.bat`. `run.bat` and `run.sh` still start the old Streamlit screens.
- Docs are generated by `tools/make_docs.py` (`docs/TECHNICAL.md`, `docs/USER_GUIDE.md`, cheat sheets). `tests/test_docs.py` fails when they drift from the code.

### Tests

Each test is a plain script, and exit code 0 means pass. Run them all before and after any change to the engine, server, interface or launchers. The build brief counts nine test files. Some builds also carry `test_desktop.py` and `test_docs.py`.

```
python tests/test_crosswalk_api.py
python tests/test_smoke.py
python tests/test_parity.py
python tests/test_identity.py
python tests/test_proof.py
python tests/test_table_detect.py
python tests/test_corrections.py
python tests/test_preflight.py
python tests/test_layout.py      (needs Playwright, checks 1280, 1366, 1440 and 1920 wide)
python tests/test_desktop.py     (opens the real window; needs a display)
python tests/test_docs.py
```

`tests/test_crosswalk_api.py` inspects the launchers and `START HERE.txt` line by line. Read the failing check before changing a file it names. `tests/test_proof.py` runs `proof/Proof_Workbook.xlsx`, which is the definition of correct for the engine.

## How it got here

| When | What happened |
| --- | --- |
| June or early July 2026 | First build. An offline Streamlit app that merged messy exports from five systems into a "Master ETO Schema," geocoded against a local NYC address file, and jittered points 150 to 250 feet for privacy |
| 2026-07-30 | Redesign work started from a Claude Design project |
| July to September | Wizard front end (FastAPI plus HTML) built beside the Streamlit screens, then Results and Download as their own stages, the two goals wired in, and Programs as its own stage for grouping program spellings |
| 2026-09-08 | Generalized. St. Nicks and ETO labels removed from code, UI and README, with guard tests |
| 2026-09-21 | Made a standalone app. pywebview window, `streamlit_stub.py`, PyInstaller spec and build scripts. VS Code setup with a `CLAUDE.md` for Claude Code |
| 2026-09-22 | Style guide v1 to v1.2. Nine stages, color carries meaning, the cockpit frame |
| 2026-09-28 | Security review, written up as the fix plan (24 issues). The AI description, the Excel runbook and the Excel tutorial written |
| 2026-09-29 | Build brief and decisions doc written. Build 12 (the cockpit front end) built, then sped up and matched closer to the boards. Everything renamed to Crosswalk with American spelling |
| 2026-09-30 | Training video (about 10 minutes, with captions and script) |

Names over time were ETO Master Merge, then Crosswalker for the wizard build, then Crosswalk everywhere as of 2026-09-29. Old chats and file names use the older names.

A separate chat, [Lossless AI data transformation feasibility](https://claude.ai/chat/3994c727-7d76-4ce1-b299-2589e47e2c53), built an optional AI rule assistant (`ai_assist.py`, switched on by `CROSSWALK_AI_ONLINE=1`), an installation white paper, a 19,000-row sample data set, and an "ink vault" HTML prototype. That prototype isn't the design direction. The cockpit boards and the style guide are.

## Where it stands

### Build 12, the cockpit front end

From the chat [Redesigning Crosswalker application](https://claude.ai/chat/cce707ef-99d8-4574-bdaf-79a0f6f303f3).

- Built to the brief and boards. All nine test files passed, with 705 API checks, 50 parity checks and 175 layout checks at seven widths.
- Sample data counts were the same through the fast path and stage by stage. 256 unique clients (a range of 244 to 256 with 14 pairs open) and 52 by program. With every pair decided, 244 and 51.
- The first version was about twice as slow as build 11. The fix caches each table's tidy-up result, reuses the strip's numbers until their inputs change, and stops screens waiting on identity matching (Results still waits). Twenty clicks on about 7,000 rows went from 20.1 seconds in build 11 to 8.6 seconds.
- Archivo now ships in `ui/fonts/`. Before that the app showed the system font, which is the main reason it didn't look like the boards.
- Three screens were brought back in line with their boards. Add your files lost a second Continue button. Match your columns uses the board's plain field names and rules. Results shows the two goals as one split panel.

Behavior changes in build 12 to check:

- **Finish review waits for the duplicate groups**, because board 07 counts them as a cause. Build 11 let you finish without deciding them.
- **Keep this row** shows only for possible duplicates and identical copies, not for records that just share an ID.
- **The counts check in the brief couldn't be done as written.** `test_identity.py` builds its own records and has no numbers for the sample data, so the counts were checked against the download files instead.

Known issues left open:

- `sessions_store.py` names the stages from a list older than Programs. It was on the do-not-touch list.
- Same-person decisions on Results don't go to the audit log. That was already true in build 11.

### What the docs describe versus what's next

`docs/crosswalk-described-for-an-ai.md` was written against build 11. It still describes a stage 0 "Check this computer" and a Guided and Advanced mode switch. The build brief and decisions doc replace both. The system check becomes a status line at the foot of the ledger, and there's one vocabulary with no mode switch. Everything it says about the engine still holds.

### The fix plan

`docs/crosswalk-fix-plan.md` was written from the docs without the source in front of it, so steps marked "Check first" need checking against the code. It sorts 24 issues into seven phases. 18 can be fully fixed, 5 can only be reduced, and one (data-sharing approvals) can't be fixed in the tool at all. Before the next real client run it calls for three things.

- Stop logging requests and remove `run.bat`, plus the stopgap security fixes if the native window isn't ready.
- Agree the machine rules with Stephanie.
- Get St. Nicks' approval on the data agreements and the saved crosswalk.

Two items still need a Windows machine to confirm. One is the DPAPI encryption calls and the other is WebView2's 2 MB limit on a page passed in as a string.

## Open decisions for Joe

From the build brief, the decisions doc and the build 12 chat.

- **Streamlit.** The brief recommends keeping `app.py` as the engine and dropping the Streamlit screens as a maintained interface. If they have to stay current, every screen gets built twice.
- **Stage 02's plain name.** "Set up your columns" wraps to two lines in the strip at 1280 wide. A shorter name keeps the strip one line tall.
- **Color pass.** The earlier boards still use blue where green or amber belongs. Once the rule is approved they get green decided tags on Fix problems, amber on the column check in Match your columns and on the header row tag in Add your files, and matching hues in the ledger.
- **Undrawn stages.** Set up your columns, Process and Download are specified in words, not drawn.
- **Moved, not drawn yet.** The system check table, header row picker, fill lookup list, side by side duplicate compare, proposals screen for open pairs, keep this row for possible duplicates, per-row fill, resume notice, and sorting on tables.
- **Still need a home.** Editing the schema and choosing export columns.
- **Stage header count.** Build 11's headers read "Stage 04 of 07" while the rail listed eight. Fix it in the rebuild whatever else happens.

## Known limits to state, not hide

From `docs/crosswalk-described-for-an-ai.md`.

- Identity weights and thresholds are reasoned and tested on constructed cases. They haven't been calibrated against a hand-labeled sample of real files.
- The bundled `nyc_address_points.csv` is a small sample. Real geocoding needs Geosupport installed, with `GEOFILES` ending in a backslash on Windows.
- Goal 2 is only as good as the program column matching and grouping. A file with no program column and no per-source default is left out of Goal 2, and the tool says so.
- Address parsing is tuned to New York City. Only NY is a recognized state. Addresses outside the city are flagged, not resolved.

## Links

Chats in the project:

- [Main Development Thread](https://claude.ai/chat/8ccd2537-04bb-4770-b62e-6ad009582ce9)
- [Redesigning Crosswalker application](https://claude.ai/chat/cce707ef-99d8-4574-bdaf-79a0f6f303f3) (build 12)
- [Converting browser app to standalone](https://claude.ai/chat/91ae1060-92ec-42ff-916f-d49ff1a04cef)
- [Product security concerns](https://claude.ai/chat/e77e863b-da7b-4103-a347-caa2830f822e) (the fix plan)
- [Lossless AI data transformation feasibility](https://claude.ai/chat/3994c727-7d76-4ce1-b299-2589e47e2c53)
- [Generalizing application version](https://claude.ai/chat/8d8e927b-c041-4d96-a8b0-9274578870cb)
- [St Nick's app version](https://claude.ai/chat/0a9bb3a9-bdf6-4d81-8e73-2b00d7eca662)
- [Crosswalk redesign project](https://claude.ai/chat/76b97975-4a3f-4d45-bc81-85f0c4c2d608)
- [Training video with screen recording](https://claude.ai/chat/59af27c7-d2a7-48f9-b412-2e342f122e7b)

Artifacts are linked in `START_HERE.md`.
