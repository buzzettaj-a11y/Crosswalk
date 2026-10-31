"""Who is the same person (SPEC 6.8, P-ID-1 to P-ID-7) and M06's ID rules."""
import inspect
import re

import pytest

from tests.conftest import ROOT
from tests.fixtures.people.builders import c01_rows, crow, pair_of, prow, to_person
from wholecount.engine import identity
from wholecount.engine.copies import DifferentPeople, key_modes, split_group
from wholecount.engine.identity import (EVIDENCE_CODES, PairVerdict, block_keys, load_settings, resolve, score_from_codes,
                                        score_pair)

W = load_settings()["weights"]


def test_P_ID_1_block_key_families():
    r = prow("a", "A", "1", "Ana", "Perez", "1990-05-06", "7 Elm St", "11201")
    fams = set(block_keys(r).values())
    assert fams == {"K1", "K2", "K3", "K4", "id"}
    keys = block_keys(r)
    assert "K1y:perez|1990" in keys and "K1md:perez|0506" in keys and "K4:ana|perez" in keys
    assert not any(k.startswith(("dob:", "addr:")) for k in keys)


def test_P_ID_1_swapped_columns_still_meet():
    rows = [prow("a", "A", "1", "Wei", "Li", "1980-01-01", "1 Oak St", "11201"),
            prow("b", "B", "2", "Li", "Wei", "1980-01-01", "1 Oak St", "11201")]
    (p,) = resolve(rows).proposals
    assert "names_swapped" in [e.code for e in p.evidence]


def test_P_ID_1_big_buckets_are_skipped_and_counted():
    rows = [prow(f"r{i}", "A", str(i), "Ana", "Perez", "", f"{i} Elm St", "11201") for i in range(5)]
    r = resolve(rows, settings={"limits": {"max_bucket": 3}})
    assert r.skipped_buckets > 0


def test_P_ID_2_score_is_a_sum_of_weights():
    rows = c01_rows()
    f = {x.record_key: x for x in rows}
    sc = score_pair(f["A3"], f["B3"], False, W)
    assert sc.points == score_from_codes([e for e in sc.evidence], W) == 112
    assert "suffix_differs" in sc.cautions and "suffix_differs" not in sc.evidence


def test_P_ID_3_joins_only_for_named_reasons():
    src = inspect.getsource(identity.resolve) + inspect.getsource(identity.four_exact_facts)
    assert not re.search(r"(points|score)\s*>=?\s*\S*(auto|same_system_id|100)", src)
    for j in resolve(c01_rows()).auto_joins:
        assert j.reason in identity.REASONS


def test_P_ID_3_four_facts_need_unit_and_suffix_to_agree():
    a = prow("a", "A", "1", "Ana", "Perez", "1990-05-06", "7 Elm St", "11201", unit="2B")
    assert [j.reason for j in resolve([a, prow("b", "B", "2", "Ana", "Perez", "1990-05-06", "7 Elm St", "11201", unit="2B")]).auto_joins] == [
        "four_exact_facts"]
    assert resolve([a, prow("b", "B", "2", "Ana", "Perez", "1990-05-06", "7 Elm St", "11201", unit="5C")]).auto_joins == ()
    assert resolve([prow("a", "A", "1", "Ana", "Perez", "1990-05-06", "7 Elm St", "11201"),
                    prow("b", "B", "2", "Ana", "Perez Jr", "1990-05-06", "7 Elm St", "11201")]).auto_joins == ()


def test_P_ID_4_twins_and_parent_child_are_proposals():
    twins = [prow("a", "A", "1", "Ana", "Perez", "2001-01-01", "7 Elm St", "11201"),
             prow("b", "B", "2", "Eva", "Perez", "2001-01-01", "7 Elm St", "11201")]
    parent = [prow("a", "A", "1", "Luis", "Diaz", "1970-04-04", "7 Elm St", "11201"),
              prow("b", "B", "2", "Luis", "Diaz Jr", "1970-04-04", "7 Elm St", "11201")]
    for rows in (twins, parent):
        r = resolve(rows)
        assert r.auto_joins == () and len(r.proposals) == 1


def test_P_ID_5_same_id_records_always_compared():
    rows = [crow("a", "t", "S", "7", "Ana", "Perez", "1990-05-06", "7 Elm St", "11201"),
            crow("b", "t", "S", "7", "Beth", "Lee", "1950-09-09", "1 Far Rd", "10451")]
    (g,) = [split_group(("a", "b"))]
    modes = key_modes([g], {g.group_id: DifferentPeople()}, rows=rows)
    (p,) = resolve([to_person(c, modes) for c in rows]).proposals
    assert p.band == "possible" and p.score < 62 and "same_system_id_differs" in [e.code for e in p.evidence]


