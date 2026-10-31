"""Builds the calibration population (M13): 1,000 person rows in two systems, with known true matches and degraded copies
across all four score bands. Test code, so it may use random.Random(7); the engine never does. Every value is made up.

    python -m tests.fixtures.calibration.make_population    writes people_a.csv, people_b.csv and known_pairs.txt here
"""
import csv
import pathlib
import random

HERE = pathlib.Path(__file__).resolve().parent
COLS = ["Client_ID", "First_Name", "Last_Name", "DOB", "Address", "City", "State", "Zip", "Program"]
GIVEN = ["Amara", "Bastian", "Celia", "Dorian", "Elsa", "Fennick", "Greta", "Hollis", "Ines", "Jasper", "Kaia", "Lorcan",
         "Mirela", "Nolan", "Odessa", "Pascal", "Quilla", "Rowan", "Saskia", "Tobin", "Ulla", "Viggo", "Wren", "Ximena",
         "Yorick", "Zelda", "Robert", "William", "Elizabeth", "Katherine", "Margaret", "Charles", "Thomas", "Jennifer"]
NICK = {"Robert": "Bob", "William": "Bill", "Elizabeth": "Liz", "Katherine": "Kate", "Margaret": "Peggy", "Charles": "Chuck",
        "Thomas": "Tom", "Jennifer": "Jenny"}
SURNAMES = [f"{a}{b}" for a in ("Var", "Holm", "Quen", "Tarr", "Lund", "Brask", "Ostr", "Mell", "Penn", "Zorr", "Kell",
                                "Davr", "Fenn", "Grob", "Ivar", "Jatt")
            for b in ("ington", "quist", "ovic", "ader", "ebrook", "ston", "elli", "wright")]
STREETS = ["Maple Ave", "Birch Rd", "Cedar Pl", "Willow St", "Aspen Ct", "Linden Blvd", "Hazel Ln", "Juniper Way"]
ZIPS = [("Bronx", "10451"), ("Brooklyn", "11201"), ("Queens", "11372"), ("New York", "10027"), ("Staten Island", "10301")]
PROGRAMS = ["Housing", "Youth", "Workforce"]
N_PEOPLE = 500


def _person(rng, i):
    city, z = rng.choice(ZIPS)
    return {"First_Name": rng.choice(GIVEN), "Last_Name": SURNAMES[i % len(SURNAMES)],
            "DOB": f"{rng.randint(1940, 2010)}-{rng.randint(1, 12):02d}-{rng.randint(1, 28):02d}",
            "Address": f"{rng.randint(1, 999)} {rng.choice(STREETS)}", "City": city, "State": "NY", "Zip": z,
            "Program": rng.choice(PROGRAMS)}


def _swap_md(dob):
    y, m, d = dob.split("-")
    return f"{y}-{d}-{m}" if int(d) <= 12 and d != m else f"{y}-{m}-{int(d) % 28 + 1:02d}"


def build(seed=7):
    """(rows of system A, rows of system B, true pairs as (A id, B id))."""
    rng = random.Random(seed)
    a_rows, b_rows, truth = [], [], []
    people = [_person(rng, i) for i in range(N_PEOPLE)]
    for i, p in enumerate(people):
        a_rows.append({"Client_ID": f"PA{i:04d}", **p})
    kinds = ["exact", "moved", "near_dob", "nickname", "new_address", "other_person", "other_person", "relative"]
    for i, p in enumerate(people):
        kind = kinds[i % len(kinds)]
        q = dict(p)
        if kind == "exact":                     # all four facts: an automatic join
            pass
        elif kind == "moved":                   # same name and DOB, new address in the same ZIP: band 4
            q["Address"] = f"{rng.randint(1000, 1999)} {rng.choice(STREETS)}"
        elif kind == "near_dob":                # month and day swapped or one off: band 3
            q["DOB"] = _swap_md(p["DOB"])
            q["Address"] = f"{rng.randint(1000, 1999)} {rng.choice(STREETS)}"
        elif kind == "nickname":                # a nickname, same DOB, new address
            q["First_Name"] = NICK.get(p["First_Name"], p["First_Name"][:1])
            q["Address"] = f"{rng.randint(1000, 1999)} {rng.choice(STREETS)}"
        elif kind == "new_address":             # same name and DOB, other ZIP
            city, z = rng.choice([x for x in ZIPS if x[1] != p["Zip"]])
            q.update({"Address": f"{rng.randint(1, 999)} {rng.choice(STREETS)}", "City": city, "Zip": z})
        elif kind == "other_person":            # someone else with the same surname at the same address: not a match
            q = _person(rng, i)
            q.update({"Last_Name": p["Last_Name"], "Address": p["Address"], "City": p["City"], "Zip": p["Zip"]})
        elif kind == "relative":                # same surname and birth year, other given name: not a match
            q = _person(rng, i)
            q.update({"Last_Name": p["Last_Name"], "DOB": p["DOB"][:4] + q["DOB"][4:], "Zip": p["Zip"]})
        b_rows.append({"Client_ID": f"PB{i:04d}", **q})
        if kind not in ("other_person", "relative"):
            truth.append((f"PA{i:04d}", f"PB{i:04d}"))
    return a_rows, b_rows, truth


def write(folder=HERE, seed=7):
    folder = pathlib.Path(folder)
    a_rows, b_rows, truth = build(seed)
    for name, rows in (("people_a.csv", a_rows), ("people_b.csv", b_rows)):
        with open(folder / name, "w", newline="", encoding="utf-8") as f:
            w = csv.DictWriter(f, COLS)
            w.writeheader()
            w.writerows(rows)
    with open(folder / "known_pairs.txt", "w", encoding="utf-8") as f:
        f.write("# Three known pairs to enter on Known pairs: system, Client_ID, system, Client_ID. Made-up records.\n")
        for a, b in truth[:3]:
            f.write(f"people_a {a} people_b {b}\n")
    return folder / "people_a.csv", folder / "people_b.csv"


if __name__ == "__main__":
    write()
