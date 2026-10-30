from _common import *
pairs = [("111 Main St","11 Main St"),("1 Main St","11 Main St"),("1234 Main St","1243 Main St"),("2250 Flatbush Ave","2205 Flatbush Ave"),("117-19 45th Ave","117-91 45th Ave"),
         ("40 W 100 St","100 W 40 St"),("1 Avenue U","1 Avenue V"),("1 Avenue M","1 Avenue N"),("100 E 10 St","100 E 11 St"),("100 W 10 St","100 W 100 St"),("100 W 10 St","100 E 10 St"),
         ("350 Broadway","350 Broadway Apt 5"),("45 Beach 9 St","45 Beach 90 St"),("12 W 4 St","12 W 40 St"),("123 Fulton St","123 Fulton Ave"),("20 Park Ave","200 Park Ave"),("5 Court St","5 Courtlandt St"),("100 Hall St","100 Hale St")]
for a, b in pairs:
    r = engine._ratio(engine._norm_addr(a), engine._norm_addr(b))
    print(f"{a!r:22} vs {b!r:22} -> {r:3} {'MATCH (>=88)' if r >= 88 else ''}")
