"""Properties of program proposals and the map (P-PROG-2, P-PROG-3, B-20)."""
from hypothesis import given, settings
from hypothesis import strategies as st

from wholecount.engine.programs import (ProgramDecision, ProgramName, build_program_map, canonical_program, pair_reason,
                                        propose_groups)

POOL = ["Workforce Development", "Workforce Dev.", "WFD", "Workforce", "Youth", "youth", "Youth Services", "Youth Employment",
        "SYEP", "Summer Youth Employment Program", "Senior Housing", "Senior Services", "Adult", "Adult Literacy", "Level 1",
        "Level 2", "ESL", "GED", "Food Pantry"]
NAMES = st.lists(st.tuples(st.sampled_from(POOL), st.integers(1, 20)), max_size=12, unique_by=lambda t: t[0])


def build(ts):
    return [ProgramName(n, r) for n, r in ts]


@settings(max_examples=100, deadline=None)
@given(NAMES, st.randoms(use_true_random=False))
def test_order_free_and_no_name_twice(ts, rnd):
    a = propose_groups(build(ts))
    shuffled = list(ts)
    rnd.shuffle(shuffled)
    assert propose_groups(build(shuffled)) == a
    members = [m for p in a for m in p.members]
    assert len(members) == len(set(members))
    for p in a:
        for i, x in enumerate(p.members):
            for y in p.members[i + 1:]:
                assert pair_reason(x, y)


@settings(max_examples=150, deadline=None)
@given(st.sampled_from(["Level", "Cohort", "Section", "Tier", "Group", "Class", "ESL", "Youth Program"]),
       st.sampled_from(["1", "2", "3", "A", "B", "C", "2023", "2024"]), st.sampled_from(["1", "2", "3", "A", "B", "C", "2023", "2024"]))
def test_a_digit_letter_or_year_keeps_names_apart(base, x, y):
    if x != y:
        assert propose_groups(build([(f"{base} {x}", 1), (f"{base} {y}", 1)])) == []


@settings(max_examples=100, deadline=None)
@given(NAMES, st.data())
def test_map_properties(ts, data):
    ns = build(ts)
    props = propose_groups(ns)
    assert build_program_map(ns, props, ()).alias == {}
    chosen = [p for p in props if data.draw(st.booleans())]
    pm = build_program_map(ns, props, [ProgramDecision("confirm", p.members) for p in chosen])
    labels = [g.label for g in pm.groups]
    assert len(labels) == len(set(labels))
    seen = [m for g in pm.groups for m in g.members]
    assert len(seen) == len(set(seen))
    for n in ns:
        c = canonical_program(n.name, pm)
        assert canonical_program(c, pm) == c
