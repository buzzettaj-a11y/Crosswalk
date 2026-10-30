# Reference

Set these up once on the Ref sheet and keep them for every batch. Every formula in the procedures calls them by name, and every list here is copied from the app's own code.

## Setting up names

Three kinds of thing live on the Ref sheet. Set them up in this order, because the formulas refer to the patterns and the tables.

1. **A lookup table.** Copy a list from the Lookup tables section. On Ref, paste it into A1 of an empty area, then Data > Text to Columns > Delimited > Comma if it pasted into one column. Select it with its header and press Ctrl+T. Name the table in Table Design > Table Name, exactly as written, for example CityAliases.
2. **A named pattern.** Type the pattern into one cell on Ref with an apostrophe in front, so Excel keeps it as text. Click the cell, type the name in the Name Box left of the formula bar, for example UnitTail, and press Enter.
3. **A named formula.** Formulas > Name Manager > New. Type the name, for example CLEANCELL. Paste the whole formula, starting with =LAMBDA, into Refers to. Press OK.

Test each formula once on a scratch cell before the batch. `=CLEANCELL("  N/A ")` should show an empty cell, `=BORO("11211")` should show Brooklyn, and `=SIMILAR("Brookln","Brooklyn")` should show 93.

## Named patterns

Eleven patterns, each in its own cell on Ref with the name shown. A name inside LET or LAMBDA in any formula here never looks like a cell address, such as c1 or a2, and is never r or c on its own, because Excel refuses those. They are the app's own patterns, unchanged except for one capture group each where Excel needs it.

**SepRun.** A dash, comma, semicolon, colon, pipe, slash or backslash with spaces around it. P4.

```
\s+[\-,;:|/\\]{1,3}\s+
```

**CommaRun.** Two or more commas in a row. P4.

```
\s*,\s*(?:,\s*)+
```

**Country.** USA and its forms at the end, as a word. P4.

```
(?i)(?:^|[\s,]+)(?:usa|u\.s\.a\.|us|united states)\s*$
```

**ZipTail.** A ZIP or ZIP+4 at the end. P4.

```
(\d{5})(?:-\d{4})?\s*$
```

**StateTail.** New York as a state at the end. P4.

```
(?i)(?:^|[\s,])(?:N\.?\s?Y\.?|New\s+York(?:\s+State)?)\s*$
```

**UnitTail.** A unit at the end of a street. P4.

```
(?i)\s+(#\s*:?\s*(?:[0-9]{1,5}(?:[\s\-]{0,2}[A-Za-z]{1,2})?|[A-Za-z]{1,2}[\s\-]{0,2}[0-9]{1,5}|[0-9A-Za-z\-]*[0-9][0-9A-Za-z\-]*|[A-Za-z]{1,2})|(?:apt|apartment|suite|ste|unit|fl|floor|rm|room|bldg|building|dept|department|space|spc|lot|trailer|hangar|slip|pier|stop)\.?\s*#?\s*:?\s*(?:[0-9]{1,5}(?:[\s\-]{0,2}[A-Za-z]{1,2})?|[A-Za-z]{1,2}[\s\-]{0,2}[0-9]{1,5}|[0-9A-Za-z\-]*[0-9][0-9A-Za-z\-]*)|[0-9]+(?:st|nd|rd|th)?\s+(?:floor|fl)\b|penthouse|basement|bsmt|lobby|mezzanine)\s*$
```

**BareUnit.** A bare designator such as 14A straight after a street type. P4.

```
(?i)\b(?:st|street|ave|avenue|rd|road|blvd|boulevard|pl|place|dr|drive|ct|court|ln|lane|way|pkwy|parkway|ter|terrace|expy|expressway|hwy|highway|sq|square|cir|circle|plz|plaza)\.?\s+(\d{1,4}[A-Za-z])\s*$
```

**UnitLikePat.** A comma piece that reads as a unit. Applied to lower-case text. UNITLIKE. Excel names ignore capitals, so this pattern cannot be called UnitLike.

