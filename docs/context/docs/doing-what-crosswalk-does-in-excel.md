# Manually converting data

&#32;This tutorial simplifies several rules, so its results will not match the app. For work done by hand when the app is unavailable, use Crosswalker by hand: the Excel runbook instead.

Every function the application performs can be reproduced in Excel with formulas, lookups and a few built-in tools, on a small fake dataset shown in pictures at each step. Some limitations exist and are documented at the bottom of the document.&#32;

Excel formulas will need to be modified if someone needs to reproduce results using these steps. The formulas are set to the fake data tables and data set in this document.&#32;

## Before you start

Every step below works on the same two fake files, so you can follow the numbers from one section to the next. The people, addresses and identifiers are invented. Nothing here is a real client.

**File A, an ETO-style export.** One name column, one jammed address column, a program, a birth date. Row E103 is the same person as E102 typed twice. Row E105 has a Brooklyn city with a Manhattan ZIP. Row E106 has NULL for an address. The last row is a total, not a person.

| PID | Name | Address | DOB | Program |
| --- | --- | --- | --- | --- |
| E100 | Smith, Joseph A | 209 Joralemon St, Apt 4B, Brooklyn, NY 11201 | 1984-03-15 | Workforce Development |
| E101 | Adeyemi, Kira | 65 Central Ave, Brooklyn, NY 11221 | 1990-07-02 | Workforce Development |
| E102 | Sample, Ada | 60 Centre St, New York, NY 10007 | 1978-11-30 | Resident Services |
| E103 | SAMPLE, ADA | 60 Centre St., New York, NY 10007 | 1978-11-30 | Resident Svcs |
| E104 | Fixture, Ben | 87 Bay Terrace, Woodside, NY 11377 | 2001-01-09 | Youth |
| E105 | Mock, Devi | 2300 Avenue U, Brooklyn, NY 10007 | 1966-05-21 | Youth |
| E106 | Draft, Fay | NULL | 1995-09-12 | Youth |
| Total |  |  |  | 7 |

**File B, a partner list.** Already split into columns, with its own habits: a ZIP+4, the state spelled out, a blank city, a unit jammed onto the street, a missing ZIP, a street that does not exist, a neighborhood instead of a borough, and a double surname. P-9 is the same person as E100 (Joe for Joseph). P-10 is the same as E102, and she is in a second program, Housing. P-14 is probably the same as E101, and that word probably is the point of section 11.

| Client ID | First | Last | Street | Apt | City | State | Zip | Service area | Birth date |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| P-9 | Joe | Smith | 209 Joralemon St | 4B | Brooklyn | New York | 11201-1234 | WFD | 3/15/1984 |
| P-10 | Ada | Sample | 60 Centre St |  |  | NY | 10007 | Housing | 11/30/1978 |
| P-11 | Evan | Stub | 117-19 45TH AVE 14A |  | Queens | NY | 11355 | Youth | 6/6/2003 |
| P-12 | Hana | Proxy | 88 Meserole St |  | Brooklyn | NY |  | Housing | 2/2/1959 |
| P-13 | Gus | Trial | 1 Nowhere Rd |  | Brooklyn | NY | 11206 | Housing | 8/8/1970 |
| P-14 | Kira | Adeyemi-Cole | 65 Central Ave |  | Bushwick | NY | 11221 | Workforce | 7/2/1990 |

**Which Excel.** Every formula pictured uses functions that exist in every Excel since 2007 (TRIM, CLEAN, LEFT, MID, FIND, SEARCH, INDEX, MATCH, COUNTIF, COUNTIFS, SUMPRODUCT, IFERROR) plus TEXTJOIN, which needs Excel 2019 or Microsoft 365. Where Microsoft 365 has a shorter way (XLOOKUP, TEXTSPLIT, UNIQUE, FILTER) it is named in one line, but the pictured formula is the one that works everywhere.

**The one rule.** Never overwrite a source cell. Every step adds a new column beside the original, exactly as the application does, so a mistake can be undone by deleting the column and nothing is lost. Keep each source file on its own sheet, untouched, and do all the work on copies.

Every picture is taken from one workbook, Crosswalk\_in\_Excel.xlsx, with a sheet per section and every formula live. It travels as a separate file; attach it when you share this document. Open it beside the text and click any green cell to see its formula. Green columns are the ones each step adds; blue headers are the source.

