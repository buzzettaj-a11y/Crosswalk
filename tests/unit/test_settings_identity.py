"""settings/identity.toml holds the milestone's starting values."""
from wholecount.engine.identity import load_settings


def test_values():
    s = load_settings()
    assert s["weights"] == {"dob_exact": 42, "dob_near": 26, "dob_differs": -20, "last_exact": 30, "last_overlap": 24,
                            "last_swapped": 20, "first_exact": 26, "first_nick": 22, "first_initial": 8, "addr_exact": 30,
                            "zip_only": 6, "same_system_id": 100, "rare_name_bonus": 8, "rare_name_max_count": 3}
    assert s["bands"] == {"possible_min": 62, "likely_min": 90} and s["limits"] == {"max_bucket": 150}


def test_overrides_are_per_run():
    assert load_settings({"bands": {"possible_min": 40}})["bands"] == {"possible_min": 40, "likely_min": 90}
    assert load_settings()["bands"]["possible_min"] == 62
