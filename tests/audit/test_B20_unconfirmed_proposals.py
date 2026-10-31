"""B-20: the old app wrote proposals straight into the alias map, so counts changed before anyone agreed (P-PROG-3)."""
import pytest

from wholecount.engine.programs import (ProgramDecision, StopAtPrograms, TableProgram, audit_fields, build_program_map,
                                        canonical_program, fast_path_gate, program_sources, propose_groups)

pytestmark = pytest.mark.claim("CL-PROG-07")


def names():
    tables = [TableProgram("a", "column", "Program", None, 14, (("Workforce Dev.", 5), ("Youth Services", 9))),
              TableProgram("b", "column", "Program", None, 16, (("Workforce Development", 9), ("Youth Employment", 7))),
              TableProgram("c", "column", "Program", None, 7, (("Level 1", 4), ("Level 2", 3)))]
    return program_sources(tables)[0]


def test_no_decision_changes_nothing():
    ns = names()
    props = propose_groups(ns)
    assert [(p.members, {r for _, _, r in p.reasons}) for p in props] == [(("Workforce Dev.", "Workforce Development"), {"same_name"})]
    pm = build_program_map(ns, props, ())
    assert pm.alias == {} and pm.groups == ()
    assert all(canonical_program(n.name, pm) == n.name for n in ns)
    assert fast_path_gate(pm) == StopAtPrograms(unconfirmed=1)


def test_one_confirm_groups_only_those_names():
    ns = names()
    props = propose_groups(ns)
    d = ProgramDecision("confirm", props[0].members)
    pm = build_program_map(ns, props, [d])
    assert pm.alias == {"Workforce Dev.": "Workforce Development", "Workforce Development": "Workforce Development"}
    for n in ("Youth Services", "Youth Employment", "Level 1", "Level 2"):
        assert canonical_program(n, pm) == n
    assert audit_fields(d) == {"kind": "confirm", "programs": ("Workforce Dev.", "Workforce Development"), "label": None}
