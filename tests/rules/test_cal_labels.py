"""Two labelers, hidden labels, disagreements and settling (M13 CAL-2)."""
import pytest

from tests.support import calibration as K
from wholecount.session.calibration import CalibrationRefused, CalibrationSession


@pytest.fixture(scope="module")
def pop(tmp_path_factory):
    return K.population_session(tmp_path_factory.mktemp("pop"))


def refused(code, fn, *a):
    with pytest.raises(CalibrationRefused) as e:
        fn(*a)
    assert e.value.code == code


def test_the_same_name_is_refused(pop):
    cal, _ = K.draw(pop, 3)
    K.label_all(cal, "Joe Reviewer", lambda p: "same")
    for name in ("Joe Reviewer", "  joe   REVIEWER ", "JOE reviewer"):
        refused("labeler_same_person", cal.start, name)


def test_labels_are_hidden_until_both_finish_and_disagreements_settle(pop):
    cal, _ = K.draw(pop, 3)
    ids = [p.pair_id for p in cal.pairs]
    cal.label("Ana", ids[0], "same")
    refused("labels_hidden", cal.labels_for, "Ana", "Ben")
    K.label_all(cal, "Ana", lambda p: "same" if p.score >= 80 else "different")
    cal.label("Ben", ids[0], "unsure")
    refused("labels_hidden", cal.labels_for, "Ben", "Ana")
    refused("labels_hidden", cal.disagreements)
    rule = {ids[0]: "unsure", ids[1]: "different" if cal.labels_for("Ana")[ids[1]] == "same" else "same", ids[2]: "unsure"}
    for p in cal.pairs:
        cal.label("Ben", p.pair_id, rule.get(p.pair_id, cal.labels_for("Ana")[p.pair_id]))
    cal.finish("Ben")
    assert set(cal.disagreements()) == {ids[0], ids[1], ids[2]}
    cal.settle(ids[1], "same")
    cal.settle(ids[0], "unsure")
    assert set(cal.disagreements()) == {ids[2]}
    st = cal.settlement()
    assert st.labels[ids[1]] == "same" and ids[0] in st.dropped and ids[2] in st.dropped


def test_unsure_for_both_is_dropped(pop):
    cal, _ = K.draw(pop, 3)
    K.label_all(cal, "Ana", lambda p: "unsure")
    K.label_all(cal, "Ben", lambda p: "unsure")
    st = cal.settlement()
    assert st.labels == {} and len(st.dropped) == len(cal.pairs)


def test_a_draft_restores_and_one_for_another_batch_is_refused(pop, tmp_path):
    cal, dp = K.draw(pop, 3)
    cal.label("Ana", cal.pairs[0].pair_id, "same")
    again = CalibrationSession.draw(pop, 3, dp.protect, dp.unprotect)
    assert again.restore_draft() and again.labelers[0].labels == {cal.pairs[0].pair_id: "same"}
    other = K.population_session(tmp_path / "o", names=("people_a.csv",))
    other.calibration_dir = pop.calibration_dir
    oc = CalibrationSession.draw(other, 3, dp.protect, dp.unprotect)
    refused("draft_for_other_batch", oc.restore_draft)
