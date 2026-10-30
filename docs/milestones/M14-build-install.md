# M14: Build, installer, firewall, signing and Windows CI

## Goal

Turn the working app into something a client can install. The result is a signed `Wholecount-Setup-{version}.exe` that installs `Wholecount.exe` for all users, adds Windows Firewall block rules on that exact path, and removes them on uninstall. The shipped folder contains no network code, no AI code and no model files, and tests prove it. A GitHub Actions run on `windows-latest` builds, installs, tests, uninstalls and uploads the installer. After this milestone the offline promise has all five layers of SPEC 12.1 behind it, and Joe can check the installer by hand on his machine and in Windows Sandbox with the network off. This milestone closes A-17 and A-20.

## Spec sections

12 (all), 14, 13.6, 13.1 (`tests_windows/`), P-GEO-4a (the example data ships), 3.1, 3.3 (`build/`, `installer/`, `tools/`), 5.1 (where the install secret lives, for the docs). Hard rules H1, H2, H8, H9, H11, H16. Research `docs/research/offline-enforcement.md` sections 2, 3, 5, 6, 7, 8, R1 to R8 and Open risks. Audit A-17 and A-20.

## Depends on

M00 (guard with `allow_open_file` already built, `tools/offline_rules.py`, `tools/pe_net_imports.py`, `tools/offline_scan.py`, both lockfiles, `ci.yml`, the `bundle` stub in the Makefile). M05 (Geosupport discovery, DPAPI, district files). M01 to M12 (a running app that reads, processes, shows and writes). M10 (`resource_path()`, Archivo files). M09 (`tests_windows/test_dpapi_store_real.py`).

