# Crosswalk, described for an AI

Sep 28, 2026 · @Joe Buzzetta

## What it is

Crosswalk is an offline desktop tool that takes the client lists a New York City human-services nonprofit exports from many separate systems, turns them into one clean master list, and produces two numbers: how many unique people the organization serves in all (Goal 1), and how many unique people it serves in each program (Goal 2). It was built for St. Nicks Alliance, whose client records live in roughly 12 to 20 systems (ETO, property management, DYCD exports, partner spreadsheets), each with its own identifiers, column names, address formats and program spellings. Every number it produces can be traced back through an audit trail that names rows by identifier and never by value.

It does four kinds of work, in this order: it standardizes every file into one schema and cleans each row; it places every address on the map through Geosupport, the City's own address engine, and assigns state Senate, Assembly and Council districts; it finds duplicates within a file and across files; and it resolves which records across systems are the same person, producing one master identity per person. A human reviewer decides everything the rules cannot settle, and the tool is built so that this review is done in batches, by cause, rather than one row at a time.

The operator is a data or program staff member at the nonprofit, not an engineer. The interface uses plain words by default (a Guided mode) and precise terms on request (an Advanced mode); only the words differ. The consultant who built it is Joseph; the client contact is Stephanie. The product's current version string is 2026.09.17. The product is named Crosswalk, and every file, launcher and document uses that name.

An AI reading this should treat the product as a deterministic rules engine with a human in the loop, not as a data-cleaning heuristic. Every transformation is a written rule listed in this document or in the generated technical reference (`docs/TECHNICAL.md`); there is no model, no fuzzy merge, and no network call anywhere in the processing path.

## Hard rules

These are invariants. Code or behavior that breaks one is a bug, and any change an AI proposes must keep all of them.

| Rule | What it means in practice |
| --- | --- |
| Offline | No network call in the processing path. Geocoding runs locally through Geosupport or a local reference file. The only internet use is the one-time package install on first launch. |
| Deterministic | Same input and settings give the same output. No model, no learned weights, no randomness except the privacy jitter, which is seeded (default seed 1337). |
| Lossless | On every run, clean rows + review rows + set-aside rows = input rows. The server asserts this (`_reconciliation`) and refuses to report counts that do not add up. Rows are set aside, never deleted. |
| Nothing merged on a guess | The engine collapses records only where the same identifier appears with identical data in one system, or where name, date of birth and address all agree at once. Everything weaker is proposed to a person with its evidence. Fuzzy matching is used only to suggest, never to merge. |
| Originals preserved | Every tidy-up step adds columns and never overwrites. The value as entered stays on the row and in the audit. Uploaded files are kept as bytes so a reviewer can open the original. |
| PII-safe audit | The audit trail and the printable summary carry identifiers, row numbers and column names only. Never a name, address or value. Saved set-ups and saved sessions hold no client data. |
| No per-value editing | The review screens offer only changes that are safe at scale: fills derived from the row's own address, keeping one row of a group of copies, accepting or setting aside. A reviewer cannot type a new value into a cell. Anything else is fixed at the source and reloaded. |
| Nothing written until asked | Output files are written only when downloaded. Processing holds everything in memory. |
| Plain words | Guided mode uses no jargon; Advanced mode uses precise terms. Only the words differ, never the behavior. No em dashes anywhere in the product or its documents. |

## Inputs

The tool accepts `.csv`, `.tsv`, `.xlsx`, `.json` and `.xml` files, several at once, of any size the machine's memory allows (batches of about 19,000 rows across 10 to 20 files are the working case). Every value is read as a string; nothing is coerced on the way in, so a ZIP of `07030` keeps its leading zero and a date keeps the form it was typed in until the schema types it.

**Tables within files.** A sheet is not assumed to be one table. `table_detect.detect_in_grid` splits a sheet on blank rows and columns into separate blocks, so a list of people and a summary table pasted beside it become two tables. Each table gets a stable key of the form `file :: sheet :: A1:H63` (the range in A1 notation). `classify_table` labels each block as records (has person and address fields), summary (totals, counts, headings) or unknown, and summary tables are unticked by default. Nested JSON and XML are flattened to rows first.

**Header row.** `detect_header` decides whether the first row of a block is column names. The operator can choose a different row under Show data on the files stage; rows above it are dropped. `header_looks_wrong` flags a choice that looks wrong: a row with most cells empty (a title), a row of numbers or ZIPs (data), two columns that would share a name, no header chosen when one of the first six rows plainly holds names, or a header with the same cell-by-cell shape as the row beneath it (a record, not names). Choosing a header row includes the table.

**What is proposed on upload.** For every table the tool proposes tidy-up steps (`auto_prep_ops`): a jammed-address split when one column holds street, unit, city, state and ZIP together; a jammed-name split when one column holds a whole name; and nothing else unless a person adds it. Proposals are shown with the evidence that triggered them and can be removed.

