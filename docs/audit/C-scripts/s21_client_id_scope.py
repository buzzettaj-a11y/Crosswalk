"""
s21: Client_ID handling.
 (a) each system numbers its own clients 1..N (normal): IDs repeat across files for different people
 (b) one enrollment-level file: the same person, same ID, two programs
 (c) the same system ID is 'decisive' evidence, but only if the two rows share a blocking key
"""
from invariants import *
import pandas as pd

H = ["Client_ID", "First_Name", "Last_Name", "DOB", "Address", "City", "State", "Zip", "Program"]
FIRST = ["Ada", "Ben", "Cara", "Devi", "Evan", "Faye", "Gus", "Hana", "Ivo", "Jae"]
LAST = ["Alvarez", "Brown", "Chen", "Diaz", "Evans", "Fox", "Gupta", "Hill", "Ito", "Jones"]


def people(offset, n):
    out = []
    for i in range(n):
        k = offset + i
        out.append([str(i + 1), FIRST[k % 10], LAST[(k // 10) % 10] + chr(97 + k % 7) * 2, f"19{50 + k % 40}-0{1 + k % 9}-1{k % 9}",
                    f"{100 + k} Test St", "Brooklyn", "NY", "11201", "Housing"])
    return pd.DataFrame(out, columns=H)


print("== (a) three systems, each numbering its own clients 1..20, 60 DIFFERENT people")
files = {"sysA.csv": people(0, 20), "sysB.csv": people(20, 20), "sysC.csv": people(40, 20)}
reset(); upload({k: v.to_csv(index=False).encode() for k, v in files.items()}); set_schema(dob=True); run()
print("   ", counts_line(True))
print("    groups:", [(g["id"], g["count"]) for g in groups()])
print("    the 60 rows are 60 distinct people; clean rows =", summary()["rows"]["clean"])

print("\n== (b) one enrollment-level file: same client, same ID, two programs (3 clients, 6 rows)")
rows = [["7", "Ana", "Perez", "1990-05-06", "7 Elm St", "Brooklyn", "NY", "11201", "Housing"],
        ["7", "Ana", "Perez", "1990-05-06", "7 Elm St", "Brooklyn", "NY", "11201", "Youth"],
        ["8", "Bo", "Lee", "1991-01-01", "8 Elm St", "Brooklyn", "NY", "11201", "Housing"],
        ["8", "Bo", "Lee", "1991-01-01", "8 Elm St", "Brooklyn", "NY", "11201", "Workforce"],
        ["9", "Cy", "Kim", "1992-02-02", "9 Elm St", "Brooklyn", "NY", "11201", "Housing"],
        ["9", "Cy", "Kim", "1992-02-02", "9 Elm St", "Brooklyn", "NY", "11201", "Youth"]]
reset(); upload({"enroll.csv": pd.DataFrame(rows, columns=H).to_csv(index=False).encode()}); set_schema(dob=True); run()
print("   ", counts_line(True), "(truth: Goal 1 = 3, Goal 2 = 6)")
print("    groups:", [(g["id"], g["count"], g["title"][:60]) for g in ui("review")["review"]["groups"]])
print("    reason:", queue("all", per=3).get("items", [{}])[0].get("reason", "")[:120] if queue("all")["items"] else "")
vr = client.get("/api/review/preview?gid=idconflict").json()
print("    sample message:", vr["rows"][0]["problems"][0] if vr["rows"] else None)

print("\n== (c) same ID in one system, name and address changed (marriage and a move), nothing else shared")
rows = [["500", "Maria", "Lopez", "", "100 Grand Concourse", "Bronx", "NY", "10451", "Housing"],
        ["500", "Maria", "Garcia", "", "5 Main St", "Brooklyn", "NY", "11201", "Housing"]]
reset(); upload({"one.csv": pd.DataFrame(rows, columns=H).to_csv(index=False).encode()}); set_schema(dob=True); run()
print("    after run:", counts_line(True))
decide("idconflict", "accept_all")
print("    after the reviewer accepts them as entered:", counts_line(True), "(same identifier, same system: one person)")

print("\n== (b2) the enrollment file after the reviewer presses 'accept all' on the ID group")
reset(); upload({"enroll.csv": pd.DataFrame([["7", "Ana", "Perez", "1990-05-06", "7 Elm St", "Brooklyn", "NY", "11201", "Housing"],
        ["7", "Ana", "Perez", "1990-05-06", "7 Elm St", "Brooklyn", "NY", "11201", "Youth"],
        ["8", "Bo", "Lee", "1991-01-01", "8 Elm St", "Brooklyn", "NY", "11201", "Housing"],
        ["8", "Bo", "Lee", "1991-01-01", "8 Elm St", "Brooklyn", "NY", "11201", "Workforce"],
        ["9", "Cy", "Kim", "1992-02-02", "9 Elm St", "Brooklyn", "NY", "11201", "Housing"],
        ["9", "Cy", "Kim", "1992-02-02", "9 Elm St", "Brooklyn", "NY", "11201", "Youth"]], columns=H).to_csv(index=False).encode()})
set_schema(dob=True); run()
decide("idconflict", "accept_all")
print("   ", counts_line(True), "(truth: Goal 1 = 3, Goal 2 = 6)")
