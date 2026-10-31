# M14 report

## Questions for Joe

The Linux half of M14 is done. Three done-list items need the Windows workflow, which you chose to start by hand. Questions 1 to 3 are the milestone's own questions.

1. **The publisher name on the signature (SPEC 17 Q6).** It reads "Joe Buzzetta" now, from the `publisher` setting in `tools/signing.json`. The certificate subject, the installer's publisher and the version resource all follow that one setting. Should a release carry a business name instead?
2. **Per-machine installs only.** The installer needs administrator approval and installs for all users, because the firewall rules need administrator rights. No per-user install is offered. Is that right for the client's computers?
3. **The cost of the Windows job.** One run builds, installs, tests and uninstalls, with a 45-minute limit. GitHub bills Windows runner minutes at twice the Linux rate on private repositories, so one full run can use up to 90 Linux-minute equivalents of the free allowance. Public repositories don't pay for hosted runners. That's from GitHub's billing page as I remember it, and I couldn't check today's rates, so it's **Unconfirmed**. Running it by hand, as you chose, keeps it to the runs you start.
4. **Please start the Windows workflow once.** Go to Actions, then `windows`, then Run workflow, on the `build/m14-build-install` branch. Three done-list items can only finish there:
   - a green Windows run, with any unexpected skip failing it
   - the signed installer and its checksum, uploaded as the `wholecount-installer` artifact
   - the re-measured `PE_NETWORK_IMPORT_ALLOWLIST`

   The same run answers the questions the research left open:
   - whether the hosted runner is elevated
   - whether `x64compatible` is Inno's accepted value
   - whether `netsh`'s rule name is PowerShell's `DisplayName`
   - which modules the frozen Windows build is missing, if any

   I'll fold the results into this report and the allowlist in a follow-up.
5. **No district files ship.** M05 couldn't fetch the boundary files, so `data/districts/` holds only its README.
   - The self-check's `data.districts` checks that a point at sea gets no district. The "point in the city gets a district" half runs only once the files are there.
   - `NYC-DATA-NOTICE.txt` says no district files are shipped.

Readings I took. The default is built in each case.

6. **The build lock is constrained by `requirements-dev.lock`, not only `requirements.lock`.** The Windows job installs both locks together, so the shared pins (`packaging`, `pefile`) must agree with the dev lock.
   - `pefile` and `pywin32-ctypes` are named in `requirements-build.in` without markers, because a Linux compile drops Windows-only markers. The same goes for `colorama` in the dev lock.
   - `APPROVED_BUILD_DISTS` is `altgraph`, `pyinstaller`, `pyinstaller-hooks-contrib`, `pywin32-ctypes` and `setuptools`. PyInstaller is 6.22.3.
7. **The pip-flag scan skips comment lines.** The Makefile's comment explains how to install pip-tools in a throwaway venv, and a comment runs nothing. Every real `pip install` line has all three flags.
8. **The Windows workflow runs only by hand (`workflow_dispatch`),** as you chose, not on every push and pull request as the milestone says.
   - `ci.yml` gained the milestone's step, so `make bundle` and the bundle tests run on every Linux push, with `WHOLECOUNT_REQUIRE_BUNDLE=1`.
   - The lock comparison on the runner downloads both locks for `win_amd64` with `--require-hashes`. It doesn't also run `pip-compile` there, because pip-tools is in no lock.
9. **The icon is the top bar's blue square, drawn by Qt** (`tools/make_icon.py`).
10. **The self-check's IDs.** It runs 19 checks on Linux and 22 on Windows.
    - Windows adds `guard.denies_unc`, `secret.roundtrip` and `dpapi.roundtrip`.
    - The milestone's `outputs.nine_files` and `secret.roundtrip` are both there.
    - `pipeline.sample` compares tables, rows received, counted, not counted yet, set aside, Goal 1 and Goal 2 with `EXPECTED.json`. Its table count is the included tables plus the workbook table its header decision includes, because `EXPECTED.json` lists the workbook as 0 included before that choice.
    - It runs with a fresh in-memory secret and never touches the real profile.
    - It passes from source under the guard, and from the frozen Linux build.
11. **The guard probes live in `wholecount/guard/probe.py`.** The network-path check needs a network path written out, and the guard package is the one place the static scan exempts, because it names what it forbids. `tests/copy/test_frame_claims.py` now scans the same source list as M00's static scan, which leaves out the guard.
12. **A-20's provenance allowlist has three entries the milestone doesn't list,** each with its reason in the test:
    - `wholecount/ui/theme/fonts/OFL.txt`, the font's license text
    - `tools/data/README.md`, where the hand-saved ZIP and district files came from
    - `tools/offline_scan.py`, whose pip check names pip

    Inside the guard, network-path examples are exempt from the URL check. Its http URLs are not.
