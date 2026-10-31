"""Re-scoring saved labels when the weights change (M13 CAL-6)."""
from tests.support import calibration as K
from wholecount.session.calibration import current_weights, run_regression


def setup(tmp_path):
    pop = K.population_session(tmp_path)
    cal, dp = K.draw(pop, 20)
    rule = lambda p: "same" if p.score >= 80 else "different"  # noqa: E731
    K.label_all(cal, "Ana", rule)
    K.label_all(cal, "Ben", rule)
    cal.save()
    return pop, dp


def test_unchanged_weights_do_not_drop(tmp_path):
    pop, dp = setup(tmp_path)
    assert not run_regression(pop, unprotect=dp.unprotect).dropped


def test_lowering_dob_exact_drops_and_a_helping_change_does_not(tmp_path):
    pop, dp = setup(tmp_path)
    w = dict(current_weights())
    w["dob_exact"] = 10
    assert run_regression(pop, w, dp.unprotect).dropped
    better = dict(current_weights())
    better["dob_differs"] = -60
    assert not run_regression(pop, better, dp.unprotect).dropped
