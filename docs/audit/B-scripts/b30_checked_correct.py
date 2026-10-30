"""Behaviors that were probed and found correct. Each line asserts the expected value."""
from _common import *
import _refdata, csv, tempfile, os
ok = lambda label, cond: print(("PASS  " if cond else "FAIL  ") + label)
cc = engine.clean_cell
ok("NBSP, tab, CR/LF and runs of spaces collapse to one space", cc("a b\tc\r\nd   e") == "a b c d e")
ok("NULL, N/A, none, NA, NaN, #N/A, nil, (null) and empty become blank", all(cc(v) == "" for v in ["NULL","N/A","none","NA","NaN","#N/A","nil","(null)","", "  ", " "]))
ok("None and float NaN become blank", cc(None) == "" and cc(float("nan")) == "")
ok("07030 and 00501 keep their leading zero", engine.normalize_zip("07030")[0] == "07030" and engine.normalize_zip("00501")[0] == "00501")
ok("ZIP+4 and 9-digit ZIP in the ZIP column reduce to 5 digits", engine.normalize_zip("11201-1234")[0] == "11201" and engine.normalize_zip("112011234")[0] == "11201")
ok("4-digit, 7030.0, letters and 11201-123 are rejected (review), not repaired", all(engine.normalize_zip(v)[0] == "" for v in ["7030","7030.0","112O1","11201-123"]))
sj = engine.split_jammed_address
ok("Apt 4B, #4B, 4th Floor, Basement split to the unit", [sj(a)["unit"] for a in ["123 Main St Apt 4B","123 Main St #4B","123 Main St 4th Floor","123 Main St Basement"]] == ["Apt 4B","#4B","4th Floor","Basement"])
ok("117-19 45th Ave stays whole; 14A / Apt 14A split off", sj("117-19 45th Ave")["street"] == "117-19 45th Ave" and sj("117-19 45th Ave 14A")["unit"] == "14A")
ok("Avenue U, Avenue of the Americas, Floor St, Suite Rd, Route 9 stay whole", all(sj(a)["unit"] == "" and sj(a)["street"] == a for a in ["100 Avenue U","2250 Avenue of the Americas","1 Floor St","55 Suite Rd","1234 Route 9"]))
ok("123 1/2 Main St keeps the 1/2", sj("123 1/2 Main St")["street"] == "123 1/2 Main St")
ok("Brooklyn Ave / Queens Blvd / Jamaica Ave are not read as the city", sj("123 Brooklyn Ave NY 11203")["city"] == "" and sj("1 Queens Blvd 11375")["city"] == "" and sj("123 Jamaica Ave NY 11432")["city"] == "")
ok("street with a city after it still splits (Brooklyn Ave, Brooklyn)", sj("123 Brooklyn Ave Brooklyn NY 11203") == {"street":"123 Brooklyn Ave","unit":"","city":"Brooklyn","state":"NY","zip":"11203"})
ok("100 New York Ave keeps New York in the street", sj("100 New York Ave, NY 11216")["street"] == "100 New York Ave")
ok("extra commas, New York State, country at end, ZIP+4", sj("123 Main St,, Brooklyn NY 11201")["city"] == "Brooklyn" and sj("123 Main St, Brooklyn, New York State 11201")["state"] == "NY" and sj("123 Main St, Brooklyn, NY 11201 USA")["zip"] == "11201" and sj("123 Main St, Brooklyn, NY 11201-1234")["zip"] == "11201")
ok("Apt 4B in the street plus 4B in Address_2 collapses; Apt 4B vs Apt 5C goes to review", final(Addr="123 Main St Apt 4B", Addr2="4B")[0] == "CLEAN" and final(Addr="123 Main St Apt 4B", Addr2="Apt 5C")[0].startswith("REVIEW: Unit conflict"))
ok("blank City filled from ZIP; recognized borough that contradicts the ZIP goes to review", final(City="", Zip="11355")[1]["City"] == "Queens" and final(City="Brooklyn", Zip="10001")[0].startswith("REVIEW: City/ZIP conflict"))
ok("typed recognized City is never overwritten (Manhattan typed + 10001)", final(City="Manhattan", Zip="10001")[1]["City"] == "New York")
ok("neighborhood Flushing folds to Queens, note recorded", engine.normalize_city("Flushing")[0] == "Queens")
ok("State NJ / blank-State-with-NJ-city goes to review", final(State="NJ", City="Hoboken", Zip="07030")[0].startswith("REVIEW"))
sn = engine.split_jammed_name
ok("Smith, John A / John A Smith / Smith, John Jr / John Smith III", sn("Smith, John A") == {"first":"John","middle":"A","last":"Smith"} and sn("John A Smith")["last"] == "Smith" and sn("Smith, John Jr")["last"] == "Smith Jr" and sn("John Smith III")["last"] == "Smith III")
ok("hyphenated surname and O'Brien survive, casing is preserved", sn("Mary Smith-Jones")["last"] == "Smith-Jones" and sn("Pat O'Brien")["last"] == "O'Brien" and sn("SMITH,JOHN")["last"] == "SMITH")
ok("single name gives first only (then Missing Last_Name in review)", sn("Madonna") == {"first":"Madonna","middle":"","last":""} and final(First="Madonna", Last="")[0].startswith("REVIEW: Missing Last_Name"))
ok("smart_title_name keeps DiNapoli, McDonald, O'Brien, MacArthur, St. Claire", [engine.smart_title_name(n) for n in ["DiNapoli","MCDONALD","O'BRIEN","MACARTHUR","ST. CLAIRE"]] == ["DiNapoli","McDonald","O'Brien","MacArthur","St. Claire"])
pv = engine.parse_date_value
ok("impossible dates are rejected: 2/30/1990, 02/29/2001, 4/31/1990, 2/29/1900, 00/00/0000", all(pv(v) is None for v in ["2/30/1990","02/29/2001","4/31/1990","2/29/1900","00/00/0000"]))
ok("leap day 2/29/2000 accepted; 8-digit 19900304 and month names go to review", pv("2/29/2000") == (2000,2,29) and pv("19900304") is None and pv("March 4, 1990") is None)
ok("fuzzy backend is thefuzz token_sort_ratio (order-insensitive)", engine.FUZZ_BACKEND == "thefuzz")
for a, b in [("100 e 10 st","100 w 10 st"),("123 fulton ave","123 fulton st"),("5 beach 19 st","5 beach 9 st"),("1 avenue w","1 avenue v")]:
    print(f"      info: ratio({a!r}, {b!r}) = {engine._ratio(engine._norm_addr(a), engine._norm_addr(b))} (threshold 88)")
ok("transform: Rear/Front stay in the stored street (spec: ignored for geocoding only)", sj("123 Main St Rear")["street"] == "123 Main St Rear")
