from _common import *
# Each case: jammed Address_1 value, plus the other columns the file has.
cases = [
 ("9-digit ZIP jammed, no Zip column",     dict(Addr="123 Main St, Brooklyn, NY 112011234", City="", State="", Zip="")),
 ("9-digit ZIP jammed, Zip col blank",     dict(Addr="123 Main St Brooklyn NY 112011234", City="", State="", Zip="")),
 ("Grand Concourse no city",               dict(Addr="1010 Grand Concourse NY 10452", City="", State="", Zip="")),
 ("Grand Concourse w/ Bronx",              dict(Addr="1010 Grand Concourse Bronx NY 10452", City="", State="", Zip="")),
 ("Grand Concourse, Zip col",              dict(Addr="1010 Grand Concourse", City="Bronx", State="NY", Zip="10452")),
 ("spaced hyphen house number",            dict(Addr="117 - 19 45th Ave", City="Queens", Zip="11355")),
 ("spaced hyphen house number, jammed",    dict(Addr="117 - 19 45th Ave, Flushing, NY 11355", City="", State="", Zip="")),
 ("Woodhaven (not in neighborhood table)", dict(Addr="85-10 Forest Pkwy Woodhaven NY 11421", City="", State="", Zip="")),
 ("Brooklyn Heights jammed",               dict(Addr="123 Montague St Brooklyn Heights NY 11201", City="", State="", Zip="")),
 ("Bklyn after unit",                      dict(Addr="123 Main St Apt 4B Bklyn NY 11201", City="", State="", Zip="")),
 ("unit then city, comma",                 dict(Addr="123 Main St, Apt 3 Brooklyn NY 11201", City="", State="", Zip="")),
 ("unit after zip",                        dict(Addr="123 Main St, Brooklyn NY 11201 Apt 3", City="", State="", Zip="")),
 ("', Lower' with City col",               dict(Addr="123 Main St, Lower", City="Brooklyn", Zip="11201")),
 ("', Top Floor' with City col",           dict(Addr="123 Main St, Top Floor", City="Brooklyn", Zip="11201")),
 ("', c/o Jane Doe' with City col",        dict(Addr="123 Main St, c/o Jane Doe", City="Brooklyn", Zip="11201")),
 ("parsed city disagrees with City col",   dict(Addr="123 Main St, Brooklyn", City="Queens", Zip="11355")),
 ("parsed ZIP disagrees with Zip col",     dict(Addr="123 Main St, Brooklyn NY 11201", City="Brooklyn", Zip="11234")),
 ("Apt B left in street",                  dict(Addr="123 Main St Apt B", City="Brooklyn", Zip="11201")),
 ("', B' unit with comma",                 dict(Addr="123 Main St, B, Brooklyn NY 11201", City="", State="", Zip="")),
 ("Hoboken NJ jammed, no cols",            dict(Addr="123 Main St, Hoboken, NJ 07030", City="", State="", Zip="")),
 ("Hoboken NJ jammed, City/State cols",    dict(Addr="123 Main St", City="Hoboken", State="NJ", Zip="07030")),
 ("Unit in Addr, other unit in Addr2",     dict(Addr="123 Main St Apt 4B", Addr2="Apt 5C", Zip="11201")),
 ("Unit in Addr same as Addr2",            dict(Addr="123 Main St Apt 4B", Addr2="4B", Zip="11201")),
 ("Unit in Addr, Addr2 = c/o",             dict(Addr="123 Main St Apt 4B", Addr2="c/o Jane", Zip="11201")),
 ("Addr2 '4' vs Addr 'Apt 4B'",            dict(Addr="123 Main St Apt 4B", Addr2="4", Zip="11201")),
]
for label, kw in cases:
    st, r = final(**kw)
    show(label, st, r)
    print(f"{'':38}    Flags: {[f['message'][:60] for f in r['__flags__']]}")
