"""The calibration note in the detail view and the methods note (M13 CAL-8)."""
import pytest

from tests.support import calibration as K
from wholecount import copy
from wholecount.session import calibration as cs


def saved(tmp_path):
    pop = K.population_session(tmp_path)
    cal, dp = K.draw(pop, 5)
    rule = lambda p: "same" if p.score >= 80 else "different"  # noqa: E731
    K.label_all(cal, "Ana", rule)
    K.label_all(cal, "Ben", rule)
    cal.save()
    return pop, dp


@pytest.mark.claim("CL-CAL-METHODS-01")
def test_the_note_feeds_both_places(tmp_path, monkeypatch):
    pop, dp = saved(tmp_path)
    note = cs.calibration_note(pop, dp.unprotect)
    assert note.calibrated_at == pop.now_iso()[:10] and note.matches_weights and note.line == 62
    assert [b for b, _, _ in note.bands] == [1, 2, 3, 4] and all(n == 5 or n <= 5 for _, n, _ in note.bands)
    from wholecount.session.frame import calibration_line, methods_note
    monkeypatch.setattr(cs, "calibration_note", lambda s, u=None: note)
    line = calibration_line(pop)
    from wholecount.session.frame import calibration_rates
    assert line[0] == note.calibrated_at and line[1] == calibration_rates(note) and "were the same person" in line[1]
    assert note.calibrated_at in methods_note(pop)


@pytest.mark.claim("CL-CAL-EARLIER-01")
def test_earlier_weights_are_said(tmp_path, monkeypatch):
    pop, dp = saved(tmp_path)
    w = dict(cs.current_weights())
    w["dob_exact"] = 41
    monkeypatch.setattr(cs, "current_weights", lambda: w)
    note = cs.calibration_note(pop, dp.unprotect)
    assert not note.matches_weights
    from wholecount.session.frame import calibration_line, methods_note
    monkeypatch.setattr(cs, "calibration_note", lambda s, u=None: note)
    assert copy.get("calibration.earlier_weights") in calibration_line(pop)[1]
    assert copy.get("calibration.earlier_weights") in methods_note(pop)


@pytest.mark.claim("CL-CAL-JOINS-01")
@pytest.mark.claim("CL-CAL-JOINS-02")
@pytest.mark.claim("CL-CAL-RECALL-01")
def test_joins_and_recall_follow_the_labels(tmp_path, monkeypatch):
    from wholecount.engine.calibration.measure import measure
    from wholecount.session.frame import methods_note

    pop = K.population_session(tmp_path)
    cal, dp = K.draw(pop, 5)
    # Every sampled join is right, so the check is met only when 1,000 x wrong <= 5 x n.
    rule = lambda p: "same" if p.kind == "join" or p.score >= 80 else "different"  # noqa: E731
    K.label_all(cal, "Ana", rule)
    K.label_all(cal, "Ben", rule)
    cal.save()
    real = cs.calibration_note
    note = real(pop, dp.unprotect)
    n, wrong, result = note.joins
    assert wrong == 0 and n > 0 and result == "confirmed"
    st = cs.stored_labels(pop, dp.unprotect)
    m = measure(st.populations, [(p.score, p.band, p.label) for p in st.pairs if p.kind == "proposal"])
    assert note.recall_pct == int(m.recall(62) * 100)
    monkeypatch.setattr(cs, "calibration_note", lambda s, u=None: note)
    text = methods_note(pop)
    assert copy.get("calibration.joins.confirmed", n=n, wrong=0) in text
    assert copy.get("calibration.recall", line=62, pct=note.recall_pct) in text
    # A second calibration where every join is wrong misses the check.
    cal2, _ = K.draw(pop, 5, dp)
    K.label_all(cal2, "Ana", lambda p: "different")
    K.label_all(cal2, "Ben", lambda p: "different")
    cal2.save()
    worse = real(pop, dp.unprotect)
    assert worse.joins[2] == "not_confirmed" and worse.joins[1] * 1000 > worse.joins[0] * 5
    monkeypatch.setattr(cs, "calibration_note", lambda s, u=None: worse)
    assert copy.get("calibration.joins.not_confirmed", n=worse.joins[0], wrong=worse.joins[1]) in methods_note(pop)