## 1. Bring every file into one shape

The application maps every file onto the same columns in the same order, so the files can be stacked and compared. In Excel you build one sheet with the standard columns, and each cell points back at the source cell it came from.

1. Add a sheet named One shape. Type these headers across row 1. Client\_ID, First\_Name, Last\_Name, Address\_1, Address\_2, City, State, Zip, Program, DOB, Source and anything else that is needed for the main shape of the data.&#32;
2. Click A2, type =, click the Client ID cell on the File B sheet, and press Enter. The cell now reads `='File B'!A2`. Do the same for each column in row 2.
3. Select row 2 across all the columns and drag the fill handle down to the last row of File B.
4. Best to type the file name in Source on every row. The duplicates check, the audit and the quality report all need it.
5. File A still has its name and address jammed into one column each. Leave those columns until sections 3 and 4 have split them, then point at the split columns the same way.

&#91;image: The One shape sheet with A2 pointing at File B's Client ID\]

The name box shows the selected cell, A2, and the formula bar shows where it points. Rows 2 to 7 come from File B. Rows 8 to 14 are File A, waiting on the splits.

Before going on, look at the first three values in every column. A street column full of apartment numbers means the wrong source column was picked, and that mistake runs through everything after it. The application checks this on its own and names the column that would fit; Excel will not.

In Microsoft 365 there is a faster way for files you receive every quarter. Data, Get Data, From File loads each file as a query. Rename each query's columns to the standard names, then Append Queries stacks them. Next quarter, Refresh All pulls in the new files.

## 2. Clean every cell

One formula removes what makes two equal values look different to a computer. Placeholders such as NULL, N/A, None and a lone dash become blank. Tabs and non-breaking spaces become ordinary spaces. Hidden characters are dropped. Repeated spaces collapse to one.

1. Insert a new column to the right of the column you are cleaning. Never type over the original.
2. In the first row of the new column, paste the formula below, changing A2 to the cell you are cleaning.
3. Double-click the fill handle to copy it down.
4. Point the One shape sheet at the cleaned column, not the original.

```
=IF(OR(TRIM(CLEAN(A2))="",UPPER(TRIM(A2))="NULL",UPPER(TRIM(A2))="N/A",UPPER(TRIM(A2))="NONE",TRIM(A2)="-"),"",TRIM(CLEAN(SUBSTITUTE(SUBSTITUTE(A2,UNICHAR(160)," "),CHAR(9)," "))))
```

&#91;image: Cleaning cells, with B2 selected\]

In column A of the picture a red dot is a space, an arrow is a tab, and a small circle is a non-breaking space. They are drawn so you can see them; Excel shows them as nothing, which is exactly why they cause trouble. Row 2 goes from 15 characters to 10. Row 4 looks the same before and after but loses a non-breaking space that would have stopped the address matching the reference file.

TRIM alone is not enough. It leaves non-breaking spaces, which arrive in anything copied from a web page or a PDF. UNICHAR needs Excel 2013 or later; in older Windows Excel use CHAR(160) instead.

The application also fixes casing for names in a way that keeps DiNapoli and O'Brien intact. Excel's PROPER function would turn them into Dinapoli and O'brien, so leave casing alone unless you check every name by hand.

## 3. Split a jammed address

File A holds the street, the apartment, the city, the state and the ZIP in one cell. Splitting it takes one built-in tool and four short formulas.

**Split at the commas.**

1. Copy the address column to a working sheet.
2. Select it, then Data, Text to Columns, Delimited, tick Comma, Finish. The parts land in Part 1 to Part 4.
3. Add five columns to the right. Street, Unit, City, State, Zip.
4. Street is Part 1. `=TRIM(B2)`
5. Unit is Part 2 only when there are four parts and Part 2 has a digit in it. City names never have digits, so this never takes a city for a unit.

```
=IF(AND(COUNTA(B2:E2)=4,SUMPRODUCT(--ISNUMBER(FIND({0,1,2,3,4,5,6,7,8,9},C2)))>0),TRIM(C2),"")
```

