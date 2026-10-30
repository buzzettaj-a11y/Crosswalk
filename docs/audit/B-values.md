# Audit B: where Crosswalk changes, fills or matches values wrongly

Scope: the data transformations of the old Crosswalk (Python engine in `app.py`, plus `fill_missing.py`, `dedupe_rules.py`, `program_names.py`, `column_check.py`, `crosswalk_server.py`). Findings are requirements and test cases for the rewrite. Nothing in the original source was changed. Everything below was run on a copy at `/tmp/claude-0/-home-claude/ec68250d-d5ac-549e-8d94-20759c381437/scratchpad/src/agentB`.

## How to read this file

**Severity** (the rubric from the brief, applied one way throughout):

- **High**: a wrong, lost or invented value in a row that is marked clean (nobody reviews it), or a wrong merge or match with no review.
- **Medium**: a wrong value where the row still goes to review, or a misleading confidence or label, or the right text placed in the wrong field in a clean row (nothing lost, but matching and counting suffer).
- **Low**: inconsistent but harmless.

Two judgment calls, stated so you can overrule them: (1) "right text in the wrong field" (for example a neighborhood name left inside Address_1 while City is filled correctly from the ZIP) is Medium, but text that is dropped, replaced or invented is High. (2) The jitter-reversal finding (B-18) is High because privacy is a stated hard rule, even though it sits outside the rubric wording.

**Reach** on each finding says who hits it: the fast path (`/api/express/run`, no match screen), every path, or a rare input. **Where** gives file:line in the original source.

**Spec conflicts.** The two spec documents disagree with each other and with the code in places. Where that matters it is named in the finding (for example B-01 and B-24). Where the code follows the spec and the spec itself is the problem (B-13, B-14, B-16), the finding says so.

**Reference data caveat.** The shipped `nyc_address_points.csv` is synthetic: 3,712 of 4,587 rows (81%) name a city that contradicts their own ZIP, and the built-in preflight reports "fail" (script b14). Every geocoding probe therefore uses a tiny hand-built reference file (`_refdata.py`, or built inline). Geosupport is not installed here, so only the CSV fallback path was tested.

**Re-running a proof.** Every script is in `B-scripts/`; its saved output is in `B-scripts/out/`.

```
cd /tmp/claude-0/-home-claude/ec68250d-d5ac-549e-8d94-20759c381437/scratchpad/audit/B-scripts
. ../../venv-old/bin/activate
python bNN_name.py
```

Status words: CLEAN means the row would land in the clean output with no review. REVIEW means it goes to the review queue with the quoted reason.

## Index

49 findings: 23 High, 17 Medium, 9 Low.

| ID | Sev | Area | Title |
|---|---|---|---|
| B-01 | High | 1 Cell cleaning | Placeholders outside the sentinel list pass as real names, IDs and addresses |
| B-02 | High | 1 Cell cleaning | Windows-1252 / Latin-1 CSV is decoded with replacement characters, rows stay clean |
| B-03 | High | 2 ZIP | Nassau County ZIPs (115xx) are treated as Queens and overwrite the typed city |
| B-04 | High | 2 ZIP | A NYC borough with a non-NYC ZIP (07030, 12345, 99999, 00000) is clean |
| B-05 | High | 4 City and borough | Non-NYC place names are folded into a NYC borough and State defaults to NY |
| B-06 | High | 7 Calculated ZIP | Calculated ZIP truncates garbage to its first five digits |
| B-07 | High | 2 ZIP / 3 Address | A 9-digit ZIP inside an address is read as its last five digits |
| B-08 | High | 3 Address split | "1010 Grand Concourse NY 10452" loses "Concourse" from the street |
| B-09 | High | 3 Address split | A spaced hyphen in a Queens house number ("117 - 19 45th Ave") breaks the address |
| B-10 | High | 3 Address split | A trailing comma segment is read as the city and silently dropped |
| B-11 | High | 5 Name split | Particles, double surnames and compound given names are mis-split with no flag |
| B-12 | High | 5 Name split | Titles and suffixes become first names or last names |
| B-13 | High | 6 Dates of birth | Day and month are swapped silently, so a day-first file is half wrong |
| B-14 | High | 6 Dates of birth | Two-digit year pivot is fixed at 25 ("1/2/26" becomes 1926) |
| B-15 | High | 6 Dates of birth | Future dates are accepted as dates of birth, up to the year 2100 |
| B-16 | High | 6 Dates of birth | Any five-digit string is read as an Excel date with no range check |
| B-17 | High | 8 Geocoding | Fuzzy geocode match lands on a different building or cross street |
| B-18 | High | 8 Geocoding | Privacy jitter can be reversed with the documented seed, and averaged away |
| B-19 | High | 8 Geocoding | District polygons with holes are treated as solid (latent) |
| B-20 | High | 10 Program names | Unconfirmed program-name proposals are applied at run time |
| B-21 | High | 11 Auto-mapping | Auto-map takes the first matching column in file order, not by meaning |
| B-22 | High | 11 Auto-mapping | Program is mapped to a date column; Program ID becomes the Client ID |
| B-23 | High | 11 Auto-mapping | Split-off columns silently replace the real name and address columns |
| B-24 | Medium | 1 Cell cleaning | Zero-width, BOM, soft-hyphen, NUL and a leading apostrophe are not stripped |
| B-25 | Medium | 1 Cell cleaning | Real names "Na", "Nan" and "None" are blanked as null markers |
| B-26 | Medium | 2 ZIP | Full-width and Arabic-Indic digits are accepted as a ZIP |
| B-27 | Medium | 3/4 Address, City | Address text that contradicts the City or ZIP column is discarded with a note only |
| B-28 | Medium | 3 Address split | Neighborhoods outside a 114-name table stay inside Address_1 |
| B-29 | Medium | 3 Address split | A unit swallows the city ("Apt 3 Brooklyn" lands in Address_2) |
| B-30 | Medium | 3 Address split | Lone-letter units ("Apt B", "Unit B", ", B", "5C") stay in the street |
| B-31 | Medium | 4 City and borough | A typed city that is not recognized is overwritten by the ZIP's borough |
| B-32 | Medium | 5 Name split | Extra name tokens are dropped, and the row is clean |
| B-33 | Medium | 5 Name split | Middle-initial placeholders become letters (NMI to N, Jr to J, Unknown to U) |
| B-34 | Medium | 7 fill_missing | Fill proposals ignore house numbers and non-NYC ZIPs, and overstate their evidence |
| B-35 | Medium | 8 Geocoding | Fuzzy matches are labeled "Verified" and pass `require_geocode` |
| B-36 | Medium | 9 Duplicates | The same-ID check runs across files, so two systems that reuse IDs send every row to review |
| B-37 | Medium | 9 Duplicates | "Identical record" ignores date of birth, middle initial and every custom field |
| B-38 | Medium | 9 Duplicates | A saved "copies" decision silently covers a person added later |
| B-39 | Medium | 9 Duplicates | The person key does not fold accents or punctuation, so true duplicates are missed |
| B-40 | Medium | 10 Program names | Proposals join different programs, and the screen shows only "worth a glance" |
| B-41 | Low | 4 City and borough | Marble Hill gives a false City/ZIP conflict |
| B-42 | Low | 3 Address split | "Rear" and "Front" split with a comma but not without |
| B-43 | Low | 5 Name split | Name-aware title case gets a few names wrong |
| B-44 | Low | 1 Cell cleaning | Surnames Sum, Mean and Count with no street are set aside as summary rows |
| B-45 | Low | 8 Geocoding | One early failed row changes every later row's jittered coordinates |
| B-46 | Low | 8 Geocoding | The stored (jittered) point can sit in a different district than the stored district |
| B-47 | Low | 9 Duplicates | The default within-file rule groups different people with common names |
| B-48 | Low | 11 Auto-mapping | "Last Visit" is mapped as Last_Name when it comes before "Surname" |
| B-49 | Low | 11 Auto-mapping | "Address Line 2" before "Address Line 1" is mapped to Address_1 (the check catches it) |

---

# High

### B-01. Placeholders outside the sentinel list pass as real names, IDs and addresses

- **Severity:** High
- **Area:** 1 Cell cleaning
- **Input:** `First_Name = "-"`; `Last_Name = "-"`; `Client_ID = "-"` or `"0"`; `Address_1 = "Homeless"`, `"Unknown"` or `"0"`; `Address_2 = "-"` or `"0"`. In the cleaner alone these also pass through unchanged: `TBD`, `unknown`, `n.a.`, `?`, `XXX`, `#REF!`, `#VALUE!`, `NaT`, `<NA>`, `undefined`.
- **Got:** every one of the named name, ID and address cases is CLEAN and stored as typed (`First='-'`, `ID='-'`, `A1='Homeless'`, `A1='0'`, `A2='-'`). `Address_1 = "-"` and `"N/A"` do go to review ("Missing Address_1"), so the address field is inconsistent with the name and ID fields.
- **Expected:** a placeholder is not a value. A name, ID or street address that is only a dash, a zero or a word like Unknown or Homeless is treated as missing and the row goes to review with the reason "placeholder".
- **Spec conflict:** `crosswalk-described-for-an-ai.md:93` says "a lone dash" becomes empty; `excel-runbook.md:126` says "A dash is not on that list. A cell holding - stays as typed." The code follows the runbook.
- **Where:** `app.py:242` (`NULL_SENTINELS` has nine entries), `app.py:375` (exact-match test only).
- **Reach:** every path. "Homeless" and "Unknown" in an address column are common in shelter and outreach data.
- **Proof:** `python b01_cleaning.py`, `python b02_placeholders_rows.py`
  ```
  dash        '-'        -> '-'          zero  '0'  -> '0'
  unknown     'unknown'  -> 'unknown'    TBD   'TBD' -> 'TBD'     n.a. -> 'n.a.'
  First='-'              -> CLEAN   First='-' Last='Lopez' ...
  Last='-'               -> CLEAN
  Client_ID='-'          -> CLEAN   ID='-'
  Client_ID='0'          -> CLEAN   ID='0'
  Addr='Homeless'        -> CLEAN   A1='Homeless'
  Addr='Unknown'         -> CLEAN   A1='Unknown'
  Addr='0'               -> CLEAN   A1='0'
  Addr='-'               -> REVIEW: Missing Address_1
  Addr2='-'              -> CLEAN   A2='-'
  ```
- **Rewrite requirement:** keep a configurable placeholder list per field (name, ID, address) that includes dash runs, `0`, `unknown`, `tbd`, `n.a.`, `xxx`, `?`, spreadsheet error strings, and address words like `homeless`; match whole cell only; a placeholder in a required field is reported as "placeholder", not as a value. Test: `First_Name="-"` gives Missing First_Name; `Client_ID="0"` gives Missing Client_ID; `Address_1="Homeless"` gives REVIEW with reason "placeholder"; `Address_1="123 Unknown Ave"` stays valid.

### B-02. Windows-1252 / Latin-1 CSV is decoded with replacement characters, rows stay clean

