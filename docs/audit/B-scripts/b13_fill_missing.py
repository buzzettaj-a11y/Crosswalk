from _common import *
import _refdata, fill_missing
idx, meta = engine.load_geocode_index(_refdata.write())
fnd = fill_missing.ZipFinder(idx, None)
print("== propose(street, city) ==")
for st, city in [("900 Flatbush Ave","Brooklyn"),("2250 Flatbush Ave","Brooklyn"),("85 Montague St","Brooklyn"),("999 Montague St","Brooklyn"),("999 Montague St",""),
                 ("1 Main St","Brooklyn"),("1010 Grand Concourse","Bronx"),("77 Grand Concourse","Bronx"),("1 Avenue W","Brooklyn"),("1 Avenue U","Brookline")]:
    print(f"{st!r:26} {city!r:12} ->", fnd.propose(st, city))
print("\n== propose_city for rows with a NON-NYC zip ==")
for st, z in [("85 Montague St","07030"),("85 Montague St","99999"),("85 Montague St","10701"),("1010 Grand Concourse","12345")]:
    print(f"{st!r:26} zip={z} ->", fnd.propose_city(st, z))

print("\n== propose_for_row on review-style records ==")
def rec(city, zipc, st, state="NY", errs=()):
    return {"Address_1": st, "City": city, "Zip": zipc, "State": state, "__errors__": list(errs)}
for r in [rec("Hoboken","07030","85 Montague St", errs=["Unrecognized City: 'Hoboken'"]),
          rec("Hoboken","","85 Montague St", errs=["Unrecognized City: 'Hoboken'","Invalid ZIP Code format: (blank)"]),
          rec("Yonkers","10701","85 Montague St", errs=["Unrecognized City: 'Yonkers'"]),
          rec("Brookline","","900 Flatbush Ave", errs=[]),
          rec("Brooklyn","","2250 Flatbush Ave", errs=["Invalid ZIP Code format: (blank)"]),
          rec("Brooklyn","7030","85 Montague St", errs=["Invalid ZIP Code format: 7030"])]:
    print(r["City"], r["Zip"], r["Address_1"], "->", fill_missing.propose_for_row(r, fnd))