6. City is always the part before the last one, whether or not there is a unit. `=TRIM(INDEX(B2:E2,1,COUNTA(B2:E2)-1))`
7. The last part holds the state and the ZIP. State `=LEFT(TRIM(INDEX(B2:E2,1,COUNTA(B2:E2))),2)` and Zip `=RIGHT(TRIM(INDEX(B2:E2,1,COUNTA(B2:E2))),5)`

&#91;image: Splitting a jammed address, with the city formula in H2\]

COUNTA(B2:E2) counts how many parts the row has. That one number is what lets the same formulas handle a row with an apartment (four parts) and a row without one (three parts).

**A unit stuck to the street with no comma.** File B has 117-19 45TH AVE 14A, and other exports have Apt. 10 R and APT18L. The trick is to find where the unit starts, then cut there.

1. Last word of the street, in B15. `=TRIM(RIGHT(SUBSTITUTE(TRIM(A15)," ",REPT(" ",99)),99))`
2. Where the unit starts, in C15. It looks for " apt" or " #" first. Failing that, it takes a last word that starts with a digit and ends with a letter, such as 14A or 4B, unless it is an ordinal such as 45TH.

```
=IFERROR(SEARCH(" apt",A15),IFERROR(SEARCH(" #",A15),IF(AND(ISNUMBER(--LEFT(B15,1)),NOT(ISNUMBER(--RIGHT(B15,1))),ISERROR(MATCH(UPPER(RIGHT(B15,2)),{"ST","ND","RD","TH"},0))),LEN(TRIM(A15))-LEN(B15),0)))
```

3. Street `=IF(C15>0,TRIM(LEFT(A15,C15)),TRIM(A15))` and Unit `=IF(C15>0,TRIM(MID(A15,C15,99)),"")`

&#91;image: Separating a unit from the street, with the position formula in C15\]

2300 Avenue U and 88 Meserole St come through whole, with no unit, because their last words do not start with a digit.

In Microsoft 365, `=TEXTSPLIT(A2,",")` does the first step in one formula. The application handles two shapes these formulas miss. A unit written after the city, and a unit word with no number such as Rear or Basement. Look over the Unit column by eye after splitting.

## 4. Split a jammed name

File A writes names as Last, First Middle. The comma is the anchor. Everything before it is the last name, and the first word after it is the first name.

1. Add four columns beside the name. Last\_Name, First\_Name, Middle, and a helper called Rest.
2. Rest is everything after the comma. `=TRIM(MID(A2,FIND(",",A2)+1,99))`
3. Last\_Name is everything before the comma. `=TRIM(LEFT(A2,FIND(",",A2)-1))`
4. First\_Name is the first word of Rest. `=IFERROR(LEFT(E2,FIND(" ",E2)-1),E2)`
5. Middle is the first letter of the second word. `=IFERROR(LEFT(MID(E2,FIND(" ",E2)+1,99),1),"")`

&#91;image: Splitting Last, First Middle, with First\_Name in C2\]

The IFERROR in First\_Name matters. Without it, a name with no middle initial, such as Adeyemi, Kira, would show #VALUE! because there is no second space to find.

**Names written First Middle Last, with no comma.** Flash Fill is faster than formulas here.

1. Add a column and type the first name for the first two rows by hand.
2. Click the next empty cell in that column and press Ctrl+E. Excel fills the rest by copying your pattern.
3. Do the same in a second column for the last name.
4. Read every row it filled. Flash Fill guesses, and a suffix such as Jr or a double surname such as Adeyemi-Cole is where it guesses wrong.

Flash Fill does not update when the source changes. Rerun it on new rows.

## 5. Check every row and list its problems

The application sends a row to review when any check fails, and says why in plain words. In Excel, one Problems column does the same. A row with anything in it needs a person; a row with nothing in it passed.

1. Add Zip5, the first five characters of the ZIP, so ZIP+4 becomes a plain ZIP. `=IF(LEN(TRIM(F2))>=5,LEFT(TRIM(F2),5),TRIM(F2))`
2. Add Zip ok?, TRUE only when Zip5 is exactly five digits. `=AND(LEN(G2)=5,ISNUMBER(--G2))`
3. Add Problems. Each IF adds one reason, and TEXTJOIN strings them together with a semicolon, skipping the blanks.

