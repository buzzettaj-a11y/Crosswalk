"""
s02: Can two different people be auto-linked without a person deciding?
Uses identity.resolve directly (unit level) and then the server end to end.
"""
from cwlib import *
import identity as I


def rec(rid, first, last, dob="", street="", zip="", program="", cid="", system="A.csv"):
    return I.PersonRecord(rid, first=first, last=last, dob=dob, street=street, zip=zip,
                          program=program, client_id=cid, system=system)


def verdict(label, a, b, truth):
    pts, ev, caution = I.score_pair(a, b)
    auto = I._is_auto(a, b, pts, ev)
    res = I.resolve([a, b])
    n_people = res["unique_clients"]["settled"]
    props = len(res["proposals"])
    print(f"{label:<62} pts={pts:<4} auto={auto!s:<5} people={n_people} open_proposals={props}"
          f"  truth={truth}")
    return auto


print("--- unit level: identity.score_pair / _is_auto / resolve ---")
# 1. same name + DOB, different addresses, same ZIP
verdict("same name+DOB, different street, same ZIP (Maria Rodriguez)",
        rec("a", "Maria", "Rodriguez", "1985-03-14", "100 Grand Concourse", "10451", system="A.csv"),
        rec("b", "Maria", "Rodriguez", "1985-03-14", "900 Walton Ave", "10451", system="B.csv"),
        "unknown (could be a move or a namesake)")
# 2. same name+DOB, different addresses, different ZIPs
verdict("same name+DOB, different street, different ZIP",
        rec("a", "Maria", "Rodriguez", "1985-03-14", "100 Grand Concourse", "10451", system="A.csv"),
        rec("b", "Maria", "Rodriguez", "1985-03-14", "55 Main St", "11201", system="B.csv"),
        "unknown")
# 3. twins at one address (same surname, DOB, address, different given names)
verdict("TWINS: Jordan/Jaden Smith same DOB same address",
        rec("a", "Jordan", "Smith", "2015-06-01", "10 Oak St", "11201", system="A.csv"),
        rec("b", "Jaden", "Smith", "2015-06-01", "10 Oak St", "11201", system="B.csv"),
        "2 people")
# 4. Jr and Sr at one address, DOBs one digit apart
verdict("JR/SR: Robert Smith 1962-03-14 vs Jr 1992-03-14, same address",
        rec("a", "Robert", "Smith", "1962-03-14", "10 Oak St", "11201", system="A.csv"),
        rec("b", "Robert", "Smith Jr", "1992-03-14", "10 Oak St", "11201", system="B.csv"),
        "2 people")
# 5. Jr and Sr, DOBs far apart
verdict("JR/SR: Robert Smith 1958-03-14 vs Jr 1985-07-30, same address",
        rec("a", "Robert", "Smith", "1958-03-14", "10 Oak St", "11201", system="A.csv"),
        rec("b", "Robert", "Smith Jr", "1985-07-30", "10 Oak St", "11201", system="B.csv"),
        "2 people")
# 6. Jr and Sr, no DOB at all
verdict("JR/SR: no DOB, same address",
        rec("a", "Robert", "Smith", "", "10 Oak St", "11201", system="A.csv"),
        rec("b", "Robert", "Smith Jr", "", "10 Oak St", "11201", system="B.csv"),
        "2 people")
# 7. same DOB typed day/month swapped (a typo or a different person?)
verdict("same name+address, DOB day and month swapped (05/06 vs 06/05)",
        rec("a", "Ana", "Perez", "1990-05-06", "7 Elm St", "10013", system="A.csv"),
        rec("b", "Ana", "Perez", "1990-06-05", "7 Elm St", "10013", system="B.csv"),
        "needs a person (near DOB)")
# 8. nickname + same DOB + same ZIP, different street
verdict("Bill vs William Smith, same DOB, same ZIP, different street",
        rec("a", "Bill", "Smith", "1970-01-02", "1 Pine St", "10013", system="A.csv"),
        rec("b", "William", "Smith", "1970-01-02", "99 Oak Ave", "10013", system="B.csv"),
        "needs a person")
# 9. same name, same DOB, NYC directional spelled differently (address says different)
verdict("same name+DOB, 'W 45th St' vs 'West 45th Street' same ZIP",
        rec("a", "Luis", "Diaz", "1980-02-02", "12 W 45th St", "10036", system="A.csv"),
        rec("b", "Luis", "Diaz", "1980-02-02", "12 West 45th Street", "10036", system="B.csv"),
        "same person")
# 10. address street type is ignored: 123 45th St vs 123 45th Ave (Queens has both)
verdict("123 45th St vs 123 45th Ave same ZIP, same name+DOB",
        rec("a", "Luis", "Diaz", "1980-02-02", "123 45th St", "11377", system="A.csv"),
        rec("b", "Luis", "Diaz", "1980-02-02", "123 45th Ave", "11377", system="B.csv"),
        "different places")
# 10b. strong ids
va = verdict("10b: addr_key ignores street type: '45 Park Ave' vs '45 Park Pl' (name differs by sibling)",
        rec("a", "Ana", "Perez", "", "45 Park Ave", "10013", system="A.csv"),
        rec("b", "Ana", "Perez", "", "45 Park Pl", "10013", system="B.csv"),
        "different addresses")
print("   addr_key a:", rec("a", "Ana", "Perez", "", "45 Park Ave", "10013").addr_key,
      "| b:", rec("b", "Ana", "Perez", "", "45 Park Pl", "10013").addr_key)
# 11. same system id, different names
verdict("same system ID '1001', different people, same surname+ZIP",
        rec("a", "Carlos", "Vega", "1975-01-01", "5 A St", "10001", cid="1001", system="A.csv"),
        rec("b", "Elena", "Vega", "1999-09-09", "6 B St", "10001", cid="1001", system="A.csv"),
        "2 people (ID reuse)")
# 12. one person, strong evidence, split?
verdict("same person: name+DOB+address, but middle name in first",
        rec("a", "Maria", "Lopez", "1985-03-14", "100 Grand Concourse", "10451", system="A.csv"),
        rec("b", "Maria Elena", "Lopez", "1985-03-14", "100 Grand Concourse Apt 4B", "10451", system="B.csv"),
        "1 person")
verdict("same person: married surname, same first, DOB, address",
        rec("a", "Maria", "Lopez", "1985-03-14", "100 Grand Concourse", "10451", system="A.csv"),
        rec("b", "Maria", "Garcia", "1985-03-14", "100 Grand Concourse", "10451", system="B.csv"),
        "1 person, needs a person by design")
verdict("same person: DOB year typo + same name+address",
        rec("a", "Maria", "Lopez", "1985-03-14", "100 Grand Concourse", "10451", system="A.csv"),
        rec("b", "Maria", "Lopez", "1958-03-14", "100 Grand Concourse", "10451", system="B.csv"),
        "needs a person")
verdict("same person: name+address+ZIP, no DOB in either",
        rec("a", "Maria", "Lopez", "", "100 Grand Concourse", "10451", system="A.csv"),
        rec("b", "Maria", "Lopez", "", "100 Grand Concourse", "10451", system="B.csv"),
        "needs a person (no DOB)")
verdict("same person: first-name accent José vs Jose, DOB, address",
        rec("a", "José", "Lopez", "1985-03-14", "100 Grand Concourse", "10451", system="A.csv"),
        rec("b", "Jose", "Lopez", "1985-03-14", "100 Grand Concourse", "10451", system="B.csv"),
        "1 person")