def test_P_ID_6_verdicts():
    rows = c01_rows()
    ab, cd = pair_of(rows, "A2", "B2"), pair_of(rows, "A4", "B4")
    r = resolve(rows, [PairVerdict(*ab, "same", "d1", "Joe")])
    assert r.master_of[ab[0]] == r.master_of[ab[1]] and ab not in {p.pair for p in r.proposals}
    r = resolve(rows, [PairVerdict(*ab, "different", "d1", "Joe")])
    assert ab not in {p.pair for p in r.proposals}
    # A cannot-link through a third record refuses a same verdict, and says so.
    k = {x.record_key: x.person_key for x in rows}
    vs = [PairVerdict(k["A2"], k["B2"], "same", "d1"), PairVerdict(k["A2"], k["A4"], "different", "d2"),
          PairVerdict(k["B2"], k["A4"], "same", "d3")]
    r = resolve(rows, vs)
    assert len(r.refused) == 1 and r.refused[0].decision_id in ("d1", "d3")
    assert r.master_of[k["A2"]] != r.master_of[k["A4"]]
    assert resolve(rows, list(reversed(vs))).refused == r.refused
    # A batch verdict beats an inherited one on the same pair.
    r = resolve(rows, [PairVerdict(*cd, "same", "old", inherited=True), PairVerdict(*cd, "different", "new")])
    assert r.master_of[cd[0]] != r.master_of[cd[1]]


def test_P_ID_7_split_a_four_facts_join_and_a_same_id_join():
    rows = c01_rows()
    p = pair_of(rows, "A1", "B1")
    assert resolve(rows, [PairVerdict(*p, "different", "d1")]).settled == 12
    enrolled = [crow("e1", "t", "S", "7", "Ana", "Perez", "1990-05-06", "7 Elm St", "11201", "Housing"),
                crow("e2", "t", "S", "7", "Ana", "Perez", "1990-05-06", "7 Elm St", "11201", "Youth")]
    assert resolve([to_person(c) for c in enrolled]).settled == 1
    g = split_group(("e1", "e2"))
    modes = key_modes([g], {g.group_id: DifferentPeople()}, split_rows=("e1", "e2"), rows=enrolled)
    assert modes == {"e1": "row", "e2": "row"}
    people = [to_person(c, modes) for c in enrolled]
    k = {x.record_key: x.person_key for x in people}
    r = resolve(people, [PairVerdict(k["e1"], k["e2"], "different", "d1")])
    assert r.settled == 2 and r.auto_joins == ()


def test_ID_5_floor_only_without_a_different_verdict():
    rows = [crow("a", "t", "S", "7", "Ana", "Perez", "1990-05-06", "7 Elm St", "11201"),
            crow("b", "t", "S", "7", "Beth", "Lee", "1950-09-09", "1 Far Rd", "10451")]
    g = split_group(("a", "b"))
    people = [to_person(c, key_modes([g], {g.group_id: DifferentPeople()}, rows=rows)) for c in rows]
    k = {x.record_key: x.person_key for x in people}
    assert resolve(people, [PairVerdict(k["a"], k["b"], "different")]).proposals == ()


def test_ID_9_range():
    r = resolve(c01_rows())
    assert r.low <= r.settled and len(set(r.low_master_of.values())) == r.low


def test_ID_10_rare_bonus_only_via_k4():
    rows = c01_rows()
    assert not any("rare_name" in [e.code for e in p.evidence] for p in resolve(rows).proposals)


def test_ID_11_audit_fields_only():
    v = PairVerdict("b", "a", "same", "d9", "Joe")
    assert (v.a, v.b) == ("a", "b")
    assert v.audit_fields("M-1", "M-2") == {"decision_id": "d9", "reviewer": "Joe", "verdict": "same", "master_before": "M-1",
                                             "master_after": "M-2"}


def test_ID_12_calibration_hooks():
    rows = [prow("a", "A", "1", "Bob", "Smith", "", "1 Oak St", "11201"), prow("b", "B", "2", "Robert", "Smith", "", "9 Pine Ave", "10451")]
    r = resolve(rows, settings={"bands": {"possible_min": 40}}, keep_compared=True)
    (p,) = r.proposals
    assert p.score == 60 and p.features and r.compared == frozenset({p.pair})
    assert resolve(rows).compared is None


def test_evidence_codes_are_closed():
    assert len(EVIDENCE_CODES) == 16
    for p in resolve(c01_rows()).proposals:
        assert {e.code for e in p.evidence + p.cautions} <= set(EVIDENCE_CODES)


def test_no_score_threshold_decides_a_join():
    text = (ROOT / "wholecount" / "engine" / "identity.py").read_text(encoding="utf-8")
    assert "AUTO_THRESHOLD" not in text and "auto_min" not in text
