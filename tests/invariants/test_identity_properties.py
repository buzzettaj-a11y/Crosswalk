"""Properties of identity (H3, H5, H12, P-ID): determinism, named reasons only, the range, master IDs and cannot-links."""
import random

from hypothesis import given, settings
from hypothesis import strategies as st

from tests.fixtures.people.builders import prow
from wholecount.engine.addresskey import address_key
from wholecount.engine.fold import fold
from wholecount.engine.identity import REASONS, PairVerdict, load_settings, resolve, score_from_codes, score_pair

W = load_settings()["weights"]
FIRST = st.sampled_from(["Ana", "Anna", "Bob", "Robert", "Wei", "Li", "Maria", "Mary", "José", "Jose"])
LAST = st.sampled_from(["Perez", "Pérez", "Li", "Wei", "Smith", "Smith Jr", "Garcia Lopez", "Lopez"])
DOB = st.sampled_from(["", "1990-05-06", "1990-06-05", "1990-05-07", "1980-01-01"])
STREET = st.sampled_from(["", "7 Elm St", "7 Elm Ave", "9 Oak St"])
ZIP = st.sampled_from(["11201", "10451"])
REC = st.tuples(FIRST, LAST, DOB, STREET, ZIP, st.sampled_from("AB"))


def build(recs):
    return [prow(f"r{i:03d}", sys, f"{sys}{i}", f, l, d, s, z) for i, (f, l, d, s, z, sys) in enumerate(recs)]


def canon(r):
    return (r.master_of, tuple(sorted((j.pair, j.reason) for j in r.auto_joins)), tuple(sorted((p.pair, p.score) for p in r.proposals)))


@settings(max_examples=60, deadline=None)
@given(st.lists(REC, min_size=1, max_size=12), st.randoms(use_true_random=False))
def test_shuffling_changes_nothing(recs, rnd):
    rows = build(recs)
    a = resolve(rows)
    shuffled = list(rows)
    rnd.shuffle(shuffled)
    assert canon(resolve(shuffled)) == canon(a)


@settings(max_examples=60, deadline=None)
@given(st.lists(REC, min_size=2, max_size=12))
def test_named_reasons_only_and_no_earlier_batch_without_hooks(recs):
    r = resolve(build(recs))
    assert all(j.reason in REASONS and j.reason != "earlier_batch" for j in r.auto_joins)
    joined = {j.pair for j in r.auto_joins}
    for p in r.proposals:
        assert p.pair not in joined


@settings(max_examples=60, deadline=None)
@given(st.lists(REC, min_size=2, max_size=12))
def test_range_and_verdicts(recs):
    rows = build(recs)
    r = resolve(rows)
    assert r.low <= r.settled
    if r.proposals:
        p = r.proposals[0]
        same = resolve(rows, [PairVerdict(*p.pair, "same")])
        assert same.settled == r.settled - 1 and same.low == r.low
        diff = resolve(rows, [PairVerdict(*p.pair, "different")])
        assert diff.settled == r.settled and diff.low >= r.low
        assert diff.master_of[p.pair[0]] != diff.master_of[p.pair[1]]


@settings(max_examples=60, deadline=None)
@given(st.lists(REC, min_size=1, max_size=10))
def test_master_ids_unique_and_stable_when_a_stranger_arrives(recs):
    rows = build(recs)
    r = resolve(rows)
    assert len(set(r.groups)) == r.settled
    stranger = prow("zzz", "C", "Z1", "Quentin", "Xylophone", "1901-01-01", "1 Nowhere Pl", "10301")
    r2 = resolve(rows + [stranger])
    assert all(r2.master_of[k] == v for k, v in r.master_of.items())


@settings(max_examples=100, deadline=None)
@given(REC, REC, st.booleans())
def test_score_from_codes_matches(a, b, rare):
    x, y = build([a, b])
    sc = score_pair(x, y, rare, W)
    assert score_from_codes(sc.evidence, W) == sc.points


@settings(max_examples=100, deadline=None)
@given(st.text(max_size=20), st.integers(1, 999), st.sampled_from(["St", "Ave"]), st.booleans())
def test_fold_idempotent_and_address_key_stable(text, n, typ, upper):
    assert fold(fold(text)) == fold(text)
    a = f"W {n}th {typ}"
    assert address_key("5", a.upper() if upper else a, "10011") == address_key("5", f"West  {n} {typ}.", "10011")


@settings(max_examples=60, deadline=None)
@given(st.lists(REC, min_size=2, max_size=10), st.lists(st.tuples(st.integers(0, 9), st.integers(0, 9), st.booleans()), max_size=8))
def test_a_cannot_link_is_never_violated(recs, picks):
    rows = build(recs)
    keys = [r.person_key for r in rows]
    verdicts = [PairVerdict(keys[i % len(keys)], keys[j % len(keys)], "same" if s else "different", f"d{n}")
                for n, (i, j, s) in enumerate(picks) if keys[i % len(keys)] != keys[j % len(keys)]]
    r = resolve(rows, verdicts)
    for v in verdicts:
        if v.verdict == "different":
            assert r.master_of[v.a] != r.master_of[v.b]
