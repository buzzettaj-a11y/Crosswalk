# Wholecount specification

Version 1.1, 2026-10-30. Owner: Joe Buzzetta.

Version 1.1 settles the gaps found while drafting the milestones, and it builds in every fix plan item. The fix plan is `docs/context/docs/crosswalk-fix-plan.md`. Version 1.1 makes these changes:
- People are counted whether or not their address can be placed (fix plan 5.1).
- Record keys survive re-exports (fix plan 5.4).
- The privacy offset is per building, and coordinates leave the clean file (fix plan 4.4).
- The audit splits into an internal log and a shareable log (fix plan 4.5).
- The review file is shrunk and signed (fix plan 4.3).
- A saved crosswalk is added (fix plan 5.4).
- Matching calibration is added (fix plan 5.6).
- Reviewers are named, and bulk accepts get extra checks (fix plan 5.7).

Wholecount is the new name for the product called Crosswalk until now. The repo keeps the name `crosswalk` until Joe renames it on GitHub. The product name lives in one constant, `wholecount/brand.py: PRODUCT_NAME`, and every user-facing string reads it from there. Renaming the product later means changing that constant, the package name and the installer file. Nothing else should need to change.

## 0. How to use this document

- **This spec is the source of truth.** When it disagrees with anything else, the spec wins. That includes the old code in `legacy/`, the old docs in `docs/context/` and the design boards.
- **The milestone files in `docs/milestones/` say what to build in what order.** Each one points back to sections of this spec. Build one milestone, then stop and report (see `CLAUDE.md`).
- **The old build is reference, not a base.** `legacy/` holds the old Crosswalk source. Read it to learn what a rule did, then rewrite it to this spec. Don't copy code from it, don't import from it, and don't ship any of it. Where this spec gives a rule, follow the rule even if the old code did something else.
- **The audit says what the old build got wrong.** `docs/audit/AUDIT.md` summarizes 101 findings, and `A-claims.md`, `B-values.md` and `C-counts.md` hold the detail. Each finding has an ID like B-13. This spec cites those IDs where a rule exists because of one. Every High and Medium finding has a regression test in the rewrite (section 13.3).
- **Words like must, never and always are rules.** Should means do it unless a test or a later section gives a reason not to. May means optional.
- **Rule IDs.** Hard rules are H1 to H16 (section 2). Pipeline rules are P-numbered (section 6). Tests cite these IDs in their names or docstrings, so a reviewer can see which rule a test protects.

Contents:

1. What Wholecount is
2. Hard rules
3. Architecture
4. Data model
5. Identity of rows and decisions
6. The pipeline, rule by rule
7. Counting, the balance and confidence
8. The review model and undo
9. Outputs
10. Saved progress, set-ups and staleness
11. The interface
12. Offline and AI-free guarantee
13. Testing
14. Packaging, install and signing
15. Performance budgets
16. Decisions log
17. Open questions for Joe
18. Glossary

---

## 1. What Wholecount is

Wholecount is an offline Windows desktop tool for nonprofits in New York City. An operator adds the client lists their organization exports from different systems: ETO, property management, DYCD, partner spreadsheets and so on. The tool turns those lists into one clean master list and produces two numbers.

- **Goal 1, unique clients.** Each person is counted once across every file.
- **Goal 2, unique clients by program.** Each person is counted once per program they're in. A person in Workforce and Resident Services in one system, plus Property Management in another, counts 1 for Goal 1 and 3 for Goal 2.

**The operator** is a data or program staff member, not an engineer, who runs a batch a few times a year. A batch is 10 to 20 files and about 19,000 rows.

**The tool does four kinds of work, in order:**
1. It standardizes every file into one schema and checks each row.
2. It places each address with NYC Geosupport on the same computer and assigns State Senate, Assembly and City Council districts.
3. It finds copies inside each file and works out which records across files are the same person.
4. It counts.

A person decides everything the rules can't settle, in batches by cause rather than one row at a time.

**The nine stages**, with their plain names and their technical names in small caps:

| # | Plain name | Technical name | What happens |
| --- | --- | --- | --- |
| 01 | Add your files | SOURCES | Add files, find tables, choose header rows, include or exclude tables, group files into systems |
| 02 | Your columns | SCHEMA | The fields every file maps onto, including custom fields |
| 03 | Tidy up | PREPARE | Steps that add columns: clean, split by delimiter, split jammed address, split jammed name, calculated ZIP |
| 04 | Match your columns | MAP | Match each field to a column per table, with value checks, per-source defaults and date order |
| 05 | Programs | PROGRAMS | Which column holds the program in each file, which names are the same program, preview of the counts |
| 06 | Process | RUN | Run the pipeline over every included table |
| 07 | Fix problems | REVIEW | Decide causes in groups, then row by row |
| 08 | Results | SUMMARY | Goal 1, Goal 2, open same-person pairs, where people are, the printable page |
| 09 | Download | EXPORT | Choose the format and columns, write the output files, get the receipt |

The design boards for these stages are in `docs/context/design/`. Section 11 says how the boards and this spec fit together.

---

## 2. Hard rules

These are invariants. Code that breaks one is a bug, whatever a milestone or test says. Each rule has tests (section 13.2).

**H1. No network capability.** Wholecount can't reach the internet or any other computer. It has no web server, no port, no browser engine and no HTTP client. Section 12 sets out the layered design that enforces this and proves it. The only exception is a file the operator opens or saves through a Windows file dialog, which can be on a network drive. That's the operator's choice, and section 12.6 covers it.

**H2. No AI.** No model, no model file, no AI library and no call to any AI service, at runtime or at build time. Nothing in the product is decided by a statistical model. Every transformation is a written rule in this spec.

**H3. Deterministic.** The same input files, the same set-up and the same decisions on the same installation produce byte-identical outputs. The privacy offset is keyed per installation (P-GEO-6), so two installations put the same client's point in different places, while one installation always puts it in the same place.

**H4. Every row is accounted for.** Two balances hold at every moment, for every included table and for the batch:

1. Rows received = counted + not counted yet + set aside.
2. Counted = mapped + counted but not mapped.

Every non-empty row in every file is in exactly one of four places: an included table, a table the operator excluded, a block the tool found that isn't a table, or the header row. The first screen shows all four counts (P-READ-7). Rows are never deleted, only set aside, with a reason.

The engine asserts both balances before any count is shown or any file is written. If either fails, the app shows an error with the numbers and refuses to report counts. Whether a row counts never depends on its address (P-VAL-2, fix plan 5.1). (Fixes A-09, C-15, C-23, A-22.)

**H5. Nothing is joined on a guess.** Two records become one person without asking only for one of the three named reasons in P-ID-3. Every other likely pair is a proposal a person decides. Every automatic join is listed on Results with its reason and a "These are different people" action. A score threshold is never a reason to join. (Fixes C-01, C-02, A-05.)

**H6. Originals are kept.** No step overwrites a value. Tidy-up steps add columns. Standardization writes standard values into the output columns, while the value as entered stays on the row in memory and in the review file. A typed city that disagrees with its ZIP is never replaced. The row goes to review with both values. (Fixes B-03, B-31, A-11, B-27.)

**H7. No typing values in review.** A reviewer can't type a new value into a cell. A reviewer can do only these things:
- accept a fill derived from the row's own data, after seeing it
- approve a row as entered
- set a row aside with a reason
- keep one row of a group of copies
- decide a same-person pair
- confirm or split a program group
- change set-up, such as mappings, steps or defaults, which applies to whole tables

Corrections to values come from a corrections file (P-REV-6) or from the source system. (Fixes A-10.)

**H8. No client values in the audit, logs or progress messages.** The audit logs, any log file and every progress message carry only:
- record keys, which are keyed hashes (section 5.1), plus source letters, table keys and row numbers
- field and column names
- rule IDs, decision IDs, reason codes and counts
- keyed hashes of old and new values, for corrections (P-REV-6)
- reviewer names (section 8.7)
- program names
- file names, but only in the internal audit log, its file legend, the receipt, and progress messages on screen

They never carry a name, address, unit, city, ZIP, date of birth, Client_ID value or any other cell value.

The shareable audit log carries less than the internal one: no file names and no row numbers (section 9.2). Progress messages may name a file, because they're on screen only and never saved. (Fixes A-02, C-22, A-15.)

**H9. Client values are written to disk only in files the operator downloads.** Wholecount writes cell values only to the files the operator downloads, in the folder they pick. The app also writes three other things, and none of them holds a cell value:
- **Saved progress and set-ups** hold set-up and decisions, encrypted (section 10).
- **The saved crosswalk** holds keyed hashes, master IDs and decisions. It's off until the organization turns it on (section 10.5).
- **The install secret** is encrypted with DPAPI (section 5.1).

The app also keeps `%LOCALAPPDATA%\Wholecount\prefs.json`, which holds settings only: the saved-progress switch, the reviewer name, the publisher setting, thresholds, view choices such as the Tidy up grouping, and the window size. It keeps the labeled calibration pairs too, which are encrypted and hold no names (section 8.8). It keeps no other files. (Fixes A-04.)

**H10. Unmapped columns never leave the tool.** A source column that isn't mapped to a field doesn't appear in any export, either audit log or the printable page. It may be shown on screen inside the tool, as in the record panel (section 8.2). Columns whose names suggest sensitive data are pointed out on Add your files and dropped at load unless the operator keeps them on purpose (P-READ-9). (Fixes A-01.)

**H11. Every claim on screen is true and tested.** Every user-facing sentence lives in one copy registry (`wholecount/copy/`). Every sentence that states a fact about behavior has a claim ID (`CL-...`) and at least one test that proves the behavior. Examples are "Nothing leaves this computer" and "Client data is written only to the files you download." Copy without a test doesn't ship. (Fixes A-03, A-06, A-16, A-18, A-19, A-21, A-25.)

**H12. Decisions are tied to records, not positions.** Every decision is stored against a record key (section 5) and survives re-running, re-uploading and resuming. A decision whose record no longer exists or whose basis changed is never dropped silently. It's listed under "No longer apply" with the reason. (Fixes C-06, C-07, C-08, A-07, A-08.)

**H13. Results never describe an older state.** When anything upstream changes, everything downstream that depends on it is marked out of date at once. Counts and exports are never shown or written from out-of-date results. (Fixes C-03, C-04, C-18.)

**H14. Every long action shows progress.** Any action that can take longer than 300 ms shows a progress bar per step, with a count and a few words saying what's running. A bar never moves backward. Progress messages follow H8. (Section 11.6.)

**H15. Confidence comes from checked facts only.** Every confidence level is computed from counts and rules in this spec, with thresholds in one settings file. Every confidence level shows its reason in one line. (Section 7.4.)

**H16. Wording.** Plain words first, with the technical term beside them in small caps where it helps. Use American spelling, numbers with thousands separators, and no emoji, exclamation marks or em dashes. A problem says what it means and what to check. A button says what it does. A held control says what releases it. Every correction says it goes to the audit log.

---

## 3. Architecture

### 3.1 Stack

| Part | Choice | Why |
| --- | --- | --- |
| Language | Python 3.12 | The engine logic is Python and pandas. 3.12 is the supported line for PySide6 and PyInstaller. |
| UI | PySide6-Essentials, Qt Widgets only | A native window with no browser engine (H1). It has no QtWebEngine, no QML and no QtNetwork. PySide6 is LGPL, which allows handing it to clients. |
| Data | pandas, numpy | Tables and columns |
| Excel | openpyxl | Reads and writes .xlsx |
| XML | lxml, with network access off | XML sources |
| Geocoding | python-geosupport, wrapping NYC Geosupport Desktop Edition (local DLL) | It's the City's own address engine and runs on the machine. |
| Encryption at rest | Windows DPAPI through `ctypes` (CryptProtectData, CurrentUser scope) | It needs no key management and has no network. |
| Packaging | PyInstaller one-folder build, inside an Inno Setup installer | One setup file. The installer adds the firewall rules (section 14). |
| Tests | pytest, pytest-qt, hypothesis (dev only) | |