```
^(?:(?:apt|apartment|ste|suite|unit|fl|floor|rm|room|bldg|building|ph|penthouse|bsmt|basement|lobby|mezzanine|rear|front|no|num)\b|#|\d{1,3}(?:st|nd|rd|th)\s+(?:apt|apartment|ste|suite|unit|fl|floor|rm|room|bldg|building|ph|penthouse|bsmt|basement|lobby|mezzanine|rear|front|no|num)\b|(?:[0-9]{1,4}[a-z]?|[a-z][0-9]{1,4}|[0-9]{1,4}-?[a-z])$)
```

**UnitWords.** The unit labels dropped when two units are compared. UNITKEY.

```
apt|apartment|ste|suite|unit|fl|floor|rm|room|bldg|building|ph|penthouse|bsmt|basement|lobby|mezzanine|rear|front|no|num
```

**Suffix.** Jr, Sr, II, III or IV at the end of a name. P4.

```
(?i)[,\s]+(Jr|Sr|II|III|IV|Jr\.|Sr\.)\s*$
```

**SummaryWords.** A cell that starts with a total word. P3.

```
(?i)^\s*(grand\s+)?(total|subtotal|sub-total|sum|count|average|avg|mean|summary|overall|all\s+(clients|records|programs)|n\s*=)\b
```

## Named formulas

Twenty-two formulas, each added once in Name Manager. Paste each whole block into Refers to. Set up the patterns and tables first, because these formulas use them.

| Name | Does | Used in |
| --- | --- | --- |
| CLEANCELL | The P3 clean rule | Everywhere |
| DEF | The Defaults value for a file and field | CLEANORDEF |
| CLEANORDEF | Clean, or the default when empty | P3 |
| TIDY | Tidy a split part | P4 |
| UNITLIKE | Does a piece read as a unit | P4, P6 |
| UNITKEY | A unit without its label, to compare two units | P6 |
| SPLITUNIT | Peel a unit off the end of a street. Returns street and unit | P4 |
| CITYWORD | Is it a borough or neighborhood name | P4 |
| MIDINIT | A middle initial | P4, P6 |
| NORMADDR | The app's street form for matching | P8, P9 |
| BORO | The borough of a New York ZIP | P6 |
| SIMILAR | Similarity from 0 to 100 | P5, P6, P9 |
| LENCHK | The max length problem | P7 |
| NORMF, NORMZ | Name and ZIP forms for copies in one file | P8 |
| DATEFIX | A date in the form 2024-03-15, or #BAD | P6 |
| FOLD | Lower case with accents and punctuation removed | P11 |
| SPARTS | The words of a surname that tell people apart | P11 |
| AKEY | Street and ZIP key for matching people | P11 |
| DOBNEAR | Two birth dates one slip apart | P11 |
| SAMESET, ANYSHARED | Compare two word lists | P11 |

**CLEANCELL**

```
=LAMBDA(v,LET(t,TRIM(SUBSTITUTE(SUBSTITUTE(SUBSTITUTE(SUBSTITUTE(IFERROR(v&"",""),CHAR(9)," "),CHAR(13)," "),CHAR(10)," "),UNICHAR(160)," ")),IF(ISNUMBER(XMATCH(LOWER(t),Placeholders[Value])),"",t)))
```

**DEF**

```
=LAMBDA(f,fld,LET(a,XLOOKUP(1,(Defaults[File]=f)*(Defaults[Field]=fld),Defaults[Value],"")&"",IF(a<>"",a,XLOOKUP(1,(Defaults[File]="(all)")*(Defaults[Field]=fld),Defaults[Value],"")&"")))
```

**CLEANORDEF**

```
=LAMBDA(v,f,fld,LET(t,CLEANCELL(v),IF(t<>"",t,CLEANCELL(DEF(f,fld)))))
```

**TIDY**

```
=LAMBDA(s,LET(a,TRIM(s),b,REGEXREPLACE(a,"(\s*)([\-,;:|/\\])(?:\s*[\-,;:|/\\])+(\s*)","$1$2$3"),cc,REGEXREPLACE(b,"\s+([,;:])","$1"),TRIM(REGEXREPLACE(cc,"^[\s\-,;:|/\\]+|[\s\-,;:|/\\]+$",""))))
```

