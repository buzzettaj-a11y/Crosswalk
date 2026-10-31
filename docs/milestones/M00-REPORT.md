# M00 report

## Questions for Joe

Joe answered all five on 2026-10-31 and kept the default each time:
- Network share files stay refused for "open in Excel."
- The work stays on `build/mNN-...` branches.
- The guard install stays as two lines.
- `os.startfile` must say `"open"` explicitly.
- "Cancelled" stays allowed.

No code changed. The questions are below as asked.

1. **Files on a network share can't be opened in Excel.** The milestone told me to log this one. `guard.allow_open_file` refuses UNC and WebDAV paths, and the guard's UNC rule isn't overridden. So a file the operator added from `\\server\share\...` can be read, but the "open the source file" action in M12 will refuse it. A file on a mapped drive letter still works. Default: keep refusing. If you want it allowed, it's a one-line change in the allowance, but then `os.startfile` would hand a network path to Windows.
2. **Which branch the work is on.** The cloud session was set up with a branch named `ccr-4a2904a0-r5rge0`. `CLAUDE.md` and the milestone file both say `build/m00-foundation`, so the work and the pull request are on `build/m00-foundation`. The CI trigger for `build/**` depends on that name. Nothing was pushed to the `ccr-` branch.
3. **"First statement installs the guard."** In `__main__.py` and `dev.py` it's two statements, `from wholecount.guard import install_for_app` and then `install_for_app()`, with nothing between them. The A-20 test checks exactly that pair. Doing it in one statement would mean a semicolon or an `__import__` call, and both read worse. Tell me if you want it as one line.
4. **`os.startfile` must pass `"open"` explicitly.** A real `os.startfile(path)` with no operation raises its audit event with the operation as `None`, and the allowance only accepts `open`. So M12's `shell.py` has to call `os.startfile(path, "open")`. Registering a second path before the first is spent replaces the first.
5. **Spelling list.** The milestone docs use "cancelled" 14 times (M01, M10, M12). It's an accepted American variant, so I left it off the reject list rather than edit those files. The list has 20 words.

Choices made on the most conservative reading:
- `FORBIDDEN_DISTS` also lists the old build's stack: `streamlit`, `fastapi`, `uvicorn`, `python-multipart` and `thefuzz`. Adding to a deny list can't let anything new in.
- `allow_open_file` treats a path with `://` anywhere in it as a URL, even when the path is absolute.

## What was built

- **SPEC 3.1, 3.3.** The full package tree, each package with a one-line docstring and nothing else. `wholecount/brand.py` holds the product name and version. `pyproject.toml` lists no dependencies and pins Python 3.12. The `Makefile` gives the `CLAUDE.md` target names, and the `screens` and `bundle` stubs exit 1.
- **SPEC 12.1 layer 5.** `requirements.in` and `requirements-dev.in`, compiled with hashes on Python 3.12 into `requirements.lock` and `requirements-dev.lock`.
- **SPEC 12.1 layer 4, 12.6.** `wholecount/guard/`: the research's audit hook (R2) with its deny lists at module level, plus `allowed_dll_names` (bare names, exact, case-insensitive) and the thread-safe open-file allowance. `install_for_app()` merges the DPAPI and Geosupport constants from `guard/config.py`. Nothing installs the guard at import time.
- **SPEC 12.4.** `tools/offline_rules.py` (R6, plus `ALLOWED_STDLIB`, `APPROVED_DEV_DISTS`, `STARTFILE_EXEMPT`), `tools/offline_scan.py` (the scans and lock checks as plain functions), `tools/pe_net_imports.py` (carried for M14).
- **Entry points.** `python -m wholecount` installs the guard and prints `Wholecount 0.1.0`. `wholecount/app_imports.py` is R6's import list. `python -m wholecount.dev check` prints counts only through `emit()`, which takes a closed `CountLabel` and an `int` (H8). If the guard denies an import, `check` still prints its counts and then exits 1.
- **H11, H16.** The copy registry in `wholecount/copy/` with `get`, `claims` and `all_entries`, one claim (`CL-OFFLINE-01`, "Nothing leaves this computer."), an empty `problems.toml`, and the wording lint.
- **SPEC 13.2, 13.3.** `tests/HARD_RULES.md` and `tests/audit/INDEX.md`.
- **CI.** `.github/workflows/ci.yml`, one Linux job.

### Lock pins

Runtime, 11 pins and 322 hashes, the same versions the research got:

| Distribution | Version |
| --- | --- |
| et-xmlfile | 2.0.0 |
| lxml | 6.1.3 |
| numpy | 2.5.4 |
| openpyxl | 3.1.5 |
| pandas | 3.1.0 |
| pyside6-essentials | 6.12.0 |
| python-dateutil | 3.0.0 |
| python-geosupport | 1.1.0 |
| shiboken6 | 6.12.0 |
| six | 1.17.0 |
| tzdata | 2026.6 |

Dev, 22 pins: the 11 above at the same versions, plus `APPROVED_DEV_DISTS`:

| Distribution | Version | Why it's there |
| --- | --- | --- |
| colorama | 0.4.6 | pytest needs it on Windows |
| hypothesis | 6.170.14 | property tests |
| iniconfig | 2.3.1 | pytest |
| packaging | 26.3 | pytest |
| pefile | 2024.8.26 | the PE import scan (M14) |
| pluggy | 1.7.0 | pytest |
| pygments | 2.21.0 | pytest |
| pytest | 9.2.0 | test runner |
| pytest-qt | 4.5.0 | UI tests |
| sortedcontainers | 2.4.0 | hypothesis |
| typing-extensions | 4.16.0 | pytest-qt |

### CI action versions