No other runtime dependencies are allowed. FastAPI, uvicorn, Streamlit, httpx, requests, aiohttp, urllib3, fsspec and every AI SDK are forbidden, and the lockfile test enforces this (section 12.4). Adding a dependency needs Joe's approval and an update to the approved set in `tools/offline_rules.py`.

### 3.2 Process model

- **One process.** The UI runs on the Qt main thread. Long jobs run on one worker `QThread` at a time, and the UI stays responsive (section 11.6).
- **The engine is plain Python with no Qt imports.** The UI calls it through the session layer. The engine never calls the UI. It reports progress through a `ProgressSink` interface (section 11.6.3).
- **All state changes go through commands** (section 3.4). This gives undo, audit and staleness tracking one choke point.

### 3.3 Package layout

```
wholecount/
  __main__.py          entry point: installs the offline guard first, then starts the app
  brand.py             PRODUCT_NAME and version
  guard/               offline guard (section 12)
  copy/                copy registry: every user-facing string, with claim IDs (H11)
  settings/            confidence.toml, limits.toml, defaults (no client data)
  engine/
    read/              file readers, encodings, table and header detection (P-READ)
    schema.py          canonical fields and custom fields (section 4)
    mapping.py         auto-mapping and column checks (P-MAP)
    prepare/           tidy-up steps (P-PREP)
    standardize/       names, addresses, ZIP, city, state, dates, typed values (P-STD)
    validate.py        row checks and problem kinds (P-VAL)
    geo/               Geosupport adapter, fallback reference, districts, privacy offset (P-GEO)
    copies.py          copies inside a file, same identifier in one system (P-DUP)
    identity.py        same person across files (P-ID)
    calibrate.py       matching calibration: sampling pairs, labels, measured rates (section 8.8)
    programs.py        program column per source, grouping proposals (P-PROG)
    counts.py          Goal 1, Goal 2, ranges, the balance (section 7)
    confidence.py      batch, match and location confidence (section 7.4)
    pipeline.py        runs the steps in order and reports progress
    outputs/           the output files, the two audit logs, the printable page, the receipt (section 9)
  session/
    state.py           the Session object (section 3.4)
    commands.py        every change, as a command with undo (section 8.5)
    staleness.py       the dependency graph (section 10.4)
    store.py           saved progress and set-ups, DPAPI encrypted (section 10)
    keys.py            install secret, record keys, person keys and fingerprints (section 5)
    crosswalk.py       the saved crosswalk across batches (section 10.5)
    reviewer.py        reviewer names and sign-offs (section 8.7)
  ui/
    theme/             tokens.json to QSS, the Archivo font (section 11.2)
    frame/             top bar, stage strip, ticker, ledger, ledger band (section 11.3)
    stages/            one module per stage (section 11.5)
    widgets/           callouts, tags, source marks, held buttons, grids, run panel, confidence
tools/                 developer tools only, never shipped: offline_rules.py, pe_net_imports.py, screens.py, make_zip_table.py
tests/                 section 13
tests_windows/         tests that need Windows (section 13.6)
installer/             wholecount.iss (section 14)
build/                 PyInstaller spec and runtime hook (section 12)
legacy/                the old build, for reference only
docs/                  milestones, audit, research, context
```

### 3.4 Session state and commands

`session.state.Session` holds all working state:
- `sources`: files, with byte fingerprints
- `tables`: key, block, header row, included flag, system
- `schema`
- `steps`: tidy-up steps per table
- `mappings`: per table
- `defaults`: per source
- `date_orders`: per table and field
- `program_columns`
- `program_groups`
- `run_settings`
- `results`: derived, versioned
- `decisions`: review, copies, identity, programs, all keyed by record key
- `export_settings`
- `undo_stack`
- `stale`: set of derived artifacts that are out of date

Every change is a `Command` with:
- `apply(session) -> CommandResult`
- `undo(session)`
- `label`: plain words naming the change, shown on the Undo control
- `audit_entry()`: H8-safe
- `invalidates`: the artifacts it makes stale (section 10.4)

The UI never mutates the session directly. The engine never sees the session. It receives plain inputs and returns results.

### 3.5 What the old build did, and what changes

The old build was a FastAPI server on 127.0.0.1 with an HTML front end in the browser and a Streamlit app beside it, started by a launcher that ran `pip install` on first launch. All of that goes. The engine's rules are kept where the audit found them right (each audit file has a "Checked and correct" list) and fixed where it didn't. The 60-plus server routes become session commands and engine functions with the same responsibilities. `legacy/crosswalk_server.py` is a useful map of what the UI needs.

---

## 4. Data model

### 4.1 Canonical fields

| Field | Type | Required | Notes |
| --- | --- | --- | --- |
| First_Name | text | yes | P-STD-1 |
| Middle_Initial | text, 1 letter | no | P-STD-1. Never derived from a placeholder or suffix (B-33). |
| Last_Name | text | yes | P-STD-1 |
| Client_ID | text | yes by default | The source system's identifier. The operator may make it optional for the batch. |
| Address_1 | text | for mapping | Street, with the unit moved to Address_2 |
| Address_2 | text | no | Unit |
| City | text | for mapping | For an NYC address, one of the five boroughs: New York, Brooklyn, Queens, Bronx or Staten Island. Outside NYC, the city as written. |
| State | text | for mapping | A US state's two-letter code. NY for NYC addresses. |
| Zip | text, 5 digits | for mapping | ASCII digits only (B-26) |
| Program | text | no | Built in, because Goal 2 depends on it |
| Date_of_Birth | date | no | Built in and recommended. It is the strongest identity evidence. In the old build it was a custom field, and the default now includes it. |

Client_ID's column requirement is met when a table maps either Client_ID or Date_of_Birth, because the count rule accepts either (P-VAL-2). A table that maps neither blocks Process for that table, naming both fields. A required custom field with no column blocks Process only if it's marked "needed to count." Otherwise Match your columns shows a warning, and every row of that table gets the soft reason "Required field has no column."

"Required for mapping" means the field is needed to place the address. A missing or failing address field never stops a row from counting (P-VAL-2). It only stops the row from being mapped.

Custom fields carry a type (text, whole number, decimal, date or yes/no), an optional default, a maximum length and a required flag. A value that doesn't parse as its type fails the row's check, with the field named. A required custom field blocks counting only if the operator marks it "needed to count." By default it doesn't.

"Address fields" in this spec means Address_1, Address_2, City, State and Zip.

### 4.2 Source systems

Every file belongs to a source system. By default each file is its own system. On Add your files the operator can say that several files come from one system (for example two ETO exports), and that choice decides where "same identifier" rules apply (P-DUP-3, P-ID-3). Each system has a display name the operator can edit. It defaults to the file name without its extension.

### 4.3 Source letters

Each file gets a letter, A onward, in the order files were added. The letter stays fixed for the batch and is shown as a 16px ink square with a white letter wherever the source appears (section 11.2). Tables inside a file are shown as the letter plus the sheet or block name.

---

## 5. Identity of rows and decisions

### 5.1 Keys

- **Install secret.** 32 random bytes from `secrets.token_bytes(32)`, made at first launch. It's stored DPAPI-encrypted (CurrentUser) at `%LOCALAPPDATA%\Wholecount\key.bin`. It's never shown, logged or exported. Every key below that involves client data is an HMAC-SHA256 with this secret, so no key can be worked back to a value without it.
  - **Backup.** Settings has "Back up the install secret." It writes a file the operator chooses, protected by a passphrase they type twice. The format is:
    - an scrypt-derived key (n=2^15, r=8, p=1, 16-byte random salt) encrypting the secret with a SHAKE-256 keystream
    - an HMAC-SHA256 tag
    - standard library only, with no new dependency

    Restore needs the passphrase. Losing the secret orphans the saved crosswalk (section 10.5), and the screen says so plainly.
- **Source fingerprint.** SHA-256 of the file's bytes. Used to tell whether a re-added file is the same file.
- **Table key.** `normalized file name :: sheet name or "data" :: header signature`.
  - The normalized file name is lowercase, with no folder, and spaces and punctuation collapsed to one underscore.
  - The header signature is the first 8 hex characters of SHA-256 over the chosen header row's cell texts.
  - If two added files have the same normalized name, the second and later ones get `~` plus the first 6 hex characters of their fingerprint appended.
  - Source letters are display only and aren't part of any key, so the order files are added in never changes a key. Block ranges like `A1:H63` are shown but aren't part of the key, because they shift when rows are added.
- **Record key.** It identifies one row, for decisions inside a batch. It's the first 20 hex characters of HMAC-SHA256(install secret, the table key, then the row's raw cell texts joined with U+001F, then an occurrence number). The occurrence number is 0, 1, 2 and so on, counting exact-duplicate rows in order within the table.
  - It's stable across re-runs, re-adds, resumes and add order as long as the row's own text doesn't change. It doesn't depend on row position. (Fixes C-06, C-08, C-20.)
- **Person key.** It identifies a person record across batches and quarters, for the saved crosswalk and master IDs (fix plan 5.4). It's HMAC-SHA256(install secret, `system | client_id`), with the system name lowercased and trimmed, and the Client_ID trimmed.
  - With no Client_ID, it's built from `system | folded given name | folded surname | date of birth`.
  - With no date of birth either, it adds `| address key` (P-ID-5).
  - Two rows with the same Client_ID-based person key in one system are the same person record, handled as copies or ID conflicts by P-DUP-3.
  - A name-based person key, built without a Client_ID, never joins rows by itself. Rows that share one become a copy group when they're in one table (P-DUP-2), or a same-person proposal when they're in different tables (P-ID-4). Only a decision makes them one person record, and until then each row is keyed on its own for counting.
- **Row number.** The row's position in its file (1-based, as Excel shows it), for display only.

### 5.2 Decisions

Every decision stores:
- a decision ID
- its kind
- the record keys it covers
- the basis it was made on (for example the fill value's derivation rule, or a same-person pair's evidence summary)
- when it was made

Decisions are re-applied after every run by record key. A decision whose records are missing or whose basis no longer holds goes to the "No longer apply" list, which Fix problems shows with the reason. Examples: the record changed, the file was removed, the mapping changed so the fill rule no longer yields the same value.

### 5.3 Master IDs

A master ID names a resolved person, and it's stable.
- **With the saved crosswalk on (section 10.5),** a person key seen in an earlier batch keeps its master ID.
- **Otherwise,** and for people the crosswalk hasn't seen, the master ID comes from the smallest person key in the person's group: `M-` plus the first 10 hex characters of SHA-256 over that person key.

Either way, deciding one pair doesn't renumber other people, and shuffling or re-exporting files doesn't change anyone's master ID. (Fixes C-20, fix plan 5.4.)

---

## 6. The pipeline, rule by rule

Rules are grouped by step. Each step reports progress (section 11.6). Where a rule exists because of an audit finding, the finding ID follows it. Where the old code was right, the rule says "as the old build" and names the function in `legacy/` to read.

### 6.1 Reading files (P-READ)

- **P-READ-1. Formats.** .csv, .tsv, .txt (delimited), .xlsx, .json and .xml. Every value is read as text. Nothing is converted on the way in, so a ZIP of 07030 keeps its zero. For .xlsx, a cell's number format is kept beside its text, so a real date cell can be recognized later (P-STD-6).
- **P-READ-2. Encodings.** Read text files as UTF-8, removing a leading BOM. If that fails, try Windows-1252, then show an amber callout on Add your files. It reads: "This file was read as Windows Western text. Check that names with accents look right," with up to five sample values from the file that contain non-ASCII characters. If neither encoding reads cleanly, the file is reported as unreadable, with the reason. Never decode with replacement characters. (Fixes B-02.)
- **P-READ-3. Invisible characters.** Remove the following from every cell, and count them for the quality report:
  - zero-width spaces and joiners
  - BOMs inside cells
  - soft hyphens
  - NUL and the other C0 control characters
  - a single leading apostrophe left by Excel

  Tabs, carriage returns, line feeds, non-breaking spaces and repeated spaces collapse to one space. A U+FFFD replacement character already present in the source text gives the row a review reason, "Value has an unreadable character," naming the field. (Fixes B-24.)