**UNITLIKE**

```
=LAMBDA(s,LET(v,LOWER(TRIM(s)),AND(v<>"",REGEXTEST(v,UnitLikePat))))
```

**UNITKEY**

```
=LAMBDA(s,REGEXREPLACE(REGEXREPLACE(REGEXREPLACE(LOWER(TRIM(s)),"^(?:"&UnitWords&")\b\.?\s*",""),"^#+",""),"[^a-z0-9]",""))
```

**SPLITUNIT**

```
=LAMBDA(s,LET(t,CLEANCELL(s),IF(REGEXTEST(t,UnitTail),LET(p,REGEXREPLACE(REGEXREPLACE(t,UnitTail,""),"\s*,*\s*$",""),IF(p="",HSTACK(t,""),HSTACK(p,CLEANCELL(INDEX(REGEXEXTRACT(t,UnitTail,2),1))))),LET(b,IFERROR(INDEX(REGEXEXTRACT(t,BareUnit,2),1),""),IF(b="",HSTACK(t,""),HSTACK(REGEXREPLACE(REGEXREPLACE(t,"\s*\d{1,4}[A-Za-z]\s*$",""),"\s*,*\s*$",""),b))))))
```

**CITYWORD**

```
=LAMBDA(t,AND(t<>"",OR(ISNUMBER(XMATCH(t,Boroughs)),ISNUMBER(XMATCH(t,Hoods[Key])))))
```

**MIDINIT**

```
=LAMBDA(m,LET(t,CLEANCELL(m),f,LEFT(t,1),IF(t="","",IF(EXACT(UPPER(f),LOWER(f)),"",UPPER(f)))))
```

**NORMADDR**

```
=LAMBDA(s,TRIM(REDUCE(TRIM(REGEXREPLACE(LOWER(CLEANCELL(s)),"[.,]"," ")),SEQUENCE(ROWS(AddrFold[From])),LAMBDA(a,i,REGEXREPLACE(a,"\b"&INDEX(AddrFold[From],i)&"\b",INDEX(AddrFold[To],i))))))
```

**BORO**

```
=LAMBDA(z,IF(NOT(REGEXTEST(z&"","^\d{5}$")),"",LET(n,--z,i,XMATCH(n,ZipRanges[From],-1),IF(ISNA(i),"",IF(n<=INDEX(ZipRanges[To],i),INDEX(ZipRanges[Borough],i),"")))))
```

**SIMILAR.** The app's token sort ratio. Both texts are lowered, stripped to letters and digits, and their words sorted. The score is twice the longest common run of letters in order, over the two lengths, times 100. It was checked against the app on 20,000 pairs. It differs by 1 only on exact halves, and never on the 80, 86 or 88 cut-offs.

```
=LAMBDA(a,b,LET(p,LAMBDA(s,LET(t,TRIM(REGEXREPLACE(REGEXREPLACE(LOWER(s&""),"[^\x00-\x7F]",""),"[^a-z0-9]+"," ")),IF(t="","",TEXTJOIN(" ",TRUE,SORT(TOCOL(TEXTSPLIT(t," "))))))),x,p(a),y,p(b),lx,LEN(x),ly,LEN(y),IF(OR(lx=0,ly=0),0,LET(yc,MID(y,SEQUENCE(1,ly),1),fin,REDUCE(SEQUENCE(1,ly+1,0,0),SEQUENCE(lx),LAMBDA(prev,i,HSTACK(0,SCAN(0,SEQUENCE(1,ly),LAMBDA(lft,j,IF(INDEX(yc,1,j)=MID(x,i,1),INDEX(prev,1,j)+1,MAX(lft,INDEX(prev,1,j+1)))))))),ROUND(200*INDEX(fin,1,ly+1)/(lx+ly),0)))))
```

**LENCHK**

```
=LAMBDA(label,v,n,IF(LEN(v)>n,label&" exceeds max length "&n&" (got "&LEN(v)&")",""))
```

