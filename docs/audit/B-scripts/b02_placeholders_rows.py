from _common import *
cases = [
 ("First='-'", dict(First="-")),
 ("Last='-'", dict(Last="-")),
 ("First='0'", dict(First="0")),
 ("Last='Na' (real surname)", dict(Last="Na")),
 ("First='Nan' (real name)", dict(First="Nan")),
 ("Last='None'", dict(Last="None")),
 ("Client_ID='-'", dict(ID="-")),
 ("Client_ID='0'", dict(ID="0")),
 ("Client_ID=\"'0012345\"", dict(ID="'0012345")),
 ("Addr='Homeless'", dict(Addr="Homeless")),
 ("Addr='Unknown'", dict(Addr="Unknown")),
 ("Addr='-'", dict(Addr="-")),
 ("Addr='0'", dict(Addr="0")),
 ("Addr='N/A'", dict(Addr="N/A")),
 ("Addr2='-'", dict(Addr2="-")),
 ("Addr2='0'", dict(Addr2="0")),
 ("Zip='-'", dict(Zip="-")),
 ("Zip='0'", dict(Zip="0")),
 ("Zip=\"'11201\"", dict(Zip="'11201")),
 ("Zip='11201\\u200b'", dict(Zip="11201​")),
 ("First with ZWSP 'Ana\\u200b'", dict(First="Ana​")),
 ("First with leading apostrophe", dict(First="'Ana")),
 ("City='-' zip=11201", dict(City="-")),
 ("City='Unknown' zip=11201", dict(City="Unknown")),
 ("State='-'", dict(State="-")),
 ("State='0'", dict(State="0")),
]
for label, kw in cases:
    st, r = final(**kw)
    show(label, st, r)
