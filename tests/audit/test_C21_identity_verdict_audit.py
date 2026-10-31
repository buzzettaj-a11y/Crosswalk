"""C-21: identity decisions reached the audit with names and dates. audit_fields holds IDs, the reviewer and the verdict only."""
from tests.fixtures.people.builders import C01_A, C01_B, c01_rows, pair_of
from wholecount.engine.identity import PairVerdict, resolve


def test_audit_fields_hold_no_client_value():
    rows = c01_rows()
    a, b = pair_of(rows, "A2", "B2")
    before = resolve(rows)
    for verdict in ("same", "different"):
        v = PairVerdict(a, b, verdict, "dec-0007", "Joe")
        after = resolve(rows, [v])
        f = v.audit_fields(before.master_of[a], after.master_of[a])
        assert set(f) == {"decision_id", "reviewer", "verdict", "master_before", "master_after"}
        assert f["verdict"] == verdict and f["decision_id"] == "dec-0007" and f["reviewer"] == "Joe"
        text = repr(f)
        for rec in C01_A + C01_B:
            for value in rec[1:]:
                assert value not in text
