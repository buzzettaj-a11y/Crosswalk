"""The labeled store (M13 CAL-5): no client value, a changed byte refused, and a newer label wins."""
import csv

import pytest

from tests.support import calibration as K
from wholecount.session.calibration import LABELED, CalibrationRefused, load_labels, stored_labels


def values():
    out = set()
    for n in ("people_a.csv", "people_b.csv"):
        with open(K.FIX / n, encoding="utf-8") as f:
            for row in csv.DictReader(f):
                out.update(v for k, v in row.items() if k != "Program" and len(v) >= 4)
    return out


def calibrate(pop, dp=None, rule=lambda p: "same" if p.score >= 80 else "different"):
    cal, dp = K.draw(pop, 5, dp)
    K.label_all(cal, "Ana", rule)
    K.label_all(cal, "Ben", rule)
    cal.save()
    return cal, dp


def test_no_client_value_and_no_string_parameter(tmp_path):
    pop = K.population_session(tmp_path)
    cal, dp = calibrate(pop)
    data = load_labels(pop, dp.unprotect)
    text = repr(data)
    for v in values():
        assert v not in text, v
    assert all(isinstance(c, str) and c.isidentifier() for p in data["pairs"] for c in p["codes"])
    assert set(data) == {"format", "calibrated_at", "weights_digest", "populations", "joins", "known", "baseline_line", "pairs"}
    assert not (pop.calibration_dir / "draft.wcl").exists()
    assert any(e.code == "CALIBRATION" and e.get("reviewer") == ["Ana"] and e.get("second_reviewer") == ["Ben"] for e in pop.audit)


def test_a_flipped_byte_is_refused(tmp_path):
    pop = K.population_session(tmp_path)
    cal, dp = calibrate(pop)
    p = pop.calibration_dir / LABELED
    raw = bytearray(p.read_bytes())
    raw[len(raw) // 2] ^= 1
    p.write_bytes(bytes(raw))
    with pytest.raises(CalibrationRefused) as e:
        load_labels(pop, dp.unprotect)
    assert e.value.code == "label_file_damaged"


def test_a_second_calibration_adds_and_the_newer_label_wins(tmp_path):
    pop = K.population_session(tmp_path)
    cal, dp = calibrate(pop)
    first = {(p.a, p.b): p.label for p in stored_labels(pop, dp.unprotect).pairs}
    cal2, _ = calibrate(pop, dp, rule=lambda p: "different")
    second = {(p.a, p.b): p.label for p in stored_labels(pop, dp.unprotect).pairs}
    assert set(first) <= set(second)
    assert all(v == "different" for v in second.values())
