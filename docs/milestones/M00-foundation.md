# M00: Repo, toolchain, offline guard and copy registry

## Goal

Stand up the repo, the toolchain and the proof machinery every later milestone leans on. When this merges, a fresh Linux or Windows checkout installs from hashed lockfiles, `make test`, `make offline` and `make copy` pass, the offline guard and its tests exist, the approved and forbidden lists live in one file, the copy registry and its lint enforce H11 and H16, and `python -m wholecount.dev check` prints counts only (H8). No product feature is built here.

## Spec sections

- SPEC 2 (H1, H2, H8, H11, H16), 3.1, 3.3, 12.1 to 12.4, 12.6 (the open-file allowance only, not the UI that uses it), 13.1 to 13.3.
- Audit: A-20 (closed by design, with a test). Groundwork for A-25 (every claim has a test).

## Depends on

Nothing. Branch from `main`, which holds `SPEC.md`, `CLAUDE.md`, `docs/` and `legacy/`.

## Branch

`build/m00-foundation`

## Read first

- `SPEC.md` sections 2, 3.1 to 3.3, 12 and 13.1 to 13.3. Then `CLAUDE.md` and `docs/milestones/README.md`.
- `docs/research/offline-enforcement.md`. Recommended design R1 to R6 (line 383 on), the test inventory in 7.1 (line 274), the lockfile section 8 (line 351), R7 (line 1029), R8 (line 1050) and Open risks (line 1058). The code blocks there were run, so start from them. Rename `crosswalk` to `wholecount` and `CROSSWALK_*` to `WHOLECOUNT_*`.
- `docs/audit/A-claims.md`, A-20 (line 265) and A-25 (line 314).
- `legacy/launch.py:170-198` (first-launch `pip install`), `legacy/run.sh`, `legacy/run.bat` (install on every launch) and `legacy/requirements.txt`. Read them to see what to leave out. Do not copy or import anything from `legacy/`.

## What to build

### 1. Skeleton (SPEC 3.3)

- Create every directory in the section 3.3 tree, each Python package with an `__init__.py` holding one docstring line. That covers `wholecount/{guard,copy,settings,session}`, `wholecount/engine/{read,prepare,standardize,geo,outputs}`, `wholecount/ui/{theme,frame,stages,widgets}`, `tools/`, `tests/{unit,rules,audit,golden,invariants,offline,ui,copy,acceptance}`, `tests_windows/`, `installer/` and `build/` (the last three get a `.gitkeep`).
- Do not create the module files the spec lists inside those packages. Each later milestone creates its own.
- `.gitignore` for `.venv/`, `build/` outputs, `dist/`, `__pycache__/`, `.pytest_cache/` and `*.egg-info/`.
- `pyproject.toml`: `[project]` with name, version, `requires-python = ">=3.12,<3.13"` and `dependencies = []` (the `.in` files are the only dependency source, and a test pins this). `[tool.pytest.ini_options]` with `testpaths = ["tests"]`, `addopts = "-ra --strict-markers"` and the markers `claim(id)` and `windows`.
- `wholecount/brand.py` with `PRODUCT_NAME = "Wholecount"`, `PACKAGE_NAME = "wholecount"` and `VERSION = "0.1.0"`. `wholecount/__init__.py` holds only a docstring, so importing the package never imports anything heavy.

### 2. Makefile (same names as CLAUDE.md)

- `test` runs `QT_QPA_PLATFORM=offscreen python -m pytest -q`. `offline` runs `python -m pytest -q tests/offline`. `copy` runs `python -m pytest -q tests/copy`. `run` runs `python -m wholecount`.
- `screens` and `bundle` are stubs that print "arrives in M10" and "arrives in M14" and exit 1. A stub must never look green.
- `lock` recompiles both lockfiles (below). Write the pip-tools command as a comment, since pip-tools is installed in a throwaway venv and is not in either lock.

### 3. Dependencies and lockfiles (SPEC 12.1 layer 5)

- `requirements.in`: `pandas`, `numpy`, `openpyxl`, `lxml>=6.1.3`, `python-geosupport`, `PySide6-Essentials`. Never `PySide6`.
- `requirements.lock`: `pip-compile --generate-hashes --allow-unsafe --strip-extras` on Python 3.12. The research resolved 11 pins and 322 hashes (section 8.2), which is the expected shape. Report the versions you get.
- `requirements-dev.in`: `-c requirements.lock`, `-r requirements.in`, `pytest`, `pytest-qt`, `hypothesis`, `pefile` and `colorama` (listed with no marker, because a Linux compile drops Windows-only markers and pytest needs colorama on Windows). `requirements-dev.lock` is compiled from it and must hold every runtime pin at the same version.
- Install is always `pip install --require-hashes --no-deps --only-binary=:all: -r <lock>`. Never `--no-require-hashes`.
- Fuzzy matching later uses stdlib `difflib`. `thefuzz` is not approved.

