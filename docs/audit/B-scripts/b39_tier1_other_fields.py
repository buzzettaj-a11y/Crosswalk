"""Tier 1 'identical record' with the same Client ID: which fields does the comparison actually use?"""
from _common import *
mapping = dict(MAPPING); mapping["Middle_Initial"] = "MI"
base = dict(First="John", Last="Smith", ID="77", Addr="10 Main St", Addr2="", City="Brooklyn", State="NY", Zip="11201")
def run(label, a, b, schema=None, mp=None):
    res = pipeline([dict(base, **a), dict(base, **b)], schema=schema, mapping=mp)
    print(label)
    for r in res["transformed"]:
        print("   MI=%r Addr2=%r ->" % (r["Middle_Initial"], r["Address_2"]), ("REVIEW: " + "; ".join(r["__errors__"])) if r["__errors__"] else "CLEAN")
run("same ID, same name/address/ZIP, middle initial A vs B (two different people):", dict(MI="A"), dict(MI="B"), mp=mapping)
run("same ID, same name/street/ZIP, Address_2 'Apt 1' vs 'Apt 2' (two apartments):", dict(Addr2="Apt 1"), dict(Addr2="Apt 2"))
