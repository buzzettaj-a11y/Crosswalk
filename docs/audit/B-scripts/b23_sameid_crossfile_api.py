from _api import *
c = new_client()
# Two exports from two different systems. Each numbers its own clients 1001, 1002, ...
def csv_(prefix_first, last, street, city, zipc, n):
    head = "First_Name,Last_Name,Client_ID,Address_1,City,State,Zip,Program\n"
    return (head + "\n".join(f"{prefix_first}{chr(97+i%26)}{chr(97+i//26)},{last},{1001+i},{10+i} {street},{city},NY,{zipc},{'Food' if prefix_first=='Al' else 'Legal'}" for i in range(n)) + "\n").encode()
upload(c, {"pantry_system.csv": csv_("Al","Reyes","Oak St","Brooklyn","11201",60),
           "legal_system.csv": csv_("Bo","Chen","Elm Ave","Queens","11355",60)})
st = run_and_wait(c)
res = cw.S["results"]
n_review = [r for r in res["review"] if any("Same Client ID" in e for e in r["__errors__"])]
print("rows:", len(res["transformed"]), "clean:", len(res["clean"]), "sent to review as 'Same Client ID used by records with different data':", len(n_review))
print("example:", n_review[0]["__source_file__"].split(" :: ")[0], n_review[0]["Client_ID"], n_review[0]["__errors__"])