```
=TEXTJOIN("; ",TRUE,IF(B2="","Missing First_Name",""),IF(C2="","Missing Last_Name",""),IF(D2="","Missing Address_1",""),IF(NOT(H2),IF(F2="","No ZIP","Invalid ZIP: "&F2),""),IF(NOT(OR(UPPER(E2)="NY",UPPER(E2)="NEW YORK")),"State is not NY: "&E2,""))
```

4. Color the review rows. Select the table from A2, then Home, Conditional Formatting, New Rule, Use a formula. Type `=$I2<>""` and pick a light red fill.

&#91;image: One Problems column, with E106's two problems in I5\]

P-9 passes even though its ZIP was typed as 11201-1234 and its state as New York, because the formulas read past both. E106 fails twice, with no address and no ZIP. X-1 and X-2 are two extra rows made up only for this picture, to show the other checks.

To add a check for a new column, add one more IF inside the TEXTJOIN. To make a date of birth required, for example, add `IF(J2="","Missing DOB","")`.

TEXTJOIN needs Excel 2019 or Microsoft 365. In older Excel, join the IFs with & instead and accept a trailing semicolon.

## 6. Fill the city from the ZIP and catch conflicts

The first three digits of a New York City ZIP name its borough. That one fact fills a blank city, turns a neighborhood into a borough, and catches a city that disagrees with its ZIP.

1. Beside the work, type two small lookup tables. ZIP prefix to borough in I:J (100, 101 and 102 are New York, 103 is Staten Island, 104 is Bronx, 112 is Brooklyn, 110, 111, 113, 114 and 116 are Queens). Neighborhood to borough in L:M (Woodside is Queens, Bushwick is Brooklyn, and so on).
2. Borough from ZIP. `=IFERROR(INDEX($J$2:$J$13,MATCH(--LEFT(C2,3),$I$2:$I$13,0)),"")`
3. City folded to borough. A neighborhood becomes its borough; anything else stays as typed. `=IFERROR(INDEX($M$2:$M$11,MATCH(TRIM(B2),$L$2:$L$11,0)),TRIM(B2))`
4. City to use. The typed city when there is one, otherwise the borough from the ZIP. `=IF(E2="",D2,E2)`
5. Conflict flag. `=IF(AND(E2<>"",D2<>"",E2<>D2),"City conflicts with ZIP",IF(AND(E2="",D2=""),"No city and no usable ZIP",""))`
6. Color the conflicts with the same conditional formatting as section 5, using `=$G2<>""`.

&#91;image: Filling cities and catching conflicts, with E105's conflict in G4\]

E105 says Brooklyn but its ZIP, 10007, is Manhattan, so it is flagged for a person rather than changed. P-10 had no city and gets New York from its ZIP. E104 said Woodside and becomes Queens. P-12 has no ZIP, so its typed city stands and the missing ZIP is caught in section 5.

The neighborhood table is the part that grows. Every time a new neighborhood name shows up in a file, add a row. The application ships 114.

In Microsoft 365, `=XLOOKUP(--LEFT(C2,3),$I$2:$I$13,$J$2:$J$13,"")` replaces the INDEX and MATCH pair.

## 7. Place addresses on the map, add districts, and protect the point

Excel cannot geocode. The application calls Geosupport, the City's address engine, on this computer. In Excel you get the same answers by running your addresses through Geosupport or the City's Geoclient batch once, pasting the results in as a reference sheet, and looking each address up in it.

1. Get a reference sheet with one row per address. Street, ZIP, latitude, longitude, Senate, Assembly and Council district. Paste it beside the work, in K:P.
2. In the reference sheet, build a key that joins street and ZIP. `=UPPER(TRIM(street))&"|"&zip` so 209 Joralemon St in 11201 becomes 209 JORALEMON ST|11201.
3. Build the same key on your rows, in D. `=UPPER(TRIM(B2))&"|"&C2`
4. Look up each value by key. Latitude is `=IFERROR(INDEX($L$2:$L$8,MATCH(D2,$K$2:$K$8,0)),"not found")` and the other four columns use the same formula with M to P in place of L.

&#91;image: Looking up coordinates and districts, with latitude in E2\]

1 Nowhere Rd shows not found in every column. That row goes to review as an address that could not be matched. The coordinates and districts in the picture are made up.

**The privacy offset.** The application never stores a client's front door. It moves each point 150 to 250 feet in a random direction, after the districts are read from the true point.