- **Severity:** High
- **Area:** 1 Cell cleaning
- **Input:** a CSV saved by Excel's plain "CSV (Comma delimited)" option (Windows-1252 bytes) with `José Núñez`, `Zoë Müller`, `Ana Peña`, `Renée O'Brien`.
- **Got:** the upload succeeds, the fast-path check reports `ok = True, warnings = [], blockers = []`, and the stored names contain U+FFFD, all CLEAN:
  `First='Jos�' Last='N��ez'`, `First='Zo�' Last='M�ller'`, `Last='Pe�a'`, `First='Ren�e'`. The bytes are lost for good.
- **Expected:** decode as UTF-8 only when valid, otherwise try Windows-1252, or reject the file with a plain message. No stored value may ever contain U+FFFD.
- **Where:** `app.py:3437` (`raw.decode("utf-8-sig", errors="replace")` in the table-detection path the server uses). The older loader `read_uploaded_file` (`app.py:1170`) raises `UnicodeDecodeError` for the same bytes, so the two read paths disagree (b24).
- **Reach:** every CSV or TSV upload through the server. High in practice for NYC client lists, where accented Spanish names are common.
- **Proof:** `python b35_encoding_api.py`; `python b24_invisible.py`
  ```
  express check: ok = True | warnings = [] | blockers = []
  typed José Núñez    -> stored First='Jos�' Last='N��ez'  CLEAN
  typed Zoë Müller    -> stored First='Zo�'  Last='M�ller'  CLEAN
  typed Ana Peña      -> stored First='Ana'  Last='Pe�a'    CLEAN
  typed Renée O'Brien -> stored First='Ren�e' Last="O'Brien" CLEAN
  (b24, read_uploaded_file) latin-1 csv -> UnicodeDecodeError 'utf-8' codec can't decode byte 0xe9
  ```
- **Rewrite requirement:** detect encoding explicitly (BOM, then strict UTF-8, then Windows-1252) and show the detected encoding; any U+FFFD present after decoding sends the row to review. Test: the bytes of `José` in cp1252 produce `First_Name = "José"`; a file with bytes that fit no encoding is rejected, never loaded with replacement characters.

### B-03. Nassau County ZIPs (115xx) are treated as Queens and overwrite the typed city

- **Severity:** High
- **Area:** 2 ZIP (with 4 City)
- **Input:** `City = "Hempstead"`, `ZIP = 11550`, `State = NY`; `City = "Garden City"`, `ZIP = 11530`; `City = "Valley Stream"`, `ZIP = 11580`; `City = "Mineola"`, `ZIP = 11501`, `State` blank; and `City` blank with `ZIP = 11550`.
- **Got:** all CLEAN with `City='Queens'`. The typed city is erased. A typed `Brooklyn` with `11550` goes to review with the misleading text "ZIP 11550 is in Queens".
- **Expected:** 115xx ZIPs are Nassau County, not New York City. The row goes to review ("ZIP is outside NYC") and the typed city is kept.
- **Where:** `app.py:748` (`11351 <= n <= 11697` counts as Queens); `app.py:1637-1655` (an unrecognized or blank city is replaced by the ZIP's borough). The same range appears in the spec reference list `excel-runbook-reference.md:433`, so the spec carries the bug.
- **Reach:** every path. Residents of Hempstead, Garden City, Valley Stream and similar towns appear in NYC agency lists.
- **Proof:** `python b04_city_zip.py`, `python b03_zip.py`
  ```
  Hempstead + Nassau ZIP 11550      -> CLEAN  A1='123 Fulton Ave' City='Queens' St='NY' Zip='11550'
  City blank + Nassau ZIP 11550     -> CLEAN  City='Queens'
  Garden City + ZIP 11530           -> CLEAN  City='Queens'
  Valley Stream + ZIP 11580         -> CLEAN  City='Queens'
  Mineola + 11501, state blank      -> CLEAN  City='Queens' St='NY'
  Brooklyn + Nassau ZIP 11550       -> REVIEW: City/ZIP conflict: City says 'Brooklyn' but ZIP 11550 is in Queens
  borough_from_zip: 11500 11501 11530 11550 11553 11570 11580 11590 11599 -> 'Queens'
  ```
- **Rewrite requirement:** store the assigned NYC ZIPs as an explicit table (from the USPS list, with the borough for each), not as one block 11351-11697, and treat every other ZIP as "not NYC". Test: `Hempstead / 11550` gives REVIEW with the city still `Hempstead`; `Far Rockaway / 11691` stays valid.

### B-04. A NYC borough with a non-NYC ZIP (07030, 12345, 99999, 00000) is clean

- **Severity:** High
- **Area:** 2 ZIP
- **Input:** `City = "Brooklyn"`, `State = NY`, `ZIP` = `07030`, `12345`, `99999` or `00000`.
- **Got:** CLEAN, ZIP stored as typed, nothing flagged.
- **Expected:** a ZIP that is not a NYC ZIP, attached to a NYC borough, is a conflict and goes to review. `00000` and `99999` are not ZIPs at all.
- **Where:** `app.py:685-727` (`normalize_zip` checks the shape only, five digits); `app.py:1637-1655` (the City/ZIP conflict test runs only when `borough_from_zip` returns a borough, so a non-NYC ZIP is never compared to a NYC city).
- **Reach:** every path.
- **Proof:** `python b04_city_zip.py`, `python b03_zip.py`
  ```
  Brooklyn + NJ ZIP 07030 (Hoboken) -> CLEAN  City='Brooklyn' St='NY' Zip='07030'
  Brooklyn + ZIP 99999              -> CLEAN  Zip='99999'
  Brooklyn + ZIP 12345              -> CLEAN  Zip='12345'
  Brooklyn + ZIP 00000              -> CLEAN  Zip='00000'
  normalize_zip('00000') -> ('00000', None, '')   normalize_zip('99999') -> ('99999', None, '')
  ```
- **Rewrite requirement:** validate ZIPs against a real list of USPS ZIPs, and compare every recognized NYC city to it. Test: `Brooklyn / 07030`, `Brooklyn / 12345`, `Brooklyn / 99999` and `Brooklyn / 00000` all give REVIEW with a reason that names the ZIP.

### B-05. Non-NYC place names are folded into a NYC borough and State defaults to NY

- **Severity:** High
- **Area:** 4 City and borough
- **Input:** `State` blank, and (City, ZIP) = (`Chelsea`, `02150`), (`Riverdale`, `20737`), (`Flushing`, `48433`), (`Jamaica`, `05343`), (`Brookline`, `02446`).
- **Got:** CLEAN with City `New York`, `Bronx`, `Queens`, `Queens`, `Brooklyn` and `State='NY'`. "Brookline" is fuzzy-matched to "Brooklyn" at 82% (threshold 80).
- **Expected:** a Massachusetts or Maryland ZIP with a name that happens to match a NYC neighborhood is not a NYC address. A blank State must not become NY when the ZIP is outside NYC. Fuzzy city matches may be proposed, never applied silently.
- **Where:** `app.py:804-843` (`normalize_city`: neighborhood table, then fuzzy at `CITY_FUZZ_THRESHOLD = 80`, `app.py:252`); `app.py:794-795` (blank State becomes NY); `app.py:1637-1655` (no NYC-ZIP test).
- **Reach:** every path. It needs a blank State and a non-NYC place with a NYC-sounding name, so the rate is low, but nothing in the output shows it.
- **Proof:** `python b04_city_zip.py`, `python b08_city_fuzzy.py`
  ```
  Chelsea (MA) + ZIP 02150, state blank   -> CLEAN  City='New York' St='NY' Zip='02150'
  Riverdale (MD) + 20737, state blank     -> CLEAN  City='Bronx'
  Flushing (MI) + 48433, state blank      -> CLEAN  City='Queens'
  Jamaica (VT) + 05343, state blank       -> CLEAN  City='Queens'
  Brookline (MA) + 02446, state blank     -> CLEAN  City='Brooklyn'
  'Brookline' -> 'Brooklyn' note="City: fuzzy-matched 'Brookline'->'Brooklyn' (82%)"
  ```
- **Rewrite requirement:** default State only when the ZIP is a NYC ZIP; apply neighborhood and fuzzy city folding only when the ZIP is NYC or absent; a fuzzy city match is a proposal. Test: `Chelsea / 02150 / State blank` gives REVIEW and State stays blank; `Brookline` is never changed to `Brooklyn` without a person.

### B-06. Calculated ZIP truncates garbage to its first five digits

- **Severity:** High
- **Area:** 7 Calculated ZIP and fill_missing
- **Input:** a file where the operator added the "calculate ZIP" tidy-up step, and the ZIP column holds `112019`, `11201 7`, `11201-12`, `123456789012`, `1 1 2 0 1`, `11201abc`, `99999-0000`.
- **Got:** `Zip_calculated` keeps the first five digits ("kept the ZIP the row already had"), `guess_mapping` maps the Zip role to `Zip_calculated`, and every row is CLEAN: `112019` becomes `11201`, `123456789012` becomes `12345`, `11201abc` becomes `11201`. Only the 4-digit `1120` is caught.
- **Expected:** a malformed ZIP is invalid and goes to review. The calculated column may only keep a ZIP that already validates.
- **Where:** `app.py:1087` (`re.match(r"\d{5}", have.replace(" ", ""))` takes any five leading digits after deleting spaces); `app.py:2854` (the calculated column wins the Zip role).
- **Reach:** only when the calculated-ZIP step is added (it is operator-added, not proposed automatically, `crosswalk_server.py:1550-1571`); then every row.
- **Proof:** `python b26_calc_zip.py`
  ```
  typed ZIP '112019'         -> stored Zip='11201'  CLEAN
  typed ZIP '11201 7'        -> stored Zip='11201'  CLEAN
  typed ZIP '11201-12'       -> stored Zip='11201'  CLEAN
  typed ZIP '123456789012'   -> stored Zip='12345'  CLEAN
  typed ZIP '1 1 2 0 1'      -> stored Zip='11201'  CLEAN
  typed ZIP '11201abc'       -> stored Zip='11201'  CLEAN
  typed ZIP '99999-0000'     -> stored Zip='99999'  CLEAN
  typed ZIP '1120'           -> stored Zip=''       REVIEW: Invalid ZIP Code format: (blank)
  ```
- **Rewrite requirement:** "keep the existing ZIP" means keep it only if it passes the same validation as the ZIP field; otherwise leave it unchanged and let validation fail. Test: `112019`, `11201abc` and `123456789012` all give REVIEW; `11201-1234` gives `11201`.

### B-07. A 9-digit ZIP inside an address is read as its last five digits

- **Severity:** High
- **Area:** 2 ZIP (with 3 Address split)
- **Input:** `Address_1 = "123 Main St, Brooklyn, NY 112011234"`, ZIP column blank. Also the no-comma form `"123 Main St Brooklyn NY 112011234"`.
- **Got:** CLEAN with `Zip='11234'` (the last five digits, a different Brooklyn ZIP). The comma form also stores `Address_1='123 Main St, Brooklyn'`; the no-comma form stores `Address_1='123 Main St Brooklyn NY 1120'`.
- **Expected:** `112011234` is ZIP+4: ZIP `11201`, street `123 Main St`, city Brooklyn. If the tail cannot be read safely, review.
- **Where:** `app.py:401` (`_ZIP_TAIL_RE = (\d{5})(?:-\d{4})?\s*$` has no boundary, so it matches the last five digits of a longer run); `app.py:524` (use). The same input in a ZIP column is handled correctly (`normalize_zip` trims a 9-digit ZIP to the first five, b03).
- **Reach:** jammed addresses only; moderate.
- **Proof:** `python b06_address_cities.py`, `python b07_address_pipeline.py`
  ```
  '123 Main St, Brooklyn, NY 112011234' -> street='123 Main St, Brooklyn' city='NY 1120' zip='11234'
  9-digit ZIP jammed, no Zip column     -> CLEAN  A1='123 Main St, Brooklyn' City='Brooklyn' Zip='11234'
  9-digit ZIP jammed, Zip col blank     -> CLEAN  A1='123 Main St Brooklyn NY 1120' Zip='11234'
  ```
- **Rewrite requirement:** the ZIP tail must be preceded by a non-digit and be exactly 5 or 5+4 digits (with or without a dash). Test: `123 Main St, Brooklyn, NY 112011234` gives street `123 Main St`, city `Brooklyn`, ZIP `11201`; `Apt 1120123 Main St` never yields a ZIP.

### B-08. "1010 Grand Concourse NY 10452" loses "Concourse" from the street

- **Severity:** High
- **Area:** 3 Jammed address split
- **Input:** `Address_1 = "1010 Grand Concourse NY 10452"` (no commas, no City column).
- **Got:** CLEAN, `Address_1='1010 Grand'`, `City='Bronx'` ("mapped neighborhood 'Concourse' to borough 'Bronx'"). With a comma or an explicit `Bronx` it is correct.
- **Expected:** `Address_1 = "1010 Grand Concourse"`. "Grand Concourse" is a main Bronx street; a street name cannot be cut off at its last word.
- **Where:** `app.py:567-581` (no-comma path: the last 1 to 3 words are tested against the borough and neighborhood table, `for n in (3, 2, 1)` at line 573); the table is `app.py:289-346`.
- **Reach:** any jammed address that ends in a word on the table; "Grand Concourse" is the common real case.
- **Proof:** `python b07_address_pipeline.py`
  ```
  Grand Concourse no city      -> CLEAN  A1='1010 Grand' City='Bronx' Zip='10452'
     Flags: ["City: mapped neighborhood 'Concourse' to borough 'Bronx'"]
  Grand Concourse w/ Bronx     -> CLEAN  A1='1010 Grand Concourse' City='Bronx'
  ```
- **Rewrite requirement:** find the street by its street-type word or house-number pattern first; only the text after the street (and unit) is a city candidate. Test: `1010 Grand Concourse NY 10452` gives street `1010 Grand Concourse`, city from ZIP `Bronx`.

### B-09. A spaced hyphen in a Queens house number breaks the address

- **Severity:** High
- **Area:** 3 Jammed address split
- **Input:** `Address_1 = "117 - 19 45th Ave"`, `City = Queens`, `ZIP = 11355`; and `"117 - 19 45th Ave, Flushing, NY 11355"`.
- **Got:** CLEAN. First form: `Address_1='117'` (the rest, "19 45th Ave", is gone). Second form: `Address_1='117, 19 45th Ave'` with a comma in the street.
- **Expected:** `117-19 45th Ave` in both cases.
- **Where:** `app.py:473` (`_normalize_separators` turns any dash with spaces on both sides into a comma). The spec does this on purpose (`excel-runbook.md:186`) but the rule does not protect digit-dash-digit.
- **Reach:** Queens addresses typed with spaces around the hyphen; also spreadsheets that auto-format.
- **Proof:** `python b07_address_pipeline.py`
  ```
  spaced hyphen house number           -> CLEAN  A1='117' A2='' City='Queens' Zip='11355'
  spaced hyphen house number, jammed   -> CLEAN  A1='117, 19 45th Ave' City='Queens'
     Flags: ['Split jammed address into street + city/ZIP', 'Address_1 still contains a comma; possible concatenated frag', ...]
  ```
- **Rewrite requirement:** never treat a dash as a separator when a digit sits on each side; join `digits - digits` at the start of the address. Test: `117 - 19 45th Ave` gives `117-19 45th Ave`; `123 Main St - Apt 4 - Brooklyn` still splits.

### B-10. A trailing comma segment is read as the city and silently dropped

- **Severity:** High
- **Area:** 3 Jammed address split
- **Input:** `Address_1 = "123 Main St, Lower"`, `"123 Main St, Top Floor"`, `"123 Main St, c/o Jane Doe"`, with a `City` column (`Brooklyn`) and ZIP (`11201`).
- **Got:** CLEAN, `Address_1='123 Main St'`, `Address_2=''`. The words "Lower", "Top Floor" and "c/o Jane Doe" are gone. The only flag is "Split jammed address into street + city/ZIP".
- **Expected:** the segment is kept (in Address_2) or the row goes to review. A care-of name or a unit hint must not be thrown away.
- **Where:** `app.py:538-565` (the last non-unit segment becomes `city`); `app.py:1572` (`city_source = src("City") or parsed["city"]`: the City column wins and the parsed segment is discarded without comment).
- **Reach:** any comma address with an extra segment when a City column exists.
- **Proof:** `python b06_address_cities.py`, `python b07_address_pipeline.py`
  ```
  ', Lower' with City col          -> CLEAN  A1='123 Main St' A2='' City='Brooklyn'
  ', Top Floor' with City col      -> CLEAN  A1='123 Main St' A2=''
  ', c/o Jane Doe' with City col   -> CLEAN  A1='123 Main St' A2=''
  split_jammed_address('123 Main St, c/o Jane Doe') -> street='123 Main St' city='c/o Jane Doe'
  ```
- **Rewrite requirement:** a parsed city that does not match the City column or a known place is not discarded; keep it as Address_2 text or flag the row. Test: `123 Main St, c/o Jane Doe` with City `Brooklyn` gives Address_2 `c/o Jane Doe` or a REVIEW row; never an empty Address_2.

### B-11. Particles, double surnames and compound given names are mis-split with no flag

- **Severity:** High
- **Area:** 5 Name split
- **Input:** a single name column in natural order (no comma): `Maria de la Cruz`, `Martin Van Buren`, `Ana Garcia Lopez`, `Mary Jane Watson`, `Kim Soo Jin`, `Ludwig van Beethoven`, `Mohammed bin Salman`.
- **Got:** through the fast path every one is CLEAN: `Maria / D / la Cruz`; `Martin / V / Buren`; `Ana / G / Lopez`; `Mary / J / Watson`; `Kim / S / Jin`; `Ludwig / V / Beethoven`; `Mohammed / B / Salman`. The express check shows no warning.
- **Expected:** `Maria / (none) / de la Cruz`; `Martin / Van Buren`; `Ana / Garcia Lopez` (or review, because the order is not knowable from the text); `Mary Jane / Watson`; Korean and Chinese orders are ambiguous and go to review. The comma form is handled well (`de la Cruz, Maria` is right), so the weakness is the comma-less form.
- **Where:** `app.py:597-654` (`split_jammed_name`: with three or more tokens and no comma, token 2 is the middle initial and the rest is the last name).
- **Reach:** the fast path proposes this split whenever a column holds two to four name parts, and applies it with no screen. Common in Hispanic, Asian and Arabic name data.
- **Proof:** `python b09_names.py`, `python b27_name_split_api.py`
  ```
  'Maria de la Cruz'   -> first='Maria'  mid='D'  last='la Cruz'
  'Martin Van Buren'   -> first='Martin' mid='V'  last='Buren'
  'Ana Garcia Lopez'   -> first='Ana'    mid='G'  last='Lopez'
  'Mary Jane Watson'   -> first='Mary'   mid='J'  last='Watson'
  'Kim Soo Jin'        -> first='Kim'    mid='S'  last='Jin'
  'de la Cruz, Maria'  -> first='Maria'  mid=''   last='de la Cruz'     (correct)
  express check: ok = True | warnings = []
  'Maria de la Cruz'   -> first='Maria' mi='D' last='la Cruz'  CLEAN
  ```
- **Rewrite requirement:** keep a particle list (de, del, de la, van, von, der, bin, al, el, di, da, dos, le, la, st) that stays with the surname; only treat the second token as a middle name when it is a single letter (with or without a period); a three-or-more-token name with no comma and no initial is a REVIEW row ("name order unclear"), never a guess. Test: `Maria de la Cruz` gives last `de la Cruz`; `Ana Garcia Lopez` gives REVIEW; `Maria E Cruz` gives middle `E`.

### B-12. Titles and suffixes become first names or last names

- **Severity:** High
- **Area:** 5 Name split
- **Input:** `Dr. John Smith`, `Mr John Smith`, `Mrs. Jane Doe`, `Rev. John Smith`, `John Smith, MD`, `John Smith PhD`, `John Smith V`, `John Smith VI`, `John Smith 2nd`, `John Smith 3rd`, `Smith, Jr., John`, `Smith, III John`.
- **Got:** `first='Dr.'`; `first='Mr'`; `first='Mrs.'`; `first='Rev.'`; `first='MD' last='John Smith'`; `last='PhD'`; `last='V'`; `last='VI'`; `last='2nd'`; `last='3rd'`; `first='Jr.'`; `first='III'`. Through the fast path `Dr. John Smith`, `John Smith V` and `John Smith, MD` are CLEAN.
- **Expected:** title and professional suffix stripped (and noted), generational suffix kept with the last name (`Smith V`, `Smith 2nd`), first name always the given name.
- **Where:** `app.py:597-654`; the suffix pattern at `app.py:615` knows only Jr, Sr, II, III, IV.
- **Reach:** the fast path; titles are common in clinic and court exports.
- **Proof:** `python b09_names.py`, `python b27_name_split_api.py`
  ```
  'Dr. John Smith'      -> first='Dr.'   mid='J'  last='Smith'
  'John Smith, MD'      -> first='MD'    mid=''   last='John Smith'
  'John Smith PhD'      -> first='John'  mid='S'  last='PhD'
  'John Smith V'        -> first='John'  mid='S'  last='V'
  'John Smith 2nd'      -> first='John'  mid='S'  last='2nd'
  'Smith, Jr., John'    -> first='Jr.'   mid='J'  last='Smith'
  'Dr. John Smith' (fast path) -> first='Dr.' mi='J' last='Smith' CLEAN
  'John Smith, MD' (fast path) -> first='MD' mi='' last='John Smith' CLEAN
  ```
- **Rewrite requirement:** a table of titles (Mr, Mrs, Ms, Dr, Rev, Fr, Sr as title vs suffix by position), professional suffixes (MD, PhD, Esq, RN), and generational suffixes (Jr, Sr, II to X, 2nd to 5th) with a position-aware parser. Test: `Dr. John Smith` gives `John / Smith`; `John Smith V` gives last `Smith V`; `Smith, Jr., John` gives `John / Smith Jr`.

### B-13. Day and month are swapped silently, so a day-first file is half wrong

- **Severity:** High
- **Area:** 6 Dates of birth
- **Input:** `13/04/1990`, `31/12/1990`, `03/04/1990`.
- **Got:** `13/04/1990` is stored as `1990-04-13` (swapped) and `03/04/1990` as `1990-03-04` (not swapped). Both rows are CLEAN with the same note, "DOB was written in a standard form for its type". In a day-first file (3 April 1990 written `03/04/1990`) the first is right and the second is wrong, and nothing says which.
- **Expected:** decide the order once per column from all its values (any first part above 12 means day-first; any second part above 12 means month-first); when no value settles it, review or use a stated setting. A single value that is "wrong way round" is reported as a swap.
- **Spec:** by design, `excel-runbook.md:454` ("Day and month typed the wrong way around are swapped when only one reading is a real date"). The spec rule is the problem.
- **Where:** `app.py:1318-1321`.
- **Reach:** every date column; any file from a day-first system.
- **Proof:** `python b11_dates.py`, `python b12_dob_pipeline.py`
  ```
  '03/04/1990' -> (1990, 3, 4)
  '13/04/1990' -> (1990, 4, 13)
  '31/12/1990' -> (1990, 12, 31)
  '13/04/1990' -> ('CLEAN', '1990-04-13', ['DOB was written in a standard form for its type'])
  ```
- **Rewrite requirement:** column-level format detection with an explicit setting; a row whose value had to be swapped, or whose format is undecidable, is REVIEW. Test: column `[13/04/1990, 03/04/1990]` is day-first and gives `1990-04-13` and `1990-04-03`; column `[03/04/1990]` alone is ambiguous and is REVIEW unless a format is set; column `[04/13/1990, 13/04/1990]` has contradicting rows and is REVIEW.

### B-14. Two-digit year pivot is fixed at 25 ("1/2/26" becomes 1926)

- **Severity:** High
- **Area:** 6 Dates of birth
- **Input:** `1/2/26`, `5/5/26`, `12/25/26`, `1/2/24`, `1/2/25`.
- **Got:** `1/2/26` is stored as `1926-01-02`, `5/5/26` as `1926-05-05`, `12/25/26` as `1926-12-25`; `1/2/25` as `2025-01-02`. All CLEAN. The run date for this audit was 2026-10-30, so a baby born in 2026 is given a birth year of 1926 and an age of 100.
- **Expected:** choose the unique plausible reading (age 0 to 110 on the run date); when both 19yy and 20yy are plausible, review.
- **Spec:** by design, `excel-runbook.md:454` ("25 or less is 20xx, above 25 is 19xx"). The pivot is a constant that was right only in 2025.
- **Where:** `app.py:1316` (`y += 1900 if y > 25 else 2000`).
- **Reach:** every two-digit-year date; worse every year.
- **Proof:** `python b11_dates.py`, `python b12_dob_pipeline.py`
  ```
  '1/2/26'  -> (1926, 1, 2)     '5/5/26'  -> (1926, 5, 5)     '12/25/26' -> (1926, 12, 25)
  '1/2/25'  -> (2025, 1, 2)     '1/2/24'  -> (2024, 1, 2)     '1/2/45'   -> (1945, 1, 2)
  '1/2/26'  -> ('CLEAN', '1926-01-02', [...])
  ```
- **Rewrite requirement:** no hard-coded pivot; take "today" as an input so tests are stable. Test with today = 2026-10-30: `1/2/45` gives `1945-01-02`; `1/2/70` gives `1970-01-02`; `1/2/26` is REVIEW (1926 and 2026 both plausible); `1/2/15` gives `2015-01-02` (1915 is older than 110); `12/25/26` gives `1926-12-25` (2026-12-25 is still in the future).

### B-15. Future dates are accepted as dates of birth, up to the year 2100

- **Severity:** High
- **Area:** 6 Dates of birth
- **Input:** `2045-01-02`, `03/04/2050`, `2099-12-31`, `2100-01-01`, `2026-11-01` (two days after this audit's run date of 2026-10-30), `2027-01-01`.
- **Got:** all parsed; the first four are stored and CLEAN (`2045-01-02` carries no flag at all).
- **Expected:** a date of birth later than today is REVIEW. So is an age above about 110.
- **Where:** `app.py:1323` (`if not (1900 <= y <= 2100)` is the only range check).
- **Reach:** every date-of-birth column; typing mistakes and misaligned columns.
- **Proof:** `python b11_dates.py`, `python b12_dob_pipeline.py`
  ```
  '2045-01-02' -> (2045, 1, 2)    '2099-12-31' -> (2099, 12, 31)    '2100-01-01' -> (2100, 1, 1)
  '2026-11-01' -> (2026, 11, 1)   '03/04/2050' -> (2050, 3, 4)      '2101-01-01' -> None
  '2045-01-02'  -> ('CLEAN', '2045-01-02', [])
  '03/04/2050'  -> ('CLEAN', '2050-03-04', [...])
  ```
- **Rewrite requirement:** DOB validation takes "today" as an input and rejects dates after it and ages over 110 (configurable). Test with today = 2026-10-30: `2026-10-30` valid, `2026-10-31` REVIEW, `2045-01-02` REVIEW, `1900-01-01` REVIEW.

### B-16. Any five-digit string is read as an Excel date with no range check

- **Severity:** High
- **Area:** 6 Dates of birth
- **Input:** `12345`, `99999`, `00000`, `73051`, `60000`, `10000` in a date field (for example a ZIP landing in the DOB column after a column shift).
- **Got:** CLEAN with `1933-10-18`, `2173-10-13`, `1899-12-30`, `2100-01-01`, `2064-04-08`, `1927-05-18`. The 1900 to 2100 check is never reached for these. `32874.0` and `32874.5` (what a float-typed Excel column produces) are rejected.
- **Expected:** accept an Excel serial only when it lands in the plausible date-of-birth range and the rest of the column is also serial numbers; otherwise REVIEW. `32874` in a column of serials is `1990-01-01`.
- **Spec:** by design, `excel-runbook.md:454` allows "a 5-digit Excel date number", but not unbounded ones.
- **Where:** `app.py:1299-1306` (the serial branch returns before the range test at `app.py:1323`).
- **Reach:** moderate; the column-shift error it hides is common.
- **Proof:** `python b11_dates.py`, `python b12_dob_pipeline.py`
  ```
  '12345' -> (1933, 10, 18)    '99999' -> (2173, 10, 13)    '00000' -> (1899, 12, 30)
  '73051' -> (2100, 1, 1)      '60000' -> (2064, 4, 8)      '32874.0' -> None
  '99999' -> ('CLEAN', '2173-10-13', [...])    '00000' -> ('CLEAN', '1899-12-30', [...])
  ```
- **Rewrite requirement:** run every parsed date, whatever the route, through the same range check; decide serial-versus-text by the whole column. Test: `99999`, `00000` and `73051` are REVIEW; a column `[32874, 33000]` gives `1990-01-01` and `1990-05-06`; a mixed column `[03/04/1990, 12345]` sends `12345` to REVIEW.

### B-17. Fuzzy geocode match lands on a different building or cross street

- **Severity:** High
- **Area:** 8 Geocoding fallback
- **Input:** reference file holds only the neighbor address, ZIP the same. Ask for: `111 Main St` (ref `11 Main St`), `1 Main St` (ref `11 Main St`), `Avenue U` (ref `Avenue V`), `40 W 100 St` (ref `100 W 40 St`), `100 W 100 St` (ref `100 W 10 St`), `12 W 40 St` (ref `12 W 4 St`), `45 Beach 90 St` (ref `45 Beach 9 St`).
- **Got:** every one is CLEAN with the neighbor's coordinates, `Geocode_Confidence = Low`, `Verification_Status = "Verified (low confidence)"`. The stored point, and the Senate, Assembly and Council districts taken from it, belong to another place. Example: `1 Main St`, truly in district 10/20/30, is given district 11/21/31 from `11 Main St`.
- **Expected:** a different house number or a different street number is a different place. No match, blank coordinates, "Unverified" (or review when geocoding is required).
- **Where:** `app.py:1915-1951` (`geocode_record`); `app.py:1947` (accept at ratio 88, `ADDRESS_FUZZ_THRESHOLD`, `app.py:253`); the score is `thefuzz` `token_sort_ratio`, which ignores word order and treats one extra digit as a near match.
- **Reach:** every row that has no exact match and a similar address in the same ZIP; the more complete the reference file, the more neighbors it offers.
- **Proof:** `python b15_geocode_fuzzy.py`, `python b17_districts.py`, `python b31_ratio_table.py`
  ```
  ask 111 Main St, ref has 11 Main St only    CLEAN | status='Verified (low confidence)' conf='Low' geo=fuzzy latlon=('40.704000', '-73.980000')
  ask Avenue U, ref has Avenue V only         CLEAN | status='Verified (low confidence)' ... ('40.595000', '-73.960000')
  ask 40 W 100 St, ref has 100 W 40 St        CLEAN | status='Verified (low confidence)' ... ('40.754000', '-73.986000')
  ask 100 W 100 St, ref has 100 W 10 St only  CLEAN | status='Verified (low confidence)'
  ask 12 W 40 St, ref has 12 W 4 St only      CLEAN | status='Verified (low confidence)'
  ask 45 Beach 90 St, ref has 45 Beach 9 St   CLEAN | status='Verified (low confidence)'
  ratios: 111 Main St/11 Main St 97; 40 W 100 St/100 W 40 St 100; 12 W 4 St/12 W 40 St 97; 20 Park Ave/200 Park Ave 97; 1234 Main St/1243 Main St 94
  ask '1 Main St' (truly district A, 10/20/30), ref only '11 Main St' (district B)
     -> ('CLEAN', 'Verified (low confidence)', 'Low', '40.703431', '-73.980159', ('11', '21', '31'))
  ```
- **Rewrite requirement:** compare the house number and every number in the street name exactly; allow fuzziness only on alphabetic words, in order, and only to propose, with the percent and the matched address shown. Test: `111 Main St` vs `11 Main St`, `40 W 100 St` vs `100 W 40 St`, `Avenue U` vs `Avenue V`, `12 W 40 St` vs `12 W 4 St` are all no-match; `123 Fultin St` vs `123 Fulton St` is a proposal that needs a person.

### B-18. Privacy jitter can be reversed with the documented seed, and averaged away

- **Severity:** High (privacy rule)
- **Area:** 8 Geocoding fallback
- **Input:** a run with the default settings (seed 1337, jitter on), 400 clients each at a distinct address; and 300 clients at one address.
- **Got:** (a) With the seed from the docs and the row order, the true points are recovered with a worst error of 0.23 ft over 400 rows (rounding alone is about 0.4 ft). (b) The 300 clients at one address get 300 distinct points, and the centroid of those points is 9.5 ft from the true door (19.4 ft with 20 clients, 82.6 ft with 5). Distance (150 to 250 ft) and determinism hold.
- **Expected:** "no stored point is a client's front door" (`crosswalk-described-for-an-ai.md:134`). Neither the documented default seed nor many clients at one address may recover the address.
- **Where:** `app.py:1902-1912` (`jitter_point` draws a fresh offset per row); `app.py:2326` (`random.Random(jitter_seed)`); seed default 1337 in `crosswalk_server.py:106`, documented in `crosswalk-described-for-an-ai.md:22,134`, and shown in the UI (`app.py:3706`).
- **Reach:** every run with jitter on, which is the default.
- **Proof:** `python b16_jitter_districts.py`
  ```
  jitter distance over 400 rows: min=150.5 max=250.4 mean=201.6 ft      all within 150-250 ft: True
  300 clients at 1 Test St: distinct stored points: 300
  centroid of the 300 jittered points is 9.5 ft from the true door
     centroid of first 5 points: 82.6 ft from the true door
     centroid of first 20 points: 19.4 ft from the true door
  undoing the jitter with seed 1337 and row order: max error 0.23 ft over 400 rows
  ```
- **Rewrite requirement:** one displaced point per address (every client at an address shares it), derived from a keyed hash of the address with a secret that never appears in the output, the docs or the UI, and independent of row order. Test: 300 clients at one address have one stored point, 150 to 250 ft from the door; the same input in a different row order gives the same points; reversing with seed 1337 leaves an error above 100 ft.

### B-19. District polygons with holes are treated as solid (latent)

- **Severity:** High (latent: the shipped district file has no holes)
- **Area:** 8 Geocoding fallback
- **Input:** district 1 is a square with a square hole; district 2 fills the hole. Ask for a point inside the hole.
- **Got:** `Senate/Assembly/Council = 1/1/1` (district 1, the donut) when the point belongs to district 2.
- **Expected:** a point in a hole is outside that polygon, so district 2.
- **Where:** `app.py:2005-2033` (`_extract_polygons` keeps every ring); `app.py:2036-2043` (`assign_districts` tests each ring as a filled polygon and returns the first hit, whatever the ring's role).
- **Reach:** zero with the shipped sample file (each polygon has one ring); real boundary files contain enclaves.
- **Proof:** `python b25_district_holes.py`
  ```
  point inside the hole (-73.95, 40.70), which belongs to district 2: {'Senate_District': '1', 'Assembly_District': '1', 'Council_District': '1'}
  point in the donut body (-73.99, 40.62), district 1: {'Senate_District': '1', 'Assembly_District': '1', 'Council_District': '1'}
  shipped district file features: 5 rings per polygon: [1, 1, 1, 1, 1]
  ```
- **Rewrite requirement:** treat ring 0 as the outer boundary and later rings as holes (GeoJSON rule), and use a tested point-in-polygon library or routine. Test: the donut and plug fixture above returns district 2 for the hole point and district 1 for the body point; a point on a shared edge returns exactly one district.

### B-20. Unconfirmed program-name proposals are applied at run time

- **Severity:** High
- **Area:** 10 Program names
- **Input:** three files with programs `Youth Services`, `Youth Employment`, `Level 1`, `Level 2`. The person opens the Programs screen (or just loads it) and clicks nothing.
- **Got:** the screen shows the groups with `needs_confirming = True`, but the server has already written the alias map (`Youth Services` to `Youth Employment`, `Level 1` to `Level 2`). The run stores the merged names (`Youth Employment: 16`, `Level 2: 7`) and the audit says "recorded as 'Youth Employment', the agreed name for it", though nobody agreed.
- **Expected:** a proposal with `needs_confirming = True` changes nothing until a person accepts it. Different programs (Level 1 and Level 2) are never merged without a decision.
- **Where:** `crosswalk_server.py:2321-2353` (`_program_group_state` sets `S["program_aliases"] = build_alias_map(...)` straight from `suggest_groups`); `program_names.py:222-228`; `app.py:1740-1755` (the "agreed name" wording and the replacement).
- **Reach:** every run with more than one program spelling, including the fast path.
- **Proof:** `python b20_programs_api.py`
  ```
  proposed groups shown on Programs stage:
      Youth Employment ['Youth Employment', 'Youth Services'] needs_confirming = True
      Level 2 ['Level 2', 'Level 1'] needs_confirming = True
  server alias map after only LOADING the screen: {'Youth Employment': 'Youth Employment', 'Youth Services': 'Youth Employment', 'Level 2': 'Level 2', 'Level 1': 'Level 2'}
  Program stored on the processed rows (no person confirmed anything): Counter({'Youth Employment': 16, 'Level 2': 7})
  flags example: ["Program 'Youth Services' recorded as 'Youth Employment', the agreed name for it"]
  ```
- **Rewrite requirement:** keep two lists, proposed and accepted; only accepted groups reach the alias map and the audit text; a name without an accepted group keeps its spelling. Test: after upload with `Youth Services` and `Youth Employment` and no click, the output program values are unchanged; after one accept, only that group is merged, and the audit says who accepted it.

### B-21. Auto-map takes the first matching column in file order, not by meaning

- **Severity:** High
- **Area:** 11 Column check and auto-mapping
- **Input:** (a) headers `Emergency Contact First Name, Emergency Contact Last Name, First Name, Last Name, Client ID, ...`; (b) `Provider First Name, Provider Last Name, Client First Name, Client Last Name, ...`; (c) `Mailing Address, Mailing City, Mailing State, Mailing Zip` before `Home Address, Home City, Home State, Home Zip`.
- **Got:** (a) the emergency contact's names are stored as the client's, CLEAN, with express check `ok = True` and no warning (`First='Rosa' Last='Diaz'` where the client is Ana Lopez). (b) `First_Name = Provider First Name`. (c) `Address_1/City/State/Zip` come from the Mailing columns, CLEAN, no warning. Put the same columns in a different order and the mapping changes.
- **Expected:** a column named for another person or purpose (emergency contact, provider, caseworker, employer, mailing, parent, guardian, birth) is not a candidate for the client's own field; when two columns could fill one role, the choice is shown and confirmed, in the fast path as well.
- **Where:** `app.py:2767-2864` (`guess_mapping`). The exact-name pass (lines 2817-2820) only matches underscore names such as `first_name`, so spaced headers (`First Name`) fall to the whole-token pass (lines 2821-2825), which accepts any header that merely contains the candidate's words, in file order. `Emergency Contact First Name` and `Provider First Name` contain "first name", so the first one in the file wins. No qualifier words are excluded for the name, address or ZIP roles (the only avoid list is for Program, line 2863). `Caseworker First` is skipped only because it does not contain the word "name".
- **Reach:** the fast path, which has no match screen, applies the guess unseen. Guided mode shows it.
- **Proof:** `python b36_mapping_end_to_end.py`, `python b21_mapping.py`, `python b22_mapping_check.py`
  ```
  Emergency-contact name columns come first in the file
     mapped: {'First_Name': 'Emergency Contact First Name', 'Last_Name': 'Emergency Contact Last Name', ...}
     express check ok = True | warnings = [] | blockers = []
     stored First='Rosa' Last='Diaz' ID='5001' A1='10 Main St' City='Brooklyn' Zip='11201'  CLEAN
  Mailing address columns come before Home address columns
     mapped: {'Address_1': 'Mailing Address', 'City': 'Mailing City', 'State': 'Mailing State', 'Zip': 'Mailing Zip', ...}
     express check ok = True | warnings = []
     stored First='Ana' Last='Lopez' ID='5101' A1='99 Elm St' City='Brooklyn' Zip='11202'  CLEAN
  (b21) ['Provider First Name', 'Provider Last Name', 'Client First Name', ...] -> First_Name: 'Provider First Name'
  ```
  Place of Birth City before City of Residence is also mapped to City (b21, b36); the stored City stayed right only because a valid ZIP replaces an unrecognized city.
- **Rewrite requirement:** score columns by role words and by the values in them; keep a deny list of qualifier words per role; when two candidates remain, do not choose, and put the question in front of the person. Test: header order `[Emergency Contact First Name, ..., First Name, ...]` maps First_Name to `First Name`; `[Mailing Address ..., Home Address ...]` yields an "which address is the client's?" question and no silent choice; reordering the columns never changes the mapping.

### B-22. Program is mapped to a date column; Program ID becomes the Client ID

- **Severity:** High
- **Area:** 11 Column check and auto-mapping
- **Input:** (a) no Program column, but `Program Start Date` (or `Service Date` before `Service Provider`) holding US-format dates `03/04/2024`; (b) a file whose only ID-like column is `Program ID` with a different value per row (`P-7`, `P-8`).
- **Got:** (a) `Program` is mapped to the date column; the express check passes and every row is CLEAN with `Program='03/04/2024'`. The check does catch ISO dates (`2024-03-04` fails as "numbers, which look like program codes"), but not US dates. (b) `Program ID` is mapped to both `Client_ID` and `Program`; no warning when values are unique; rows are CLEAN with `ID='P-7'`, `Program='P-7'`. With repeated values the check warns and the fast path stops.
- **Expected:** a date column is never a Program; an ID column named for a program, case, household or parent is not the Client ID; one column cannot fill two roles.
- **Where:** `app.py:2841-2843` (Client_ID accepts any header containing the word `id`, so `Program ID` qualifies); `app.py:2858-2863` (Program takes the first header containing `program`, so `Program Start Date` qualifies; the id-word avoid list handles `Program ID` here); `crosswalk_server.py:298-305` (`_match_custom`, used for the Program field on the server, matches `key in ck or ck in key` as a raw substring, which is how `Program ID` also becomes Program; the `guess_mapping` docstring says raw substring tests are deliberately not used); `column_check.py:104-106` (date-like test is applied to Address_1 only) and `column_check.py:214-215` (Program "numeric" test is `[\d.\-]+`, which does not match slashes).
- **Reach:** files without a dedicated Program or Client ID column; fast path.
- **Proof:** `python b36_mapping_end_to_end.py`, `python b22_mapping_check.py`
  ```
  No Program column, but 'Program Start Date' with US-format dates
     mapped: {..., 'Program': 'Program Start Date'}   express check ok = True | warnings = []
     stored ... Program='03/04/2024'  CLEAN
  (b22, ISO dates) Program: problem - These are numbers, which look like program codes rather than program names.
  'Program ID' only, unique per row
     mapped: {..., 'Client_ID': 'Program ID', ..., 'Program': 'Program ID'}   express check ok = True | warnings = []
     stored ID='P-7' ... Program='P-7'  CLEAN
  ```
- **Rewrite requirement:** a column may fill one role only; Program must not be date-shaped in any format; a Client_ID candidate must not carry a qualifier (program, case, household, parent, provider). Test: header `[..., Program Start Date]` leaves Program unmapped; `[..., Program ID]` leaves Client_ID unmapped and blocks the fast path with a "no client ID" message.

### B-23. Split-off columns silently replace the real name and address columns

- **Severity:** High
- **Area:** 11 Column check and auto-mapping
- **Input:** (a) a file with `Caseworker Name` (one combined column) plus `First Name` and `Last Name` for the client; (b) a file with a real `Street Address`, `City`, `State`, `Zip` plus an `Employer Address` column (`"500 Work Ave, Manhattan, NY 10001"`).
- **Got:** the fast path proposes splitting `Caseworker Name` and `Employer Address` and then maps the split columns ahead of the real ones. (a) Every client row stores the caseworker's name (`Ana Lopez` is stored as `Jane Doe`), CLEAN. (b) `Address_1 = '500 Work Ave'` (the employer's street) beside the client's own City and ZIP, CLEAN. Express check `ok = True`, `warnings = []` both times.
- **Expected:** a derived column fills a role only when the file has no real column for it, and a split of a column that is not the client's name or address is never proposed.
- **Where:** `app.py:2835` (`"First_Name": derived("_first") or find(...)`) and `app.py:2845` (`"Address_1": derived("_street") or find(...)`): the `or` puts the derived column first. Split proposals come from `auto_prep_ops`, `app.py:2867-2988`.
- **Reach:** fast path; any file with a second person or second address in one column.
- **Proof:** `python b28_split_hijack_api.py`, `python b29_addr_hijack_api.py`
  ```
  matched columns: {'First_Name': 'Caseworker Name_first', 'Middle_Initial': 'Caseworker Name_middle', 'Last_Name': 'Caseworker Name_last', 'Client_ID': 'Client ID', ...}
  express check: ok = True warnings = []
  client Ana Lopez   -> stored First='Jane' Last='Doe' CLEAN
  client Bo Chen     -> stored First='Raj' Last='Patel' CLEAN
  ...
  matched columns: {..., 'Address_1': 'Employer Address_street', 'Address_2': 'Employer Address_address2', 'City': 'City', 'Zip': 'Zip'}
  client Ana Lopez: stored Address_1='500 Work Ave' City='Brooklyn' Zip='11201' CLEAN
  ```
- **Rewrite requirement:** real columns win over derived ones; derived columns are proposed only for the column that the mapper already picked for that role. Test: file with `Caseworker Name, First Name, Last Name` stores `First Name` and `Last Name`; file with `Street Address` and `Employer Address` stores `Street Address`.

---

# Medium

### B-24. Zero-width, BOM, soft-hyphen, NUL and a leading apostrophe are not stripped

- **Severity:** Medium (the stored value is dirty and duplicates are missed, but no value is lost; High if downstream joins on the ID)
- **Area:** 1 Cell cleaning
- **Input:** `First_Name = "Ana\u200b"`, `"\ufeffAna"`, `"An\u00ada"`, `"Ana\x00"`; two rows with `Client_ID = "A1"` and `"A1\u200b"`; `ZIP = "'11201"`; `First_Name = "'Ana"`; `Client_ID = "'0012345"`.
- **Got:** the invisible characters stay and the rows are CLEAN. The two IDs are not seen as the same (both CLEAN; with identical plain IDs the second is correctly set aside). `ZIP "'11201"` goes to review as invalid, but `Client_ID "'0012345"` is stored with its apostrophe.
- **Expected:** invisible characters removed; Excel's text-marker apostrophe removed from digit strings. For the invisible characters the spec agrees: `crosswalk-described-for-an-ai.md:93` ("zero-width and control characters are removed; smart quotes become plain ones"). `excel-runbook.md:126-127` says "Nothing else changes". The documents disagree and the code follows neither (smart quotes also stay). The apostrophe case is not in either document.
- **Where:** `app.py:353-377` (`clean_cell` handles only tab, CR, LF, whitespace runs).
- **Reach:** pasted or exported data; unpredictable and invisible.
- **Proof:** `python b01_cleaning.py`, `python b24_invisible.py`, `python b02_placeholders_rows.py`
  ```
  zwsp 'Ana\u200bMaria' -> 'Ana\u200bMaria'   bom '\ufeffAna' -> '\ufeffAna'   soft hyphen -> unchanged   NUL -> unchanged
  'A1' -> CLEAN
  'A1\u200b' -> CLEAN          (with identical plain IDs: 'A1' -> CLEAN, 'A1' -> REVIEW: Confirmed duplicate)
  'Ana\u200b' -> CLEAN 'Ana\u200b'
  Zip="'11201" -> REVIEW: Invalid ZIP Code format: '11201      Client_ID="'0012345" -> CLEAN  ID="'0012345"
  ```
- **Rewrite requirement:** NFC-normalize and remove category Cf and Cc characters (except tab, CR, LF, which become spaces) and a single leading apostrophe on a digit string; compare IDs and names on the cleaned form. Test: `Ana\u200b` is `Ana`; `A1\u200b` and `A1` are the same ID; `'07030` is `07030`.

