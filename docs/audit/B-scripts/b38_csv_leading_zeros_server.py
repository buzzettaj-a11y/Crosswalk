"""CSV values that look like numbers, through the server's reader: do leading zeros, long IDs and exponent-like IDs survive?"""
from _api import *
c = new_client()
body = ("First Name,Last Name,Client ID,Street Address,City,State,Zip\n"
        "Ana,Lopez,0012345,10 Main St,Hoboken,NJ,07030\n"
        "Bo,Chen,12345678901234567890,12 Oak Ave,Queens,NY,11355\n"
        "Cy,Diaz,1E5,14 Elm St,Bronx,NY,10452\n"
        "Di,Khan,00501,16 Pine St,Holtsville,NY,00501\n")
upload(c, {"zeros.csv": body.encode()})
for k, df in cw.S["frames"].items():
    print("frame", k); print(df.to_string())
    print("dtypes:", dict(df.dtypes.astype(str)))
