from _common import *
df = pd.DataFrame({"First":["Ana"]*8, "Last":["Lopez"]*8, "ID":[f"A{i}" for i in range(8)],
                   "Addr":["10 Main St"]*8, "City":["Brooklyn"]*8, "State":["NY"]*8,
                   "Zip":["112019","11201 7","1120","11201-12","123456789012","1 1 2 0 1","11201abc","99999-0000"]})
out = engine.op_calc_zip(df, "Addr", "City", "Zip", "blanks")
print(out[["Zip","Zip_calculated","Zip_calculated_note"]].to_string())
# now push through the pipeline with the calculated column mapped to Zip, exactly as guess_mapping does
cols = list(out.columns)
m = engine.guess_mapping(cols)
print("guess_mapping picks Zip ->", m["Zip"])
mapping = dict(MAPPING); mapping["Zip"] = m["Zip"]
res = engine.run_pipeline({"t.csv": out}, {"t.csv": mapping}, False, None, 1337, None, None, None, None, True)
for raw, r in zip(df["Zip"], res["transformed"]):
    print(f"typed ZIP {raw!r:16} -> stored Zip={r['Zip']!r:8}", "REVIEW: " + "; ".join(r["__errors__"]) if r["__errors__"] else "CLEAN")
