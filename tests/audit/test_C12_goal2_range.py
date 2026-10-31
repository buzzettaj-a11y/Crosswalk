"""C-12: Goal 2's low end now comes from the same union as Goal 1's: every open pair and open copy group united."""
from tests.support.session import base


def _low(s, program=None):
    r = s.results
    parent = {}

    def find(x):
        parent.setdefault(x, x)
        while parent[x] != x:
            x = parent[x]
        return x

    for p in r.identity.proposals:
        parent[find(p.pair[0])] = find(p.pair[1])
    for g in r.open_groups:
        ks = [r.person_of_record[m] for m in g.members if m in r.person_of_record]
        for k in ks[1:]:
            parent[find(k)] = find(ks[0])
    for k in r.identity.master_of:
        for j in r.identity.groups[r.identity.master_of[k]]:
            parent[find(j)] = find(k)
    rows = [k for k, o in r.outcomes.items() if o.counted]
    if program is None:
        return len({find(r.person_of_record[k]) for k in rows})
    return len({find(r.person_of_record[k]) for k in rows if r.program_of_record.get(k) == program})


def test_base_state_ranges(tmp_path):
    s = base(tmp_path)
    c = s.counts()
    assert (c.goal2.low, c.goal2.high) == (9, 11) and (c.per_program["Housing"].low, c.per_program["Housing"].high) == (3, 4)
    assert c.goal1.low == _low(s)
    for p in ("Housing", "Youth", "Workforce"):
        assert c.per_program[p].low == _low(s, p)