- **P-READ-4. Tables inside sheets.** Split a sheet into blocks on fully blank rows and columns, as the old build did (`legacy/table_detect.py: detect_in_grid`). Classify each block as records, summary or unknown, as the old `classify_table` did. Records blocks are ticked by default. Summary blocks and unknown blocks are unticked by default.
- **P-READ-5. Continuation blocks.** A block with the same column count as the records block above it, and no header-like first row, is shown as a continuation of that table and included with it by default. (Fixes A-09.)
- **P-READ-6. Header rows.** Detect the header row as the old `detect_header` did. Flag a choice that looks wrong with the old `header_looks_wrong` checks. The operator can choose a different row under Show data. Rows above the header are counted as "above the header" (P-READ-7).
- **P-READ-7. Accounting for every row.** Add your files shows, per file, the rows in included tables, the rows in excluded tables, the rows in blocks that aren't tables, and the rows above the header. Those add up to the non-empty rows in the file, and the screen says so. (Fixes A-09, C-23, H4.)
- **P-READ-8. Bad files.** A file that can't be read is reported by name with the reason, and the other files in the same add still load. (Fixes A-13.)
- **P-READ-9. Sensitive columns.** Columns whose names suggest sensitive data are listed on Add your files, with "Drop at load" ticked. That covers SSN, social security, Medicaid ID, gender, sex, race, ethnicity, religion, diagnosis, HIV, immigration status and similar, kept in one list in `settings/sensitive_columns.toml`. A dropped column is never held in memory after load. Columns whose values mostly look like Social Security numbers are listed the same way, whatever their name. That means the ###-##-#### pattern, or nine digits that pass the SSN structure rules (no 000, 666 or 9xx area, no 00 group, no 0000 serial). (Fixes A-01, H10, fix plan 4.1.)
- **P-READ-10. No URLs.** Readers accept only local file paths chosen through the file dialog or drag and drop. They open the file themselves and pass a file object to pandas, openpyxl or lxml, and never a path string. lxml parsers are created with `no_network=True`, `resolve_entities=False` and `load_dtd=False`. (H1, research section 4.)

### 6.2 Matching columns (P-MAP)

- **P-MAP-1. Auto-mapping is by meaning, not file order.** For each field, score every column: exact name, then known synonyms, then whole-word tokens. Columns whose names say they belong to someone else are excluded from person fields. That covers words like emergency, contact, guardian, parent, caseworker, staff, employer and landlord, kept in a list in `settings/mapping.toml`. Mailing columns lose to home or residential columns for address fields. "Visit," "last visit" and date-like names never map to name fields. A column that holds dates never maps to Program. An identifier-named column never maps to Program. (Fixes B-21, B-22, B-48, B-49.)
- **P-MAP-2. Column check.** After mapping, check each mapped column against its values, as the old `column_check.check_mapping` did, and add these checks:
  - a Program column that looks like dates or codes
  - an Address_1 column that's mostly units
  - an Address_2 column that's mostly streets
  - a name column that's mostly one value

  A warning names the column that would fit better and offers a one-click fix. A warning never blocks. A required field with no column blocks Process and the fast path, naming the table and field.
- **P-MAP-3. Split columns don't replace real ones.** A column made by a tidy-up step is offered for a field only when the table has no real column for it, or when the operator picks it. (Fixes B-23.)
- **P-MAP-4. Per-source defaults.** For one table, a value can be set for any field wherever that field is blank. It never replaces a value the file supplied, and every use goes to the audit by record key.
- **P-MAP-5. Date order per table.** For each date field in each table, the tool counts three kinds of value: values that can only be month first (a second part over 12), values that can only be day first (a first part over 12), and values that could be either.
  - **The unambiguous values all agree:** that order is used and shown.
  - **There are none:** Match your columns asks the operator, "This table writes dates as month/day or day/month?", with the counts as evidence. Until the operator answers, ambiguous values in that table go to review.
  - **They disagree,** meaning the column holds both kinds: every non-ISO date in that column goes to review, with "Dates in this column are written both ways," until the operator chooses an order. Then only the values that contradict the chosen order stay in review.

  (Fixes B-13.)
- **P-MAP-6. Two-digit years.** For each date field in each table, the operator may set a rule on Match your columns: "Two-digit years up to NN mean 20NN, otherwise 19NN." For a date of birth, the suggested NN is the current two-digit year. Without a rule, P-STD-6 sends two-digit years to review.
- **P-MAP-7. SSN-shaped identifiers.** A column mapped to Client_ID whose values mostly look like Social Security numbers (P-READ-9) blocks Process. The screen says "These identifiers look like Social Security numbers. Map a different identifier, or drop this column." (Fix plan 4.1.)
- **P-MAP-8. Weights.** "Lose to" in P-MAP-1 means a score penalty, not exclusion, so a mailing address column is still offered when it's the only address column. A calculated ZIP column (P-PREP-5) wins over a real Zip column, because a person made it on purpose, as in the old build.

### 6.3 Tidy-up steps (P-PREP)

Steps add columns and never change the source column. Steps run in the order listed per table. A step that changes nothing is shown as an amber row with what it failed to find.

- **P-PREP-1. Clean columns.** Trim, collapse spaces, and set case: none, Title, UPPER or lower. Title case for names follows P-STD-1. Steps can also strip junk characters and strip edge punctuation.
- **P-PREP-2. Split by a delimiter.** Takes a delimiter, a custom delimiter, a maximum number of splits and new column names.
- **P-PREP-3. Split a jammed address.** Parses one cell into street, unit, city, state and ZIP. The grammar must handle every case in the old build's proof workbook plus these (each one is a test):
  - The house number keeps its hyphen, with or without spaces around it: "117-19 45th Ave" and "117 - 19 45th Ave" both give house number 117-19. (Fixes B-09.)
  - A street name that contains a city or borough word stays whole. "1010 Grand Concourse" keeps "Concourse," "Brooklyn Ave" stays a street, and so do "Jamaica Ave" and "Queens Blvd." A city is read only from the segment after the street, never from inside it. (Fixes B-08.)
  - A 9-digit ZIP, with or without a dash, gives its first five digits, and the row is flagged "ZIP had 9 digits" for the audit, not for review. (Fixes B-07.)
  - A trailing segment that's neither a city, state nor ZIP isn't dropped. It goes to a new column, `<name>_extra`, and the row gets a review reason "Address has extra text: check it." That covers "c/o Jane Doe" and "rear building." (Fixes B-10.)
  - A unit followed by a city, as in "Apt 3 Brooklyn," gives unit "Apt 3" and city "Brooklyn." (Fixes B-29.)
  - Lone-letter and letter-number units are recognized after a unit word or a comma, and as a final token after a street type: "Apt B," "Unit B," ", B" and "5C." (Fixes B-30.)
  - "Rear," "Front" and "Basement" are units with or without a comma. (Fixes B-42.)
  - Ordinal streets aren't units: "45th Ave" is a street, and a trailing "14A" after a street type is a unit.
- **P-PREP-4. Split a jammed name.** Parses "Last, First Middle," "First Middle Last" and "Last First" when the operator says so. Rules:
  - Particles stay with the surname. The list is de, del, de la, della, di, da, do, dos, du, van, van der, von, la, le, st, bin, ibn and al. (Fixes B-11.)
  - Hyphenated and two-word surnames stay whole when written "Last, First." With no comma, a name of three or more words can't be split with certainty, because a two-word surname looks like a middle name. The tool splits it as First, Middle, Last, keeps every word, and adds the soft review reason "Name has three or more words: check which is the surname." Nothing is dropped. (Fixes B-11, B-32.)
  - Compound given names that are commonly written as two words stay together as the first name when the file is "Last, First": Mary Ann, Jose Luis, Juan Carlos and Maria Elena, kept in a list.
  - Titles go to a `<name>_title` column. That covers Mr, Mrs, Ms, Miss, Mx, Dr, Rev, Fr, Sr (as Sister, only before a given name) and Hon.
  - Post-nominals go to `<name>_credential`. That covers MD, DO, PhD, EdD, Esq, RN, LPN, NP, LCSW, LMSW and CPA.
  - Generational suffixes go to `<name>_suffix`. That covers Jr, Sr, I, II, III, IV, V, VI, 2nd, 3rd and 4th, with or without a period or comma.

  None of these ever becomes a first, middle or last name. All three lists live in `settings/names.toml`. (Fixes B-12.)
  - A middle initial comes only from a real middle name or initial. NMI, NMN, "Unknown" and suffixes never become initials. (Fixes B-33.)
- **P-PREP-5. Calculated ZIP column.** Calculates the ZIP the address points to, through Geosupport, or through the fallback reference with an exact match only. A value that isn't a valid NYC ZIP is never written. A garbage input gives blank, with the reason "No ZIP could be worked out," and never the first five digits of something. (Fixes B-06.)

### 6.4 Standardizing each field (P-STD)

- **P-STD-1. Names.**
  - Trim and collapse spaces.
  - Title-case only values written entirely in upper or lower case. Keep the case of mixed-case values as typed.
  - Title casing knows Mc, Mac (only when followed by an uppercase letter in a known list), O' and D', hyphenated parts, and the particles in P-PREP-4. The cases the old build got wrong are tests. (Fixes B-43.)
  - Digits in a name are flagged as possible column misalignment.
- **P-STD-2. Placeholders.** Placeholders are field-specific, and every list lives in `settings/placeholders.toml`.
  - **In every field except the name fields:** an empty cell, or one of NULL, N/A, #N/A, (null), none and nil in any case, or a lone "-", "--" or "?". Treat these as blank.
  - **In the name fields** (First_Name, Middle_Initial, Last_Name), only an empty cell, NULL, N/A, #N/A, (null), "-", "--" and "?" are blank. The name rule below wins for None and Nil.
  - **A soft review reason** is a review reason that doesn't block counting. Its likely action is "Accept all as they are." Fix problems groups soft reasons after the others.
  - **In identifier and address fields:** also 0, 00, 000, unknown, unk, refused, declined, TBD, same, "see above," NA and N.A. Treat these as blank, with the reason "Placeholder in place of a value." (Fixes B-01.)
  - **In name fields:** Na, Nan, None and Nil are real names in some languages. Keep them as values and add a soft review reason, "Name may be a placeholder." Never blank them. (Fixes B-25.)
  - **Words that describe a housing situation:** homeless, shelter, street, no fixed address, NFA and undomiciled, in an address field. These set the row's location status to "No fixed address." The row still counts if it passes the count checks (P-VAL-2), and it isn't mapped.
- **P-STD-3. ZIP.**
  - Five ASCII digits only. Full-width and other Unicode digits are flagged and never accepted. (Fixes B-26.)
  - ZIP+4 is reduced to five digits.
  - A ZIP mapped from a numeric .xlsx cell is read as its integer, and left-padded with zeros to five digits when it has three or four digits, so 7030 becomes 07030. A numeric cell with one, two or more than five digits isn't padded. It fails the ZIP check.
  - The borough of a ZIP comes from an explicit list of NYC ZIP codes, never from ranges. The list lives in `wholecount/engine/geo/data/nyc_zips.csv` (ZIP, borough, source), and `tools/make_zip_table.py` builds it from a cited public source at development time. It must place 11004 and 11005 in Queens, 11690 to 11697 in Queens, 11001 and 11580 outside NYC, and 10463 (Marble Hill) in Bronx for postal purposes. (Fixes B-03, B-41.)
  - A valid five-digit ZIP that isn't in the NYC list gives location status "Outside NYC, not mapped." The row still counts. A NYC borough written beside a non-NYC ZIP gets the location problem "City and ZIP disagree." (Fixes B-04, fix plan 5.1.)
  - A ZIP that isn't five valid digits gives the location problem "ZIP is not a valid ZIP."