**NORMF**

```
=LAMBDA(v,TRIM(REGEXREPLACE(LOWER(CLEANCELL(v)),"[^\w]+"," ")))
```

**NORMZ**

```
=LAMBDA(v,LET(cv,CLEANCELL(v),s,SUBSTITUTE(cv," ",""),IF(cv="","",IF(REGEXTEST(s,"^\d{5}"),LEFT(s,5),LOWER(cv)))))
```

**DATEFIX**

```
=LAMBDA(v,LET(s,CLEANCELL(v),IF(s="","",IF(REGEXTEST(s,"^\d{5}$"),TEXT(--s,"yyyy-mm-dd"),LET(ga,IFERROR(REGEXEXTRACT(s,"^(\d{4})[-/.](\d{1,2})[-/.](\d{1,2})$",2),""),gb,IFERROR(REGEXEXTRACT(s,"^(\d{1,2})[-/.](\d{1,2})[-/.](\d{2,4})$",2),""),ka,COUNTA(ga)=3,kb,COUNTA(gb)=3,IF(NOT(OR(ka,kb)),"#BAD",LET(yr,--IF(ka,INDEX(ga,1),INDEX(gb,3)),mo,--IF(ka,INDEX(ga,2),INDEX(gb,1)),dy,--IF(ka,INDEX(ga,3),INDEX(gb,2)),yy,IF(AND(kb,yr<100),yr+IF(yr>25,1900,2000),yr),ok,AND(mo>=1,mo<=12,dy>=1,dy<=31),sw,AND(dy>=1,dy<=12,mo>=1,mo<=31),mm,IF(ok,mo,dy),dd,IF(ok,dy,mo),IF(AND(NOT(ok),NOT(sw)),"#BAD",IF(OR(yy<1900,yy>2100),"#BAD",IF(OR(MONTH(DATE(yy,mm,dd))<>mm,DAY(DATE(yy,mm,dd))<>dd),"#BAD",TEXT(DATE(yy,mm,dd),"yyyy-mm-dd")))))))))))
```

**FOLD**

```
=LAMBDA(s,TRIM(REGEXREPLACE(SUBSTITUTE(SUBSTITUTE(REDUCE(LOWER(s&""),SEQUENCE(ROWS(Accents[From])),LAMBDA(a,i,SUBSTITUTE(a,INDEX(Accents[From],i),INDEX(Accents[To],i)))),"-"," "),"'",""),"[^a-z0-9 ]"," ")))
```

**SPARTS**

```
=LAMBDA(nm,LET(f,FOLD(nm),p,TEXTSPLIT(f," ",,TRUE),q,FILTER(p,ISNA(XMATCH(p,Suffixes[Word])),""),k,FILTER(q,ISNA(XMATCH(q,Particles[Word]))*(LEN(q)>1),""),IF(f="","",TEXTJOIN(" ",TRUE,IF(TEXTJOIN("",TRUE,k)="",q,k)))))
```

**AKEY**

```
=LAMBDA(street,zip,LET(s,TRIM(REGEXREPLACE(FOLD(street),"\b(?:street|st|avenue|ave|road|rd|boulevard|blvd|place|pl|drive|dr|court|ct|lane|ln|terrace|ter|parkway|pkwy)\b","")),z,LEFT(TRIM(zip&""),5),IF(OR(s="",z=""),"",s&"|"&z)))
```

**DOBNEAR.** Takes two dates written 2024-03-15.

```
=LAMBDA(a,b,LET(x,SUBSTITUTE(a,"-",""),y,SUBSTITUTE(b,"-",""),d,MID(x,SEQUENCE(8),1)<>MID(y,SEQUENCE(8),1),n,SUM(--d),p,IFERROR(XMATCH(TRUE,d),0),OR(AND(LEFT(x,4)=LEFT(y,4),MID(x,5,2)=MID(y,7,2),MID(x,7,2)=MID(y,5,2)),n=1,IF(AND(n=2,p>0,p<8),AND(INDEX(d,p+1),MID(x,p,1)=MID(y,p+1,1),MID(x,p+1,1)=MID(y,p,1)),FALSE))))
```

