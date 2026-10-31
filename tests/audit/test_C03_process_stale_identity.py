"""C-03: the old app kept a cached identity after a file was excluded. Excluding a file and processing again now gives what a
fresh session would."""
import csv

from tests.fixtures.session.r_fixture import Clock
from tests.support.secrets import TEST_SECRET
from wholecount.engine.geo.backend import NoBackend
from wholecount.session import commands as C
from wholecount.session.runner import process
from wholecount.session.secret_store import InstallSecret
from wholecount.session.state import Session

COLS = ["Client_ID", "First_Name", "Last_Name", "DOB", "Address", "City", "State", "Zip", "Program"]
A = [("A1", "Maria", "Rodriguez", "1985-03-14", "100 Grand Concourse", "Bronx", "NY", "10451", "Housing"),
     ("A2", "Jordan", "Smith", "2015-06-01", "10 Oak St", "Brooklyn", "NY", "11201", "Youth"),
     ("A3", "Robert", "Smith", "1962-03-14", "20 Elm St", "Brooklyn", "NY", "11201", "Housing"),
     ("A4", "Ana", "Perez", "1990-05-06", "7 Elm St", "New York", "NY", "10013", "Workforce"),
     ("A5", "Luis", "Diaz", "1980-02-02", "123 45th St", "Queens", "NY", "11377", "Housing"),
     ("A6", "Carlos", "Vega", "1975-01-01", "5 A St", "New York", "NY", "10001", "Housing")]
B = [("B1", "Maria", "Rodriguez", "1985-03-14", "100 Grand Concourse", "Bronx", "NY", "10451", "Youth"),
     ("B2", "Jaden", "Smith", "2015-06-01", "10 Oak St", "Brooklyn", "NY", "11201", "Youth"),
     ("B3", "Robert", "Smith Jr", "1992-03-14", "20 Elm St", "Brooklyn", "NY", "11201", "Housing"),
     ("B4", "Ana", "Perez", "1990-06-05", "7 Elm St", "New York", "NY", "10013", "Workforce"),
     ("B5", "Luis", "Diaz", "1980-02-02", "123 45th Ave", "Queens", "NY", "11377", "Workforce"),
     ("B6", "Elena", "Vega", "1999-09-09", "6 B St", "New York", "NY", "10001", "Youth")]
CC = [("C1", "Dee", "Wu", "1988-08-08", "30 Pine St", "Brooklyn", "NY", "11201", "Youth"),
      ("C2", "Maria", "Rodriguez", "1985-03-14", "100 Grand Concourse", "Bronx", "NY", "10451", "Workforce"),
      ("C3", "Evan", "Cole", "1972-04-04", "8 Birch Rd", "Queens", "NY", "11377", "Housing")]


def write(path, rows):
    with open(path, "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(COLS)
        w.writerows(rows)
    return path


def session(paths):
    import datetime as dt
    return Session(InstallSecret(TEST_SECRET), paths, backend=NoBackend(), clock=Clock(), today=lambda: dt.date(2026, 10, 30),
                   getuser=lambda: "Joe")


def counts(s):
    c = s.counts()
    return (c.goal1.low, c.goal1.high), (c.goal2.low, c.goal2.high)


def test_exclude_a_file_and_process_again(tmp_path):
    a, b, c = write(tmp_path / "A.csv", A), write(tmp_path / "B.csv", B), write(tmp_path / "C.csv", CC)
    s = session([a, b, c])
    process(s)
    assert counts(s) == ((9, 13), (12, 15))
    s.history.execute(C.SetupChange("sources", str(c), False))
    assert s.stale
    process(s)
    assert counts(s) == ((7, 11), (9, 12))
    assert len([k for k, o in s.results.outcomes.items() if o.counted]) == 12
    fresh = session([a, b])
    process(fresh)
    assert fresh.results.digest() == s.results.digest()