### B-25. Real names "Na", "Nan" and "None" are blanked as null markers

- **Severity:** Medium (the row goes to review, but with a misleading reason)
- **Area:** 1 Cell cleaning
- **Input:** `Last_Name = "Na"` (a Korean and Chinese surname), `First_Name = "Nan"`, `Last_Name = "None"`; and a correction typed as `Nan` or `None`.
- **Got:** the cell becomes empty and the row is REVIEW "Missing Last_Name" or "Missing First_Name", with no hint that the person wrote a name. In the corrections reader `Nan` and `None` become empty and `Na` does not, so the two readers disagree.
- **Expected:** the name is kept and the row is flagged "looks like a placeholder: 'Na'" so that approving as entered stores it. A person is not unloadable.
- **Where:** `app.py:242` (`NULL_SENTINELS` includes `na`, `nan`, `none`); `app.py:375`; `app.py:3341-3346` (`_corr_value` blanks `nan` and `none`).
- **Reach:** every path; rare names, but the failure is permanent for those people.
- **Proof:** `python b02_placeholders_rows.py`, `python b34_accents_corr_encoding.py`
  ```
  Last='Na' (real surname)   -> REVIEW: Missing Last_Name      First='Ana' Last=''
  First='Nan' (real name)    -> REVIEW: Missing First_Name
  Last='None'                -> REVIEW: Missing Last_Name
  _corr_value: 'Na' -> 'Na'    'Nan' -> ''    'None' -> ''    'nan' -> ''    'N/A' -> 'N/A'
  ```
