# Cheat sheet: The two counts

_One page. Built from `ui/help.json` by `tools/make_docs.py`._

## Results
- **For:** The two numbers the whole effort exists to produce: unique clients across every file, and unique clients per program. Both are worked out from the rows that passed, by an engine that decides who is the same person across systems.
- **Do:** Read the two counts. Where records may be one person, decide the open pairs; the first count is a range until you do. The per-program bars show where people are. Open the printable page to share the counts without any client data.

## Records that may be one person
- **For:** Across systems the same client appears with different identifiers, a changed surname, a nickname, or a mistyped birth date. The first count is only right if each person is counted once.
- **Do:** The engine joins records on its own only where coincidence is not a reasonable explanation. Everything weaker is shown as a pair with its evidence for a person to decide. Until they are decided the count is a range.

## Which names are the same program
- **For:** Systems spell the same program differently. Counted literally, one program looks like several, and a person in one of them appears to be in several.
- **Do:** The tool proposes groups and says why. Click a name to pick it up, click the group it belongs to. Type over a group's name to change what it is counted under. Apply once, then preview the counts.

## What the counts would be
- **For:** Grouping decisions change Goal 2 directly, and it is far better to see that before the report than after.
- **Do:** Preview processes the files with the programs as they stand and shows both counts, program by program. Any change marks the preview out of date; refresh as often as you like.