**What is rejected or held.** A file that cannot be parsed is reported by name and skipped. A table with no rows is skipped. A re-uploaded `Manual_Review_Needed` file is recognized as a corrections file and applied as corrections rather than loaded as a source. Nothing else is rejected; a table missing a required column is loaded and blocks processing at the matching stage with the file and field named.

**Sensitive columns.** Columns whose names suggest sensitive personal data (social security number, gender, race and the like) are pointed out on the files stage so they can be excluded from the clean output; the tool never needs them.

## The canonical schema

Every file is mapped onto one set of fields. The nine built-in fields are the `MASTER_COLUMNS`; Program is a custom field that ships in the default schema because both counts depend on it. The operator can add further custom fields with a type, and a date of birth is the one worth adding, since it strengthens identity resolution considerably.

| Field | Type | Required | Rules applied to it |
| --- | --- | --- | --- |
| First\_Name | str | yes | cleaned; digits flagged as possible column misalignment |
| Middle\_Initial | str | no | reduced to one letter |
| Last\_Name | str | yes | cleaned; digits flagged |
| Client\_ID | str | yes by default | the source system's identifier; the operator may relax the requirement per batch, and the fast path offers a one-click relax when a file lacks it |
| Address\_1 | str | yes | street; a trailing unit is moved to Address\_2 |
| Address\_2 | str | no | unit; de-duplicated against a unit found in Address\_1, flagged when they disagree |
| City | str | yes | filled from the ZIP when blank; a borough that contradicts the ZIP is flagged; neighborhoods fold to their borough |
| State | str | yes | written as NY; anything else flagged |
| Zip | str | yes | five digits; ZIP+4 reduced; anything else flagged |
| Program | str (custom) | no | cleaned; filled from a per-source default when blank; harmonized through the program alias map |

Custom fields carry a `dtype` of `str`, `int`, `decimal`, `date` or `bool`, an optional default, and a required flag. A typed value is stored in its standard form (`normalize_typed_value`), so a date written `3/15/2024` in one export and `2024-03-15` in another end up identical; a value that does not parse as its type fails the row's check with the field named.

**Matching columns to fields.** `guess_mapping` proposes a source column for each field by exact name, then by whole-word token. A real source column beats a column a split step derived for City, State and Zip; for Address\_1 a `_street` column beats a jammed original; a column named `Zip_calculated` wins for Zip because a person calculated it on purpose; identifier-named columns are never taken as Program. Every matched column is then checked against its values by `column_check.check_mapping`, which warns when a column matched to street holds units, dates or phone numbers, when Program holds codes, when Zip holds four-digit values, when one identifier is shared by many rows, and names the column that would fit. Warnings never block; a missing required column does.

**Per-source defaults.** For one table alone, a value can be set for any field wherever that field is blank. It never replaces a value the file supplied, it wins over a schema default, and every use is written to the audit on the row. Program is the field this matters most for: a file with no program column gets the program the person named, on every row.

## The ten stages

The interface is a fixed sequence of stages, numbered 0 to 9. A stage unlocks the next when its gate is met; every stage already reached can be revisited, and a change upstream invalidates what depends on it (a changed mapping clears results, a changed grouping marks the program preview stale). The Guided name is first, the Advanced name in brackets.

| # | Stage | What happens | State it changes | Gate to continue |
| --- | --- | --- | --- | --- |
| 0 | Check this computer | Python version, packages, Geosupport presence, reference files. Lists saved sessions that can be resumed. | none | always open |
| 1 | Add your files (Sources) | Upload, table detection, table kinds, header row choice, include or exclude, per-table Show data. Offers the fast path (Skip the steps) and saved set-ups. | `uploads`, `tables`, `frames`, `blocks`, `header_row`, `included`, proposed `ops` | at least one table included |
| 2 | Set up your columns (Schema) | The canonical schema; add custom typed fields; relax a required flag. | `schema` | always |
| 3 | Tidy up (Prepare) | Tidy-up steps per table: clean, split by delimiter, split jammed address, split jammed name, calculated ZIP column. Each adds columns only. | `ops` | always |
| 4 | Match your columns (Map) | Field-to-column matching per table, value checks with warnings, per-source defaults, confirmation. | `map_ov`, `confirmed`, `source_defaults` | every required field matched on every included table |
| 5 | Programs | Which column carries the program per file; grouping of spellings; preview of both counts. Edits are local until Apply. | `program_groups`, `program_aliases`, `program_preview` | same gate as stage 4 |
| 6 | Process (Run) | `run_pipeline` over every included table in a worker thread; progress per file. | `results`, `rid_index`, `run` | a completed run |
| 7 | Fix problems (Review) | Failed rows grouped by cause; diagnosis; batch fills; duplicates within a file; group decisions; the row-by-row queue. Decisions are chosen locally and applied together. | `actions`, `queue_edits`, `dup_decisions` | always (rows may remain in review) |
| 8 | Results (Summary) | Identity resolution; Goal 1 and Goal 2; open pairs to decide; per-program bars; printable summary. | `identity`, `id_decisions` | always |
| 9 | Download (Export) | Output format and columns; the seven output files; the audit trail; saved set-ups. | `fmt`, `cols_off` | end |

