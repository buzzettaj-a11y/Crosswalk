# Crosswalk

Offline client data cleaning, geocoding and identity resolution.

A fully offline desktop tool that merges messy client lists exported from several
systems (.csv, .tsv, .xlsx, .json, .xml) into one clean, validated master list,
then geocodes each address locally and assigns NYC political districts. It is built
for client data that contains PII, so all processing stays on the machine with no
external calls. Nothing is written to disk until you export.

## Made for someone who does this a few times a year

### The column matching is checked before you process

Everything else in this tool guards the data. Nothing guarded the matching,
which is the mistake most easily made and the one with the worst consequence: a
column in the wrong place processes without complaint and produces confidently
wrong results.

The Map stage now reads a sample of every matched column and says plainly when
the values do not look like the field. Apartment numbers matched as the street,
four digit ZIPs, addresses matched as names, one identifier repeated on every
row. Each warning shows examples from your own data. It never blocks you, since
you may have a reason, but you are told before the run rather than after.

### A grid stays where you scrolled it

Paging through a wide grid with Next or Back keeps the grid on the columns you
were looking at, and keeps the page where it was. Every grid remembers its own
position across a redraw and is put back there. Opening a different stage still
starts at the top.

### The audit trail, complete and always at hand

Three things change a row, and all three are in the trail: the set-up that
shaped the run (files, header rows, column set-up, tidy-up steps, matching per
file, program grouping, what counted as a duplicate, settings); what the
engine did to each row by file, row and identifier; and every decision a
person took, with the rows it touched by identifier. Identifiers and column
names only, never a name, address or value.

The trail is open from the menu at any point in the session, filterable by
kind, file and search, and downloads as Secure_Audit_Log. An earlier version
exported only the engine's part; decisions and the set-up never reached it.

### Processing shows itself, calmly

While the tool processes, the screen grays out behind one card: a wheel, what
is happening, which file it is on, and how many steps of the batch are left.
The message changes once per file, not per row; a batch of 7,500 rows across
three files shows six messages. Every action that reprocesses says why on the
card, "Applying your duplicate decisions", so it is never a mystery what a
wait is for.

### Saved set-ups

The work of configuring a run can be saved under a name and loaded next time:
the files by name, header rows, the column set-up, tidy-up steps, the matching
as it stood (proposal and choices together, since a later version's proposal
may differ), defaults per file, program grouping, what counts as a duplicate,
and the settings. No client data is saved.

Loading checks every part against the files loaded now and this version of the
tool before applying anything: a file that is not loaded, a column a file no
longer has, a field the column set-up lacks, a step this version does not
have, a set-up saved in another format. Each is named as a problem, and the
choice is to load what fits and skip the rest, or not. A set-up that cannot be
read is listed as broken rather than hidden. A file that grew or shrank is
still the same file. Loading is undoable.

### Choose everything, then apply once

Where a click used to mean a round trip, and sometimes a full reprocess, the
work is now chosen locally and applied together.

On the Programs stage every pick, drop, rename and column choice changes a
working copy on the page, with no call to the tool at all, and one Apply
sends the whole set-up. Preview and Continue apply it for you. On the review
stage, choosing what to do with a group marks it "will: send all to review"
and can be undone; one Apply carries every choice at once. Duplicate decisions
work the same way, which matters most: each used to reprocess the whole batch
on its own, and now all of them are applied with a single reprocess. Finishing
the review applies anything still pending.

Behind this, a table with its tidy-up steps applied is now built once and
reused until something it depends on changes. It used to be rebuilt on every
call, and one screen asked for it many times over, so a single grouping click
on a 7,000-row file rebuilt it fifteen times and took over three seconds; the
same click now takes a tenth of a second. Every screen is faster for it, and
the calculated ZIP column, which looks every address up, no longer runs again
on every click.

The Guided and Advanced switch sits at the foot of the menu.

### Every click shows itself

A thin bar appears at the top of the page whenever a request is in flight, so
a click is never followed by nothing, and the control that was clicked is held
until its work is done. When the server is processing rows, on the Process
stage, the fast path, or any review action that reprocesses, the bar shows the
actual phase and how far along it is, taken from the engine's own progress:
"Cleaning and checking rows (3,000 of 7,000 rows)", then "Finding locations".
A fast answer never shows the bar at all, so nothing flickers.

Making this work exposed a real fault. Review actions that reprocess the batch
were doing so on the server's request loop, which blocked every other request,
including the one asking for progress, until they finished. That is why the
page seemed to freeze. Reprocessing now runs in a worker thread and the server
keeps answering while it works.

### Skipping the steps

Once files are loaded, the Add your files stage offers one button: process
everything and show me what needs fixing. It keeps the tidy-up steps and the
column matching the tool proposed, processes, and lands on Fix problems. Every
stage can still be visited afterward.

It is honest about the two things that can stop it. If a required field has no
column matched, it says which file and which field, and offers the usual fix
for the common case: a file with no identifier column can have Client ID marked
optional in one click, with a note that such rows cannot be checked for exact
duplicates. If a matched column does not look like its field, it stops and
shows the warning, with the column that looks right, and lets you fix it first
or run anyway. Consequences are folded into their cause, so a wrong ZIP column
is one warning, not three.

### Plain words, unless you ask for the precise ones

In Guided the stages read Add your files, Set up your columns, Tidy up, Match
your columns, Process, Fix problems, Download, and a problem reads "This row has
no ZIP code."

Switch to Advanced and the same things read Sources, Schema, Prepare, Map, Run,
Review, Export, with the original message text. Advanced is a request for
control, so it uses the words that match what is being controlled. Only the
words change; the behavior is identical.

