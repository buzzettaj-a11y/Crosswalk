# Cheat sheet: Fixing problems

_One page. Built from `ui/help.json` by `tools/make_docs.py`._

## Fix problems
- **For:** Rows the tool could not finish on its own, grouped by cause so the common ones are dealt with together. The tool never guesses at a person's address or identity; it asks.
- **Do:** Work the groups first. Each says what is wrong, how many rows, and offers a decision for the whole group: look the ZIPs up, accept the rows as they are, set them aside, or send them to the row-by-row queue. Duplicates within a file are decided here too. Choose everything, then Apply once. Anything left goes to the row-by-row queue.

## Row by row
- **For:** The rows that need an individual look. Each shows what is wrong, what the tool can do about it safely, and the original row exactly as it arrived.
- **Do:** Values are never edited one by one here. Fill in what the tool can derive, keep one row of a group of copies, accept a row as it stands, or set it aside. Anything else is fixed at the source and loaded again.

## Deciding a whole group
- **For:** Most problems come in batches with one cause. Deciding them together is faster and more consistent than one row at a time.
- **Do:** Each group offers its own decisions, plus Accept all as they are. A chosen decision shows as "will:" until you Apply; apply them all at once.

## Look up missing ZIPs from the street
- **For:** A row with a street but no ZIP is not stuck. The city's address engine, or the reference data, knows which ZIP a street falls in.
- **Do:** The button lists what would be filled for every row in the group, with the reason. A street that runs through several ZIPs, or that the engine does not know, is left alone and says why. Approve the list and every filled row is checked again.

## Duplicates within a file
- **For:** The same person can be listed twice in one export. Two rows that match on the fields you chose are shown side by side so a person decides whether they are one client or two.
- **Do:** Copies, keep the first: the first row stays and the rest are set aside, listed and recoverable. Keep this one: a different row stays instead. Different people, keep all: every row stays and the tool stops pairing them. Decide, then Apply once; nothing is merged or deleted.