1. Two numbers between 0 and 1 per row. For a result that stays the same every time the sheet recalculates, derive them from the row number. `=MOD(ROW()*9301+49297,233280)/233280` and `=MOD(ROW()*7919+104729,233280)/233280`
2. Distance in feet, 150 to 250. `=150+100*D11`
3. Direction, a random angle. `=2*PI()*E11`
4. The moved point. One degree of latitude is about 364,000 feet, and a degree of longitude shrinks with the cosine of the latitude.

```
Jittered latitude:   =B11+F11*COS(G11)/364000
Jittered longitude:  =C11+F11*SIN(G11)/(364000*COS(RADIANS(B11)))
```

&#91;image: Moving each point 150 to 250 feet, with the jittered latitude in H11\]

Do not use RAND(). It gives a new answer on every keystroke, so the same person would be in a different place every time the file opened. Keep the districts from the true point and publish only the moved one.

## 8. Find copies inside one file, keep one, set the rest aside

The same person typed twice into one export is a copy. The application shows each group side by side, a person decides, and the copies are set aside, never deleted. In Excel a match key finds the groups and a dropdown records the decision.

1. Match key. Join the fields that make two rows one person, in capitals so ADA and Ada match. `=UPPER(TRIM(B2))&"|"&UPPER(TRIM(C2))&"|"&D2`
2. Count. How many rows share this key. `=COUNTIF($E$2:$E$8,E2)`
3. Keep or copy. The first row of a group says keep, every later one says which row it copies.

```
=IF(F2=1,"",IF(COUNTIF($E$2:E2,E2)=1,"keep (first of "&F2&")","copy of row "&(MATCH(E2,$E$2:$E$8,0)+1)))
```

4. Decision. Select H2:H8, then Data, Data Validation, List, and type `Copies, keep the first,Different people, keep all`. A person picks one per group.
5. Color every row whose count is more than 1, with conditional formatting on `=$F2>1`.

&#91;image: Finding copies in File A, with the keep-or-copy formula in G5\]

E102 and E103 are the same Ada Sample, one typed in capitals. The formula keeps E102 and marks E103 as a copy of row 4.

The mixed reference `$E$2:E2` is what makes this work. It grows by one row as the formula is filled down, so each row only counts the matches above it.

**Setting aside, not deleting.** Do not use Data, Remove Duplicates on your working rows. It deletes, with no record of what went. Instead, filter column G on copy of, copy those rows to a sheet named Set aside with the reason in a column beside them, then mark their status as Set aside (section 12).

To keep a row other than the first, sort the group so the row you want is on top before the formula runs. The application has a Keep this one button beside every row for this.

## 9. Make every spelling of a program one program

Workforce Development, Workforce and WFD are one program to a person and three to a computer. Counted as typed, one program looks like three, and the per-program count is wrong. A two-column alias table fixes it.

1. Copy every program value from every file into one column on a spare sheet. Then Data, Remove Duplicates on that copy only. You now have each spelling once.
2. Beside each spelling, type the name it should be counted as. That is the alias table, Spelling in E and Counted as in F.
3. On your working rows, add Program, one name. It looks the spelling up and falls back to the spelling itself when it is not in the table. `=IFERROR(INDEX($F$2:$F$9,MATCH(TRIM(B2),$E$2:$E$9,0)),TRIM(B2))`
4. Count from this column from now on, never from the one as typed.

&#91;image: Program spellings folded to one name, with Resident Svcs in C5\]

Resident Svcs becomes Resident Services and WFD becomes Workforce. Housing and Youth are already one spelling each.

Keep the alias table on its own sheet and save the workbook as your template. Next quarter, add any new spelling as a row and every count updates. This is the program grouping the application saves in a set-up.

**A file with no program column.** If every row in one file belongs to one program, type it into a Program column for that file before stacking it in section 1. The application calls this a default for this source only. Without it, those clients are missing from the per-program count.

## 10. Work out who is the same person across files

File A calls him Joseph Smith, E100. File B calls him Joe Smith, P-9. Nothing links the two IDs. The application scores every likely pair on name, date of birth and address, joins only the certain ones, and asks a person about the rest. Excel can do the certain ones with a match key, and flag the uncertain ones for you to decide.

