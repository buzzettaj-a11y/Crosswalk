# Crosswalk by hand: the Excel runbook

Sep 28, 2026 · @Joe Buzzetta

When Crosswalk is unavailable, follow these procedures in order, in one Excel workbook. Each applies the same rule the app applies, with the app's exact wording, so a batch done by hand gives the same clean list, the same review list and the same two counts. Two things differ, and say so where they come up. Map points get a different random privacy offset, and districts stay empty unless Geosupport is installed.

The named formulas, patterns and lookup lists are on the Reference tab.

## At a glance

&#91;embedded content: the 14 procedures and where every row ends\]

Rows with a problem wait in review until a person decides. Only rows that passed or that a person approved reach the two counts.

## Set up the workbook

One workbook holds the whole batch, and no source value is ever typed over. Set it up once and reuse it every quarter.

**Excel version.** You need Excel for Microsoft 365. Type `=REGEXTEST("a","a")` in any cell. TRUE means every formula here will work. #NAME? means your Excel is too old for them. In that case apply each rule by eye with filters, and send any row you are unsure of to review.

**Speed.** Some formulas compare text letter by letter. On a big batch set Formulas > Calculation Options > Manual and press F9 when you want results.

| Sheet | What it holds | Rule |
| --- | --- | --- |
| Src1, Src2, and so on | One source table each, exactly as exported | Never edited |
| Work | An Excel table named Work. One row per source row, every file stacked | Every step adds a column. Nothing is typed over |
| Ref | The lookup tables and named formulas on the Reference tab | Set up once |
| Points | The address reference file (nyc\_address\_points.csv, or the city's full address points export) | Never edited |
| Programs | Every program spelling and the name it counts under | Filled in P5 |
| Dupes | Duplicate groups inside one file and the decision for each | Filled in P8 |
| Decisions | One line per review decision | Filled in P10 |
| Pairs | Records that may be one person, their points and the decision | Filled in P11 |
| Counts | Goal 1 and Goal 2 | Filled in P12 |
| Audit | One line per change or decision | Added to at every step |

### The four rules that keep it safe

1. **Never type over a source value.** Src sheets stay as exported. Work starts as a pasted copy, and every step adds a new column beside it.
2. **Never merge on a guess.** Only two joins happen without a person. Identical rows that share one Client ID (P8), and cross-file records that meet the automatic rule in P11. Everything else is a written decision.
3. **Every row ends in exactly one place.** Clean, still in review, or set aside. Nothing is deleted. The check in P13 proves the three add up to the rows you loaded.
4. **Keep it private.** Work offline. Never paste client data into a website, a chat tool or an online geocoder. The Audit sheet holds file names, row numbers, Client IDs and column names. Never a client's name or street.

### The six statuses

Every row in Work gets one of these in its Status column. They are the exact words the app writes in Resolution\_Status.

| Status | Meaning | Output file |
| --- | --- | --- |
| Passed every check | No problem on the row, including a row that passes after an approved fill | Final\_Clean\_Mapped |
| Approved as entered by reviewer | Had a problem, and a person accepted the row as it stands | Final\_Clean\_Mapped |
| Pending | Waiting for a person to look at it row by row | Manual\_Review\_Needed |
| Held | Parked on purpose for later | Manual\_Review\_Needed |
| Rejected | A person looked and it cannot be used as it stands. Fix it at the source | Manual\_Review\_Needed |
| Set aside | Excluded by a decision. Kept and listed, never deleted | Manual\_Review\_Needed and Set\_Aside\_Records |

## P1 Load the files and find the tables

Bring every export in as text, split out each table, and decide which tables are lists of people. The app reads every value as text, so Excel must too.

1. **Load as text.** Data > Get Data > From File. Pick the file (CSV, TSV, Excel, JSON or XML). Choose Transform Data. Select every column and set Data Type to Text. Close & Load to a new sheet named Src1, then Src2 for the next table. This keeps 11201-1234 and 000123 exactly as exported.
2. **Find the tables.** A table is a block of filled cells with blank rows or blank columns around it. One sheet can hold several. Give each block its own Src sheet.
3. **Pick the header row.** It is the row holding the column names. In Power Query use Remove Top Rows for any title rows above it, then Use First Row as Headers.
4. **Check the header row.** Pick again if any of these is true.
   - The row is empty.
   - A third or fewer of its cells have a value. That is a title, not column names.
   - Half or more of its cells are numbers, dates or ZIPs.
   - Two columns would get the same name.
   - The row under it has the same shape, number under number and word under word. That means you picked a data row.
5. **Keep or skip each table.** Keep it when it has name and address columns, three or more address columns, or two or more person columns. Skip it when its columns are totals (Total, Count, Sum, Average, Percent, Rate, Subtotal). Write each skipped table in Audit.
6. **Mark sensitive columns.** A column whose name starts with ssn, socialsecurity, dob, dateofbirth, birthdate, birth, race, ethnicity, gender, sex, diagnosis, medicaid, medicare or income holds sensitive data. Do not copy it into Work unless you need it. Date of birth is worth keeping because it makes P11 far stronger.
7. **Watch for repeat exports.** A file name containing copy, final, backup, bkp, old, draft, temp, tmp, verified, upload, done, new, latest, v1, v2, v3, test, duplicate or dup is often a second version of another export. Load only one version.
8. **Name each table the app's way.** File name, sheet, then cell range, joined by " :: ". For example `legacy_export.xlsx :: Sheet1 :: A1:I58`, or `clinic_export.csv :: A1:K120` for a file with no sheets. This name goes in the File column in P2 and in Source\_File in the clean output.

**Audit line for each table.** `[<table name>] loaded, <rows> rows, <columns> columns, header row <n>, included` (or `skipped: summary table`).

## P2 Match columns to the standard fields

Stack every kept table into Work under one set of columns, check each match against its values, and write down any per-file default.

| Work column | Standard field | Required | Max length | Note |
| --- | --- | --- | --- | --- |
| In\_First | First\_Name | Yes | 60 |  |
| In\_Middle | Middle\_Initial | No | 1 |  |
| In\_Last | Last\_Name | Yes | 60 |  |
| In\_Name | none | No | none | Only for a file with the whole name in one column. P4 splits it |
| In\_ID | Client\_ID | Yes | 30 |  |
| In\_Addr1 | Address\_1 | Yes | 150 | A jammed address goes here whole. P4 splits it |
| In\_Addr2 | Address\_2 | No | 150 |  |
| In\_City | City | Yes | 50 | May stay empty. The ZIP fills it |
| In\_State | State | Yes | 2 | May stay empty. It becomes NY |
| In\_Zip | Zip | Yes | 5 |  |
| In\_Program | Program | No | 80 |  |
| In\_DOB | Date of birth, if you added it | No | none | Any other added field gets its own In\_ column |

1. **Build Work.** Type the headers File, Row, the In\_ columns above, and In\_All. Select them and press Ctrl+T. Name the table Work (Table Design > Table Name).
2. **Paste each table.** For each kept Src table, copy the values of each matched column and Paste Special > Values under its In\_ column. Leave an In\_ column blank when the file has nothing for it. Keep the files in the order you loaded them. Several later rules keep "the first" row.
3. **File and Row.** File is the table name from P1 on every row. Row counts from 0 for the first row under the header, then 1, 2, 3. The app numbers rows the same way.
4. **In\_All.** On a scratch sheet, in A2 enter `=TEXTJOIN(CHAR(31),TRUE,CLEANCELL(Src1!A2:K2))` with the range covering that table's columns, and fill down one row per data row. This leaves the Src sheet untouched. Paste the values into In\_All. P3 uses it to spot total rows.
5. **Check each match.** Filter each In\_ column and look at the first 200 values. The app warns on these signs. A warning never blocks you. It means look again.

| Field | Warn when |
| --- | --- |
| Any required field | Fewer than half the rows have a value. Most rows would fail as missing |
| Address\_1 | Over half are dates. Or under 40% are a house number then a street name. Or over 40% start with a unit word or # (that column belongs in Address\_2). Or over half are digits only. Or under 40% hold any digit |
| Zip | Under half are 5 digits or ZIP+4, and over 30% are 4 digits (a lost first digit). Or under half are 5 digits at all |
| State | Under 60% are two letters |
| City | Over 30% contain a digit. Or there are over 25 different values, more than half the rows, and under 20% are boroughs |
| First\_Name, Last\_Name | Over 30% look like addresses (the columns are one across). Or over 20% contain a digit |
| Middle\_Initial | Over 60% are longer than one letter. Only the first letter is kept |
| Client\_ID | Over half the rows share one value. It cannot tell people apart |
| Program | Over 70% are numbers. Counting by program needs names, not codes |
| Address\_2 | More than 5 values and under 30% look like a unit |

6. **Per-file defaults.** When a file leaves a field out and every row shares one value, most often the program, add a line to the Defaults table on Ref with File, Field and Value. A default only fills a blank. It never replaces a value the file supplied. A line with File set to (all) applies to every file, after the file's own line.

**Audit lines.** One per match, `[<table>] <field> matched to column '<column name>'`. One per default, `[<table>] default for <field> set to '<value>'`.

## P3 Clean every value and mark total rows

Every value gets the same light clean before any rule reads it, and rows that are totals rather than people are marked first.

**The clean rule.**

- Tabs, line breaks and non-breaking spaces become spaces. Runs of spaces become one. Spaces at both ends go.
- A blank value stays empty. So does null, none, n/a, na, #n/a, nan, nil or (null), in any capitals.
- A dash is not on that list. A cell holding - stays as typed.
- Nothing else changes. Capitals, spelling and punctuation stay as typed.

**Add these columns to Work.** Each line in a formula box is a column name, then the formula for its first row. Excel fills the rest of the column. CLEANCELL and CLEANORDEF are named formulas on the Reference tab. CLEANORDEF cleans the value and, when it comes out empty, uses the Defaults line for that file and field.

```
C_First   = CLEANORDEF([@In_First],[@File],"First_Name")
C_Middle  = CLEANORDEF([@In_Middle],[@File],"Middle_Initial")
C_Last    = CLEANORDEF([@In_Last],[@File],"Last_Name")
C_Name    = CLEANCELL([@In_Name])
C_ID      = CLEANORDEF([@In_ID],[@File],"Client_ID")
C_Addr1   = CLEANORDEF([@In_Addr1],[@File],"Address_1")
C_Addr2   = CLEANORDEF([@In_Addr2],[@File],"Address_2")
C_City    = CLEANORDEF([@In_City],[@File],"City")
C_State   = CLEANORDEF([@In_State],[@File],"State")
C_Zip     = CLEANORDEF([@In_Zip],[@File],"Zip")
C_Program = CLEANORDEF([@In_Program],[@File],"Program")
```

Add a C\_ column the same way for each added field, such as C\_DOB.

**Note each default used.** Add a Def\_Note column. For each Defaults line, filter Work to that file with the field's In\_ column empty after the clean rule, which includes cells holding N/A, null or only spaces. In Def\_Note on those rows type the note below. Skip rows marked Summary.

| Default from | Field | Note, exactly |
| --- | --- | --- |
| This file's line | Any field | `<Field> was blank, set to the default '<Value>' from this source` |
| An (all) line | A standard field | `<Field> was blank, set to the default '<Value>' from the schema` |
| An (all) line | Program or an added field | `<Field> was blank, set to the default '<Value>'` |

**Mark total rows.** A row is a total, count or heading when any of these holds, checked in this order.

1. A name column starts with a total word and the address is empty. Summary.
2. Otherwise, any name or the address has a value. Not summary.
3. Otherwise, every cell in the row is empty. Not summary.
4. Otherwise, any cell starts with a total word. Summary.
5. Otherwise, every filled cell holds only digits, commas, periods, dashes, % or $. Summary.

The total words are total, grand total, subtotal, sub-total, sum, count, average, avg, mean, summary, overall, all clients, all records, all programs, and n= at the start of a cell. The pattern is SummaryWords on the Reference tab.

```
Summary = LET(f,CLEANCELL([@In_First]&[@In_Name]), l,CLEANCELL([@In_Last]),
  a,CLEANCELL([@In_Addr1]), v,IFERROR(TEXTSPLIT([@In_All],CHAR(31)),""),
  IF(AND(OR(REGEXTEST(f,SummaryWords),REGEXTEST(l,SummaryWords)),a=""),TRUE,
  IF(OR(f<>"",l<>"",a<>""),FALSE,
  IF([@In_All]="",FALSE,
  OR(OR(REGEXTEST(v,SummaryWords)),AND(REGEXTEST(v,"^[\d,.\-%$ ]+$")))))))
```

A row marked TRUE gets one problem and nothing else. Every later check skips it.

| Scenario | Problem, exactly |
| --- | --- |
| 0 Not a record | `Summary row, not a client record (a total, count or heading); set aside` |

## P4 Split jammed addresses and names

The app reads every address from the right. It takes the ZIP, then the state, then the city, then the unit, and whatever is left is the street. Anything it cannot place stays in the street, so nothing is lost. Run this on every row, not only the jammed ones.

**The address rule, in order.**

1. **Separators.** A dash, slash, semicolon, colon, pipe or backslash with a space on both sides counts as a comma. 40-22 and c/o have no spaces, so they stay. Repeated commas become one. USA, U.S.A., US or United States at the end goes, only as its own word. Spaces, periods, commas and semicolons at the end go.
2. **ZIP.** Five digits at the very end, with or without a dash and four more.
3. **State.** NY, N.Y., N Y, NY., New York or New York State at the end, after a space or comma. Only New York is recognized. New York at the very end is read as the state, not the city.
4. **City, when there are commas.** Split on commas. The first piece is the street. A later piece that looks like a unit is never the city. The city is the last piece that is not a unit.
5. **City, when there are no commas.** Only if a ZIP or state was found. Try the last three words, then two, then one. They are the city if they are a borough name or a neighborhood on the Reference tab. At least one word must stay for the street.
6. **Unit.** A comma piece that looks like a unit becomes Address\_2. A unit at the end of the street is also peeled off. When both happen, the unit is the peeled one, a space, then the piece.
7. **Tidy each part.** Repeated separators become one, no space before a comma, semicolon or colon, and no separator at either end.

**What counts as a unit at the end of a street.** A unit word, then an optional period, # and colon, then a designator. The unit words are apt, apartment, suite, ste, unit, fl, floor, rm, room, bldg, building, dept, department, space, spc, lot, trailer, hangar, slip, pier, stop. A designator always has a digit, such as 10R, 10 R, 18L, 12-B or B4. Also a # then a designator or one or two letters, an ordinal floor such as 4th Floor, and penthouse, basement, bsmt, lobby or mezzanine. A bare 14A straight after a street type (St, Ave, Rd, Blvd, Pl, Dr and the rest) is a unit too. Only digits then one letter, so Avenue U and Route 9 stay whole. If the whole street is a unit, it stays as the street.

**What makes a comma piece look like a unit.** It starts with apt, apartment, ste, suite, unit, fl, floor, rm, room, bldg, building, ph, penthouse, bsmt, basement, lobby, mezzanine, rear, front, no or num. Or it starts with #. Or it is an ordinal then one of those words, such as 4th Fl. Or it is a bare designator such as 14, 2A, 3-L or B12.

| Address as typed | Street | Unit | City | State | ZIP |
| --- | --- | --- | --- | --- | --- |
| 111 test street, Apt. 4, Brooklyn, NY, 11201 | 111 test street | Apt. 4 | Brooklyn | NY | 11201 |
| 117-19 45TH AVE, 14A, QUEENS, NY 11355 | 117-19 45TH AVE | 14A | QUEENS | NY | 11355 |
| 67 Jill Ave Apt#: 11T | 67 Jill Ave | Apt#: 11T |  |  |  |
| 25 Tom Street APT18L | 25 Tom Street | APT18L |  |  |  |
| 88 Grand Concourse Bronx NY 10451 | 88 Grand Concourse |  | Bronx | NY | 10451 |
| 12 Main St - Bklyn - 11211 | 12 Main St |  | Bklyn |  | 11211 |
| 10 Avenue U Brooklyn NY 11223 | 10 Avenue U |  | Brooklyn | NY | 11223 |
| 12 Main St New York | 12 Main St |  |  | NY |  |
| 99 Pine St, c/o Jane Doe, Brooklyn, NY 11201 | 99 Pine St, c/o Jane Doe |  | Brooklyn | NY | 11201 |

The city stays as typed here (Bklyn, QUEENS). P6 turns it into a borough.

**Address columns to add.** The patterns and named formulas are on the Reference tab. Their logic was replayed step for step against the app on 40,000 generated addresses with no difference. Before a real batch, paste the example addresses above into Work and confirm you get the same parts.

```
A_Norm = LET(s,[@C_Addr1], a,REGEXREPLACE(s,SepRun,", "),
  b,TRIM(REGEXREPLACE(a,CommaRun,", ")), cc,REGEXREPLACE(b,Country,""),
  REGEXREPLACE(cc,"[\s.,;]+$",""))
A_Zip = IFERROR(REGEXEXTRACT([@A_Norm],ZipTail,2),"")
A_W1 = IF([@A_Zip]="",[@A_Norm],
  REGEXREPLACE(REGEXREPLACE([@A_Norm],ZipTail,""),"\s*,*\s*$",""))
A_State = IF(REGEXTEST([@A_W1],StateTail),"NY","")
A_W2 = IF([@A_State]="",[@A_W1],
  REGEXREPLACE(REGEXREPLACE([@A_W1],StateTail,""),"\s*,*\s*$",""))
A_City = LET(w,[@A_W2], IF(w="","",
  IF(ISNUMBER(SEARCH(",",w)),
    LET(t,TRIM(TEXTSPLIT(w,",")), s,FILTER(t,t<>"",""),
      IF(COLUMNS(s)<2,"",
        LET(rest,DROP(s,,1), u,MAP(rest,LAMBDA(x,UNITLIKE(x))), o,FILTER(rest,NOT(u),""),
          TIDY(CLEANCELL(TAKE(o,,-1)))))),
    IF(OR([@A_Zip]<>"",[@A_State]<>""),
      LET(ws,TEXTSPLIT(w," "), n,COLUMNS(ws),
        three,IF(n>3,TEXTJOIN(" ",,TAKE(ws,,-3)),""),
        two,IF(n>2,TEXTJOIN(" ",,TAKE(ws,,-2)),""),
        one,IF(n>1,TAKE(ws,,-1),""),
        IF(CITYWORD(three),three,IF(CITYWORD(two),two,IF(CITYWORD(one),one,"")))),
      ""))))
A_Pre = LET(w,[@A_W2],
  IF(ISNUMBER(SEARCH(",",w)),
    LET(t,TRIM(TEXTSPLIT(w,",")), s,FILTER(t,t<>"",""),
      IF(COLUMNS(s)<2,INDEX(s,1),
        LET(rest,DROP(s,,1), u,MAP(rest,LAMBDA(x,UNITLIKE(x))),
          o,FILTER(rest,NOT(u),""), k,FILTER(rest,u,""),
          TEXTJOIN(", ",TRUE,INDEX(s,1),
            IF(COLUMNS(o)>1,DROP(o,,-1),""),
            IF(COLUMNS(k)>1,DROP(k,,1),""))))),
    IF([@A_City]="",w,TRIM(LEFT(w,LEN(w)-LEN([@A_City]))))))
A_UnitSeg = LET(w,[@A_W2],
  IF(ISNUMBER(SEARCH(",",w)),
    LET(t,TRIM(TEXTSPLIT(w,",")), s,FILTER(t,t<>"",""),
      IF(COLUMNS(s)<2,"",
        LET(rest,DROP(s,,1), u,MAP(rest,LAMBDA(x,UNITLIKE(x))),
          IF(OR(u),INDEX(FILTER(rest,u),1),"")))),
    ""))
A_Street = TIDY(CLEANCELL(INDEX(SPLITUNIT([@A_Pre]),1)))
A_Unit = LET(m,INDEX(SPLITUNIT([@A_Pre]),2), g,[@A_UnitSeg],
  TIDY(CLEANCELL(IF(g="",m,IF(m="",g,m&" "&g)))))
```

**The name rule.** Only for files with the whole name in one column (C\_Name).

1. Jr, Sr, II, III or IV at the very end, with or without a period, is moved to the end of the last name.
2. With a comma, the text before the first comma is the last name. The next word is the first name and the word after it is the middle.
3. Without a comma, one word is the first name. Two words are first and last. Three or more are first, middle, and the rest is the last name.
4. The middle becomes its first letter in capitals, only if that first character is a letter.
5. Each part is cleaned with the P3 rule.

| Name as typed | First | Middle | Last |
| --- | --- | --- | --- |
| Smith, John A | John | A | Smith |
| John A Smith | John | A | Smith |
| John Smith Jr. | John |  | Smith Jr |
| Garcia, Ana Maria Lopez | Ana | M | Garcia |
| Maria de la Cruz Lopez | Maria | D | la Cruz Lopez |

The last two show why a jammed name is a weak source. Keep the original column. Fix these at the source when you can.

```
N_Sfx = SUBSTITUTE(IFERROR(REGEXEXTRACT([@C_Name],Suffix,2),""),".","")
N_Core = IF([@N_Sfx]="",[@C_Name],TRIM(REGEXREPLACE([@C_Name],Suffix,"")))
N_First = LET(cc,[@N_Core], IF(cc="","",
  IF(ISNUMBER(SEARCH(",",cc)),
    LET(rest,TRIM(TEXTAFTER(cc,",")), IF(rest="","",TIDY(CLEANCELL(TEXTBEFORE(rest&" "," "))))),
    TIDY(CLEANCELL(TEXTBEFORE(cc&" "," "))))))
N_Mid = LET(cc,[@N_Core], IF(cc="","",
  IF(ISNUMBER(SEARCH(",",cc)),
    LET(tk,IFERROR(TEXTSPLIT(TRIM(TEXTAFTER(cc,","))," "),""),
      MIDINIT(IF(COLUMNS(tk)>1,INDEX(tk,2),""))),
    LET(tk,TEXTSPLIT(cc," "), MIDINIT(IF(COLUMNS(tk)>2,INDEX(tk,2),""))))))
N_Last = LET(cc,[@N_Core], x,[@N_Sfx],
  b,IF(cc="","",IF(ISNUMBER(SEARCH(",",cc)),CLEANCELL(TEXTBEFORE(cc,",")),
    LET(tk,TEXTSPLIT(cc," "), n,COLUMNS(tk),
      IF(n=1,"",IF(n=2,INDEX(tk,2),TEXTJOIN(" ",,DROP(tk,,2))))))),
  TIDY(CLEANCELL(IF(AND(x<>"",b<>""),b&" "&x,b))))
```

Names inside LET are chosen so Excel cannot read them as cell addresses. Never shorten them to c, r, or a letter and a number such as c1.

**Notes to write.** The app notes when it split an address and when the street still holds a comma.

```
Addr_Note = TEXTJOIN("; ",TRUE,
  IF(OR([@A_City]<>"",[@A_Zip]<>""),"Split jammed address into street + city/ZIP",""),
  IF(ISNUMBER(SEARCH(",",[@A_Street])),"Address_1 still contains a comma; possible concatenated fragments",""))
```

## P5 Programs

Goal 2 counts people per program, so every spelling of one program must count under one agreed name. The app only proposes groups. A person confirms every one.

1. **Check the source of each file's program.** It is the column matched to In\_Program in P2, or a Defaults line when the file has no program column. A row with no program stays in the batch. It counts in Goal 1 and is left out of Goal 2.
2. **List every spelling.** On the Programs sheet, in A2 enter `=UNIQUE(FILTER(Work[C_Program],Work[C_Program]<>""))`. In B2 enter `=COUNTIFS(Work[C_Program],A2#)` for the rows using each one. Copy both and paste as values into a table named ProgramMap with columns Variant and Rows.
3. **Group the spellings.** The app proposes two spellings as one program when any of these holds. Use the same tests.
   - **Same once wording is set aside.** Lowercase it. Turn & into and, and other punctuation into spaces. Expand the short forms (dev, admin, mgmt, svcs, res, comm, educ, empl, trng, asst, hsg, wf). Drop the filler words (program, service, department, division, unit, team, office, initiative, project, client, participant, general, the, of, and, for, a, an, and their plurals and short forms). Sort the words left. The same result means the same program. The full lists are on the Reference tab.
   - **Initials.** A short name of 2 to 6 letters built from the longer name's letters in order, starting with its first letter. WFD from Workforce Development. RS from Resident Services. The app also needs a letter for each word, except where filler words are left out.
   - **Nearly the same.** SIMILAR of the two reduced names is 86 or more.
   - **More words on the end.** Workforce and Workforce Development. The shorter name's first real word must have 4 or more letters. These tests only suggest. The map you confirm is what counts, as in the app.
4. **Pick the agreed name.** The app suggests the spelling used on the most rows, alphabetical on a tie. Type over it when the real program name is different.
5. **Fill ProgramMap.** Add columns Agreed and Key. Agreed holds the group's agreed name on every variant in the group, and a variant on its own agrees with itself. Key is `=LOWER(REGEXREPLACE([@Variant],"[^A-Za-z0-9]",""))`. Spellings that differ only in capitals or punctuation share a Key, so they must share an agreed name.
6. **Add to Work.**

```
Program = LET(p,[@C_Program],
  a,IF(p="","",XLOOKUP(LOWER(REGEXREPLACE(p,"[^A-Za-z0-9]","")),ProgramMap[Key],ProgramMap[Agreed],"")),
  IF(a="",p,a))
Prog_Note = IF(EXACT([@Program],[@C_Program]),"",
  "Program '"&[@C_Program]&"' recorded as '"&[@Program]&"', the agreed name for it")
```

7. **Look before you go on.** Insert a PivotTable of Work with Program in Rows and a count of rows. The list should read like your real list of programs. UNIQUE and COUNTIFS ignore capitals, so spellings that differ only in capitals show as one Variant. They share a Key and an agreed name anyway, so no count changes. If two lines are one program, fix ProgramMap and refresh.

**Audit lines.** One per grouped variant, `Programs: '<variant>' counted as '<agreed>'`.

## P6 Standardize each field

Each field is put in one standard form. The app changes only what a rule names, notes every change, and never invents a value except a borough from a New York ZIP.

**Names.** Kept as typed after the P3 clean. A file with a jammed name uses the P4 parts. The middle becomes one capital letter. A full middle name keeps its first letter. A first character that is not a letter is dropped.

```
First   = IF([@C_Name]<>"",[@N_First],[@C_First])
Last    = IF([@C_Name]<>"",[@N_Last],[@C_Last])
Middle  = IF([@C_Name]<>"",[@N_Mid],MIDINIT([@C_Middle]))
MI_Note = LET(t,[@C_Middle], IF(OR([@C_Name]<>"",t=""),"",
  IF(EXACT(UPPER(LEFT(t,1)),LOWER(LEFT(t,1))),"Middle_Initial: dropped non-alphabetic value",
  IF(LEN(t)>1,"Middle_Initial: reduced multi-character value to initial '"&UPPER(LEFT(t,1))&"'",
  IF(EXACT(t,UPPER(t)),"","Middle_Initial: upper-cased to '"&UPPER(t)&"'")))))
```

**Street and unit.** A unit found in the address moves to Address\_2 when Address\_2 is empty. When Address\_2 already holds the same unit, the copy in the street is dropped. Units compare without their label and punctuation, so Apt 2A, apt. 2-a and #2A are one unit. When Address\_2 holds something else, the unit stays in the street and a person decides.

```
Address_2 = IF(AND([@A_Unit]<>"",[@C_Addr2]=""),[@A_Unit],[@C_Addr2])
Address_1 = LET(s,[@A_Street], u,[@A_Unit], addrtwo,[@C_Addr2],
  IF(OR(u="",addrtwo=""),s,IF(AND(UNITKEY(u)<>"",UNITKEY(u)=UNITKEY(addrtwo)),s,TRIM(s&" "&u))))
Unit_Note = LET(u,[@A_Unit], addrtwo,[@C_Addr2], IF(u="","",
  IF(addrtwo="","Moved secondary unit from the address into Address_2",
  IF(AND(UNITKEY(u)<>"",UNITKEY(u)=UNITKEY(addrtwo)),
    "The same unit appeared in the address and in Address_2; kept it in Address_2 and cleaned it out of the street",""))))
Unit_Msg = LET(u,[@A_Unit], addrtwo,[@C_Addr2], IF(OR(u="",addrtwo=""),"",
  IF(AND(UNITKEY(u)<>"",UNITKEY(u)=UNITKEY(addrtwo)),"",
  IF(UNITLIKE(addrtwo),
    "Unit conflict: the address says '"&u&"' but Address_2 says '"&addrtwo&"'; confirm which is correct",
    "The address contains the unit '"&u&"' but Address_2 already holds something else; confirm where the unit belongs"))))
Place_Msg = LET(a,[@Address_1],
  h,LOWER(TRIM(REGEXREPLACE(a,"(?i)\b(?:st|ave|street|avenue|rd|road|blvd)\b\.?$",""))),
  IF(OR(a="",REGEXTEST(a,"^\s*\d")),"",
  IF(OR(ISNUMBER(XMATCH(h,Hoods[Key])),ISNUMBER(XMATCH(h,Boroughs))),
    "Address_1 looks like a place name, not a street address","")))
```

**City.** Use the city column, or the city from P4 when that column is empty. Then try in this order and stop at the first hit.

1. The alias list (24 spellings such as bklyn, qns, nyc, the bronx, s.i.). Any capitals.
2. The neighborhood list (114 names such as Williamsburg, Astoria, Riverdale). Any capitals.
3. SIMILAR against the five boroughs. The best score wins if it is 80 or more. On a tie, the first in the order New York, Brooklyn, Queens, Bronx, Staten Island.
4. Otherwise the city is not recognized.

```
City_Src = IF([@C_City]<>"",[@C_City],[@A_City])
City_Score = LET(t,[@City_Src],
  IF(OR(t="",XLOOKUP(t,CityAliases[Key],CityAliases[City],"")<>"",
    XLOOKUP(t,Hoods[Key],Hoods[Borough],"")<>""),"",
  MAX(MAP(Boroughs,LAMBDA(b,SIMILAR(t,b))))))
City_0 = LET(t,[@City_Src], s,[@City_Score],
  a,XLOOKUP(t,CityAliases[Key],CityAliases[City],""),
  h,XLOOKUP(t,Hoods[Key],Hoods[Borough],""),
  IF(t="","",IF(a<>"",a,IF(h<>"",h,
  IF(s>=80,INDEX(Boroughs,XMATCH(s,MAP(Boroughs,LAMBDA(b,SIMILAR(t,b))))),t)))))
City_Err0 = IF([@City_Src]="","City could not be determined",
  IF(ISNUMBER(XMATCH([@City_0],Boroughs)),"","Unrecognized City: '"&[@City_Src]&"'"))
City_Note = LET(t,[@City_Src], cty,[@City_0], IF(OR(t="",[@City_Err0]<>""),"",
  IF(XLOOKUP(t,CityAliases[Key],CityAliases[City],"")<>"",
    IF(EXACT(cty,t),"","City: normalized '"&t&"'->'"&cty&"'"),
  IF(XLOOKUP(t,Hoods[Key],Hoods[Borough],"")<>"",
    "City: mapped neighborhood '"&t&"' to borough '"&cty&"'",
    "City: fuzzy-matched '"&t&"'->'"&cty&"' ("&[@City_Score]&"%)"))))
```

**State.** Empty becomes NY. NY in any capitals stays NY. New York, N.Y. and NY. become NY. Anything else is kept in capitals and is a problem.

```
State_Src = IF([@C_State]<>"",[@C_State],[@A_State])
State = LET(t,[@State_Src], IF(t="","NY",
  IF(OR(UPPER(t)="NY",LOWER(t)="new york",LOWER(t)="n.y.",LOWER(t)="ny."),"NY",UPPER(t))))
State_Note = LET(t,[@State_Src], IF(t="","State: defaulted empty value to 'NY'",
  IF(EXACT(UPPER(t),"NY"),"",
  IF(OR(LOWER(t)="new york",LOWER(t)="n.y.",LOWER(t)="ny."),"State: normalized '"&t&"' to 'NY'",""))))
State_Err = IF([@State]="NY","","State is not NY: '"&[@State_Src]&"'")
```

**ZIP.** The ZIP column wins. The ZIP from the address is used only when the column is empty. 12345-6789 and 123456789 keep their first five digits. Anything else is not a ZIP.

```
Zip_Chosen = IF([@C_Zip]<>"",[@C_Zip],[@A_Zip])
Zip_5 = LET(z,[@Zip_Chosen],
  IF(OR(REGEXTEST(z,"^\d{5}(-\d{4})?$"),REGEXTEST(z,"^\d{9}$")),LEFT(z,5),""))
Zip_Note = LET(p,[@C_Zip], f,[@A_Zip], z,[@Zip_Chosen],
  n,IF(AND(p="",f<>""),"Zip: column empty; recovered ZIP from address text",
    IF(AND(p<>"",f<>"",p<>f,LEFT(f,5)<>LEFT(p,5)),
      "Zip: kept mapped column '"&p&"'; address text showed differing '"&f&"'","")),
  IF(n<>"",n,IF(REGEXTEST(z,"^\d{5}-\d{4}$"),"Zip: trimmed ZIP+4 to 5-digit",
    IF(REGEXTEST(z,"^\d{9}$"),"Zip: trimmed 9-digit ZIP to 5-digit",""))))
Zip_Err0 = IF([@Zip_5]="","Invalid ZIP Code format: "&IF([@Zip_Chosen]="","(blank)",[@Zip_Chosen]),"")
```

**The ZIP settles the borough.** A New York ZIP names its borough (ranges on the Reference tab). When the city is empty or not recognized, the borough from the ZIP fills it. When the city is a borough and the ZIP says another, neither wins. The row goes to a person.

```
ZIP_Boro = BORO([@Zip_5])
From_ZIP = AND([@ZIP_Boro]<>"",OR([@City_Err0]<>"",[@City_0]=""))
City = IF([@From_ZIP],[@ZIP_Boro],[@City_0])
City_Err = IF([@From_ZIP],"",[@City_Err0])
ZipCity_Note = IF([@From_ZIP],"City set to '"&[@ZIP_Boro]&"' from ZIP "&[@Zip_5],"")
Conflict_Msg = LET(cty,[@City_0], zb,[@ZIP_Boro],
  IF(OR(zb="",[@City_Err0]<>"",cty="",cty=zb),"",
  "City/ZIP conflict: City says '"&cty&"'"&
  IF(LOWER([@City_Src])=LOWER(cty),""," (entered as '"&[@City_Src]&"')")&
  " but ZIP "&[@Zip_5]&" is in "&zb&"; confirm which is correct"))
```

**Second chance for city and ZIP.** A city that is missing or not recognized is not yet a problem when the row has a street and a ZIP. A ZIP that is missing or not valid is not yet a problem when the row has a street and a borough. P9 tries the street against the reference file first. A row that has another problem is never tried, so it never gets these two messages, exactly as in the app.

```
Needs_City = AND([@City_Err]<>"",[@Address_1]<>"",[@Zip_5]<>"")
Needs_Zip  = AND([@Zip_Err0]<>"",[@Address_1]<>"",ISNUMBER(XMATCH([@City],Boroughs)))
City_Msg   = IF(AND([@City_Err]<>"",NOT([@Needs_City])),[@City_Err],"")
Zip_Msg    = IF(AND([@Zip_Err0]<>"",NOT([@Needs_Zip])),[@Zip_Err0],"")
```

**Added fields.** Each added field is checked against its type. A value that does not fit is a problem. It is never forced.

| Type | Accepted | Stored as | Problem, exactly |
| --- | --- | --- | --- |
| Date | 2024-03-15, 3/15/2024, 15.03.2024, 3/15/24, or a 5-digit Excel date number. A two-digit year of 25 or less is 20xx, above 25 is 19xx. Day and month typed the wrong way around are swapped when only one reading is a real date | 2024-03-15 | `<Field> is not a date that can be read ('<value>')` |
| Yes or no | y, yes, true, t, 1 and n, no, false, f, 0 | Yes or No | `<Field> must be yes or no` |
| Whole number | Digits, with a minus in front if needed | As typed | `<Field> must be a whole number` |
| Number | Digits with optional decimals. Commas are removed | Without commas | `<Field> must be a number` |
| Text | Anything | As typed | none |

For a date field, `DOB = DATEFIX([@C_DOB])`. DATEFIX returns #BAD for a value that is not a date. When the stored form differs from the typed one, `Type_Note = IF(AND([@DOB]<>"",[@DOB]<>"#BAD",NOT(EXACT([@DOB],[@C_DOB]))),"DOB was written in a standard form for its type","")` writes `<Field> was written in a standard form for its type`.

**Notes this procedure writes.** Addr\_Note from P4, MI\_Note, Unit\_Note, City\_Note, State\_Note, Zip\_Note, ZipCity\_Note, Prog\_Note from P5, and Def\_Note from P3. Join them with `Notes = TEXTJOIN("; ",TRUE,[@Def_Note],[@Addr_Note],[@Unit_Note],[@City_Note],[@State_Note],[@Zip_Note],[@MI_Note],[@ZipCity_Note],[@Type_Note],[@Prog_Note])`. Notes never send a row to review. They go to the Audit sheet in P14.

## P7 Check every row

A row with any problem goes to review. The problems are joined with a semicolon and a space, in the order below, which is the order the app writes them. Keep the wording exact, because the review groups in P10 are found by these words.

| Order | Scenario | Problem, exactly | Comes from |
| --- | --- | --- | --- |
| 1 | 1 Address parsing | `Unit conflict: the address says '<unit>' but Address_2 says '<address 2>'; confirm which is correct` | Unit\_Msg |
| 1 | 1 Address parsing | `The address contains the unit '<unit>' but Address_2 already holds something else; confirm where the unit belongs` | Unit\_Msg |
| 2 | 3 Verification | `Address_1 looks like a place name, not a street address` | Place\_Msg |
| 3 | 3 Verification | `State is not NY: '<state>'` | State\_Err |
| 4 | 3 Verification | `Missing First_Name`, then `Missing Last_Name` | First, Last empty |
| 5 | 7 ETL artifact | `Name field contains digits; possible column misalignment` | A digit in First or Last |
| 6 | 3 Verification | `Missing Client_ID`, then `Missing Address_1` | C\_ID, Address\_1 empty |
| 7 | 3 Verification | `City/ZIP conflict: City says '<city>' (entered as '<typed>') but ZIP <zip> is in <borough>; confirm which is correct` | Conflict\_Msg. The part in brackets only when the typed city differs from the borough name |
| 8 | 3 Verification | `City could not be determined` or `Unrecognized City: '<city>'` | City\_Msg |
| 9 | 3 Verification | `Invalid ZIP Code format: <zip>` or `Invalid ZIP Code format: (blank)` | Zip\_Msg |
| 10 | 3 Verification | `<Field> exceeds max length <max> (got <length>)` | Each standard field in order, First\_Name to Zip |
| 11 | 3 Verification | `Missing <Field>`, the length problem, then the type problem | Program, then each added field, in column order |
| 12 | 4 Deduplication | `Duplicate within file by your rule (matched on <fields>), copy of row <n>; set aside` | P8 |
| 13 | 9 Duplicate | `Confirmed duplicate: identical record with the same Client ID` or `Same Client ID '<id>' used by records with different data; review required (not merged)` | P8 |
| 14 | 3 Verification | `City/geocode mismatch: row says <city>, gazetteer says <borough>` | P9 |
| 15 | 3 Verification | The city or ZIP problem held back in P6, when P9 cannot fill it | P9 |
| 16 | 12 Geolocation | `Address could not be matched locally` or `No reference points in this ZIP` | P9, only when a map match is required |

A total row from P3 gets only its own problem. Nothing else is checked.

```
Len_Msg = TEXTJOIN("; ",TRUE,
  LENCHK("First_Name",[@First],60), LENCHK("Middle_Initial",[@Middle],1),
  LENCHK("Last_Name",[@Last],60), LENCHK("Client_ID",[@C_ID],30),
  LENCHK("Address_1",[@Address_1],150), LENCHK("Address_2",[@Address_2],150),
  LENCHK("City",[@City],50), LENCHK("State",[@State],2), LENCHK("Zip",[@Zip_5],5))
Added_Msg = TEXTJOIN("; ",TRUE, LENCHK("Program",[@C_Program],80),
  IF([@DOB]="#BAD","DOB is not a date that can be read ('"&[@C_DOB]&"')",""))
Problems = IF([@Summary],
  "Summary row, not a client record (a total, count or heading); set aside",
  TEXTJOIN("; ",TRUE, [@Unit_Msg], [@Place_Msg], [@State_Err],
    IF([@First]="","Missing First_Name",""), IF([@Last]="","Missing Last_Name",""),
    IF(REGEXTEST([@First]&[@Last],"\d"),"Name field contains digits; possible column misalignment",""),
    IF([@C_ID]="","Missing Client_ID",""), IF([@Address_1]="","Missing Address_1",""),
    [@Conflict_Msg], [@City_Msg], [@Zip_Msg], [@Len_Msg], [@Added_Msg]))
```

Adjust Added\_Msg to your added fields. A required added field adds `IF([@DOB]="","Missing DOB","")` in front of its other checks. Program uses the value as the file had it, before P5 gave it the agreed name, which is what the app checks.

P8 and P9 add Dup\_Msg and Geo\_Msg. The final list is `Error_Reason = TEXTJOIN("; ",TRUE,[@Problems],[@Dup_Msg],[@Geo_Msg])`. A row with an empty Error\_Reason has Status Passed every check. Every other row has Status Pending until P10.

## P8 Duplicates

Three checks, in this order. Only one of them sets a row aside without a person, and only when the rows are identical and share a Client ID. The other two are shown for a decision and never merged.

### A. Copies inside one file, by your rule

Two rows in the same file are a possible copy when they match on the rule's fields. The standard rule is First\_Name, Last\_Name and Zip, and one rule covers every file. Capitals, spacing and punctuation are ignored, and a ZIP counts by its first five digits. A row with any rule field empty is never grouped. A file with no ZIP column has no ZIP to match, so the rule is not applied to it.

```
DupKey = LET(f,NORMF([@First]), l,NORMF([@Last]), z,NORMZ([@C_Zip]),
  nozip,COUNTIFS(Work[File],[@File],Work[In_Zip],"?*")=0,
  IF(OR(f="",l="",z="",nozip),"",[@File]&"|"&f&"|"&l&"|"&z))
Dup_Size = IF([@DupKey]="",0,COUNTIFS(Work[DupKey],[@DupKey]))
```

1. On the Dupes sheet list each key with Dup\_Size of 2 or more, its rows side by side, and a Decision column.
2. Decide each group. Look at the ID, street, unit and program before you do.

| Decision | What happens |
| --- | --- |
| Copies, keep the first | The first row stays. Each other row gets the problem `Duplicate within file by your rule (matched on First_Name, Last_Name, Zip), copy of row <n>; set aside`, where n is the kept row's Row plus 1 |
| Copies, keep row n | The same, keeping the row you chose |
| Different people, keep all | Nothing is marked. The group is settled |
| Not decided yet | Every row stays and gets the note `Duplicate within file by your rule, group <label>, matched on First_Name, Last_Name, Zip; kept and marked` |

3. Label the groups F1, F2 and so on within each file, in the order of each group's first row. Skip groups decided as different people. Add three columns to Work and fill them from the Dupes sheet. Dup\_Label holds the label on every row of a labeled group, and it is what the output calls Duplicate\_In\_File. Dup\_Drop holds the set-aside problem on each copy. Dup\_Note holds the kept-and-marked note on every other row of the group, including the row kept from a group of copies, as the app does. Rows with a Dup\_Drop still go through P10, in the group Copies you confirmed.

`Dup_Line = IF([@Dup_Drop]<>"",[@Dup_Drop],[@Dup_Note])` gathers the row's line for the audit in P14.

### B. The same Client ID twice in the batch (automatic)

All files together. A total row takes no part. Build the person key the app uses. It is blank unless first name, last name, street and ZIP all have a value.

```
PKey = IF(OR([@First]="",[@Last]="",[@Address_1]="",[@Zip_5]=""),"",
  LOWER([@Last])&"|"&LOWER([@First])&"|"&NORMADDR([@Address_1])&"|"&
  NORMADDR([@Address_2])&"|"&[@Zip_5]&"|"&LOWER([@Program]))
ID_Key = IF(OR([@Summary],[@C_ID]=""),"",[@C_ID])
ID_Count = IF([@ID_Key]="",0,COUNTIFS(Work[ID_Key],[@ID_Key]))
ID_Same = IFERROR(AND([@PKey]<>"",COUNTIFS(Work[ID_Key],[@ID_Key],Work[PKey],[@PKey])=[@ID_Count]),FALSE)
ID_First = XMATCH([@ID_Key],Work[ID_Key])=ROW()-ROW(Work[#Headers])
ID_Msg = IF([@ID_Count]<2,"",IF([@ID_Same],
  IF([@ID_First],"","Confirmed duplicate: identical record with the same Client ID"),
  "Same Client ID '"&[@ID_Key]&"' used by records with different data; review required (not merged)"))
ID_Line = IF([@ID_Msg]<>"",[@ID_Msg],IF(AND([@ID_Count]>1,[@ID_Same],[@ID_First]),
  "Confirmed duplicate group of "&[@ID_Count]&" (identical record, same Client ID); keeping one",""))
```

The first row of an identical group stays and gets the note `Confirmed duplicate group of <n> (identical record, same Client ID); keeping one`. When the rows under one ID differ in any way, every one of them goes to review. The app compares IDs with exact capitals, and COUNTIFS ignores them. COUNTIFS also reads \* and ? as wildcards, and cannot compare text longer than 255 characters. Check any group whose IDs or keys hold those by eye.

`Dup_Msg = TEXTJOIN("; ",TRUE,[@Dup_Drop],[@ID_Msg])`, where Dup\_Drop holds the problem from part A.

### C. Possible duplicates across files (a flag, not a problem)

Rows that share a person key but come from different files. Rows set aside in part A and identical copies from part B take no part.

1. Keep rows with a person key, an empty Dup\_Drop, and no Confirmed duplicate problem.
2. Group them by person key. Keep groups with rows from two or more files.
3. Drop a group when every row in it has the same Client ID.
4. Number the rest Group 1, Group 2 and so on, in the order of each group's first row in Work. Write the label in Possible\_Duplicate.
5. Each row gets the note `Possible duplicate (Group <n>, <count> records with matching name/address/ZIP/program); not merged, confirm manually`.

```
T2_Line = IF([@Possible_Duplicate]="","","Possible duplicate ("&[@Possible_Duplicate]&", "&
  COUNTIFS(Work[Possible_Duplicate],[@Possible_Duplicate])&
  " records with matching name/address/ZIP/program); not merged, confirm manually")
```

These rows stay where they are. P11 decides whether they are one person.

## P9 Place each row on the map

Only rows with no problem so far are placed. The street is matched against the reference file inside the row's ZIP, a missing city or ZIP is filled from what it finds, and each point is moved a short random distance for privacy.

**If Geosupport Desktop is installed on this computer,** the app uses it first, offline. Run the rows through its batch tool instead of steps 1 to 3. It returns the ZIP, borough, coordinates and the three districts, the same answers the app gets.

1. **Load the reference file.** Load nyc\_address\_points.csv (or the city's full address points export) as text, the P1 way, and name the table Points. Its headers must read address, zip, city, latitude and longitude. Rename them if the export uses addr, zipcode, borough, lat or lon. The city column must spell the boroughs exactly as the Boroughs list does, because the app compares them letter for letter. Skip any line with no address, no ZIP, or coordinates that are not numbers. Add these columns.

```
P_Zip    = LEFT([@zip],5)
P_Norm   = NORMADDR([@address])
P_Key    = [@P_Zip]&"|"&[@P_Norm]
P_Street = LET(k,[@P_Norm], h,TEXTBEFORE(k&" "," "),
  IF(AND(ISNUMBER(SEARCH(" ",k)),REGEXTEST(SUBSTITUTE(h,"-",""),"^\d+$")),TEXTAFTER(k," "),k))
```

2. **Match the street.** An exact match of ZIP and normalized street wins. Otherwise the most similar street in the same ZIP wins if SIMILAR is 88 or more. The first in file order wins a tie. A ZIP missing from the file cannot be matched at all.

```
G_Try   = AND([@Problems]="",[@Dup_Msg]="")
G_Exact = IF([@G_Try],IFERROR(XMATCH([@Zip_5]&"|"&NORMADDR([@Address_1]),Points[P_Key]),""),"")
G_Fuzzy = IF(OR(NOT([@G_Try]),[@G_Exact]<>"",COUNTIFS(Points[P_Zip],[@Zip_5])=0),"",
  LET(t,NORMADDR([@Address_1]), f,Points[P_Zip]=[@Zip_5],
    rix,FILTER(SEQUENCE(ROWS(Points[P_Zip])),f), sc,MAP(FILTER(Points[P_Norm],f),LAMBDA(x,SIMILAR(t,x))),
    m,MAX(sc), IF(m>=88,INDEX(rix,XMATCH(m,sc))&"|"&m,"")))
G_Row    = IF([@G_Exact]<>"",[@G_Exact],IF([@G_Fuzzy]<>"",--TEXTBEFORE([@G_Fuzzy],"|"),""))
G_Status = IF(NOT([@G_Try]),"",IF([@G_Exact]<>"","exact",IF([@G_Fuzzy]<>"","fuzzy",
  IF(COUNTIFS(Points[P_Zip],[@Zip_5])=0,"No reference points in this ZIP","Address could not be matched locally"))))
G_City   = IF([@G_Row]="","",INDEX(Points[city],[@G_Row]))
```

3. **Settle the city and ZIP.**

| Case | Result |
| --- | --- |
| Matched, and the file's borough differs from the row's city, the city was not filled from the ZIP, and the row did not need a city | Problem `City/geocode mismatch: row says <city>, gazetteer says <borough>` |
| Matched, and the row needed a city | City becomes the file's borough. Note `Backfilled City '<borough>' from gazetteer`. If the file has no borough, the P6 city problem |
| The row needed a ZIP | The reference file gives no ZIP, so the P6 ZIP problem. Use the street lookup below first |
| Not matched, and the row needed a city or a ZIP | The P6 city problem, then the P6 ZIP problem |
| Not matched, nothing needed | No problem. Status stays Unverified. Only when the run requires a map match does G\_Status become the problem |

Put FALSE in a cell named RequireMap, the app's default. Set it to TRUE only if this run must place every row on the map.

```
Geo_Msg = LET(hit,[@G_Row]<>"", nc,[@Needs_City], nz,[@Needs_Zip],
  mis,IF(AND(hit,[@G_City]<>"",NOT(nc),[@City]<>"",NOT(EXACT([@G_City],[@City])),NOT([@From_ZIP])),
    "City/geocode mismatch: row says "&[@City]&", gazetteer says "&[@G_City],""),
  cf,IF(AND([@G_Try],nc,OR(NOT(hit),[@G_City]="")),[@City_Err],""),
  zf,IF(AND([@G_Try],nz),[@Zip_Err0],""),
  rq,IF(AND([@G_Try],NOT(hit),NOT(nc),NOT(nz),RequireMap),[@G_Status],""),
  TEXTJOIN("; ",TRUE,mis,cf,zf,rq))
City_Final = IF(AND([@Needs_City],[@G_Row]<>"",[@G_City]<>""),[@G_City],[@City])
Backfill_Note = IF([@City_Final]<>[@City],"Backfilled City '"&[@City_Final]&"' from gazetteer","")
```

4. **Move the point for privacy.** Every matched row. A random distance from 150 to 250 feet in a random direction, 364,000 feet to a degree of latitude.

```
J_Dist = IF([@G_Row]="","",150+100*RAND())
J_Dir  = IF([@G_Row]="","",2*PI()*RAND())
Latitude  = IF([@G_Row]="","",TEXT(INDEX(Points[latitude],[@G_Row])+[@J_Dist]*COS([@J_Dir])/364000,"0.000000"))
Longitude = IF([@G_Row]="","",TEXT(INDEX(Points[longitude],[@G_Row])+[@J_Dist]*SIN([@J_Dir])/
  (364000*COS(RADIANS(INDEX(Points[latitude],[@G_Row])))),"0.000000"))
Geo_Line  = IF([@G_Row]="","","Geocoded via gazetteer ("&IF([@G_Status]="exact","exact match",
  "fuzzy match "&TEXTAFTER([@G_Fuzzy],"|")&"%")&"; jittered "&ROUND([@J_Dist],0)&" ft; confidence "&
  IF([@G_Status]="exact","High","Low")&")")
```

Copy J\_Dist, J\_Dir, Latitude and Longitude and paste them as values straight away, or RAND changes them on every recalculation. The app uses a fixed starting number, so its own reruns repeat. Excel cannot reproduce its random numbers, so your points will differ from the app's by up to 500 feet. The rule is the same. Audit note `Geocoded via gazetteer (exact match; jittered <feet> ft; confidence High)`, or `(fuzzy match <score>%; jittered <feet> ft; confidence Low)`.

5. **Districts.** Senate, Assembly and Council districts come from the true point, not the moved one. Geosupport returns them. Excel cannot test a point against district boundaries, so without Geosupport leave the three columns empty and write the note `Districts unresolved (no boundary file loaded)`. That is what the app writes when it has no boundary file. Fill them the next time the app runs.
6. **Confidence and status.**

| Row | Geocode\_Confidence | Verification\_Status |
| --- | --- | --- |
| A problem found before P9 | empty | Needs Review |
| Exact match | High | Verified |
| Similar match | Low | Verified (low confidence) |
| No match, no problem | empty | Unverified |

### Fill a missing ZIP or city from the street

The app offers this for the ZIP review groups and as a calculated ZIP column. It proposes a value only when there is exactly one answer, and a person approves it. Type approved values into Fix\_Zip and Fix\_City, and change C\_Zip and C\_City to use them first, for example `C_Zip = IF([@Fix_Zip]<>"",[@Fix_Zip],CLEANORDEF([@In_Zip],[@File],"Zip"))`. Every check then runs again on that row.

```
W_SName = LET(k,NORMADDR([@Address_1]), h,TEXTBEFORE(k&" "," "),
  IF(AND(ISNUMBER(SEARCH(" ",k)),REGEXTEST(SUBSTITUTE(h,"-",""),"^\d+$")),TEXTAFTER(k," "),k))
Zip_Found = LET(z,UNIQUE(FILTER(Points[P_Zip],(Points[P_Street]=[@W_SName])*(Points[city]=[@City]),"")),
  IF(AND(ROWS(z)=1,INDEX(z,1)<>""),INDEX(z,1),""))
```

| Situation | Proposed | Reason shown, exactly |
| --- | --- | --- |
| Borough known, one ZIP | That ZIP | `<street> in <borough> is only in ZIP <zip>` |
| Borough known, no ZIP | Nothing | `the street is not in the reference data for <borough>` |
| Borough known, several ZIPs | Nothing | `<street> runs through <n> ZIPs in <borough> (<first four>); a house number is needed` |
| No borough, street in one borough with one ZIP | That ZIP, and the city from it | `<street> is only in <borough>, ZIP <zip>` |
| No borough, street in one borough with several ZIPs | Nothing | `<street> is only in <borough> but runs through <n> ZIPs; a house number is needed` |
| No borough, street in several boroughs | Nothing | `<street> exists in <n> boroughs (<list>); a city is needed` |
| Street not in the file | Nothing | `the street is not in the reference data` |

For an unrecognized city the app first proposes the borough of a New York ZIP (`ZIP <zip> is in <borough>`), then the one borough whose streets include this one (`<street> is only in <borough>`).

## P10 Review the problems

Every row with a problem sits in exactly one group, named for its cause. Decide whole groups first, then work what is left row by row. Values are never edited by hand here. A fill goes in Fix\_Zip or Fix\_City, and anything else is fixed at the source and loaded again.

**Put each row in its group.** Read Error\_Reason in lower case and take the first test that matches.

```
Group = LET(e,LOWER([@Error_Reason]), has,LAMBDA(x,ISNUMBER(SEARCH(x,e))),
  zb,OR(has("invalid zip"),has("missing zip"),AND(has("zip"),has("missing"))),
  cb,OR(has("could not be determined"),has("unrecognized city")),
  IF(e="","",
  IF(has("summary row, not a client record"),"summary",
  IF(has("city/zip conflict"),"conflict",
  IF(has("duplicate within file by your rule"),"duprule",
  IF(has("confirmed duplicate"),"dupc",
  IF(has("same client id"),"idconflict",
  IF(OR(has("missing address_1"),AND(has("address"),has("missing"))),"noaddr",
  IF(zb,IF(cb,"zipcity","zipbad"),
  IF(cb,"cityunknown",
  IF(has("missing"),"missing",
  IF(OR(has("could not be matched"),has("geocod"),has("geosupport")),"geo","other"))))))))))))
```

**The groups, in the order the app shows them.**

| Group | Title in the app | Default decision | Other decision |
| --- | --- | --- | --- |
| summary | Not client records: totals, counts and headings | Set aside, exclude | Hold for review |
| conflict | City conflicts with its ZIP | Send all to review | Apply ZIP city to all |
| zipcity | No usable ZIP code, and no city either | Send all to review | Hold for review |
| zipbad | No usable ZIP code | Send all to review | Hold for review |
| cityunknown | City is not recognized, and the ZIP did not explain it | Send all to review | Hold for review |
| noaddr | No usable address | Hold for review | Set aside, exclude |
| missing | A required field is blank | Send all to review | Hold for review |
| idconflict | One identifier used for records that do not match | Send all to review | Hold for review |
| duprule | Copies you confirmed | Set aside, keep the first | Keep them all, flag only |
| dupc | Confirmed duplicates, identical rows with one ID | Keep one of each | Send all to review |
| geo | Address could not be matched | Send all to review | Hold for review |
| other | Other validation problems | Send all to review | Hold for review |

Every group also offers Accept all as they are.

**Before deciding, look for one cause.** When 90% or more of a group's rows from one file have the same field empty, the problem is the column match in P2, not the rows. Fix the match and rerun. The app points this out the same way.

**What each decision does.**

| Decision | Status of every row in the group | Note on each row |
| --- | --- | --- |
| Set aside, exclude. Set aside, keep the first. Keep one of each | Set aside | none |
| Send all to review | Pending, for the row-by-row pass | none |
| Hold for review | Held | none |
| Accept all as they are. Keep them all, flag only | Approved as entered by reviewer | `Accepted as entered by the reviewer, as part of the group '<title>'` |
| Apply ZIP city to all | Fix\_City gets the ZIP's borough and the row is checked again. A row that now passes becomes Passed every check. One that still fails becomes Pending | The P6 notes for the new city |

The rows the Set aside decisions cover in duprule and dupc are the copies only. The first row of each group was never in review.

**Row by row.** For each Pending row, look at what is wrong and the original row, then take one action.

| Action | Result |
| --- | --- |
| Fill in what can be worked out | The ZIP or city from P9's lookup, typed in Fix\_Zip or Fix\_City. The row is checked again |
| Keep this one, from a group of copies | This row becomes Approved as entered by reviewer. The others in its group become Set aside |
| Accept as it stands | Approved as entered by reviewer |
| Reject | Rejected. It stays in review until fixed at the source |
| Set aside | Set aside |

**Record every decision.** One line per group decision on the Decisions sheet with the date, the group, the decision, the number of rows and who decided. One line per row decision with the File, Row and Client ID. The same lines go to Audit.

## P11 Same person across files

Goal 1 counts people, not rows, so the records one person has in different systems must be joined. Records are joined without asking only where coincidence is not a reasonable explanation. Everything weaker is a pair a person decides. Nothing is joined on the name alone.

**Which records.** Only rows whose Status is Passed every check or Approved as entered by reviewer. Copy their File, Row, C\_ID, First, Last, Address\_1, Zip\_5, Program and DOB (an empty DOB column when no file has one) as values to a new sheet, press Ctrl+T and name the table Id. Add these columns, and a Master\_ID column filled at the end of this procedure.

```
Rid    = [@File]&"||"&[@Row]
System = TEXTBEFORE([@File]&" :: "," :: ")
GKey   = TEXTBEFORE(FOLD([@First])&" "," ")
Groups = TEXTJOIN(",",TRUE,FILTER(Nicknames[Group],Nicknames[Name]=[@GKey],""))
Parts  = SPARTS([@Last])
AKey   = AKEY([@Address_1],[@Zip_5])
DobKey = IF(OR([@DOB]="",[@DOB]="#BAD"),"",SUBSTITUTE([@DOB],"-",""))
```

FOLD lowers the text, removes accents, turns hyphens into spaces, drops apostrophes and turns other punctuation into spaces. SPARTS keeps the surname's words, leaving out Jr, Sr, II, III, IV and V, then particles such as de, la, van and one-letter words unless nothing would be left. AKEY is the folded street with the street-type words taken out, then the ZIP. It is empty unless both exist.

**Which pairs to compare.** Two records are compared only when they share one of these keys. A key shared by more than 150 records is ignored, because it proves nothing.

| Key | Built from |
| --- | --- |
| Date of birth | DobKey |
| Address | AKey |
| Surname and birth year | each word of Parts, and the year |
| Surname and birth month and day | each word of Parts, and MMDD |
| Surname and address | each word of Parts, and AKey |
| Surname and ZIP | each word of Parts, and the ZIP |
| Given name and birth year | GKey or each nickname group, and the year |
| Given name and address | GKey or each nickname group, and AKey |
| The same two, with each word of Parts used as a given name | catches first and last typed in the wrong columns |

For each key, add a column, count it with COUNTIFS, keep the counts from 2 to 150, sort by the key, and write every pair inside each group on the Pairs sheet with its two Rids. A group of three gives three pairs. Write each pair once.

**Score each pair.**

| Evidence | Points |
| --- | --- |
| Same file and the same Client ID | 100. Nothing else is scored |
| Date of birth identical | +42 |
| Date of birth near. Same year with day and month swapped, one digit different, or two side-by-side digits swapped | +26 |
| Dates of birth both present and different | minus 20 |
| Surname words all the same | +30 |
| Some surname words shared, such as one half of a double surname | +24 |
| Given name's first word the same | +26 |
| Given names in one nickname group, such as Bob and Robert | +22 |
| One given name is a single letter and the first letters agree | +8 |
| A given name appears among the other record's surname words, and no surname word is shared | +20 |
| AKey the same | +30 |
| Otherwise the same ZIP | +6 |

Of the three given-name lines, only the first that applies counts. The opposite-columns line is separate and can add to them.

Make the Pairs sheet a table named Pairs with RidA and RidB. Pull each fact for both records with XLOOKUP, then score.

```
DobA    = XLOOKUP([@RidA],Id[Rid],Id[DobKey])&""
DobB    = XLOOKUP([@RidB],Id[Rid],Id[DobKey])&""
PartsA  = XLOOKUP([@RidA],Id[Rid],Id[Parts])&""
PartsB  = XLOOKUP([@RidB],Id[Rid],Id[Parts])&""
GKeyA   = XLOOKUP([@RidA],Id[Rid],Id[GKey])&""
GKeyB   = XLOOKUP([@RidB],Id[Rid],Id[GKey])&""
GroupsA = XLOOKUP([@RidA],Id[Rid],Id[Groups])&""
GroupsB = XLOOKUP([@RidB],Id[Rid],Id[Groups])&""
AKeyA   = XLOOKUP([@RidA],Id[Rid],Id[AKey])&""
AKeyB   = XLOOKUP([@RidB],Id[Rid],Id[AKey])&""
ZipA    = XLOOKUP([@RidA],Id[Rid],Id[Zip_5])&""
ZipB    = XLOOKUP([@RidB],Id[Rid],Id[Zip_5])&""
SystemA = XLOOKUP([@RidA],Id[Rid],Id[System])&""
SystemB = XLOOKUP([@RidB],Id[Rid],Id[System])&""
IDA     = XLOOKUP([@RidA],Id[Rid],Id[C_ID])&""
IDB     = XLOOKUP([@RidB],Id[Rid],Id[C_ID])&""
```

The &"" turns an empty cell into empty text. Without it XLOOKUP returns 0, and two blank IDs would look like the same ID.

```
DOB_Pts   = IF(OR([@DobA]="",[@DobB]=""),0,IF([@DobA]=[@DobB],42,IF(DOBNEAR([@DobA],[@DobB]),26,-20)))
Last_Pts  = IF(OR([@PartsA]="",[@PartsB]=""),0,
  IF(SAMESET([@PartsA],[@PartsB]),30,IF(ANYSHARED([@PartsA],[@PartsB]),24,0)))
Given_Pts = IF(OR([@GKeyA]="",[@GKeyB]=""),0,IF([@GKeyA]=[@GKeyB],26,
  IF(ANYSHARED([@GroupsA],[@GroupsB],","),22,
  IF(AND(OR(LEN([@GKeyA])=1,LEN([@GKeyB])=1),LEFT([@GKeyA])=LEFT([@GKeyB])),8,0))))
Swap_Pts  = IF(AND(NOT(ANYSHARED([@PartsA],[@PartsB])),
  OR(ANYSHARED([@GKeyA],[@PartsB]),ANYSHARED([@GKeyB],[@PartsA]))),20,0)
Addr_Pts  = IF(AND([@AKeyA]<>"",[@AKeyA]=[@AKeyB]),30,IF(AND([@ZipA]<>"",[@ZipA]=[@ZipB]),6,0))
SameID    = AND([@SystemA]=[@SystemB],[@IDA]<>"",EXACT([@IDA],[@IDB]))
Points    = IF([@SameID],100,[@DOB_Pts]+[@Last_Pts]+[@Given_Pts]+[@Swap_Pts]+[@Addr_Pts])
Auto      = OR([@SameID],AND([@DOB_Pts]=42,[@Last_Pts]=30,[@Given_Pts]=26,[@Addr_Pts]=30))
```

**What the points mean.**

| Points | Outcome |
| --- | --- |
| Auto is TRUE | Joined without asking. Only the same ID in one system, or date of birth, surname, given name and address all identical |
| 62 or more, Auto FALSE | A proposed pair. A person marks it Same or Different in the Decision column |
| Under 62 | Not a pair |

A nickname alone never joins two records. Without a date of birth the most two records can score without the same ID is 30 + 26 + 30 = 86, so they are always a proposal. Add a date of birth field in P2 when any file has one.

**Give each person a Master\_ID.** Join every Auto pair and every pair marked Same. Records joined through a chain are one person. If A joins B and B joins C, all three are one. Label each person with the smallest Rid among its records, and repeat until no record carries two labels. Sort the people by that Rid as text and number them M000001, M000002 and so on. A record in no pair is a person on its own.

**Audit lines.** One per pair decided, `Pair <Rid A> and <Rid B>: same person` or `different people`, with who decided.

## P12 Count Goal 1 and Goal 2

Both counts come from the Id sheet, so they include only rows that passed or that a person approved. A row still in review, or set aside, is never counted.

| Count | What it is | Formula on the Counts sheet |
| --- | --- | --- |
| Goal 1, unique clients | The number of different Master\_IDs | `=ROWS(UNIQUE(Id[Master_ID]))` |
| Goal 2, unique clients per program | The number of different Master\_ID and Program pairs. A person in three programs counts three times | `=IFERROR(ROWS(UNIQUE(FILTER(Id[Master_ID]&"\|"&Id[Program],Id[Program]<>""))),0)` |
| One program's count | The people in that program | `=ROWS(UNIQUE(FILTER(Id[Master_ID],Id[Program]=A2)))` |
| Records with no program | Counted in Goal 1, left out of Goal 2 | `=COUNTIFS(Id[Program],"")` |

**Goal 1 is a range until every pair is decided.** The count above treats every open pair as two people, which is the high end. For the low end, join the open pairs as well in a second column, Master\_ID\_IfAll, and count that the same way. Report "between low and high, with n pairs open". When no pair is open, the two are equal and the count is final.

List the programs down column A with `=SORT(UNIQUE(FILTER(Id[Program],Id[Program]<>"")))` and fill the per-program formula beside them. The per-program counts add up to Goal 2 exactly, because each person and program pair counts once, in its own program.

## P13 Write the output files and prove nothing was lost

Write the same seven files the app writes, with the same names and columns, so anyone downstream cannot tell which way they were made. Save each as CSV, or as Excel with one sheet named Data.

| File | Rows, in this order | Columns, in this order |
| --- | --- | --- |
| Final\_Clean\_Mapped | Passed every check, then Approved as entered by reviewer | First\_Name, Middle\_Initial, Last\_Name, Client\_ID, Address\_1, Address\_2, City, State, Zip, Program, any added fields, Latitude, Longitude, Verification\_Status, Geocode\_Confidence, Possible\_Duplicate, Duplicate\_In\_File, Senate\_District, Assembly\_District, Council\_District, Source\_File, Source\_Row, Resolution\_Status |
| Manual\_Review\_Needed | Pending, Held and Rejected rows, then Set aside rows | Source\_File, Source\_Row, Resolution\_Status, Error\_Reason, Scenario\_Flags, then orig:: and each column name of the source table |
| Set\_Aside\_Records | Set aside rows | Set\_Aside\_Reason, Source\_File, Source\_Row, First\_Name, Middle\_Initial, Last\_Name, Client\_ID, Address\_1, Address\_2, City, State, Zip, Program, any added fields |
| Unique\_Clients | One row per Master\_ID, in Master\_ID order | Master\_ID, First\_Name, Last\_Name, Address\_1, Zip, Programs, Program\_Count, Systems, Source\_Record\_Count, Source\_Client\_IDs, Source\_Rows |
| Unique\_Clients\_By\_Program | One row per Master\_ID and Program, in that order | Master\_ID, Program, First\_Name, Last\_Name, Address\_1, Zip, Systems, Source\_Client\_IDs, Source\_Record\_Count |
| Secure\_Audit\_Log.txt | See P14 |  |
| Data\_Quality\_Report | One row per table | Source\_File, Total\_Rows, Clean\_Rows, Review\_Rows, Clean\_Rate, Top\_Issue, Carries\_PII |

**Where each value comes from.**

| Output column | Work column |
| --- | --- |
| First\_Name, Middle\_Initial, Last\_Name | First, Middle, Last |
| Client\_ID | C\_ID |
| Address\_1, Address\_2 | Address\_1, Address\_2 |
| City | City\_Final |
| State, Zip | State, Zip\_5 |
| Program | Program, the agreed name |
| Latitude, Longitude | Latitude, Longitude from P9 |
| Verification\_Status | `=IF([@Error_Reason]<>"","Needs Review",IF([@G_Status]="exact","Verified",IF([@G_Status]="fuzzy","Verified (low confidence)","Unverified")))` |
| Geocode\_Confidence | `=IF([@G_Status]="exact","High",IF([@G_Status]="fuzzy","Low",""))` |
| Possible\_Duplicate | Possible\_Duplicate from P8 |
| Duplicate\_In\_File | Dup\_Label from P8 |
| Senate\_District, Assembly\_District, Council\_District | From Geosupport, or empty |
| Source\_File, Source\_Row | File, Row |
| Resolution\_Status | Status |
| Set\_Aside\_Reason | Error\_Reason, or `set aside by a decision` when it is empty |
| Source\_File in Set\_Aside\_Records | The file name only, the part of File before " :: " |
| orig:: columns | The source row's own values after the P3 clean, one column per source column. A table without that column leaves it empty |

**Scenario\_Flags** lists the scenario of every note and problem on the row, each once, sorted as text and joined by a semicolon and a space. A total row has only 0 Not a record. The scenario of each message is in the P7 table and in the Audit\_Lines formula in P14.

```
Scenario_Flags = IF([@Summary],"0 Not a record",LET(s,VSTACK(
  IF([@Addr_Note]&[@Unit_Note]&[@Unit_Msg]<>"","1 Address parsing",""),
  IF(OR(ISNUMBER(SEARCH("neighborhood",[@City_Note])),[@ZipCity_Note]<>"",[@Backfill_Note]<>""),"2 Geographic naming",""),
  IF(OR(AND([@City_Note]<>"",NOT(ISNUMBER(SEARCH("neighborhood",[@City_Note])))),
    [@State_Note]&[@Zip_Note]&[@MI_Note]&[@Def_Note]&[@Prog_Note]&[@Type_Note]<>""),"2 Standardization",""),
  IF(REGEXTEST([@Error_Reason],"Missing|not NY|place name|City/ZIP|City could|Unrecognized|Invalid ZIP|exceeds|must be|not a date|geocode mismatch"),"3 Verification",""),
  IF([@Dup_Label]<>"","4 Deduplication",""),
  IF(ISNUMBER(SEARCH("digits",[@Error_Reason])),"7 ETL artifact",""),
  IF(OR([@ID_Count]>1,[@Possible_Duplicate]<>""),"9 Duplicate",""),
  IF(REGEXTEST([@Geo_Msg],"matched locally|No reference points"),"12 Geolocation","")),
  TEXTJOIN("; ",TRUE,SORT(UNIQUE(FILTER(s,s<>"",""))))))
```

**Unique\_Clients details.** Name, street and ZIP come from the person's first record in Id order. Programs, Systems and Source\_Client\_IDs are the different non-empty values, sorted and joined by a semicolon and a space. Program\_Count is the number of different programs. Source\_Rows lists every Rid. Unique\_Clients\_By\_Program does the same for each person and program.

**Prove nothing was lost.** These must all be true before you send anything.

| Check | Formula |
| --- | --- |
| Every loaded row is in Work | `=ROWS(Work[File])` equals the total rows of every included Src table |
| Every row has one status | `=COUNTIFS(Work[Status],"")` is 0 |
| Clean plus review plus set aside equals rows loaded | `=ROWS(Work[File])=COUNTIFS(Work[Status],"Passed every check")+COUNTIFS(Work[Status],"Approved as entered by reviewer")+COUNTIFS(Work[Status],"Pending")+COUNTIFS(Work[Status],"Held")+COUNTIFS(Work[Status],"Rejected")+COUNTIFS(Work[Status],"Set aside")` |
| Output files match | Rows in Final\_Clean\_Mapped plus rows in Manual\_Review\_Needed equals ROWS(Work\[File\]) |

Write the balance line on the Counts sheet the way the app shows it, `<input> rows in = <clean> clean + <review> in review + <aside> set aside`.

## P14 Keep the audit log and the quality report, and save for next time

The audit log lets anyone trace a number back to the rows and decisions behind it. It holds table names, row numbers, Client IDs and column names, never a client's name or street, so it can be shared.

**Secure\_Audit\_Log.txt starts with these lines.**

```
SECURE AUDIT LOG
Generated (UTC): <date and time>
Fuzzy backend: done by hand in Excel
This log references system IDs only. No client names or full street addresses are included.
==============================================================================
```

**Then one line per change, in row order.** Each line reads `[<table> | ID <Client_ID, or <no-id>> | src-row <Row>] [<scenario> | <action>] <message>`. The action is fixed when a value was changed, annotated when the row was only marked, and segregated when it is a problem. This column writes every line for a row in the app's order.

```
Audit_Lines = IF([@Summary],
  "["&[@File]&" | ID "&IF([@C_ID]="","<no-id>",[@C_ID])&" | src-row "&[@Row]&"] [0 Not a record | segregated] "&[@Problems],
  LET(h,"["&[@File]&" | ID "&IF([@C_ID]="","<no-id>",[@C_ID])&" | src-row "&[@Row]&"] ",
  L,LAMBDA(s,a,m,IF(m="","",h&"["&s&" | "&a&"] "&m)),
  TEXTJOIN(CHAR(10),TRUE,
    L("1 Address parsing","fixed",IF(OR([@A_City]<>"",[@A_Zip]<>""),"Split jammed address into street + city/ZIP","")),
    L("1 Address parsing","annotated",IF(ISNUMBER(SEARCH(",",[@A_Street])),"Address_1 still contains a comma; possible concatenated fragments","")),
    L("1 Address parsing","fixed",[@Unit_Note]),
    L("1 Address parsing","segregated",[@Unit_Msg]),
    L(IF(ISNUMBER(SEARCH("neighborhood",[@City_Note])),"2 Geographic naming","2 Standardization"),"fixed",[@City_Note]),
    L("3 Verification","segregated",[@Place_Msg]),
    L("2 Standardization","fixed",[@State_Note]),
    L("3 Verification","segregated",[@State_Err]),
    L("2 Standardization","fixed",[@Zip_Note]),
    L("3 Verification","segregated",IF([@First]="","Missing First_Name","")),
    L("3 Verification","segregated",IF([@Last]="","Missing Last_Name","")),
    L("7 ETL artifact","segregated",IF(REGEXTEST([@First]&[@Last],"\d"),"Name field contains digits; possible column misalignment","")),
    L("2 Standardization","fixed",[@MI_Note]),
    L("3 Verification","segregated",IF([@C_ID]="","Missing Client_ID","")),
    L("3 Verification","segregated",IF([@Address_1]="","Missing Address_1","")),
    L("2 Geographic naming","fixed",[@ZipCity_Note]),
    L("3 Verification","segregated",[@Conflict_Msg]),
    L("3 Verification","segregated",[@City_Msg]),
    L("3 Verification","segregated",[@Zip_Msg]),
    L("3 Verification","segregated",[@Len_Msg]),
    L("2 Standardization","fixed",[@Def_Note]),
    L("3 Verification","segregated",[@Added_Msg]),
    L("2 Standardization","fixed",[@Type_Note]),
    L("2 Standardization","fixed",[@Prog_Note]),
    L("4 Deduplication",IF([@Dup_Drop]="","annotated","segregated"),[@Dup_Line]),
    L("9 Duplicate",IF([@ID_Msg]="","annotated","segregated"),[@ID_Line]),
    L("9 Duplicate","annotated",[@T2_Line]),
    L("12 Geolocation","fixed",[@Geo_Line]),
    L("2 Geographic naming","fixed",[@Backfill_Note]),
    L("3 Verification","segregated",[@Geo_Msg]),
    L("6 District mapping","annotated",IF(AND([@G_Row]<>"",[@Error_Reason]=""),"Districts unresolved (no boundary file loaded)","")))))
```

Dup\_Line, ID\_Line and T2\_Line come from P8. Geo\_Line and Backfill\_Note come from P9. Copy the Audit\_Lines column, paste it into a text editor, and add these lines at the end.

- Two per table. `[<table> | ID <file> | src-row -1] [13 PII | annotated] File classified: PII (names present)`, or `de-identified` when neither name field was matched. Then `[<table> | ID <file> | src-row -1] [5 Quality | annotated] <clean>/<total> clean (<rate>%); top issue: <issue>`.
- The set-up. Tables loaded and skipped, each column match, each default and each program grouping, from P1, P2 and P5.
- Every decision, with who and when. Review groups and rows from P10, duplicate groups from P8, pairs from P11.

**Data\_Quality\_Report.** One row per table, counted straight after P9 and before any review decision.

| Column | Value |
| --- | --- |
| Source\_File | The table name |
| Total\_Rows | Rows in the table |
| Clean\_Rows | Rows with an empty Error\_Reason |
| Review\_Rows | Total\_Rows minus Clean\_Rows |
| Clean\_Rate | Clean\_Rows over Total\_Rows, one decimal and a % sign, such as 93.4% |
| Top\_Issue | The most common problem, read up to its first colon. Invalid ZIP Code format, Missing First\_Name, City/ZIP conflict. A problem with no colon counts whole. On a tie, the one that appeared first. none when the table has no problem |
| Carries\_PII | True when First\_Name or Last\_Name is matched to a column, otherwise False |

Count Top\_Issue with a PivotTable over the problem columns of that table, one problem per row.

**Save for next time.** Save the workbook as Crosswalk\_by\_hand\_\<yyyy-mm-dd>.xlsx and keep it with the batch. Then save a second copy as the set-up for next quarter. In that copy clear Src, Work, Id, Pairs, Dupes, Decisions, Counts and Audit, and keep Ref, Defaults, ProgramMap and Points. The set-up holds no client data. When the app is back, load the same exports into it and compare its two counts with yours. They should match. Coordinates will not, because of the random privacy offset.
