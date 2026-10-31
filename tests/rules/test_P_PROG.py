"""Programs (SPEC 6.9, P-PROG-1 to P-PROG-6) and M07's PROG rules."""
import re

import pytest

from tests.conftest import ROOT
from wholecount import copy
from wholecount.engine.programs import (Proceed, ProgramDecision, ProgramName, StopAtPrograms, TableProgram, audit_fields,
                                        build_program_map, canonical_program, fast_path_gate, pair_reason,
                                        people_without_program, program_sources, propose_groups)


def N(*pairs):
    return [ProgramName(n, r) for n, r in pairs]


@pytest.mark.claim("CL-PROG-06")
def test_P_PROG_1_not_in_goal2():
    names, missing = program_sources([
        TableProgram("col", "column", "Program", "Ignored", 4, (("Housing", 3), ("", 1))),
        TableProgram("def", "default", None, "Youth", 5),
        TableProgram("none", "none", None, None, 7)])
    assert [(n.name, n.rows) for n in names] == [("Housing", 3), ("Youth", 5)]
    assert missing == [("none", 7)]
    assert "not in Goal 2" in copy.get("programs.not_in_goal2")


@pytest.mark.claim("CL-PROG-01")
def test_P_PROG_2_same_name():
    assert pair_reason("Workforce Dev.", "Workforce Development") == "same_name"
    assert pair_reason("Arts & Culture", "Arts and Culture Program") == "same_name"


@pytest.mark.claim("CL-PROG-02")
def test_P_PROG_2_initials():
    assert pair_reason("W.F.D.", "Workforce Development") == "initials"
    assert pair_reason("wfd", "Workforce Development") is None
    assert pair_reason("ABCDEFG", "Alpha Beta") is None


@pytest.mark.claim("CL-PROG-03")
def test_P_PROG_2_nearly_same():
    assert pair_reason("Workforce Developmnt", "Workforce Development") == "nearly_same"


@pytest.mark.claim("CL-PROG-04")
def test_P_PROG_2_more_words():
    assert pair_reason("Workforce", "Workforce Development") == "more_words"
    assert pair_reason("Art", "Art Development") is None
    assert pair_reason("Arts", "Arts Development") == "more_words"
    assert pair_reason("Workforce", "Workforce Training") is None


def test_PROG_2b_veto():
    for a, b in (("Level 1", "Level 2"), ("Cohort 2023", "Cohort 2024"), ("Section B", "Section C"),
                 ("Youth Services", "Youth Employment")):
        assert pair_reason(a, b) is None


def test_PROG_2c_no_chains():
    props = propose_groups(N(("Workforce Development", 9), ("Workforce Dev.", 5), ("WFD", 2), ("Workforce", 1)))
    names = [m for p in props for m in p.members]
    assert len(names) == len(set(names))
    for p in props:
        for i, a in enumerate(p.members):
            for b in p.members[i + 1:]:
                assert pair_reason(a, b)


def test_PROG_2d_label_and_collisions():
    (p,) = propose_groups(N(("Workforce Dev.", 5), ("Workforce Development", 5)))
    assert p.label == "Workforce Development"
    ns = N(("A Plus", 1), ("A Plus Program", 1), ("Housing", 3))
    pm = build_program_map(ns, (), [ProgramDecision("confirm", ("A Plus", "A Plus Program"), label="Housing")])
    assert [d.kind for d, why in pm.not_applied if why == "label_taken"] == ["confirm"]
    assert pm.groups[0].label == "A Plus Program"
    pm = build_program_map(ns, (), [ProgramDecision("confirm", ("A Plus", "A Plus Program")),
                                    ProgramDecision("rename", ("A Plus",), label="Housing")])
    assert pm.not_applied[0][1] == "label_taken"
    pm = build_program_map(ns, (), [ProgramDecision("confirm", ("A Plus", "A Plus Program")),
                                    ProgramDecision("rename", ("A Plus",), label="A+")])
    assert pm.groups[0].label == "A+" and canonical_program("A Plus Program", pm) == "A+"