1. Stack the clean rows from both files on one sheet, with Source, First, Last, DOB and Zip5.
2. A nickname table beside the work, in L:M. JOE folds to JOSEPH, BILL to WILLIAM, and so on.
3. Given name folded. The formal name when the nickname table has one. `=IFERROR(INDEX($M$2:$M$5,MATCH(UPPER(TRIM(B2)),$L$2:$L$5,0)),UPPER(TRIM(B2)))`
4. Match key. Folded given name, surname and date of birth. `=F2&"|"&UPPER(TRIM(C2))&"|"&TEXT(D2,"yyyy-mm-dd")`
5. Master ID. The row number of the first row with the same key, so every row of one person gets the same ID. `="M"&TEXT(MATCH(G2,$G$2:$G$13,0),"000")`
6. Soft key, for near misses. Given name and date of birth, without the surname. `=F2&"|"&TEXT(D2,"yyyy-mm-dd")`
7. Needs a person. Flags rows that share a soft key with another row but not a match key. `=IF(AND(COUNTIF($H$2:$H$13,H2)>1,COUNTIF($G$2:$G$13,G2)=1),"same given name and birth date, surname differs: decide","")`

&#91;image: One Master ID per person, with Joe Smith's in I8\]

Joe Smith in row 8 gets M001, the same as Joseph Smith in row 2, because Joe folds to Joseph and the surname and birth date match. Ada Sample gets M003 in both files. Kira Adeyemi and Kira Adeyemi-Cole share a first name and a birth date but not a surname. They could be one woman who married, or two women. The sheet flags them and a person decides; if they are one, overwrite the second Master ID with the first.

The date of birth does most of the work here. Two people can share a name and a ZIP; very few share a name and a birth date. If a file has no birth date, its people can only be matched on name and address, which is much weaker.

**What this misses, compared with the application.** The application also catches a birth date with two digits swapped, a first and last name entered the wrong way around, one half of a double surname, and the same address with a different spelling. A match key needs everything in it to be exact, so each of those is two different people to Excel. Read the Needs a person list with that in mind, and add a second soft key on surname and address if your files carry good addresses.

## 11. Count Goal 1 and Goal 2

Goal 1 is unique clients across every file. Goal 2 is unique clients per program, so a person in two programs counts twice there and once in Goal 1. Both come from the Master ID and the program, one name, on the rows that passed.

1. On a Counts sheet, list the rows that passed or were approved, with Master ID and Program, one name. Rows still in review and rows set aside are not counted.
2. Master and program, the pair Goal 2 counts. `=A2&"|"&C2`
3. Goal 1, each Master ID once. `=SUMPRODUCT(1/COUNTIF(A2:A11,A2:A11))`
4. Goal 2, each Master ID and program pair once. `=SUMPRODUCT(1/COUNTIF(D2:D11,D2:D11))`
5. Per program, unique clients in each. Type the program names in F7 down, then

```
=SUMPRODUCT(($C$2:$C$11=F7)/COUNTIFS($C$2:$C$11,$C$2:$C$11,$A$2:$A$11,$A$2:$A$11))
```

&#91;image: The two counts, with Goal 1 in G3\]

Ten rows passed. They hold 8 people (Goal 1) and 9 person and program pairs (Goal 2), because Ada Sample, M003, is in both Resident Services and Housing. Joseph Smith, M001, appears twice in Workforce but counts once.

The SUMPRODUCT(1/COUNTIF) pattern counts distinct values. Each value that appears three times contributes a third three times, which adds up to one.

**Until the open pairs are decided, Goal 1 is a range.** Kira Adeyemi (M002) and Kira Adeyemi-Cole (M012) are still two Master IDs. If a person decides they are one, Goal 1 drops to 7. Report it as 7 to 8 until then, as the application does.

**With a PivotTable instead.** Select the rows, then Insert, PivotTable, and tick Add this data to the Data Model. Put Program on Rows and Master ID on Values, then open Value Field Settings and choose Distinct Count. The grand total is not Goal 2; add the rows up for that.

In Microsoft 365, `=ROWS(UNIQUE(A2:A11))` and `=ROWS(UNIQUE(D2:D11))` are the short forms.

## 12. Record every decision and keep an audit sheet

The application gives every row a status, lets a person decide the rows in review, and logs every change so any number can be traced back. In Excel, a Status dropdown carries the decision and an Audit sheet carries the history.

