# Cheat sheet: Duplicates

_One page. Built from `ui/help.json` by `tools/make_docs.py`._

## Duplicates within a file
- **For:** The same person can be listed twice in one export. Two rows that match on the fields you chose are shown side by side so a person decides whether they are one client or two.
- **Do:** Copies, keep the first: the first row stays and the rest are set aside, listed and recoverable. Keep this one: a different row stays instead. Different people, keep all: every row stays and the tool stops pairing them. Decide, then Apply once; nothing is merged or deleted.

## Records that may be one person
- **For:** Across systems the same client appears with different identifiers, a changed surname, a nickname, or a mistyped birth date. The first count is only right if each person is counted once.
- **Do:** The engine joins records on its own only where coincidence is not a reasonable explanation. Everything weaker is shown as a pair with its evidence for a person to decide. Until they are decided the count is a range.
