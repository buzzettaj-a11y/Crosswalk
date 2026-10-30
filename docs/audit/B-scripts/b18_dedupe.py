from _common import *
import dedupe_rules

def row(first, last, i, addr="10 Main St", zipc="11201", city="Brooklyn", **kw):
    d = dict(First=first, Last=last, ID=i, Addr=addr, Addr2="", City=city, State="NY", Zip=zipc)
    d.update(kw); return d

print("== 1. Tier-1 / same-ID rule across FILES (spec says: within one file) ==")
dfA = engine.clean_dataframe(pd.DataFrame([row("Maria","Lopez","1001")]).astype(str))
dfB = engine.clean_dataframe(pd.DataFrame([row("John","Chen","1001", addr="55 Oak Ave", zipc="11355", city="Queens")]).astype(str))
res = engine.run_pipeline({"A.csv": dfA, "B.csv": dfB}, {"A.csv": MAPPING, "B.csv": MAPPING}, False, None, 1337, None, None, None, None, True)
for r in res["transformed"]:
    print("  ", r["__source_file__"], r["Client_ID"], r["First_Name"], r["Last_Name"], "->", "REVIEW: " + "; ".join(r["__errors__"]) if r["__errors__"] else "CLEAN")

print("\n== 2. identical person key + same ID across two systems: second file's row is set aside ==")
dfA = engine.clean_dataframe(pd.DataFrame([row("Maria","Lopez","1001")]).astype(str))
dfB = engine.clean_dataframe(pd.DataFrame([row("Maria","Lopez","1001")]).astype(str))
res = engine.run_pipeline({"A.csv": dfA, "B.csv": dfB}, {"A.csv": MAPPING, "B.csv": MAPPING}, False, None, 1337, None, None, None, None, True)
for r in res["transformed"]:
    print("  ", r["__source_file__"], r["Client_ID"], "->", "REVIEW: " + "; ".join(r["__errors__"]) if r["__errors__"] else "CLEAN")

print("\n== 3. same ID, same name/address/ZIP/program but DIFFERENT date of birth: engine says 'identical record' ==")
schema = [dict(f) for f in engine.DEFAULT_SCHEMA] + [{"role":"custom","label":"DOB","dtype":"date","length":0,"required":False}]
mapping = dict(MAPPING); mapping["DOB"] = "DOB"
rows = [row("Maria","Lopez","1001", DOB="03/04/1990"), row("Maria","Lopez","1001", DOB="09/09/1955")]
res = pipeline(rows, schema=schema, mapping=mapping)
for r in res["transformed"]:
    print("  ", r["Client_ID"], r["__custom__"].get("DOB"), "->", "REVIEW: " + "; ".join(r["__errors__"]) if r["__errors__"] else "CLEAN")

print("\n== 4. same ID, different middle initial / suffix only ==")
rows = [dict(row("John","Smith","77"), Last="Smith"), dict(row("John","Smith Jr","77"))]
res = pipeline(rows)
for r in res["transformed"]:
    print("  ", r["Client_ID"], r["Last_Name"], "->", "REVIEW: " + "; ".join(r["__errors__"]) if r["__errors__"] else "CLEAN")

print("\n== 5. within-file rule: default fields First+Last+Zip group two different people ==")
frame = pd.DataFrame([
  dict(First="Maria",Last="Garcia",ID="1",Addr="10 Main St",Addr2="",City="Queens",State="NY",Zip="11373"),
  dict(First="Maria",Last="Garcia",ID="2",Addr="99 Other Ave",Addr2="",City="Queens",State="NY",Zip="11373"),
  dict(First="María",Last="García",ID="3",Addr="1 Third St",Addr2="",City="Queens",State="NY",Zip="11373"),
  dict(First="Ana-Maria",Last="Lopez",ID="4",Addr="1 Third St",Addr2="",City="Queens",State="NY",Zip="11373"),
  dict(First="Ana Maria",Last="Lopez",ID="5",Addr="2 Third St",Addr2="",City="Queens",State="NY",Zip="11373"),
  dict(First="O'Brien",Last="Pat",ID="6",Addr="2 Third St",Addr2="",City="Queens",State="NY",Zip="11373"),
  dict(First="OBrien",Last="Pat",ID="7",Addr="2 Third St",Addr2="",City="Queens",State="NY",Zip="11373"),
  dict(First="Wei",Last="Li",ID="8",Addr="2 Third St",Addr2="",City="Queens",State="NY",Zip="11373"),
  dict(First="Li",Last="Wei",ID="9",Addr="2 Third St",Addr2="",City="Queens",State="NY",Zip="11373"),
]).astype(str)
groups = dedupe_rules.find_groups(frame, {"First_Name":"First","Last_Name":"Last","Zip":"Zip"})
print("  groups (row positions):", list(groups.values()))

print("\n== 6. stale decision: a 'copies' decision made for 2 rows silently covers a third person added later ==")
base = pd.DataFrame([
  dict(First="Maria",Last="Garcia",ID="1",Addr="10 Main St",Addr2="",City="Queens",State="NY",Zip="11373"),
  dict(First="Maria",Last="Garcia",ID="1",Addr="10 Main St",Addr2="",City="Queens",State="NY",Zip="11373")]).astype(str)
fields = ["First_Name","Last_Name","Zip"]
pr = dedupe_rules.proposals(base, fields, MAPPING)
gid = pr["groups"][0]["gid"]
print("  group shown to the reviewer:", [r["row"] for r in pr["groups"][0]["rows"]], "gid", gid)
grown = pd.concat([base, pd.DataFrame([dict(First="Maria",Last="Garcia",ID="3",Addr="500 Far Ave",Addr2="",City="Queens",State="NY",Zip="11373")]).astype(str)], ignore_index=True)
f2 = grown.copy()
dedupe_rules.apply_decisions(f2, fields, MAPPING, {gid: "copies"})
print("  same gid after a third, different person is added:", pr["groups"][0]["gid"] == dedupe_rules.proposals(grown, fields, MAPPING)["groups"][0]["gid"])
print("  __dup_drop__ column:", list(f2["__dup_drop__"]))