### 4. Offline rules and scanners (research R6)

- `tools/offline_rules.py` as in R6: `FORBIDDEN_MODULES`, `FORBIDDEN_DISTS`, `APPROVED_DISTS` (exactly the 11 in R6), the file-name and PE lists, `MODEL_FILE_SUFFIXES`, `URL_RE`, `normalize_dist`. Add `APPROVED_DEV_DISTS`, listing every distribution that appears in `requirements-dev.lock` and not in `APPROVED_DISTS`. Report that list.
- Two standard library modules that later milestones need must stay allowed. `sqlite3` (the saved crosswalk, M13) and `hashlib` with `hashlib.scrypt` (the install secret backup, M13) appear in neither `FORBIDDEN_MODULES` nor the guard's `DENY_MODULES`. Add `ALLOWED_STDLIB = ("sqlite3", "hashlib", "hmac", "secrets", "getpass")` to `offline_rules.py`, and the scan and import tests read it. `hashlib` does not import `ssl`, so this needs no exception.
- `tools/pe_net_imports.py` as in R6. M14 uses it, so M00 only carries it.
- `tools/offline_scan.py`: the scan logic as plain functions (`scan_imports`, `scan_url_literals`, `scan_forbidden_calls`) that take a list of paths and return findings. The static tests call them, and the negative controls call them on a temp file.
- `os.startfile` is forbidden everywhere except one file. `offline_rules.py` holds `STARTFILE_EXEMPT = ("wholecount/ui/shell.py",)` (SPEC 12.6), and `scan_forbidden_calls` skips that exact relative path for the `os.startfile` pattern only. Every other forbidden pattern still applies to it.

### 5. The guard (SPEC 12.1 layer 4, research R2)

- `wholecount/guard/offline_guard.py` from R2. Hoist `DENY_MODULES`, `DENY_PREFIXES` and `DENY_EXACT` to module level with no change in behavior, so tests can read them.
- Add one parameter the research lacks, `allowed_dll_names`. It is a case-insensitive exact match on a bare DLL name, for `ctypes.dlopen` events whose argument is a name rather than a path. SPEC 12.1 allows DPAPI's crypt32, and a bare `crypt32` never matches a path prefix.
- `wholecount/guard/config.py` holds the shared constants. `DPAPI_DLL_NAMES = ("crypt32", "kernel32")`, `DPAPI_SYMBOLS = ("CryptProtectData", "CryptUnprotectData", "LocalFree")` and `GEOSUPPORT_SYMBOLS = ("NYCgeo", "geo")`.
- The open-file allowance (SPEC 12.6). `guard.allow_open_file(path)` registers one exact path for one `os.startfile` call. It is thread-safe and lives in `offline_guard.py` next to the hook.
  - It raises `ValueError` for a path that is not absolute, has a URL scheme (`://`), or is a UNC or WebDAV path. The guard's UNC and WebDAV rule is not overridden (log this as a question, since a file added from a network share cannot then be opened in Excel).
  - A real `os.startfile(path)` raises two audit events, `os.startfile` and `os.startfile/2`. The allowance lets each name through once for the registered path (compared after `ntpath.normcase(ntpath.abspath(...))`) and only when the operation is `open`. The allowance is spent once both names have been seen. A second call, another path, or another operation is denied with `OfflineViolation`. A denied attempt never spends or changes the allowance.
  - Nothing in `wholecount/` calls `allow_open_file` yet. M12 adds `wholecount/ui/shell.py`, the only caller.
- `wholecount/guard/__init__.py` exports `install`, `install_for_app(geosupport_dirs=())`, `allow_open_file`, `OfflineViolation`, `OfflineImportViolation` and a module flag `INSTALLED`. `install_for_app` merges the config constants and returns the violations list.
- Nothing installs the guard at import time. Only entry points call it.

### 6. Entry points