**SAMESET**

```
=LAMBDA(a,b,LET(x,TEXTSPLIT(a," "),y,TEXTSPLIT(b," "),AND(ISNUMBER(XMATCH(x,y)),ISNUMBER(XMATCH(y,x)))))
```

**ANYSHARED.** The third value is the separator. Leave it out for a space.

```
=LAMBDA(a,b,[d],LET(sep,IF(ISOMITTED(d)," ",d),IF(OR(a="",b=""),FALSE,OR(ISNUMBER(XMATCH(TEXTSPLIT(a,sep),TEXTSPLIT(b,sep)))))))
```

## Lookup tables

Each list becomes an Excel table on Ref with the name and headers shown. Keep the rows in the order given. The order matters for AddrFold and ZipRanges.

**Placeholders**, one column named Value. Type #n/a as '#n/a so Excel keeps it as text rather than an error.

```csv
Value
null
none
n/a
na
#n/a
nan
nil
(null)
```

**Boroughs.** Type the header and the five names in this order. Select only the five names under the header and name them Boroughs in the Name Box. The order decides a tie in SIMILAR.

```csv
Borough
New York
Brooklyn
Queens
Bronx
Staten Island
```

**CityAliases**, 24 rows. Key is compared in any capitals.

```csv
Key,City
new york,New York
newyork,New York
newyrk,New York
new york city,New York
nyc,New York
ny,New York
manhattan,New York
mahattan,New York
new yrk,New York
brooklyn,Brooklyn
broklyn,Brooklyn
bklyn,Brooklyn
bk,Brooklyn
queens,Queens
qns,Queens
queen,Queens
bronx,Bronx
the bronx,Bronx
bx,Bronx
staten island,Staten Island
si,Staten Island
s.i.,Staten Island
staten is,Staten Island
statenisland,Staten Island
```

**Hoods**, 114 neighborhoods.

```csv
Key,Borough
harlem,New York
east harlem,New York
washington heights,New York
inwood,New York
chelsea,New York
soho,New York
tribeca,New York
greenwich village,New York
west village,New York
east village,New York
midtown,New York
upper east side,New York
upper west side,New York
lower east side,New York
chinatown,New York
financial district,New York
hell's kitchen,New York
hells kitchen,New York
murray hill,New York
gramercy,New York
morningside heights,New York
williamsburg,Brooklyn
bushwick,Brooklyn
bedford stuyvesant,Brooklyn
bed stuy,Brooklyn
crown heights,Brooklyn
flatbush,Brooklyn
east flatbush,Brooklyn
park slope,Brooklyn
sunset park,Brooklyn
bay ridge,Brooklyn
bensonhurst,Brooklyn
coney island,Brooklyn
brighton beach,Brooklyn
canarsie,Brooklyn
brownsville,Brooklyn
east new york,Brooklyn
greenpoint,Brooklyn
dumbo,Brooklyn
fort greene,Brooklyn
gowanus,Brooklyn
red hook,Brooklyn
sheepshead bay,Brooklyn
borough park,Brooklyn
boro park,Brooklyn
midwood,Brooklyn
prospect heights,Brooklyn
carroll gardens,Brooklyn
flatlands,Brooklyn
cypress hills,Brooklyn
astoria,Queens
long island city,Queens
lic,Queens
woodside,Queens
sunnyside,Queens
jackson heights,Queens
elmhurst,Queens
corona,Queens
flushing,Queens
jamaica,Queens
forest hills,Queens
rego park,Queens
kew gardens,Queens
richmond hill,Queens
ozone park,Queens
howard beach,Queens
far rockaway,Queens
rockaway,Queens
bayside,Queens
whitestone,Queens
college point,Queens
fresh meadows,Queens
ridgewood,Queens
maspeth,Queens
middle village,Queens
glendale,Queens
st albans,Queens
saint albans,Queens
cambria heights,Queens
queens village,Queens
springfield gardens,Queens
rosedale,Queens
laurelton,Queens
hollis,Queens
south ozone park,Queens
east elmhurst,Queens
riverdale,Bronx
fordham,Bronx
pelham bay,Bronx
throgs neck,Bronx
morris park,Bronx
hunts point,Bronx
mott haven,Bronx
concourse,Bronx
kingsbridge,Bronx
morrisania,Bronx
soundview,Bronx
castle hill,Bronx
parkchester,Bronx
wakefield,Bronx
williamsbridge,Bronx
co-op city,Bronx
co op city,Bronx
tremont,Bronx
st george,Staten Island
saint george,Staten Island
tottenville,Staten Island
great kills,Staten Island
new dorp,Staten Island
port richmond,Staten Island
stapleton,Staten Island
west brighton,Staten Island
todt hill,Staten Island
annadale,Staten Island
```

