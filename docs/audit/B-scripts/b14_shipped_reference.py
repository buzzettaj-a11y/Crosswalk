from _common import *
import csv, collections
rows = list(csv.DictReader(open("nyc_address_points.csv")))
agree = sum(1 for r in rows if engine.borough_from_zip(r["zip"]) == r["city"])
nonnyc = sum(1 for r in rows if engine.borough_from_zip(r["zip"]) == "")
print("rows", len(rows), "ZIP borough agrees with city column:", agree, "ZIP outside NYC ranges:", nonnyc)
print(collections.Counter(r["city"] for r in rows))
print("sample rows:"); 
for r in rows[:6]: print(r)
# real-looking addresses
import re
print("rows whose address starts with a normal house number and ends with St/Ave/Rd/Blvd:", sum(1 for r in rows if re.match(r"^\d+ .*\b(St|Ave|Rd|Blvd|Street|Avenue)$", r["address"])))
# preflight verdict on the shipped reference
print(engine.check_reference_quality("nyc_address_points.csv"))
