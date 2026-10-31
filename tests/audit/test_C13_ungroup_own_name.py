"""C-13: pulling the label name out of a group left the label behind. The label is recomputed from the members left
(P-PROG-5)."""
from wholecount.engine.programs import ProgramDecision, ProgramName, build_program_map, canonical_program


def test_split_the_label_dissolves_a_two_name_group():
    ns = [ProgramName("Workforce Development", 1), ProgramName("Workforce Dev.", 1)]
    pm = build_program_map(ns, (), [ProgramDecision("confirm", ("Workforce Development", "Workforce Dev."))])
    assert [g.label for g in pm.groups] == ["Workforce Development"]
    pm = build_program_map(ns, (), [ProgramDecision("confirm", ("Workforce Development", "Workforce Dev.")),
                                    ProgramDecision("split", ("Workforce Development",))])
    assert pm.groups == () and pm.alias == {}
    ana = [("r1", "Workforce Development"), ("r2", "Workforce Dev.")]
    assert len({canonical_program(p, pm) for _, p in ana}) == 2


def test_split_the_label_from_three_recomputes_it():
    ns = [ProgramName("Workforce Development", 3), ProgramName("Workforce Dev.", 2), ProgramName("Workforce", 1)]
    members = tuple(n.name for n in ns)
    pm = build_program_map(ns, (), [ProgramDecision("confirm", members), ProgramDecision("split", ("Workforce Development",))])
    (g,) = pm.groups
    assert g.members == ("Workforce", "Workforce Dev.") and g.label == "Workforce Dev."
    assert canonical_program("Workforce Development", pm) == "Workforce Development"
    assert len({x.label for x in pm.groups}) == len(pm.groups)