### Practice with example data

"Try it with example data" on the Add your files stage loads the five example
files that ship with the tool. They hold made-up records, so the whole process
can be learned without putting real client data at risk. Start over clears them.

### A result you can act on

After processing, the share of rows that passed is stated plainly. A low result points at the column matching first, because a single column in
the wrong place can fail most of a file and is far quicker to fix there than
row by row.

### Undo on every stage

Review always had an undo. Now so does everything before it: the column set-up,
the tidy-up steps, the matching, per-source values, which tables are included,
and the header row. The button sits at the foot of the left rail and names what
it will take back. People only try things when backing out is safe.

### A page to print or hand on

The Download stage offers a one page summary of the batch: what came in, what is
ready, what still needs work, how confident the locations are, a breakdown by
source file, what needed a decision, and what happens next. It holds counts
only, never client records, so it is safe to attach to a report or send to
whoever produces the map.

## Proving the tool does what it says

`proof/Proof_Workbook.xlsx` has one sheet for each thing the tool does,
twenty in all: junk cleaning, name casing, middle initials, ZIP forms, city from
ZIP, city against ZIP, borough names, state, jammed addresses, jammed names, a
unit in both address lines, missing fields, digits in a name, shared
identifiers, records that may be one person, program names, field types, the
same person across systems, two tables on one sheet, and title rows above the
header.

Each sheet holds a handful of rows and an Expected column saying where each
row should land and why: CLEAN with the change to look for, REVIEW with the
reason, SET ASIDE for an identical copy, POSSIBLE DUPLICATE, or PROPOSED for a
pair offered on the Results stage. Every sheet shows both what is affected and
what is left alone, so the boundary of each rule is visible.

Load the workbook, match the columns, process it, and check the rows against
Expected. The same expectations are checked automatically by
`tests/test_proof.py`, which runs every sheet through the engine, so the
workbook cannot drift from what the tool does. It is generated by
`tools/make_proof_workbook.py`, which holds the rows and expectations in one
place.

Writing the workbook exposed two defects, both now fixed: the tidy-up step was
splitting a file's own unit column as if it were a jammed address, and a unit
in the street was being dropped silently when the file also had an Address 2
column instead of being compared with it.

## The two counts the project asks for

The work exists to answer two questions, and the Results stage answers both.

**Unique clients.** Every person counted once, however many systems and programs
they appear in. This is the overall population figure.

**Unique clients by program.** The same person counted once in each program they
take part in. Somebody in Workforce, Resident Services and Property Management
counts once for the first number and three times for the second.

Both are worked out by the identity resolution described below, from the rows
that passed every check. A row still sitting in review has not been accepted
into the dataset, so it is not counted as a person; the Results stage shows
those totals alongside so the difference is visible.

### Programs is its own stage

The second count is only right if every file's program column is matched and
the same program is spelled one way, so this has a stage of its own, between
matching the columns and processing, in three steps.

Which column holds the program in each file, with sample names from each and a
warning when a column looks like codes rather than names. A file with no
program column is said plainly to drop out of the per-program count.

Which names are the same program. Every name found across the files is shown
with the file it came from and grouped by the tool's proposal, with the reason:
the same name once wording is set aside, one name being the other with more
words on the end, or one being the initials of the other. Grouping is done by
picking a name up and clicking the group it belongs to; a group's name can be
typed over to change what it is counted under, and the tool's proposal can be
restored.

A preview of the counts. One button processes the files with the programs as
they stand and shows both counts, program by program, on the spot. Any change
to the grouping marks the preview out of date, and it can be refreshed as
often as you like, so the effect of every grouping decision on Goal 2 is seen
before anything is decided. Rows still needing review are not counted, and the
preview says how many.

Nothing is merged without confirmation, the name as originally recorded stays
on the row, and every substitution is written to the audit log.

### The count is honest about what is still open

Records are joined without asking only where coincidence is not a reasonable
explanation. Where two records might be one person, the tool proposes the link
and shows both records with the evidence, and the first count is reported as a
range until a person decides. Deciding the open questions closes the range, and
the stage says plainly when the number is final.

### The files that carry the answer

Two downloads correspond directly to the two counts. Unique_Clients has one row
per person, with the programs, systems and source records behind them.
Unique_Clients_By_Program has one row per person per program, which is the shape
program reporting needs. Both carry the master ID and the original identifiers,
so any number can be traced back to the rows it came from.

### A page to share

The Results stage opens a page that leads with both counts, breaks them down by
program, and adds what was produced, how confident the locations are, and what
happens next. It holds counts only, never client records, so it is safe to send
on or attach to a report.

## Identity resolution: master IDs across systems

`identity.py` answers a different question from the duplicate check in the
cleaning pipeline. That check asks whether the same record appears twice in one
export. This asks which records describe the same person across every system,
assigns each person a master ID, and produces the two counts the project needs:
unique clients, and unique client and program pairs.

It exists because the hard cases are not near misses and string similarity
cannot find them. A maiden and a married surname share no letters. Bob and
Robert share two. So instead of comparing spellings, it looks for agreement
across independent facts: date of birth, address, given name by nickname group,
each half of a double surname, and the same name found in opposite columns.

### What it handles

Surname changes, where the date of birth and address still agree. Dates of birth
with the day and month the other way round, or one digit wrong. Nicknames that
share almost no letters, using a table of name groups rather than similarity.
Double surnames recorded inconsistently, by reducing Garcia-Lopez, Garcia Lopez
and Lopez to overlapping parts. Names entered in the wrong columns.

### The rule that keeps it safe