13. **M09's excepthook was never installed before.** The app now installs it, with the crash box as its one added handler.
14. **The installer's Geosupport check copies `discover()` exactly.** It looks for `GEOFILES`'s parent folder (machine, then user), then the two standard folders. It doesn't look for a DLL name, because `discover()` doesn't. The Windows test reads `bin\NYCGEO.dll`, the name python-geosupport loads.
15. **`install_for_app` is now idempotent.** The runtime hook and `__main__` both install it, and a second call adds no second audit hook.
16. **`QApplication` gets only the program name now,** so no Qt switch can arrive on the command line.

Changes to earlier tests:
- `tests/unit/test_makefile.py`: `make bundle` isn't a stub any more. The test now checks that `installer`, `sign` and `release` print `Windows only` and fail elsewhere.
- `tests/copy/lint.py`: the doc lint covers `docs/IT_TRUST.md` and `docs/SIGNING.md`.

## What was built

- **Build lock.** `requirements-build.in` and `.lock`, `APPROVED_BUILD_DISTS`, and a `lock` target that compiles it too.
- **PyInstaller.**
  - `build/spec_lists.py`, `build/wholecount.spec` and `build/rthook_offline.py`
  - `tools/make_version_info.py`, `tools/make_icon.py`, `tools/collect_licenses.py` and `tools/check_bundle.py`
  - `licenses/` (16 files)
  - `make bundle`, plus `installer`, `sign` and `release`, which are Windows only
- **App.** `wholecount/selfcheck.py` with the `--self-check --self-check-out DIR` flag, `wholecount/crash.py`, `wholecount/app_licenses.py` and `wholecount/guard/probe.py`.
- **Installer.** `installer/wholecount.iss`: firewall rules in and out, the check that they were added, the Geosupport page, the uninstall message and the welcome text.
- **Scripts.** `tools/build.ps1`, `make_cert.ps1`, `sign.ps1`, `release.ps1`, `signing.json` and `tools/sandbox/`. None of them ran here, and their unchecked steps say **Unconfirmed**.
- **Docs.** `docs/IT_TRUST.md` and `docs/SIGNING.md`.
- **Workflows.** `.github/workflows/windows.yml` (by hand only) and one added step in `ci.yml`.

The Linux build is 391 files and 203 MB. `check_bundle.py` finds no forbidden module, forbidden file, model file or unwanted file.

## Tests

| Command | Result |
| --- | --- |
| `make test` | 4026 passed, 11 skipped (Windows only) |
| `make offline` | 72 passed |
| `make copy` | 1707 passed |
| bundle tests on the Linux build | 18 passed, 4 skipped (Windows only) |
| `tests_windows` on Linux | 18 skipped (Windows only) |

New test files:
- **Bundle.** `tests/bundle/test_spec_lists.py`, `test_bundle.py`, `test_pe_scan.py` and `test_licenses.py`.
- **Build and installer.** `tests/offline/test_lockfile_build.py`, `tests/unit/test_iss.py`, `test_docs_match_installer.py`, `test_wsb.py` and `test_workflow.py`.
- **App.** `tests/unit/test_selfcheck.py`, `test_crash.py` and `test_guard_idempotent.py`.
- **Audit.** `tests/audit/test_A17_no_process_killing.py` and `test_A20_installer_offline.py`.
- **Windows** (`tests_windows/`): `test_firewall_probe.py`, `test_installer_rules.py`, `test_uninstall_closes_only_wholecount.py`, `test_frozen_selfcheck.py`, `test_signature.py`, `test_geosupport_installer_check.py`, `test_geosupport_imports.py` and `test_ps1_syntax.py`, with a `conftest.py` that fails a skip in required mode.

Audit IDs closed:

