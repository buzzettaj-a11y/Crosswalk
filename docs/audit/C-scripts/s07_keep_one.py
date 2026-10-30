"""
s07: 'Keep one per person per program' and 'keep this row' report rows set aside that are
still in Final_Clean_Mapped and not in Set_Aside_Records.
"""
from invariants import *
import messy

setup_standard(messy.make(), dob=True)
before_clean = export_df("clean")
print("before: clean rows", len(before_clean))

r = client.post("/api/queue/keep-one-per-program").json()
print("response:", r)
q = queue("all")
removed = [i for i in q["items"] if i["status"] == "removed"]
approved = [i for i in q["items"] if i["status"] == "approved"]
clean_keys = set(f"{a}||{b}" for a, b in zip(export_df("clean")["Source_File"], export_df("clean")["Source_Row"]))
aside_keys = set(f"{a}||{b}" for a, b in zip(export_df("aside")["Source_File"], export_df("aside")["Source_Row"])) if len(export_df("aside")) else set()
print("queue says 'removed':", len(removed), "| Set_Aside_Records rows:", len(aside_keys))
for i in removed:
    where = "Final_Clean_Mapped" if i["rid"] in clean_keys else ("Set_Aside_Records" if i["rid"] in aside_keys else "?")
    print(f"   {i['rid']:<28} id={i['id']:<6} {i['name']:<16} 'removed' on screen, but file holds it in: {where}")
print("summary rows:", summary()["rows"])
print("audit log says:")
for line in export_raw("audit").decode().splitlines():
    if "set aside, same person as" in line or line.startswith(("1.", "2.", "3.", "4.", "5.", "6.", "7.")):
        print("   ", line)
