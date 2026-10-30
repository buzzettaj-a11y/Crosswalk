from _common import *
import program_names as pn
def show(names):
    vals = {n: 10 + i for i, n in enumerate(names)}
    groups = pn.suggest_groups(vals)
    joined = [g for g in groups if len(g["variants"]) > 1]
    print(f"{names}")
    if not joined: print("    -> no proposed join"); return
    for g in joined:
        print(f"    -> JOINED {[v['name'] for v in g['variants']]} as {g['canonical']!r} because {g['why']!r}, needs_confirming={g['needs_confirming']}")
for names in [
 ["Youth Services","Youth Employment"], ["Youth Services","Youth Housing"], ["Youth Employment","Youth Housing"],
 ["Senior Housing","Housing"], ["Senior Housing","Senior Services"], ["Senior Services","Senior Employment"], ["Senior Center","Senior Housing"],
 ["Housing","Housing Court Assistance"], ["Housing","Housing Assistance"], ["Adult Education","Adult Literacy"], ["Adult","Adult Day Care"],
 ["Level 1","Level 2"], ["Tier 1","Tier 2"], ["Cohort 2023","Cohort 2024"], ["Section B","Section C"], ["Group A","Group B"], ["Class A","Class B"], ["Program A","Program B"],
 ["Head Start","Early Head Start"], ["Summer Youth Employment","Summer Youth Employment Program"], ["SYEP","Summer Youth Employment Program"],
 ["Workforce","Workforce Development"], ["WFD","Workforce Development"], ["Workforce Dev.","Workforce Development"],
 ["Food Pantry","Food Stamps"], ["Food Pantry","Food Pantry Delivery"], ["Tenant Services","Tenant Organizing"], ["Housing Counseling","Housing Court"],
 ["Youth Employment","Youth Empowerment"], ["Adult Employment","Adult Empowerment"], ["Mental Health","Mental Hygiene"], ["Mental Health","Mental Health Clinic"],
 ["Senior Services","Senior Services II"], ["Pre-K","Pre-K Extended Day"], ["3-K","Pre-K"], ["3K","4K"], ["ESL 1","ESL 2"], ["ESL Level 1","ESL Level 2"], ["GED","GED Prep"], ["GED","HSE"],
 ["Case Management","Case Management Plus"], ["Housing Court","Housing Counseling"], ["Resident Services","RS"], ["Community Services","CS"], ["Health","Hospital Employment Assistance Linkage Training Hub"],
 ["Youth","Young Adult"], ["Veterans","Veterans Housing"], ["Veterans Services","Veterans Employment"],
]:
    show(names)

print("\n== chains: three programs, no pair of the last two is proposed on its own ==")
import sys
sys.path.insert(0, "/tmp/claude-0/-home-claude/ec68250d-d5ac-549e-8d94-20759c381437/scratchpad/src/agentB")
import program_names as _pn
for names in (["Youth Services", "Youth Employment", "Youth Housing"],
              ["Senior Services", "Senior Housing", "Senior Employment"],
              ["Adult Education", "Adult", "Adult Literacy"]):
    groups = _pn.suggest_groups({n: 5 for n in names})
    print("  ", names, "->", [[v["name"] for v in g["variants"]] for g in groups if len(g["variants"]) > 1], "needs_confirming:", [g["needs_confirming"] for g in groups if len(g["variants"]) > 1])