**ZipRanges.** New York ZIPs by borough. A ZIP outside these gives no borough.

```csv
From,To,Borough
10001,10292,New York
10301,10314,Staten Island
10451,10475,Bronx
11004,11005,Queens
11101,11120,Queens
11201,11256,Brooklyn
11351,11697,Queens
```

**AddrFold.** Whole words replaced when streets are compared, applied top to bottom.

```csv
From,To
st,street
ave,avenue
rd,road
blvd,boulevard
dr,drive
ln,lane
ct,court
pl,place
apt,apartment
ste,suite
w,west
e,east
n,north
s,south
```

**Suffixes**, one column named Word.

```csv
Word
jr
sr
ii
iii
iv
v
```

**Particles**, one column named Word. Parts of a surname that do not tell people apart on their own.

```csv
Word
de
del
de la
la
las
los
van
von
der
den
di
da
do
dos
du
el
al
bin
ibn
san
santa
st
mc
mac
o
```

**Accents.** Letters with accents and the plain letter FOLD puts in their place.

```csv
From,To
á,a
à,a
â,a
ä,a
ã,a
å,a
é,e
è,e
ê,e
ë,e
í,i
ì,i
î,i
ï,i
ó,o
ò,o
ô,o
ö,o
õ,o
ú,u
ù,u
û,u
ü,u
ñ,n
ç,c
ý,y
ÿ,y
```

**Defaults**, with headers File, Field and Value. Empty until P2. File is a table name from P1, or (all). Field is First\_Name, Middle\_Initial, Last\_Name, Client\_ID, Address\_1, Address\_2, City, State, Zip, Program, or an added field's name. The row below is an example. Replace it with your own.

```csv
File,Field,Value
clinic_export.csv :: A1:K120,Program,Youth Services
```

## Nicknames

The 92 groups of given names the app treats as one name, as a table named Nicknames with one row per name. Some names sit in two groups, such as ted (Edward and Theodore) and henry (Henry and Enrique). A pair matches when the two names share any group. A nickname match adds 22 points in P11 and never joins two records by itself.

