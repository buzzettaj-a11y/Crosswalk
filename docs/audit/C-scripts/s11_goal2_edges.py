"""
s11: Goal 2 edge cases.
 a) file with no program column and no default
 b) same person twice in one program across two files
 c) program spellings grouped, then ungrouped
 d) blank program values (with and without a default)
 e) case-only spelling differences when the Programs screen is never opened (API / fast path)
 f) the 'no program' counter counts records, not people
"""
from invariants import *
import pandas as pd

H = ["Client_ID", "First_Name", "Last_Name", "DOB", "Address", "City", "State", "Zip", "Program"]


def mk(rows, cols=H):
    return pd.DataFrame(rows, columns=cols).to_csv(index=False).encode()


A = mk([
    ["A1", "Ana", "Perez", "1990-05-06", "7 Elm St", "New York", "NY", "10013", "Workforce Development"],
    ["A2", "Bo", "Lee", "1991-01-01", "8 Elm St", "New York", "NY", "10013", "Youth"],
    ["A3", "Cy", "Kim", "1992-02-02", "9 Elm St", "New York", "NY", "10013", ""],          # blank program
])
B = mk([
    ["B1", "Ana", "Perez", "1990-05-06", "7 Elm St", "New York", "NY", "10013", "Workforce Dev."],   # same person, same program, other spelling
    ["B2", "Bo", "Lee", "1991-01-01", "8 Elm St", "New York", "NY", "10013", "youth"],               # same person, same program, case only
    ["B3", "Cy", "Kim", "1992-02-02", "9 Elm St", "New York", "NY", "10013", "Housing"],            # Cy is in Housing here
])
# C has no program column at all
C = mk([
    ["C1", "Di", "Ruiz", "1993-03-03", "10 Elm St", "New York", "NY", "10013"],
    ["C2", "Bo", "Lee", "1991-01-01", "8 Elm St", "New York", "NY", "10013"],
], cols=H[:-1])

print("TRUTH: people = Ana, Bo, Cy, Di = 4.  Programs: Ana{Workforce Development}, Bo{Youth}, Cy{Housing}, Di{none}")
print("       Goal 1 = 4.  Goal 2 = Ana 1 + Bo 1 + Cy 1 = 3 (Cy's blank row has no program, Di has none)")

# e) never open the Programs screen (API / fast path)
reset(); upload({"A.csv": A, "B.csv": B, "C.csv": C}); set_schema(dob=True); run()
s = summary(True)
print("\n(e) Programs screen never opened:", counts_line(True))
print("    per-program:", s["goal2"]["totals"])
print("    aliases in force:", cw.S["program_aliases"], "| groups:", cw.S["program_groups"] is None)
print("    Unique_Clients_By_Program:\n", export_df("unique_by_program")[["Master_ID", "Program", "First_Name"]].to_string())

# opening the Programs screen builds the proposal; then a re-run uses it
ui("programs")
print("\n    aliases after the Programs screen was opened:", cw.S["program_aliases"])
run()
s = summary(True)
print("    re-run:", counts_line(True))
print("    per-program:", s["goal2"]["totals"])

# f) no_program counts records
print("\n(f) goal2.no_program =", s["goal2"]["no_program"], "(records without a program; people without ANY program: Di only = 1)")

# a) + d) file C: nothing; then with a default
client.post("/api/sources/default", json={"key": [t for t in tables() if t["file"] == "C.csv"][0]["key"],
                                           "field": "Program", "value": "Youth"})
run()
print("\n(d) default 'Youth' for C.csv:", counts_line(True))
print("    per-program:", summary(True)["goal2"]["totals"])

# c) group, then ungroup
pg = ui("programs")["programs"]
print("\n(c) groups proposed:", [(g["canonical"], [v["name"] for v in g["variants"]]) for g in pg["groups"]])
# take 'Workforce Dev.' out on its own
r = client.post("/api/programs/group", json={"name": "Workforce Dev.", "into": "__alone__"})
print("    after un-grouping 'Workforce Dev.' (no re-run yet):", counts_line(True))
print("    stale-summary check: per-program still", summary(True)["goal2"]["totals"])
run()
print("    after re-run:", counts_line(True), summary(True)["goal2"]["totals"])
