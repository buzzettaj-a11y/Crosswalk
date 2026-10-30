from _common import *
for label, kw in [("Last name 'Sum' (Cambodian/Chinese surname), no street", dict(First="Sokha", Last="Sum", Addr="", Zip="11201")),
                  ("Last name 'Sum', street present", dict(First="Sokha", Last="Sum")),
                  ("Last name 'Mean', no street", dict(First="Chan", Last="Mean", Addr="")),
                  ("First name 'Count' no street", dict(First="Count", Last="Basie", Addr=""))]:
    st, r = final(**kw); show(label, st, r)
    print("      summary flag:", bool(r.get("__summary__")))