- `wholecount/__main__.py`: the guard install is the first statement, then it prints `<PRODUCT_NAME> <VERSION>` and exits 0. The window arrives in M10.
- `wholecount/app_imports.py`: R6's import list (numpy, pandas, openpyxl, lxml.etree, PySide6 QtCore, QtGui and QtWidgets, geosupport), with `QT_QPA_PLATFORM` defaulting to `offscreen`.
- `wholecount/dev.py` (details in 9).

### 7. Copy registry and lint (H11, H16)

- `wholecount/copy/registry.py` and `wholecount/copy/__init__.py` expose `get(key, **params)`, `claims()` and `all_entries()`. Entries load from `wholecount/copy/en.toml`, one table per key such as `[offline.nothing_leaves]` with `text` and an optional `claim` such as `CL-OFFLINE-01`.
- `get` injects `product` from `brand.PRODUCT_NAME`, formats every `int` parameter with thousands separators, and raises on a missing or unused parameter. No copy text may contain the literal product name.
- `wholecount/copy/problems.toml` starts empty, with a header comment naming the four required keys per reason (`title`, `means`, `check`, `excel`). Later milestones add reasons.
- Claim IDs always take the form `CL-<AREA>-<NN>` (SPEC H11), and a test enforces the pattern. Register one claim now, `CL-OFFLINE-01`, "Nothing leaves this computer." Its proof is the guard and import tests, marked `@pytest.mark.claim("CL-OFFLINE-01")`. Do not register "Client data is written only to the files you download" yet, because no test can prove it before M09.
- `wholecount/copy/us_spelling.txt` holds the starter list of British spellings to reject, about fifteen common words with the -our, -re, -ise, -yse and -ence endings plus the other usual British variants. The words are written only in that file, never in a milestone or any other document the lint scans. Matching is whole-word and case-insensitive.

### 8. `tests/HARD_RULES.md` and `tests/audit/INDEX.md`

- `HARD_RULES.md`: one row per H1 to H16 with the rule in a few words, the test module or modules, and a status. Rows whose tests come later say "arrives in Mxx" and name the planned module (H8 arrives in M01, H11 is in this milestone, H4 in M01 for the first balance and M08 for the second, H9 in M09). H4 has two balances in SPEC v1.1, so its row names both. A hard-rule test may live in any test folder (SPEC 13.2), so a row can name a file in `tests/audit/`, `tests/copy/` or `tests/ui/`.
- `INDEX.md`: a table `ID | Severity | Milestone | Test | Status` with all 101 audit IDs. Take milestone from the README table (A-20 lists `M00, M14`) and severity from the audit files. Status is `pending` for everything except A-20, which is `done` and names its test. Low findings are listed too, with their README milestone.

### 9. `python -m wholecount.dev` (H8)

- First statement installs the guard. Commands register in a dict. Output goes through one printer, `emit(label: CountLabel, value: int, scope=None)`, where `CountLabel` is a closed enum and `scope` may only be a source letter. It prints `label value` with thousands separators and refuses any `str` value.
- `check` imports `wholecount.app_imports` under the guard and prints `pins_runtime`, `pins_dev`, `approved_distributions`, `claims_in_registry`, `audit_ids_listed`, `modules_imported_under_guard` and `guard_violations`. It exits 1 if `guard_violations` is above 0. With `--why` it also prints the denied event names. `check` opens no client file, so those names carry no client value. No other command may print a string.
- Each later milestone adds its command and its labels.

### 10. CI (`.github/workflows/ci.yml`)

- Triggers on push to `main` and `build/**` and on pull requests. One job on `ubuntu-24.04` with Python 3.12, read-only `contents` permission and no secrets.
- The steps check out the repo, set up Python, apt-install the Qt runtime libraries (start with `libegl1 libgl1 libxkbcommon0 libdbus-1-3 libfontconfig1 libglib2.0-0` and adjust until the import test is green), install the dev lock with the three flags, run `make test`, `make offline`, `make copy`.
- A final step downloads the runtime lock for Windows (`pip download --platform win_amd64 --python-version 3.12 --implementation cp --abi cp312 --only-binary=:all: --require-hashes -r requirements.lock`) so a pin with no Windows wheel fails here. That step needs the network and is the only one that does.
- Use the current major versions of `actions/checkout` and `actions/setup-python` and report them. The Windows job arrives in M14.

## Tests to write

Write each failing test first. Every static and lockfile test has a negative control that feeds the helper a bad temp file and asserts it is caught.

