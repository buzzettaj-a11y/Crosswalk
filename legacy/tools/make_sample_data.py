"""
Generate fake, obviously-not-real sample input files that exercise the tool's
features (jammed addresses, embedded units, missing city, duplicates, mixed
formats). No real client data is used. Run: python make_sample_data.py
"""
import csv, json, os, random
from xml.sax.saxutils import escape
import openpyxl

random.seed(7)
OUT = "sample_data"
os.makedirs(OUT, exist_ok=True)

FIRST = ["Ada","Ben","Cara","Devi","Evan","Faye","Gus","Hana","Ivo","Jae","Kira",
         "Leo","Mira","Nate","Opal","Pia","Quinn","Rex","Sena","Tomas","Uma","Vik"]
LAST  = ["Sample","Placeholder","Example","Testcase","Demo","Fixture","Mock",
         "Draft","Proxy","Stub","Trial","Dummy"]
PROG  = ["Older Adult Services","Housing","Workforce","Youth"]

# Internally consistent (street, borough, ZIP) so ZIP and city agree.
ADDR = [
    ("125 Worth St","New York","10013"),
    ("1 Bowling Green","New York","10004"),
    ("851 Grand Concourse","Bronx","10451"),
    ("2488 Grand Concourse","Bronx","10458"),
    ("209 Joralemon St","Brooklyn","11201"),
    ("360 Adams St","Brooklyn","11201"),
    ("118 Nassau Ave","Brooklyn","11222"),
    ("40-22 24th St","Queens","11101"),
    ("30-30 Northern Blvd","Queens","11101"),
    ("10 Richmond Terrace","Staten Island","10301"),
]
UNITS = ["Apt 4B","#3L","Suite 200","Fl 3","Unit 5","Penthouse",""]

def person(i):
    return FIRST[i % len(FIRST)], LAST[(i // len(FIRST)) % len(LAST)]

def addr(i):
    return ADDR[i % len(ADDR)]

def unit(i):
    return UNITS[i % len(UNITS)]

# ---- 1) clinic_export.csv: jammed name + fully jammed address, no ID column ----
with open(f"{OUT}/clinic_export.csv", "w", newline="") as f:
    w = csv.writer(f); w.writerow(["Name", "Full_Address"])
    for i in range(60):
        fn, ln = person(i); st, boro, z = addr(i); u = unit(i)
        full = f"{st} {u} {boro} NY {z}".replace("  ", " ").strip()
        w.writerow([f"{fn} {ln}", full])
    # two exact duplicates (same jammed line)
    w.writerow(["Ada Sample", "125 Worth St New York NY 10013"])
    w.writerow(["Ada Sample", "125 Worth St New York NY 10013"])

# ---- 2) portal_export.json: separate columns, some missing city ----
recs = []
for i in range(50):
    fn, ln = person(i + 3); st, boro, z = addr(i + 1)
    city = "" if i % 6 == 0 else boro     # some rows missing city (ZIP will fill)
    recs.append({"Name": f"{fn} {ln}", "Address": st, "City": city,
                 "State": "NY" if i % 5 else "", "Zip_Code": z})
json.dump(recs, open(f"{OUT}/portal_export.json", "w"), indent=2)

# ---- 3) legacy_export.xlsx: split name, has ID, # units, some missing ZIP ----
wb = openpyxl.Workbook(); ws = wb.active; ws.title = "Sheet1"
ws.append(["FirstName","MI","LastName","PatientNumber","Addr1","Addr2","City","State","ZipCode"])
for i in range(55):
    fn, ln = person(i + 5); st, boro, z = addr(i + 2); u = unit(i + 1)
    pid = f"P{100200 + i}"
    zip_val = "" if i % 9 == 0 else z      # some missing ZIP (recoverable if borough present)
    ws.append([fn, "", ln, pid, st, u, boro, "NY", zip_val])
# a confirmed duplicate: same PatientNumber, identical row
ws.append(["Ben","","Placeholder","P100205","360 Adams St","Apt 4B","Brooklyn","NY","11201"])
ws.append(["Ben","","Placeholder","P100205","360 Adams St","Apt 4B","Brooklyn","NY","11201"])
wb.save(f"{OUT}/legacy_export.xlsx")

# ---- 4) state_export.xml: Address_1/Address_2, some rear/front descriptors ----
rows = []
for i in range(45):
    fn, ln = person(i + 8); st, boro, z = addr(i + 3)
    a1 = st + (" Rear" if i % 8 == 0 else (" Front" if i % 11 == 0 else ""))
    a2 = unit(i + 2)
    rows.append((f"{fn} {ln}", a1, a2, boro, "NY", z))
with open(f"{OUT}/state_export.xml", "w") as f:
    f.write("<records>\n")
    for nm, a1, a2, c, s, z in rows:
        f.write("  <record>"
                f"<Name>{escape(nm)}</Name>"
                f"<Address_1>{escape(a1)}</Address_1>"
                f"<Address_2>{escape(a2)}</Address_2>"
                f"<City>{escape(c)}</City><State>{s}</State><Zip_Code>{z}</Zip_Code>"
                "</record>\n")
    f.write("</records>\n")

# ---- 5) partner_export.tsv: clean columns + program, with possible duplicates ----
with open(f"{OUT}/partner_export.tsv", "w", newline="") as f:
    w = csv.writer(f, delimiter="\t")
    w.writerow(["first","last","uid","address_line","apt","city","st","zip","program"])
    for i in range(50):
        fn, ln = person(i + 2); st, boro, z = addr(i + 4); u = unit(i + 3)
        w.writerow([fn, ln, f"U{9000+i}", st, u, boro, "NY", z, PROG[i % len(PROG)]])
    # possible duplicate: same person + program, different uid
    w.writerow(["Cara","Example","U9500","209 Joralemon St","","Brooklyn","NY","11201","Housing"])
    w.writerow(["Cara","Example","U9600","209 Joralemon St","","Brooklyn","NY","11201","Housing"])

print("wrote sample files to", OUT + "/:")
for fn in sorted(os.listdir(OUT)):
    print("  ", fn, os.path.getsize(f"{OUT}/{fn}"), "bytes")