- **P-STD-4. City.**
  - A typed city that's a borough name or one of its aliases is standardized to the borough. The aliases are in `settings/places.toml`, as in the old build, which had 24 spellings.
  - A typed neighborhood in the list of 114 NYC neighborhoods, from the old build and extended as needed, is standardized to its borough. Its original text stays on the row.
  - A blank city takes the borough of an NYC ZIP, and that's audited as a fill.
  - A typed city that isn't recognized is never overwritten. The row gets the location problem "City not recognized: check it," with a suggestion of the ZIP's borough. (Fixes B-31.)
  - A typed city whose borough disagrees with the ZIP's borough is never overwritten. The row gets the location problem "City and ZIP disagree," showing both. (Fixes B-03, A-11.)
  - City problems are location problems. They stop a row from being mapped, never from being counted (P-VAL-2).
  - A place name that's also a borough neighborhood but appears with a non-NYC ZIP or state, like "Chelsea, MA" or "Flushing, MI," isn't folded into a borough. (Fixes B-05.)
  - Address text inside Address_1 that names a different city than the City column is flagged for review, not discarded. (Fixes B-27.)
  - A neighborhood left inside Address_1 by a split is moved to its own column, `Address_1_place`, and doesn't stay in the street. (Fixes B-28.)
- **P-STD-5. State.**
  - NY, N.Y., New York and New York State all give NY.
  - Any other US state or territory, by name or two-letter code, is accepted and standardized to its code, and the row is "Outside NYC, not mapped."
  - A blank state with an NYC ZIP gets NY, audited as a fill.
  - Another state written beside an NYC ZIP gives the location problem "State and ZIP disagree," not "Outside NYC," because one of the two is a typo.
  - A blank state with a non-NYC ZIP, or a value that isn't a US state, gives the location problem "State not recognized."
  - A blank state with no ZIP gives the location problem "Address incomplete."
  - The jammed-address splitter still reads only NY as a state (P-PREP-3), so "St" is never taken as a state.

  (Fixes B-05, fix plan 5.1.)
- **P-STD-6. Dates, including date of birth.**
  - Accepted forms: ISO (2024-03-15); month and day orders with /, - or . separators, read in the table's date order (P-MAP-5); and a real date cell from .xlsx.
  - An Excel serial number is accepted only from a numeric .xlsx cell whose format is a date format. A 5-digit string is never read as a date. (Fixes B-16.)
  - A two-digit year is never guessed. The row goes to review, "Two-digit year: check the century," showing both readings, unless the operator set a rule for that table (P-MAP-6). (Fixes B-14.)
  - A 5-digit text value in a date field gets the review reason "Looks like an Excel date number," showing the date it would be, so the operator can fix the source or approve. It's never converted on its own.
  - For date of birth, a date in the future or before 1900 fails the check. An age over 115 is flagged for review. (Fixes B-15.)
  - Impossible dates fail the check with the field named.
- **P-STD-7. Typed custom fields.** As the old build's `normalize_typed_value`.
- **P-STD-8. A unit in both address lines.** When Address_1 ends in a unit and Address_2 also holds a unit:
  - If they're the same unit after normalizing (Apt 4B, #4B and 4B all match), keep one in Address_2.
  - If they differ, keep both as written and give the row the location problem "Two different units."

  (Proof workbook sheet 11.)

### 6.5 Row checks (P-VAL)

- **P-VAL-1. Every row has two statuses** (fix plan 5.1).
  - **Count status** says whether the row counts as a person record. It's one of these:
    - **Counted, passed every count check**
    - **Counted, approved as entered by a reviewer**
    - **Counted, corrected from a corrections file**
    - **Not counted yet**, with the reasons that hold it
    - **Set aside**, with the reason
  - **Location status** applies to counted rows and says whether the row is on the map. It's one of these:
    - **Mapped, high confidence**
    - **Mapped, low confidence**
    - **Not mapped**, with the reason: No fixed address, Outside NYC, Address problem (with its problem kinds), or Not found
    - **Filled from the row's own address**, which is mapped and records the fill

  The clean file writes both statuses. A corrected or filled row never says "passed every check." A per-source default (P-MAP-4) doesn't change either status, but it's audited. (Fixes A-10.)
- **P-VAL-2. The count rule.** A row counts when all of these hold:
  - It has a first name and a last name, and neither is a placeholder.
  - It has a Client_ID or a valid date of birth.
  - It isn't a summary row.
  - It isn't a confirmed copy.
  - It has no open "Same ID, different details" conflict (P-DUP-3).
  - Any custom field the operator marked "needed to count" passes.

  Address fields play no part. A row that fails only address checks or geocoding is counted and listed as "Counted, not mapped" with its reason.
- **P-VAL-3. Problem kinds.** Reasons are problem kinds with stable IDs, in `wholecount/copy/problems.toml`. Each has:
  - a plain title
  - what it means
  - what to check
  - the Excel steps to fix it at the source, as the old build's help did
  - one flag: **holds the count**, **location**, or **soft**

  Fix problems shows count-holding problems first, then location problems in their own tab, then soft ones. The table of problem kinds and their flags in `docs/milestones/M04-standardize.md` is binding. Only a missing name, a missing identifier (no Client_ID and no valid date of birth), a field marked "needed to count" that fails, and an open same-ID conflict hold the count. Date of birth problems are soft when the row has a Client_ID. Open copy groups don't hold the count. Their rows are counted, and each open group widens the Goal 1 range the same way an open same-person pair does (section 7.2). A confirmed copy is set aside.
- **P-VAL-4. Summary rows.** Rows reading Total, Subtotal, Count, Average and the like, as the old build did, are set aside with the reason. A surname that's a real name, like Sum, Mean or Count, is set aside only when the row has no other person data. (Fixes B-44.)

### 6.6 Placing addresses (P-GEO)

- **P-GEO-1. Geosupport first.** When Geosupport Desktop Edition is installed, every address goes through Function 1B through python-geosupport. The adapter interface is `GeoBackend.lookup(house_number, street, borough_or_zip) -> GeoResult`, so tests use a fake backend.
- **P-GEO-2. Location confidence.**
  - **High** means Geosupport matched the house number on the street (return code 00) or the fallback matched exactly (P-GEO-3).
  - **Low** means Geosupport matched with a warning (return code 01), matched only the street, or matched an out-of-range house number.
  - **Not placed** means no match.

  "Verified" appears only for High. (Fixes B-35.)
