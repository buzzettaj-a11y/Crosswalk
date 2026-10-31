"""C-20: the old master IDs were row counters, so deciding one pair renumbered everyone. A master ID now comes from a person
key (SPEC 5.3)."""
import random

from tests.fixtures.people.builders import pair_of, prow
from wholecount.engine.identity import KnownMaster, PairVerdict, master_id, resolve


GIVEN = ["Ada", "Bea", "Cy", "Dov", "Eli", "Fay", "Gil", "Hal", "Ivy", "Jo", "Kai", "Lu", "Mo", "Ned", "Oz", "Pia", "Quin", "Rex",
         "Sol", "Tia"]
SUR = ["Abbot", "Bryce", "Croft", "Drake", "Eaton", "Frost", "Grant", "Hayes", "Irwin", "Joyce", "Keane", "Lyons", "Moss",
       "Nash", "Oakes", "Price", "Quill", "Royce", "Stone", "Tate"]


def thirty():
    """20 people: 10 with one record, 6 with two records joined by four exact facts, 4 with two records one DOB digit apart."""
    rows = []
    for i in range(20):
        g, s, dob, street = GIVEN[i], SUR[i], f"{1940 + i * 2}-0{1 + i % 9}-1{i % 9}", f"{i + 1} Main St"
        if i < 10:
            rows.append(prow(f"s{i}", "A", f"S{i}", g, s, dob, street, "11201"))
        elif i < 16:
            rows += [prow(f"j{i}{x}", x, f"J{i}{x}", g, s, dob, street, "11201") for x in "AB"]
        else:
            rows.append(prow(f"p{i}A", "A", f"P{i}A", g, s, dob, street, "11201"))
            rows.append(prow(f"p{i}B", "B", f"P{i}B", g, s, f"{1941 + i * 2}" + dob[4:], street, "11201"))
    return rows


def test_one_decision_renumbers_nobody_else():
    rows = thirty()
    first = resolve(rows)
    assert len(rows) == 30 and len(first.proposals) == 4 and (first.settled, first.low) == (24, 20)
    p = first.proposals[0]
    second = resolve(rows, [PairVerdict(*p.pair, "same", "d1", "Joe")])
    changed = {k for k in first.master_of if first.master_of[k] != second.master_of[k]}
    assert changed <= set(p.pair) and len(changed) == 1
    assert second.master_of[p.pair[0]] == second.master_of[p.pair[1]] in {first.master_of[p.pair[0]], first.master_of[p.pair[1]]}
    assert second.settled == first.settled - 1


def test_order_does_not_matter():
    rows = thirty()
    shuffled = list(rows)
    random.Random(4).shuffle(shuffled)
    assert resolve(shuffled).master_of == resolve(rows).master_of


def test_vectors():
    assert master_id("064ab6000867a82fc1aae7bbbbf3d62558904674cd07672d911107e7ea45d2af") == "M-a7e53489dc"
    assert master_id("1479425de31cd50ffc98c3d015fb5f7ea08fe5c57c8c2981b4f43ee0f12f96c6") == "M-10438b4e7e"


def test_known_masters_older_wins_and_the_other_is_merged():
    rows = thirty()
    a, b = pair_of(rows, "p16A", "p16B")
    known = {a: KnownMaster("M-0000000old", "2025-01-01", "2025-01-01", "derived"),
             b: KnownMaster("M-0000000new", "2026-01-01", "2026-01-01", "derived")}
    r = resolve(rows, [PairVerdict(a, b, "same", "d1", "Joe")], known=known)
    assert r.master_of[a] == r.master_of[b] == "M-0000000old"
    assert ("M-0000000new", "M-0000000old") in r.merged


def test_re_export_with_new_row_order_keeps_ids():
    rows = thirty()
    again = [prow(f"x{i}", r.system, r.client_id, r.first, r.last, r.dob, "", "") for i, r in enumerate(reversed(rows))]
    again = [x.__class__(x.record_key, x.person_key, x.system, x.client_id, x.first, x.last, x.dob, o.address_key, "", o.zip5, "")
             for x, o in zip(again, reversed(rows))]
    a, b = resolve(rows), resolve(again)
    assert {k: v for k, v in a.master_of.items()} == b.master_of
