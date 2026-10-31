"""Writes the 19,000-row test set for the large-set acceptance test and the performance run (SPEC 15). A dev tool that never
ships, and the app never imports it.

    python tools/make_large_set.py --seed 20261030 --rows 19000 --files 15 --out DIR

It's deterministic: the same arguments write the same bytes. Every person is made up from the name lists below. The files
cover CSV, TSV, XLSX, JSON and XML with different column names, programs spelled several ways, nicknames and swapped
birth-date digits for some people, exact copies inside files, and a title above the header in some files. Addresses use
real NYC street names with plausible house numbers.

Beside the files it writes truth.json, which holds counts only (people planted, ambiguous records, copies, programs), and
fake_gazetteer.csv, the address list the fake geocoder places from in tests.
"""
import argparse
import csv
import datetime as dt
import io
import json
import pathlib
import random
import sys
import zipfile

FIRST = ("Aaron Abigail Adrian Aisha Alan Alicia Amara Andre Angela Anil Anthony Ariel Arjun Beatriz Benjamin Bianca Boris "
         "Caleb Camila Carmen Cedric Chloe Christopher Daniel Dalia Darius Deborah Devon Diego Dmitri Edwin Elena Elijah Elizabeth "
         "Emeka Esther Fatima Felix Fiona Gabriel Grace Hamza Hana Hector Imani Irene Isaac Ivan Jamal James Jasmine Javier Jennifer "
         "Joseph Joyce Julian Kamala Karen Kenji Kevin Lakshmi Laura Leon Lucia Malik Margaret Marisol Matthew Maya Michael Miriam "
         "Nadia Nathaniel Nia Nicholas Olga Omar Pamela Patricia Priya Rafael Rebecca Richard Robert Rosa Samuel Sandra Sofia "
         "Stephen Tamar Theodore Thomas Valeria Victor William Xiomara Yusuf Zainab").split()
LAST = ("Abara Acosta Adeyemi Agarwal Alvarez Anand Baptiste Barros Becker Bello Bergstrom Bianchi Brennan Burke Castillo "
        "Chandra Chen Cohen Coleman Cruz Dalton Delgado Diallo Dimitrov Duarte Dunn Ekwueme Ellison Espinal Farouk Fischer "
        "Fitzgerald Fonseca Gallagher Garcia Gill Goldberg Gomez Gordon Greco Guzman Haddad Hall Hernandez Hoffman Huang "
        "Ibrahim Ivanova Jaramillo Jensen Joseph Kaplan Kaur Khan Kim Kowalski Kruger Lam Lebedev Levine Lopez Lund Madsen "
        "Maldonado Mbeki Mendez Mehta Mishra Molina Moreau Murphy Nakamura Navarro Nguyen Novak Obi Okafor Oliveira Ortiz "
        "Osei Park Patel Pereira Petrov Quinn Rahman Ramirez Rao Reyes Rivera Romano Rossi Russo Saito Salazar Santos Schmidt "
        "Sharma Silva Sokolov Suarez Sullivan Tanaka Torres Tran Uddin Valdez Vargas Vasquez Volkov Walsh Wang Weiss Williams "
        "Wong Yamamoto Yilmaz Zamora Zhang").split()
NICKNAMES = {"Robert": "Bob", "William": "Bill", "Richard": "Dick", "James": "Jim", "Joseph": "Joe", "Michael": "Mike",
             "Thomas": "Tom", "Elizabeth": "Liz", "Margaret": "Peggy", "Patricia": "Pat", "Christopher": "Chris",
             "Nicholas": "Nick", "Matthew": "Matt", "Benjamin": "Ben", "Samuel": "Sam", "Daniel": "Dan", "Anthony": "Tony",
             "Stephen": "Steve", "Jennifer": "Jen", "Deborah": "Debbie", "Rebecca": "Becky", "Theodore": "Ted",
             "Abigail": "Abby", "Nathaniel": "Nate", "Pamela": "Pam", "Sandra": "Sandy"}
