# Changes to the proof workbook's expected answers

Where the spec changes a rule, the ported expectation follows the spec (SPEC 13.1). Each row is one changed answer. `tests/golden/test_changes_log.py` checks every row has all five cells and a rule ID.

| Sheet | Row | Old expected | New expected | Rule |
| --- | --- | --- | --- | --- |
| 10 Jammed name | 3 | Last name `Smith Jr` | Last name `Smith`, suffix `Jr` in its own column | P-PREP-4 |
| 01 Junk and spacing | 1 | REVIEW: first name NULL is missing | Not counted yet, `name_missing` (holds the count) | P-VAL-2 |
| 02 Name casing | 1 to 4 | CLEAN only with a Smart Title tidy-up step | Re-cased by standardizing with no tidy-up step, noted `name_recased` | P-STD-1 |
| 04 ZIP forms | 4 to 6 | REVIEW | Counted, not mapped: `zip_not_valid` or `address_part_missing` (location) | P-VAL-2 |
| 05 City from ZIP | 6 | REVIEW | Counted, not mapped: outside NYC with `address_part_missing` (location) | P-VAL-2 |
| 06 City against ZIP | 1 to 3 | REVIEW | Counted, not mapped: `city_zip_disagree` (location) | P-VAL-2 |
| 06 City against ZIP | 7 | CLEAN: Springfield replaced by Brooklyn | City kept as Springfield, `city_not_recognized` with Brooklyn as a suggestion | P-STD-4 |
| 08 State | 5 and 6 | REVIEW: NJ and CT are not New York | Counted, not mapped: `state_zip_disagree`, because the base row's ZIP 11201 is an NYC ZIP | P-STD-5 |
| 11 Unit in both lines | 9 | REVIEW: two different units | Counted, not mapped: `units_differ` (location) | P-STD-8 |
| 11 Unit in both lines | 10 | REVIEW: Address 2 is not a unit | Counted, not mapped: `address_extra_text` (location) | P-STD-8 |
| 12 Missing required | 3 and 4 | REVIEW: no street, no ZIP | Counted, not mapped: `address_part_missing` (location) | P-VAL-2 |
| 13 Digits in a name | 1 to 3 | REVIEW | Counted, with the soft reason `digits_in_name` | P-VAL-3 |
| 17 Field types | 1 and 3 | One column, read in two orders | Separate tables, because one column in both orders is `date_both_ways` | P-MAP-5 |
