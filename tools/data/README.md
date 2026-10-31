# Source extracts for tools/make_zip_table.py

Each file here is a public list of NYC ZIP codes, committed unchanged so the ZIP table can be rebuilt offline. The script reads every extract named in its `SOURCES` list.

| File | What it is | Where it came from | Retrieved |
| --- | --- | --- | --- |
| `nyc_zips_uhf_copy.csv` | Borough, United Hospital Fund neighborhood and ZIP, 178 ZIPs | A public copy of the NYC Health ZIP table, at `https://raw.githubusercontent.com/erikgregorywebb/nyc-housing/master/Data/nyc-zip-codes.csv` | 2026-10-31 |

The first-choice source is NYC Health's own table, `https://www.nyc.gov/assets/doh/downloads/pdf/ah/zipcodetable.pdf`. The cloud session that built M03 couldn't reach nyc.gov, so it used the copy above. To use the original, extract the PDF's text into a CSV with the same three columns, add it here and to `SOURCES`, and run the script again. The script then cross-checks every source and reports any ZIP that one has and another lacks.