- `tests/offline/test_guard_runtime.py`. R6's nine tests, run in a fresh `python -I` subprocess with the repo root on `sys.path`. Add:
  - `test_allowed_dll_names_match_bare_names_only` (`crypt32` passes, `crypt32x` and a path do not, `dlsym` of an unlisted symbol is denied).
  - `test_install_returns_and_logs_violations`.
  - `test_guard_is_not_installed_in_the_pytest_process` (`INSTALLED` is false).
- `tests/offline/test_open_file_allowance.py`, each in a fresh `python -I` subprocess with the guard installed, raising the events with `sys.audit("os.startfile", path, "open")` and `sys.audit("os.startfile/2", path, "open", None, None, 1)` so it runs on Linux.
  - With no allowance, both events are denied.
  - After `allow_open_file(p)`, both events for `p` pass once, and a second pair is denied.
  - Another path, and operation `print`, are denied, and a denied attempt leaves the allowance usable for `p`.
  - `allow_open_file` raises `ValueError` for a relative path, `https://example.com/a.xlsx` and `\\server\share\a.xlsx`.
  - On a Windows-style path, upper and lower case and forward and back slashes match, through the `ntpath_mod` hook.
- `tests/offline/test_stdlib_still_allowed.py`, in a fresh guarded subprocess. `sqlite3.connect(":memory:")` runs a create, insert and select. `hashlib.scrypt(b"pw", salt=bytes(16), n=2**15, r=8, p=1, maxmem=2**26, dklen=32)` returns 32 bytes (the default 32 MiB `maxmem` is too small for these settings, so the test passes it). `hmac`, `secrets` and `getpass` import. No violation is logged. A second test asserts none of the `ALLOWED_STDLIB` names is in `FORBIDDEN_MODULES` or `DENY_MODULES`.
- `tests/offline/test_guard_matches_rules.py`. `FORBIDDEN_MODULES` minus the guard's `DENY_MODULES` equals a pinned, commented exception set (build-only names such as `multiprocessing`). Drift in either list fails.
- `tests/offline/test_static_scan.py`. R6's five checks over `wholecount/**/*.py`, skipping `wholecount/guard/`. Add `test_no_model_files_in_repo` (suffix list, and any `.bin` over 1 MB, outside `legacy/`) and `test_no_import_from_legacy`. Add `test_startfile_only_in_ui_shell`: no file under `wholecount/` or `tools/` uses `os.startfile` except `wholecount/ui/shell.py`. Its negative controls build a temp tree where `wholecount/ui/shell.py` may use it, and `wholecount/ui/other.py` and `tools/x.py` may not. In `shell.py`, `subprocess` and `QDesktopServices` are still caught.
- `tests/offline/test_lockfile.py`. R6's two lock tests for `requirements.lock`, plus:
  - `test_dev_lock_is_hashed_and_clean`.
  - `test_dev_lock_pins_are_approved_or_approved_dev`.
  - `test_dev_lock_has_every_runtime_pin_at_the_same_version`.
  - `test_in_files_name_only_approved_distributions`.
  - `test_pyproject_lists_no_dependencies`.