Records are joined without asking only where coincidence is not a reasonable
explanation: the same identifier inside one system, or full agreement on given
name, surname, date of birth and address at once. Everything else becomes a
proposed link carrying the specific reason it was proposed and the specific
thing to check, for a person to confirm or reject. Decisions are stored and
replayed, so the work is done once.

Because some links stay open, the client count is reported as a range: the count
if every proposal is accepted, and the count if every one is rejected. A single
number would imply a precision the data does not support. Once every proposal is
decided, the range closes and the count is final.

### Scale

Resolution of nineteen thousand records completes in a few seconds. The number
of proposals depends heavily on how distinctive the names are: a batch with
roughly four hundred distinct surnames produced about 126 proposals, while an
unrealistically small pool of fifteen surnames produced several thousand. Expect
the review effort to fall between those, and size it from a real batch rather
than from an estimate.

## Two interfaces

This package ships two front ends over the same validated engine.

**Crosswalk** is the current interface: a seven-stage wizard with a fixed left
rail, an explicit Schema stage, an in-app two-tier review (grouped decisions
plus a row-by-row queue), and trust guarantees visible on every screen.

```
python -m pip install -r requirements.txt
python -m uvicorn crosswalk_server:api --host 127.0.0.1 --port 8765
```

Or run `run_crosswalk.bat` on Windows, `./run_crosswalk.sh` on Mac or Linux,
then open http://127.0.0.1:8765. It binds to this machine only.

**The original Streamlit app** remains available and unchanged via `run.bat`,
`run.sh`, or the command in Quick start below. Both read the same engine, so
results are identical.

### About Crosswalk review stage

The grouped plan is built from the actual run, not from a fixed list. Only the
groups your data produces appear, ranked largest first. A group offers approve
all (with an honest count of rows that do not fit the rule), send all to the
row-by-row queue, and a pageable searchable preview. Corrections made in the
queue re-enter the pipeline and are re-validated and geocoded; a fix that does
not pass stays in the queue rather than being taken on faith.

### Deciding about one record

Some problems are about a single value, such as a ZIP that is not five digits.
Others are about a relationship between records, and cannot be judged from one
record alone. Opening a row therefore shows everything the decision depends on.

Every problem is stated with what it means and what to check before deciding,
rather than only the message that raised it.

When the problem is relational, the other records involved are shown side by
side. A row flagged because several records share one identifier lists all of
those records, marks which one is being reviewed, names the fields that differ
between them, and lets you open any of the others. The same applies to possible
duplicates. Without this a reviewer is asked to judge a comparison while seeing
only one side of it.

Where the tool can propose a fix from evidence already on the record, it offers
it in one click and says why, for example setting the city to the borough its
ZIP belongs to. Applying a suggestion fills the working copy; nothing is saved
until you approve it.

The original row is shown as it arrived from the file, and any column that was
never mapped is called out separately. That is usually where a missing address
or ZIP turns out to be sitting.

### Review is one stage with two steps

Review is a single stage, shown as two numbered steps so it is clear where you
are and what remains.

Step 1, grouped decisions, is where the volume is handled. Rows are grouped by
the cause of their problem and each group is decided once. Step 2, row by row,
holds whatever is left: genuine one-offs, plus anything you deliberately sent
over from a group. Both steps show the same two-step header with live counts, so
neither is hidden behind the other.

### Working a large queue

Sending a large group to step 2 used to leave a list that could only be paged
through. The queue now takes filters, selections and batch actions, so a queue of
thousands is reduced to workable slices.

Narrow it by status, by problem, by source file, or by a free text search across
names, addresses, ZIPs and identifiers. Each filter shows how many rows it
covers, so it is clear where the volume actually sits before you choose. Filters
combine, and the page size can be raised to a hundred rows.

Select rows individually, select everything on the page, or select every row
matching the current filters, which is the option that matters at scale. With a
selection made you can approve, reject, remove or reopen all of them at once, or
set a field on all of them: choose the field, type the value, and apply.

A batch correction is applied to every selected row and the pipeline then runs
once for the whole batch rather than once per row. Every row is still validated
on its own afterward, so a row the correction does not fix stays in the queue
with its reason. The result is reported plainly, for example 82 rows now pass
every check and 15 still have a problem.

### The header row is chosen where the data is first seen

Show data on the files stage shows the first rows of each table with the row
that holds the column names ticked. If a title or note sits above the real
header, tick the right row; rows above it are dropped, and choosing a row
includes the table.

The tool says when the chosen row looks wrong: a row with most cells empty,
which looks like a title; a row of numbers, dates or ZIPs, which looks like
data; two columns that would share a name; no header chosen when one of the
first rows plainly holds the column names; or a header with the same shape as
the row beneath it, which is a record rather than the names. The table is
marked "check the header row" in the list until it is put right.

### A column the file provides beats one a split made

Splitting a jammed address produces columns for street, unit, city, state and
ZIP. Those are only filled where the value was actually jammed into the
address, and blank everywhere else. An earlier version preferred them over a
file's own Zip column, which sent every row in a file to review as missing its
ZIP while the real ZIP sat unused in the column beside it. Every downstream
symptom followed: the city could not be filled, and the duplicate check lost a
field.

A column the file provides now wins for City, State and Zip. The one exception
is the street, where the split column beats the jammed one it came from,
because the jammed column still carries the unit and city. A column named as an
identifier or code is never taken as the program, because the count by program
needs names.

### The review says when the problem is the matching, not the data

When every flagged row from one source is blank in the same field, that is not
a problem on those rows. It is a matching problem on that source, and fixing
one dropdown clears them all. The review notices this, says so plainly, names
the column that looks right, and offers to switch to it and process again in
one click.

