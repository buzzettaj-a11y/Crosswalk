"""M15 performance finding: Match_Confidence was worked out one person at a time over every proposal and every record, which
made the Download stage take 27 s on 19,000 rows. master_match_confidences answers for everyone in one pass, and each answer
equals the one-person rule (CONF-5)."""
from tests.support.example_session import example_session
from wholecount.engine.confidence import master_match_confidence, master_match_confidences


def test_the_batch_equals_the_one_person_rule(tmp_path):
    s = example_session(tmp_path)
    ident = s.results.identity
    masters = set(ident.master_of_record.values())
    batch = master_match_confidences(ident)
    assert {m: master_match_confidence(m, ident) for m in masters} == {m: batch[m] for m in masters}
    assert {"likely", "possible", "certain", "single"} >= set(batch.values()) and len(set(batch.values())) >= 3