**The fast path.** From stage 1, one button (`POST /api/express/run`) does stages 3 to 6 with the tool's own proposals and lands on stage 7. `express_check` first lists blockers (a required field with no matched column, which stops it) and warnings (a matched column whose values look wrong, which the person can override with `despite_warnings`).

**Undo.** Every set-up change takes a snapshot first (`_snapshot`), and the menu offers to undo the last one by name. Review decisions have their own undo. Loading a saved set-up is undoable.

## How one row is transformed

`app.transform_row` turns one source row into one master record, in this exact order. Every fix is recorded on the record as a flag with a scenario label and a message, and written to the audit by file, row and identifier. A failed check adds the row to `__errors__`, which sends it to review; a fix or a note does not.

1. **Read and clean.** Each mapped column is read through `clean_cell`: placeholders such as `NULL`, `N/A`, `None` and a lone dash become empty; tabs, repeated spaces, zero-width and control characters are removed; smart quotes become plain ones; apostrophes, periods and hyphens are kept.
2. **Summary rows.** A row that is a total, a heading or bare numbers (no name and no address, or a name field holding words such as Total) is flagged as a summary row and returned early. It joins no other group and is never counted as a person.
3. **Defaults.** A blank built-in field takes the value set for this source first, then the schema's default. Each fill is recorded once per field with its origin.
4. **Names.** A middle initial is reduced to one letter. Digits in a first or last name are flagged as possible column misalignment. Casing is preserved unless a clean step asked for a name-aware title case (which keeps DiNapoli and O'Brien).
5. **Address lines.** A trailing unit on Address\_1 is moved to Address\_2 (`_split_unit`). If both lines carry a unit and they agree, the duplicate is dropped; if they disagree, the row is flagged. Words such as Rear, Front and Gar are ignored for geocoding only; the stored value keeps them.
6. **ZIP.** ZIP+4 is reduced to five digits. Anything that is not five digits after cleaning fails the check with the reason (blank, four digits, letters).
7. **City.** A blank city is filled from the ZIP's borough, recorded. A neighborhood name folds to its borough, from a fixed list of 114 (Woodside, Cambria Heights, Richmond Hill and the rest). A city within 80 of a borough name on the similarity score is read as that borough. A recognized borough that contradicts the ZIP is flagged as a conflict. An unrecognized city with a valid ZIP is replaced by the ZIP's borough and recorded; with no valid ZIP the row fails with the city named.
8. **State.** Any spelling of New York becomes NY. Any other state fails the check.
9. **Custom fields.** Each is cleaned, filled from the per-source default then the schema default, typed and validated. Program goes through the alias map so grouped spellings are stored under the canonical name, with the original kept and the substitution flagged.
10. **Corrections.** If a corrections file or an in-app correction touched this row, a note names the columns replaced, and the row is validated again like any other.
11. **Duplicate marks.** Marks set by `dedupe_rules.apply_decisions` are honored: a row a reviewer confirmed as a copy is flagged with the row it copies and sent to the set-aside group.

After all rows: Tier 1 duplicates (same identifier with identical name, address, ZIP and program in one file) keep the first and set the rest aside; Tier 2 pairs (same person key across files) are noted, never merged; geocoding and districts run; jitter is applied to stored coordinates only. The record carries `__source_file__`, `__source_row__`, `__errors__`, `__flags__`, `__program__` and `__custom__` alongside the schema fields.

## Address parsing

`split_jammed_address` takes one cell that may hold a whole address and returns street, unit, city, state and ZIP. It works from the right, so the parts with the most certain shape are taken first, and anything it cannot attribute stays in the street so no data is lost. Dashes, slashes, semicolons, colons and pipes used as separators are treated as commas first (`_normalize_separators`).

1. **ZIP** at the end: five digits, or ZIP+4 reduced to five.
2. **State** at the end: NY, N.Y., New York or New York State. No other state is recognized, so a street type such as St is never mistaken for a state. A street that contains New York, such as 100 New York Ave, is untouched because the state must be the last token.
3. **City.** With commas, each segment is judged for what it is: the first is the street; a segment that is a unit is the unit wherever it sits, before or after the city; the city is the last segment that is not a unit, and if there is none the city is left blank for the ZIP to fill. Without commas, and only when a ZIP or state was found, the last one to three words are matched against the boroughs and the neighborhood table.
4. **Unit.** A trailing unit is peeled off the street into Address\_2.

**What counts as a unit.** A unit word (apt, apartment, suite, ste, unit, fl, floor, rm, room, bldg, building, dept, space, lot, trailer, hangar, slip, pier, stop, ph, penthouse, bsmt, basement, rear, front, ground, lobby, mezzanine) followed by a designator; a hash followed by a designator; an ordinal followed by floor (2nd Floor, 4th Fl); or a bare designator right after a street-type word (117-19 45TH AVE 14A, 45 Ocean Ave 2B). A designator is a number then up to two letters with an optional space or hyphen between them (10R, 10 R, 18L, 12-B), a letter then a number (B-12), or a hyphenated code, and it must contain a digit except for a lone letter after a hash (#B). The designator may be jammed onto the word (APT18L) or follow a hash and colon (Apt#: 11T).

**Traps that must not split.** Because a designator needs a digit, a street named Apartment Way, Unit Ln, Suite Drive, Stop St or Penthouse Rd stays whole. Because the bare-designator rule requires a street-type word before it and the digits-then-letter shape, Avenue U and Route 9 stay whole. Front St and Rear St stay whole because the unit words Front and Rear are recognized only as a whole segment or a trailing token, not as part of a street name. Hyphenated Queens house numbers (40-22 24th St) are never read as a designator.

**Worked examples.** `117-19 45TH AVE, 14A, QUEENS, NY 11355` gives street 117-19 45TH AVE, unit 14A, city Queens, ZIP 11355. `111 Test St, Apt. 4, NY, 11201` gives unit Apt. 4 and a blank city, which the ZIP fills as Brooklyn. `67 Franklin Avenue Apt. 10 R` gives unit Apt. 10 R. `111 Test St, Apt. 4, Brooklyn, New York, 11201` gives city Brooklyn and state NY. Every one of these is pinned in `tests/test_crosswalk_api.py` and on the jammed-address sheet of `proof/Proof_Workbook.xlsx`, which is both a demonstration and an automated test.

**Names.** `split_name` handles Last, First M and First M Last; a suffix (Jr, III) stays with the last name; a hyphenated or double surname is kept whole and each half is also indexed for matching.

## Geocoding, districts and privacy

Only rows that passed every check are geocoded. Two backends exist and the tool says which is active on the check stage and in the menu foot.

**Geosupport** is the City's own address engine (the Department of City Planning's GDE), installed locally with its data files (the `GEOFILES` environment variable, which on Windows must end in a backslash). `geocode_with_gde` splits the house number from the street, drops Rear, Front and Gar for the query only, and calls `address()` with the borough code when the city is a borough or the ZIP when it is not. It returns coordinates, the state Senate, Assembly and Council districts, and any optional Geosupport fields the operator switched on (`gde_fields`). This is the backend expected on the client's machine; results from it are authoritative.

**The reference data** is the fallback: `nyc_address_points.csv`, an index of street name and borough to ZIP and coordinates, plus a district file. `geocode_record` matches the cleaned street and ZIP against it with a fuzzy fallback (`thefuzz`) for slight misspellings, W Main St against West Main Street. The copy that ships with the tool is a small sample, not the City's full file, so it is fine for practice and wrong for real client data, and the check stage says exactly that.

**Districts** are read from the true coordinates before any jitter, so a client is placed in the right district even though the stored point is moved.

**Privacy jitter.** Stored coordinates are shifted by a random distance between 150 and 250 feet (`JITTER_MIN_FT`, `JITTER_MAX_FT`) in a random direction, from a seeded generator (default seed 1337), so the same run gives the same points and no stored point is a client's front door. Jitter can be switched off in the settings; the geocode note then says the coordinates are exact.

**The calculated ZIP column** (`op_calc_zip`, a tidy-up step) looks every address in a table up before processing and adds two columns: the ZIP where the address settles it, and a note per row with the reason, whether the evidence for a ZIP found or why one could not be. It uses the same finder as the review stage, tries every borough when the row has no city, keeps a ZIP the row already has unless told to calculate for every row, and never guesses when a street runs through several ZIPs or several boroughs. Rows it could not place reach review carrying that reason.

**The street-to-ZIP finder** (`fill_missing.ZipFinder`) backs the review stage's batch lookup and the calculated column. `propose(street, city)` returns a ZIP only when exactly one fits: through Geosupport by house number where it is active, else through the reference data by street and borough. `propose_city(street, zip)` returns a borough for an unrecognized city when a valid ZIP or a street known in exactly one borough settles it. Every proposal is shown with its evidence before it is applied, and every applied fill sends the row back through validation.

## Duplicates

Three mechanisms handle duplicates, and only the first ever acts without a person.

**Tier 1, confirmed duplicates.** The same non-blank Client\_ID on rows in one file that are otherwise identical (same name, address, ZIP and program after cleaning). The first row is kept, the rest are set aside with a flag naming the row they copy. This is the only case treated as a true duplicate by the engine itself, because there is no reading of it under which two people exist.

**Tier 2, possible duplicates across files.** Rows in different files that share a person key (normalized first name, last name and ZIP) are noted with a flag. They are never merged here; they are the raw material for identity resolution on the Results stage, where the pair is scored and either joined by rule or shown to a person.

**The within-file rule.** `dedupe_rules.proposals` groups rows in one file that match on the fields the reviewer chose (default First\_Name, Last\_Name and Zip; any schema fields can be chosen) after cleaning and case-folding. Each group is shown side by side on the review stage, in the Duplicates within a file panel. The decisions are:

- `copies`: the first row by file order stays, the rest are set aside.
- `copies:N`: row N (1-based, as shown) stays instead; the rest are set aside, each flagged as a copy of row N. If N is not in the group, the first row is kept.
- `keep`: every row stays and the tool stops pairing them.
- blank: the decision is forgotten.

A whole file can be decided at once, and the panel states the consequence in rows before anything happens. Decisions are chosen locally and applied together (`POST /api/prepare/dupes/decide` with a `decisions` list), which processes the batch once. `apply_decisions` clears its marks on every run, so changing a decision after processing takes effect; an earlier version left the old marks behind, which was a bug.

**Set aside is recoverable.** Rows a decision set aside appear in the review group Copies you confirmed and in the `Set_Aside_Records` export with the reason. Nothing is merged and nothing is deleted. Undoing the decision brings the rows back.

**In the row-by-row queue.** A row that belongs to a group of possible copies offers Keep this row (set the rest aside) and, across all such groups, Keep one per person per program, which keeps one row per name and date of birth in each program.

## Identity resolution

`identity.resolve` runs over the clean rows (after review decisions) and answers who is the same person across systems. It produces a master ID per person, Goal 1 (the number of master IDs) and Goal 2 (the number of distinct master ID and program pairs). Each clean row becomes a `PersonRecord` with normalized name keys, a date of birth if the schema has one, a street and ZIP, a program, the source system's identifier and the system it came from.

**Blocking.** Every pair is not compared. A record is indexed under keys that each combine two independent facts, and only records sharing a key are compared: date of birth alone, full street and ZIP alone, surname with birth year, surname with birth month and day, surname with address, surname with ZIP, given name with birth year, and the nickname group of the given name. Two records that share none of these are never a pair.

**Scoring.** `score_pair` adds points for agreement and returns the evidence as plain sentences:

| Evidence | Points |
| --- | --- |
| Same identifier inside one system | 100 (decisive on its own) |
| Date of birth matches exactly | 42 |
| Date of birth matches with swapped digits or a one-digit slip | 26 |
| Surname matches | 30 |
| Surnames overlap (one half of a double surname, or a maiden name) | 24 |
| First and last name swapped between the records | 20 |
| Given name matches | 26 |
| Given names are in one nickname group (Bill, William) | 22 |
| Given name matches an initial only | 8 |
| Address matches (street and ZIP) | 30 |
| ZIP matches only | 6 |

A date of birth that clearly differs subtracts, and a caution is attached. Pairs below 62 points (`PROPOSE_THRESHOLD`) are dropped. Pairs at 62 or above are proposals.

**Joining without asking.** `_is_auto` joins a pair automatically only in two cases: the same identifier within one system, or the four strong facts all present at once (date of birth exact, surname, given name and address). Everything else, however high the score, waits for a person. Joins are made through union-find over record ids, so a chain of confirmed pairs becomes one identity.

**Proposals and the range.** Open proposals are listed on the Results stage with both records' brief descriptions and the evidence, and a person confirms or rejects each (`POST /api/identity/decide`). Decisions are replayed on every resolution. While any proposal is open, Goal 1 is reported as a range: the settled count if every open pair is different people, down to the count if every open pair is the same person. When none are open the count is a single number.

**Goal 2.** For each master identity, the set of programs across its records is collected (through the alias map, so grouped spellings are one program), and Goal 2 is the sum of those set sizes. A person in three programs counts three times in Goal 2 and once in Goal 1. Records with no program are counted in Goal 1 and reported separately under no program recorded.

**Known limit.** The weights and thresholds were set by reasoning about the client's data patterns and tested on constructed cases (47 checks in `tests/test_identity.py`); they have not been calibrated against a hand-labeled ground truth from the client's real files. That calibration is the most valuable open item in the product.

## Programs

Goal 2 is only right if every file's program column is matched and the same program is spelled one way, so this has a stage of its own (stage 5) with three steps.

**Which column holds the program, per file.** Each included table shows the column matched to Program, sample names from it, a warning when the column looks like codes rather than names (`column_check`), and a dropdown to change it. A file with no program column is said plainly to drop out of Goal 2, unless a per-source default names its program, in which case every row of that file counts under it and the stage says so.

**Which names are the same program.** Every distinct program name across the files is listed with the file it came from, and `program_names.suggest_groups` proposes groups with a stated reason: the same name once wording is set aside (Workforce Development and Workforce Dev.), one name being the other with more words on the end (Workforce and Workforce Development), or one being the initials of the other (WFD). Grouping is pick-up-and-place: click a name, click the group it belongs to, or count it on its own. A group's canonical name can be typed over. The tool's proposal can be restored. Every edit is local to the page until Apply sends the whole set-up in one call (`POST /api/programs/apply`), which the Preview and Continue buttons do on the operator's behalf.

**The alias map.** `program_names.build_alias_map` turns the groups into a map from each spelling to its canonical name. `transform_row` applies it, storing the canonical name in the program field, keeping the original in the flags, and recording the substitution in the audit. The map is part of the saved set-up.

**The preview.** One button processes the batch with the programs as they stand and resolves identity, exactly the work the Results stage does, and shows Goal 1, Goal 2, and unique clients per program with row counts, plus how many counted rows have no program. Any change to a column choice or the grouping marks the preview stale; it can be refreshed as often as wanted. Rows still needing review are not counted and the preview says how many. Nothing is decided by previewing.

**What an AI should know about the counts here.** Taking a spelling out of a group makes a new program appear in Goal 2 and moves its people; the preview shows that immediately, which is the point of the stage. The grouping never changes a row's stored original value or Goal 1.

## The review model

Every row that failed a check goes to review, and review is organized by cause so that common problems are decided together. `_classify` assigns each failed row to exactly one group, in a fixed priority order (summary rows first, so a total never appears among address problems). `_review_rows` returns the groups; each shows a plain-language title, the count, a root-cause diagnosis where the cause is the set-up (`_group_diagnosis`: a column matched to the wrong field, a field with no column, a file that never carries the field), and its decisions.

| Group id | Title | Decisions offered |
| --- | --- | --- |
| summary | Not client records: totals, counts and headings | Set aside, exclude / Hold for review |
| conflict | City conflicts with its ZIP | Send all to review / Apply ZIP city to all |
| zipcity | No usable ZIP code, and no city either | Send all to review / Hold for review, plus batch lookup |
| cityunknown | City is not recognized, and the ZIP did not explain it | Send all to review / Hold for review, plus batch lookup |
| zipbad | No usable ZIP code | Send all to review / Hold for review, plus batch lookup |
| noaddr | No usable address | Hold for review / Set aside, exclude |
| missing | A required field is blank | Send all to review / Hold for review, plus batch lookup |
| idconflict | One identifier used for records that do not match | Send all to review / Hold for review |
| duprule | Copies you confirmed | Set aside, keep the first / Keep them all, flag only |
| dupc | Confirmed duplicates, identical rows with one ID | Keep one of each / Send all to review |
| dupp | Two records in one file that may be one person | Send all to review / Keep both, flag only |
| geo | Address could not be matched | Send all to review / Hold for review |
| other | Other validation problems | Send all to review / Hold for review |

Every group except summary and duprule also offers Accept all as they are, which moves its rows to the clean list marked Approved as entered by reviewer and records the acceptance on each row in the audit, naming the group.

**Batch fills.** On the ZIP and city groups, one button looks every row up from its street (`fill_missing.propose_for_row`), lists what would be filled with the reason for each, names the rows it cannot place and why, and applies the list on approval (`POST /api/fill/apply`). Every filled row is validated again, so a fill that contradicts the row's own city is still caught.

**Decisions are batched.** A group decision is chosen locally and shown as will: send all to review with an undo; one Apply sends every choice (`POST /api/review/decide-many`). Duplicate decisions are batched the same way with one reprocess. Finishing the review applies anything still pending. Every decision is an action in `S["actions"]`, and `_replay` derives each row's status from the actions in order, so undo is a pop.

**Row statuses.** A row in review is `pending` (in the queue), `held`, `cleared` (a group decision resolved it), `approved` (a person accepted it as it stood), `corrected` (a fill or suggestion was applied and it passed), `removed` or `aside`. `_export_sets` resolves these into the four sets the outputs use: clean, kept by a reviewer, set aside, still in review.

**The row-by-row queue.** Whatever a group sent on is worked one row at a time with filters and facets. Each row shows what is wrong in plain words, including why a calculated ZIP could not be worked out, the record as transformed, the original row exactly as it arrived (with unmapped columns available as chips), and the actions: fill from the address, keep this row of a group of copies, accept as it stands, leave for later, set aside. Selected rows can be decided together with one reprocess (`POST /api/queue/bulk`). There is no field for typing a new value.

**Corrections files.** A `Manual_Review_Needed` file that was exported, corrected outside the tool and uploaded again is applied as corrections by identifier; the columns replaced are noted on each row and the row is validated again.

## Outputs

Seven files, each written on demand by `GET /api/export/file?which=...`, in CSV or Excel as chosen (the audit log is always plain text, the quality report always CSV). Columns can be switched off for the clean file; sensitive columns are pointed out for that purpose.

| File | What it holds |
| --- | --- |
| `Unique_Clients` | One row per master identity (Goal 1), with the master ID, the identity's name and address as resolved, and every source record behind it by system and identifier. |
| `Unique_Clients_By_Program` | One row per master identity and program pair (Goal 2), with the program under its canonical name. Never a blank program where a per-source default was set. |
| `Final_Clean_Mapped` | Every row that passed, in the canonical schema, with coordinates (jittered), districts, the source file and row, a `Resolution_Status` column reading Passed every check or Approved as entered by reviewer, and any custom fields. |
| `Manual_Review_Needed` | Every row still in review, with the original values preserved and one plain-language reason column, so it can be corrected outside the tool and uploaded again as corrections. |
| `Set_Aside_Records` | Every row set aside, with the reason: a confirmed copy (and of which row), a summary row, a reviewer's exclusion. |
| `Secure_Audit_Log.txt` | The complete audit trail (next section). |
| `Data_Quality_Report.csv` | Per source file: rows in, passed, in review, set aside, and the count of each problem kind, for reporting back to the system that produced the file. |

**Reconciliation.** Before any count is reported, `_reconciliation` asserts that clean + review + set aside equals the input row count across all included tables. The Results stage and the summary page show the four numbers so the arithmetic is visible.

**The printable summary** (`GET /api/summary`) is one page for sharing: both goals, the per-program table, the reconciliation, the settings and the backend used, with no client data at all.

**Coordinates in the outputs are jittered.** Districts were computed from the true point before the jitter. A consumer of `Final_Clean_Mapped` must not treat the coordinates as a residence.

## The audit trail, saved set-ups and sessions

**The audit trail** (`audit_trail.full_text`) has three sections, and together they let any number be traced back without opening client data.

1. The set-up that shaped the run: files loaded, each table's inclusion and header row, the column set-up, every tidy-up step in force, the matching per file, per-source defaults, the program grouping, what counts as a duplicate, and the settings.
2. What the engine did to each row, by file, row number and identifier: every fix, fill, split, default, substitution and failed check, with column names only.
3. Every decision a person took: group decisions with the rows they touched by identifier, row decisions with their note, fills approved, duplicate decisions per file, in order.

It is readable during the session from the menu foot and the Download stage (`GET /api/audit`, filterable by kind, file and search) and exported as `Secure_Audit_Log.txt`. The rule is absolute: identifiers, row numbers and column names only, never a name, address or value. An earlier version exported only the engine's section; that gap is closed and tested.

**Saved set-ups** (`setups.py`, one JSON file per set-up in `setups/`, format 1) record the work of configuring a run: the files by name and the columns each had, header rows, inclusion, the column set-up, tidy-up steps, the matching as it stood (the tool's proposal and the person's choices together, because a later version's proposal might differ), per-source defaults, the program grouping and alias map, the duplicate fields and the settings. No client data is written.

Loading a set-up checks every part against the files loaded now and the running version before anything is applied (`check_setup`), and names each problem: a saved file that is not loaded; a loaded file that no longer has a column the set-up used; a field the column set-up lacks; a tidy-up step of a kind this version does not have; a set-up saved in another format or version. Files are matched by name with the row range stripped, so the same export with more or fewer rows is the same file, and the columns that saved steps will add are counted as present. The person then loads what fits and skips the rest, or does not. A set-up file that cannot be read is listed as broken rather than hidden. Loading is undoable and marks the program preview stale.

**Sessions** (`sessions_store.py`) save progress between launches: the set-up and every decision, never `frames`, `uploads` or `results`. A session is autosaved after each change when saving is on, listed on the check stage for resumption (the files must be added again, since they were never stored), and purged after seven days (`RETENTION_DAYS`).

## Architecture and runtime

&#91;embedded content: architecture · launcher, server, browser, engine and its modules\]

The launcher starts one server; the browser only draws what the server sends, and every rule lives in the engine and its modules. Nothing runs anywhere else.

**Launcher** (`launch.py`, started by `Crosswalk.vbs` on Windows through `pythonw` so no console appears, `Crosswalk.command` on Mac, `Crosswalk.sh` elsewhere). It refuses a Python older than the tool needs and says which to install; installs the packages once and leaves a `.installed` marker; picks port 8765 or the next free one; asks any copy already on the port for its version and stops an older one (through `/api/quit`, or by the port's process id when it does not answer); writes `crosswalk.pid` and `launch-log.txt`; opens the browser; and exits 15 seconds after the page reports it is closing, or after 45 seconds with no heartbeat. `Stop Crosswalk.vbs` forces a stop. With no console, `sys.stdout` is None, and the launcher installs a stand-in that writes to the log so uvicorn's logging can start; that failure was seen on a client machine and is fixed.

**Server** (`crosswalk_server.py`). FastAPI bound to 127.0.0.1 only. One dictionary `S` holds every piece of working state, about 30 keys, listed in section 5 of `docs/TECHNICAL.md`. `GET /api/ui?screen=...` returns the shared chrome plus that screen's data; every change is a POST that mutates `S` and, where needed, reprocesses. Reprocessing (`_recompute`) runs in a worker thread through `run_in_threadpool`, so the server keeps answering while it works. A table with its tidy-up steps applied is cached by a signature of the raw frame, the header row and the active steps (`_PREP_CACHE`); before that cache a single grouping click on a 7,000-row file rebuilt it fifteen times and took 3.3 seconds, and now takes 0.12. There are 69 routes, all listed in the technical reference with their handler and purpose.

**Progress.** The engine reports per file, not per row, through a `progress` callback carrying the phase, the file name, its index and the file count. `S["run"]` holds the phase, one calm message such as Cleaning and checking the rows in Elder Care.csv, a percentage that never runs backward, and how many steps of the batch are left (two per file plus one). The page polls it and grays the screen behind one card while it runs.

**Interface** (`ui/app.js`). One page, no framework. `UI` holds the page's own state; `load(screen)` fetches and `render()` rebuilds from one `vScreen()` function per stage. A single document-level click handler dispatches on `data-*` attributes. Grids keep their scroll position across a redraw. Choices that used to cost a round trip each are held locally and applied once: program grouping, review group decisions, duplicate decisions. Every stage and every complex element has a ? button reading `ui/help.json`, which is also the source of the user guide and the cheat sheets.

**Documentation is generated.** `tools/make_docs.py` builds `docs/TECHNICAL.md` (the narrative sections plus a reference of every class, function and route read from the source), `docs/USER_GUIDE.md` and the cheat sheets; `tools/take_screenshots.py` retakes the guide's pictures; `tests/test_docs.py` fails when any generated file no longer matches the code or any function lacks a docstring.

**Tests.** Ten suites and more than 1,200 checks: smoke, table detection (21), corrections (25), preflight (21), identity (47), the API (694), parity between the Streamlit and web front ends (46), the proof workbook (253 rows that are both a demonstration and a test), layout in Playwright at several widths (121) and docs (11). All must pass from inside the packaged archive before a build ships.

## What it does not do, known limits, and the glossary

**Deliberately not done.** It makes no network calls. It uses no model and no learned weights. It never merges two records on similarity alone. It never edits a value a person types into a cell; corrections come from the row's own address, from a corrections file, or from the source system. It never deletes a row. It never writes client data to disk except in the output files the person downloads. It does not send email, sync to a database, or run on a schedule; it is a desktop tool run by a person a few times a year. It does not decide anything a human should: an ambiguous pair, an ambiguous address, a duplicate group, a program grouping.

**Known limits an AI should state rather than paper over.**

- The identity weights and thresholds are reasoned, tested on constructed cases, and not yet calibrated against a hand-labeled sample of the client's real files.
- The reference file that ships (`nyc_address_points.csv`) is a small sample. Real geocoding needs Geosupport installed on the client machine, with `GEOFILES` ending in a backslash on Windows.
- Goal 2 is only as good as the program column matching and the grouping; a file whose program column is unmatched and has no per-source default is absent from Goal 2 and the tool says so.
- Address parsing is tuned to New York City: only NY is recognized as a state, the five boroughs, 24 spellings of them and 114 neighborhoods are the recognized cities, and hyphenated Queens house numbers are handled. Addresses outside the city are flagged, not resolved.
- The Streamlit front end (`run.bat`) is kept for parity tests and is not the supported interface.

**Glossary.** Guided term first, Advanced term in brackets, then the meaning.

| Guided | Advanced | Meaning |
| --- | --- | --- |
| Add your files | Sources | uploaded files and the tables found in them |
| Set up your columns | Schema | the canonical fields every file is mapped onto |
| Tidy up | Prepare | steps that add columns: clean, split, calculated ZIP |
| Match your columns | Map | field-to-column matching per table |
| Process | Run | `run_pipeline` over every included table |
| Fix problems | Review | failed rows grouped by cause, plus the queue |
| Row by row | Queue | one failed row at a time |
| Results | Summary | Goal 1, Goal 2, open pairs |
| Download | Export | the seven output files |
| Set aside | Segregated | removed from the clean list, kept and recoverable |
| Copies | Duplicates within a file | rows one person decided are the same client |
| May be one person | Proposal | an identity pair awaiting a decision |
| Look up from the street | Fill | a ZIP, city or state derived from the row's own address |
| Set-up | Configuration | everything saved by `setups.py` |
| Master ID | Master identity | one id per resolved person; the unit of Goal 1 |
| Goal 1 | Unique clients | count of master identities |
| Goal 2 | Unique clients by program | count of distinct master identity and program pairs |

**Where to read more.** `docs/TECHNICAL.md` is the generated engineer's reference with every function, route and state key; `docs/USER_GUIDE.md` and `docs/Crosswalk_User_Guide.docx` are the operator's guide with screenshots; `docs/cheatsheets/` holds one page per hard topic; `docs/VIDEO_SCRIPT.md` is the narration for a screen recording; `README.md` is the changelog of behavior, written as it was built; `proof/Proof_Workbook.xlsx` demonstrates every rule on constructed rows and is run as a test.