The matching stage says the same thing earlier: a mostly empty column is flagged
and, where the file has a column that would rescue those rows, that column is
named.

### The review count is the run count

Processing reports how many rows failed a check. The review stage reports the
same number, under the same words. It used to add the rows marked as possible
duplicates and call the total "flagged", which made a batch look several times
worse than it was, because those rows are clean rows carrying a note.

### Matches across files are not review items

When the same people appear in several exports, for example one program's list
for three different years, nearly every row matches a row in another file on
name, street, ZIP and program. That is not a problem with any file. It is the
crosswalk question itself, which the Results stage answers by working out who
is who. The review stage shows those matches as one note with a count, and asks
for no decision. Only a match inside one file, a likely double entry, is a
review question.

A file with a ZIP column but no City or State column is not blocked, since the
ZIP fills both; the readiness check now agrees with what the matching stage
says.

### Accepting a whole group as it stands

Every group on the review stage offers Accept all as they are. The rows go into
the clean list exactly as they stand, marked "Approved as entered by reviewer"
in a Resolution_Status column that every clean row carries (the others read
"Passed every check"), and the audit log records the decision on each row by
identifier, naming the group it was part of.

### An unrecognized city is given a suggestion

When the city as entered is not one the tool recognizes, a typo, an out-of-town
name or a neighborhood it does not know, the row's own address is used to
suggest the right borough: a valid ZIP first, then the street, through
Geosupport when it is active and the reference data otherwise. The suggestion
is offered only when the street points to exactly one borough; a street that
exists in several is not guessed. It is shown as a replacement, naming the
value as entered, and applied only on approval, after which the row is checked
again. The value as entered stays in the audit log.

### A correction always carries its note

Every value corrected inside the tool, whether filled in, suggested or applied
to a group, is marked on the row and in the audit log by column name, and the
row is validated again. An earlier version lost that note whenever a correction
touched a row that had also been patched from a re-imported corrections file;
that is fixed.

### Values are not edited one at a time

Correcting hundreds of records by hand inside the tool is not a workflow, so
the record panel does not offer a box per field. It offers the three kinds of
change that are safe at scale, each recorded in the audit log:

Filling in missing location data. Every ZIP group on the review stage says how
many of its rows have a street, and one button looks them all up. A row with a
street but no ZIP, and no city either, is tried in every borough; when exactly
one borough knows the street, its ZIP and borough are both proposed with the
reason. A street that several boroughs know, or that runs through several
ZIPs, is left as it is and the reason is shown. Geosupport answers for the
exact house number where it is active; the reference data is used otherwise.
Every proposed fill is listed for the whole group, approved in one click, and
every filled row is checked again afterward, so a fill that contradicts the
row's own city is still caught. A blank city with a valid ZIP is filled from
the ZIP.

Keeping one of a group of copies. Where records may be one person, the panel
lists them and you choose the row to keep; the others are set aside with the
reason and can be brought back. Across the whole queue, one action keeps one
row per person per program, matching on name and date of birth as far as they
are recorded; the same person in two programs is two enrollments and both stay.

Splitting jammed values, on the Tidy up stage.

Anything else is fixed at the source and loaded again. Every button on the
record panel says what it does when you rest on it. Any unmatched column in the
source row can be shown alongside the record with one click, and the original
file can be opened from there.

### Summary rows

A row that is a total, a subtotal or a heading rather than a person, whether a
bare number, a "Total" in a name column or a "Grand Total" label, is flagged as
exactly that and nothing else. It does not appear as a missing name, a missing
address and a bad ZIP all at once, and it is not counted in any other group.
Setting it aside keeps it out of the data; it stays listed so you can check
none was a real record.

### Set-aside records

Everything set aside, by any decision, downloads as Set_Aside_Records with the
reason on every row and where it came from. Nothing is deleted.

### The menu stays out of the way

The stage menu is a narrow strip showing where you are. It opens over the
content when you rest on it or click the grip, and closes when you move away;
click the grip to pin it open. The content never moves.

### A program set for one file reaches every row

Where a file has no program column, the matching stage's "Fill a field for
this source only" takes a program name for that file, and every row from it
counts under that program: on the Programs stage, in the counts, and in the
files. Where a file has a program column, the default fills only the blank
rows. An earlier version saved the value and then ignored it for Program,
because defaults reached only the built-in fields, so those rows came out
with a blank program; that is fixed, and each fill is recorded in the audit
as coming from that source.

### Choosing which row to keep

Where rows in one file may be one person, any row can be the one kept: "keep
this one" beside each row. The choice shows on the group before it is applied,
and the rows set aside say which row they are a copy of.

### The preview grid

Every column is shown. The grid scrolls sideways inside its own box with the
bar always drawn, the header stays put while scrolling down, the first column
stays put while scrolling sideways, and the page itself never moves. A line
above the grid says how many columns and rows there are.

### One place for each duplicate question

Two rows in the same file that may be one person are decided on Tidy up, where
they are shown side by side, and nowhere else. The review stage does not ask
about them again; it only lists the copies you confirmed, so they can be
brought back.

The same person appearing in several files is not a problem to fix. It is what
the Results stage resolves, counting each person once. The review stage shows
it as a one-line note.

An earlier version asked about within-file pairs in both places under
different wording, which was confusing. It no longer does.

### Groups name the cause, not the symptom

The city is filled from the ZIP, so a row with no usable ZIP reports two
problems: the ZIP is unusable, and the city could not be worked out. Grouping
such a row under the city sends a reviewer to fix the wrong field, and a row
with no ZIP cannot be geocoded either.