- `tests/offline/test_import_graph.py`. R6's test using `wholecount.app_imports`.
- `tests/unit/test_layering.py`. By AST: `wholecount/engine` imports no PySide6, no `wholecount.session`, no `wholecount.ui`; `wholecount/session` imports no `wholecount.ui`; `wholecount/ui` imports `wholecount.engine` only through `wholecount.session`.
- `tests/unit/test_layout.py`. The SPEC 3.3 directories exist. `tests/unit/test_brand.py`. The product name appears as a string literal only in `brand.py` and appears in no copy text.
- `tests/unit/test_makefile.py`. The targets exist and the stubs exit 1. Skip when `make` is missing.
- `tests/unit/test_dev_counts_only.py`. The printer rejects a `str` value and a non-letter scope. `python -m wholecount.dev check` run as a subprocess exits 0 and every output line matches `^[a-z_]+( [A-Z]+)? [0-9,]+$`.
- `tests/invariants/test_hard_rules_map.py`. Every H1 to H16 has a row in `HARD_RULES.md`, and every test path in a row marked done exists.
- `tests/copy/test_registry.py`. Keys are unique and lowercase-dotted, claim IDs all start with `CL-`, match `^CL-[A-Z0-9]+(-[A-Z0-9]+)*$` and are unique, `get` formats `1234` as `1,234`, and a missing or extra parameter raises.
- `tests/copy/test_lint.py`. No em dash, no exclamation mark, no emoji (U+1F300 to U+1FAFF, U+2600 to U+27BF, U+FE0F, U+200D), no spelling from `us_spelling.txt`, in every copy text and in `docs/milestones/*.md` and `tests/*.md` (the exclamation check covers copy text only, since code samples contain comparison operators). Negative controls use a temp registry.
- `tests/copy/test_claims_have_tests.py`. Scan `tests/**/*.py` by AST for `@pytest.mark.claim("ID")`. Every registry claim has at least one test, and every marker names a real claim.
- `tests/audit/test_A20_no_launchers.py` (Medium, closed by design). No `run.bat`, `run.sh`, `launch.py`, `*.command`, `*.vbs` or "START HERE" file outside `legacy/` and `docs/`. An AST scan of every `.py` file in `wholecount/` and `tools/` finds no import of `pip`, `streamlit`, `fastapi`, `uvicorn` or `webbrowser`, and no call through them (such as `pip.main` or `webbrowser.open`). Names inside strings and comments don't count, because the deny lists must name them. `tools/offline_rules.py`, `tools/offline_scan.py` and everything under `wholecount/guard/` are exempt, as R6 exempts `offline_guard.py`. A negative control puts `import webbrowser` in a temp file under `wholecount/` and expects it caught. Neither lock names Streamlit, FastAPI or uvicorn. The first statement of `__main__.py` and `dev.py` (after the docstring) installs the guard.
- `tests/audit/test_index_complete.py`. Every `### X-NN` heading in `docs/audit/*.md` has a row in `INDEX.md`, the milestone matches the README table, and every `done` row names a test file that exists. A finding the README lists under more than one milestone (A-20 is under M00 and M14) may name any of them, and its row lists every test that closes it.

## Done when

- [ ] `make test`, `make offline` and `make copy` are green on Linux, and the report gives the pass count from each.
- [ ] The CI run on the pull request is green.
- [ ] A-20 has a passing test and a `done` line in `tests/audit/INDEX.md`, and all 101 IDs are listed with the README milestone.
- [ ] `requirements.lock` has exactly the 11 approved distributions, every pin hashed, and the Windows download step passes.
- [ ] No dependency outside `APPROVED_DISTS` plus the listed `APPROVED_DEV_DISTS`. The report lists every pin and version.
- [ ] `python -m wholecount.dev check` prints `guard_violations 0` on Linux.
- [ ] `guard.allow_open_file` exists with its tests, `sqlite3` and `hashlib.scrypt` pass under the guard, and the scan allows `os.startfile` only in `wholecount/ui/shell.py`.
- [ ] `docs/milestones/M00-REPORT.md` is written, the branch is pushed, the pull request is open, and work has stopped.

## Windows checks for Joe

Run from the repo root in a Command Prompt, on a normal Windows machine with Python 3.12.

1. `py -3.12 -m venv .venv`. It finishes with no output.
2. `.venv\Scripts\activate`. The prompt now starts with `(.venv)`.
3. `pip install --require-hashes --no-deps -r requirements-dev.lock`. It ends with "Successfully installed" and a list. Any "do not match the hashes" message is a failure.
4. `python -m pytest -q`. Everything passes. A few tests may be reported as skipped on Windows, and the report says how many to expect.
5. `python -m wholecount`. It prints the product name and version and returns to the prompt.
6. `python -m wholecount.dev check`. It prints a short list of counts and `guard_violations 0`. This is the first time numpy, pandas, lxml and Qt load on Windows under the guard, so a nonzero number matters. Run it again with `--why` and send the lines it prints. The dev command prints counts only and never shows client values.

## Out of scope

- Any reader, mapping, tidy-up or UI code. No `ProgressMessage` type (M01 builds it).
- The PyInstaller spec, the runtime hook, the installer and firewall rules, bundle tests and the PE scan test (M14). Signing (M14).
- The real Geosupport adapter and its DLL allowlist entries (M05). DPAPI use (M01). Only the config constants exist now.
- Screens and `make screens` (M10). `wholecount/ui/shell.py`, the only caller of `allow_open_file` and `os.startfile`, and its confirmation dialog (M12).
- The install secret, `SecretStore` and every key (M01). The scrypt backup format and the saved crosswalk (M13). Only the allowed-module rule exists now.
- Editing `SPEC.md`, `CLAUDE.md` or `docs/milestones/README.md`. If one is wrong, put the question at the top of the report.
