"""Compares a perf run's output with tests/perf/budgets.toml and writes perf-report.txt (SPEC 15). A dev tool that never
ships.

    python -m wholecount.dev perf --set DIR [--fake] > perf-out.txt
    python tools/perf_report.py perf-out.txt [--out perf-report.txt] [--startup-ms N] [--baseline tests/perf/baseline.json]

The report is a plain table of budget, measured, and ok or over. A run on the fake geocoder is labeled as such, and its
Process time is never accepted as the Geosupport row. With --baseline it also lists every value more than 1.5 times its
baseline, for the CI regression alarm.
"""
import argparse
import json
import pathlib
import sys
import tomllib

ROOT = pathlib.Path(__file__).resolve().parents[1]
BUDGETS = ROOT / "tests" / "perf" / "budgets.toml"
ALARM = 1.5


def parse(text):
    """{label: int} and the backend word from the perf command's lines."""
    values, backend = {}, None
    for line in text.splitlines():
        parts = line.split()
        if len(parts) == 2 and parts[0] == "backend":
            backend = parts[1]
        elif len(parts) == 2 and parts[1].lstrip("-").isdigit():
            values[parts[0]] = int(parts[1])
    return values, backend


def rows(values, backend, budgets=None):
    """[(what, label, budget, measured or None, status)]. status is ok, over, not measured, or not accepted."""
    budgets = budgets or tomllib.loads(BUDGETS.read_text(encoding="utf-8"))
    out = []
    for key, b in budgets.items():
        for label in b["measured"]:
            v = values.get(label)
            if v is None:
                status = "not measured"
            elif b.get("geosupport_only") and backend != "geosupport":
                status = "not accepted"
            else:
                status = "ok" if v <= b["budget"] else "over"
            out.append((b["what"], label, b["budget"], v, status))
    return out


def alarms(values, baseline):
    return sorted(k for k, base in baseline.items() if k in values and base > 0 and values[k] > ALARM * base)


def render(values, backend, baseline=None):
    lines = [f"Backend: {backend or 'unknown'}"]
    if backend == "fake":
        lines.append("This run used the fake geocoder. Its Process time is not the Geosupport number.")
    lines.append("")
    table = rows(values, backend)
    w = max(len(r[0]) for r in table)
    lines.append(f"{'Action'.ljust(w)}  {'Label'.ljust(16)}  {'Budget':>8}  {'Measured':>9}  Status")
    for what, label, budget, v, status in table:
        lines.append(f"{what.ljust(w)}  {label.ljust(16)}  {budget:>8}  {'' if v is None else v:>9}  {status}")
    for k in ("rows", "files"):
        if k in values:
            lines.append(f"{k}: {values[k]}")
    if baseline is not None:
        over = alarms(values, baseline)
        lines.append("")
        lines.append("More than 1.5 times the baseline: " + (", ".join(over) if over else "none"))
    return "\n".join(lines) + "\n"


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("output")
    ap.add_argument("--out", default="perf-report.txt")
    ap.add_argument("--startup-ms", type=int)
    ap.add_argument("--baseline")
    ap.add_argument("--github", action="store_true", help="also write the GitHub job summary and a warning per alarm")
    a = ap.parse_args(argv)
    values, backend = parse(pathlib.Path(a.output).read_text(encoding="utf-8"))
    if a.startup_ms is not None:
        values["startup_ms"] = a.startup_ms
    baseline = json.loads(pathlib.Path(a.baseline).read_text(encoding="utf-8")) if a.baseline else None
    text = render(values, backend, baseline)
    pathlib.Path(a.out).write_text(text, encoding="utf-8")
    sys.stdout.write(text)
    if a.github:
        import os

        summary = os.environ.get("GITHUB_STEP_SUMMARY")
        if summary:
            with open(summary, "a", encoding="utf-8") as f:
                f.write("## Performance (regression alarm, never pass or fail)\n\n```\n" + text + "```\n")
        for k in alarms(values, baseline or {}):
            print(f"::warning title=Performance::{k} is more than 1.5 times its baseline")
    return 0


if __name__ == "__main__":
    sys.exit(main())