# (street, ZIP, city) on real NYC streets. House numbers are drawn from a plausible range for each.
STREETS = (("Broadway", "10025", "New York", 2600, 2900), ("Amsterdam Ave", "10024", "New York", 400, 600),
           ("Columbus Ave", "10025", "New York", 800, 1000), ("2nd Ave", "10003", "New York", 100, 200),
           ("Lenox Ave", "10027", "New York", 100, 400), ("St Nicholas Ave", "10032", "New York", 900, 1100),
           ("Atlantic Ave", "11217", "Brooklyn", 500, 700), ("Flatbush Ave", "11226", "Brooklyn", 2000, 2300),
           ("Nostrand Ave", "11216", "Brooklyn", 200, 400), ("Eastern Pkwy", "11213", "Brooklyn", 1100, 1400),
           ("Fulton St", "11238", "Brooklyn", 900, 1100), ("Myrtle Ave", "11205", "Brooklyn", 300, 600),
           ("Grand Concourse", "10451", "Bronx", 200, 600), ("Fordham Rd", "10458", "Bronx", 300, 600),
           ("Southern Blvd", "10459", "Bronx", 900, 1100), ("Tremont Ave", "10457", "Bronx", 1, 300),
           ("Queens Blvd", "11375", "Queens", 10000, 10800), ("Northern Blvd", "11372", "Queens", 7000, 9000),
           ("Roosevelt Ave", "11372", "Queens", 7000, 8500), ("Jamaica Ave", "11432", "Queens", 16000, 17000),
           ("Victory Blvd", "10301", "Staten Island", 1, 400), ("Richmond Ave", "10314", "Staten Island", 1400, 2000),
           ("Forest Ave", "10310", "Staten Island", 400, 900), ("Bay St", "10304", "Staten Island", 300, 700))
# One canonical program, then the spellings files use.
PROGRAMS = {"Housing Assistance": ("Housing Assistance", "Housing Asst."),
            "Summer Youth Employment Program": ("Summer Youth Employment Program", "SYEP"),
            "Workforce Development": ("Workforce Development", "Workforce Dev."),
            "Older Adult Services": ("Older Adult Services", "Older Adults"),
            "Youth Services": ("Youth Services",),
            "Food Pantry": ("Food Pantry", "Pantry")}
FORMATS = ("csv", "tsv", "xlsx", "json", "xml")
# Column names by format, from the styles the example files use (each auto-matches with no blockers).
COLUMNS = {
    "csv": ("Client ID", "First Name", "Last Name", "Date of Birth", "Address", "Apt", "City", "State", "ZIP", "Program"),
    "tsv": ("uid", "first", "last", "dob", "address_line", "apt", "city", "st", "zip", "program"),
    "xlsx": ("Client ID", "First Name", "Last Name", "Date of Birth", "Address", "Apt", "City", "State", "ZIP", "Program"),
    "json": ("id", "first_name", "last_name", "birth_date", "street", "unit", "city", "state", "zip", "program"),
    "xml": ("ClientNumber", "FirstName", "LastName", "BirthDate", "Street", "Apt", "City", "State", "Zip", "Program"),
}
TITLE = ("Client list export", "Prepared for the annual count")