This is the first milestone whose main code cannot run in the cloud session. Push the branch early and iterate against the Windows job. Read its logs with `gh run list`, `gh run watch` and `gh run view --log-failed`, fix, and push again. What the Linux session can run is the PyInstaller build (it checks the spec's logic, per research 7.1), every parser-level test, and the self-check. Nothing here is done until the Windows job is green.

## Branch

`build/m14-build-install`

## Read first

- `SPEC.md` 12, 14, 13.6, and `docs/milestones/M00-foundation.md` to see what exists. Do not rebuild anything M00 made. If a thing M00 should have made is missing, make it and say so in the report.
- `docs/research/offline-enforcement.md` in full. Start from the code blocks in R3, R4, R5 and R6, which were run on Linux except the Inno and Windows lines. Rename `crosswalk` to `wholecount`, `Crosswalk.exe` to `Wholecount.exe`, `CROSSWALK_DIST`, `CROSSWALK_BUILD` and `CROSSWALK_LOCK` to `WHOLECOUNT_DIST`, `WHOLECOUNT_BUILD` and `WHOLECOUNT_LOCK`, and the rule names to `Wholecount offline (out)` and `Wholecount offline (in)`.
- `docs/audit/A-claims.md` A-17 (line 230) and A-20 (line 265). The legacy `Stop Crosswalk.command`, `Stop Crosswalk.vbs`, `run.bat`, `run.sh` and `launch.py` show what not to do. Do not copy or import them.
- `docs/milestones/M05-geo.md` for `GeosupportBackend.discover()` and the DLL names, `docs/milestones/M10-window.md` for `resource_path()` and the font files, `docs/milestones/M09-outputs.md` for the outputs writer.
- The Inno Setup help pages and Microsoft's `netsh advfirewall`, `New-NetFirewallRule`, `Get-AuthenticodeSignature` and `signtool` pages. Read them with WebFetch. Anything you cannot read, or cannot run, is marked **Unconfirmed** in the file where you rely on it, the way the research does.

## What to build

### 0. Names, version and files

- `wholecount/brand.py` already holds `PRODUCT_NAME` and `VERSION`. Everything below reads the version from there: the exe's version resource (`tools/make_version_info.py` writes `build/version_info.txt`), `ISCC /DAppVersion=`, and the installer file name.
- Files, all new unless noted.

```
build/wholecount.spec      build/spec_lists.py       build/rthook_offline.py     build/version_info.txt (generated)
installer/wholecount.iss
tools/build.ps1            tools/make_cert.ps1       tools/sign.ps1              tools/release.ps1
tools/signing.json         tools/make_version_info.py  tools/collect_licenses.py  tools/check_bundle.py  tools/make_icon.py
tools/sandbox/wholecount-offline.wsb.in   tools/sandbox/make_wsb.ps1   tools/sandbox/sandbox_run.ps1
requirements-build.in      requirements-build.lock
licenses/                  (generated, committed)
wholecount/selfcheck.py    wholecount/crash.py
.github/workflows/windows.yml          (and one added step in ci.yml)
docs/IT_TRUST.md           docs/SIGNING.md
tests/bundle/              tests_windows/            tests/audit/test_A17_*.py  tests/audit/test_A20_installer_offline.py
```

- `.gitignore` adds `*.pfx`, `*.p12`, `tools/signing.local.json`, `tools/sandbox/*.wsb`, `dist/`, `Output/` and `build/wholecount/`.
- `make bundle` replaces the M00 stub. It builds the one-folder app and runs `tools/check_bundle.py`. It works on Linux (for the spec's logic) and on Windows (the real thing). New targets: `installer`, `sign` and `release`, which are Windows only and print `Windows only` and exit 1 elsewhere. A stub must never look green.

### 1. Build lock (SPEC 12.1 layer 5)

- `requirements-build.in`: `pyinstaller`, `pefile` (already in the dev lock), and whatever PyInstaller needs. Compile `requirements-build.lock` with `--generate-hashes --allow-unsafe --strip-extras` on Python 3.12, with `-c requirements.lock` so shared pins agree. Build tools are not shipped but they write what is shipped (research 8.2), so they get a hashed lock and an exact-set test.
- Add `APPROVED_BUILD_DISTS` to `tools/offline_rules.py` with every distribution in the build lock that is not already approved, and a test that the lock pins exactly the approved set plus that list. The forbidden list still applies, so a build tool can never bring in `requests` or an AI SDK. Report the list.
- Install is always `pip install --require-hashes --no-deps --only-binary=:all:`. A test over `.github/workflows/*.yml`, `tools/*.ps1` and `Makefile` fails on any `pip install` line without all three flags, and on `--no-require-hashes`.
- Pip-tools resolves per environment (research 8.1). The Linux-compiled locks stay the source. The Windows job runs `pip download --platform win_amd64 --python-version 3.12 --implementation cp --abi cp312 --only-binary=:all: --require-hashes` for both locks and compares the resolved set with `pip-compile` run on the runner. A difference fails the job with the diff printed.

### 2. PyInstaller spec (SPEC 14, research R4)

- `build/spec_lists.py` holds the lists and two pure functions, so they can be tested without PyInstaller. `EXCLUDES` (R4's network stdlib, sub-interpreter, dev-only, third-party network and AI, and Qt module lists, plus `wholecount.dev` and `wholecount.app_imports`, which are developer tools), `QT_DROP` (plugin directories and Qt DLL patterns, with the Windows-only `Qt6Network`, `Qt6Qml` and `Qt6Quick` drops), `leaked(pure, binaries, datas) -> list[str]` and `drop(toc, patterns)`. The lists are deliberately a second copy of `offline_rules.py` (research 8.3), and a test keeps them in step (section Tests).
- `build/wholecount.spec` is the R4 file with these changes.
  - Entry `wholecount/__main__.py`, `name="Wholecount"`, `console=False` (windowed), `upx=False`, `icon` from `tools/make_icon.py` (a 256 px icon drawn with Qt from the brand mark; if that is not simple, ship without an icon and say so), `version="build/version_info.txt"`, one folder, output `dist/Wholecount/`.
  - `hiddenimports`: `secrets`, `hmac`, `geosupport`, `lxml.etree`, `lxml._elementpath`, plus `collect_submodules("wholecount")` so stage and rule modules loaded by name are found. Expect the first Windows run to show more. Add each one with a comment saying what imports it.
  - Data. `collect_data_files("wholecount", includes=["**/*.toml", "**/*.csv", "**/*.tsv", "**/*.xlsx", "**/*.xml", "**/*.geojson", "**/*.json", "**/*.ttf", "**/*.txt"])` for settings, the copy registry, the ZIP table, district files, Archivo with `OFL.txt`, and `wholecount/sample_data/` (the five example files, `EXPECTED.json` and the sample reference, P-GEO-4a). `("licenses", "licenses")`. Nothing from `tests/`, `docs/` or `legacy/`.
  - The R4 build gate stays and runs `spec_lists.leaked(...)`, failing the build, not the audit, with `OFFLINE GATE FAILED`. It also fails if any `.onnx`, `.pt`, `.pth`, `.safetensors`, `.gguf`, `.h5` or `.bin` over 1 MB is in `a.datas`.
  - If a pandas or numpy hook collects `*.tests` packages or their `.pkl` and `.pickle` data, add them to `EXCLUDES` rather than loosening the model-file test.
- `build/rthook_offline.py` is R3's file calling `wholecount.guard.install_for_app(geosupport_dirs=...)`. The Geosupport directories come from one pure function (`os` and `sys` only) that M05's `discover()` also uses. If M05 put it somewhere that imports `geosupport`, move it into `wholecount/guard/paths.py`. The hook must not import anything from the denied list. `install_for_app` must be idempotent, because `__main__.py` installs the guard too. If it is not, make it so and add a test.
- `tools/check_bundle.py DIST BUILD` is the pure-Python check behind `make bundle` and the bundle tests. It reads `PYZ-00.toc`, `COLLECT-00.toc`, `warn-wholecount.txt` and walks `dist/Wholecount`. It prints counts only.
- `tools/collect_licenses.py` writes `licenses/`. One file per approved distribution (from its `dist-info`), the Python license, the PyInstaller bootloader license, `PySide6-LGPL-NOTICE.txt` (says Qt is LGPL 3, that the Qt libraries are separate files in `_internal` so the operator can replace them, and where the source is), the Archivo OFL, and `NYC-DATA-NOTICE.txt` for the ZIP table and district files with the source and date from M05's `SOURCE.txt`. A test fails when an approved distribution has no license file.

### 3. The frozen app must start, explain itself and fail politely

- `wholecount/selfcheck.py` and the flag `Wholecount.exe --self-check --self-check-out DIR`. Handled in `__main__.py` right after the guard install and before any window. It is the only command line option, and the `QApplication` is made as `QApplication([sys.argv[0]])` so no Qt switch can arrive on the command line (research 3.3). Without `--self-check-out` it refuses and writes nothing. It exists because a windowed exe has no console and PyInstaller's biggest risk is a module that is missing only when frozen.
  - It writes `DIR/result.json` and `DIR/files/` and nothing else. The JSON has a fixed list of check IDs, each `ok` or `failed`, and counts. It holds no string from any data file (H8).
  - Checks. `guard.installed` and `guard.denies_socket`. The frozen build has no `socket` module, so the check raises the audit event itself with `sys.audit("socket.connect", None, ("192.0.2.1", 80))` and expects the guard's error. It never imports `socket`, which M00's static scan would catch. `guard.denies_unc` (Windows). `modules.none_loaded` (after everything below, none of `FORBIDDEN_MODULES` is in `sys.modules`, reading the guard's own deny list since `tools/` is not shipped). `fonts.archivo` (three weights). `copy.registry` and `settings.load`. `data.zip_table` and `data.districts` (a point inside the city gets a district, a point at sea gets none). One `readers.*` check for each file type the app reads, on the five example files in `sample_data/` (CSV, Windows-1252 TSV, XLSX, JSON, XML). `geosupport.import` (imports, does not call). `pipeline.sample` (adds the five example files, chooses the workbook header as `EXPECTED.json` says, accepts the proposed tidy-up steps, auto-maps, takes the planned decisions in `EXPECTED.json`, runs with no geocoder, and compares tables, rows, counted, not counted yet, set aside, Goal 1 and Goal 2 with `EXPECTED.json`). `outputs.nine_files` (a real run with no geocoder, so not a practice run, writes the nine default files into `DIR/files/` without Map_Points and compares their row counts with the no-geocoder block of `outputs` in `EXPECTED.json`). `data.sample_reference` (`sample_data/sample_reference.csv` loads and is marked as a sample, so a practice run can work). `secret.roundtrip` (Windows: make a secret in a temporary folder, protect it with DPAPI, read it back, and never touch the real profile). `ui.build` (builds the main window and all nine stage bodies offscreen). `dpapi.roundtrip` (Windows). `licenses.present`.
  - Expected counts come from the shipped `sample_data/EXPECTED.json`, so there's no second copy of them. The same numbers must come out of the Linux source run and the frozen Windows exe, which is a cross-platform determinism check that costs nothing.
  - Use the same calls the stages and `tests/acceptance` use (M08 and M09 names). Add no second code path to the engine.
- `wholecount/crash.py` adds the GUI message box to M09's `errors.install_excepthook()`, which stays the package's only `sys.excepthook`. An unhandled exception shows one message box, `Wholecount stopped because of a fault in the program. Error code {code}. Nothing was written, and your own files were not changed.` The code is M10's `error_code(exc)` (type and code location only, never the message) and the box has a `Copy the error code` button. Nothing is logged to disk (A-15, H9). The copy is registered with a claim test.
- `console=False` means `sys.stdout` and `sys.stderr` are `None` when frozen. A test runs the self-check with both set to `None` and passes.

### 4. Installer (`installer/wholecount.iss`, Inno Setup 6, research R5)

- `[Setup]`. A fixed `AppId` GUID made once and never changed. `AppName=Wholecount`, `AppVersion={#AppVersion}` (passed in by the build script), `AppPublisher={#Publisher}` (read from the `publisher` setting in `tools/signing.json`, default `Joe Buzzetta`, the same string as the certificate subject, SPEC 17 Q6), `PrivilegesRequired=admin`, `DefaultDirName={autopf}\Wholecount`, `ArchitecturesAllowed=x64compatible`, `ArchitecturesInstallIn64BitMode=x64compatible` (Inno's accepted value name is Unconfirmed, so the Windows job is the arbiter), `MinVersion=10.0.19045` (Windows 10 22H2, with Windows 11 above it, SPEC 14) and nothing else for 32-bit, `CloseApplications=yes` so Restart Manager closes a running Wholecount and nothing else, `OutputBaseFilename=Wholecount-Setup-{#AppVersion}`, `UninstallDisplayIcon={app}\Wholecount.exe`, `DisableProgramGroupPage=yes`, `Compression=lzma2`, `SolidCompression=yes`. Behind `#ifdef SignIt`, `SignTool=wholecountsign` and `SignedUninstaller=yes`.
- `[Files]` is `dist\Wholecount\*` with `recursesubdirs ignoreversion`. `[InstallDelete]` removes `{app}\_internal` first, so an upgrade never leaves a module the new build dropped. `[Icons]` is the Start menu entry only. No desktop icon, no autostart, no file association.
- `[Run]` and `[UninstallRun]` are R5's lines with the new names, in this order. Delete the two rules (a missing rule fails harmlessly), then add the outbound block and the inbound block with `program="{app}\Wholecount.exe" enable=yes profile=any`, all `runhidden waituntilterminated`. Uninstall deletes both by name with `RunOnceId`. The launch entry at the end is `postinstall nowait skipifsilent runasoriginaluser`, so the app never starts with the installer's admin token.
- `[Code]`. Inno does not stop when `netsh` fails (Unconfirmed in the research), so verify.
  - On `CurPageChanged(wpFinished)` run `netsh advfirewall firewall show rule name="Wholecount offline (out)"` and the inbound one, and check each exit code. If either is missing, the finish page says `The firewall rules could not be added. Wholecount will still run, but Windows will not block it from using the network. See IT_TRUST.md.` and `Log` records it. In a silent install only the log shows it.
  - `GeosupportFound()` follows M05's `discover()` exactly. The `GEOFILES` variable (machine, then user, through `RegQueryStringValue`) and the standard install path under `C:\Program Files\Geosupport Desktop Edition`, and the DLL name M05 uses. Copy M05's paths, do not guess. It logs `Geosupport check: found` or `Geosupport check: not found`. When not found and not silent, an output page after Welcome says `Geosupport Desktop Edition was not found on this computer. Wholecount will install and run, but it cannot place addresses until Geosupport is installed or you add an address reference file. You can do either later.`
  - On uninstall, after files go, a suppressible message says `Saved progress, settings and the install secret in %LOCALAPPDATA%\Wholecount were left in place. Delete that folder to remove them. A saved crosswalk can't be read without the install secret.` Nothing in a user profile is deleted (H9, and the installer cannot know every user).
- Welcome text (`[Messages] WelcomeLabel2`): `Wholecount works on this computer only. This setup adds two Windows Firewall rules that block Wholecount.exe from using the network in either direction. It connects to nothing and downloads nothing.`
- No `[Languages]` beyond English, no `DownloadTemporaryFile`, no `idp`, no URL anywhere in the file.

### 5. Signing (SPEC 14, free route)

- `tools/signing.json` (committed, no secrets) holds `provider` (`local_cert` or `azure_artifact_signing`), `publisher` (default `Joe Buzzetta`), `thumbprint` (empty), `timestamp_url`, and the Azure fields (endpoint, account, profile, all non-secret). `tools/signing.local.json` (ignored) overrides it per machine. The only network use in signing is the timestamp request, made by the developer's machine at build time, never by the app. If the timestamp server cannot be reached, `sign.ps1` fails unless `-NoTimestamp` is given, and then prints that the signature stops being valid when the certificate expires.
- `tools/make_cert.ps1`. `New-SelfSignedCertificate -Type CodeSigningCert` with RSA 3072, SHA-256, subject `CN={publisher}`, exportable, in `Cert:\CurrentUser\My`, valid three years. It exports the public `.cer`, offers a `.pfx` backup with a password read as a secure string, writes the thumbprint into `signing.local.json`, and prints three lines for Joe. With `-Ci` the subject is `CN=Wholecount CI (not for release)`, valid one day, no `.pfx`, and the thumbprint goes to `$env:GITHUB_OUTPUT`.
- `tools/sign.ps1 -Path ...`. Reads the settings, finds `signtool.exe` in the newest Windows SDK folder, and falls back to `Set-AuthenticodeSignature` when there is no SDK, so Joe needs nothing extra. It signs with SHA-256, then checks `Get-AuthenticodeSignature` and fails on `NotSigned` or `HashMismatch`. `UnknownError` or `NotTrusted` on a machine that has not trusted the certificate is expected for a self-signed one, and the script says so and compares the thumbprint. The `azure_artifact_signing` branch is written from Microsoft's current documentation and marked Unconfirmed, since nothing can run it here. Switching is a change to `signing.json`.
- `tools/release.ps1` is Joe's one command. It checks the venv, runs `tools/build.ps1` (PyInstaller, `check_bundle`, bundle tests), signs `Wholecount.exe`, compiles the installer with `/DSignIt /Swholecountsign=...`, signs it, and prints the SHA-256 and the signature status of both. The order matters, because the installer must hold the signed exe.
- CI signs with an ephemeral certificate made by `make_cert.ps1 -Ci`. The workflow never reads a secret, and the real key never leaves Joe's machine. The CI `.cer` is uploaded beside the installer so Joe can trust it for his own test.

### 6. Docs

Both files follow the style rules, and `make copy` lints them (extend M00's file list). Every step names the Microsoft page it came from. A step you could not check is marked **Unconfirmed**, and the Windows checks below cover what Joe can verify.

- `docs/IT_TRUST.md`, for a client's IT staff. What the program does and does not do (offline, no AI, what it writes and where). The publisher name on the signature is the `publisher` setting, and the document says it can be changed to a business name. The facts for the firewall rule in a table (program path, direction in and out, action block, profile any) with the `New-NetFirewallRule` and `Remove-NetFirewallRule` lines for GPO or Intune, and what to do when local rule merging is off (research 5.5). How to check the installer (`Get-FileHash`, `Get-AuthenticodeSignature`, the thumbprint and publisher). How to trust the certificate: Group Policy to Trusted Root Certification Authorities and Trusted Publishers, Intune, and `certutil -addstore` for one machine. An AppLocker or App Control publisher rule. What SmartScreen and Smart App Control do on a machine that has not trusted the certificate, stated plainly as a warning that stays on unmanaged machines. Whether they accept the certificate once it is trusted by policy is written as `to confirm on a managed machine`, because the research did not verify it (SPEC 14). The supported systems, Windows 10 22H2 and Windows 11, 64-bit only. Where data lives (`%LOCALAPPDATA%\Wholecount`), listed by file from M09's STORE-8 and M13's report if it has merged, which file is the install secret, that deleting it makes a saved crosswalk unreadable, and how to remove everything.
- `docs/SIGNING.md`, for the maintainer. Make the certificate, keep the `.pfx` off the repo and off cloud sync, sign, timestamp, renew before expiry, what CI signs with and why, and the switch to Azure Artifact Signing as a `signing.json` change (the SPEC's price and eligibility note, and what to read first).
- A test makes the `netsh` and PowerShell lines in `IT_TRUST.md` equal the lines in the `.iss`, so the doc cannot drift from the installer.

### 7. Windows CI (`.github/workflows/windows.yml`, SPEC 13.6)

- Triggers: push to `main` and `build/**`, pull requests, and `workflow_dispatch`. `permissions: contents: read`. No secrets. One job on `windows-latest`, `shell: pwsh`, a timeout of 45 minutes. Same action major versions as M00's `ci.yml`.
- Steps, in order.
  1. Check out. Set up Python 3.12. Print the Python build (`python -VV`), because the PE allowlist was measured on conda-forge and must be re-measured on this interpreter.
  2. Print whether the runner is elevated (SPEC 13.6 says hosted runners run as administrator, and this step confirms it) and the Windows version. Both go in the job summary. If the runner is not elevated, the install and firewall tests cannot run, so stop and put the question at the top of the report.
  3. Install `requirements-dev.lock` and `requirements-build.lock` with the three flags. Run the lock comparison from section 1.
  4. Locate Inno Setup. Use the preinstalled `ISCC.exe` if present. Otherwise install a pinned version with Chocolatey and print its version (Unconfirmed which the image has, so read the runner image list first).
  5. `tools/build.ps1`. Then `pytest tests/bundle` with `WHOLECOUNT_DIST` and `WHOLECOUNT_BUILD`. Then the frozen self-check, `dist\Wholecount\Wholecount.exe --self-check --self-check-out out\selfcheck`, and a step that fails unless every check is `ok` and the counts equal `sample_data/EXPECTED.json`.
  6. `tools/pe_net_imports.py` in report mode on the folder, uploaded as `pe-report.txt`. The first run lists the real allowlist for this interpreter. Update `PE_NETWORK_IMPORT_ALLOWLIST` with a comment for each entry saying why that binary imports winsock, then the bundle test is strict.
  7. `make_cert.ps1 -Ci`, then compile and sign as in `release.ps1`, using the CI certificate. Import the CI `.cer` into the runner's Trusted Root and Trusted Publishers stores so the signature check can read `Valid`.
  8. `pytest tests_windows -m windows -rs` with `WHOLECOUNT_REQUIRE_WINDOWS_TESTS=1`. In that mode a skipped test fails the run, except tests that need Geosupport or a second account, which are named in an allowlist in `conftest.py`. A skip must never look green.
  9. Upload artifacts. `wholecount-installer` (the signed installer, its SHA-256, the CI `.cer`) and `wholecount-reports` (`install.log`, `pe-report.txt`, `selfcheck`, `bundle-report.json`, the junit file). Write the test counts and the skip list to the job summary.
- Add one step to `ci.yml` after the tests, `make bundle` and `pytest tests/bundle`, so the spec's logic is checked on every Linux push. `WHOLECOUNT_REQUIRE_BUNDLE=1` makes the bundle tests fail rather than skip when the folder is missing.

### 8. Windows Sandbox check (SPEC 12.4)

GitHub runners cannot run Windows Sandbox, so this one is a scripted manual check that Joe does (SPEC 13.6).

- `tools/sandbox/wholecount-offline.wsb.in` is a template, because a `.wsb` file needs absolute host paths. `tools/sandbox/make_wsb.ps1 -InstallerDir ... -ResultsDir ...` fills it in and writes `wholecount-offline.wsb` (ignored by git). The file has `<Networking>Disable</Networking>`, `<vGPU>Disable</vGPU>`, one read-only mapped folder holding the installer, the CI `.cer` and the script, one writable folder for results, and a `<LogonCommand>` that runs `sandbox_run.ps1`.
- `sandbox_run.ps1`. Imports the `.cer` into Trusted Root and Trusted Publishers, runs the installer silently with a log, runs `Wholecount.exe --self-check --self-check-out` into the results folder, and starts the app so Joe can use it. It writes a plain `sandbox-result.txt` line for each step.
- This proves the app works with no network at all. It does not prove it could not use one, and the report and `IT_TRUST.md` say exactly that (research 6).
- A test parses the template and a generated file, and fails unless networking is disabled and every mapped path and the script exist.

## Tests to write

Write each failing test first. Every scan has a negative control that feeds it a bad input and asserts it is caught. Tests that need a built folder read `WHOLECOUNT_DIST` and `WHOLECOUNT_BUILD` and skip with a clear message when they are unset, unless `WHOLECOUNT_REQUIRE_BUNDLE=1`.

Linux and Windows (`tests/`):

- `tests/bundle/test_spec_lists.py`. `EXCLUDES` contains every name in `FORBIDDEN_MODULES` except a pinned, commented exception set (the Qt names M00 already treats this way). `leaked()` flags a table of contents holding `_socket`, `PySide6.QtNetwork`, an AI SDK name or a file named `libssl`, and passes a clean one. `drop()` removes `plugins/tls/` and `plugins/generic/` entries.
- `tests/bundle/test_bundle.py`. From the built folder and the build tables.
  - `test_no_forbidden_python_modules_in_pyz_or_extensions` (PYZ and COLLECT tables).
  - `test_no_forbidden_files_in_output_folder` using `FORBIDDEN_FILE_NAME_PARTS`, plus the Windows-only parts when the folder holds `.dll` files.
  - `test_no_model_or_pickle_files_in_output_folder` and `test_no_large_bin_files`.
  - `test_warn_file_shows_exclusions_not_inclusions`.
  - `test_required_files_present` (Archivo and its OFL, the copy registry, settings, ZIP table, district files, the five example files with `EXPECTED.json` and `sample_reference.csv` in `sample_data/`, one license file per approved distribution, the LGPL notice).
  - `test_nothing_unwanted_shipped` (no `tests`, `docs`, `legacy`, `.git`, `.md` outside `licenses`, `wholecount/dev.py`).
  - `test_exe_is_windowed` (PE subsystem is GUI, Windows only) and `test_version_resource_matches_brand`.
- `tests/bundle/test_pe_scan.py`. On a Windows folder, every binary that imports a networking DLL is in `PE_NETWORK_IMPORT_ALLOWLIST` and no allowlist entry is stale. The logic is also tested on Linux with `imported_dlls` stubbed. The Windows negative control copies a real allowlisted binary under another name into a temp tree and expects it flagged.
- `tests/offline/test_lockfile_build.py`. `requirements-build.lock` is hashed and pinned, has no forbidden distribution, and pins exactly the approved set plus `APPROVED_BUILD_DISTS`. No `pip install` in the workflows, scripts or Makefile lacks the three flags.
- `tests/unit/test_iss.py`. The installer has `PrivilegesRequired=admin`, the 64-bit directives, `MinVersion=10.0.19045`, `AppPublisher` equal to the `publisher` in `signing.json`, `CloseApplications=yes`, a fixed `AppId`, the version from a define, the four `netsh` add and delete lines and two uninstall lines naming `{app}\Wholecount.exe`, `dir=out` and `dir=in`, `action=block` and `profile=any`, the launch entry with `runasoriginaluser`, no `[Languages]` network use, no `http`, and no em dash, emoji or exclamation mark inside any quoted string. Its Geosupport check uses the same paths and variable name as M05's `discover()`.
- `tests/unit/test_docs_match_installer.py` (the `netsh` and PowerShell lines in `IT_TRUST.md` equal the installer's) and `tests/copy` coverage of both docs and the `.iss` strings.
- `tests/unit/test_wsb.py` and `tests/unit/test_workflow.py`. In the sandbox file, networking is disabled and every path exists. The workflow runs on `windows-latest`, has `contents: read`, uses no `secrets.`, uploads both artifacts, sets `WHOLECOUNT_REQUIRE_WINDOWS_TESTS`, and every `pip install` has the three flags.
- `tests/unit/test_selfcheck.py`. It runs under the guard on Linux and every check is `ok`. It refuses without `--self-check-out`. It writes only `result.json` and `files/` under the given directory (compare directory listings). The JSON holds no canary value from the example files (H8). It passes with `sys.stdout` and `sys.stderr` set to `None`. Counts equal `wholecount/sample_data/EXPECTED.json`.
- `tests/unit/test_crash.py`. A forced exception shows the box with a code that is the same for the same fault location and has no message text. The box has no value from a canary row. Nothing is written to disk (compare a temp directory before and after).
- `tests/unit/test_guard_idempotent.py` (second `install_for_app` call adds no second violation list and keeps `INSTALLED`).
- `tests/audit/test_A17_no_process_killing.py`. No `taskkill`, `Stop-Process`, `pkill`, `kill`, `wmic` or `.pid` file in `installer/`, `build/`, `tools/` or `wholecount/`, and no `Stop*` script anywhere outside `legacy/`. The installer closes the app only through `CloseApplications`.
- `tests/audit/test_A20_installer_offline.py`. It has three parts.
  - **What it scans.** Every file in `installer/`, `build/wholecount.spec`, `build/rthook_offline.py`, every shipped `wholecount/**/*.py` (everything under `wholecount/` except `dev.py` and `app_imports.py`), and every PowerShell script under `tools/`. None of them may hold a URL or the words `pip`, `curl`, `wget`, `Invoke-WebRequest`, `Start-BitsTransfer`, `DownloadFile` or `DownloadTemporaryFile`. `wholecount/guard/` is exempt from the word check only, as in M00, because its deny lists must name modules.
  - **The provenance allowlist.** A second pass reads every other file under `wholecount/`, `tools/` and `build/`, and fails on a URL or `pip` that isn't on an explicit allowlist. Each entry names one file and the reason:
    - `tools/make_zip_table.py` and the `source` column of `wholecount/engine/geo/data/nyc_zips.csv` (the ZIP table's source, M03)
    - `tools/make_district_files.py` (the district files' source, M05)
    - `tools/offline_rules.py` (`URL_RE` and `URL_ALLOW_PREFIXES`, which are a pattern and XML namespaces)
    - `build/spec_lists.py` (its `DEV_ONLY` list names `pip` so the build can exclude it)
    - `wholecount/ui/theme/fonts/SOURCE.txt` (the Archivo source, M10)
    - `tools/signing.json` (the timestamp address) and `tools/sandbox/`

    A new entry needs a reason in the same change.
  - **Negative controls.** A URL in a temp `wholecount/x.py`, a `pip install` line in a temp `.ps1`, and a URL in a temp data file that isn't on the allowlist are each caught.

  No launcher scripts are in the shipped folder (`.bat`, `.cmd`, `.sh`, `.command`, `.vbs`). The README claim is M15's, and its test lives there.

Windows only (`tests_windows/`, marked `windows`, run in the workflow and on Joe's machine):

- `test_firewall_probe.py`. Research 7.3, with its control. Build the probe exe with PyInstaller outside the guard, bind a listener on a non-loopback address of the machine, and require `CONNECTED` before the rule exists. Then add the rule using the `netsh` text parsed out of `wholecount.iss` with `{app}` replaced by the probe's folder, and require `BLOCKED_OR_FAILED`. Delete the rule in a `finally`. Also test the inbound rule if the runner allows it. If the machine cannot make the control connect, the test fails with `control failed`, never passes.
- `test_installer_rules.py`. Silent install with `/VERYSILENT /SUPPRESSMSGBOXES /NORESTART /LOG /DIR=`. `Get-NetFirewallRule -DisplayName 'Wholecount offline*'` returns exactly two rules, one each way, both Block, enabled, profile Any, and `Get-NetFirewallApplicationFilter` shows the installed `Wholecount.exe` path (this settles whether `netsh name=` is the PowerShell `DisplayName`, which is Unconfirmed). Installing over itself still leaves exactly two. Uninstall removes both rules and the folder.
- `test_uninstall_closes_only_wholecount.py` (A-17). Start an unrelated long-running process the test owns, and start the installed app. Uninstall silently. The app is gone and the unrelated process is still alive.
- `test_frozen_selfcheck.py`. Runs the built exe and the installed exe, and requires every check `ok` and the same counts as Linux.
- `test_signature.py`. Both files are signed by the CI certificate's thumbprint, with status `Valid` once the certificate is trusted in the job, and the installer's embedded exe is the signed one.
- `test_geosupport_installer_check.py` and `test_geosupport_imports.py`. Skipped unless Geosupport is installed. The first compares the installer log line with `GeosupportBackend.discover()`. The second prints the DLL's import table and fails if it imports a networking DLL that is not listed in a reviewed allowlist, so Joe decides (research Open risk 5).
- `test_ps1_syntax.py`. Parses every script with the PowerShell parser and runs none of them.

## Done when

- [ ] `make test`, `make offline` and `make copy` are green on Linux, with counts in the report. `make bundle` builds on Linux and the bundle tests pass on that folder.
- [ ] The Windows workflow is green on the pull request, with no unexpected skips. The report links the run and lists the skipped tests with their reasons.
- [ ] The signed installer and its checksum are uploaded as a workflow artifact.
- [ ] `PE_NETWORK_IMPORT_ALLOWLIST` was re-measured on the runner's interpreter, with a comment on each entry. The report shows the old and new lists.
- [ ] A-17 and A-20 have passing tests and a `done` line in `tests/audit/INDEX.md`.
- [ ] `docs/IT_TRUST.md` and `docs/SIGNING.md` are written, every unchecked step is marked Unconfirmed, and `make copy` lints them.
- [ ] `docs/milestones/M14-REPORT.md` lists each spec difference (the first-run hidden imports found, the self-check IDs added for the nine files and the secret), the runner's elevation result, each question for Joe (the publisher name, Q6, and per-machine install only), and the cost of the Windows job.
- [ ] The report is written, the branch is pushed, the pull request is open, and work has stopped.

## Windows checks for Joe

Use the installer from the pull request's workflow run (Actions, the run, Artifacts, `wholecount-installer`). Unzip it into a new folder. These steps use the CI certificate, which is for testing only. Delete it at step 12.

1. Open PowerShell in that folder and run `Get-FileHash .\Wholecount-Setup-*.exe -Algorithm SHA256`. The value matches the checksum file in the artifact.
2. Right-click the installer, choose Properties, and open the Digital Signatures tab. A signature from `Wholecount CI (not for release)` is listed. Before you trust the certificate it will not say it is OK.
3. Import the `.cer` from the artifact: right-click it, Install Certificate, Local Machine, place it in Trusted Root Certification Authorities, and repeat for Trusted Publishers. Reopen Properties. The signature now reads OK.
4. Double-click the installer. Windows asks for administrator approval and names the publisher. Read the welcome text. If Geosupport Desktop Edition is installed you see no Geosupport page. Install to the default folder and leave Launch ticked.
5. Wholecount opens within a few seconds, and the top bar says Offline. Press `Try example data`, then `Process everything`. It runs, and the counts on Results match the `counts` section of `wholecount\sample_data\EXPECTED.json` in the repository. Download to a new folder. Expect seven files, each starting `PRACTICE_` (a practice run writes no map files). Compare the files with a run from source if you have one.
6. Press the Windows key, type `Windows Defender Firewall with Advanced Security`, and open it. Under Inbound Rules find `Wholecount offline (in)`, and under Outbound Rules find `Wholecount offline (out)`. Double-click each. General shows `Block the connection`. Programs and Services shows `C:\Program Files\Wholecount\Wholecount.exe`. Advanced shows all three profiles ticked. Enabled is checked on General.
7. Run the installer again over the top. In the firewall window press F5. There are still exactly two Wholecount rules.
8. Open Notepad and leave it open. With Wholecount running, open Settings, Apps, Wholecount, Uninstall. Wholecount closes by itself, the uninstall finishes, the message about saved progress appears, and Notepad is still open.
9. Press F5 in the firewall window. Both rules are gone. `C:\Program Files\Wholecount` is gone. `%LOCALAPPDATA%\Wholecount` is still there, as the message said.
10. In PowerShell, from the repository folder, run `.\tools\sandbox\make_wsb.ps1 -InstallerDir <the unzipped folder> -ResultsDir <a new empty folder>` and double-click the `wholecount-offline.wsb` it writes (Windows Sandbox needs Windows 11 Pro or Enterprise, and the feature switched on in Windows Features). Wait for the sandbox to finish its script. Open `sandbox-result.txt` in the results folder and check every line says ok. The sandbox has no Geosupport, so the install log line reads `Geosupport check: not found`, and the app runs with no network adapter at all. Run the example data through to Download inside the sandbox.
11. Optional release test on your machine: in PowerShell run `.\tools\make_cert.ps1`, read the three lines it prints, then `.\tools\release.ps1`. It prints a SHA-256 and the signature status of the exe and the installer. Keep the `.pfx` backup outside the repository.
12. Cleanup. Open `certmgr.msc` and `certlm.msc` and remove `Wholecount CI (not for release)` from Trusted Root Certification Authorities and Trusted Publishers.

## Out of scope

- The user guide, help pages, the README and its open-risk list, `docs/REFERENCE_DATA.md`, acceptance runs and performance budgets (M15).
- Moving to Azure Artifact Signing. Only the setting and the docs for the switch are built here.
- Bundling or installing Geosupport. The installer only checks for it and says what that means.
- Per-user installs, MSI or MSIX packages, auto-update, 32-bit Windows, macOS and Linux packages.
- Changes to engine rules, screens, or the copy of any stage. The only app code added is `selfcheck.py`, `crash.py` and the small guard changes named above.
- Editing `SPEC.md`, `CLAUDE.md` or `docs/milestones/README.md`. If one is wrong, put the question at the top of the report.
