"""
Tests for table detection. Run: python test_table_detect.py
Exit code 0 means every check passed.
"""
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if os.path.basename(os.path.dirname(os.path.abspath(__file__))) == "tests":
    os.chdir(ROOT)
    sys.path.insert(0, ROOT)

import table_detect as td

results = []


def check(label, condition):
    results.append((label, bool(condition)))


def ranges(tables):
    return [t.a1_range for t in tables]


# 1) A normal single table must stay one table, so ordinary files are unchanged.
t = td.detect_in_grid([
    ["ID", "First", "Last", "address1", "city", "state", "zip"],
    ["1", "a", "b", "1 Main St", "Brooklyn", "NY", "11201"],
    ["2", "c", "d", "2 Oak St", "Queens", "NY", "11375"],
])
check("single table stays one table", len(t) == 1)
check("single table is classified as records", t[0].kind == "records")
check("single table header detected", t[0].has_header)

# 2) Two tables side by side, separated by a blank column.
t = td.detect_in_grid([
    ["Program", "Total", "", "ID", "First", "city", "zip"],
    ["Housing", "5", "", "1", "a", "Brooklyn", "11201"],
    ["Youth", "9", "", "2", "b", "Queens", "11375"],
])
check("side by side splits into two", len(t) == 2)
check("side by side ranges are correct", ranges(t) == ["A1:B3", "D1:G3"])
check("summary table classified as summary", t[0].kind == "summary")
check("records table classified as records", t[1].kind == "records")

# 3) Two tables stacked, separated by a blank row.
t = td.detect_in_grid([
    ["ID", "First"],
    ["1", "a"],
    ["", ""],
    ["Program", "Total"],
    ["Housing", "5"],
])
check("stacked splits into two", len(t) == 2)
check("stacked ranges are correct", ranges(t) == ["A1:B2", "A4:B5"])

# 4) Offset from A1 (data starting at B2) must be located correctly.
t = td.detect_in_grid([
    ["", "", "", ""],
    ["", "ID", "First", "city"],
    ["", "1", "a", "Brooklyn"],
])
check("offset table found at B2", ranges(t) == ["B2:D3"])

# 5) A header row is not invented when the first row is numeric.
t = td.detect_in_grid([["1", "2", "3"], ["4", "5", "6"]])
check("no header when first row is numeric", t[0].has_header is False)
check("numbered columns generated", t[0].headers == ["Column_1", "Column_2", "Column_3"])

# 6) Nothing is lost: every data row is preserved in the split tables.
grid = [
    ["Program", "Total", "", "ID", "First"],
    ["Housing", "5", "", "1", "a"],
    ["Youth", "9", "", "2", "b"],
]
t = td.detect_in_grid(grid)
check("all data rows preserved", sum(x.n_rows for x in t) == 4)

# 7) Duplicate header names are made unique rather than colliding.
t = td.detect_in_grid([["ID", "ID", "name"], ["1", "2", "x"]])
check("duplicate headers made unique", len(set(t[0].headers)) == 3)

# 8) Empty and sensitive columns are reported.
t = td.detect_in_grid([
    ["ID", "dob", "address2", "city"],
    ["1", "2001-01-01", "", "Brooklyn"],
    ["2", "1990-05-02", "", "Queens"],
])
check("empty column detected", t[0].empty_columns == ["address2"])
check("sensitive column detected",
      any(c == "dob" for c, _ in t[0].sensitive_columns))

# 9) Blank-ish placeholder tokens count as empty for layout purposes.
t = td.detect_in_grid([
    ["ID", "First", "NULL", "Program", "Total"],
    ["1", "a", "", "Housing", "5"],
])
check("placeholder separator column splits tables", len(t) == 2)

# 10) CSV text with two tables side by side.
t = td.detect_in_delimited(
    "Program,Total,,ID,First\nHousing,5,,1,a\nYouth,9,,2,b\n", source="x.csv")
check("csv side by side splits into two", len(t) == 2)

# 11) The real sample workbook, when present, yields four tables, two of records.
sample = "/mnt/user-data/uploads/TestETOData.xlsx"
if os.path.exists(sample):
    t = td.detect_in_excel(sample, source="TestETOData.xlsx")
    check("sample workbook finds four tables", len(t) == 4)
    check("sample workbook finds two record tables",
          sum(1 for x in t if x.kind == "records") == 2)
    check("sample workbook reads both sheets",
          len({x.sheet for x in t}) == 2)

for label, passed in results:
    print(f"  [{'PASS' if passed else 'FAIL'}] {label}")
ok = all(p for _, p in results)
print(f"TABLE DETECTION TESTS: {'PASS' if ok else 'FAIL'} "
      f"({sum(1 for _, p in results if p)}/{len(results)})")
sys.exit(0 if ok else 1)