Rows are therefore grouped by the most fundamental problem they have. A row
missing its address is an address problem whatever else is wrong. A row with a
ZIP problem is a ZIP problem even when the city also failed, and those rows get
their own group saying so. A city problem is only reported as a city problem
when the ZIP was usable and still did not explain it.

### Seeing the rows behind a group

Preview on any group shows the actual fields, one row per line: identifier,
name, both address lines, city, state and ZIP, every problem on that row, the
file and row number it came from, and what is suggested. Blank values are
marked rather than left as empty space, which is what makes a pattern of blanks
visible at a glance.

Above the rows is a summary of what the group has in common, for example which
problems repeat and which fields are blank across it. That is usually enough to
decide the whole group without paging through it.

### Sorting

Column headings sort. Click one to sort, click again to reverse. Sorting applies
to the whole table rather than the page on screen, so the largest or smallest
values are the ones you see first. The system check, the data previews on
Sources and Map, the rows behind a review group, the row-by-row queue and the
export column list can all be sorted.

The schema table is deliberately not sortable, because its order is the order of
the columns in the exported file.

### Filling a field for one source only

Where one file leaves a field out entirely and you know the value for every row
in it, set it on the Map stage under "Fill a field for this source only". A
common case is a source that never records State, or an export that covers a
single borough.

The value applies to that table alone, fills only blanks, and never replaces a
value the file supplied. A value set here wins over a default on the schema, and
every use is recorded in the audit log with which of the two it came from.

### Choosing which row holds the column names

Files often begin with a title or a note before the real header. On the Map
stage the first rows of the table are shown and you tick the one that holds the
column names. Rows above it are dropped, the table is read again, and the
mapping is set from the new names.

This is what to reach for when a table arrives with numbered columns
(Column_1, Column_2 and so on), which means no header row was recognized.

### Saved progress

Your schema, staging steps, mapping, per-source defaults, header row choices,
run settings and every review decision are saved as you work, so a closed window
does not lose them. When you return, the first screen lists what was saved and
offers to pick it up.

Uploaded files and the rows read from them are not saved. They stay in memory
and are gone when the server stops, which keeps the promise that client data is
never written to disk unless you export it. Resuming asks for the same files
again and reattaches your decisions to them.

One thing is worth naming plainly: a correction typed during review, such as a
corrected borough, is part of a decision and is saved with it. Those are single
field values, never whole rows. If that is not acceptable on a given machine,
turn saved progress off on the first screen and the tool behaves as it did
before.

Saved progress is deleted after seven days. Expired sessions are removed when
the server starts and whenever progress is saved, so an abandoned batch clears
itself. Start over deletes the current saved progress immediately.

### Screen sizes

The layout adapts from a wide desktop down to a phone. On narrower screens the
left rail moves above the content and its stage list scrolls sideways, wide
panels become single columns, and tables that cannot fit scroll rather than
being cut off. No control is hidden at any size, because a control an operator
cannot reach is a feature they do not have.

The page itself never scrolls sideways. Fields are sized to what they hold and
laid out in as many columns as fit, so a wide screen gets more fields across
rather than wider fields, and a dropdown holding a short column name is not
stretched to fill the screen. Anything genuinely wider than the window, such as
a table with many columns, scrolls inside its own box.

`tests/test_layout.py` renders every screen at five widths in a real browser
with data loaded and measures this, so sideways scrolling cannot creep back in.

### Field types

A schema field can be declared as text, whole number, decimal, date, or yes/no.
The type is checked on every value, and a value that does not fit its type sends
the row to review rather than being changed to fit.

A date is stored in one consistent form, so 3/15/2024 from one export and
2024-03-15 from another end up identical in the output. Day-first and month-first
writing, dots or slashes or dashes, a two digit year, and an Excel serial number
are all read. A decimal accepts thousands separators and stores the plain number.
Yes/no accepts Y, yes, true and 1, and stores Yes or No.

### Default values

In Advanced mode every field can carry an optional default, built-in fields as
well as custom ones. When the source leaves that field blank the default is
written in, which is useful when a whole file belongs to one program, or one
borough, and the export does not repeat it on every row.

Three rules keep this safe. A default only fills a gap and never replaces a
value the source provided. Every use is recorded in the audit log, so a reader
can tell which values were supplied rather than read. And a defaulted value is
still validated like any other: a City default that disagrees with the row's ZIP
is sent to review rather than accepted.

Take care with a default on the client identifier. Giving many rows the same ID
makes separate people look like duplicates, so the editor flags it when you set
one.

### Duplicates within a file: proposed, reviewed, then processed out

After processing, the review stage shows rows that appear to be the same
person more than once in the same file, each group with its rows side by side, the fields they matched
on, and the fields that tell them apart, which is what a person needs in order
to judge.

What counts as the same person is a set of your columns, First_Name, Last_Name
and Zip to begin with, and can be changed there; one rule covers every file
however its columns are named, and a file with no column for one of the fields
says so. Matching ignores case, spacing and punctuation, uses the tool's own
address normalization so St and Street agree, and takes a ZIP as its first five
digits. A row blank in any chosen field is never proposed.

Each group is decided by a person: copies, in which case the first row is kept
and the rest are set aside at once, listed under "Copies you confirmed"; or different people, in which
case they are left alone and the built-in check does not pair them again. A
whole file can be decided at once. A group nobody has looked at is kept and
flagged, never removed.
Rows set aside stay listed on the review stage, marked in a Duplicate_In_File
column, and can be brought back. Decisions are saved with your progress and can
be undone.

### A unit designator in every shape people type

