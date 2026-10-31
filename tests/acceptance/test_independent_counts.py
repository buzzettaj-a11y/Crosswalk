"""An independent check of the downloaded files (SPEC 13.5). It reads only the files, with pandas, and imports nothing from
wholecount. The fixtures run the app and hand over the folder and the numbers Results shows, as plain integers.

Each file's source system comes from the `files` section of EXPECTED.json, which is plain JSON, because Final_Clean_Mapped
has no system column.
"""
import ast
import json
import pathlib
import re
import unicodedata

import pandas as pd
import pytest

ROOT = pathlib.Path(__file__).resolve().parents[2]
PLAN = json.loads((ROOT / "wholecount" / "sample_data" / "EXPECTED.json").read_text(encoding="utf-8"))
SYSTEMS = {name: f["system"] for name, f in PLAN["files"].items()}


def read(folder, stem):
    path = next(pathlib.Path(folder).glob(f"*{stem}.csv"))
    df = pd.read_csv(path, dtype=str, keep_default_na=False, encoding="utf-8-sig")
    return df.drop(columns=["PRACTICE"], errors="ignore")


def source_pairs(cell):
    """'B :: example_housing.xlsx / Clients :: 40; E :: ...' to [(file, row)], with the letter dropped."""
    return [tuple(part.split(" :: ")[1:]) for part in cell.split("; ") if part]


def fold(s):
    return " ".join(unicodedata.normalize("NFKD", s).encode("ascii", "ignore").decode().casefold().split())


def people(fcm, keep_apart=()):
    """The two automatic join reasons of P-ID-3 that apply with the saved crosswalk off, over Final_Clean_Mapped.
    same_system_id: one Client_ID inside one system, with surname, given name and birth date (when both have one) agreeing.
    four_exact_facts: birth date, surname, given name and address key (street, unit, ZIP) exactly equal after folding.
    keep_apart holds record keys of open copy groups, which the high end of Goal 1 counts as different people (SPEC 7.2)."""
    system = fcm["Source_File"].map(lambda f: SYSTEMS[f.split(" / ")[0]])
    first, last = fcm["First_Name"].map(fold), fcm["Last_Name"].map(fold)
    dob, cid, rk = fcm["Date_of_Birth"].str.strip(), fcm["Client_ID"].str.strip(), fcm["Record_Key"]
    addr = fcm["Address_1"].map(fold) + "|" + fcm["Address_2"].map(fold) + "|" + fcm["Zip"].str.strip()
    parent = list(range(len(fcm)))

    def find(i):
        while parent[i] != i:
            parent[i] = parent[parent[i]]
            i = parent[i]
        return i

    def join(a, b):
        if not ({rk[a], rk[b]} <= set(keep_apart) and rk[b] in fcm["Possible_Duplicate_Of"][a].split("; ")):
            parent[find(a)] = find(b)

    keyed = pd.DataFrame({"s": system, "c": cid})[cid != ""]
    for idx in keyed.groupby(["s", "c"]).groups.values():
        for a in idx:
            for b in idx:
                if a < b and last[a] == last[b] and first[a] == first[b] and (not dob[a] or not dob[b] or dob[a] == dob[b]):
                    join(a, b)
    full = (dob != "") & (last != "") & (first != "") & (fcm["Address_1"].str.strip() != "") & (fcm["Zip"].str.strip() != "")
    facts = pd.DataFrame({"d": dob, "l": last, "f": first, "a": addr})[full]
    for idx in facts.groupby(["d", "l", "f", "a"]).groups.values():
        for b in idx[1:]:
            join(idx[0], b)
    return len({find(i) for i in range(len(fcm))})


def program_groups(folder):
    """The confirmed program groups, from the PROGRAM lines of the shareable audit log."""
    log = next(pathlib.Path(folder).glob("*Shareable_Audit_Log.txt")).read_text(encoding="utf-8")
    return [set(re.findall(r'program_name="([^"]*)"', line)) for line in log.splitlines()
            if " PROGRAM " in line and 'reason_code="confirm"' in line]


