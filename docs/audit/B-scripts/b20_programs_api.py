from _api import *
c = new_client()
fileA = b"First_Name,Last_Name,Client_ID,Address_1,City,State,Zip,Program\n" + b"\n".join(
    f"Ana{chr(97+i)},Lopez,A{i},{10+i} Main St,Brooklyn,NY,11201,Youth Services".encode() for i in range(6)) + b"\n"
fileB = b"First_Name,Last_Name,Client_ID,Address_1,City,State,Zip,Program\n" + b"\n".join(
    f"Bo{chr(97+i)},Chen,B{i},{40+i} Oak Ave,Queens,NY,11355,Youth Employment".encode() for i in range(10)) + b"\n"
fileC = b"First_Name,Last_Name,Client_ID,Address_1,City,State,Zip,Program\n" + b"\n".join(
    f"Cy{chr(97+i)},Diaz,C{i},{70+i} Elm St,Bronx,NY,10452,Level 1".encode() for i in range(3)) + b"\n" + b"\n".join(
    f"Di{chr(97+i)},Diaz,D{i},{80+i} Elm St,Bronx,NY,10452,Level 2".encode() for i in range(4)) + b"\n"
upload(c, {"A_youth_services.csv": fileA, "B_youth_employment.csv": fileB, "C_levels.csv": fileC})
# NOTE: the person never opens the Programs stage and never clicks anything about grouping.
# Merely loading the Programs screen (or the Process stage reading the same state) computes the proposal:
r = c.get("/api/ui?screen=programs").json()["programs"]
print("proposed groups shown on Programs stage:")
for g in r["groups"]:
    print("   ", g["canonical"], [v["name"] for v in g["variants"]], "needs_confirming =", g["needs_confirming"])
print("server alias map after only LOADING the screen:", cw.S["program_aliases"])
st = run_and_wait(c)
print("run:", st["state"])
res = cw.S["results"]
from collections import Counter
print("Program stored on the processed rows (no person confirmed anything):", Counter(r["__program__"] for r in res["transformed"]))
print("flags example:", [f["message"] for f in res["transformed"][0]["__flags__"]][:3])
