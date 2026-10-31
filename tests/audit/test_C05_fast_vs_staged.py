"""C-05: the old fast path never built program groups, so it counted 4 (person, program) pairs where the staged route counted
2. Both routes now call build_program_map, and the fast path stops while proposals are open (P-PROG-4)."""
import ast

from tests.conftest import ROOT
from wholecount.engine.programs import (Proceed, ProgramDecision, StopAtPrograms, TableProgram, build_program_map,
                                        canonical_program, fast_path_gate, program_sources, propose_groups)

RECORDS = [("a1", "M-ana", "Workforce Development"), ("a2", "M-bo", "Youth"), ("b1", "M-ana", "Workforce Dev."), ("b2", "M-bo", "youth")]


def names():
    return program_sources([TableProgram("A", "column", "Program", None, 2, (("Workforce Development", 1), ("Youth", 1))),
                            TableProgram("B", "column", "Program", None, 2, (("Workforce Dev.", 1), ("youth", 1)))])[0]


def pairs(pm):
    return len({(m, canonical_program(p, pm)) for _, m, p in RECORDS})


def staged(decisions):
    ns = names()
    return build_program_map(ns, propose_groups(ns), decisions)


def fast(decisions):
    ns = names()
    pm = build_program_map(ns, propose_groups(ns), decisions)
    return pm, fast_path_gate(pm)


def test_routes_agree():
    ns = names()
    props = propose_groups(ns)
    assert len(props) == 2 and all({r for _, _, r in p.reasons} == {"same_name"} for p in props)
    decisions = [ProgramDecision("confirm", p.members) for p in props]
    s = staged(decisions)
    f, gate = fast(decisions)
    assert s == f and gate == Proceed()
    assert all(canonical_program(n.name, s) == canonical_program(n.name, f) for n in ns)
    assert pairs(s) == 2


def test_no_decisions_stop_and_four_names_remain():
    pm, gate = fast(())
    assert gate == StopAtPrograms(unconfirmed=2)
    assert len({canonical_program(n.name, pm) for n in names()}) == 4 and pairs(pm) == 4


def test_only_build_program_map_constructs_a_map():
    bad = []
    for p in (ROOT / "wholecount").rglob("*.py"):
        tree = ast.parse(p.read_text(encoding="utf-8"))
        for fn in ast.walk(tree):
            if not isinstance(fn, ast.FunctionDef):
                continue
            for n in ast.walk(fn):
                if isinstance(n, ast.Call) and getattr(n.func, "id", getattr(n.func, "attr", "")) == "ProgramMap":
                    if fn.name != "build_program_map":
                        bad.append(f"{p.name}:{fn.name}")
    assert bad == []
    src = (ROOT / "wholecount" / "engine" / "programs.py").read_text(encoding="utf-8")
    gate = src[src.index("def fast_path_gate"):src.index("def people_without_program")]
    assert "build_program_map" not in gate and "alias" not in gate
