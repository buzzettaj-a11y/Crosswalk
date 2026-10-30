"""How many common NYC neighborhood names are in the 114-name table the address splitter relies on."""
from _common import *
names = ["woodhaven","brooklyn heights","kew gardens hills","rockaway park","bay terrace","jamaica estates",
 "little neck","douglaston","bellerose","floral park","glen oaks","breezy point","woodlawn","bedford park",
 "norwood","spuyten duyvil","arverne","kensington","bergen beach","marine park","mill basin","gravesend",
 "dyker heights","windsor terrace","cobble hill","boerum hill","clinton hill","ditmas park","east williamsburg",
 "hamilton heights","kips bay","roosevelt island","battery park city","mariners harbor","new brighton",
 "bulls head","oakland gardens","briarwood","hollis hills","ridgewood","cypress hills","maspeth",
 "bensonhurst","canarsie","bushwick"]
tbl = engine.NEIGHBORHOOD_TO_BOROUGH
print("neighborhood table size:", len(tbl), "| city alias table size:", len(engine.CITY_ALIASES))
present = [n for n in names if n in tbl]
print(f"{len(present)} of {len(names)} common names are in the table; present: {present}")
print("missing:", [n for n in names if n not in tbl])
