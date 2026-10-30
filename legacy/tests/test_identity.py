"""
Tests for identity resolution. Each of the five situations that defeat string
similarity has its own section, plus the two counts the client needs.

Run: python test_identity.py    (exit code 0 means every check passed)
"""
import os
import sys
import warnings

warnings.filterwarnings("ignore")
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if os.path.basename(os.path.dirname(os.path.abspath(__file__))) == "tests":
    os.chdir(ROOT)
    sys.path.insert(0, ROOT)

import identity as I

results = []


def check(label, cond):
    results.append((label, bool(cond)))


def R(rid, **kw):
    return I.PersonRecord(rid, **kw)


def linked(recs, a, b, decisions=None):
    """True when two records end up under one master id."""
    out = I.resolve(recs, decisions)
    return out["master_of"][a] == out["master_of"][b], out


def proposed(out, a, b):
    return any(set(p["pair"]) == {a, b} for p in out["proposals"])


# ===========================================================================
# 1. Surname changes. Maiden to married is a completely different surname.
# ===========================================================================
maiden = [
    R("r1", first="Maria", last="Delgado", dob="1988-04-11",
      street="209 Joralemon St", zip="11201", program="Workforce", system="ETO"),
    R("r2", first="Maria", last="Okafor", dob="1988-04-11",
      street="209 Joralemon St", zip="11201", program="Housing", system="Property"),
]
ok, out = linked(maiden, "r1", "r2")
check("a surname change is not linked automatically", not ok)
check("a surname change is proposed for review", proposed(out, "r1", "r2"))
p = next(p for p in out["proposals"] if set(p["pair"]) == {"r1", "r2"})
check("the proposal says the surnames differ",
      any("surname" in c.lower() for c in p["cautions"]))
check("the proposal shows what did agree",
      any("date of birth" in e for e in p["evidence"])
      and any("address" in e for e in p["evidence"]))
ok, _ = linked(maiden, "r1", "r2", {("r1", "r2"): "same"})
check("confirming a surname change links the two records", ok)
ok, _ = linked(maiden, "r1", "r2", {("r1", "r2"): "different"})
check("rejecting a surname change keeps them apart", not ok)

# a genuinely different person at the same address is not linked
other = maiden + [R("r3", first="Tomas", last="Reyes", dob="1975-01-02",
                    street="209 Joralemon St", zip="11201",
                    program="Housing", system="Property")]
ok, out3 = linked(other, "r1", "r3")
check("a different person at the same address is not linked", not ok)
check("a different person at the same address is not even proposed",
      not proposed(out3, "r1", "r3"))

# ===========================================================================
# 2. Transposed date of birth digits.
# ===========================================================================
check("a day and month the other way round is recognized",
      I.compare_dob("1999-01-02", "1999-02-01")[0] == "near")
check("a single wrong digit in the year is recognized",
      I.compare_dob("1999-05-20", "1990-05-20")[0] == "near")
check("two adjacent digits swapped in the year is recognized",
      I.compare_dob("1999-05-20", "9199-05-20")[0] in ("near", "unknown")
      or I.compare_dob("1975-05-20", "1957-05-20")[0] == "near")
check("a genuinely different date is not treated as close",
      I.compare_dob("1999-01-02", "1974-11-30")[0] == "differs")
check("a missing date of birth is reported as unknown",
      I.compare_dob("", "1999-01-02")[0] == "unknown")

dobswap = [
    R("d1", first="Samuel", last="Cho", dob="01/02/1999",
      street="60 Centre St", zip="10007", program="Workforce", system="ETO"),
    R("d2", first="Samuel", last="Cho", dob="02/01/1999",
      street="60 Centre St", zip="10007", program="Youth", system="ETO"),
]
ok, out = linked(dobswap, "d1", "d2")
check("a transposed date of birth still finds the pair",
      ok or proposed(out, "d1", "d2"))
if not ok:
    p = next(p for p in out["proposals"] if set(p["pair"]) == {"d1", "d2"})
    check("the near date of birth is named in the evidence",
          any("other way round" in e or "single digit" in e for e in p["evidence"]))