- **P-GEO-3. The fallback reference is exact only.** Without Geosupport, the tool looks the address up in a reference file of real NYC address points that the operator installs. The key is the normalized house number, the street name with its type and direction expanded, and the ZIP or borough. There's no fuzzy match. Near matches are shown as suggestions in Fix problems, and never assigned coordinates or districts on their own. (Fixes B-17, C-24.)
- **P-GEO-4a. Example data.** "Try example data" loads five made-up files from `wholecount/sample_data/`, made by a committed, seeded script, `tools/make_example_data.py`. M01 builds both. They keep the shapes the old samples tested: a CSV with jammed names and addresses, a multi-sheet .xlsx with a header row that needs choosing and a notes sheet, a TSV, a nested JSON and an XML. Every row has a Client_ID or a date of birth, except twelve marked rows that show the count rule. Their programs, copies, same-ID conflicts and cross-file people are planned so the counts are known in advance, and the script writes those expected counts to `wholecount/sample_data/EXPECTED.json` for the acceptance tests. The sample reference sits in the same folder. The old samples stay in `legacy/sample_data/` for reading tests only.
- **P-GEO-4. No sample reference in real runs.** The sample reference file in the repo is for tests and the example data only. A batch of the operator's own files can't use it, and preflight says so. "Try example data" uses it, and then every screen and every output carries PRACTICE in its header or first line. When neither Geosupport nor a real reference is present, Process runs without placing addresses, says so in the pre-run summary and the ledger, and every row is "Counted, not mapped: no geocoder." The real reference file lives in `%LOCALAPPDATA%\Wholecount\reference\`, and `docs/REFERENCE_DATA.md` explains how to get it. (Fixes the synthetic reference problem in AUDIT.md section 5, and fix plan 5.3.)
- **P-GEO-5. Districts come from the true point.** State Senate, Assembly and City Council districts come from Geosupport, or from point-in-polygon on the official NYC Planning district files bundled with the app. The point-in-polygon test must handle holes and multipolygons. (Fixes B-19.)
- **P-GEO-6. Where coordinates go** (fix plan 4.4).
  - **Final_Clean_Mapped carries no coordinates by default.** It already holds the address, so it's identified data. It keeps the districts. The operator can switch on "Exact coordinates, for internal use," which adds Latitude and Longitude with that label in the column note and the receipt.
  - **Map_Counts** is always written. It holds counts per program by Council, Assembly and Senate district, plus census tract if that Geosupport field is on. It has no names, addresses, IDs or points. Any count from 1 to 10 is blanked and shown as "fewer than 11," and the blanking threshold lives in `settings/privacy.toml`.
  - **Map_Points** is optional and off by default. It holds only program and a moved point per person.
- **P-GEO-7. The privacy offset** for Map_Points.
  - Each point is moved 150 to 250 feet in a direction derived from HMAC-SHA256(install secret, "offset|" + address key), using the fix plan's `stable_offset` and `move_point` with the address key in place of the master ID.
  - Every client at one building gets the same moved point. Averaging many clients, or many quarters, gives back the moved point, never the true one.
  - The offset is independent of other rows and run order, and nobody can reverse it without the install secret.
  - There is no seed setting. The secret is never shown, logged or exported, and the audit records only that the offset was applied.
  - Districts always come from the true point. The Map_Points note and the receipt say a moved point can sit across a district line from its district.

  (Fixes B-18, A-14, C-25, B-45, B-46.)
- **P-GEO-8. Crash-free.** A test geocodes at least one address from each reference source, end to end, through Process. (Fixes C-10.)
- **P-GEO-9. Fill proposals.** "Look up all N" proposes a ZIP, city or state from the row's own street through Geosupport or the exact fallback only. Each proposal shows the evidence: house number and street matched, and the borough or ZIP it came from. Nothing changes until the reviewer accepts. A proposal is never made from the street name alone, without the house number. (Fixes B-34.)

### 6.7 Copies inside a file, and the same identifier (P-DUP)

- **P-DUP-1. Identical records.** Two rows in one table are identical only when every mapped field matches after standardization. That includes date of birth, middle initial and every custom field. (Fixes B-37.)
- **P-DUP-2. Possible copies inside a file.**
  - **Default rule.** Rows in one table group only when surname, given name (or a known nickname) and date of birth all match. In a table with no date of birth, surname, given name and the full address key must all match.
  - **Never enough.** Name alone, or name and ZIP, never groups rows.
  - **Different programs.** Rows with different Program values are never copies, because they're one person's separate enrollments.
  - The rule is editable on Fix problems. (Fixes B-47, C-17.)
- **P-DUP-3. Same identifier.** The same Client_ID twice is checked only inside one source system (section 4.2), never across systems.
  - If the names and date of birth agree, the rows are copies of one person, or one person's enrollments in different programs.
  - If they disagree, the rows are "Not counted yet: Same ID, different details."
  - A reviewer who decides "These are different people" splits them, and each counts.
  - A reviewer who approves them "as entered" leaves them as separate records. They then become a same-person proposal in at least the Possible band (P-ID-4), so the shared ID is never forgotten.

  (Fixes C-17, B-36, A-05, C-02.)
- **P-DUP-4. Keep this copy.** It's stored by record key. Re-exporting or reordering the source never flips which row is kept. (Fixes C-08.)
- **P-DUP-5. Saved copy decisions** cover only the record keys they were made on. A new record that would join a decided group reopens the group for a decision. (Fixes B-38.)
- **P-DUP-6.** Person keys fold accents, case, punctuation and spacing before comparing, so José and Jose, and O'Brien and OBrien, compare equal. (Fixes B-39.)

### 6.8 The same person across files (P-ID)

- **P-ID-1. Candidates.** Identity runs over every counted row, mapped or not (fix plan 5.1). Pairs are blocked by four keys, so the tool compares likely pairs, not every pair:
  - surname key plus date of birth
  - surname key plus address key
  - given name key plus date of birth
  - surname key plus given name key alone, which catches people who moved and have no date of birth (fix plan 5.2)

  Pairs found only through the name-only key need a rare name to reach the Possible band. A rare name is one shared by no more than 3 records in the batch. Nicknames come from the old build's 92 groups. Surname changes, swapped birth-date digits, swapped first and last names, one half of a double surname, and the same address spelled differently all make a pair a candidate.
- **P-ID-2. Evidence.** Every candidate pair gets an evidence list in plain words, like "date of birth matches exactly," "surname matches," "given names are nicknames of each other," "address matches (house number, street, ZIP)," "birth dates differ by two swapped digits," and "suffixes differ (Jr and none)." It also gets a score. The weights are in `settings/identity.toml`, starting from the old build's weights. The score is shown only to sort and band pairs.
- **P-ID-3. Joining without asking happens for three named reasons only:**
  - `same_system_id`: the same Client_ID inside one source system, with surname, given name (or nickname) and date of birth (when both have one) agreeing.
  - `four_exact_facts`: date of birth exact, surname exact, given name exact (after folding), and address key exact, with house number, street name and type, ZIP, and unit when both have one. Suffixes must also agree. A Jr and a no-suffix record never join without asking.

  - `earlier_batch`: with the saved crosswalk on (section 10.5), two groups in this batch whose person keys a person already joined in an earlier batch. It applies only to a join a person decided, never to one the tool made.

  The reason is returned by the matcher as a value, never derived from a score. Every automatic join, including `earlier_batch`, is listed on Results with its reason and a "These are different people" action. (Fixes C-01, C-02.)
- **P-ID-4. Every other candidate is a proposal**, banded by score into Likely and Possible (thresholds in `settings/identity.toml`). Pairs below the Possible band aren't shown, except during calibration (section 8.8). Twins, and a parent and child with the same name, must come out as proposals, never joins. The expected results in C-01 were worked out with the old address key. With P-ID-5 they change, and the spec's rules decide the numbers the test asserts.
- **P-ID-5. The address key** includes the street type and direction. 45 Park Ave and 45 Park Pl are different addresses. (Fixes C-24.)
- **P-ID-6. Decisions.** "Same person" and "Different people" decisions are stored per pair of person keys. They go to both audit logs with both master IDs, the decision ID and the reviewer's name, and they survive re-runs. With the saved crosswalk on, they also carry into later batches. (Fixes C-21.)
- **P-ID-7. Undoing a join.** "These are different people" on an automatic join splits it, and goes to the audit.

### 6.9 Programs (P-PROG)

- **P-PROG-1.** Each table has at most one program column, or a per-source default. A table with neither is listed on Programs and on Results as "not in Goal 2," with its row count.
- **P-PROG-2.** Grouping proposals are made as the old build's `program_names.py` did, with filler words, short forms and similarity, plus one more rule. Two names that differ in a word that changes meaning are never proposed together, unless that word is only a short form of the same word. Those words are youth and senior, employment and housing, level numbers, and so on, kept in a list in `settings/programs.toml`. The screen states the reason for each proposal. (Fixes B-40.)
- **P-PROG-3. Proposals are never applied until a person confirms them.** An unconfirmed proposal counts its names separately. Continue to Process is held until every proposal is confirmed or split, and the held caption says how many are left. (Fixes B-20.)
- **P-PROG-4. The fast path builds program grouping the same way** and stops at Programs if any proposal needs confirming. Fast path and stage-by-stage give identical results on the same inputs and decisions, and a test proves it. (Fixes C-05.)
- **P-PROG-5.** Taking any name out of a group works, including the name the group is called by, in which case the group takes the next name. (Fixes C-13.)
- **P-PROG-6.** Every confirmation, split and rename goes to the audit with the program names involved. Program names aren't client data.

### 6.10 The pipeline order

1. Read and detect (P-READ)
2. Tidy-up steps (P-PREP)
3. Map and apply defaults (P-MAP)
4. Standardize (P-STD)
5. Check rows (P-VAL)
6. Place addresses and districts (P-GEO)
7. Copies and the same identifier (P-DUP)
8. Apply review decisions by record key (section 8)
9. Same person across files (P-ID), on counted rows
10. Programs (P-PROG)
11. Count and balance (section 7)
12. Confidence (section 7.4)

Each step is a pure function of its inputs and the decisions that apply to it, so the staleness graph (section 10.4) can tell exactly what to re-run.

---

## 7. Counting, the balance and confidence

### 7.1 What counts

Counted rows count (P-VAL-2), whether or not they're mapped. Rows not counted yet and rows set aside don't count, and Results says how many of each there are. Results and the printable summary show "Counted, no usable address" with its number and its breakdown: No fixed address, Outside NYC, Address problem, Not found, and No geocoder.

### 7.2 Goal 1 and Goal 2

- **Goal 1** is the number of master IDs among counted rows.
- **Goal 2** is the number of distinct (master ID, program as grouped) pairs among counted rows with a program.
- **While same-person pairs or copy groups are open, both are ranges.** The low end treats every open pair and every open copy group as one person. The high end treats them all as different people. Results shows "5,940 to 5,954 until 14 pairs are decided" for Goal 1, and the same form for Goal 2. (Fixes C-12, A-12.)
- **"Final" appears only when no pairs or copy groups are open and no rows are "Not counted yet."** Otherwise the wording says what's still open: "Settled for the rows counted so far. 1,232 rows aren't counted yet." Location problems don't stop a count from being final. (Fixes A-06.)
- **"Without a program" counts people, not records,** and says so. (Fixes C-19.)

### 7.3 The balance

- **For every included table:** rows received = counted + not counted yet + set aside. Also, counted = mapped + counted but not mapped.
- **Across the batch:** the sum over tables, plus rows in excluded tables, rows in non-table blocks and rows above headers, equals the non-empty rows in the files (H4).
- **When it's checked.** The engine checks all three after every run and every decision.
- **The ledger** shows the first sum as the stacked bar, with "The three add up to the rows received." It shows the second sum in Locations.
- **The row files.** Final_Clean_Mapped holds the counted rows. Manual_Review_Needed holds every row with an open problem, with a Counted column (Yes or No). Set_Aside_Records holds only set-aside rows. So clean rows + rows with Counted No in the review file + set-aside rows = rows received, exactly, and a test proves it. (Fixes C-15.)

### 7.4 Confidence

Thresholds live in `wholecount/settings/confidence.toml`. These are the starting values Joe approved, to be tuned later.

**Batch confidence**, shown in the ledger at all times after a run. Three measures:
- rows counted, divided by rows received
- open same-person pairs
- counted rows mapped with High confidence, divided by counted rows whose address was looked up

The level is set as follows:
- **High**: counted rows at or above 95%, zero open pairs, and High placements at or above 95%.
- **Low**: any percentage under 80%.
- **Medium**: anything else.
- **When nothing was looked up,** because there's no geocoder, the third measure reads "not available" and the level can't be High. The reason says "Addresses weren't placed, so confidence can't be High."

The display is the level in one word, then one sentence of reason built from the measure that set it. For example: "Medium. 6,084 of 7,412 rows are counted, and 14 possible same-person pairs are still open." The detail view lists all three measures, with each value and what High needs. There are no percentages in the headline and no letter grades.

When matching has been calibrated (section 8.8), the detail view adds one line with the measured rates and the date of the calibration.

**Low holds Download.** When batch confidence is Low, Download waits until someone ticks "I have seen that confidence is Low." The tick goes to the audit with the time and the three measures. It resets when the level is recomputed.

**Match confidence**, on each same-person pair in Results and Fix problems:
- **Certain**: an automatic join, with its named reason.
- **Likely** and **Possible**: score bands, with the evidence list.

**Location confidence**, on each row and in the ledger's Locations section: High, Low or Not placed, with a reason. For example: "Geosupport matched the building," "Matched the street but not the house number," "Not found."

**Colors.** High is ink, Medium and Low are amber, and the action to take is blue. Green is never used for confidence, because green means a person decided. The prototype settled this (section 16). For same-person pairs:
- The band word (Certain, Likely or Possible) is ink text.
- An open pair carries the blue NEEDS YOU tag.
- A pair a person decided carries the green "Decided by you" tag.

---

## 8. The review model and undo

### 8.1 Fix problems, step 1: the causes

Open rows are grouped by cause, largest first, under three tabs:
- **Affects the counts** comes first. It holds the problems that keep rows out of the count, the same-identifier conflicts, and the open copy groups, which widen the range.
- **Location** holds address problems. These rows already count, and fixing them improves the map.
- **Worth a look** holds the soft reasons.

The cross-file note says how many people also appear in another file, and says nothing needs doing. Each cause has:
- a count
- a plain title
- one line of what it means
- its actions

The possible actions depend on the cause:
- **Look up all N.** A fill derived from the row's own address, shown as a preview list before anything changes.
- **Accept all as they are.**
- **Set all aside**, with a reason picked from a fixed list in `wholecount/copy/reasons.toml`, such as Not a client, Test record, Duplicate of another system's record, Out of scope for this report, or Other. Other takes a short note of up to 120 characters, and that note goes only to the internal audit log, after a warning not to type client names.
- **Send to row by row.**
- **Preview.**
- **Compare.** For copies, opens the side-by-side view.
- **Match it and process again.** For a mapping diagnosis, as board 07 shows.

### 8.2 Fix problems, step 2: row by row

A queue with:
- a status filter, problem and source facets, search and page size
- select the page, or every row matching the filters
- bulk approve, set aside, return to open, and keep one per program
- a record panel, showing:
  - what the problem means
  - the original row with every mapped column
  - unmatched columns with their values, on screen only. Sensitive columns are already dropped at load (P-READ-9), and unmatched values never reach an export (H10).
  - other rows that share the identifier
  - the suggestion, if any
  - approve, set aside, and open the source file in its own app

There's no free-text cell editing and no "set a field on all selected" (H7). The old boards show "Set a field on all N" and "Reject," and both are dropped (Q7). "Open the source file" hands the file to Windows through the file's own association, after a confirmation, and only for files the operator added. Section 12.6 covers how that stays inside H1.

### 8.3 Decisions survive everything

Process, Preview the counts, the fast path, mapping changes and resume never discard decisions (H12). After each run, decisions are re-applied by record key. The "No longer apply" list shows any that don't fit. (Fixes C-07, A-07, A-08.)

### 8.4 Finish review

Finish review is held while any cause in the "Affects the counts" tab of step 1, including groups of copies, is undecided. The held caption names what's left. The old build changed this in build 12, and it's kept.

When the causes are decided but rows sent to row by row are still open, Finish review asks first: "N rows are still open. They stay in the review file and aren't counted. Finish anyway?" Location problems never hold Finish review.

### 8.5 Undo

One Undo control in the stage strip covers every command: set-up changes, review decisions, row decisions, copies, same-person decisions and program decisions. It names the change it takes back, for example "Undo: Set 96 summary rows aside." Undoing re-derives everything downstream before the screen redraws, so counts never show an undone state. (Fixes C-04, C-14.)

### 8.6 Corrections files (P-REV-6)

The review export is shrunk and signed (fix plan 4.3). It carries:
- `Record_Key`, `Run_ID` and `Signature`, where the signature is HMAC-SHA256(install secret, run ID | record key), first 16 hex characters
- the source system, Client_ID, source letter, file and row
- the Counted column, and the reasons
- the original and standardized values of the failing fields only
- the name fields, when Client_ID is blank or is itself failing, so the fixer can find the person

When the operator sends that file back:
- Each row is matched by Record_Key, never by position.
- Signatures are checked. A row with a missing or wrong signature, or from another installation, is refused with the reason "This row didn't come from this computer's review file."
- The original values in the file are checked against the record. Rows whose originals don't match are refused, with "This row has changed since the review file was made."
- Corrections are accepted only for the fields that failed. Any other changed column is refused and named.
- Each accepted correction sets the count status to "Counted, corrected from a corrections file" when the count checks now pass.
- Each correction goes to the internal audit log with the record key, the field names, a keyed hash of the old and new values, the reviewer's name and the corrections file name. It never logs the values.

(Fixes C-06, A-10.)

### 8.7 Reviewers and bulk accepts (fix plan 5.7)

- **Reviewer names.** When Fix problems first opens in a session, it asks for the reviewer's name, defaulting to the Windows login name from `getpass.getuser()`. Every decision stores the reviewer's name, and both audit logs record it. The name can be changed from the ledger footer.
- **Before "Accept all as they are" runs on a group:**
  - The screen shows five rows picked at random from the group. The pick is seeded by the decision ID, so it's reproducible.
  - The reviewer types the group's row count, and picks a reason from the fixed list. There's no free-text note on a bulk accept. Only Set aside's Other reason takes a note (section 8.1).
  - The typed count and the reason go to the audit.
- **Second sign-off.** A bulk accept over 200 rows, or a same-person group that joins more than 5 records, needs a second reviewer's name before it applies. The second reviewer types their name and confirms. The audit records both names.
- **Decisions by reviewer.** The internal audit log ends with a table of decision counts by reviewer and decision type.

### 8.8 Matching calibration (fix plan 5.6)

- **Where it lives.** Settings has "Measure matching." It's meant to run on the client's own computer with a real batch, because the pairs are client data.
- **Sampling.** The tool lowers the proposal line to a calibration floor of 40 points for this run only, which is never reported. It draws about 400 pairs spread across four score bands: 40 to 61, 62 to 79, 80 to 99, and 100 or more.
- **Labeling.**
  - Two staff label each pair on screen as Same, Different or Unsure, working apart under their own reviewer names.
  - The screen then shows the disagreements for them to settle together. Pairs that stay Unsure are dropped.
  - Staff can also enter about 50 known cross-system pairs by Client_ID, to measure what blocking misses.
- **The result** shows, for each band, how often Same was right, and how many known pairs were never compared. It suggests the proposal line that catches at least 98% of true matches, and confirms that automatic joins were right at least 99.5% of the time. Joe and the client agree the final thresholds, which the operator enters in Settings and the audit records.
- **Storage.** The labeled pairs are saved encrypted with DPAPI in `%LOCALAPPDATA%\Wholecount\calibration\`, as person keys plus score features with no names. They become a regression check on that computer: after a weight change, Settings runs them and shows whether accuracy dropped.
- **Reporting.** The printable summary adds a methods note with the measured rates and the calibration date.

---

## 9. Outputs

### 9.1 The output files

All files are written only when the operator presses Download and picks a folder, through the Windows save dialog.
- **Format.** Each file is CSV, Excel or JSON, chosen per file. The audit logs are always plain text, and the quality report is always CSV.
- **Synced and network folders.** If the chosen folder is inside a OneDrive, Dropbox, Google Drive or Box folder, or on a network path, an amber callout asks the operator to confirm: "This folder copies files to other computers. These files hold client data." (Fix plan 2.3 and 4.6.)

| File | Written | Rows | Columns |
| --- | --- | --- | --- |
| Unique_Clients | Always | One per master ID among counted rows | Master_ID, the person's name and address taken from their most complete record, Date_of_Birth if mapped, programs, systems, source records as letter, file and row, Match_Confidence |
| Unique_Clients_By_Program | Always | One per (master ID, program) | Master_ID, Program, source records |
| Final_Clean_Mapped | Always | Every counted row | Canonical and custom fields, Count_Status, Location_Status, Location_Confidence, districts, Source_File, Source_Row, Record_Key, Duplicate_In_File, Possible_Duplicate_Of. Latitude and Longitude only when "Exact coordinates, for internal use" is on (P-GEO-6). |
| Manual_Review_Needed | Always | Every row with an open problem | The signed, shrunk layout in section 8.6, with Counted (Yes or No) |
| Set_Aside_Records | Always | Every set-aside row | Record_Key, Source_File, Source_Row, the reason, and Kept_Record_Key for copies |
| Map_Counts | Always | One per (program, district type, district) | Counts with small cells blanked (P-GEO-6) |
| Map_Points | Only when switched on | One per counted, mapped person and program | Program and the moved point (P-GEO-7) |
| Internal_Audit_Log.txt | Always | One line per event | Section 9.2 |
| Shareable_Audit_Log.txt | Always | One line per event | Section 9.2 |
| Data_Quality_Report.csv | Always | One per source table | Rows received, counted, not counted yet, set aside, mapped, each problem kind's count, invisible characters removed, encoding used |

`docs/milestones/M09-outputs.md` defines every column exactly, and those definitions are binding. That includes Duplicate_In_File, Possible_Duplicate_Of, Source_File, and how Unique_Clients picks a person's name and address.

Unmapped columns never appear in any file (H10). Rows are ordered by normalized file name, sheet and row number, so exports are the same whatever order files were added in. (Fixes C-27.) Every column has a chip on Download, and the operator can switch columns off for the clean file. (Fixes C-26.) When example data was used, every file's first line or first row says PRACTICE (P-GEO-4). Map_Counts, Map_Points and the district columns aren't written in a practice run, because the sample reference gives made-up districts (fix plan 5.3). Download says why. "Always" in the table means every real run.

### 9.2 The audit logs

There are two logs (fix plan 4.5). Both are plain text, one event per line, with an ISO time, an event code, and H8-safe fields.
- **Internal_Audit_Log.txt** starts with the line "This log contains record keys and file names. Keep it inside the organization." It has a file legend that maps each source letter to its file name.
- **Shareable_Audit_Log.txt** has the same events with these differences:
  - Source letters only, with no file names and no legend.
  - No row numbers.
  - Each record key replaced by a second keyed hash: HMAC-SHA256(install secret, "share|" + record key), first 10 hex characters.
  - Reviewer names kept.

Events cover:
- files added, with name and fingerprint
- tables included and excluded
- header choices
- set-up changes
- every fill and correction, by record key and field name
- every decision, by record key and decision ID
- automatic joins, with the reason and master IDs
- program confirmations
- runs, with settings and backend
- confidence acknowledgments
- downloads, with the file names written, in the internal log only
- reviewer names and second sign-offs (section 8.7)

Neither log contains cell values or the install secret. A test scans both logs from a full session for every value in the test data and fails on any hit. A second test also scans the shareable log for every file name and Client_ID. (Fixes A-02, C-22.) There's no cap on how many decisions they record. (Fixes A-24.)

### 9.3 The printable summary

One page, shown in the app and saved as PDF (through `QPdfWriter`) or HTML through the save dialog. The screen and both files are drawn from one `SummaryDoc` model, so there's no browser engine. It shows:
- Goal 1 and Goal 2, ranges included
- the per-program table
- both balances
- "Counted, no usable address" and its breakdown
- the confidence level and reason
- the settings and backend
- the methods note, if matching was calibrated
- the sources by letter

File names are included only when the operator ticks "Include file names" before saving. It has no Client IDs, no master IDs and no person rows, and its copy says exactly that: "Counts only," or "Counts and file names only" when the box is ticked. (Fixes A-03.)

### 9.4 The receipt

After Download, the screen lists each file written, with its full path, row count, column count and the time. Nothing else was written, and the receipt says so. The operator can copy the receipt. It also goes to the audit, by file name.

---

## 10. Saved progress, set-ups and staleness

### 10.1 Saved progress

- It's on by default and can be switched off in a setting the "Your data" page links to.
- It holds:
  - the set-up: schema, steps, mappings, defaults, date orders, program columns and groups, run settings
  - every decision, by record key
  - each source's fingerprint, file name and system
- It never holds cell values, rows or the privacy key. Column names are kept, because mappings need them.
- It's saved after each command, encrypted with DPAPI for the current Windows user, under `%LOCALAPPDATA%\Wholecount\sessions\`.
- Saved progress older than seven days is deleted at launch, and the "Your data" page says so.

(Fixes A-04, fix plan 4.2.)

### 10.2 Resume

Resume asks the operator to add the same files again, because no rows are saved. Files are matched by fingerprint:
- **Same fingerprint:** everything is restored, including identity decisions and program groups. (Fixes A-08.)
- **Same file name, different fingerprint:** the screen says the file changed, then re-applies decisions by record key. Anything that doesn't fit goes to "No longer apply." Rows whose text didn't change keep their record keys, so their decisions still apply. (Fixes C-08.)

### 10.3 Set-ups

A set-up is the saved set-up without decisions or fingerprints, named by the operator. It's for next quarter's batch.
- **Stored** the same way, encrypted, in `%LOCALAPPDATA%\Wholecount\setups\`.
- **Exported** as plain JSON to a file the operator chooses, to move it to another computer. The export screen says what's in it: column names, steps, mappings, defaults and program names, with no client data. Column names are its only link to data.

### 10.4 Staleness

`session/staleness.py` holds the dependency graph:

```
sources -> tables -> steps -> mappings/defaults/date orders -> standardized rows -> checks -> geo -> copies -> decisions applied -> identity -> programs -> counts -> confidence -> exports
```

Every command declares what it invalidates. Stale artifacts show as "out of date" in the stage strip caption and the ledger, with "Process again." Results and Download are held while their inputs are stale, and the held caption says why. Counts never show stale numbers. (Fixes C-03, C-18, H13.)

### 10.5 The saved crosswalk (fix plan 5.4)

- **Off by default.** The organization turns it on in Settings after its data agreements allow linking systems (fix plan phase 7). Turning it on records the reviewer's name and the time in the audit.
- **What it stores.** `%LOCALAPPDATA%\Wholecount\crosswalk.db`, an SQLite file through the standard library `sqlite3`. It holds person keys, master IDs, same-person decisions and program groupings, each with the reviewer and time. It never holds names, addresses, Client_ID values or dates.
- **How it's protected.** Person keys are keyed hashes (section 5.1), so the file means nothing without the install secret. The secret should be backed up (section 5.1).
- **Each batch:**
  - Person keys the crosswalk has seen keep their master IDs.
  - Decided pairs are re-applied, and the "No longer apply" list shows any that conflict with new evidence.
  - New people get new master IDs.
  - Results says how many people were matched from earlier batches.
- **Removing it.** Settings has "Forget the saved crosswalk," which deletes the file after a typed confirmation.
- **The milestone file is binding.** `docs/milestones/M13-calibration-crosswalk.md` sets when the crosswalk is written (at Download) and what new evidence reopens a decided pair.

---

## 11. The interface

### 11.1 The boards and the style guide

- **The style guide is the authority on the look.** It's in `docs/context/design/style-guide/README.md`, with `tokens.json`.
- **The boards show the layout and copy of each stage.** They're in `docs/context/design/boards/`, with PNGs in `board-images/`. The table in `docs/context/START_HERE.md` maps board files to stages.
- **The boards predate some decisions, and this spec wins on these:**
  - the color rule on the older boards
  - the stage 02 name, which is now "Your columns"
  - the product name, which is now Wholecount
  - the progress and confidence elements in sections 11.6 and 11.7
- **The boards are HTML,** and the app is Qt Widgets. Match the regions, order, sizes, type, colors and copy. Pixel-identical isn't required. `tools/screens.py` renders each stage offscreen at 1440 by 980 and 1280 by 900 for Joe to compare with the boards at each milestone review.

### 11.2 Theme

- **QSS is generated from tokens.** `ui/theme/build_qss.py` turns `tokens.json` into QSS. It may run at startup or at build time, and a test checks that the QSS in use matches the tokens. Widgets get a `kind` property for their style (primary, secondary, quiet, held), so there are no inline colors.
- **Archivo is bundled.** Archivo 400, 600 and 800 (SIL Open Font License) ship in `ui/theme/fonts/` and load with `QFontDatabase.addApplicationFont`. The license file ships beside them. The fallback is Segoe UI.
- **Shape and color.** Zero radius, no shadows, one-pixel borders, and 3px rules on top or bottom only. The colors are blue for needs you, green for a person decided, amber for looks wrong, and gray for settled. No red.
- **Source marks.** A 16px ink square with a white letter, and 14px in table cells.

### 11.3 The frame

- **Top bar.** It's 48px, ink colored, with the mark, the wordmark WHOLECOUNT, and at the right: "Offline," the geocoder backend, and when progress was last saved. Under 1360px wide, Close Wholecount moves here.
- **Stage strip.** Nine items plus Undo, pinned, three lines each:
  - number and technical name
  - plain name
  - a live caption, which is data from the session, never fixed text

  It has four states: current, done with work, nothing to decide, and not yet. Stale stages show "out of date" in the caption. Under 1360px the names drop to 11.5px, Undo narrows to 150px, and the two longest names may wrap. It never scrolls.
- **Run ticker.** A slim line, 34px tall, directly under the strip. It appears only while something is running or after a run. Section 11.6 has the detail.
- **Ledger.**
  - **Layout.** A 280px column at 1360px and up. Below that, a 44px band under the ticker with four groups and a Details link that opens the column as a drawer.
  - **Sections.** This batch; Where they stand, with the stacked bar and the balance line; The two counts, with ranges; Confidence in this batch (section 7.4); Locations.
  - **Stage sections.** Some stages add their own: Tidy up, Match your columns and Programs, as the boards show.
  - **Before a run,** each section says in one sentence what it doesn't know yet.
  - **Footer.** The system check line, "What happens to your data," "Settings," the trust sentence, the reviewer's name, Close Wholecount and Start over. Settings opens a drawer like the "Your data" one. M10 builds it with the saved-progress switch, the reviewer name and the system check table. Later milestones add the secret backup, the saved crosswalk and Measure matching. The trust sentence reads: "Nothing leaves this computer. Client data is written only to the files you download." When saved progress is on, it adds: "Your decisions are saved, encrypted, never the data."
- **No sideways scrolling** at 1280px or wider. A layout test checks this at 1280, 1366, 1440 and 1920.

### 11.4 Shared controls

- **Buttons.** Primary, secondary, quiet and held. A held button is never just disabled. It has a caption saying what releases it.
- **Callouts.** A white card with a 3px top rule in the hue of its kind. It has a title, one line, and the action on the right. Inside an amber callout the button is still blue.
- **Tags.** NEEDS YOU is solid blue. Confirmed is green tint. Neutral facts are an outline.
- **Grids.** `QTableView` with a model. Each grid keeps its scroll position and page across a redraw. Opening a different stage starts at the top.
- **Two-step header.** In Fix problems only.
- **Numbered section heads.** In Programs.

### 11.5 Stages

Each stage module builds the screen from its board and the rules in this spec. The milestone files list each stage's contents and every control in the feature ledger, from `docs/context/project-docs/crosswalk-redesign-decisions.md`. Every feature in that ledger has a home, and the parity checklist test (section 13.4) lists them. Stages 02 (Your columns), 06 (Process) and 09 (Download) have no board, and their milestone files specify them.

### 11.6 Progress (H14)

The prototype settled this. Its HTML is in `docs/context/design/prototype/progress-confidence.html` (open it in any browser and use the arrows in the bottom bar), and the milestone text is complete without it. Joe's copy is at https://claude.ai/artifact/G1JFyQQYpT3dSDezBGrf2Z.

**11.6.1 What the operator sees.**
- **On every stage, the run ticker** under the strip shows the current step, like "Step 4 of 7 · Placing addresses · 4,210 of 7,412." Beside it, a few words on what's running, like "Looking up addresses, [A] clinic_export.csv." A 2px bar along its bottom edge shows overall progress. "All steps" opens a dropdown with every step's bar. The dropdown sits over the content and doesn't push it.
- **On Process,** the full run panel sits at the top of the stage. It has one row per step: the name, a count like "852 of 6,084," a bar, and one line of message. Finished steps show what they found, like "6,084 passed, 1,232 need a decision, 96 set aside."
- **Stage underlines.** The stage strip's 3px underline for each stage that owns running steps fills as those steps run. Tidy up owns tidying. Process owns reading, checking and placing. Fix problems owns copies. Results owns matching and counting.
- **The screen stays readable while a run goes.** Every control that would change data is held, with the caption "Held until the run finishes. A change now would not apply to this run." Navigation, scrolling, Show data, help and "What happens to your data" stay live.
- **After a run,** the ticker reads "Last run finished in 30.5 s · 7 steps, nothing written to disk," with "Show the log." The Process panel folds to one line with the same text. The log lists each step with how long it took and what it found.
- **Cancel.** A running job can be cancelled from the ticker or the panel. Cancelling leaves the session exactly as it was before the run started.

**11.6.2 Which actions report progress.** Each action has its own step list:

| Action | Steps |
| --- | --- |
| Adding files | Reading files, Finding tables |
| Process, and the fast path | Reading files, Tidying up, Checking every row, Placing addresses, Finding copies in each file, Matching people across files, Counting and balancing |
| Preview the counts (Programs) | Checking every row, Matching people across files, Counting |
| Look up all N (Fix problems) | Looking up addresses |
| Download | Writing files, one bar per file |
| Resume | Reading files, Re-applying decisions |
| Applying a corrections file | Reading the corrections file, Checking signatures and originals, Re-applying decisions |
| Measure matching (section 8.8) | Matching people across files, Drawing pairs |
| Back up the install secret (section 5.1) | Protecting the backup |

Any action under 300 ms shows nothing.

**11.6.3 How it's built.**
- The engine takes a `ProgressSink` with these methods:
  - `begin(step_id, total, unit)`
  - `advance(n, message: ProgressMessage)`
  - `end(found: ProgressMessage)`
  - `cancelled() -> bool`
- **`ProgressMessage`** holds a message ID from the copy registry plus parameters of only three types: `SourceRef` (letter and file name), `int` counts, and `StepRef`. It can't hold a free string, so a client value can never reach the screen's progress line or a log (H8). A unit test proves the type rejects strings.
- **Speed.** The worker posts updates at most every 100 ms, and at least every 250 ms while work continues. Steps report at least per 200 rows, or per file for reading.
- **Bars only move forward.** The UI rejects a smaller value.

**11.6.4 Step durations** in the log come from a monotonic clock, rounded to tenths of a second.

### 11.7 Confidence on screen

- **Ledger section "Confidence in this batch":**
  - the level word (ink for High, amber-700 for Medium and Low)
  - the reason sentence
  - a "How this is worked out" link that opens the three measures and what High needs
  - before a run: "Worked out from the checks once the run finishes. It says why, in one line."
- **Process,** after a run: a callout with the full detail. It's ink-ruled for High and amber-ruled for Medium and Low.
- **Low:** the acknowledgment tick sits in the callout and in the ledger. Download's held caption reads "Download is held until the Low confidence is ticked as seen."
- **Results:** each pair shows Certain, Likely or Possible with its evidence. The Locations bars show High, Low and Not placed.
- **Fix problems:** each row with a location shows its location confidence and reason.

### 11.8 What happens to your data (R11)

- **A line on every stage.** Each stage shows one line, under its title, with three parts: Reads, Changes and Writes. The text is in the copy registry, and each part has a claim test.

| Stage | Reads | Changes | Writes |
| --- | --- | --- | --- |
| Add your files | the files you add, once | nothing in your files | nothing to disk |
| Your columns | nothing from your files | only the list of fields | nothing to disk |
| Tidy up | the tables you included | nothing in your files; steps add new columns in memory | nothing to disk |
| Match your columns | column names and sample values | nothing in your files | nothing to disk |
| Programs | the program columns you chose | nothing in your files | nothing to disk |
| Process | the tables you included | nothing in your files | nothing to disk until you download |
| Fix problems | the rows that need a decision | only what you decide, and it goes to the audit log | nothing to disk |
| Results | the counted rows | nothing | nothing until you save the printable page |
| Download | the results | nothing | only the files you choose, in the folder you pick |

  If saved progress is on, every line where Writes says "nothing to disk" adds "except your saved decisions, encrypted," and that's claim-tested.
- **The "Your data" page** opens from the ledger footer as a drawer. It has a three-box diagram:
  - **Your files:** opened once, never changed.
  - **Memory on this computer:** every step works here, and nothing is sent anywhere.
  - **The files you download:** written to the folder you pick.

  Then a "Saved progress" paragraph with its switch, and a "Never" list:
  - sent over the internet
  - shown to or decided by AI
  - written to a log
  - kept after you close, unless you saved progress
- **The pre-run summary,** on Process before the run, says in four lines what the run will do. It names the geocoding backend, and says whether exact coordinates or Map_Points will be offered on Download.
- **The receipt** is shown after Download (section 9.4).

### 11.9 Accessibility

- Text contrast is at least 4.5:1.
- Every control is reachable by keyboard, with a visible focus outline.
- Hit targets are 36px or taller.
- Every icon-only control has an accessible name.
- Progress announces step changes to screen readers through Qt accessibility events.

---

## 12. Offline and AI-free guarantee

The research behind this section is in `docs/research/offline-enforcement.md`, which has citations and tested code. Follow its "Recommended design" (R1 to R6), with the package renamed to `wholecount`.

### 12.1 Layers, strongest first

1. **Windows Firewall.** The installer adds outbound and inbound block rules for the exact path of `Wholecount.exe` and removes them on uninstall (research R5, section 5).
2. **Not in the build.** The PyInstaller spec excludes these and fails the build if any appear in the table of contents (research R4):
   - socket, `_socket`, ssl, http.*, urllib.request, ftplib, smtplib, asyncio, multiprocessing
   - `PySide6.QtNetwork` and every web, network and bearer Qt module or plugin, plus `Qt6Network.dll`
3. **Libraries get local file objects only** (P-READ-10). There are no URL strings, `QDesktopServices` is never called, and `openExternalLinks` is always false.
4. **In-process guard.** `wholecount/guard/` installs a fail-closed `sys.addaudithook` as the first statement of `__main__.py` and in the PyInstaller runtime hook (research R2 and R3). It denies:
   - socket events, DNS and `urllib.Request`
   - http.client, ftplib and smtplib
   - subprocess, `os.system` and `os.startfile`, except the one allowlisted "open the source file" call (section 12.6)
   - UNC and WebDAV paths
   - first imports of network modules
   - ctypes loads outside an allowlist (DPAPI's crypt32, Geosupport's DLLs)

   The guard is defense in depth, not a sandbox, and the research says so.
5. **Supply chain.** Use `PySide6-Essentials`, not `PySide6`. A hashed lockfile (`requirements.lock`) is installed with `--require-hashes --no-deps --only-binary=:all:`. A test keeps the approved package set exact and the forbidden list out (research section 8).

### 12.2 No AI

No AI SDK may appear in the lockfile, source, or build. The forbidden list includes openai, anthropic, google-generativeai, transformers, torch, tensorflow, onnxruntime, llama-cpp, langchain and ollama. No model files may appear either: no .onnx, .pt, .pth, .safetensors, .gguf, .bin over 1 MB, or .h5. Static and bundle tests enforce both.

### 12.3 The old build's network paths, all removed

These are the old build's network paths, and none of them survive:
- first-launch `pip install`
- `run.bat` and `run.sh`
- the Streamlit server
- the FastAPI server and its port
- `webbrowser.open`
- the launcher's port probing and process killing (A-17, A-20)
- the Google Fonts link

### 12.4 Tests

All of the research's test inventory (section 7.1) is implemented:
- guard runtime tests
- static scan
- lockfile checks
- import graph
- bundle tests
- PE import scan
- Windows-only firewall probe
- installer rule check
- Windows Sandbox offline run

### 12.5 What can't be guaranteed

These go in the README as written in the research's Open risks:
- An administrator can remove the firewall rule.
- A managed computer can ignore local rules.
- C and C++ code isn't seen by the audit hook. That covers Qt, libxml2 and the Geosupport DLL.
- A mapped network drive looks like a local path.

### 12.6 The two allowed calls out of the app

**Open the source file.** The operator can ask Windows to open one of their own added files in its default app, for example Excel. It works like this:
- The only `os.startfile` call in the code base is in `wholecount/ui/shell.py`, and the static scan exempts that one file.
- Before calling, `shell.py` registers the exact path with `guard.allow_open_file(path)`.
- The guard permits that one `os.startfile` event for that path, once, and denies everything else.
- The path must be one of the files added to this batch, and the operator confirms first.

**Windows file dialogs.** The dialogs can browse anywhere the operator can, including network drives. A file picked on a network path shows an amber note: "This file is on a network drive. Wholecount reads it like any file, and sends nothing back."

---

## 13. Testing

### 13.1 Layout

```
tests/
  unit/            per module, fast
  rules/           one test file per P-rule group, cases named after rule IDs
  audit/           one test per High and Medium audit finding: test_B13_day_month_swap.py and so on
  golden/          the proof workbook, ported, with expected outputs as fixtures. Where this spec changes a rule, the ported expectation follows the spec, and golden/CHANGES.md lists every sheet and row whose expected value changed and the rule that changed it (for example sheets 02, 06 and 17).
  invariants/      hypothesis property tests: balance, determinism, record-key stability
  offline/         section 12.4 (Linux)
  ui/              pytest-qt, QT_QPA_PLATFORM=offscreen: screens build, held states, progress, layout widths
  copy/            every claim ID has a test, no em dashes, American spelling list, no exclamation marks
  acceptance/      full runs: sample data both routes, the 19,000-row set
