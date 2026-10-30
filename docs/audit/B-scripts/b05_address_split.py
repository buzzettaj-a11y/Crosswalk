from _common import *
cases = [
 # units
 "123 Main St Apt 4B", "123 Main St #4B", "123 Main St 4th Floor", "123 Main St, 4th Floor", "123 Main St Rear",
 "123 Main St Basement", "123 Main St 1/2", "123 1/2 Main St", "123 1/2 Main St Apt 2", "123 Main St Fl 2", "123 Main St 2nd Fl",
 "123 Main St Apt. 4-B", "123 Main St Apt#4B", "123 Main St Unit B", "123 Main St Apt B", "123 Main St Apt 12", "123 Main St Ste 200",
 "123 Main St Front", "123 Main St, Front", "123 Main St 3F", "123 Main St 3 F", "123 Main St 3-F", "123 Main St, 3F",
 "123 Main St Garage", "123 Main St Rm 5", "123 Main Street, Lower", "123 Main St Top Floor", "123 Main St Bsmt",
 # hyphenated queens house numbers
 "117-19 45th Ave", "117-19 45th Ave 14A", "117-19 45th Ave Apt 14A", "117-19 45th Ave, Flushing NY 11355", "40-22 24th St, Long Island City, NY 11101",
 "40-22 24th St Fl 2", "40-22 24th St 2", "40-22 24th St 2R",
 # street names with unit-like words
 "100 Avenue U", "100 Avenue U Apt 2", "100 Avenue U 2", "2250 Avenue of the Americas", "1350 Avenue of the Americas 12F", "1 Floor St", "12 Floor St Apt 3",
 "55 Suite Rd", "55 Unit Ave", "9 Lot Ln", "9 Stop St", "14 Slip Ln", "14 Pier St", "14 Pier 40", "Pier 40", "90 Ground Ave", "90 Lobby Ln",
 "300 Ocean Pkwy 4F", "300 Ocean Pkwy F4", "300 East 4th Street Apt 3", "300 E 4 St 3F", "300 E 4 St 4", "300 W 4 St 4F", "4 W 4 St 4", "4 Avenue A 4", "4 Avenue A", "4 Avenue A Apt 4",
 "1234 Route 9", "77 Route 9 2", "Coney Island Ave", "2 Park Ave 12", "2 Park Ave 12C", "2 Park Ave 12 C", "2 Park Ave PH", "2 Park Ave Penthouse A", "2 Park Ave PH A",
 "500 8th Ave 12th Fl", "500 8th Ave 12 Fl", "500 8 Ave Fl 12", "500 8th Avenue Floor 12", "500 Eighth Ave Floor 12",
 "1 First Ave Apt 1", "1 1st Ave #1", "100 Hall Pl 5", "1010 Grand Concourse Apt 5C", "1010 Grand Concourse 5C", "1010 Grand Concourse #5C",
 "250 Broadway Suite 1200", "250 Broadway Ste 1200", "250 Broadway, Suite 1200", "250 Broadway 12th Floor", "250 Broadway Floor 12",
 "100 Bldg 5", "100 Main St Bldg 5", "Bldg 5 100 Main St", "Apt 4B 123 Main St", "#4B 123 Main St",
 "4B 123 Main St", "123 Main St Apt 4B Brooklyn", "123 Main St Apt 4B Brooklyn NY", "123 Main St Apt 4B, Brooklyn NY 11201",
]
for c in cases:
    d = engine.split_jammed_address(c)
    print(f"{c!r:50} -> street={d['street']!r} unit={d['unit']!r} city={d['city']!r} st={d['state']!r} zip={d['zip']!r}")