def test_P_PROG_3_only_confirm_and_merge_group():
    ns = N(("Workforce Dev.", 1), ("Workforce Development", 1), ("WFD", 1))
    props = propose_groups(ns)
    assert build_program_map(ns, props, ()).alias == {}
    pm = build_program_map(ns, props, [ProgramDecision("confirm", ("Workforce Dev.", "Workforce Development")),
                                       ProgramDecision("merge", ("Workforce Dev.", "WFD"))])
    assert set(pm.alias) == {"Workforce Dev.", "Workforce Development", "WFD"}


@pytest.mark.claim("CL-PROG-05")
def test_P_PROG_4_gate():
    ns = N(("Workforce Dev.", 1), ("Workforce Development", 1))
    props = propose_groups(ns)
    assert fast_path_gate(build_program_map(ns, props, ())) == StopAtPrograms(1)
    assert fast_path_gate(build_program_map(ns, props, [ProgramDecision("split", ("Workforce Dev.",))])) == Proceed()
    assert copy.get("programs.held", count=3).endswith("3 left.")


def test_P_PROG_5_split_changes_counts():
    ns = N(("Workforce Dev.", 1), ("Workforce Development", 1))
    pm = build_program_map(ns, (), [ProgramDecision("confirm", ("Workforce Dev.", "Workforce Development")),
                                    ProgramDecision("split", ("Workforce Dev.",))])
    assert canonical_program("Workforce Dev.", pm) != canonical_program("Workforce Development", pm)


def test_P_PROG_6_audit_fields():
    d = ProgramDecision("merge", ("B", "A"), "A")
    assert audit_fields(d) == {"kind": "merge", "programs": ("A", "B"), "label": "A"}


def test_PROG_7_names_gone():
    ns = N(("Workforce Dev.", 1), ("Workforce Development", 1))
    d = ProgramDecision("confirm", ("Workforce Dev.", "Workforce Development", "WFD"))
    pm = build_program_map(ns, (), [d])
    assert pm.groups[0].members == ("Workforce Dev.", "Workforce Development") and pm.not_applied == ()
    gone = ProgramDecision("confirm", ("Old A", "Old B"))
    assert build_program_map(ns, (), [gone]).not_applied == ((gone, "names_gone"),)


def test_PROG_8_people_without_program():
    assert people_without_program({"r1": "M1", "r2": "M1", "r3": "M2"}, {"r1": "", "r2": "Youth", "r3": None}) == 1


def test_PROG_9_inherited():
    ns = N(("Workforce Dev.", 1), ("Workforce Development", 1))
    old = ProgramDecision("confirm", ("Workforce Dev.", "Workforce Development"), inherited=True)
    pm = build_program_map(ns, (), [old])
    assert pm.groups[0].from_earlier_batch
    pm = build_program_map(ns, (), [ProgramDecision("split", ("Workforce Dev.",)), old])
    assert pm.groups == ()
    pm = build_program_map(ns, (), [ProgramDecision("confirm", ("Gone A", "Gone B"), inherited=True)])
    assert pm.groups == () and pm.not_applied == ()
    pm = build_program_map(ns, (), [old, ProgramDecision("confirm", ("Workforce Dev.", "Workforce Development"))])
    assert not pm.groups[0].from_earlier_batch


def test_no_alias_written_outside_build_program_map():
    src = (ROOT / "wholecount" / "engine" / "programs.py").read_text(encoding="utf-8")
    body = src[src.index("def build_program_map"):src.index("def canonical_program")]
    rest = src.replace(body, "")
    assert not re.search(r"alias\s*(\[|=)", rest)
    for p in (ROOT / "wholecount").rglob("*.py"):
        if p.name != "programs.py":
            assert not re.search(r"\.alias\s*\[.*\]\s*=", p.read_text(encoding="utf-8")), p
