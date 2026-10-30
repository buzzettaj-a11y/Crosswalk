# Crosswalk: video tutorial script

I cannot record video, so this is the next best thing: a narration script,
one section per slide of `docs/Crosswalk_Walkthrough.pptx`, timed for a
screen recording of about twelve minutes. Read it aloud over a recording of
the app running on the example files (Try it with example data on the first
stage), pausing where it says. Each section names the screenshot in
`docs/screenshots/` that shows what should be on screen.

Speak plainly. The audience does this a few times a year and does not think
in schemas or mappings.

---

## 1. What this is for (00:00 to 00:45)
_On screen: the title slide, then 00_check.png_

Crosswalk takes the client lists your systems export, each in its own shape,
and turns them into one answer: how many people you serve, and how many in
each program. Along the way it cleans every address, puts it on the map, and
works out which records across your systems are the same person. Everything
runs on this computer. Nothing leaves it, and nothing is written to disk until
you download a file.

## 2. Starting it (00:45 to 01:15)
_On screen: the folder, then the browser opening_

Double-click Crosswalk. There is no terminal. It opens in your browser. The
first screen checks this computer: the right Python, the pieces it needs, and
whether Geosupport, the city's own address engine, is set up. If it is not,
the tool says so and uses a small reference file instead, which is fine for
practice and not for real client data. Continue.

## 3. Adding your files (01:15 to 02:15)
_On screen: 01_sources.png, then 01b_sources_showdata.png_

Drop your exports in. The tool finds the tables inside each one; a sheet can
hold a list of people and a summary table side by side, and the summary is
unticked for you. Show data opens the first rows. If a title sits above the
real column names, tick the row that has them; the tool flags a wrong choice.

_Pause on the Skip the steps card._

If you have done this before and the files are clean, this button does every
stage at once and takes you straight to what needs fixing. It stops only when
something would make the run wrong, and says what.

## 4. Columns and tidy-up (02:15 to 03:15)
_On screen: 02_schema.png, then 03_prepare.png_

Every file is turned into one shape: the same columns in the same order. The
standard set works for most work; add a date of birth if your files have one,
because it makes matching people across systems much stronger.

Tidy up is where jammed cells get untangled: a street, an apartment, a city
and a ZIP all in one address column, or a whole name in one column. The tool
proposes the steps; remove any that are wrong. Nothing in the file is
overwritten; every step only adds columns.

## 5. Matching columns (03:15 to 04:30)
_On screen: 04_map.png_

This is the step that matters most. The tool has to know which of your
columns holds the first name, which the street, and so on. It guesses, and
then it checks its guess against the values, because a column in the wrong
place processes without complaint and produces confidently wrong results.

_Point at a warning._

A warning under a field means the values do not look like that field, and it
names the column that does. City and State can be left empty; the ZIP fills
them in. If a file leaves out the program entirely, type it once under Fill a
field for this source only, and every row of that file gets it.

## 6. Programs (04:30 to 06:00)
_On screen: 05_programs.png, then 05b_programs_preview.png_

The second count is clients per program, and it is only right if the same
program is spelled one way. Workforce, Workforce Development and WFD are one
program to you and three to a computer.

_Pick a name up and drop it on a group._

Click a name to pick it up, click the group it belongs to. Type over a group's
name to change what it is counted under. Then press Preview the counts.

_Pause on the preview._

Here are both numbers, program by program, as they would stand. Change a
grouping and refresh; watch the program list until it looks like your real
list of programs. Nothing is decided here; it is a preview.

## 7. Processing (06:00 to 06:45)
_On screen: 06_run.png, then the processing card_

Press Process. The screen grays out and one card tells you what is happening:
which file it is on and how many steps are left. It changes once per file,
not once per row. When it finishes, you see how many rows passed and how many
need a person.

## 8. Fixing problems (06:45 to 09:00)
_On screen: 07_review.png_

Rows the tool could not finish on its own, grouped by cause, so the common
ones are dealt with together. Each group says what is wrong and how many rows.

_Point at the ZIP group._

This group has no usable ZIP. The tool can look the ZIPs up from the street
for the whole group, show every answer with the reason, and fill them in when
you approve. A street it cannot place, or one that runs through several ZIPs,
is left alone and says why.

_Open Duplicates within a file: 07b_review_duplicates.png_

Duplicates within one file are shown side by side. Copies, keep the first: the
first row stays and the rest are set aside, listed and recoverable. Keep this
one, beside any row, keeps that one instead. Different people, keep all,
leaves them. Nothing is merged, nothing is deleted.

Choose what to do with every group, then Apply once.

_Open the row-by-row queue: 07c_queue.png_

Anything left comes here, one row at a time, with what is wrong, the original
row exactly as it arrived, and only the safe actions: fill in what the tool can
derive, keep one of a group, accept as it stands, set aside. You never edit
values one by one here; that is fixed at the source.

## 9. Results (09:00 to 10:15)
_On screen: 08_summary.png_

The two numbers the whole effort exists to produce. Goal 1: unique clients
across every file. Goal 2: unique clients per program, with a bar for each
program. Where records may be one person, the tool shows the pair with its
evidence and asks; until you decide, the first count is a range. When nothing
is open, the count is final.

Open a page to print or share: counts only, no client data.

## 10. Download and next time (10:15 to 11:30)
_On screen: 09_export.png, then 10_audit.png_

Download the files: the two counts as lists, the clean master list, the rows
still needing work with the reason for each, everything set aside, an audit
log safe to share, and a quality report per file.

The audit trail is here and in the menu at any time: everything that changed
and who or what changed it, by identifier only.

Save the set-up. Next quarter, add the new files, load it, and the tool tells
you what still fits and what does not before applying anything.

## 11. Help is on every screen (11:30 to 12:00)
_On screen: 11_help.png_

Every stage and every complex element has a small question mark. Press it for
what that thing is for in the real world and how to use it. The user guide is
the same text, in order, with pictures.

That is Crosswalk. Two numbers you can stand behind, and a trail that shows
how you got them.