1. On the review sheet, add Status and Note columns.
2. Select the Status cells, then Data, Data Validation, List, and type `Clean,Review,Approved as entered,Corrected,Set aside`. Only those five words can go in.
3. For each row with a problem, a person picks a status and writes a short reason in Note.

| Status | Means | Counted? |
| --- | --- | --- |
| Clean | passed every check | yes |
| Corrected | fixed from its own ZIP or street, then checked again | yes |
| Approved as entered | a person accepted it as it stands | yes |
| Review | still waiting on a person | no |
| Set aside | a copy, a total row, or excluded, kept with the reason | no |

&#91;image: Statuses and notes, with the Status dropdown in C3\]

**The Audit sheet.** Excel cannot log its own changes without a macro, so every decision gets one line written by hand. When, Row, Field, Change, Who, Why.

&#91;image: The Audit sheet\]

Write identifiers and field names, never the value itself. The line says E105's City was filled from its ZIP, not that it changed from Brooklyn to New York at a named address. That way the audit sheet can be shared without sharing client data, which is the rule the application follows.

Two habits keep this honest. Never type over a value in the working rows; a correction goes in a new column, as in every section above. And never delete a row; set it aside with a reason.

## 13. Make the output files and prove nothing was lost

The application writes each output file from the statuses, and refuses to report numbers that do not add up. In Excel the same check is four COUNTIFs and one IF.

1. On an Outputs sheet, list every input row with its Status, including the total row and the copies.
2. Count each file's rows.
   - Final\_Clean\_Mapped `=COUNTIF(B2:B15,"Clean")+COUNTIF(B2:B15,"Corrected")+COUNTIF(B2:B15,"Approved as entered")`
   - Manual\_Review\_Needed `=COUNTIF(B2:B15,"Review")`
   - Set\_Aside\_Records `=COUNTIF(B2:B15,"Set aside")`
   - Input rows `=COUNTA(A2:A15)`
3. The check. `=IF(E2+E3+E4=E5,"yes, lossless","NO: rows are missing")`

&#91;image: Every row accounted for, with the check in E6\]

Fourteen rows came in. Ten are clean, two wait for review, and two are set aside (E103, a copy, and the total row). Ten plus two plus two is fourteen, so nothing went missing. If this cell ever says NO, stop and find the missing rows before reporting any number.

**Making each file.**

1. Data, Filter. On Status, tick only the statuses for one file.
2. Select the visible rows, copy, and paste into a new workbook.
3. File, Save As, CSV. Name it as the application would, such as Manual\_Review\_Needed.csv.
4. Repeat for each file. Make the two count files from the Counts sheet in section 11.

In Microsoft 365, `=FILTER(A2:B15,B2:B15="Review")` builds the review list live on its own sheet, and it updates as statuses change.

## Where Excel stops

Everything above reproduces the application's logic, and the fake data gives the same answers in both. What Excel cannot give you is the discipline around the logic. Each row below is something the application does on its own that a spreadsheet leaves to the person using it.

| The application | In Excel | What to do about it |
| --- | --- | --- |
| Checks every matched column against its values and names the right column | nothing warns you | read the first rows of every column before building on it |
| Calls Geosupport for every address on this computer | cannot geocode | run the addresses through Geosupport or Geoclient once and paste the results in as a reference sheet |
| Scores likely pairs on name, birth date, address, nicknames, swapped digits and double surnames | exact match keys only | read the Needs a person list closely; add a soft key on surname and address |
| Logs every change and decision by identifier, automatically | the Audit sheet is typed by hand | write one line for every decision, the same day |
| Refuses to report counts that do not add up | the lossless check is one cell you must look at | put the check at the top of the Counts sheet |
| Never overwrites or deletes; every step adds columns | one keystroke overwrites a cell | work on copies, lock the source sheets with Review, Protect Sheet |
| Remembers the whole set-up for next quarter | the workbook is the set-up | save it as a template with the alias, nickname and neighborhood tables in it |
| Works through 19,000 rows in about a minute | slows past a few thousand rows of these formulas | paste the formula columns as values once each step is checked |

Excel is a good way to understand exactly what the application does, to check one of its answers by hand, or to handle a small batch when the application is not to hand. For the full quarterly run across every system, the application is the safer tool, because it cannot forget a step.