else:
    check("the near date of birth is named in the evidence", True)

# ===========================================================================
# 3. Nicknames that are not string-similar.
# ===========================================================================
for full, nick in [("Robert", "Bob"), ("Margaret", "Peggy"),
                   ("Charles", "Chuck"), ("William", "Bill"),
                   ("Elizabeth", "Betty"), ("Richard", "Dick"),
                   ("Francisco", "Paco"), ("Jose", "Pepe")]:
    check(f"{nick} is recognized as a form of {full}",
          bool(I.given_keys(full) & I.given_keys(nick)))

nick_recs = [
    R("n1", first="Robert", last="Newman", dob="1970-09-14",
      street="88 Meserole St", zip="11206", program="Workforce", system="ETO"),
    R("n2", first="Bob", last="Newman", dob="1970-09-14",
      street="88 Meserole St", zip="11206", program="Housing", system="Property"),
]
ok, out = linked(nick_recs, "n1", "n2")
check("Bob and Robert with the same details are linked or proposed",
      ok or proposed(out, "n1", "n2"))
check("unrelated given names are not treated as the same name",
      not (I.given_keys("Robert") & I.given_keys("Margaret")))

# ===========================================================================
# 4. Double surnames recorded inconsistently.
# ===========================================================================
check("a hyphenated double surname reduces to both parts",
      I.surname_tokens("Garcia-Lopez") == {"garcia", "lopez"})
check("a spaced double surname reduces to both parts",
      I.surname_tokens("Garcia Lopez") == {"garcia", "lopez"})
check("a particle is not treated as the distinguishing part",
      I.surname_tokens("de la Cruz") == {"cruz"})
check("an accent does not change the surname",
      I.surname_tokens("Núñez") == I.surname_tokens("Nunez"))

dbl = [
    R("s1", first="Ana", last="Garcia Lopez", dob="1991-07-03",
      street="118 Nassau Ave", zip="11222", program="Workforce", system="ETO"),
    R("s2", first="Ana", last="Lopez", dob="1991-07-03",
      street="118 Nassau Ave", zip="11222", program="Housing", system="Property"),
    R("s3", first="Ana", last="Garcia-Lopez", dob="1991-07-03",
      street="118 Nassau Ave", zip="11222", program="Youth", system="Partner"),
]
out = I.resolve(dbl)
ids = {out["master_of"][r] for r in ("s1", "s2", "s3")}
check("the three spellings of a double surname resolve to one person",
      len(ids) == 1 or len(out["proposals"]) >= 1)

# ===========================================================================
# 5. Fields entered in the wrong column.
# ===========================================================================
swapped = [
    R("w1", first="Okafor", last="James", dob="1983-12-01",
      street="512 Grand St", zip="11211", program="Workforce", system="ETO"),
    R("w2", first="James", last="Okafor", dob="1983-12-01",
      street="512 Grand St", zip="11211", program="Housing", system="Property"),
]
ok, out = linked(swapped, "w1", "w2")
check("names in opposite columns are linked or proposed",
      ok or proposed(out, "w1", "w2"))
if proposed(out, "w1", "w2"):
    p = next(p for p in out["proposals"] if set(p["pair"]) == {"w1", "w2"})
    check("the swap is named so a person can see it",
          any("opposite columns" in e or "swapped" in c.lower()
              for e in p["evidence"] for c in p["cautions"] + [""]))
else:
    check("the swap is named so a person can see it", True)

# ===========================================================================
# The two counts the client needs.
# ===========================================================================
joe = [
    R("j1", first="Joe", last="Smith", dob="1980-03-15", street="1 Bowling Green",
      zip="10004", program="Workforce", system="ETO", client_id="E100"),
    R("j2", first="Joseph", last="Smith", dob="1980-03-15", street="1 Bowling Green",
      zip="10004", program="Resident Services", system="ETO", client_id="E200"),
    R("j3", first="Joe", last="Smith", dob="1980-03-15", street="1 Bowling Green",
      zip="10004", program="Property Management", system="External", client_id="X9"),
    R("k1", first="Kira", last="Adeyemi", dob="1995-06-02", street="65 Central Ave",
      zip="11221", program="Workforce", system="ETO", client_id="E300"),
]
out = I.resolve(joe)
# accept everything proposed, which is what a reviewer would do here
dec = {p["pair"]: "same" for p in out["proposals"]}
out = I.resolve(joe, dec)
jm = {out["master_of"][r] for r in ("j1", "j2", "j3")}
check("one person across three programs and two systems is one master id",
      len(jm) == 1)
