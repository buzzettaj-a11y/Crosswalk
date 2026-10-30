"""Deterministic messy 3-file fixture that produces every review group and several duplicate kinds."""
import random
import pandas as pd

COLS = ["Client_ID", "First_Name", "Last_Name", "DOB", "Address", "City", "State", "Zip", "Program"]
FIRST = ["Ada", "Ben", "Cara", "Devi", "Evan", "Faye", "Gus", "Hana", "Ivo", "Jae", "Kira", "Leo",
         "Mira", "Nate", "Opal", "Pia", "Quinn", "Rex", "Sena", "Tomas"]
LAST = ["Alvarez", "Brown", "Chen", "Diaz", "Evans", "Fox", "Gupta", "Hill", "Ito", "Jones"]
ADDR = [("125 Worth St", "New York", "10013"), ("851 Grand Concourse", "Bronx", "10451"),
        ("209 Joralemon St", "Brooklyn", "11201"), ("40-22 24th St", "Queens", "11101"),
        ("10 Richmond Terrace", "Staten Island", "10301"), ("360 Adams St", "Brooklyn", "11201"),
        ("2488 Grand Concourse", "Bronx", "10458")]
PROGS = ["Housing", "Youth", "Workforce", "Older Adult Services"]


def person(i):
    f = FIRST[i % len(FIRST)]
    l = LAST[(i // len(FIRST)) % len(LAST)]
    a = ADDR[(i * 3 + i // 7) % len(ADDR)]
    dob = f"{1950 + (i * 7) % 50}-{1 + i % 12:02d}-{1 + (i * 5) % 28:02d}"
    return f, l, a, dob


def make(seed=11, missing=False, summary=False):
    rnd = random.Random(seed)
    A, B, C = [], [], []
    # --- File A: 40 clean people with IDs A001.. (some in two programs through repeated IDs is avoided)
    for i in range(40):
        f, l, (st, c, z), dob = person(i)
        A.append([f"A{i:03d}", f, l, dob, st, c, "NY", z, PROGS[i % 4]])
    # --- File B: the first 15 people again (cross-file, same person) with different IDs and program
    for i in range(15):
        f, l, (st, c, z), dob = person(i)
        B.append([f"B{i:03d}", f, l, dob, st, c, "NY", z, PROGS[(i + 1) % 4]])
    # 15 more new people in B
    for i in range(40, 55):
        f, l, (st, c, z), dob = person(i)
        B.append([f"B{i:03d}", f, l, dob, st, c, "NY", z, PROGS[i % 4]])
    # --- File C: a third system, new people, plus the problem rows
    for i in range(60, 75):
        f, l, (st, c, z), dob = person(i)
        C.append([f"C{i:03d}", f, l, dob, st, c, "NY", z, PROGS[i % 4]])
    # problem rows in A
    A.append(["A900", "Zed", "Zimmer", "1970-01-01", "1 Test St", "Brooklyn", "NY", "", "Housing"])        # zipbad (blank zip)
    A.append(["A901", "Yan", "Young", "1971-01-01", "2 Test St", "", "NY", "", "Housing"])                 # zipcity
    A.append(["A902", "Xi", "Xu", "1972-01-01", "3 Test St", "Queens", "NY", "10451", "Housing"])          # conflict (Queens vs Bronx ZIP)
    if missing:
        A.append(["A903", "", "Wong", "1973-01-01", "4 Test St", "Brooklyn", "NY", "11201", "Housing"])    # missing first name
    A.append(["A904", "Vic", "Voss", "1974-01-01", "", "Brooklyn", "NY", "11201", "Housing"])              # no address
    if summary:
        A.append(["", "TOTAL", "", "", "", "", "", "", ""])                                                 # summary row
    # exact duplicate (same ID, identical) in A: confirmed duplicate
    A.append(list(A[3]))
    A.append(list(A[3]))
    # within-file possible duplicates (same first/last/zip, different ID)
    f, l, (st, c, z), dob = person(5)
    A.append(["A950", f, l, dob, st, c, "NY", z, PROGS[1]])
    # B: an ID that collides with A's ID but is a different person (cross-file ID reuse)
    B.append(["A010", "Collide", "Person", "1999-09-09", "77 Test Ave", "Bronx", "NY", "10451", "Youth"])
    # C: person duplicated across files with same program as A (possible duplicate across files)
    f, l, (st, c, z), dob = person(2)
    C.append(["C990", f, l, dob, st, c, "NY", z, PROGS[2 % 4]])
    return {"A.csv": rows(A), "B.csv": rows(B), "C.csv": rows(C)}


def rows(r):
    return pd.DataFrame(r, columns=COLS).to_csv(index=False).encode()
