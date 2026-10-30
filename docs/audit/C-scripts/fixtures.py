"""Small hand-built fixtures with known truth, so the right Goal 1 / Goal 2 is known."""
import pandas as pd

COLS = ["Client_ID", "First_Name", "Last_Name", "DOB", "Address", "City", "State", "Zip", "Program"]


def df(rows):
    return pd.DataFrame(rows, columns=COLS)


def csv(rows):
    return df(rows).to_csv(index=False).encode()


# Each row: (id, first, last, dob, address, city, state, zip, program)
# TRUTH people are noted in comments.
A_ROWS = [
    # P1 Maria Rodriguez, in Housing here and Youth in B.csv: all four strong facts -> legit auto-link
    ("A1", "Maria", "Rodriguez", "1985-03-14", "100 Grand Concourse", "Bronx", "NY", "10451", "Housing"),
    # P2 Jordan Smith and P3 Jaden Smith are twins at one address
    ("A2", "Jordan", "Smith", "2015-06-01", "10 Oak St", "Brooklyn", "NY", "11201", "Youth"),
    # P4 Robert Smith Sr (b. 1962) and P5 Robert Smith Jr (b. 1992), same house
    ("A3", "Robert", "Smith", "1962-03-14", "20 Elm St", "Brooklyn", "NY", "11201", "Housing"),
    # P6 Ana Perez
    ("A4", "Ana", "Perez", "1990-05-06", "7 Elm St", "New York", "NY", "10013", "Workforce"),
    # P7 Luis Diaz
    ("A5", "Luis", "Diaz", "1980-02-02", "123 45th St", "Queens", "NY", "11377", "Housing"),
    # P8 Carlos Vega
    ("A6", "Carlos", "Vega", "1975-01-01", "5 A St", "New York", "NY", "10001", "Housing"),
]
B_ROWS = [
    ("B1", "Maria", "Rodriguez", "1985-03-14", "100 Grand Concourse", "Bronx", "NY", "10451", "Youth"),
    ("B2", "Jaden", "Smith", "2015-06-01", "10 Oak St", "Brooklyn", "NY", "11201", "Youth"),
    ("B3", "Robert", "Smith Jr", "1992-03-14", "20 Elm St", "Brooklyn", "NY", "11201", "Housing"),
    # same Ana Perez but DOB typed with day and month swapped (a probable typo)
    ("B4", "Ana", "Perez", "1990-06-05", "7 Elm St", "New York", "NY", "10013", "Workforce"),
    # a DIFFERENT Luis Diaz, same DOB by coincidence, lives at 123 45th AVE (other street in Queens)
    ("B5", "Luis", "Diaz", "1980-02-02", "123 45th Ave", "Queens", "NY", "11377", "Workforce"),
    # a different Carlos? no: Elena Vega, a relative
    ("B6", "Elena", "Vega", "1999-09-09", "6 B St", "New York", "NY", "10001", "Youth"),
]
TRUTH_PEOPLE = {
    "P1 Maria Rodriguez (A1,B1)": 1,
    "P2 Jordan Smith (A2)": 1, "P3 Jaden Smith (B2)": 1,
    "P4 Robert Smith Sr (A3)": 1, "P5 Robert Smith Jr (B3)": 1,
    "P6 Ana Perez (A4,B4)": 1,
    "P7 Luis Diaz 45th St (A5)": 1, "P7b Luis Diaz 45th Ave (B5)": 1,
    "P8 Carlos Vega (A6)": 1, "P9 Elena Vega (B6)": 1,
}