tests_windows/     firewall probe, installer rules, Geosupport adapter on a real install, DPAPI round trip
```

### 13.2 Hard rule tests

Each hard rule H1 to H16 has at least one named test, wherever it lives. `tests/HARD_RULES.md` maps each rule to its tests, and a test fails if any rule has none.

### 13.3 Audit regression

Every High and Medium finding in `docs/audit/` gets a test named for its ID, built from the finding's own input and expected output. The finding's script in `docs/audit/*-scripts/` is a worked example to port, not a test to run. Low findings get a test when the milestone that touches them makes it cheap. `tests/audit/INDEX.md` lists every finding ID with its test or the reason it has none.

### 13.4 Parity checklist

`tests/ui/test_feature_ledger.py` lists every feature in the decisions doc's feature ledger, the build brief and the old `test_parity.py`, with the screen and widget that provides it. A missing feature fails.

### 13.5 Acceptance

- The five sample files go through all nine stages twice, once by the fast path and once stage by stage. Both routes must give byte-identical output files, apart from the audit logs. The audit logs must match once timestamps and the events that only one route makes are removed. M15 lists those route-only event codes, such as the confirmations a person makes stage by stage.
- The 19,000-row set goes through Process within the budget in section 15.
- An independent pandas computation of Goal 1 and Goal 2 from the exports must match Results.

### 13.6 Windows

`tests_windows/` runs on a GitHub Actions `windows-latest` runner and on Joe's machine at milestone reviews. GitHub-hosted Windows runners are documented to run with administrator rights, and M14 confirms it on the first run. Windows Sandbox can't run on hosted runners, so the offline Sandbox run is a scripted manual check Joe does. The runner builds the PyInstaller folder and the installer, installs them, runs the bundle and firewall tests, and uploads the installer as a workflow artifact. Geosupport tests run only on a machine with Geosupport Desktop Edition installed, which means Joe's. They skip with a clear message elsewhere.

---

## 14. Packaging, install and signing

- **Build.** `build/wholecount.spec`: one folder, `Wholecount.exe` as a windowed app with no console, the excludes and build gate from research R4, the runtime hook from R3, Archivo and its license, the NYC ZIP table, district files and copy registry as data, and the PySide6 LGPL notice and every third-party license in `licenses/`.
- **Installer.** `installer/wholecount.iss`, built with Inno Setup 6:
  - per-machine install to Program Files, needing admin once
  - a Start menu shortcut
  - the firewall rules from research R5, removed on uninstall
  - checks for Geosupport Desktop Edition and, if it's missing, says plainly what that means (addresses won't be placed until it's installed or a reference file is added)
  - no internet use, and no downloads during install
- **Signing (free route).**
  - `tools/make_cert.ps1` makes a self-signed code-signing certificate.
  - `tools/sign.ps1` signs `Wholecount.exe` and the installer with signtool.
  - `docs/IT_TRUST.md` tells a client's IT how to trust the certificate through Group Policy or Intune, as Trusted Publisher and Trusted Root. Whether SmartScreen and Smart App Control then accept it is marked "to confirm on a managed machine," because the research didn't verify it.
  - On unmanaged machines the warning stays, and the docs say so.
  - The certificate's publisher name is a setting (Q6). Wholecount supports Windows 10 22H2 and Windows 11, 64-bit only.
  - The signing step reads its certificate from a setting, so moving to Azure Artifact Signing later is a configuration change. About $9.99 a month, US individuals qualify. `docs/SIGNING.md` covers the switch.
- **Geosupport.** It isn't bundled. The client installs NYC Geosupport Desktop Edition separately. The app finds it through the `GEOFILES` environment variable and the standard install path, and shows its release in the top bar and the audit (fix plan 5.3).

---

## 15. Performance budgets

These are measured on Joe's Windows machine at the M15 review, with Geosupport installed.

| Action | Budget |
| --- | --- |
| Start to first screen | 3 s |
| Add 15 files, 19,000 rows | 10 s |
| Process 19,000 rows with Geosupport | 90 s |
| Any click that doesn't start a job | 200 ms to redraw |
| Preview the counts, 19,000 rows | 10 s |
| Download all output files | 10 s |
| Memory, 19,000-row batch | under 1.5 GB |

Linux CI tracks the same numbers on the fake geocoder, as a regression alarm, not a pass or fail.

---

## 16. Decisions log

Joe's answers, from the planning chat on 2026-10-30.

| Topic | Decision |
| --- | --- |
| Rebuild | Rewrite everything. The behavior spec, proof workbook and old tests are the answer key. |
| Platform | Windows only |
| Stack | Python with a native Qt window and no browser engine |
| Install | Windows installer that adds a firewall rule |
| Fix plan | Build in all 24 items from the start |
| Signing | Free route: self-signed with IT trust. Azure Artifact Signing later as a switch. |
| Progress | One bar per step with a count. A few words per bar. The screen stays readable, with data controls held. Bars fold into a log after the run. |
| Progress placement | The run ticker under the strip on every stage, plus the full run panel on Process (prototype variant C plus B). |
| Confidence | Batch level in the ledger, plus each same-person match and each location. Word plus reason. Low holds Download until ticked. Thresholds 95 and 80, tune later. |
| Confidence colors | High in ink. Medium and Low in amber. Never green. |
| Data clarity | A line per stage, the "Your data" page, a summary before Process, and a receipt after Download |
| Color rule | Applies to every screen |
| Stage 02 name | Your columns |
| Product name | Wholecount, a working name chosen from round 2 of the name research (`docs/research/rename.md`). Joe had no preference, so this is the recommended pick, and Joe can veto it. |
| Plan shape | Spec plus milestone files. Code stops after each milestone for review. |
| AI | None anywhere |
| Streamlit | Dropped |
| Counting (v1.1, fix plan 5.1) | A row counts on its person data alone. Address problems affect the map, never the count. |
| Keys (v1.1, fix plan 5.4) | Keyed hashes with an install secret. Record keys for rows, and person keys for people across batches. Letters are display only. |
| Coordinates (v1.1, fix plan 4.4) | Out of the clean file by default. Map_Counts always, with cells under 11 blanked. Map_Points optional, with a per-building offset. |
| Audit (v1.1, fix plan 4.5) | Internal and shareable logs |
| Review file (v1.1, fix plan 4.3) | Shrunk to failing fields and signed. Corrections only to failing fields. |
| Saved crosswalk (v1.1, fix plan 5.4) | Built, and off until the organization turns it on |
| Calibration (v1.1, fix plan 5.6) | Built into Settings, run on the client's computer |
| Reviewers (v1.1, fix plan 5.7) | Named on every decision. Bulk accepts need a typed count and a reason, and a second sign-off over 200 rows. |
| Export formats | CSV, Excel or JSON per file. JSON is kept for parity with the old build. |

---

## 17. Open questions for Joe

Code builds the default and flags each one in the milestone report, so Joe can change it.

- **Q1. Clients with no fixed address.** Settled by fix plan 5.1. They count, and they aren't mapped. This is kept here only so the change from the old build is visible.
- **Q2. Saved progress default.** Default: on, encrypted, seven-day clean-up. The alternative is off until the operator turns it on.
- **Q3. Real reference file.** Without Geosupport, which address file should the fallback use? Default: none bundled. The operator adds NYC's address points file, and `docs/REFERENCE_DATA.md` says where to get it and how to load it.
- **Q4. Product name.** Default: Wholecount.
- **Q5. Excel passwords on outputs** (fix plan 4.3 step 5). This needs msoffcrypto-tool and the cryptography package, which aren't in the approved set. Default: not included. The review file is signed instead. If Joe approves the packages, it becomes an option on Download.
- **Q6. Publisher name on the signature.** Default: "Joe Buzzetta". Joe may want a business name.
- **Q7. "Set a field on all selected" and "Reject"** from the old boards. Both are dropped, because they break H7. If Joe wants a bulk change back, it has to come in through set-up, as a per-source default, or through a corrections file.
- **Q8. Turning on the saved crosswalk.** It needs the client's sign-off on its data agreements (fix plan phase 7). Default: off.

---

## 18. Glossary

| Plain | Technical | Meaning |
| --- | --- | --- |
| Add your files | Sources | Files added and the tables found in them |
| Your columns | Schema | The fields every file maps onto |
| Tidy up | Prepare | Steps that add columns |
| Match your columns | Map | Field-to-column matching per table |
| Process | Run | The pipeline over every included table |
| Fix problems | Review | Open rows grouped by cause, then the queue |
| Results | Summary | Goal 1, Goal 2, open pairs |
| Download | Export | The output files and the receipt |
| Set aside | Segregated | Out of the clean list, kept and recoverable, with a reason |
| Copies | Duplicates within a file | Rows in one table a person decided are one client |
| May be one person | Proposal | A same-person pair awaiting a decision |
| Look up from the street | Fill | A value derived from the row's own address |
| Set-up | Configuration | Everything saved for reuse except decisions |
| Master ID | Master identity | One ID per resolved person, the unit of Goal 1 |
| Record key | | A row's stable identity (section 5.1) |
| Source system | | A group of files that share one identifier space (section 4.2) |
| Run ticker | | The progress line under the stage strip |