| ID | Severity | Test |
| --- | --- | --- |
| A-17 | Medium | `tests/audit/test_A17_no_process_killing.py` |
| A-20 | Medium | `tests/audit/test_A20_installer_offline.py` (with M00's `test_A20_no_launchers.py`) |

## Done list

- [x] `make test`, `make offline` and `make copy` are green on Linux, with the counts above. `make bundle` builds on Linux and the bundle tests pass on that folder.
- [ ] The Windows workflow is green. **Waiting on question 4.** It runs only by hand.
- [ ] The signed installer and its checksum are uploaded as a workflow artifact. **Waiting on question 4.**
- [ ] `PE_NETWORK_IMPORT_ALLOWLIST` is re-measured on the runner's interpreter. **Waiting on question 4.** The list now is M00's, measured on conda-forge Python: `python312.dll`, `select.pyd`, `qt6core.dll`, `etree.cp312-win_amd64.pyd` and `objectify.cp312-win_amd64.pyd`.
- [x] A-17 and A-20 have passing tests and a `done` line in `tests/audit/INDEX.md`.
- [x] `docs/IT_TRUST.md` and `docs/SIGNING.md` are written, every unchecked step is marked Unconfirmed, and `make copy` lints them.
- [x] This report lists each difference, the questions for Joe, and the cost of the Windows job. The runner's elevation and the first-run hidden imports wait on question 4.
- [x] This report is written, the branch is pushed, and the pull request is open.

## Windows checks

The milestone's twelve checks use the installer from the workflow's artifact, so they start after question 4. Use the installer from the workflow run (Actions, the run, Artifacts, `wholecount-installer`). Unzip it into a new folder. These steps use the CI certificate, which is for testing only. Delete it at step 12.

- [ ] 1. Open PowerShell in that folder and run `Get-FileHash .\Wholecount-Setup-*.exe -Algorithm SHA256`. The value matches the checksum file in the artifact.
- [ ] 2. Right-click the installer, choose Properties, and open the Digital Signatures tab. A signature from `Wholecount CI (not for release)` is listed. Before you trust the certificate it will not say it is OK.
- [ ] 3. Import the `.cer` from the artifact: right-click it, Install Certificate, Local Machine, place it in Trusted Root Certification Authorities, and repeat for Trusted Publishers. Reopen Properties. The signature now reads OK.
- [ ] 4. Double-click the installer. Windows asks for administrator approval and names the publisher. Read the welcome text. If Geosupport Desktop Edition is installed you see no Geosupport page. Install to the default folder and leave Launch ticked.
- [ ] 5. Run the example data through.
  - Wholecount opens within a few seconds, and the top bar says Offline.
  - Press `Try example data`, then `Process everything`. The counts on Results match the `counts` section of `wholecount\sample_data\EXPECTED.json`.
  - Download to a new folder. Expect the practice files, each starting `PRACTICE_`. M09 question 1 is about how many there are.
- [ ] 6. Check the two firewall rules.
  - Open `Windows Defender Firewall with Advanced Security`. Find `Wholecount offline (in)` under Inbound Rules and `Wholecount offline (out)` under Outbound Rules.
  - Double-click each one. General shows `Block the connection` and Enabled is checked.
  - Programs and Services shows `C:\Program Files\Wholecount\Wholecount.exe`, and Advanced shows all three profiles ticked.
- [ ] 7. Run the installer again over the top, then press F5 in the firewall window. There are still exactly two Wholecount rules.
- [ ] 8. Open Notepad and leave it open. With Wholecount running, open Settings, Apps, Wholecount, Uninstall. Wholecount closes by itself, the uninstall finishes, the message about saved progress appears, and Notepad is still open.
- [ ] 9. Press F5 in the firewall window. Both rules are gone, and so is `C:\Program Files\Wholecount`. `%LOCALAPPDATA%\Wholecount` is still there, as the message said.
- [ ] 10. Run the sandbox check (Windows 11 Pro or Enterprise, with Windows Sandbox switched on in Windows Features).
  - In PowerShell, from the repository folder, run `.\tools\sandbox\make_wsb.ps1 -InstallerDir <the unzipped folder> -ResultsDir <a new empty folder>`.
  - Double-click the `wholecount-offline.wsb` it writes, and wait for the sandbox to finish its script.
  - Open `sandbox-result.txt` in the results folder. Every line should say ok.
  - The install log line reads `Geosupport check: not found`, and the app runs with no network adapter at all.
  - Run the example data through to Download inside the sandbox.
- [ ] 11. Optional release test on your machine: run `.\tools\make_cert.ps1`, read the three lines it prints, then `.\tools\release.ps1`. It prints a SHA-256 and the signature status of the exe and the installer. Keep the `.pfx` backup outside the repository.
- [ ] 12. Cleanup. Open `certmgr.msc` and `certlm.msc` and remove `Wholecount CI (not for release)` from Trusted Root Certification Authorities and Trusted Publishers.

## Not done

- The three done-list items that need the Windows workflow (question 4).
