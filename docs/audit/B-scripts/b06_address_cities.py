from _common import *
cases = [
 "123 Main St, Apt 4B, Brooklyn, NY 11201", "123 Main St, Brooklyn, Apt 4B, NY 11201", "123 Main St,, Brooklyn NY 11201", "123 Main St, , Brooklyn, NY, 11201",
 "123 Main St Brooklyn NY 11201", "123 Main St Brooklyn, NY 11201", "123 Main St Brooklyn 11201", "123 Main St, Brooklyn 11201", "123 Main St, Brooklyn, 11201",
 "123 Brooklyn Ave NY 11203", "123 Brooklyn Ave 11203", "123 Brooklyn Ave Brooklyn NY 11203", "123 Brooklyn Ave, Brooklyn, NY 11203", "123 Brooklyn Ave Brooklyn",
 "1 Queens Blvd Queens NY 11375", "1 Queens Blvd NY 11375", "1 Queens Blvd 11375", "100 Queens Blvd", "92-10 Queens Blvd Elmhurst NY 11373",
 "123 Jamaica Ave Queens NY 11432", "123 Jamaica Ave NY 11432", "123 Jamaica Ave 11432", "123 Jamaica Ave Jamaica NY 11432", "123 Jamaica Ave, Jamaica, NY 11432",
 "100 Bronx River Ave Bronx NY 10472", "100 Bronx River Ave NY 10472", "1 Staten Island Expy NY 10314", "10 Manhattan Ave Brooklyn NY 11222", "10 Manhattan Ave NY 11222",
 "10 Manhattan Ave Manhattan NY 10025", "200 Flushing Ave Brooklyn NY 11205", "200 Flushing Ave NY 11205", "55 Astoria Blvd NY 11370", "55 Astoria Blvd Astoria NY 11370",
 "34 Park Pl NY 11217", "78 Richmond Hill Rd NY 10314", "78 Richmond Hill Rd Staten Island NY 10314", "5 Woodside Ave NY 11377", "12 Williamsburg St NY 11211",
 "123 Main St, Brooklyn, New York State 11201", "123 Main St, Brooklyn, New York 11201", "123 Main St Brooklyn New York 11201", "123 Main St, New York, NY 10001", "123 Main St New York NY 10001",
 "100 New York Ave Brooklyn NY 11216", "100 New York Ave, NY 11216", "100 New York Ave NY 11216", "100 New York Ave 11216", "100 New York Ave",
 "123 Main St, Brooklyn, NY 11201 USA", "123 Main St, Brooklyn, NY 11201, United States", "123 Main St, Brooklyn, NY 11201 US", "123 Main St, Brooklyn, NY, USA", "123 Main St, Brooklyn, USA 11201",
 "123 Main St, Brooklyn, NY 11201-1234", "123 Main St, Brooklyn, NY 112011234", "123 Main St, Brooklyn NY 11201.", "123 Main St Brooklyn NY",
 "123 Main St, Hoboken, NJ 07030", "123 Main St, Yonkers, NY 10701", "123 Main St, Newark, New Jersey 07102", "123 Main St, Brooklyn, NY 11201 - Rear", "123 Main St - Apt 4 - Brooklyn - NY - 11201",
 "123 Main St, Lower", "123 Main St, Top Floor", "123 Main St, c/o Jane Doe", "123 Main St, Attn Jane", "123 Main St, Rear Building", "123 Main St, Basement Apt", "123 Main St, Bklyn", "123 Main St, Brooklyn NY 11201 Apt 3", "123 Main St, Apt 3 Brooklyn NY 11201",
 "123 Main St, 2nd Fl, Brooklyn", "123 Main St, #2, Brooklyn", "123 Main St, 2R, Brooklyn NY 11201", "123 Main St, B, Brooklyn NY 11201", "123 Main St, Apt B, Brooklyn NY 11201", "123 Main St, Unit B",
 "123 Main St Apt 4B Brooklyn NY 11201", "123 Main St Apt 4B Bklyn NY 11201", "123 Main St Apt 4B Brooklyn, NY", "123 Main St Fl 2 Brooklyn NY 11201",
 "123 Main St, Long Island City, NY 11101", "123 Main St Long Island City NY 11101", "123 Main St, Far Rockaway, NY 11691", "123 Main St Far Rockaway NY 11691", "123 Main St Rockaway Park NY 11694", "123 Main St Howard Beach NY 11414",
 "123 Main St South Ozone Park NY 11420", "123 Main St Ozone Park NY 11417", "123 Main St Jackson Heights NY 11372", "123 Main St Bayside NY 11361", "123 Main St Park Slope NY 11215", "123 Main St Brooklyn Heights NY 11201", "123 Main St Kew Gardens Hills NY 11367",
]
for c in cases:
    d = engine.split_jammed_address(c)
    print(f"{c!r:56} -> street={d['street']!r} unit={d['unit']!r} city={d['city']!r} st={d['state']!r} zip={d['zip']!r}")