`actions/checkout@v6` and `actions/setup-python@v6`. Both v6 majors are confirmed. One aggregator site claims a v7 of checkout, and I couldn't confirm it from a primary source, so I used v6.

## Tests

| Command | Result |
| --- | --- |
| `make test` | 167 passed |
| `make offline` | 55 passed |
| `make copy` | 38 passed |
| `python -m wholecount.dev check` | `guard_violations 0`, exit 0 |

`dev check` on Linux printed:

```
pins_runtime 11
pins_dev 22
approved_distributions 11
claims_in_registry 1
audit_ids_listed 101
modules_imported_under_guard 719
guard_violations 0
```

New test files:
- `tests/offline/`: `test_guard_runtime.py` (R6's nine, plus AI SDK imports, bare DLL names, the violations list, `install_for_app`, and not installed in pytest), `test_open_file_allowance.py`, `test_stdlib_still_allowed.py`, `test_guard_matches_rules.py`, `test_static_scan.py`, `test_lockfile.py`, `test_import_graph.py`
- `tests/unit/`: `test_layering.py`, `test_layout.py`, `test_brand.py`, `test_makefile.py`, `test_dev_counts_only.py`
- `tests/copy/`: `test_registry.py`, `test_lint.py`, `test_claims_have_tests.py`, plus the shared `lint.py`
- `tests/invariants/test_hard_rules_map.py`
- `tests/audit/`: `test_A20_no_launchers.py`, `test_index_complete.py`
- `tests/support/guarded.py` runs a code body in a fresh `python -I` with the guard installed

Audit IDs closed: **A-20**, by `tests/audit/test_A20_no_launchers.py`. A-25 has its groundwork: every claim needs a marked test, and every marker must name a real claim.

Where I moved things from the milestone text:
- R6's two lockfile checks are in `test_lockfile.py`, not repeated in `test_static_scan.py`. The static scan file has R6's three source checks.
- The `os.startfile` check is by AST, not text, so the scanner's own source and the guard's event names don't trip it. It catches `x.startfile`, `from os import startfile` and `getattr(x, "startfile")`.
- The product-name check on code is case-sensitive, because the package name is the same word in lowercase and appears in module paths. The check on copy text isn't case-sensitive.

**On "write the failing test first".** I wrote the code and the tests in the same pass, not strictly red then green. To check that the tests can fail, every scan and lock check has a negative control, and I broke the guard on purpose seven ways and reran `tests/offline`:
- no allowance
- an allowance that's never spent
- bare DLL names ignored
- DLL names matched by prefix
- `socket` imports allowed
- the `print` operation allowed
- URLs accepted

The first six failed the suite. The seventh passed, because the absolute-path rule also refuses ordinary URLs. I added an absolute path containing `://`, and then that break failed too. I'll go strictly test-first from M01 on.

## Done list

- [x] `make test`, `make offline` and `make copy` are green on Linux: 167, 55 and 38 passed. (This report is itself linted, which adds one test to `make test` and `make copy`.)
- [x] CI is green. The first run on the branch failed before starting any job, because a `:all: ` flag broke the YAML. That's fixed in `19af718`, and [run 2](https://github.com/buzzettaj-a11y/Crosswalk/actions/runs/41145421296) passed every step, including the Windows wheel download. The pull request's own run is on the pull request page.
- [x] A-20 has a passing test and a `done` line in `tests/audit/INDEX.md`, and all 101 IDs are listed with their README milestone (44 High, 40 Medium, 17 Low, matching `AUDIT.md`).
- [x] `requirements.lock` has exactly the 11 approved distributions, every pin hashed. The Windows download step passed locally: all 11 `win_amd64` / `cp312` wheels downloaded under `--require-hashes`.
- [x] Nothing outside `APPROVED_DISTS` plus the listed `APPROVED_DEV_DISTS`. Every pin and version is listed above.
- [x] `python -m wholecount.dev check` prints `guard_violations 0` on Linux.
- [x] `guard.allow_open_file` exists with its tests, `sqlite3` and `hashlib.scrypt` work under the guard, and the scan allows `os.startfile` only in `wholecount/ui/shell.py`.
- [x] This report is written, the branch is pushed, the pull request is open, and work has stopped.

## Windows checks

Run from the repo root in a Command Prompt, on a normal Windows machine with Python 3.12.

- [ ] 1. `py -3.12 -m venv .venv`. It finishes with no output.
- [ ] 2. `.venv\Scripts\activate`. The prompt now starts with `(.venv)`.
- [ ] 3. `pip install --require-hashes --no-deps -r requirements-dev.lock`. It ends with "Successfully installed" and a list. Any "do not match the hashes" message is a failure.
- [ ] 4. `python -m pytest -q`. Everything passes. Expect 3 skipped if `make` isn't installed (the two stub checks and the documented-commands check in `test_makefile.py`). Several tests call `git`, so run it where `git` is on the PATH.
- [ ] 5. `python -m wholecount`. It prints `Wholecount 0.1.0` and returns to the prompt.
- [ ] 6. `python -m wholecount.dev check`. It prints a short list of counts and `guard_violations 0`. This is the first time numpy, pandas, lxml and Qt load on Windows under the guard, so a nonzero number matters. Run it again with `--why` and send the lines it prints. The dev command prints counts only and never shows client values.

Two things that could behave differently on Windows:
- PySide6's `__init__.py` tries to import `QtNetwork` when it finds a `PySide6/openssl` folder. If that happens, `test_import_graph.py` fails and `dev check --why` shows `denied import PySide6.QtNetwork`.
- `test_open_file_allowance.py` uses POSIX-style absolute paths such as `/data/clients.xlsx`. Python 3.12 treats those as absolute on Windows too, so they should pass.

## Screens

None. M00 has no UI.

## Not done

Nothing
