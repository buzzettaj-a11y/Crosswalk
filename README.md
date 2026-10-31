# Wholecount

Wholecount is an offline Windows desktop tool for nonprofits in New York City. It merges a nonprofit's client lists from different systems into one master list, on one computer, with no network and no AI. It gives two numbers: how many different people the organization served (Goal 1), and how many each program served (Goal 2).

## Install

Run the signed installer, `Wholecount-Setup-<version>.exe`. It needs administrator approval and installs for all users. It also adds two Windows Firewall rules that block `Wholecount.exe` from the network. IT staff should read `docs/IT_TRUST.md` first. It covers the firewall rules, checking the signature, trusting the certificate and where data lives.

The user guide is in the app (press F1) and in `docs/USER_GUIDE.md`. `docs/REFERENCE_DATA.md` explains Geosupport Desktop Edition and the address reference file.

## Run from source

Python 3.12 on Windows or Linux.

```
python3.12 -m venv .venv && . .venv/bin/activate      # Windows: py -3.12 -m venv .venv; .venv\Scripts\activate
pip install --require-hashes --no-deps -r requirements-dev.lock
make run
```

## Build and release

- `make bundle` builds the one-folder app with PyInstaller into `dist/Wholecount/` and checks it with `tools/check_bundle.py`. It installs nothing; install `requirements-build.lock` the same way first.
- On Windows, `tools\release.ps1` builds, signs the exe, compiles the installer with Inno Setup and signs it. `docs/SIGNING.md` covers the certificate.
- The Windows workflow (`.github/workflows/windows.yml`) builds, installs, tests and uninstalls on a GitHub runner. It is started by hand from Actions.

## Tests

| Command | What it runs |
| --- | --- |
| `make test` | The whole suite, with Qt offscreen |
| `make offline` | The offline and no-AI checks only |
| `make copy` | Copy registry checks: claim tests, spelling, no em dashes |
| `make screens` | Renders every stage to `build/screens/` |
| `make docs-check` | Fails when `docs/USER_GUIDE.md` is out of date with the copy registry, or a doc names a file, command or function that isn't there |

## Where things are

| Path | What it holds |
| --- | --- |
| `wholecount/engine/` | The rules: reading, tidying, matching, checking, placing, copies, people, programs and counts. No Qt. |
| `wholecount/session/` | The session: set-up, decisions, undo, staleness, saved progress, the crosswalk and calibration |
| `wholecount/ui/` | The Qt Widgets window. It reaches the engine only through the session layer. |
| `wholecount/copy/` | Every sentence a person reads, and the user guide builder |
| `wholecount/guard/` | The in-process offline guard |
| `wholecount/settings/` | Thresholds and word lists |
| `wholecount/sample_data/` | The five example files, `EXPECTED.json` and the sample reference |
| `build/` | The PyInstaller spec, its lists and the runtime hook |
| `installer/` | The Inno Setup script |
| `tools/` | Developer tools: the offline rules and scanner, data builders, build, signing and docs scripts |
| `tests/` | The test suite; `tests_windows/` holds the Windows-only tests |
| `docs/` | The user guide, the IT and signing notes, reference data, the spec's milestones and reports |

## The guarantees

| Guarantee | Layer (SPEC 12.1 and 12.2) | Proved by |
| --- | --- | --- |
| Windows blocks the program from the network in both directions | Layer 1, Windows Firewall | `tests_windows/test_firewall_probe.py`, `tests/unit/test_iss.py` |
| No network module is in the build | Layer 2, not in the build | `tests/bundle/test_bundle.py`, `tests/bundle/test_spec_lists.py` |
| Libraries get local files only, with no URL anywhere | Layer 3, local file objects only | `tests/rules/test_P_READ_10_no_urls.py`, `tests/offline/test_static_scan.py` |
| A network call, network path or network import is refused while it runs | Layer 4, the in-process guard | `tests/offline/test_guard_runtime.py`, `tests/offline/test_open_file_allowance.py` |
| Only reviewed packages, pinned by hash | Layer 5, supply chain | `tests/offline/test_lockfile.py`, `tests/offline/test_lockfile_build.py` |
| No AI of any kind, and no model files | No AI (SPEC 12.2) | `tests/offline/test_lockfile.py`, `tests/bundle/test_bundle.py` |

## What cannot be guaranteed

- An administrator can remove the firewall rule.
- A managed computer can ignore local rules.
- C and C++ code isn't seen by the audit hook. That covers Qt, libxml2 and the Geosupport DLL.
- A mapped network drive looks like a local path.

The research's other open risks, in plain words:

- **Native code is outside the audit hook.** Qt, libxml2 and the Geosupport DLL could make calls Python never sees. Nothing documented says they do, and nothing says they never do.
- **Geosupport's own behavior is unknown until its import table has been read.** That check (`tests_windows/test_geosupport_imports.py`) runs on a computer with Geosupport installed and hasn't run yet.
- **Hash pins prove the same bytes as before, not safe bytes.** The build tools are pinned too, and the bundle scan runs again on every version bump.
- **A list of AI package names can never be complete.** The exact list of allowed packages is the real control. "No AI" describes the shipped program, and says nothing about how its code was written.
- **The guard is not a sandbox.** Anyone who can run their own Python inside the process can get around it, which is outside what it is for.

What the Windows runs have shown so far: the Windows workflow and the Windows Sandbox check haven't run yet. The Linux build passes every bundle check and the self-check. Until the Windows runs pass, the firewall rule, the Windows build's contents and the installer are tested only by reading.

## Licenses

`licenses/` holds the license of every package that ships, the Python license, the PyInstaller bootloader license, the Archivo font's OFL and a notice for the NYC data. Qt for Python is used under the LGPL 3; `licenses/PySide6-LGPL-NOTICE.txt` says how to replace its libraries.
