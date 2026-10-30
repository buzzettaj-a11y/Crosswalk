# Crosswalk: user guide

_Built by `tools/make_docs.py` from `ui/help.json`, the same text the help buttons in the app show, and the screenshots in `docs/screenshots/`. Do not edit by hand._

## Before you start

Crosswalk takes the client lists your systems export, cleans them into one
shape, places every address on the map, works out which records are the same
person, and gives you two numbers: how many people you serve in all, and how
many in each program. Nothing leaves your computer and nothing is written to
disk until you download it.

Start it by double-clicking `Crosswalk.vbs` (Windows) or `Crosswalk.command`
(Mac). It opens in your browser. Close it with the Close Crosswalk button at
the foot of the menu; closing the browser works too.

Every stage and every complex element has a small **?** button. Press it for
what that thing is for and how to use it. This guide is the same text, in
order, with pictures.

## The stages

### 0. Check this computer

**Why this exists.** Before any client data is opened, the tool checks that this computer can do the job: the right Python, the packages it needs, and whether Geosupport, the city's own address engine, is set up. If Geosupport is missing it falls back to a small reference file, which is fine for practice and wrong for real work, and it says so plainly.

**What to do.** Read the list. Anything marked as a problem tells you what to fix. Saved progress from earlier sessions appears here too, so you can pick a batch back up.

![Check this computer](screenshots/00_check.png)

### 1. Add your files

**Why this exists.** Each system you work with exports its own file, in its own shape. This stage takes them all in, finds the tables inside them (a sheet can hold more than one), and lets you say which tables count.

**What to do.** Drop the files in or browse for them. Untick a table that is a summary rather than a list of people. Show data opens the first rows so you can check the header row is the right one; if a title sits above the real header, tick the row that holds the column names. When the set-up is done, Skip the steps processes everything and takes you straight to what needs fixing.

![Add your files](screenshots/01_sources.png)

### 2. Set up your columns

**Why this exists.** Every file is turned into one shape, the same columns in the same order, so the systems can be compared at all. The standard set covers a person, an address and a program; you can add columns your work needs, such as a date of birth, which also makes matching people across files stronger.

**What to do.** Most batches use the standard set unchanged. Add a column when a file carries something you want kept and checked, and give it a type so it is written one way (a date as 2024-03-15 however it was typed).

![Set up your columns](screenshots/02_schema.png)

### 3. Tidy up

**Why this exists.** Some files jam several things into one cell: a street, an apartment, a city and a ZIP all in one address column, or a whole name in one column. This stage untangles them into separate columns so they can be matched and checked. It can also calculate a ZIP from an address using the city's address engine.

**What to do.** The tool proposes steps it thinks are needed; remove any that are wrong. Add an operation to split a jammed column, clean casing, or add a calculated ZIP column. Every step only adds columns; nothing in the file is overwritten, so a step can be taken back without loss.

![Tidy up](screenshots/03_prepare.png)

### 4. Match your columns

**Why this exists.** The tool has to know which of your columns holds the first name, which the street, and so on. It guesses, and it checks its guess against the values in each column, because a column in the wrong place processes without complaint and produces confidently wrong results.

**What to do.** Look at each table. A warning under a field means the values do not look like that field, and it names the column that does. City and State can be left empty; the ZIP fills them. If a file leaves out a field entirely and every row shares one value, such as the program, set it under Fill a field for this source only.

![Match your columns](screenshots/04_map.png)

### 5. Programs

**Why this exists.** The second count the project asks for is clients per program, and it is only right if every file's program column is matched and the same program is spelled one way. Workforce, Workforce Development and WFD are one program to a person and three to a computer.

**What to do.** Check which column each file reads the program from. Group the names that are the same program: pick a name up, click the group it belongs to. Then Preview the counts to see both goals as they would stand, and refresh after every change until the list of programs looks like the real list.

![Programs](screenshots/05_programs.png)

### 6. Process

**Why this exists.** Every row is cleaned, checked and placed on the map, all on this computer, with nothing written to disk. The result says how many rows passed and how many need a person.

**What to do.** Press Process. The settings rarely need changing; the seed only affects the small random offset added to map points for privacy. Watch the card: it says which file it is on and how many steps are left.

![Process](screenshots/06_run.png)

### 7. Fix problems

**Why this exists.** Rows the tool could not finish on its own, grouped by cause so the common ones are dealt with together. The tool never guesses at a person's address or identity; it asks.

**What to do.** Work the groups first. Each says what is wrong, how many rows, and offers a decision for the whole group: look the ZIPs up, accept the rows as they are, set them aside, or send them to the row-by-row queue. Duplicates within a file are decided here too. Choose everything, then Apply once. Anything left goes to the row-by-row queue.

![Fix problems](screenshots/07_review.png)

### 8. Row by row

**Why this exists.** The rows that need an individual look. Each shows what is wrong, what the tool can do about it safely, and the original row exactly as it arrived.

**What to do.** Values are never edited one by one here. Fill in what the tool can derive, keep one row of a group of copies, accept a row as it stands, or set it aside. Anything else is fixed at the source and loaded again.

![Row by row](screenshots/07c_queue.png)

### 9. Results

**Why this exists.** The two numbers the whole effort exists to produce: unique clients across every file, and unique clients per program. Both are worked out from the rows that passed, by an engine that decides who is the same person across systems.

**What to do.** Read the two counts. Where records may be one person, decide the open pairs; the first count is a range until you do. The per-program bars show where people are. Open the printable page to share the counts without any client data.

![Results](screenshots/08_summary.png)