def plan(seed, rows, files):
    """Every file's records, as tuples in COLUMNS order, and the truth counts."""
    rnd = random.Random(seed)
    names = [f"{FORMATS[i % len(FORMATS)]}_{i + 1:02d}" for i in range(files)]
    spelling = {n: {canon: rnd.choice(sp) for canon, sp in PROGRAMS.items()} for n in names}
    records = {n: [] for n in names}
    ids = {n: 0 for n in names}
    seen = set()
    people = ambiguous = 0
    copies_target = rows // 100
    while sum(len(v) for v in records.values()) < rows - copies_target:
        first, last = rnd.choice(FIRST), rnd.choice(LAST)
        dob = dt.date(1940, 1, 1) + dt.timedelta(days=rnd.randrange(25000))
        street, zip5, city, lo, hi = rnd.choice(STREETS)
        house = str(rnd.randrange(lo, hi))
        if (first, last, dob, house, street) in seen:
            continue
        seen.add((first, last, dob, house, street))
        people += 1
        unit = rnd.choice(("", "", "", f"Apt {rnd.randrange(1, 20)}{rnd.choice('ABCDEFG')}"))
        k = rnd.choices((1, 2, 3), (60, 30, 10))[0]
        program = rnd.choice(tuple(PROGRAMS))
        for j, n in enumerate(rnd.sample(names, k)):
            f, d = first, dob
            if j == k - 1 and k > 1 and rnd.random() < 0.03:
                if first in NICKNAMES:
                    f = NICKNAMES[first]
                else:
                    swapped = _swap_digits(dob)
                    if swapped is None:
                        f = first
                    else:
                        d = swapped
                ambiguous += (f, d) != (first, dob)
            ids[n] += 1
            cid = f"{n[:1].upper()}{n[-2:]}-{ids[n]:05d}"
            records[n].append((cid, f, last, d.isoformat(), f"{house} {street}", unit, city, "NY", zip5,
                               spelling[n][program] if rnd.random() < 0.9 else spelling[n][rnd.choice(tuple(PROGRAMS))]))
    copies = rows - sum(len(v) for v in records.values())     # exact copies inside files make up the rest
    for i, n in enumerate(sorted(records)):
        recs = records[n]
        for _ in range(copies // files + (1 if i < copies % files else 0)):
            recs.insert(rnd.randrange(len(recs) + 1), recs[rnd.randrange(len(recs))])
    truth = {"seed": seed, "files": files, "rows": sum(len(v) for v in records.values()), "people_planted": people,
             "ambiguous_records": ambiguous, "identical_copies": copies, "programs": len(PROGRAMS),
             "program_spellings": len({s for v in spelling.values() for s in v.values()}),
             "titled_files": sum(1 for n in names if _titled(n))}
    return names, records, truth


def _swap_digits(d):
    """The day's two digits swapped (12 to 21), when that is a different real date."""
    a, b = f"{d.day:02d}"
    try:
        out = d.replace(day=int(b + a))
    except ValueError:
        return None
    return out if out != d else None


def _titled(name):
    return name.startswith("csv") and name.endswith(("01", "11"))


def write_csv(path, cols, recs, delimiter, titled):
    buf = io.StringIO()
    w = csv.writer(buf, delimiter=delimiter, lineterminator="\n")
    if titled:
        for t in TITLE:
            w.writerow([t])
    w.writerow(cols)
    w.writerows(recs)
    path.write_bytes(buf.getvalue().encode("utf-8"))


def write_json(path, cols, recs):
    out = [{cols[0]: r[0], cols[1]: r[1], cols[2]: r[2], cols[3]: r[3],
            "address": {cols[4]: r[4], cols[5]: r[5], cols[6]: r[6], cols[7]: r[7], cols[8]: r[8]}, cols[9]: r[9]}
           for r in recs]
    path.write_text(json.dumps({"clients": out}, indent=1) + "\n", encoding="utf-8")


def _esc(s):
    return s.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


def write_xml(path, cols, recs):
    parts = ["<?xml version='1.0' encoding='UTF-8'?>", "<clients>"]
    for r in recs:
        parts.append("  <client>" + "".join(f"<{c}>{_esc(v)}</{c}>" for c, v in zip(cols, r)) + "</client>")
    parts.append("</clients>")
    path.write_text("\n".join(parts) + "\n", encoding="utf-8")


def write_xlsx(path, cols, recs):
    """A one-sheet workbook with inline strings and a fixed timestamp, so the bytes don't change between runs."""
    def cell(ref, v):
        return f'<c r="{ref}" t="inlineStr"><is><t>{_esc(v)}</t></is></c>'

    def col(i):
        s = ""
        i += 1
        while i:
            i, r = divmod(i - 1, 26)
            s = chr(65 + r) + s
        return s
    rows = [cols] + list(recs)
    sheet = ['<?xml version="1.0" encoding="UTF-8" standalone="yes"?>',
             '<worksheet xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main"><sheetData>']
    for i, r in enumerate(rows, start=1):
        sheet.append(f'<row r="{i}">' + "".join(cell(f"{col(j)}{i}", v) for j, v in enumerate(r)) + "</row>")
    sheet.append("</sheetData></worksheet>")
    files = {
        "[Content_Types].xml": '<?xml version="1.0" encoding="UTF-8" standalone="yes"?><Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types"><Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/><Default Extension="xml" ContentType="application/xml"/><Override PartName="/xl/workbook.xml" ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet.main+xml"/><Override PartName="/xl/worksheets/sheet1.xml" ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.worksheet+xml"/></Types>',  # noqa: E501
        "_rels/.rels": '<?xml version="1.0" encoding="UTF-8" standalone="yes"?><Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships"><Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/officeDocument" Target="xl/workbook.xml"/></Relationships>',  # noqa: E501
        "xl/workbook.xml": '<?xml version="1.0" encoding="UTF-8" standalone="yes"?><workbook xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main" xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships"><sheets><sheet name="Clients" sheetId="1" r:id="rId1"/></sheets></workbook>',  # noqa: E501
        "xl/_rels/workbook.xml.rels": '<?xml version="1.0" encoding="UTF-8" standalone="yes"?><Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships"><Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/worksheet" Target="worksheets/sheet1.xml"/></Relationships>',  # noqa: E501
        "xl/worksheets/sheet1.xml": "".join(sheet),
    }
    with zipfile.ZipFile(path, "w", zipfile.ZIP_DEFLATED) as z:
        for name, text in files.items():
            info = zipfile.ZipInfo(name, (2026, 10, 30, 0, 0, 0))
            info.compress_type = zipfile.ZIP_DEFLATED
            z.writestr(info, text)


def gazetteer(records):
    """Every address in the set, placed at a made-up point inside its borough, for the fake geocoder."""
    centers = {"New York": (40.78, -73.97), "Brooklyn": (40.65, -73.95), "Bronx": (40.85, -73.89), "Queens": (40.73, -73.82),
               "Staten Island": (40.60, -74.12)}
    seen = {}
    for recs in records.values():
        for r in recs:
            house, street = r[4].split(" ", 1)
            seen[(house, street, r[8])] = r[6]
    buf = io.StringIO()
    w = csv.writer(buf, lineterminator="\n")
    w.writerow(("house", "street", "zip", "borough", "lat", "lon", "senate", "assembly", "council", "tract", "grc"))
    for i, ((house, street, zip5), city) in enumerate(sorted(seen.items())):
        lat, lon = centers[city]
        w.writerow((house, street, zip5, "Manhattan" if city == "New York" else city, f"{lat + (i % 97) / 10000:.6f}",
                    f"{lon + (i % 89) / 10000:.6f}", "", "", "", "", "00"))
    return buf.getvalue()


def write_set(seed, rows, files, out):
    out = pathlib.Path(out)
    out.mkdir(parents=True, exist_ok=True)
    names, records, truth = plan(seed, rows, files)
    for n in names:
        fmt = n.split("_")[0]
        cols, recs = COLUMNS[fmt], records[n]
        path = out / f"{n}.{fmt}"
        if fmt in ("csv", "tsv"):
            write_csv(path, cols, recs, "," if fmt == "csv" else "\t", _titled(n))
        elif fmt == "json":
            write_json(path, cols, recs)
        elif fmt == "xml":
            write_xml(path, cols, recs)
        else:
            write_xlsx(path, cols, recs)
    (out / "truth.json").write_text(json.dumps(truth, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    (out / "fake_gazetteer.csv").write_text(gazetteer(records), encoding="utf-8")
    return truth


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--seed", type=int, default=20261030)
    ap.add_argument("--rows", type=int, default=19000)
    ap.add_argument("--files", type=int, default=15)
    ap.add_argument("--out", required=True)
    a = ap.parse_args(argv)
    truth = write_set(a.seed, a.rows, a.files, a.out)
    for k in sorted(truth):
        print(f"{k} {truth[k]}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
