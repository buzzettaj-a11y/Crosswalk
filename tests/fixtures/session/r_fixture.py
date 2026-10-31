"""The R and S fixture for M08 (made-up people). R.csv is one system with 15 rows, S.csv a second with 2."""
import csv
import datetime as dt

from tests.support.secrets import TEST_SECRET
from wholecount.engine.geo.reference import ReferenceBackend
from wholecount.session.secret_store import InstallSecret
from wholecount.session.state import Session

HEADER = ["Client_ID", "First_Name", "Last_Name", "DOB", "Address_1", "City", "State", "Zip", "Program"]
CLEAN = [("R01", "Ada", "Lee", "1980-01-01", "Housing"), ("R02", "Ben", "Cruz", "1981-02-02", "Housing"),
         ("R03", "Cara", "Diaz", "1982-03-03", "Youth"), ("R04", "Dev", "Rao", "1983-04-04", "Youth"),
         ("R05", "Eli", "Fox", "1984-05-05", "Workforce"), ("R06", "Fay", "Gil", "1985-06-06", "Workforce")]


def r_rows():
    rows = [[cid, f, l, dob, f"{10 + 2 * i} Oak St", "Brooklyn", "NY", "11201", p] for i, (cid, f, l, dob, p) in enumerate(CLEAN)]
    gus = ["R07", "Gus", "Hall", "1986-07-07", "22 Oak St", "Brooklyn", "NY", "11201", "Housing"]
    rows += [gus, list(gus)]
    rows += [["R09", "Hana", "Ito", "1987-08-08", "24 Oak St", "Brooklyn", "NY", "11201", "Youth"],
             ["R10", "HANA", "ITO", "1987-08-08", "24 Oak St", "Brooklyn", "NY", "11201", "Youth"],
             ["R11", "Ivy", "Jones", "1988-09-09", "26 Oak St", "Brooklyn", "NY", "11201", "Housing"],
             ["R11", "Jon", "Kane", "1975-10-10", "28 Oak St", "Brooklyn", "NY", "11201", "Housing"],
             ["R13", "Kim", "Lu", "1989-11-11", "85 Montague St", "Brooklyn", "NY", "", "Workforce"],
             ["R14", "", "Moss", "1990-12-12", "30 Oak St", "Brooklyn", "NY", "11201", "Youth"],
             ["", "Total", "", "", "", "", "", "", ""]]
    return rows


def s_rows():
    return [["S1", "Ada", "Lee", "1980-01-01", "10 Oak St", "Brooklyn", "NY", "11201", "Housing"],
            ["S2", "Ben", "Cruz", "1981-02-02", "99 Elm St", "Brooklyn", "NY", "11201", "Housing"]]


GAZETTEER = [(str(n), "Oak St", "11201", "Brooklyn", 40.690 + n / 10000, -73.990) for n in (10, 12, 14, 16, 22, 24, 26, 28, 30)]
GAZETTEER += [("85", "Montague St", "11201", "Brooklyn", 40.6940, -73.9930), ("99", "Elm St", "11201", "Brooklyn", 40.6950, -73.9800)]


def write(path, rows, header=HEADER):
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(header)
        w.writerows(rows)
    return path


def reference():
    text = "house_number,street,zip,borough,latitude,longitude\n" + "\n".join(",".join(map(str, g)) for g in GAZETTEER) + "\n"
    return ReferenceBackend.from_text(text)


class Clock:
    """An injected clock that moves one second per reading, so decisions are ordered."""

    def __init__(self):
        self.t = dt.datetime(2026, 10, 30, 12, 0, 0, tzinfo=dt.timezone.utc)

    def __call__(self):
        self.t += dt.timedelta(seconds=1)
        return self.t


def files(tmp_path, r=None, s=None):
    return [write(tmp_path / "R.csv", r or r_rows()), write(tmp_path / "S.csv", s or s_rows())]


def session(tmp_path, backend=None, paths=None, **kw):
    s = Session(InstallSecret(TEST_SECRET), paths or files(tmp_path), backend=backend or reference(), clock=Clock(),
                today=lambda: dt.date(2026, 10, 30), getuser=lambda: "Joe", **kw)
    return s
