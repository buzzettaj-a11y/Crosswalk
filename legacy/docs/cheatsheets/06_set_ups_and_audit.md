# Cheat sheet: Set-ups and the audit trail

_One page. Built from `ui/help.json` by `tools/make_docs.py`._

## Audit trail
- **For:** Everything that changed and who or what changed it, so any number can be traced back. It holds identifiers and column names only, never a name, address or value, so it can be read and shared safely.
- **Do:** Filter by kind (the set-up, changes the engine made, decisions a person took), by file, or search by identifier. Download the full trail as a text file.

## Saved set-ups
- **For:** Configuring a run is real work. Saving it means next quarter starts from here rather than from scratch.
- **Do:** Save under a name. Loading checks every part against the files loaded now and this version of the tool, and names anything that no longer fits before applying what does. No client data is saved.

## Skip the steps
- **For:** A repeat user with clean-enough files should not have to click through every stage. This does the tidy-up, the matching and the processing using what the tool proposes, then lands on what needs fixing.
- **Do:** If a required field has no column matched it stops and says which file and which field. If a matched column looks wrong it stops and shows the warning, and you choose to fix it first or run anyway.

## Calculated column: ZIP from the address
- **For:** Some files carry addresses but no ZIP. The ZIP can be worked out from the street and borough by the city's address engine, once, for the whole file.
- **Do:** Choose the street column and, if there is one, the city and existing ZIP columns. The step adds the calculated ZIP and a note per row saying why. Rows it could not place go to review carrying that reason.