### 10. Download

**Why this exists.** The finished files, written only when you ask for them: the two counts as lists, the clean master list, the rows still needing work with the reason for each, everything set aside, an audit log safe to share, and a quality report per file.

**What to do.** Choose the format and the columns, then download each file. Save the set-up so next quarter's run starts from here.

![Download](screenshots/09_export.png)

### 11. Audit trail

**Why this exists.** Everything that changed and who or what changed it, so any number can be traced back. It holds identifiers and column names only, never a name, address or value, so it can be read and shared safely.

**What to do.** Filter by kind (the set-up, changes the engine made, decisions a person took), by file, or search by identifier. Download the full trail as a text file.

![Audit trail](screenshots/10_audit.png)

## The elements that need a closer look

### Skip the steps

**Why this exists.** A repeat user with clean-enough files should not have to click through every stage. This does the tidy-up, the matching and the processing using what the tool proposes, then lands on what needs fixing.

**What to do.** If a required field has no column matched it stops and says which file and which field. If a matched column looks wrong it stops and shows the warning, and you choose to fix it first or run anyway.

### Which row holds the column names

**Why this exists.** Files often begin with a title or a note above the real header. Read that way, the column names would be nonsense and every field would be missing.

**What to do.** Tick the row that holds the column names; rows above it are dropped. The tool flags a choice that looks wrong: a mostly empty row, a row of numbers, or no header chosen when one of the first rows plainly holds the names.

### Does this column hold what the field expects?

**Why this exists.** A column matched to the wrong field is the mistake with the worst consequence: it processes without complaint and produces confidently wrong results, such as apartment numbers as streets.

**What to do.** The tool reads a sample of each matched column and warns when the values do not look like the field, naming the column that does. It never blocks you, since you may have a reason.

### Fill a field for this source only

**Why this exists.** One file may leave a field out entirely, such as the program, while every row in it shares the same value. Typing it once here gives it to every row of that file.

**What to do.** Set it here and it fills only blanks, never replacing a value the file supplied. It applies to this table alone and is recorded in the audit log on every row it touched.

### Which names are the same program

**Why this exists.** Systems spell the same program differently. Counted literally, one program looks like several, and a person in one of them appears to be in several.

**What to do.** The tool proposes groups and says why. Click a name to pick it up, click the group it belongs to. Type over a group's name to change what it is counted under. Apply once, then preview the counts.

### What the counts would be

**Why this exists.** Grouping decisions change Goal 2 directly, and it is far better to see that before the report than after.

**What to do.** Preview processes the files with the programs as they stand and shows both counts, program by program. Any change marks the preview out of date; refresh as often as you like.

### Look up missing ZIPs from the street

**Why this exists.** A row with a street but no ZIP is not stuck. The city's address engine, or the reference data, knows which ZIP a street falls in.

**What to do.** The button lists what would be filled for every row in the group, with the reason. A street that runs through several ZIPs, or that the engine does not know, is left alone and says why. Approve the list and every filled row is checked again.

### Duplicates within a file

**Why this exists.** The same person can be listed twice in one export. Two rows that match on the fields you chose are shown side by side so a person decides whether they are one client or two.

**What to do.** Copies, keep the first: the first row stays and the rest are set aside, listed and recoverable. Keep this one: a different row stays instead. Different people, keep all: every row stays and the tool stops pairing them. Decide, then Apply once; nothing is merged or deleted.

### Deciding a whole group

**Why this exists.** Most problems come in batches with one cause. Deciding them together is faster and more consistent than one row at a time.

**What to do.** Each group offers its own decisions, plus Accept all as they are. A chosen decision shows as "will:" until you Apply; apply them all at once.

### Records that may be one person

**Why this exists.** Across systems the same client appears with different identifiers, a changed surname, a nickname, or a mistyped birth date. The first count is only right if each person is counted once.

**What to do.** The engine joins records on its own only where coincidence is not a reasonable explanation. Everything weaker is shown as a pair with its evidence for a person to decide. Until they are decided the count is a range.

### Saved set-ups

**Why this exists.** Configuring a run is real work. Saving it means next quarter starts from here rather than from scratch.

**What to do.** Save under a name. Loading checks every part against the files loaded now and this version of the tool, and names anything that no longer fits before applying what does. No client data is saved.

### Calculated column: ZIP from the address

**Why this exists.** Some files carry addresses but no ZIP. The ZIP can be worked out from the street and borough by the city's address engine, once, for the whole file.

**What to do.** Choose the street column and, if there is one, the city and existing ZIP columns. The step adds the calculated ZIP and a note per row saying why. Rows it could not place go to review carrying that reason.

## Workflows

### A first run, end to end
1. Add your files. Untick anything that is a summary rather than a list of people.
2. On Match your columns, read the warnings; a wrong column is the mistake that matters most.
3. On Programs, group the spellings and preview the counts until the program list looks right.
4. Process.
5. On Fix problems, work the groups: look ZIPs up, decide duplicates, accept or set aside. Apply once.
6. On Results, decide any open pairs. The counts are final when none are open.
7. Download the files, and save the set-up for next time.

### The quick run
Add your files, then press "Process everything and show me what needs fixing". It stops only when something would make the run wrong, and says what.

### Next quarter
Add the new files, load the saved set-up, read what fitted and what did not, then run.

### When a file has no program column
On Match your columns, under Fill a field for this source only, type the program. Every row of that file counts under it.

### When the tool cannot place an address
Look up the ZIPs from the street on the review group. A street in several ZIPs needs a house number; one the engine does not know needs a person.
