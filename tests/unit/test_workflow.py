"""The Windows workflow (M14 section 7). Joe chose to start it by hand only, so its trigger is workflow_dispatch alone."""
import re

from tests.conftest import ROOT

WF = (ROOT / ".github" / "workflows" / "windows.yml").read_text(encoding="utf-8")
CI = (ROOT / ".github" / "workflows" / "ci.yml").read_text(encoding="utf-8")


def test_runs_on_windows_by_hand_with_read_only_permissions():
    assert "runs-on: windows-latest" in WF
    on = re.search(r"^on:\n((?:  .*\n)+)", WF, re.M).group(1)
    assert on.strip() == "workflow_dispatch:"
    assert re.search(r"^permissions:\n  contents: read$", WF, re.M)
    assert "timeout-minutes: 45" in WF


def test_no_secrets_and_both_artifacts():
    assert "secrets." not in WF
    assert "name: wholecount-installer" in WF and "name: wholecount-reports" in WF


def test_require_windows_tests_and_the_bundle():
    assert 'WHOLECOUNT_REQUIRE_WINDOWS_TESTS: "1"' in WF and 'WHOLECOUNT_REQUIRE_BUNDLE: "1"' in WF
    assert "--self-check --self-check-out" in WF and "tests_windows -m windows -rs" in WF


def test_ci_runs_the_bundle_on_every_linux_push():
    assert "make bundle" in CI and "pytest -q tests/bundle" in CI and 'WHOLECOUNT_REQUIRE_BUNDLE: "1"' in CI


def plain_runs_with_a_colon(text):
    """`run:` values written as plain YAML scalars that hold ": ", which YAML reads as a mapping and so rejects the file.
    The project has no YAML parser, so this checks the one shape that broke ci.yml in M14."""
    bad = []
    for i, line in enumerate(text.splitlines(), 1):
        m = re.match(r"\s*(?:- )?run: (.*)$", line)
        if m and m.group(1)[:1] not in ("|", ">", "'", '"') and ": " in m.group(1):
            bad.append(i)
    return bad


def test_no_plain_run_value_holds_a_colon_and_space():
    for f in (ROOT / ".github" / "workflows").glob("*.yml"):
        assert plain_runs_with_a_colon(f.read_text(encoding="utf-8")) == [], f.name


def test_negative_control_for_the_colon_check():
    assert plain_runs_with_a_colon("      - run: pip install --only-binary=:all: -r x\n") == [1]
    assert plain_runs_with_a_colon("        run: >\n          pip install --only-binary=:all: -r x\n") == []