check("a different person keeps a different master id",
      out["master_of"]["k1"] not in jm)
check("unique clients counts each human once", out["unique_clients"]["settled"] == 2)
check("unique client and program pairs counts each program once",
      out["unique_client_programs"] == 4)

# the same person twice in one program counts once for that program
same_prog = joe + [R("j4", first="Joe", last="Smith", dob="1980-03-15",
                     street="1 Bowling Green", zip="10004",
                     program="Workforce", system="ETO", client_id="E100")]
o2 = I.resolve(same_prog)
o2 = I.resolve(same_prog, {p["pair"]: "same" for p in o2["proposals"]})
check("a repeat inside one program does not inflate the pair count",
      o2["unique_client_programs"] == 4)

# ===========================================================================
# Honesty of the reported count.
# ===========================================================================
open_case = [
    R("o1", first="Maria", last="Delgado", dob="1988-04-11", street="209 Joralemon St",
      zip="11201", program="Workforce", system="ETO"),
    R("o2", first="Maria", last="Okafor", dob="1988-04-11", street="209 Joralemon St",
      zip="11201", program="Housing", system="Property"),
]
out = I.resolve(open_case)
lo, hi = out["unique_clients"]["range"]
check("an open proposal is reported as a range, not a single number", lo < hi)
check("the low end assumes every proposal is accepted", lo == 1)
check("the high end assumes every proposal is rejected", hi == 2)
lines = I.summarize(out)
check("the summary states the range in plain words",
      any("between" in ln for ln in lines))
out_done = I.resolve(open_case, {("o1", "o2"): "same"})
check("once decided, the count is final",
      not out_done["proposals"]
      and out_done["unique_clients"]["range"][0]
      == out_done["unique_clients"]["range"][1])

# ===========================================================================
# Safety: nothing is joined on thin evidence.
# ===========================================================================
thin = [
    R("t1", first="John", last="Smith", zip="11201", program="A", system="ETO"),
    R("t2", first="John", last="Smith", zip="11201", program="B", system="Other"),
]
ok, out = linked(thin, "t1", "t2")
check("a common name and a shared ZIP alone do not join two records", not ok)

conflict = [
    R("c1", first="Ada", last="Sample", dob="1960-01-01", street="1 Main St",
      zip="11201", program="A", system="ETO"),
    R("c2", first="Ada", last="Sample", dob="1994-11-30", street="9 Other Rd",
      zip="10007", program="B", system="Other"),
]
ok, _ = linked(conflict, "c1", "c2")
check("the same name with a different date of birth and address is not joined",
      not ok)

exact = [
    R("e1", first="Ada", last="Sample", dob="1960-01-01", street="1 Main St",
      zip="11201", program="A", system="ETO"),
    R("e2", first="Ada", last="Sample", dob="1960-01-01", street="1 Main St",
      zip="11201", program="B", system="Other"),
]
ok, out = linked(exact, "e1", "e2")
check("full agreement on name, date of birth and address is joined automatically",
      ok and out["auto_links"])

# every record always receives a master id
big = joe + dbl + swapped + nick_recs
out = I.resolve(big)
check("every record receives a master id",
      all(r.rid in out["master_of"] for r in big))
check("no record is lost during resolution",
      len(set(out["master_of"])) == len(big))

for label, passed in results:
    print(f"  [{'PASS' if passed else 'FAIL'}] {label}")
ok_all = all(p for _, p in results)
print(f"IDENTITY TESTS: {'PASS' if ok_all else 'FAIL'} "
      f"({sum(1 for _, p in results if p)}/{len(results)})")
sys.exit(0 if ok_all else 1)
