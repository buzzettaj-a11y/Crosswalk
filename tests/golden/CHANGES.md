# Changes to the proof workbook's expected answers

Where the spec changes a rule, the ported expectation follows the spec (SPEC 13.1). Each row is one changed answer. `tests/golden/test_changes_log.py` checks every row has all five cells and a rule ID.

| Sheet | Row | Old expected | New expected | Rule |
| --- | --- | --- | --- | --- |
| 10 Jammed name | 3 | Last name `Smith Jr` | Last name `Smith`, suffix `Jr` in its own column | P-PREP-4 |