- **Rewrite requirement:** null markers apply to non-name fields; in a name field a marker is kept and flagged with the original text. Test: `Last_Name = "Na"` gives REVIEW with the message naming `Na`, and after "approve as entered" the output has `Na`.

### B-26. Full-width and Arabic-Indic digits are accepted as a ZIP

- **Severity:** Medium (the value is semantically right but stored in the wrong characters; every later ZIP match fails)
- **Area:** 2 ZIP
- **Input:** `ZIP = "１１２０１"` (full-width) and `"١١٢٠١"` (Arabic-Indic).
- **Got:** CLEAN. The ZIP is stored in those characters, and the city is filled as `Brooklyn` (Python's `int()` reads them). The geocoder bucket for ZIP `11201` will not match.
- **Expected:** full-width digits normalized to ASCII; any other script of digits goes to review.
- **Where:** `app.py:685-727` (`\d` in Python matches any Unicode digit).
- **Reach:** rare.
- **Proof:** `python b24_invisible.py`, `python b03_zip.py`
  ```
  '１１２０１' -> CLEAN Zip= '１１２０１' City= Brooklyn
  '١١٢٠١'     -> CLEAN Zip= '١١٢٠١' City= Brooklyn
  normalize_zip('١١٢٠١') -> ('١١٢٠١', None, '')
  ```
- **Rewrite requirement:** match ZIP digits as `[0-9]` after NFKC normalization. Test: full-width `１１２０１` stores `11201`; `١١٢٠١` is REVIEW.

### B-27. Address text that contradicts the City or ZIP column is discarded with a note only

- **Severity:** Medium (one of the two values is wrong and the row is clean, but the choice is recorded)
- **Area:** 3 Jammed address split (with 4 City)
- **Input:** `Address_1 = "123 Main St, Brooklyn"`, `City = Queens`, `ZIP = 11355`; and `Address_1 = "123 Main St, Brooklyn, NY 11201"`, `City = Brooklyn`, `ZIP = 11234`.
- **Got:** both CLEAN. First: City `Queens`, the text's "Brooklyn" gone, no flag beyond "Split jammed address". Second: ZIP `11234` kept, with a flag "Zip: kept mapped column '11234'; address text showed differing '11201'" that does not send the row to review.
- **Expected:** two sources that disagree send the row to review, with both values shown.
- **Where:** `app.py:1572` (`src("City") or parsed["city"]`); `app.py:685-727` (the ZIP conflict note, with the comment "trust the explicitly-mapped column, but record it").
- **Reach:** jammed Address_1 plus separate City and ZIP columns.
- **Proof:** `python b07_address_pipeline.py`
  ```
  parsed city disagrees with City col   -> CLEAN  A1='123 Main St' City='Queens' Zip='11355'   Flags: ['Split jammed address into street + city/ZIP']
  parsed ZIP disagrees with Zip col     -> CLEAN  City='Brooklyn' Zip='11234'
     Flags: [..., "Zip: kept mapped column '11234'; address text showed differi"]
  ```
- **Rewrite requirement:** any disagreement between a parsed address part and its own column is a REVIEW reason. Test: the two inputs above both give REVIEW with a reason that shows both values.

### B-28. Neighborhoods outside a 114-name table stay inside Address_1

- **Severity:** Medium (right text, wrong field; City is correct because the ZIP fills it)
- **Area:** 3 Jammed address split
- **Input:** no commas, with a ZIP: `85-10 Forest Pkwy Woodhaven NY 11421`; `123 Montague St Brooklyn Heights NY 11201`; `123 Main St Rockaway Park NY 11694`; `123 Main St Kew Gardens Hills NY 11367`; `123 Main St Apt 4B Bklyn NY 11201`.
- **Got:** CLEAN, with the place name inside Address_1, for example `A1='85-10 Forest Pkwy Woodhaven'`, `A1='123 Montague St Brooklyn Heights'`, `A1='123 Main St Apt 4B Bklyn'` (the unit also stays unsplit because the abbreviation is not recognized).
- **Expected:** `Address_1 = '85-10 Forest Pkwy'`, `Address_2` the unit, `City` from the text or the ZIP.
- **Where:** `app.py:567-581` (city is found only if the last 1 to 3 words are in `NEIGHBORHOOD_TO_BOROUGH`); table at `app.py:289-346`. Of 45 common NYC neighborhoods I tried, 6 are in the table (Ridgewood, Cypress Hills, Maspeth, Bensonhurst, Canarsie, Bushwick). Missing include Woodhaven, Brooklyn Heights, Kew Gardens Hills, Rockaway Park, Douglaston, Bellerose, Floral Park, Kensington, Gravesend, Cobble Hill, Kips Bay and Hamilton Heights.
- **Reach:** every no-comma jammed address with a neighborhood name or abbreviation.
- **Proof:** `python b33_table_coverage.py`, `python b07_address_pipeline.py`, `python b06_address_cities.py`
  ```
  neighborhood table size: 114 | city alias table size: 24
  6 of 45 common names are in the table
  Woodhaven (not in neighborhood table) -> CLEAN  A1='85-10 Forest Pkwy Woodhaven' City='Queens' Zip='11421'
  Brooklyn Heights jammed               -> CLEAN  A1='123 Montague St Brooklyn Heights' City='Brooklyn'
  Bklyn after unit                      -> CLEAN  A1='123 Main St Apt 4B Bklyn'
  '123 Main St Rockaway Park NY 11694'  -> street='123 Main St Rockaway Park'
  ```
- **Rewrite requirement:** locate the end of the street by its street-type word (or the house-number pattern) and treat what follows, after units, as city text, whatever it is. Test: each of the five inputs gives the street without the place name, the unit in Address_2 where present, and City from the ZIP.

### B-29. A unit swallows the city ("Apt 3 Brooklyn" lands in Address_2)

- **Severity:** Medium (right text, wrong field; City is filled from the ZIP)
- **Area:** 3 Jammed address split
- **Input:** `Address_1 = "123 Main St, Apt 3 Brooklyn NY 11201"`.
- **Got:** CLEAN, `Address_1='123 Main St'`, `Address_2='Apt 3 Brooklyn'`.
- **Expected:** `Address_2 = 'Apt 3'`, `City = Brooklyn`.
- **Where:** `app.py:538-565` (a comma segment that starts with a unit word is taken whole as the unit); `app.py:774` (`_looks_like_unit`).
- **Reach:** comma addresses where the unit and the city share a segment.
- **Proof:** `python b06_address_cities.py`, `python b07_address_pipeline.py`
  ```
  '123 Main St, Apt 3 Brooklyn NY 11201' -> street='123 Main St' unit='Apt 3 Brooklyn' city='' st='NY' zip='11201'
  unit then city, comma -> CLEAN  A1='123 Main St' A2='Apt 3 Brooklyn' City='Brooklyn' Zip='11201'
  ```
- **Rewrite requirement:** a unit is the designator token(s) only; the rest of the segment is re-parsed as city text. Test: the input above gives Address_2 `Apt 3`.

### B-30. Lone-letter units ("Apt B", "Unit B", ", B", "5C") stay in the street

- **Severity:** Medium (right text, wrong field; breaks geocode exact match, which needs the bare street)
- **Area:** 3 Jammed address split
- **Input:** `123 Main St Apt B`, `123 Main St Unit B`, `123 Main St, B, Brooklyn NY 11201`, `1010 Grand Concourse 5C`.
- **Got:** the unit stays in `Address_1`: `123 Main St Apt B`, `123 Main St Unit B`, `123 Main St, B` (with the comma), `1010 Grand Concourse 5C`. By contrast `Apt 4B`, `#B`, `3F` and `Apt B` after a comma are split. The geocoder cannot match `123 Fulton St Apt B` to `123 Fulton St` (no_match).
- **Expected:** an explicit unit word followed by a letter or letters is a unit.
- **Spec:** by design (`crosswalk-described-for-an-ai.md:116`: a designator needs a digit, except a lone letter after `#`), to protect `Avenue U`. An explicit word like Apt or Unit does not need that protection.
- **Where:** `app.py:416-433` (`_UNIT_DESIGNATOR`, `_UNIT_TAIL_RE`).
- **Reach:** common; letter units are frequent in the Bronx and Brooklyn.
- **Proof:** `python b05_address_split.py`, `python b07_address_pipeline.py`, `python b15_geocode_fuzzy.py`
  ```
  '123 Main St Unit B'  -> street='123 Main St Unit B' unit=''
  '123 Main St Apt B'   -> street='123 Main St Apt B' unit=''
  '1010 Grand Concourse 5C' -> street='1010 Grand Concourse 5C' unit=''
  '123 Main St, B, Brooklyn NY 11201' -> street='123 Main St, B' unit='' city='Brooklyn'
  unit left in street: 123 Fulton St Apt B (should match) -> CLEAN | status='Unverified' geo=no_match
  ```
- **Rewrite requirement:** unit word plus any designator (digit or 1 to 2 letters) is a unit; a bare designator without a unit word needs a digit. Test: `123 Main St Apt B` gives street `123 Main St`, unit `Apt B`; `100 Avenue U` stays whole.

### B-31. A typed city that is not recognized is overwritten by the ZIP's borough

- **Severity:** Medium (specified behavior, and the original is recorded in the audit, but a typed value is erased)
- **Area:** 4 City and borough
- **Input:** `City = "Yonkers"`, `ZIP = 10001`; `City = "Hoboken"`, `ZIP = 10001`, `State` blank.
- **Got:** CLEAN, `City='New York'`. (`Hoboken` with `State = NJ` goes to review: "State is not NY".)
- **Expected:** a real place outside NYC typed next to a NYC ZIP is a conflict. Review, with both values shown.
- **Spec:** by design, `crosswalk-described-for-an-ai.md` item 7 ("An unrecognized city with a valid ZIP is replaced by the ZIP's borough and recorded").
- **Where:** `app.py:1637-1655`.
- **Reach:** every path.
- **Proof:** `python b04_city_zip.py`
  ```
  Yonkers + 10001                   -> CLEAN  City='New York' St='NY' Zip='10001'
  Hoboken + 10001, state blank      -> CLEAN  City='New York' St='NY'
  Hoboken + 10001 (NYC ZIP)         -> REVIEW: State is not NY: 'NJ'
  Yonkers + ZIP 10701               -> REVIEW: Unrecognized City: 'Yonkers'
  ```
- **Rewrite requirement:** replace an unrecognized city only when it is a misspelling of a borough or neighborhood; otherwise REVIEW. Test: `Yonkers / 10001` is REVIEW; `Brooklin / 11201` is a proposal to `Brooklyn`.

### B-32. Extra name tokens are dropped, and the row is clean

- **Severity:** Medium (data lost, but only on unusual shapes)
- **Area:** 5 Name split
- **Input:** `Smith, John Q Public`; `Smith, John, Mary`; `John (Jack) Smith`; `John 'Johnny' Smith`.
- **Got:** `Smith, John Q Public` gives `John / Q / Smith` ("Public" dropped), CLEAN through the fast path. `Smith, John, Mary` gives `John / M / Smith`. The nickname forms give `John / Smith`.
- **Expected:** anything that does not fit the shape is kept in a note or sends the row to review.
- **Where:** `app.py:597-654`.
- **Reach:** the fast path, on unusual names.
- **Proof:** `python b09_names.py`, `python b27_name_split_api.py`
  ```
  'Smith, John Q Public'   -> first='John' mid='Q' last='Smith'          (CLEAN in the fast path)
  'Smith, John, Mary'      -> first='John' mid='M' last='Smith'
  'John (Jack) Smith'      -> first='John' mid=''  last='Smith'
  ```
- **Rewrite requirement:** a split must account for every token or flag the leftovers. Test: `Smith, John Q Public` is REVIEW with the unused token named.

### B-33. Middle-initial placeholders become letters (NMI to N, Jr to J, Unknown to U)

- **Severity:** Medium (an invented value; flagged, not reviewed)
- **Area:** 5 Name split
- **Input:** `Middle_Initial` = `NMI`, `NMN`, `Jr`, `no`, `Unknown`.
- **Got:** `N`, `N`, `J`, `N`, `U`, with the note "reduced multi-character value to initial". `None`, `N/A`, `.` and `(none)` are dropped correctly.
- **Expected:** a multi-letter value that is not a name is blank. A real middle name is reduced to its first letter (the spec's rule).
- **Where:** `app.py:661-682`.
- **Reach:** files with a middle-name column; low harm, but the letters are false.
- **Proof:** `python b24_invisible.py`
  ```
  'NMI' -> 'N' Middle_Initial: reduced multi-character value to initial 'N'
  'NMN' -> 'N'     'Jr' -> 'J'     'no' -> 'N'     'Unknown' -> 'U'
  'None' -> ''     'N/A' -> ''     '.' -> ''       '(none)' -> ''
  ```
- **Rewrite requirement:** a stop list (NMI, NMN, NMI, no, none, unknown, n/a, Jr, Sr, II to V) maps to blank, with suffix values moved to the suffix. Test: `NMI` gives blank; `Marie` gives `M`.

### B-34. Fill proposals ignore house numbers and non-NYC ZIPs, and overstate their evidence

- **Severity:** Medium (these are proposals for a person, but their text claims more than the data supports)
- **Area:** 7 Calculated ZIP and fill_missing
- **Input:** (a) `85 Montague St` with `City = Hoboken`, `ZIP = 07030`; (b) `999 Montague St`, Brooklyn, and `1 Main St`, Brooklyn; (c) `1 Avenue U` with `City = Brookline`.
- **Got:** (a) proposes replacing `Hoboken` with `Brooklyn` ("montague street is only in Brooklyn") although the ZIP is New Jersey's. (b) proposes ZIP `11201` for any house number ("main street in Brooklyn is only in ZIP 11201", from a sample reference). (c) accepts the typed `Brookline` as Brooklyn and proposes `11223`.
- **Expected:** a proposal must respect house-number ranges, must not override a ZIP that is valid and outside NYC without saying so, and must say "in the reference I have" rather than "is only in".
- **Where:** `fill_missing.py:59-80` (street to ZIP set), `fill_missing.py:142-191` (`propose_city`, `propose_for_row`).
- **Reach:** the Fix problems screen; also depends on the quality of the reference file.
- **Proof:** `python b13_fill_missing.py`
  ```
  '999 Montague St'  'Brooklyn' -> ('11201', 'montague street in Brooklyn is only in ZIP 11201')
  '1 Main St'        'Brooklyn' -> ('11201', 'main street in Brooklyn is only in ZIP 11201')
  '85 Montague St' zip=07030 -> ('Brooklyn', 'montague street is only in Brooklyn')
  Hoboken 07030 85 Montague St -> [{'field': 'City', 'value': 'Brooklyn', 'why': "replace 'Hoboken' with Brooklyn: montague street is only in Brooklyn"}]
  '1 Avenue U'  'Brookline' -> ('11223', 'avenue u in Brooklyn is only in ZIP 11223')
  ```
- **Rewrite requirement:** a reference with house-number ranges per ZIP; evidence text that states the data source and its coverage; no city proposal when the ZIP is valid and outside NYC (send it to review instead). Test: `85 Montague St, Hoboken, 07030` produces no proposal and a REVIEW reason; `1 Main St, Brooklyn` produces "ZIP unknown" unless the reference has house-number ranges.

### B-35. Fuzzy matches are labeled "Verified" and pass `require_geocode`

- **Severity:** Medium (misleading label; the underlying wrong match is B-17)
- **Area:** 8 Geocoding fallback
- **Input:** the `111 Main St` vs `11 Main St` case from B-17, with `require_geocode = True`.
- **Got:** CLEAN with status `Verified (low confidence)`, coordinates and districts filled in. With `require_geocode` on, the row still passes. The match percent (97) appears only in the audit log line (`app.py:2512-2515`), not in the output row, where only `Low` is shown.
- **Expected:** a fuzzy match is "Needs check", not "Verified"; with `require_geocode` on, only exact matches pass.
- **Where:** `app.py:2579-2583` (status assignment); `app.py:2565-2572` (`require_geocode` sends a row to review only in the branch where no coordinates were found, so a fuzzy hit passes); default `require_geocode = False` at `crosswalk_server.py:106` means unmatched rows are also CLEAN ("Unverified").
- **Reach:** every run that uses the fallback geocoder.
- **Proof:** `python b15_geocode_fuzzy.py`
  ```
  exact w/ require_geocode, fuzzy wrong building
      CLEAN | status='Verified (low confidence)' conf='Low' geo=fuzzy latlon=('40.704000', '-73.980000')
  exact: 100 W 10 St -> CLEAN | status='Verified' conf='High' geo=exact
  ```
- **Rewrite requirement:** statuses are Exact, Proposed (fuzzy, needs a person), Unmatched; the match percent is a column in the output. Test: fuzzy match with `require_geocode = True` goes to REVIEW; exact match is the only one counted as verified.

### B-36. The same-ID check runs across files, so two systems that reuse IDs send every row to review

- **Severity:** Medium (no wrong value, but the tool's main job, merging lists from several systems, stalls)
- **Area:** 9 Duplicates and same-ID
- **Input:** two exports from two systems, each numbering its own clients 1001 to 1060, with different people.
- **Got:** 120 of 120 rows go to review: "Same Client ID '1001' used by records with different data; review required (not merged)". Zero clean rows.
- **Expected:** a Client ID is unique within one source system. Across files the same number means nothing by itself; matching across systems uses the person key.
- **Spec:** `crosswalk-described-for-an-ai.md:105` describes Tier 1 as "in one file". The code groups by ID over all files.
- **Where:** `app.py:2386-2417` (`id_groups` is built over `transformed`, all files together).
- **Reach:** every multi-file run where two systems number from 1.
- **Proof:** `python b23_sameid_crossfile_api.py`, `python b18_dedupe.py`
  ```
  rows: 120 clean: 0 sent to review as 'Same Client ID used by records with different data': 120
  example: pantry_system.csv 1001 ["Same Client ID '1001' used by records with different data; review required (not merged)"]
  A.csv 1001 Maria Lopez -> REVIEW: Same Client ID '1001' used by records with different data; review required (not merged)
  B.csv 1001 John Chen  -> REVIEW: Same Client ID '1001' used by records with different data; review required (not merged)
  ```
- **Rewrite requirement:** key the ID check by (source system, ID); across systems only the person key can pair rows. Test: A.csv `1001 Maria Lopez` and B.csv `1001 John Chen` are both clean; two rows in A.csv with `1001` and different people are both REVIEW.

### B-37. "Identical record" ignores date of birth, middle initial and every custom field

- **Severity:** Medium (the second row goes to review, but it is labeled a "confirmed duplicate" and can be dropped on that word)
- **Area:** 9 Duplicates and same-ID
- **Input:** same Client ID, name, address, ZIP and program, but `DOB` `03/04/1990` vs `09/09/1955`; or middle initial `A` vs `B`.
- **Got:** the second row is REVIEW "Confirmed duplicate: identical record with the same Client ID". With `Address_2` different the message is the "different data" one (Address_2 is in the key).
- **Expected:** a different DOB or middle initial under one ID is "different data", never "identical".
- **Where:** `app.py:1759-1762` (`dup_key` = last, first, address 1, address 2, ZIP, program); `app.py:2394-2407`.
- **Reach:** same system, one ID, two people.
- **Proof:** `python b18_dedupe.py`, `python b39_tier1_other_fields.py`
  ```
  1001 1990-03-04 -> CLEAN
  1001 1955-09-09 -> REVIEW: Confirmed duplicate: identical record with the same Client ID
  same ID, middle initial A vs B: MI='A' -> CLEAN ; MI='B' -> REVIEW: Confirmed duplicate: identical record with the same Client ID
  same ID, Address_2 'Apt 1' vs 'Apt 2' -> both REVIEW: Same Client ID '77' used by records with different data
  ```
- **Rewrite requirement:** "identical" means every mapped field is equal after cleaning. Test: same ID with a different DOB or middle initial gives the "different data" reason, never "identical".

### B-38. A saved "copies" decision silently covers a person added later

- **Severity:** Medium
- **Area:** 9 Duplicates and same-ID
- **Input:** two rows grouped by the rule (First + Last + Zip); the reviewer decides "copies"; later a third, different Maria Garcia in the same ZIP is added.
- **Got:** the group id stays the same (it hashes only the key), the old decision applies to the new row, and `__dup_drop__` reads `['', 'copy of row 1', 'copy of row 1']`, so the third person is marked a copy.
- **Expected:** a decision applies to the exact rows that were shown; a new row in the group makes the group undecided again.
- **Where:** `dedupe_rules.py:104-109` (`group_id` is the SHA-1 of the key only); `dedupe_rules.py:143` (`apply_decisions`).
- **Reach:** reruns after a file is replaced or extended.
- **Proof:** `python b18_dedupe.py`
  ```
  group shown to the reviewer: [1, 2] gid bc6648ad10
  same gid after a third, different person is added: True
  __dup_drop__ column: ['', 'copy of row 1', 'copy of row 1']
  ```
- **Rewrite requirement:** the decision id includes the member row ids; a changed membership invalidates it. Test: decide "copies" for rows 1 and 2, add row 3 with the same key: row 3 is undecided and shown again.

### B-39. The person key does not fold accents or punctuation, so true duplicates are missed

- **Severity:** Medium (missed match only; the tool never merges, so the cost is duplicate people in the master list)
- **Area:** 9 Duplicates and same-ID
- **Input:** the same person in two files with different IDs and the same address and ZIP: `Maria Garcia` vs `María García`; `Pat OBrien` vs `Pat O'Brien`; `Ana Maria Lopez` vs `Ana-Maria Lopez`; `Jose Nunez` vs `José Núñez`. Within one file: `Maria Garcia` vs `María García`, `O'Brien` vs `OBrien`.
- **Got:** the control (`Maria Garcia` vs `Maria Garcia`, and `MARIA GARCIA`) is paired as a possible duplicate; none of the four variants is. In the within-file rule the groups found are `[[0, 1], [3, 4]]` and rows 2 (accents) and 5 to 6 (apostrophe) are left out. (Hyphen versus space does fold in the within-file rule only.)
- **Expected:** accents, apostrophes, hyphens and spacing are ignored when comparing names.
- **Where:** `app.py:1759-1762` (`last.lower()`, `first.lower()` only); `dedupe_rules.py:23-35` (`_norm` replaces punctuation with a space, so `O'Brien` becomes `o brien`, not `obrien`, and `\w` keeps accented letters as they are).
- **Reach:** Hispanic and French names; any system that drops accents.
- **Proof:** `python b34_accents_corr_encoding.py`, `python b18_dedupe.py`
  ```
  Maria 'Garcia'   vs Maria 'Garcia'   -> paired as possible duplicate: True
  Maria 'Garcia'   vs MARIA 'GARCIA'   -> paired as possible duplicate: True
  Maria 'Garcia'   vs María 'García'   -> paired as possible duplicate: False
  Pat 'OBrien'     vs Pat "O'Brien"    -> paired as possible duplicate: False
  Ana Maria 'Lopez' vs Ana-Maria 'Lopez' -> paired as possible duplicate: False
  Jose 'Nunez'     vs José 'Núñez'     -> paired as possible duplicate: False
  groups (row positions): [[0, 1], [3, 4]]
  ```
- **Rewrite requirement:** one comparison function for names, used by every duplicate check: NFKD without combining marks, lower case, strip apostrophes, treat hyphens as spaces. Test: all four pairs above are paired; `Wei Li` and `Li Wei` are still not paired.

### B-40. Proposals join different programs, and the screen shows only "worth a glance"

- **Severity:** Medium (a proposal; B-20 is what makes it take effect)
- **Area:** 10 Program names
- **Input:** pairs of program names.
- **Got:** proposed for joining: `Youth Services` + `Youth Employment` and `Youth Housing`; `Senior Services` + `Senior Housing` and `Senior Employment`; `Level 1` + `Level 2`; `Cohort 2023` + `Cohort 2024`; `Section B` + `Section C`; `ESL Level 1` + `ESL Level 2`; `Group A` + `Group B`; `Class A` + `Class B`; `Adult` + `Adult Day Care` ("initials of the other"); `GED` + `GED Prep`; `Health` + `Hospital Employment Assistance Linkage Training Hub` ("initials"); `Pre-K` + `Pre-K Extended Day`; `Tenant Services` + `Tenant Organizing`. Joins chain: given `Youth Services`, `Youth Employment` and `Youth Housing` together, all three land in one group even though `Youth Employment` and `Youth Housing` are not proposed as a pair; the same happens for `Senior Services` / `Senior Housing` / `Senior Employment`, and for `Adult` / `Adult Education` / `Adult Literacy`.
- **Expected:** the same first word or a one-character difference does not make a match. Numbers, letters and years that differ mean different programs.
- **Where:** `program_names.py:150-222` (`suggest_groups`): similar-enough ratio 86 (`program_names.py:47`), initials rule (`program_names.py:108`), starts-the-same rule (`program_names.py:134`, used at line 191); the screen text is in `ui/app.js` (about lines 1134-1170).
- **Reach:** every run with more than one program.
- **Proof:** `python b19_programs.py`
  ```
  ['Youth Services', 'Youth Employment'] -> JOINED ... 'one name is the other with more words on the end', needs_confirming=True
  ['Senior Services', 'Senior Employment'] -> JOINED ...
  ['Level 1', 'Level 2'] -> JOINED ['Level 2', 'Level 1'] as 'Level 2' because 'the names are nearly the same'
  ['Cohort 2023', 'Cohort 2024'] -> JOINED ... 'the names are nearly the same'
  ['Adult', 'Adult Day Care'] -> JOINED ... 'one is the initials of the other'
  ['Health', 'Hospital Employment Assistance Linkage Training Hub'] -> JOINED ... 'one is the initials of the other'
  ['Food Pantry', 'Food Stamps'] -> no proposed join       ['Youth Employment', 'Youth Empowerment'] -> no proposed join
  chains (three names together):
     ['Youth Services', 'Youth Employment', 'Youth Housing']  -> [['Youth Employment', 'Youth Housing', 'Youth Services']] needs_confirming: [True]
     ['Senior Services', 'Senior Housing', 'Senior Employment'] -> [['Senior Employment', 'Senior Housing', 'Senior Services']]
     ['Adult Education', 'Adult', 'Adult Literacy']            -> [['Adult', 'Adult Education', 'Adult Literacy']]
  ```
- **Rewrite requirement:** propose only spelling, case, abbreviation and punctuation variants of the same name; never when a digit, a single letter or a year differs; initials only when every letter lines up with a word in order. Test: `Level 1`/`Level 2`, `Cohort 2023`/`Cohort 2024`, `Youth Services`/`Youth Employment`, `Health`/`Hospital ...` are not proposed; `Workforce Dev.`/`Workforce Development` and `SYEP`/`Summer Youth Employment Program` are.

---

# Low

### B-41. Marble Hill gives a false City/ZIP conflict

- **Severity:** Low
- **Area:** 4 City and borough
- **Input:** `City = Manhattan`, `ZIP = 10463`, `Address_1 = 5 Marble Hill Ave`.
- **Got:** REVIEW "City/ZIP conflict: City says 'New York' (entered as 'Manhattan') but ZIP 10463 is in Bronx". Marble Hill is in Manhattan by law and has a Bronx ZIP, so the pair is legitimate.
- **Expected:** accept Manhattan for 10463 when the street is in Marble Hill; or review with a note that names Marble Hill.
- **Where:** `app.py:1637-1655`; `app.py:730-750`.
- **Reach:** tiny.
- **Proof:** `python b04_city_zip.py`
  ```
  Brooklyn + 10463 Marble Hill -> REVIEW: City/ZIP conflict: City says 'New York' (entered as 'Manhattan') but ZIP 10463 is in Bronx; confirm which is correct
  ```
- **Rewrite requirement:** a small exception table (ZIP and borough pairs that are legitimate). Test: `Manhattan / 10463` is clean.

### B-42. "Rear" and "Front" split with a comma but not without

- **Severity:** Low
- **Area:** 3 Jammed address split
- **Input:** `123 Main St Rear`, `123 Main St Front`, `123 Main St, Front`.
- **Got:** the first two stay in the street; the third gives unit `Front`.
- **Expected:** one rule. The spec says the words are kept in the stored value but ignored for geocoding (`crosswalk-described-for-an-ai.md:97`), and also lists rear and front as unit words (line 116).
- **Where:** `app.py:416-433`.
- **Reach:** low.
- **Proof:** `python b05_address_split.py`, `python b30_checked_correct.py`
  ```
  '123 Main St Rear'   -> street='123 Main St Rear' unit=''
  '123 Main St Front'  -> street='123 Main St Front' unit=''
  '123 Main St, Front' -> street='123 Main St' unit='Front'
  ```
- **Rewrite requirement:** decide once; recommended: both go to Address_2 and geocoding uses the bare street. Test: all three forms give the same Address_1.

### B-43. Name-aware title case gets a few names wrong

- **Severity:** Low (only when the title-case clean step is turned on; casing is otherwise preserved)
- **Area:** 5 Name split
- **Input:** `MCE`, `MACKENZIE`, `DEJESUS`, `LEBRON`, `DINAPOLI`, `O’BRIEN` (curly apostrophe).
- **Got:** `McE`, `MacKenzie`, `Dejesus`, `Lebron`, `Dinapoli`, `O’brien`. (`MACHADO` to `Machado` and `MACKEY` to `Mackey` are right; `MACKENZIE` to `MacKenzie` is a defensible choice.)
- **Expected:** at minimum the curly apostrophe behaves like the straight one.
- **Where:** `app.py:927-929` and its helpers.
- **Reach:** only when the step is chosen; all-caps source files.
- **Proof:** `python b10_name_case.py`
  ```
  'MCE' -> 'McE'    'DEJESUS' -> 'Dejesus'    'DINAPOLI' -> 'Dinapoli'    'O’BRIEN' -> 'O’brien'    "O'BRIEN" -> "O'Brien"
  ```
- **Rewrite requirement:** normalize curly apostrophes before casing; an exceptions table that a person can extend. Test: `O’BRIEN` gives `O’Brien`; `MCE` stays `Mce`.

### B-44. Surnames Sum, Mean and Count with no street are set aside as summary rows

- **Severity:** Low (shows in review; the person's name is blanked on the review row)
- **Area:** 1 Cell cleaning (summary-row test)
- **Input:** `First = Sokha`, `Last = Sum`, no address; `Last = Mean`; `First = Count`, `Last = Basie`.
- **Got:** REVIEW "Summary row, not a client record (a total, count or heading); set aside", and the shown name is blank. With a street the row is CLEAN. A summary row is also "never counted as a person".
- **Expected:** a row with a first name, a last name and an ID is a person, whatever the words.
- **Where:** `app.py:1393-1426` (`SUMMARY_WORDS`, `is_summary_row`).
- **Reach:** rare.
- **Proof:** `python b32_summary_row.py`
  ```
  Last name 'Sum', no street     -> REVIEW: Summary row, not a client record (a total, count or heading); set aside   First='' Last=''
  Last name 'Sum', street present -> CLEAN  First='Sokha' Last='Sum'
  First name 'Count' no street   -> REVIEW: Summary row ...
  ```
- **Rewrite requirement:** a summary row is one with no first name or no last name that also matches a summary word; keep the original values on the review row. Test: `Sokha Sum` with an ID and no address is a person with a missing address.

### B-45. One early failed row changes every later row's jittered coordinates

- **Severity:** Low (breaks the claim that a rerun gives the same points)
- **Area:** 8 Geocoding fallback
- **Input:** 400 rows geocoded with seed 1337; then row 0 is made to fail validation and the file is run again.
- **Got:** 399 of 399 later rows have different stored coordinates.
- **Expected:** a row's stored point depends only on its own address and the secret (see B-18).
- **Where:** `app.py:2326` (one shared `random.Random` consumed per geocoded row, in row order).
- **Reach:** every rerun after a review decision.
- **Proof:** `python b16_jitter_districts.py`
  ```
  rows 1..399 whose stored coordinate changed because row 0 failed: 399 of 399
  same seed, same input -> identical coordinates: True
  ```
- **Rewrite requirement:** per-address offset (B-18). Test: failing one row leaves every other row's coordinates unchanged.

### B-46. The stored (jittered) point can sit in a different district than the stored district

- **Severity:** Low (documented behavior, but surprising to a consumer)
- **Area:** 8 Geocoding fallback
- **Input:** an address 5 ft inside district A, jitter 150 to 250 ft, 40 seeds.
- **Got:** the district columns say A every time; the stored point lands in district B on 16 of the 40 seeds.
- **Expected:** the output states plainly that districts come from the true point, in the column header or a note on the results; or districts are taken from the displaced point as well.
- **Where:** `app.py:2551-2554` (`assign_districts(tlat, tlon, ...)` uses the true point, while the stored point is the jittered one from `app.py:2503`); documented in `crosswalk-described-for-an-ai.md:132`.
- **Reach:** addresses within 250 ft of a boundary.
- **Proof:** `python b17_districts.py`
  ```
  40 seeds: district always A (10/20/30); stored point landed in B on 16 of 40 seeds, so the stored point and its district disagree on those rows
  ```
- **Rewrite requirement:** a visible note on the output; a consumer-facing field that says "district computed from the exact address". Test: the results sheet carries that note.

### B-47. The default within-file rule groups different people with common names

- **Severity:** Low (groups are shown to a person; nothing is merged)
- **Area:** 9 Duplicates and same-ID
- **Input:** default fields First_Name + Last_Name + Zip; two `Maria Garcia` rows with different IDs and addresses in one ZIP.
- **Got:** grouped as a possible duplicate (`[[0, 1], [3, 4]]` in the test).
- **Expected:** the default rule includes the address (or ID) so that the common-name groups are small.
- **Where:** `crosswalk_server.py:124` (`"dup_fields": ["First_Name", "Last_Name", "Zip"]`).
- **Reach:** large lists with common names.
- **Proof:** `python b18_dedupe.py`
  ```
  groups (row positions): [[0, 1], [3, 4]]      (rows 0 and 1: Maria Garcia, 10 Main St vs 99 Other Ave, same ZIP)
  ```
- **Rewrite requirement:** default key = name + address (or name + DOB when present); ZIP-only matches are shown as weak. Test: two `Maria Garcia` at different addresses are not grouped by default.

### B-48. "Last Visit" is mapped as Last_Name when it comes before "Surname"

- **Severity:** Low (the check catches it when the values contain digits)
- **Area:** 11 Column check and auto-mapping
- **Input:** headers `First Name, Last Visit, Surname, Client ID, ...` with values like `March 2024`.
- **Got:** `Last_Name = 'Last Visit'`; the express check returns the warning "Last_Name: Names should not contain numbers" and the fast path produces no results. `Surname` and `Forename` are not recognized as name columns at all (b21), so a file with only those headers maps no names.
- **Expected:** `Surname` is a Last_Name synonym; `Last Visit` is not a name column.
- **Where:** `app.py:2839-2840` (`Last_Name` candidates are `last_name ... last ...`; the bare candidate `last` matches any header containing the word, and `surname` is not a candidate).
- **Reach:** low.
- **Proof:** `python b36_mapping_end_to_end.py`, `python b21_mapping.py`
  ```
  'Last Visit' comes before 'Surname'
     mapped: {'First_Name': 'First Name', 'Last_Name': 'Last Visit', ...}
     express check ok = True | warnings = [{... 'field': 'Last_Name', 'text': 'case.csv, Last_Name: Names should not contain numbers.'}]
     (express run did not produce results)
  (b21) ['Forename', 'Surname', 'ID', ...] -> no First_Name or Last_Name mapped
  ```
- **Rewrite requirement:** add surname, forename, given and family synonyms; do not accept a column whose header carries a time or date word. Test: `[First Name, Last Visit, Surname]` maps `Surname`.

### B-49. "Address Line 2" before "Address Line 1" is mapped to Address_1 (the check catches it)

- **Severity:** Low (`column_check` reports a "problem" and the fast path stops)
- **Area:** 11 Column check and auto-mapping
- **Input:** headers `Address Line 2, Address Line 1` (or `Street Address 2, Street Address`).
- **Got:** `Address_1 = 'Address Line 2'`; for `Street Address 2` the same column is mapped to both `Address_1` and `Address_2`. `column_check` reports "These look like apartment or floor numbers rather than street addresses" (or "Only about 35% of rows have a value").
- **Expected:** Line 2 is Address_2; one column fills one role.
- **Where:** `app.py:2845-2847` (`address_line` is a whole-token candidate that `Address Line 2` satisfies); the check that catches it is `column_check.py:62` (`check_field`).
- **Reach:** low, because it is caught.
- **Proof:** `python b22_mapping_check.py`
  ```
  4. 'Address Line 2' listed before 'Address Line 1' (Line 2 mostly filled): verdict: problem (1 problems)
     Address_1: problem - These look like apartment or floor numbers rather than street addresses.
  5. 'Street Address' and 'Street Address 2': mapping Address_1 -> 'Street Address 2', Address_2 -> 'Street Address 2'
  ```
- **Rewrite requirement:** a trailing "2" or "line 2" means Address_2. Test: `[Address Line 2, Address Line 1]` maps Address_1 to `Address Line 1`.

---

# Checked and correct

Each line below was confirmed by running it (scripts in brackets).

- NBSP, tabs, CR/LF and runs of spaces collapse to one space; a cell of only NBSP becomes blank [b01, b30].
- `NULL`, `N/A`, `none`, `NA`, `NaN`, `#N/A`, `nil`, `(null)` and empty cells become blank, in any capitals [b01, b30].
- A UTF-8 BOM at the start of a CSV is removed from the first header [b24].
- A CSV is read as text: `07030`, `00501`, `0012345`, a 20-digit ID and `1E5` all survive unchanged through the server [b38].
- An `.xlsx` with date-typed cells, numeric ZIP cells and a numeric Excel serial in the DOB column uploads through the server with `1990-03-04` and `11201` intact, and the serial `32874` gives `1990-01-01` [b37].
- `07030` and `00501` keep their leading zero; ZIP+4 (`11201-1234`) and a 9-digit ZIP in the ZIP column reduce to five digits [b03, b30].
- 4-digit ZIPs, `7030.0`, `11201.0`, `112O1`, `11201-123`, `11,201` and `NY 11201` in a ZIP column go to review and are never repaired [b03].
- `Apt 4B`, `#4B`, `4th Floor`, `Basement`, `Fl 2`, `Ste 200`, `Rm 5` split to the unit [b05].
- `117-19 45th Ave` stays whole; `14A` and `Apt 14A` after it split off [b05].
- `Avenue U`, `Avenue of the Americas`, `Floor St`, `Suite Rd`, `Unit Ave`, `Route 9`, `Pier 40` (on its own) stay whole [b05].
- `123 1/2 Main St` keeps the `1/2` [b05].
- `Brooklyn Ave`, `Queens Blvd`, `Jamaica Ave`, `Bronx River Ave`, `Staten Island Expy` and `Flushing Ave` are not read as the city [b06].
- `100 New York Ave` keeps `New York` in the street [b06].
- Extra commas, `New York State`, a country at the end (`USA`, `US`, `United States`), ZIP+4 and a trailing period all parse [b06].
- The same unit in the street and Address_2 collapses; differing units (`Apt 4B` vs `Apt 5C`) go to review [b07].
- A blank City is filled from the ZIP; a recognized borough that contradicts a NYC ZIP goes to review; a typed recognized city is never overwritten [b04, b30].
- `Flushing`, `Elmhurst`, `Ozone Park`, `Queens Village`, `Harlem` and similar names fold to their borough, with a note [b08].
- State `NJ` or blank-State-with-NJ-city goes to review; `New York` and `N.Y.` in State become `NY` [b04, b07, b30].
- Names: `Last, First M`, `First M Last`, `Last, First`, `Jr` and `III` stay with the last name, hyphenated surnames, `O'Brien`, `D'Angelo`, casing preserved, a single name gives the first name only and then "Missing Last_Name" [b09].
- `de la Cruz, Maria`, `Van Buren, Martin` and `Juan C. De La Rosa` split correctly; the comma form is reliable [b09].
- `smart_title_name` keeps DiNapoli, McDonald, O'Brien, MacArthur and St. Claire [b10].
- Dates: ISO, US `M/D/YYYY`, dotted and `3-4-90` forms parse; `2/30/1990`, `4/31/1990`, `2/29/1900`, `2/29/2001`, `00/00/0000` are rejected; `2/29/2000` is accepted; 8-digit dates (`19900304`) and month names go to review [b11].
- Exact geocode match gives `High` and "Verified"; no match leaves blank coordinates and "Unverified" (it does not guess) [b15].
- A flipped direction (`100 E 10 St` vs `100 W 10 St`), `Fulton St` vs `Fulton Ave`, `Beach 19` vs `Beach 9` and `Avenue W` vs `Avenue V` are not fuzzy-matched [b15, b31]. (`Avenue U` vs `Avenue V` is, see B-17.)
- Jitter distance is always 150 to 250 ft, the same seed and input give the same points, and a different seed gives different points [b16].
- Districts are computed from the true point, not the jittered one [b17].
- Same Client ID with an identical record in a second file: the first row is clean, the second goes to review as a duplicate [b18].
- Same Client ID with a different Address_2 goes to review as "different data" [b39].
- Tier 2 cross-file same-person pairs (different IDs) are annotated "Possible duplicate", never merged; the within-file rule never merges or drops a row on its own [b34, b18].
- A row blank in any rule field is never grouped [b18].
- Reasonable program joins are proposed: `Workforce Dev.` / `Workforce Development` / `WFD`, `SYEP` / `Summer Youth Employment Program`, `Summer Youth Employment` / `Summer Youth Employment Program` [b19].
- Different programs that are left alone: `Food Pantry` / `Food Stamps`, `Youth Employment` / `Youth Empowerment`, `Mental Health` / `Mental Hygiene`, `Housing Counseling` / `Housing Court`, `Tier 1` / `Tier 2`, `ESL 1` / `ESL 2`, `3K` / `4K` [b19].
- `column_check` flags `Address Line 2` mapped as Address_1, 4-digit ZIPs, ISO dates mapped to Program, a repeated identifier mapped to Client_ID, and a name column with digits [b22, b36].

---

# Script index

All in `/tmp/claude-0/-home-claude/ec68250d-d5ac-549e-8d94-20759c381437/scratchpad/audit/B-scripts/`; saved output in `out/<script>.txt`.

| Script | What it probes | Findings |
|---|---|---|
| `_common.py`, `_api.py`, `_refdata.py` | helpers: single-row and pipeline runner; in-process FastAPI client; tiny reference CSV rows | all |
| `b01_cleaning.py` | `clean_cell` on placeholders and invisible characters | B-01, B-24 |
| `b02_placeholders_rows.py` | placeholders, sentinels and apostrophes through the full pipeline | B-01, B-24, B-25 |
| `b03_zip.py` | `normalize_zip` and `borough_from_zip` | B-03, B-04 |
| `b04_city_zip.py` | city and ZIP matrix | B-03, B-04, B-05, B-31, B-41 |
| `b05_address_split.py` | unit and street-name splitting | B-30, B-42 |
| `b06_address_cities.py` | commas, cities, state, country | B-07, B-10, B-29 |
| `b07_address_pipeline.py` | risky addresses through the pipeline | B-07 to B-10, B-27 to B-30 |
| `b08_city_fuzzy.py` | `normalize_city` fuzzy and table | B-05 |
| `b09_names.py` | `split_jammed_name` | B-11, B-12, B-32 |
| `b10_name_case.py` | `smart_title_name` | B-43 |
| `b11_dates.py` | `parse_date_value` | B-13 to B-16 |
| `b12_dob_pipeline.py` | DOB through the pipeline | B-13 to B-16 |
| `b13_fill_missing.py` | ZIP and city proposals | B-34 |
| `b14_shipped_reference.py` | the shipped reference CSV | method caveat |
| `b15_geocode_fuzzy.py` | fuzzy geocode cases | B-17, B-35 |
| `b16_jitter_districts.py` | jitter distance, determinism, reversal, averaging | B-18, B-45 |
| `b17_districts.py` | true versus jittered district, wrong-building district | B-17, B-46 |
| `b18_dedupe.py` | same-ID, DOB, stale decision, default rule | B-36 to B-39, B-47 |
| `b19_programs.py` | program-name proposals | B-40 |
| `b20_programs_api.py` | proposals applied unconfirmed | B-20 |
| `b21_mapping.py`, `b22_mapping_check.py` | `guess_mapping` and `column_check` | B-21, B-22, B-48, B-49 |
| `b23_sameid_crossfile_api.py` | same-ID across two files | B-36 |
| `b24_invisible.py` | BOM, encodings, Unicode digits, middle initials | B-02, B-24, B-26, B-33 |
| `b25_district_holes.py` | polygon hole | B-19 |
| `b26_calc_zip.py` | calculated ZIP | B-06 |
| `b27_name_split_api.py` | name split via the fast path | B-11, B-12, B-32 |
| `b28_split_hijack_api.py`, `b29_addr_hijack_api.py` | split columns replacing real columns | B-23 |
| `b30_checked_correct.py` | pass assertions | Checked list |
| `b31_ratio_table.py` | fuzzy ratio table | B-17 |
| `b32_summary_row.py` | summary-row false positives | B-44 |
| `b33_table_coverage.py` | neighborhood table coverage | B-28 |
| `b34_accents_corr_encoding.py` | accents in the person key, `_corr_value` | B-25, B-39 |
| `b35_encoding_api.py` | Windows-1252 CSV through the fast path | B-02 |
| `b36_mapping_end_to_end.py` | mapping mistakes through the fast path | B-21, B-22, B-48 |
| `b37_xlsx_dates_server.py` | xlsx date and numeric cells through the server | Checked list |
| `b38_csv_leading_zeros_server.py` | CSV numeric-looking values through the server | Checked list |
| `b39_tier1_other_fields.py` | Tier 1 comparison fields | B-37 |