```csv
Group,Name
1,robert
1,rob
1,bob
1,bobby
1,robbie
1,bert
2,margaret
2,peggy
2,peg
2,maggie
2,meg
2,marge
2,margie
2,rita
2,greta
3,charles
3,charlie
3,chuck
3,chas
3,chip
3,carlos
4,william
4,will
4,bill
4,billy
4,willie
4,liam
5,richard
5,rich
5,rick
5,ricky
5,dick
5,richie
6,elizabeth
6,liz
6,beth
6,betty
6,betsy
6,eliza
6,libby
6,lizzie
6,liza
7,james
7,jim
7,jimmy
7,jamie
8,john
8,jack
8,johnny
8,jon
9,joseph
9,joe
9,joey
10,michael
10,mike
10,mikey
10,mickey
10,micky
11,thomas
11,tom
11,tommy
12,edward
12,ed
12,eddie
12,ted
12,teddy
12,ned
13,anthony
13,tony
13,ant
14,katherine
14,catherine
14,kathryn
14,kate
14,katie
14,kathy
14,cathy
14,kay
14,kit
15,patricia
15,pat
15,patty
15,trish
15,tricia
15,patsy
16,barbara
16,barb
16,babs
17,susan
17,sue
17,susie
17,suzy
17,suzanne
18,jennifer
18,jen
18,jenny
18,jenn
19,deborah
19,debra
19,deb
19,debbie
20,sandra
20,sandy
21,theodore
21,ted
21,teddy
21,theo
22,nicholas
22,nick
22,nicky
23,alexander
23,alexandra
23,alex
23,xander
23,sasha
24,christopher
24,chris
24,topher
25,daniel
25,dan
25,danny
26,david
26,dave
26,davey
27,donald
27,don
27,donnie
28,ronald
28,ron
28,ronnie
29,kenneth
29,ken
29,kenny
30,lawrence
30,larry
30,laurence
30,laurie
31,gregory
31,greg
32,jeffrey
32,geoffrey
32,jeff
33,stephen
33,steven
33,steve
33,stevie
34,andrew
34,andy
34,drew
35,frederick
35,fred
35,freddie
35,freddy
36,eugene
36,gene
37,vincent
37,vince
37,vinny
37,vinnie
38,francis
38,frances
38,frank
38,fran
38,franny
38,francisco
38,paco
38,pancho
39,henry
39,hank
39,hal
39,harry
40,albert
40,al
40,albie
41,arthur
41,art
41,artie
42,benjamin
42,ben
42,benny
42,benji
43,bernard
43,bernie
44,dennis
44,denny
45,douglas
45,doug
46,eleanor
46,ellie
46,nell
46,nora
47,emily
47,em
47,emmy
48,florence
48,flo
48,flossie
49,george
49,georgie
50,gerald
50,gerry
50,jerry
51,harold
51,hal
51,harry
52,jacob
52,jake
53,janet
53,jan
54,jonathan
54,jon
54,jonny
55,joshua
55,josh
56,judith
56,judy
56,jude
57,louis
57,lou
57,louie
57,luis
58,martha
58,marty
58,mattie
59,mary
59,molly
59,polly
59,mae
59,may
59,maria
60,matthew
60,matt
60,matty
61,melissa
61,mel
61,missy
62,nancy
62,nan
63,nathaniel
63,nathan
63,nate
64,pamela
64,pam
65,peter
65,pete
66,philip
66,phillip
66,phil
67,rebecca
67,becky
67,becca
67,reba
68,raymond
68,ray
69,rose
69,rosie
69,rosa
70,samuel
70,sam
70,sammy
71,sarah
71,sara
71,sally
71,sadie
72,stanley
72,stan
73,timothy
73,tim
73,timmy
74,victoria
74,vicky
74,vicki
74,tori
75,virginia
75,ginny
75,ginger
76,walter
76,walt
76,wally
77,zachary
77,zach
77,zack
78,jose
78,pepe
79,guadalupe
79,lupe
80,concepcion
80,concha
81,jesus
81,chuy
82,ignacio
82,nacho
83,enrique
83,quique
83,henry
84,eduardo
84,lalo
84,edward
85,manuel
85,manny
85,manolo
86,antonio
86,tono
86,tony
87,dolores
87,lola
88,mercedes
88,meche
89,rosario
89,charo
90,magdalena
90,magda
90,lena
91,esperanza
91,espy
92,soledad
92,sole
92,chole
```

## Program words

The words P5 sets aside when it compares program spellings. They only shape the suggestions. The ProgramMap a person confirms is what counts.

**Filler words**, dropped from a program name before comparing.

```csv
Word
a
an
and
client
clients
department
dept
div
division
for
general
initiative
of
office
participant
participants
prog
program
programs
project
service
services
svc
svcs
team
the
unit
```

**Short forms**, read as the long word before comparing.

```csv
Short,Long
dev,development
admin,administration
mgmt,management
svcs,services
res,resident
comm,community
educ,education
empl,employment
trng,training
asst,assistance
hsg,housing
wf,workforce
```

Before comparing, & becomes and, accents are removed, and punctuation becomes a space. Two names are proposed as one program at SIMILAR 86 or more on the reduced names.