A unit at the end of the street is peeled into Address 2 whatever shape its
designator takes: 10R, 10 R with a space inside it, 18L jammed onto the word
as APT18L, 11T after a hash and a colon as Apt#: 11T, or a hyphenated code
such as 12-B or B-12. A designator must carry a digit, except a lone letter
after a hash, so a street named Apartment Way, Unit Lane, Suite Drive or
Penthouse Road is never mistaken for a unit.

### A unit is never taken as the city

When a jammed address is split at its commas, each part is looked at for what
it is. The first part is the street. A part that is a unit (Apt. 4, 4th Fl,
Rear, #4) is the unit wherever it sits, before or after the city. The city is
the last part that is not a unit, and if there is none the city is left blank
and filled from the ZIP. An earlier version took the last comma part as the
city regardless, so "111 Test St, Apt. 4, NY, 11201" produced a city called
"Apt. 4"; that is fixed, and the state spelled out as New York is read as the
state rather than the city. A bare designator such as 14A or 3L standing right
after a street-type word, "117-19 45TH AVE 14A", is a unit with the word left
off and goes to Address 2; only the digits-then-letter shape is taken, so
"Avenue U" and "Route 9" are left as street names.

### A calculated column: the ZIP the address points to

On Tidy up, Add an operation offers a calculated column. Choose the street
column, and optionally a city or borough column and an existing ZIP column,
and the step looks every address up the same way the review stage does, with
Geosupport when it is active and the reference data otherwise. It adds two
columns: the ZIP where the address settles it, and a note on every row with
the reason, whether the evidence for a ZIP that was found or why one could not
be. A street the geocoder cannot place, or one that runs through several ZIPs
without a house number, is left blank. Where an existing ZIP column is given,
rows that already have a ZIP keep it and are not looked up, unless the step is
set to calculate for every row. No value the file already has is changed.

The step says what it achieved as soon as it is added: how many rows got a
ZIP, how many kept one, and how many could not be placed. On the matching
stage the calculated column is chosen for Zip by itself, because a column a
person calculated on purpose is the one they mean. A row whose ZIP could not
be calculated reaches review carrying its reason, "runs through 3 ZIPs; a
house number is needed", for a person to decide.

### Cleaning up after a split

Real exports separate parts of an address with whatever was handy: a dash, a
slash, a semicolon, a pipe. Two things happen so those never leak into the
output.

Before parsing, a separator that sits between spaces is treated as if it were a
comma, so "123 Main St - Apt 3L - Brooklyn NY 11201" splits properly instead of
leaving the unit stuck in the street. Only separators surrounded by whitespace
are converted, which is why 40-22 24th St, 123-A Main St and c/o Jane Doe are
left exactly as written.

After parsing, every piece is tidied: repeated separators collapse to one, any
separator stranded at the start or end is removed, a space before a comma is
closed up, and runs of whitespace collapse. A trailing period survives, because
"123 Main St." is correct.

### When a unit appears in both address lines

Address 1 often carries a unit that Address 2 already holds. The tool treats the
three cases differently, and never picks one value over another on a guess.

If both name the same unit, the copy jammed into the street is removed and
Address 2 keeps it. Labels and punctuation are ignored when comparing, so
"Apt 2A", "apt. 2-a", "#2A" and "2A" all count as the same unit. The row stays
clean, and the street is left in a state the geocoder can match.

If they name different units, for example Apt 2A in the street and Apt 3B in
Address 2, the row goes to review showing both. That is a real contradiction
about where somebody lives and a person decides it.

If Address 2 holds something that is not a unit, such as "c/o Jane Doe" or a
building name, nothing is overwritten and nothing is merged. The row goes to
review so a person decides where the unit belongs.

### What counts as a jammed address

A column is proposed for splitting when it carries more than a street: values
ending in a ZIP, an embedded unit such as Apt 3L or Suite 200, or a city and
state tacked on the end. Each proposal states its own evidence, for example
"100% carry a unit such as Apt or Fl", so the reason is visible before you
accept it. A column that already holds a clean street is left alone.

Name columns are only split when they name a person. Headers such as Program
name, Site name, Agency name or Provider name are deliberately skipped, since
splitting those produces meaningless first and last name columns.

### Starting over

"Start over" sits at the bottom of the left rail. It asks for a second click to
confirm, then clears uploaded files, staging steps, schema changes, mapping,
results and every review decision, and returns to the system check. Files you
already downloaded are not touched, since the tool never writes to disk on its
own.

### Seeing the data

Every table can be inspected on screen. On Sources, "Show data" opens a paged
preview of the file exactly as uploaded. On Map, the same control shows the
table after the prepare steps have run, which is what the column mapping
actually sees, and the columns the prepare steps added are highlighted so it is
obvious where a split street or a split name came from.

### If the interface looks out of date

The server sends the interface with no-store, so a browser will not reuse an old
copy. If a control described here is still missing after an update, you are
running an older copy of the folder rather than a cached page.

### Feature parity between the two interfaces

Crosswalk offers everything the Streamlit interface does, and `tests/test_parity.py`
asserts it so the two cannot drift apart silently. That test exists because an
earlier Crosswalk build quietly dropped three capabilities: the schema editor,
the options on prepare steps, and the optional Geosupport fields. Screen-by-screen
tests missed it, since every screen still returned data. What was missing were
the controls.

In Advanced mode Crosswalk provides the full schema editor (rename a label,
change type or max length, toggle required, add custom passthrough fields,
remove fields, reset to the default, and a default value on custom fields), the complete prepare options (column
picker, six case modes including the two Smart Title variants, sanitize junk
characters, strip edge punctuation, delimiter choice with a custom option, max
splits, and explicit new column names), and all 18 optional Geosupport data
points across five categories, which are appended to the clean export when
Geosupport is active.

### Network exposure

The Crosswalk server binds to 127.0.0.1, so it is reachable only from this
machine. Traffic stays on the loopback interface and never touches a network
adapter, which is why plain HTTP is appropriate here: there is no transit to
intercept. A localhost certificate would have to be self-signed, which trains an
operator to click through browser security warnings for no security gain.

Two protections back that up. The server refuses any request whose Host header
names something other than this machine, which closes the DNS rebinding path
where a hostile web page points its own hostname at the loopback address. And no
CORS policy is published, so a browser will not let another origin read
responses from it.

Two things the app does not do, which the machine must: there is no login, so
any other user or process on the same computer can reach the interface while it
runs, and nothing here substitutes for full-disk encryption and an account
password. Run it on a single-user, encrypted, access-controlled machine, and do
not change the bind address to 0.0.0.0.

### Typeface

The design uses Archivo. It is not bundled, because the application must run
fully offline and no webfont is fetched. Without it the system sans stack is
used, which keeps the layout intact. See `ui/fonts/README.txt` to add it.

## Quick start

Double-click one file. There is no terminal and no command to type.

```
Windows   Crosswalk.vbs
Mac       Crosswalk.command
Linux     ./Crosswalk.sh
```

It opens in the browser by itself. The first run takes a minute or two while it
downloads what it needs, which is the only step that uses the internet.
Everything afterward works with no connection.

To stop it, click "Close Crosswalk" at the bottom left. Closing the browser
window works too. The page tells the tool as it closes, and the tool stops
about fifteen seconds later unless the window comes back, as it does on a
reload. If that message never arrives, the tool stops on its own after about
forty-five seconds of silence, and a browser that never opened at all is
treated the same way. Nothing is left running in the background.

Close Crosswalk asks a plain yes-or-no, shows a goodbye page, and the
process ends a moment later however it was started. It used to set a flag for
the launcher to notice, which did nothing if something else had started the
server.

Only one copy runs at a time. Double-clicking this version while it is already
running simply opens it again. Double-clicking it while an older copy is still
running stops the older copy first and starts this one, so the version you
clicked is the version you get. Before this, the launcher opened whatever was
already on the port, and an old folder that could not be deleted quietly kept
serving the old version.

If you need it gone at once, for example before deleting or replacing the
folder, double-click Stop Crosswalk. It asks the tool to stop, and ends the
process by its recorded id if it must. While running the tool shows in Task
Manager as "Python" under background processes, since it has no window.

Started this way the tool runs with no console, which means it has no standard
output at all. The launcher gives itself one pointing at the log, and tells the
web server not to install its own logging, because the default asks whether the
output is a terminal and there is nothing to ask.

If it cannot start it says why in a message box, in plain words, and writes the
detail to `launch-log.txt` next to the app. The usual cause is Python not being
installed, and the message says where to get it.

There is a short `START HERE.txt` in the folder covering the same ground for
whoever runs it.

### Other ways to start it

`run_crosswalk.bat` on Windows does the same thing with a visible window,
which is useful when you want to watch it start. The original Streamlit
interface is still available through `run.bat` or `run.sh`. By hand:

```
python launch.py
```

## Try it with the sample data

The `sample_data` folder contains fake, obviously-not-real files in all five
supported formats. They exercise the tool's features: a fully jammed address in one
column, names that need splitting, units inside the street, missing cities that the
ZIP fills in, and both confirmed and possible duplicates. Upload some or all of
them to see the full flow. No real client data is included anywhere in this
package.

## What it does

- Merges many source files into one configurable master schema, with per-file
  column mapping. Every original column is kept.
- Cleans values (whitespace, tabs, junk placeholders like NULL and #N/A).
- Splits jammed addresses into street, unit, city, state, and ZIP, and splits
  jammed names into first, middle initial, and last, preserving forms like O'Brien
  and DiNapoli.
- Normalizes ZIPs and boroughs, and fills a missing city or state from the ZIP.
- Geocodes locally. It prefers NYC Geosupport Desktop Edition if installed, and
  otherwise falls back to the included sample address-point file. Coordinates are
  jittered for privacy, and districts are assigned.
- Shows possible duplicates without merging them. It only de-duplicates records
  that share an identical Client ID.
- Routes anything it cannot handle confidently to a review list with a plain
  reason, and guarantees that clean plus review equals the input count.
- Exports a clean list, a review list, a PII-safe audit log, and a per-file quality
  report, in CSV, Excel, or JSON.

## Finding separate tables in one sheet

Reports often place more than one table on a single tab, for example a summary
table beside a client-level table, separated by a blank column. Read naively,
those two datasets get glued together into one corrupted table, and extra sheets
are missed entirely.

On upload the tool scans every sheet, treats fully blank rows and columns as
separators, and reports each table it finds with its cell range, size, columns,
fill rate, any completely empty columns, and any sensitive fields such as date of
birth. Each table is classified as record-level or summary so you can see at a
glance which one holds the client data, and each gets a preview and an include
checkbox. Record-level tables are recommended by default, and you decide what is
compiled. Nothing is merged or included on its own.

A file that holds a single table is used automatically, so ordinary exports are
unaffected. The source of every output row records the file, sheet, and cell
range it came from.

## Fixing review rows and getting one combined file

Rows the tool cannot resolve on its own go to the Manual_Review_Needed export
with their original values and a plain reason. To fix them:

1. Open Manual_Review_Needed in Excel and correct the values in the `orig::`
   columns. Leave the Source_File and Source_Row columns alone, since those tell
   the tool which row each fix belongs to.
2. Save the file.
3. Upload it alongside the original source files and run again.

The tool recognizes it as a corrections file rather than a new data source,
applies each fix to the matching row, and re-validates and geocodes those rows
like any other. The result is one combined clean export, so there is no manual
pasting of files together.

Corrections never bypass validation. A row that is still wrong after the fix
comes back to review with the reason. Fixes that point at a source file you did
not upload, or at a row number that does not exist, are skipped and reported
rather than guessed. Every corrected row is recorded in the audit log with the
corrections file name and the column names changed, never the values, so the
audit stays free of client data.

## System check

The app runs a system check each time it opens, shown at the top of the screen.
It reports the Python version and location, whether each dependency loaded,
whether Geosupport is installed and working, whether GEOFILES is set, and
whether the local reference files are trustworthy. It expands automatically when
something is wrong.

The reference check is worth understanding. It reads the gazetteer file and asks
whether the city recorded on each row agrees with the borough its ZIP belongs to.
Real NYC address data agrees nearly always. The sample file shipped with this
package disagrees on about 81 percent of rows, because it is randomly generated
demo data, so the check reports it as unusable for real work. The district file
shipped here is likewise coarse placeholder geography. Both are fine for trying
the tool and must be replaced, or Geosupport installed, before real client data
is processed.

There is a copyable report at the bottom of the panel. It contains version and
configuration details only, never client data, so it is safe to paste into a
support request.

## Geocoding backend

The included `nyc_address_points.csv` and `nyc_districts.geojson` are small SAMPLE
reference files so the tool runs out of the box. In production, either install NYC
Geosupport Desktop Edition (the City's official engine, which the tool prefers
automatically) or replace the sample files with your real NYC address-point and
district-boundary data.

## Project layout

```
app.py                     the engine plus the original Streamlit workflow
crosswalk_server.py        Crosswalk interface backend (FastAPI)
identity.py                master IDs across systems, and the two client counts
sessions_store.py          saved progress, and the seven day clean-up
review_context.py          what a reviewer needs to decide about one row
column_check.py            checks a matched column really holds that field
wording.py                 plain and precise wording, chosen by mode
program_names.py           groups the same program written differently
audit_trail.py             the complete trail: set-up, engine changes, decisions
setups.py                  named run set-ups, saved and checked before loading
dedupe_rules.py            duplicates within a file, proposed and decided
fill_missing.py            proposes a missing ZIP, city or state from the row itself
ui/                        Crosswalk front end (HTML, CSS, JS, offline)
nyc_address_points.csv     SAMPLE local geocoding reference (replace for production)
nyc_districts.geojson      SAMPLE district boundaries (replace for production)
requirements.txt           dependencies
run.sh / run.bat           one-command launchers
.streamlit/config.toml     telemetry off, bound to localhost
sample_data/               fake input files to try the tool
tools/                     scripts that generated the sample and reference files
table_detect.py            finds the separate tables inside a sheet
tests/test_smoke.py        end-to-end check (lossless, no name leaks, duplicates)
tests/test_table_detect.py table detection checks
tests/test_corrections.py  corrections re-import checks
tests/test_preflight.py    system check diagnostics
tests/test_crosswalk_api.py end to end walk of every Crosswalk stage
tests/test_parity.py       Crosswalk offers every Streamlit capability
tests/test_identity.py     master IDs, the five hard matching situations, the counts
tests/test_layout.py       no sideways scrolling on any screen at any width
tests/test_proof.py        every row of the proof workbook lands where it says
```

## Running the test

```
python tests/test_smoke.py
python tests/test_table_detect.py
python tests/test_corrections.py
python tests/test_preflight.py
python tests/test_crosswalk_api.py
python tests/test_parity.py
python tests/test_identity.py
```

It runs the full pipeline on the sample files and checks the invariants: the clean
and review counts reconcile to the input count, the audit log contains no client
names, and possible duplicates are detected and shown. Exit code 0 means pass.

## Notes

- This is the current working application, packaged to run. It is intended to be
  the starting point for the modular rebuild described in REBUILD_PROMPT.md.
- All processing is offline. For handling real PII, keep the machine encrypted and
  access-controlled, and confirm no outbound network activity, as described in the
  data-flow and verification document.

## Documentation

Everything that describes the code is generated from it, and a test fails when
it goes stale.

| For | Where | Built by |
|---|---|---|
| Engineers: purpose, hard rules, architecture, data flow, every module, class, function and route, the working state, the tests | `docs/TECHNICAL.md` | `python tools/make_docs.py` |
| Users: every stage and element, why it exists and what to do, with screenshots; workflows; cheat sheets | `docs/Crosswalk_User_Guide.docx`, `docs/USER_GUIDE.md` | `node tools/make_guide_docx.js`, `python tools/make_docs.py` |
| Quick reference, one page each | `docs/cheatsheets/*.md` | `python tools/make_docs.py` |
| A walkthrough deck with the narration as notes | `docs/Crosswalk_Walkthrough.pptx` | `node tools/make_deck.js` |
| A narration script for a video tutorial, timed to the deck | `docs/VIDEO_SCRIPT.md` | written by hand |
| Help inside the app: a ? on every stage and complex element | `ui/help.json` | the same file feeds the guide and cheat sheets |
| Screenshots the guide and deck use | `docs/screenshots/` | `python tools/take_screenshots.py` |

The rule for a change: change the code, write the docstring, run
`python tools/take_screenshots.py` if the interface changed, run
`python tools/make_docs.py`, `node tools/make_guide_docx.js` and
`node tools/make_deck.js`, and run the tests. `tests/test_docs.py` checks that
every class and function has a docstring, that the generated documents match
the code, that every help entry has a button in the interface, and that the
screenshots exist.
