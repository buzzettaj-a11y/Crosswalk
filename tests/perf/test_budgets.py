"""tests/perf/budgets.toml holds SPEC 15's table as numbers, seven rows, and nothing changes a budget."""
import re
import tomllib

from tests.conftest import ROOT

BUDGETS = tomllib.loads((ROOT / "tests" / "perf" / "budgets.toml").read_text(encoding="utf-8"))


def spec_table():
    spec = (ROOT / "SPEC.md").read_text(encoding="utf-8")
    section = spec.split("## 15. Performance budgets", 1)[1].split("\n## ", 1)[0]
    rows = re.findall(r"^\| ([^|]+?) \| ([^|]+?) \|$", section, re.M)
    return [(a, b) for a, b in rows if a not in ("Action",) and not set(a) <= {"-", " "}]


def number(text):
    """3 s -> 3000 ms, 200 ms -> 200, under 1.5 GB -> 1536 MB."""
    m = re.search(r"([\d.]+) (s|ms|GB)", text)
    v, unit = float(m.group(1)), m.group(2)
    return int(v * {"s": 1000, "ms": 1, "GB": 1024}[unit])


def test_seven_rows_equal_the_spec():
    table = spec_table()
    assert len(table) == len(BUDGETS) == 7
    assert [number(b) for _, b in table] == [b["budget"] for b in BUDGETS.values()]
    assert [a for a, _ in table] == [b["what"].replace(" (MB)", "").replace(", to redraw", "") for b in BUDGETS.values()]


def test_only_process_is_geosupport_only():
    assert [k for k, b in BUDGETS.items() if b.get("geosupport_only")] == ["process"]