RUNS = ("planned_run", "open_run", "different_run")


@pytest.fixture(params=RUNS)
def run(request):
    return request.getfixturevalue(request.param)


def test_the_three_row_files_add_up_to_rows_received(run):
    folder, numbers = run
    clean, review, aside = read(folder, "Final_Clean_Mapped"), read(folder, "Manual_Review_Needed"), read(folder, "Set_Aside_Records")
    received = read(folder, "Data_Quality_Report")["Rows_Received"].astype(int).sum()
    assert len(clean) + (review["Counted"] == "No").sum() + len(aside) == received == numbers["received"]
    assert received == PLAN["counts"]["after_decisions"]["rows_received"]


def test_counted_is_mapped_plus_counted_not_mapped(run):
    q = read(run[0], "Data_Quality_Report")
    n = {c: q[c].astype(int) for c in ("Counted", "Mapped", "Counted_Not_Mapped")}
    assert (n["Counted"] == n["Mapped"] + n["Counted_Not_Mapped"]).all()
    assert n["Counted"].sum() == len(read(run[0], "Final_Clean_Mapped"))


def test_unique_clients_is_the_high_end_of_goal_1(run):
    folder, numbers = run
    rows = len(read(folder, "Unique_Clients"))
    assert rows == numbers["goal1"][1]
    if numbers["open_pairs"] == 0 and numbers["open_copy_groups"] == 0:
        assert numbers["goal1"][0] == numbers["goal1"][1] == rows


def test_source_records_are_exactly_the_clean_rows(run):
    folder = run[0]
    clean = read(folder, "Final_Clean_Mapped")
    cited = [p for cell in read(folder, "Unique_Clients")["Source_Records"] for p in source_pairs(cell)]
    assert len(cited) == len(set(cited))
    assert set(cited) == set(zip(clean["Source_File"], clean["Source_Row"]))


def test_people_by_program_is_goal_2(run):
    folder, numbers = run
    by_program = read(folder, "Unique_Clients_By_Program")
    assert len(by_program[["Master_ID", "Program"]].drop_duplicates()) == len(by_program) == numbers["goal2"][1]


def test_each_program_is_among_its_records_programs(run):
    folder = run[0]
    clean = read(folder, "Final_Clean_Mapped")
    program_of = dict(zip(zip(clean["Source_File"], clean["Source_Row"]), clean["Program"]))
    groups = program_groups(folder)
    for _, row in read(folder, "Unique_Clients_By_Program").iterrows():
        theirs = {program_of[p] for p in source_pairs(row["Source_Records"])}
        same = set().union({row["Program"]}, *[g for g in groups if row["Program"] in g])
        assert theirs & same, row["Master_ID"]


def test_the_people_found_independently_are_the_high_end(open_run):
    """With pairs and copy groups open, the two join reasons find the high end of Goal 1."""
    folder, numbers = open_run
    clean = read(folder, "Final_Clean_Mapped")
    open_copies = clean.loc[clean["Duplicate_In_File"] == "Yes", "Record_Key"]
    assert numbers["open_pairs"] > 0 and numbers["open_copy_groups"] > 0
    assert people(clean, keep_apart=open_copies) == numbers["goal1"][1]


def test_with_everything_decided_different_goal_1_is_exact(different_run):
    folder, numbers = different_run
    assert numbers["open_pairs"] == numbers["open_copy_groups"] == 0
    assert people(read(folder, "Final_Clean_Mapped")) == numbers["goal1"][0] == numbers["goal1"][1]


def test_this_module_imports_nothing_from_wholecount():
    tree = ast.parse(pathlib.Path(__file__).read_text(encoding="utf-8"))
    names = [a.name for n in ast.walk(tree) if isinstance(n, ast.Import) for a in n.names]
    names += [n.module or "" for n in ast.walk(tree) if isinstance(n, ast.ImportFrom)]
    assert not [n for n in names if n.split(".")[0] in ("wholecount", "tests", "tools")]
