from _common import *
import column_check, random
random.seed(1)
def frame(n, **cols):
    return pd.DataFrame({k: [v(i) if callable(v) else v for i in range(n)] for k, v in cols.items()})
def report(label, df):
    m = {k: v for k, v in engine.guess_mapping(list(df.columns)).items() if v}
    fields = [{"role": r, "label": r, "col": c} for r, c in m.items()]
    ck = column_check.check_mapping(fields, df)
    print(f"\n{label}\n   mapping: {m}\n   verdict: {ck['status']} ({ck['problems']} problems, {ck['checks']} checks)")
    for role, res in ck["fields"].items():
        if res["status"] != "ok":
            print(f"   {role}: {res['status']} - {res['message'][:110]}")

n = 40
streets = ["Main St","Oak Ave","Elm St","Pine Rd"]
home = lambda i: f"{10+i} {streets[i%4]}"
mail_box = lambda i: (f"PO Box {100+i}" if i % 3 == 0 else f"{500+i} {streets[i%4]}")
names = ["Ana","Bo","Cy","Di","Ed","Flo","Gus","Hal"]
last = ["Lopez","Chen","Diaz","Khan","Ortiz","Park","Reyes","Silva"]

report("1. Mailing address listed before home address (all values look like addresses)",
  frame(n, **{"First Name": lambda i: names[i%8], "Last Name": lambda i: last[i%8], "Client ID": lambda i: f"C{i}",
              "Mailing Address": mail_box, "Mailing City": "Brooklyn", "Mailing State": "NY", "Mailing Zip": "11201",
              "Home Address": home, "Home City": "Queens", "Home State": "NY", "Home Zip": "11355"}))
report("2. Provider/emergency-contact name columns listed before the client's own",
  frame(n, **{"Emergency Contact First Name": lambda i: names[(i+3)%8], "Emergency Contact Last Name": lambda i: last[(i+3)%8],
              "First Name": lambda i: names[i%8], "Last Name": lambda i: last[i%8], "Client ID": lambda i: f"C{i}",
              "Address": home, "City": "Queens", "State": "NY", "Zip": "11355"}))
report("3. No Program column, but 'Program Start Date' with US-format dates",
  frame(n, **{"First Name": lambda i: names[i%8], "Last Name": lambda i: last[i%8], "Client ID": lambda i: f"C{i}",
              "Address": home, "City": "Queens", "State": "NY", "Zip": "11355",
              "Program Start Date": lambda i: f"{1+i%12}/{1+i%28}/2024"}))
report("3b. same, ISO dates",
  frame(n, **{"First Name": lambda i: names[i%8], "Last Name": lambda i: last[i%8], "Client ID": lambda i: f"C{i}",
              "Address": home, "City": "Queens", "State": "NY", "Zip": "11355",
              "Program Start Date": lambda i: f"2024-{1+i%12:02d}-{1+i%28:02d}"}))
report("4. 'Address Line 2' listed before 'Address Line 1' (Line 2 mostly filled)",
  frame(n, **{"First Name": lambda i: names[i%8], "Last Name": lambda i: last[i%8], "Client ID": lambda i: f"C{i}",
              "Address Line 2": lambda i: f"Apt {1+i%9}{'ABC'[i%3]}", "Address Line 1": home, "City": "Queens", "State": "NY", "Zip": "11355"}))
report("4b. 'Address Line 2' listed before 'Address Line 1' (Line 2 mostly blank)",
  frame(n, **{"First Name": lambda i: names[i%8], "Last Name": lambda i: last[i%8], "Client ID": lambda i: f"C{i}",
              "Address Line 2": lambda i: (f"Apt {1+i%9}{'ABC'[i%3]}" if i % 6 == 0 else ""), "Address Line 1": home, "City": "Queens", "State": "NY", "Zip": "11355"}))
report("5. 'Street Address' and 'Street Address 2'",
  frame(n, **{"First Name": lambda i: names[i%8], "Last Name": lambda i: last[i%8], "Client ID": lambda i: f"C{i}",
              "Street Address 2": lambda i: (f"Apt {1+i%9}" if i % 3 == 0 else ""), "Street Address": home, "City": "Queens", "State": "NY", "Zip": "11355"}))
report("6. 'City of Residence' and 'Place of Birth City'",
  frame(n, **{"First Name": lambda i: names[i%8], "Last Name": lambda i: last[i%8], "Client ID": lambda i: f"C{i}",
              "Address": home, "Place of Birth City": lambda i: ["Santo Domingo","Brooklyn","Guangzhou","Queens"][i%4], "City of Residence": "Queens", "State": "NY", "Zip": "11355"}))
report("7. Household ID before Client ID is absent: 'Program ID', 'Household ID' only",
  frame(n, **{"First Name": lambda i: names[i%8], "Last Name": lambda i: last[i%8], "Program ID": lambda i: f"P{1000+i}",
              "Household ID": lambda i: f"H{i//3}", "Address": home, "City": "Queens", "State": "NY", "Zip": "11355"}))
report("8. Zip: employer ZIP before client ZIP",
  frame(n, **{"First Name": lambda i: names[i%8], "Last Name": lambda i: last[i%8], "Client ID": lambda i: f"C{i}",
              "Address": home, "City": "Queens", "State": "NY", "Employer Zip": "10001", "Zip": "11355"}))
report("9. 'Zip Code' and 'Mailing Zip Code' (mailing first)",
  frame(n, **{"First Name": lambda i: names[i%8], "Last Name": lambda i: last[i%8], "Client ID": lambda i: f"C{i}",
              "Address": home, "City": "Queens", "State": "NY", "Mailing Zip Code": "10001", "Zip Code": "11355"}))
