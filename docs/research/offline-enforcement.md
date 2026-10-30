# Making a Windows desktop app provably unable to reach the internet or any AI service

Research for the Crosswalk records-cleaning tool: Python 3.12, PySide6 (Qt Widgets only), pandas, numpy, openpyxl, lxml, python-geosupport, packaged with PyInstaller one-folder inside an Inno Setup installer.

Date of research: 2026-10-30. Everything marked **Tested** was run on Linux x86-64 (CPython 3.12.3 and 3.13.18, PySide6 6.12.0, pandas 3.1.0, numpy 2.5.4, lxml 6.1.3, openpyxl 3.1.5, python-geosupport 1.1.0, PyInstaller 6.22.3, pip 26.2.2, pip-tools 7.6.2). **Nothing was run on Windows.** Windows behavior is taken from Microsoft and Inno Setup documentation, from CPython/Qt/PyInstaller source, or from inspecting the Windows wheels (PE import tables) on Linux.

## How to read the citations

- A link in parentheses after a claim is the primary source for it. Source files on GitHub are pinned to the tag or branch I actually read (CPython `3.12`, PyInstaller `v6.22.3`, qtbase `v6.12.0`, lxml `lxml-6.1.3`).
- **Tested (T1 to T14)** means I ran it; the experiment log near the end says what was run and what happened. Code for the tests that matter is in "Recommended design".
- **Unconfirmed** means I could not confirm it from a primary source or could not run it. These are collected again under "Open risks".
- **Inference** means reasoning from cited facts. It is flagged so you can decide whether to trust it.
- American spelling, no em dashes.

## Summary

Layers, strongest first. "Provable" here means: each layer has an automated check that fails the build if the property is lost. It does not mean the app can be shown to emit zero packets in every possible circumstance (see "Open risks").

1. **OS firewall rule (strongest, enforced outside the process).** The installer (admin) adds an outbound block rule bound to the exact path of `Crosswalk.exe` (and an inbound block). Windows Firewall gives explicit block rules precedence over allow rules, and application rules need the full path. It is the only layer that still holds if every line of our code and every library is wrong. Weaknesses: a managed PC can disable local rule merging, an admin can delete the rule, and I could not run it on Windows (Unconfirmed). ([rules](https://learn.microsoft.com/en-us/windows/security/operating-system-security/network-security/windows-firewall/rules), [troubleshoot examples](https://learn.microsoft.com/en-us/troubleshoot/windows-server/networking/netsh-advfirewall-firewall-control-firewall-behavior))
2. **Absence from the build.** Code that is not in the folder cannot run. `Analysis(excludes=...)` removes `socket`, `_socket`, `ssl`, `http.*`, `urllib.request`, `ftplib`, `smtplib`, `asyncio`, `multiprocessing`, `PySide6.QtNetwork` and friends. A Linux build went from 1,504 bundled modules (including `socket`, `ssl`, `http.client`, `urllib.request`, `asyncio`, `QtNetwork`) to 809 with none of them, and a build gate in the spec aborts the build if anything forbidden appears (T9). Limits: on Windows the sub-interpreter modules (`_xxsubinterpreters` in 3.12, `_interpreters` in 3.13), `_winapi` and `winreg` are compiled into `python3xx.dll`, so they cannot be excluded ([PC/config.c](https://github.com/python/cpython/blob/3.12/PC/config.c)).
3. **Qt: Widgets and Gui do not need Qt Network, but the wheel ships it anyway.** QtCore/QtGui/QtWidgets never import `PySide6.QtNetwork` (T8), and on Windows their DLLs do not import `Qt6Network.dll` (T11). `PySide6-Essentials` still contains `QtNetwork.pyd`, `Qt6Network.dll` and a `generic/qtuiotouchplugin.dll` that links it, so exclude the module and drop `plugins/generic` and `Qt6Network.dll` from the TOC, then verify with a PE import scan. `Qt6Core.dll` itself imports `ws2_32.dll`, `mpr.dll` and `netapi32.dll`, and `python312.dll`, `select.pyd` and lxml's `etree.pyd` import `ws2_32.dll` too, so the process always has winsock code available: this is why layer 1 matters (T11, T14). ([gui CMake](https://github.com/qt/qtbase/blob/v6.12.0/src/gui/CMakeLists.txt), [tuiotouch CMake](https://github.com/qt/qtbase/blob/v6.12.0/src/plugins/generic/tuiotouch/CMakeLists.txt))
4. **Library hygiene (only local file objects).** pandas `read_*` and `np.loadtxt` happily fetch `http://` and `ftp://` strings (T7). Always open files yourself and pass the file object. lxml defaults are safe (`no_network=True`, `resolve_entities='internal'` with the 6.1.x XXE fixes), but the Windows lxml wheels embed libxml2 2.11.9 with HTTP and FTP client code, unlike the Linux wheels, so never hand lxml a URL string. Never call `QDesktopServices.openUrl` (on Windows it is `ShellExecute`) or enable `openExternalLinks` (default false). Enforce with a static scan. ([lxml parsing](https://lxml.de/parsing.html), [lxml CHANGES](https://github.com/lxml/lxml/blob/lxml-6.1.3/CHANGES.txt), [pandas io/common.py](https://github.com/pandas-dev/pandas/blob/main/pandas/io/common.py), [QDesktopServices](https://doc.qt.io/qt-6/qdesktopservices.html))
5. **In-process audit hook, fail-closed (defense in depth, not a sandbox).** One `sys.addaudithook` installed as the app's first statement denies `socket.*`, DNS, `urllib.Request`, `http.client.*`, `ftplib`, `smtplib`, `subprocess.Popen`, `os.system`, `os.startfile`, UNC and WebDAV paths, first imports of network modules, and any `ctypes` library or symbol outside an allowlist. Python's own docs say such hooks "are not suitable for implementing a sandbox" ([sys.addaudithook](https://docs.python.org/3/library/sys.html#sys.addaudithook)). Tested gaps: sub-interpreters, `ctypes` calls through pointers resolved earlier, `send()` on a socket opened earlier, `importlib.import_module` of builtin or pure-Python modules, and all C/C++ code (Qt `ShellExecute`, libxml2, the Geosupport DLL) (T2, T3, T4).
6. **Do not rely on monkeypatching `socket.socket`.** It blocks `socket.socket()`, `create_connection` and `urlopen`, but not `_socket.socket()`, references taken earlier with `from socket import socket`, or `getaddrinfo`, and the C type cannot be patched (T5). Use it only in tests (the [`pytest-socket`](https://github.com/miketheman/pytest-socket) approach). It adds nothing the audit hook does not already cover.
7. **Cut the supply chain.** Use `PySide6-Essentials` (the `PySide6` meta-package depends on Addons, WebEngine and Pdf wheels), compile a hashed lockfile with `pip-compile --generate-hashes`, install with `pip install --require-hashes --no-deps --only-binary=:all:`, and deny-list network and AI distribution names in a test. The Linux-compiled lock resolved cleanly for `win_amd64` / `cp312` with hash checking (T13). pip-tools says to compile on each target environment, so still compile once on Windows and diff. ([pip secure installs](https://github.com/pypa/pip/blob/main/docs/html/topics/secure-installs.md), [pip-tools README](https://github.com/jazzband/pip-tools/blob/main/README.md), [PySide6 metadata on PyPI](https://pypi.org/pypi/PySide6/6.12.0/json))
8. **A test suite is the evidence.** 20 pytest tests passed on the hardened Linux build, and 2 of the 5 bundle tests failed on the default build, 2 lock tests failed on a lock with one extra package, and 4 source tests failed on app code containing `import socket`, `QDesktopServices` and a URL (the negative controls) (T12). They run in Linux CI: guard behavior (3.12 and 3.13), import graph, bundle contents (PYZ/COLLECT TOC plus output-folder scan), PE import scan of Windows binaries, static source scan, lockfile checks.
9. **Needs a Windows runner or machine:** building the real Windows bundle (the `win32` branches of the spec are untested), the firewall control/treatment probe, tuning the `ctypes.dlopen` allowlist for Geosupport, and checking what `nycgeo.dll` imports. Windows Sandbox with `<Networking>Disable</Networking>` is a good manual check that the app works offline ([wsb options](https://learn.microsoft.com/en-us/windows/security/application-security/application-isolation/windows-sandbox/windows-sandbox-configure-using-wsb-file)).
10. **Optional layers are weak fits.** Low integrity: the Mandatory Integrity Control page says nothing about network access (Unconfirmed that it blocks it). AppContainer does gate network by capability but needs a profile, and file access to user CSVs and Geosupport files becomes a project of its own. App Control for Business controls which code may run, not network access. ([MIC](https://learn.microsoft.com/en-us/windows/win32/secauthz/mandatory-integrity-control), [AppContainer for legacy apps](https://learn.microsoft.com/en-us/windows/win32/secauthz/appcontainer-for-legacy-applications-), [App Control](https://learn.microsoft.com/en-us/windows/security/application-security/application-control/app-control-for-business/appcontrol-and-applocker-overview))
11. **Three places where a primary source contradicted what I expected.** (a) PEP 578's table of "potential" events uses names like `socket.address` and `urllib.urlopen`; the real events are `socket.connect`, `socket.getaddrinfo`, `urllib.Request` and so on. (b) The `ctypes.call_function` event is documented as raised by "some ways to invoke foreign function calls", but the source raises it only from two private helpers, so it cannot gate ordinary `ctypes` calls. (c) lxml's docs page says `resolve_entities` is "on by default"; the source and my test show the default is `'internal'`, which does not resolve external entities.
12. **Python 3.12 vs 3.13.** `telnetlib` and its events exist only on 3.12. The sub-interpreter modules are `_xxsubinterpreters` (3.12) and `_interpreters` (3.13); on the 3.13 build I used they are builtin on Linux too, and `importlib.import_module("_interpreters")` bypassed an import-time deny (T3), which is why the guard also sets `sys.modules[name] = None` for them. ([PC/config.c 3.13](https://github.com/python/cpython/blob/3.13/PC/config.c), [telnetlib, 3.12](https://docs.python.org/3.12/library/telnetlib.html))
13. **Scope of "no AI".** These controls show the shipped app contains no AI client library or model file, and (with the firewall rule in place and working) should be unable to open a connection to an AI service; the residual gaps are in Open risks. They say nothing about how the source was written; that is a process question, not a technical one.
14. **Biggest remaining risks:** the Windows branch has never run; the firewall rule can be removed by an admin or ignored under a restrictive GPO; kernel-brokered I/O (SMB, WebDAV) is not attributed to the app's rule (Unconfirmed); mapped network drives look like local paths to the `open` event; the Geosupport DLL's own behavior is undocumented in the guide I could read.

---

## 1. Python audit hooks (PEP 578)

### 1.1 What they are, and what the documentation says they are not

- `sys.addaudithook(hook)` appends a hook for "the current (sub)interpreter". A hook "can then log the event, raise an exception to abort the operation, or terminate the process entirely." ([sys.addaudithook](https://docs.python.org/3/library/sys.html#sys.addaudithook))
- Hooks cannot be removed or replaced. Hooks added from C are global; hooks added from Python are "only for the current interpreter". ([PEP 578, Audit Hook](https://peps.python.org/pep-0578/))
- They "are not suitable for implementing a 'sandbox'. In particular, malicious code can trivially disable or bypass hooks added using this function. At a minimum, any security-sensitive hooks must be added using the C API `PySys_AddAuditHook()` before [initializing] the runtime, and any modules allowing arbitrary memory modification (such as `ctypes`) should be completely removed or closely monitored." ([sys.addaudithook](https://docs.python.org/3/library/sys.html#sys.addaudithook))
- The PEP says the same thing at more length: it "does not attempt to restrict functionality", and "in most cases ... the intention is to enable logging rather than creating a sandbox". ([PEP 578, Why Not A Sandbox](https://peps.python.org/pep-0578/#why-not-a-sandbox))
- Our threat model is accidental or careless network use by our own code and its libraries, not a hostile Python program. For that model a fail-closed hook is a reasonable layer. It is not a guarantee against deliberate bypass, and we should not describe it as one.
- A C-level hook (`PySys_AddAuditHook`) would be global and would also cover sub-interpreters, but it must be installed before the runtime initializes ([sys.addaudithook](https://docs.python.org/3/library/sys.html#sys.addaudithook)). PyInstaller's bootloader starts the runtime, so that would mean a custom bootloader. **Inference:** not worth it here.
- **Contradiction of expectation:** PEP 578's "Table 2: Potential CPython Audit Hooks" lists events named `socket.address` and `urllib.urlopen` ([PEP 578](https://peps.python.org/pep-0578/)). The events CPython actually raises are different (next section). Use the docs table, not the PEP, to write rules.

### 1.2 Events that cover outbound connections and DNS

All of these are documented on the module pages and in the generated [audit events table](https://docs.python.org/3/library/audit_events.html). I checked each name against the `.. audit-event::` directives in the 3.12 and 3.13 documentation source and against the C or Python call site.

| Area | Events | Source |
|---|---|---|
| Socket creation and use | `socket.__new__`, `socket.bind`, `socket.connect` (also for `connect_ex`), `socket.sendto`, `socket.sendmsg` | [socket docs](https://docs.python.org/3.12/library/socket.html); call sites in [socketmodule.c](https://github.com/python/cpython/blob/3.12/Modules/socketmodule.c) (`PySys_Audit("socket.connect"...)` at the connect and connect_ex implementations) |
| DNS and name lookups | `socket.getaddrinfo`, `socket.gethostbyname` (also `gethostbyname_ex`), `socket.gethostbyaddr`, `socket.getnameinfo`, `socket.getservbyname`, `socket.getservbyport`, `socket.gethostname`, `socket.sethostname` | [socket docs](https://docs.python.org/3.12/library/socket.html), [socketmodule.c](https://github.com/python/cpython/blob/3.12/Modules/socketmodule.c) |
| URL opening | `urllib.Request` (raised in `OpenerDirector.open`, so it also fires for `file:` URLs), then `http.client.connect`, `http.client.send` | [urllib.request docs](https://docs.python.org/3.12/library/urllib.request.html), [Lib/urllib/request.py](https://github.com/python/cpython/blob/3.12/Lib/urllib/request.py) (`sys.audit('urllib.Request', ...)` in `OpenerDirector.open`), [http.client docs](https://docs.python.org/3.12/library/http.client.html) |
| Other protocols | `ftplib.connect`, `ftplib.sendcmd`, `smtplib.connect`, `smtplib.send`, `poplib.connect`, `poplib.putline`, `imaplib.open`, `imaplib.send`, `telnetlib.Telnet.open` and `.write` (3.12 only: the module was removed in 3.13) | [ftplib](https://docs.python.org/3.12/library/ftplib.html), [smtplib](https://docs.python.org/3.12/library/smtplib.html), [poplib](https://docs.python.org/3.12/library/poplib.html), [imaplib](https://docs.python.org/3.12/library/imaplib.html), [telnetlib](https://docs.python.org/3.12/library/telnetlib.html) |
| Opening a browser or another program | `webbrowser.open`, `subprocess.Popen`, `os.system`, `os.exec`, `os.spawn`, `os.posix_spawn`, `os.fork`, `os.forkpty`, `os.startfile` and `os.startfile/2` (Windows), `winreg.ConnectRegistry` (Windows, remote registry) | [webbrowser](https://docs.python.org/3.12/library/webbrowser.html), [subprocess](https://docs.python.org/3.12/library/subprocess.html), [os](https://docs.python.org/3.12/library/os.html), [winreg](https://docs.python.org/3.12/library/winreg.html) |
| Native code | `ctypes.dlopen`, `ctypes.dlsym`, `ctypes.dlsym/handle`, `ctypes.addressof`, `ctypes.string_at`, `ctypes.wstring_at`, `ctypes.cdata`, `ctypes.cdata/buffer`, `ctypes.set_exception`, `ctypes.call_function` | [ctypes docs](https://docs.python.org/3.12/library/ctypes.html); call sites in [callproc.c](https://github.com/python/cpython/blob/3.12/Modules/_ctypes/callproc.c) and [_ctypes.c](https://github.com/python/cpython/blob/3.12/Modules/_ctypes/_ctypes.c) |
| Imports and files | `import` (module name, filename, `sys.path`, `sys.meta_path`, `sys.path_hooks`), `open` (path, mode, flags) | `import` raised in [Python/import.c](https://github.com/python/cpython/blob/3.12/Python/import.c) (`import_find_and_load`) and [Python/importdl.c](https://github.com/python/cpython/blob/3.12/Python/importdl.c) (extension modules); `open` in [builtin functions docs](https://docs.python.org/3.12/library/functions.html#open) |
| Windows-only internals | `_winapi.CreateFile`, `_winapi.CreateProcess`, `_winapi.CreateNamedPipe` | "raised internally and do not correspond to any public API" ([audit_events.rst, 3.12](https://github.com/python/cpython/blob/3.12/Doc/library/audit_events.rst)) |

**Tested (T1, 3.12.3):** `create_connection` raised `socket.getaddrinfo`, `socket.__new__`, `socket.connect`. `urlopen` raised `urllib.Request`, `socket.getaddrinfo`, `socket.__new__`, `socket.connect`, `http.client.connect`, `http.client.send`. `xmlrpc.client` goes through `http.client.*`. A UDP socket that called `connect()` and then `send()` raised only `socket.__new__` and `socket.connect`; there is no event for `send()`.

**Windows path:** the events are raised from shared source, so Winsock use through Python's `socket` module raises the same events. **Inference:** I did not run this on Windows. The Windows-specific paths are `os.startfile` (the Windows way to open a URL in the default browser), `winreg.ConnectRegistry`, `ctypes.windll` / `WinDLL` (which raise `ctypes.dlopen` from `load_library` in [callproc.c](https://github.com/python/cpython/blob/3.12/Modules/_ctypes/callproc.c)), and the `_winapi.*` events above.

### 1.3 Can the hook be removed or bypassed? What can it not stop?

Removal: there is no API ([PEP 578](https://peps.python.org/pep-0578/)). **Tested (T3):** from the frame of a raised exception the caller can reach the hook's closure variables and module globals. Clobbering `OfflineViolation` in the module globals turned the denial into a `TypeError`, but the operation was still aborted, because any exception raised by a hook aborts the operation. The closure in the recommended code binds frozensets, so a hostile program can still defeat it, but accidents cannot.

What it cannot see (all **Tested**, on 3.12.3 and 3.13.18 unless noted):

| Gap | Evidence |
|---|---|
| **Sub-interpreters.** A hook added with `sys.addaudithook` belongs to one interpreter ([sys.addaudithook](https://docs.python.org/3/library/sys.html#sys.addaudithook)). A socket created inside a sub-interpreter produced no events in the main interpreter's hook, on both versions. | T4. 3.12 used `_xxsubinterpreters.create()` and `run_string()`; 3.13 used `_interpreters.create()` and `exec()`. |
| **Sub-interpreter modules cannot be removed from a Windows build.** `_xxsubinterpreters` and `_xxinterpchannels` (3.12), `_interpreters`, `_interpchannels`, `_interpqueues` (3.13), `_winapi` and `winreg` are compiled in. | [PC/config.c 3.12](https://github.com/python/cpython/blob/3.12/PC/config.c), [PC/config.c 3.13](https://github.com/python/cpython/blob/3.13/PC/config.c). The guard denies their import and also puts `None` in `sys.modules`. |
| **`importlib.import_module` of builtin or pure-Python modules raises no `import` event.** The event comes from `import_find_and_load` in C (reached by the `import` statement and `__import__`) and from `importdl.c` (extension modules). `import_module` calls the pure-Python `_bootstrap._gcd_import`. | [importlib/__init__.py](https://github.com/python/cpython/blob/3.12/Lib/importlib/__init__.py). T2: `import webbrowser` was not denied. T3: on 3.13, `importlib.import_module("_interpreters")` succeeded under the guard until the `None` entries were added. |
| **`ctypes` calls through pointers resolved earlier, `ctypes.memmove`, `ctypes.cast`.** The `ctypes.call_function` event is raised only by the private helpers `call_function` and `call_cdeclfunction`, not by ordinary foreign-function calls, even though the docs say "some ways to invoke foreign function calls may raise" it. | [callproc.c](https://github.com/python/cpython/blob/3.12/Modules/_ctypes/callproc.c), [ctypes docs](https://docs.python.org/3.12/library/ctypes.html). T3: a `getpid` pointer resolved before the guard still ran. |
| **`send`, `sendall`, `recv` on a socket opened before the guard**, and `send()` after a UDP `connect()`. | T1, T2 |
| **All native code.** Qt's `QDesktopServices::openUrl` calls `ShellExecute` on Windows; libxml2's HTTP and FTP client lives in `etree.pyd`; `nycgeo.dll` is a closed DLL. None of it passes through Python. | [qwindowsservices.cpp](https://github.com/qt/qtbase/blob/v6.12.0/src/plugins/platforms/windows/qwindowsservices.cpp) (`shellExecute` calls `ShellExecute`); T14 |
| **Mapped network drives (`Z:\...`) and OneDrive-style placeholders** look like local paths to the `open` event. | **Inference** from the event carrying only the path string; not tested on Windows. |

**Mitigations used:** fail-closed allowlist for `ctypes` (`ctypes.dlopen` allowed only under the Geosupport directory, `ctypes.dlsym` only for `NYCgeo` and `geo`); `ctypes.addressof`, `string_at`, `wstring_at`, `cdata`, `gc.get_objects`, `gc.get_referrers`, `gc.get_referents` denied; sub-interpreter modules unimportable; install the hook before importing anything else.

### 1.4 Is monkeypatching `socket` a useful second layer?

**Tested (T5, both versions).** Replacing `socket.socket` with a class that raises blocked `socket.socket()`, `socket.create_connection` (which looks up the module global) and `urllib.request.urlopen`. It did not block `_socket.socket()`, a name imported earlier with `from socket import socket`, a subclass of `_socket.socket`, `socket.getaddrinfo`, or `_socket.getaddrinfo`. Assigning an attribute on the C type `_socket.socket` raises `TypeError: cannot set 'connect' attribute of immutable type`. `socket.socket` is a Python subclass of the C class `_socket.socket` ([Lib/socket.py](https://github.com/python/cpython/blob/3.12/Lib/socket.py), `class socket(_socket.socket)`).

The audit events are raised inside the C implementation ([socketmodule.c](https://github.com/python/cpython/blob/3.12/Modules/socketmodule.c)), below everything a Python-level patch can reach, so the hook is strictly better in production. The well-known test-time use is `pytest-socket`, which "disables all network calls flowing through Python's `socket` interface, including DNS resolution" for tests ([pytest-socket README](https://github.com/miketheman/pytest-socket)). Recommendation: use it in the test suite; do not ship it as a layer.

---

## 2. PyInstaller: exclusion and proving what was bundled

### 2.1 How to exclude

- `--exclude-module`: "Optional module or package (the Python name, not the path name) that will be ignored (as though it was not found)." ([usage](https://pyinstaller.org/en/stable/usage.html)). In a spec file the same list is `Analysis(..., excludes=[...])`. The spec-file page I read only shows `excludes=None` in an example and does not describe it ([spec files](https://pyinstaller.org/en/stable/spec-files.html)), so the usage text is the documentation.
- Modules that are excluded but still imported by something show up in the warnings file as `excluded module named X - imported by ...`. The writer is `_write_warnings` in [build_main.py](https://github.com/pyinstaller/pyinstaller/blob/v6.22.3/PyInstaller/building/build_main.py), which prints `<status> module named <name> - imported by ...` for every entry in the graph's missing list. The documentation page only describes this file as holding "module not found" messages ([when things go wrong](https://pyinstaller.org/en/stable/when-things-go-wrong.html)). **Tested (T9):** my hardened build wrote 15 "excluded module named" lines, for example `excluded module named urllib.request - imported by numpy.lib._datasource (delayed), pandas.io.common (delayed, conditional), xml.dom.xmlbuilder (delayed, conditional), xml.sax.saxutils (top-level), lxml.html (delayed, optional), lxml.ElementInclude (optional), lxml.html.html5parser (optional)`. That file is a free import audit trail.
- The TOC lists produced by `Analysis` (`a.pure`, `a.binaries`, `a.datas`) are plain lists of three-element tuples `(dest_name, src_name, typecode)` and can be modified in the spec file ([advanced topics, TOC lists](https://pyinstaller.org/en/stable/advanced-topics.html#the-toc-and-tree-classes), source in [doc/advanced-topics.rst](https://github.com/pyinstaller/pyinstaller/blob/v6.22.3/doc/advanced-topics.rst)). The Qt plugins and DLLs that hooks collect are removed this way (T9).
- Runtime hooks given with `--runtime-hook` / `runtime_hooks=` "[are] bundled with the executable and [are] executed before any other code or module" ([usage](https://pyinstaller.org/en/stable/usage.html)). In the source, user hooks are placed ahead of PyInstaller's own: "First hooks in the list are executed first. Put their graph nodes at the head of the priority_scripts list" ([depend/analysis.py](https://github.com/pyinstaller/pyinstaller/blob/v6.22.3/PyInstaller/depend/analysis.py), `analyze_runtime_hooks`). That is where the audit hook gets installed.
- PyInstaller cannot see imports made inside compiled extension modules: "Hidden imports can also occur when an extension module uses the Python/C API to do an import. When this occurs, Analysis can detect nothing. There will be no warnings, only an ImportError at run-time." ([when things go wrong](https://pyinstaller.org/en/stable/when-things-go-wrong.html)). **Tested (T9):** numpy's compiled random module imports `secrets` and `hmac`; the hardened build crashed with `ModuleNotFoundError: secrets` until I added `hiddenimports=["secrets", "hmac"]`. Every exclusion list needs a frozen smoke test for this reason.

### 2.2 Which stdlib network modules are safe to exclude for this stack

**Tested (T8, T9, T10).** Importing the real app stack unfrozen (numpy, pandas, openpyxl, lxml, `PySide6.QtCore/QtGui/QtWidgets`, `geosupport`; 832 modules in `sys.modules`) imports none of: `socket`, `_socket`, `ssl`, `http`, `urllib.request`, `ftplib`, `smtplib`, `xmlrpc`, `socketserver`, `webbrowser`, `asyncio`, `multiprocessing`, `PySide6.QtNetwork`. It does import `select`, `selectors`, `subprocess` (first imported by `pandas._config.localization`), `ctypes` (first imported by `numpy._core._internal`), `secrets` and `hmac` (by `numpy.random`), `urllib.parse`, `ipaddress`, `mimetypes`. So `select`, `selectors`, `subprocess` and `ctypes` are not excluded; they are not network modules, and the guard gates the dangerous events inside them. On Windows, `subprocess` imports `_winapi` and only the non-Windows branch imports `select` and `selectors` ([Lib/subprocess.py, 3.12](https://github.com/python/cpython/blob/3.12/Lib/subprocess.py)), so those two being present is partly a Linux artifact of this experiment; whether `select.pyd` ends up in the Windows build is **Unconfirmed** (the PE allowlist tolerates it).

I made every module in the spec's exclude list unimportable in a normal interpreter (82 modules) and exercised the stack (T10). Everything worked (xlsx round trip, csv/json round trip, merge/groupby, `read_xml`, lxml parse/xpath/xslt, `lxml.html`, `xml.dom.minidom`, `xml.etree`, `np.loadtxt` on a local file, a PySide6 window with a table). These broke, as expected:

| Excluded module | What breaks | Evidence |
|---|---|---|
| `urllib.request` | `import xml.sax.saxutils` and therefore `xml.sax.make_parser()` (the default expat reader raises `SAXReaderNotAvailable`); URL branches of pandas and numpy (which is the point) | T10; the warn file lists `xml.sax.saxutils (top-level)` |
| `socket` | Anything that imports it at top level: `asyncio`, `multiprocessing.reduction`, `http.client`. Delayed users (`platform`, `uuid`) only break on the code path that needs it. | warn-file line for `socket`; T9 |
| `multiprocessing` | `ProcessPoolExecutor` and `n_jobs`-style parallelism. Required in practice: PyInstaller's own `pyi_rth_multiprocessing` runtime hook imports `multiprocessing` ([hook source](https://github.com/pyinstaller/pyinstaller/blob/v6.22.3/PyInstaller/hooks/rthooks/pyi_rth_multiprocessing.py)), and with the audit hook installed first, that import pulled in `socket` and crashed the first unhardened build at startup (T9). | T9 |
| `asyncio` | Nothing in this stack. | T8 |

I deliberately did **not** exclude `email`: it is not a network module, and every network module that imports it is already excluded. (An earlier draft excluded it; it only adds breakage risk, for example `importlib.metadata` needs it.)

### 2.3 Listing what got bundled, so a test can assert absence

Three checks, in order of how stable the format is:

1. **In the spec, at build time (documented TOC format).** After `Analysis`, inspect `a.pure` (Python modules), `a.binaries` and `a.datas`, and `raise SystemExit(...)` if a forbidden name is present. This is in the recommended spec. It fails the build rather than a later test.
2. **Output folder walk (stable).** List every file under the one-folder output and assert no forbidden file names (`_socket.*`, `_ssl.*`, `libssl*`, `Qt6Network*`, `plugins/generic/`, `plugins/tls/` ...) and no model files (`.onnx`, `.gguf`, `.safetensors`, `.pt` ...). On Windows, additionally scan every `.dll` and `.pyd` with a PE reader (section 7).
3. **Build records (works, but the format is not documented on the pages I read).** `build/<name>/PYZ-00.toc` and `COLLECT-00.toc` are Python literals (`ast.literal_eval` works), `base_library.zip` holds the bootstrap stdlib modules, `warn-<name>.txt` and `xref-<name>.html` are the documented import audit files ([when things go wrong](https://pyinstaller.org/en/stable/when-things-go-wrong.html)). Pin the PyInstaller version if tests parse the `.toc` files. `pyi-archive_viewer` is the alternative for listing the PYZ contents (**Unconfirmed**: not tried).

**Tested (T9, Linux build of the demo app):**

| Build | PYZ modules | COLLECT entries | Forbidden modules found | Forbidden files found |
|---|---|---|---|---|
| Default (no excludes, venv with dev tools) | 1,504 | 425 | socket, ssl, http.client, urllib.request, ftplib, xmlrpc.client, asyncio, socketserver, http.server, webbrowser, multiprocessing, unittest, pydoc, setuptools, QtNetwork | `_ssl`, libssl, `_asyncio`, Qt6Network, `plugins/tls`, `plugins/networkinformation`, `plugins/generic` |
| Clean venv, no excludes | 909 | 417 | the same, minus setuptools | the same |
| Hardened spec | 809 | 400 | none | `libQt6Network` only (Linux: the PySide6 extensions link it; see 3.2) |

The frozen hardened demo started, round-tripped CSV and Excel through file objects, parsed XML, showed a Qt window offscreen, and the guard turned `import socket` and `pandas.read_csv("http://...")` into `OfflineViolation` (T9).

**3.12 vs 3.13:** nothing in the exclusion mechanism differs. What differs is what can be excluded on Windows: the sub-interpreter modules are builtin on python.org Windows builds for both versions ([3.12](https://github.com/python/cpython/blob/3.12/PC/config.c), [3.13](https://github.com/python/cpython/blob/3.13/PC/config.c)), while `_socket`, `_ssl`, `select`, `_asyncio` and `_overlapped` are separate extension modules that exclusion does remove ([PCbuild/pcbuild.proj](https://github.com/python/cpython/blob/3.12/PCbuild/pcbuild.proj)). `_multiprocessing` and `_overlapped` are also separate `.pyd` files on Windows, so the spec excludes them with `multiprocessing` and `asyncio`. Names such as `telnetlib`, `nntplib` and `smtpd` in the exclude list do not exist on 3.12 or 3.13; PyInstaller accepted the list unchanged on 3.12.

---

## 3. Qt (PySide6 Widgets)

### 3.1 Do QtWidgets and QtGui pull in QtNetwork?

No, at every level I could check.

- **Python level (Tested, T8).** Importing `PySide6.QtCore`, `QtGui` and `QtWidgets` leaves `PySide6.QtNetwork` out of `sys.modules`.
- **C++ build level.** In qtbase v6.12.0, `src/gui/CMakeLists.txt` links `Qt::CorePrivate` and, publicly, `Qt::Core`; `src/widgets/CMakeLists.txt` links `Qt::CorePrivate`, `Qt::GuiPrivate`, `Qt::Core` and `Qt::Gui`. The only mention of "network" in the gui file is icon file names (`networkdrive-16.png` and so on), and the widgets and corelib files do not mention it. Platform-specific blocks add only system libraries (Widgets on Windows: `dwmapi`, `shell32`, `uxtheme`). ([gui](https://github.com/qt/qtbase/blob/v6.12.0/src/gui/CMakeLists.txt), [widgets](https://github.com/qt/qtbase/blob/v6.12.0/src/widgets/CMakeLists.txt), [corelib](https://github.com/qt/qtbase/blob/v6.12.0/src/corelib/CMakeLists.txt))
- **Windows binaries (Tested, T11, PE import tables of the 6.12.0 `win_amd64` wheels).** The import closure of `QtWidgets.pyd` is `Qt6Core.dll`, `Qt6Gui.dll`, `Qt6Widgets.dll`, `pyside6.abi3.dll` and `shiboken6.abi3.dll`. `Qt6Network.dll` is not in it. `QtNetwork.pyd` closure does include `Qt6Network.dll`, which imports `dnsapi.dll`, `iphlpapi.dll`, `winhttp.dll`, `secur32.dll` and `ws2_32.dll`.
- **But the process still contains winsock code.** `Qt6Core.dll` itself imports `ws2_32.dll`, `mpr.dll` and `netapi32.dll`; `python312.dll` and `select.pyd` import `ws2_32.dll`; `lxml/etree.pyd` and `objectify.pyd` import `ws2_32.dll` (T11 for the wheels; T14 for CPython 3.12.16 built by conda-forge, which stands in for the python.org build). Import tables prove capability, not use, but they mean there is no way to remove network capability from the process by exclusion alone. That is why the firewall layer exists.
- **A startup trap in the PySide6 package.** On Windows, `PySide6/__init__.py` does `from . import QtNetwork` inside `try/except ImportError` if a `PySide6/openssl` folder exists ([`PySide6/__init__.py`, read from the unpacked 6.12.0 wheel](https://pypi.org/project/PySide6-Essentials/6.12.0/#files)). The 6.12.0 wheel has no such folder, so it does not run. PyInstaller's Qt hook has special code that collects OpenSSL DLLs when `QtNetwork` is collected ([qt/__init__.py](https://github.com/pyinstaller/pyinstaller/blob/v6.22.3/PyInstaller/utils/hooks/qt/__init__.py), `collect_qtnetwork_files`), which is one more reason to exclude `QtNetwork`. The guard raises an `ImportError` subclass for denied imports so that code like the above falls back instead of crashing (T2).

### 3.2 Linux differs from Windows, so a Linux CI build cannot prove Qt Network is absent

PyInstaller's own Qt hook notes that "PySide2 and PySide6 on linux seem to link all extension modules against libQt5Core, libQt5Network, and libQt5Qml (or their libQt6* equivalents)" ([qt/__init__.py](https://github.com/pyinstaller/pyinstaller/blob/v6.22.3/PyInstaller/utils/hooks/qt/__init__.py)). **Tested (T9):** my hardened Linux build still contains `libQt6Network.so`. The PE evidence says the Windows wheels do not link it from Core/Gui/Widgets, so on Windows `Qt6Network.dll` can and should be absent. The test therefore treats `Qt6Network*`, `Qt6Qml*` and `Qt6Quick*` as forbidden only when `sys.platform == "win32"`. The Windows branch of the spec (which drops these DLLs) has not been run.

### 3.3 Excluding Qt network modules and plugins

- **Python modules.** `excludes=["PySide6.QtNetwork", "PySide6.QtWebEngine*", "PySide6.QtWebSockets", "PySide6.QtWebChannel", "PySide6.QtHttpServer", "PySide6.QtNetworkAuth", "PySide6.QtRemoteObjects", "PySide6.QtPositioning", "PySide6.QtLocation", ...]` (T9, full list in the spec). `PySide6-Essentials` already omits Addons and WebEngine, but it still ships `QtNetwork`, `QtQml`, `QtQuick`, `QtSql` and `QtDBus` (T11, wheel contents).
- **Plugins.** PyInstaller assigns plugin directories to Qt modules: for Qt 6, `QtNetwork` owns `networkaccess`, `networkinformation` and `tls`; `QtGui` owns `accessiblebridge`, `egldeviceintegrations`, `generic`, `iconengines`, `imageformats`, `platforms`, `platforminputcontexts`, `platformthemes`, `xcbglintegrations` ([_modules_info.py](https://github.com/pyinstaller/pyinstaller/blob/v6.22.3/PyInstaller/utils/hooks/qt/_modules_info.py)). The PyInstaller hooks-config documentation I read has no option to limit Qt plugins; its only Qt advice is to exclude unused Qt bindings with `--exclude-module` ([hooks config](https://pyinstaller.org/en/stable/hooks-config.html)). So plugin files are removed by filtering `a.binaries` and `a.datas` in the spec (T9 does this on Linux).
- **Windows plugin DLLs that link `Qt6Network.dll` (Tested, T11):** `generic/qtuiotouchplugin.dll`, `networkinformation/qnetworklistmanager.dll`, `designer/qquickwidget.dll`, and every `qmltooling/qmldbg_*.dll`. The TUIO plugin is built with `LIBRARIES ... Qt::Network` ([tuiotouch/CMakeLists.txt](https://github.com/qt/qtbase/blob/v6.12.0/src/plugins/generic/tuiotouch/CMakeLists.txt)). **Inference:** because the QtGui entry owns the whole `generic` directory, PyInstaller's binary dependency analysis would pull `Qt6Network.dll` back in through `qtuiotouchplugin.dll` even with `QtNetwork` excluded. I have not run a Windows build to see it happen, so the spec drops `plugins/generic` explicitly and the PE test fails the build if `Qt6Network.dll` appears anyway.
- **Generic plugins load only on request.** QGuiApplication loads extra generic plugins named by the `-plugin` command-line option and the `QT_QPA_GENERIC_PLUGINS` environment variable ([qguiapplication.cpp](https://github.com/qt/qtbase/blob/v6.12.0/src/gui/kernel/qguiapplication.cpp), option text "specifies additional plugins to load ... Concatenated with the plugins in the QT_QPA_GENERIC_PLUGINS environment variable", and the `qgetenv("QT_QPA_GENERIC_PLUGINS")` read). The same file documents `-qmljsdebugger=` ("activates the QML/JS debugger with a specified port"). So create the application with only the program name, `QApplication([sys.argv[0]])`, so command-line switches from a user or a shortcut cannot enable plugins or a debug port. The Qt documentation pages I read do not describe these switches, so the source is the reference.

### 3.4 Does `QDesktopServices.openUrl` open a browser?

Yes. The documentation says a file URL "will be opened with a suitable application instead of a Web browser", a mailto URL uses the e-mail client, and otherwise "a web browser will be used to fetch and display the file"; "This result will not be reported back to the application" ([QDesktopServices](https://doc.qt.io/qt-6/qdesktopservices.html)). On Windows the implementation builds a native path or full-encoded URL string and calls `ShellExecute` in a helper thread ([qwindowsservices.cpp](https://github.com/qt/qtbase/blob/v6.12.0/src/plugins/platforms/windows/qwindowsservices.cpp), `shellExecute`). That starts another program (the default browser) which is not covered by our program's firewall rule, and Python's audit hook never sees it (see the gap table in 1.3). `openUrl` looks up a handler registered with `setUrlHandler` for the scheme before it calls the platform code ([qdesktopservices.cpp](https://github.com/qt/qtbase/blob/v6.12.0/src/gui/util/qdesktopservices.cpp)), so registering a no-op handler for `http`, `https`, `ftp` and `mailto` is an optional extra safety net (**Inference**, not tested). The reliable control is not to call it, enforced by the static scan (`openUrl`, `QDesktopServices`, `setOpenExternalLinks`, `QProcess`, `os.startfile`).

Widgets that can trigger it by themselves:

- `QLabel.openExternalLinks`: "Specifies whether QLabel should automatically open links using QDesktopServices::openUrl()". Default false ([QLabel](https://doc.qt.io/qt-6/qlabel.html)).
- `QTextBrowser.openExternalLinks`: default false; "Links are considered external if their scheme is neither file or qrc.". `openLinks` defaults to true but opens links inside the browser by loading the resource, and the default `loadResource` "tries to locate the resources by interpreting name as a file name" ([QTextBrowser](https://doc.qt.io/qt-6/qtextbrowser.html)). In the source, `QTextDocument::loadResource` converts the URL with `toLocalFile()` and opens it with `QFile`, so an `http:` image in rich text yields an empty path and no network request ([qtextdocument.cpp](https://github.com/qt/qtbase/blob/v6.12.0/src/gui/text/qtextdocument.cpp)).
- A `QFileDialog` can browse to network shares if the user does. Python's `open` event then carries a `\\server\share` path and the guard denies it. Mapped drive letters are not detectable that way (1.3).

### 3.5 Does Qt make network calls on its own?

For the modules this app uses, the structure says it cannot use Qt's networking classes: the classes live in `QtNetwork`, which Core, Gui and Widgets do not link (3.1). I did not find a primary statement saying "Qt Widgets never contacts the network", so the evidence is structural, not a promise (**Unconfirmed** as a documented guarantee). The firewall rule, the absence of `Qt6Network.dll`, and the PE scan are what turn this into something testable.

### 3.6 Bundling the Archivo font (SIL OFL 1.1)

- **License.** The Archivo font is under the SIL Open Font License 1.1 ("Copyright 2020 The Archivo Project Authors"). Permission is granted to "use, study, copy, merge, embed, modify, redistribute, and sell" copies, and "Original or Modified Versions of the Font Software may be bundled, redistributed and/or sold with any software, provided that each copy contains the above copyright notice and this license." The font cannot be sold by itself. ([OFL.txt in Omnibus-Type/Archivo](https://github.com/Omnibus-Type/Archivo/blob/master/OFL.txt)) Ship `OFL.txt` next to the font in the one-folder output and in the installer.
- **Loading.** `QFontDatabase::addApplicationFont(fileName)` supports "TrueType fonts, TrueType font collections, and OpenType fonts" and "returns -1 if the font could not be loaded"; `applicationFontFamilies(id)` gives the family names to use ([QFontDatabase](https://doc.qt.io/qt-6/qfontdatabase.html)). The page gives no rule about calling it before or after creating the application; create the `QApplication` first (**Unconfirmed** that this is required). It reads a local file; nothing touches the network.
- **Variable fonts.** I did not check which files the Archivo repository ships. If only a variable-axis TTF is available, Qt's handling of its axes is **Unconfirmed** from the page read. Prefer static instances and check rendering on a Windows machine.
- **PyInstaller.** Add the font and license through `datas=[("assets/fonts/Archivo-Regular.ttf", "fonts"), ("assets/licenses/Archivo-OFL.txt", "licenses")]` and find them at run time under `sys._MEIPASS`, which, "For a one-folder bundle, this is the path to the `_internal` folder within the bundle" ([runtime information](https://pyinstaller.org/en/stable/runtime-information.html)). `--contents-directory` is for onedir builds only and names "the directory in which all supporting files" are placed; passing `.` restores the older layout ([usage](https://pyinstaller.org/en/stable/usage.html)). T9 shows the `_internal` folder in the output.

---

## 4. Library traps

### 4.1 lxml

- **Defaults.** `no_network` is on by default ("prevent network access when looking up external documents") ([lxml parsing](https://lxml.de/parsing.html)). The `resolve_entities` default is `'internal'` since lxml 5.0.0: "lxml no longer expands external entities (XXE) by default ... The new default is `resolve_entities='internal'`" ([CHANGES.txt, 5.0.0](https://github.com/lxml/lxml/blob/lxml-6.1.3/CHANGES.txt)). **Contradiction of expectation:** the lxml parsing page still says `resolve_entities` is "on by default". **Tested (T6, lxml 6.1.3):** a document with `<!ENTITY x SYSTEM "file:///tmp/...">` raised "Entity 'x' not defined" under the default parser, `iterparse` default, and `ETCompatXMLParser` default, and returned the file's contents only with `resolve_entities=True`. So never pass `resolve_entities=True`.
- **Fixed XXE bugs to pin past.** Before 6.1.0, `iterparse()` and `ETCompatXMLParser` still had `resolve_entities` set to `True`, "allowing for external entity injection (XXE)" (LP#2146291, CVE-2026-41066, fixed in 6.1.0). 6.1.3 fixed "External parameter entity parsing was allowed by default (with `resolve_entities="internal"`)" (LP#2165901). ([CHANGES.txt, 6.1.0 and 6.1.3](https://github.com/lxml/lxml/blob/lxml-6.1.3/CHANGES.txt)) The lock requires `lxml>=6.1.3`.
- **HTTP and FTP loading differs by platform.** lxml parses "from a local file, an HTTP URL or an FTP URL"; since 6.0 "HTTP, FTP and zlib support have become optional features" and "both HTTP and FTP are considered insecure protocols" ([lxml parsing](https://lxml.de/parsing.html)). The Linux wheels (libxml2 2.14.x) disabled direct HTTP and FTP, but "Windows binary wheels use the library versions libxml2 2.11.9" ([CHANGES.txt, 6.0.0](https://github.com/lxml/lxml/blob/lxml-6.1.3/CHANGES.txt)). **Tested (T6, T14):** on the Linux wheel `etree.LIBXML_FEATURES` has no `http` or `ftp`, and `etree.parse("http://127.0.0.1:port/doc.xml")` raised `OSError` with zero server hits. In the Windows `etree.cp312-win_amd64.pyd`, `strings` finds libxml2's client code (`USER anonymous`, `PASS anonymous@`, `PASV`, ` HTTP/1.0`, `Host: %s`, `http_proxy`, `ftp_proxy`) and the import table lists `socket`, `connect`, `send`, `recv`, `gethostbyname` from `ws2_32.dll`. **Inference:** on Windows `etree.parse("http://...")` can reach the network (not run). So: never hand lxml a URL, a UNC path or any string that lacks a `file` object or bytes; keep `no_network=True`.
- **External DTDs.** **Tested (T6, Linux wheel):** a document whose DOCTYPE pointed at an `http://127.0.0.1:port/` DTD produced zero server hits under the default parser, with `load_dtd=True`, with `load_dtd=True, no_network=False`, and with `dtd_validation=True, no_network=False`, because HTTP is compiled out of that wheel. The same test on the Windows wheel was not run; its libxml2 has the HTTP client (above), so keep `no_network=True` and never set `no_network=False`.
- **XSLT.** By default XSLT "supports all extension functions from libxslt and libexslt", and "Some extensions enable style sheets to read and write files on the local file system." Use `XSLTAccessControl.DENY_ALL` (class member) or `XSLTAccessControl(read_network=False, read_file=False, ...)`. Caveat from the docs: "XSL parsing (`xsl:import`, etc.) is not affected by this mechanism", so only load stylesheets we ship. ([lxml resolvers](https://lxml.de/resolvers.html), source in [xslt.pxi](https://github.com/lxml/lxml/blob/lxml-6.1.3/src/lxml/xslt.pxi), `DENY_ALL`). **Tested (T6):** with `DENY_ALL`, `document('file:///...')` raised "read rights ... denied".
- **Excluding `urllib.request` has a side effect here.** `lxml.html`, `lxml.ElementInclude` and `lxml.html.html5parser` import it in optional or delayed positions (warn-file line, T9); `import lxml.html` and parsing worked in the simulated exclusion (T10).

### 4.2 pandas and numpy

- **`read_*` accepts URLs.** The `read_csv` docstring: "Any valid string path is acceptable. The string could be a URL. Valid URL schemes include http, ftp, s3, gs, and file." ([pandas readers.py](https://github.com/pandas-dev/pandas/blob/main/pandas/io/parsers/readers.py)). `_get_filepath_or_buffer` imports `urllib.request` and calls `urlopen` for strings whose scheme is in `{"http", "https", "ftp", "file"}`; other `scheme://` strings go to `fsspec` ([pandas io/common.py](https://github.com/pandas-dev/pandas/blob/main/pandas/io/common.py)). The `urllib.request` import is deliberately lazy there, so excluding the module breaks only the URL branches.
- **Tested (T7, pandas 3.1.0):** `read_csv`, `read_excel`, `read_json`, `read_xml`, `read_html` given an `http://127.0.0.1:port/...` string each hit the loopback server (`read_excel` twice) and raised `http.client.connect`, `socket.connect`, `socket.getaddrinfo`, `urllib.Request`. `ftp://` raised `urllib.Request` then `socket.connect`. `file:///...` raised only `urllib.Request`. `s3://` raised `ImportError: Import fsspec failed` (no `fsspec` installed). A local `Path`, a plain local path string, or an opened file object raised no events. `np.loadtxt("http://...")` hit the server twice because `numpy.lib._datasource` opens URLs with `urlopen` ([numpy _datasource.py](https://github.com/numpy/numpy/blob/main/numpy/lib/_datasource.py)); `np.genfromtxt("http://...")` did not reach the server in my test (not investigated).
- **Rule for the app.** Open every input yourself: `with open(path, "rb") as f: pd.read_csv(f)`; reject any path string containing `://` or starting with `\\`; never forward a user-typed or config-file string straight into a `read_*` call. With the guard installed, a URL string becomes an `OfflineImportViolation` at `import urllib.request`.
- **Optional dependencies that would add network capability are not installed** in the lock (`fsspec`, `s3fs`, `requests`, `aiohttp`, `urllib3`, `bs4`, `html5lib`, `gcsfs`; all reported absent in T7). The lockfile test denies them (section 8).

### 4.3 openpyxl

- `load_workbook(..., keep_links=True)`: the docstring says "keep_links: whether links to external workbooks should be preserved. The default is True" (`openpyxl/reader/excel.py`, openpyxl 3.1.5 wheel, [PyPI](https://pypi.org/project/openpyxl/3.1.5/); the openpyxl documentation site returned an access error, so the installed source is the reference). In `openpyxl/reader/workbook.py`, `keep_links=False` sets `package.externalReferences = []`, with the comment "external links contain cached worksheets and can be very big"; with the default, `read_external_link(self.archive, rel.Target)` reads those parts from the workbook's own zip archive. Nothing is fetched. I searched openpyxl 3.1.5 and et_xmlfile for imports of `urllib`, `socket`, `http`, `ssl`, `ftplib`, `requests`, `webbrowser`, `smtplib`: none (static search, T8). Pass `keep_links=False` when cleaning client files so the output does not carry other workbooks' cached data forward (a data-hygiene choice, **Inference**).
- Relationship targets with `TargetMode="External"` (hyperlinks, linked workbooks) are skipped when `openpyxl/packaging/relationship.py` normalizes paths (`if r.TargetMode == "External": continue`); the writer creates them for hyperlinks (`openpyxl/worksheet/_writer.py`). Nothing opens them. Excel itself, or a user clicking a link in Excel, is outside this app and outside this document.

### 4.4 Indirect imports of `ftplib`, `xmlrpc`, `webbrowser`

None of them is imported by the app stack (T8). `webbrowser` and `ftplib` are not imported by pandas, numpy, openpyxl, lxml or Qt's Python modules in the graph I loaded. The tools to find an unexpected importer are PyInstaller's `warn-<name>.txt` and `xref-<name>.html` (each excluded module lists who imported it, and the xref page lets you "keep clicking the 'imported by' links until you find the top-level import" ([when things go wrong](https://pyinstaller.org/en/stable/when-things-go-wrong.html))), and at run time the audit `import` event, which names every first import. The runtime import-graph test (section 7) is the permanent check.

### 4.5 Geosupport and python-geosupport

- **What the wrapper does.** `load_geosupport` in `platform_utils.py` builds the DLL path with `build_win_dll_path`: if `geosupport_path` is given, `<geosupport_path>\bin\nycgeo.dll`; otherwise it scans the `PATH` entries that end in `bin` for a file named `nycgeo.dll`. Then, for 64-bit Python, `cdll.LoadLibrary(<that path>)` (32-bit Python uses `windll.LoadLibrary`); on Linux it loads `libgeo.so`. When `geosupport_path` is given, `geosupport.py` also sets `os.environ["GEOFILES"]` to `<geosupport_path>\Fls\` and rewrites `PATH` (drops entries containing "GEOSUPPORT", appends `<geosupport_path>\bin`). ([platform_utils.py](https://github.com/ishiland/python-geosupport/blob/master/geosupport/platform_utils.py), [geosupport.py](https://github.com/ishiland/python-geosupport/blob/master/geosupport/geosupport.py); I read the GitHub master copies, and compared `platform_utils.py` with the 1.1.0 wheel.) It reads its function tables from CSV files inside the package (`function_info/`, paths set in [config.py](https://github.com/ishiland/python-geosupport/blob/master/geosupport/config.py)), so the spec needs `collect_data_files("geosupport")` (T9: without it the frozen app raised `FileNotFoundError`). **Design consequence:** always pass `geosupport_path` explicitly, from a fixed location, so the DLL is never found by a `PATH` search.
- **Network behavior of the wrapper.** None: it imports no network module (static search, T8), and the README says "Secure and fast using local geocoding - no API calls required" ([README](https://github.com/ishiland/python-geosupport/blob/master/README.md)).
- **Network behavior of the DLL itself: Unconfirmed.** The NYC Planning guide I could read says nothing about license servers, activation or any runtime connection from Geosupport Desktop Edition, and nothing about `GEOFILES` ([NYC DCP user programming guide](https://www.nyc.gov/assets/planning/download/pdf/data-maps/open-data/upg.pdf)). Silence is not a guarantee. After installing Geosupport Desktop Edition on a Windows test machine, run the PE import scan on every DLL in its `bin` directory and add the result to the allowlist deliberately. The firewall rule covers the DLL anyway because it runs inside our process.
- **Guard consequences.** The Windows path produces `ctypes.dlopen` with the absolute DLL path and `ctypes.dlsym` for `NYCgeo`; the allowlist must name the real Geosupport install directory (the sample code uses `<install dir>\geosupport` as a placeholder, to be tuned on Windows). The DLL's own dependencies are loaded by the OS loader and raise no Python events. Because the wrapper edits `PATH` for the whole process, keep the Geosupport directory writable only by administrators (a general DLL-search-order concern, **Inference**).

---

## 5. Windows Firewall

### 5.1 Defaults and precedence

- "By default, Windows Firewall allows all outbound network traffic, unless it matches a rule that prohibits the traffic." ([configure](https://learn.microsoft.com/en-us/windows/security/operating-system-security/network-security/windows-firewall/configure)). Microsoft recommends leaving outbound allowed by default for most deployments ([rules](https://learn.microsoft.com/en-us/windows/security/operating-system-security/network-security/windows-firewall/rules)). So a per-program block rule is the way to restrict one app without changing the machine default.
- Precedence: the precedence list says "Explicitly defined allow rules take precedence over the default block setting", "Explicit block rules take precedence over any conflicting allow rules", and "More specific rules take precedence over less specific rules, except if there are explicit block rules as mentioned in 2."; "Outbound rules follow the same precedence behaviors", and "Windows Firewall doesn't support weighted, administrator-assigned rule ordering." ([rules](https://learn.microsoft.com/en-us/windows/security/operating-system-security/network-security/windows-firewall/rules)). Our block wins over a broad allow. One documented exception: an allow rule with `OverrideBlockRules` becomes an "allow bypass rule" ([New-NetFirewallRule, -Action](https://learn.microsoft.com/en-us/powershell/module/netsecurity/new-netfirewallrule?view=windowsserver2025-ps)).
- Application rules need the exact path: "The use of wildcard patterns, such as `C:\*\teams.exe` isn't supported in application rules. You can only create rules using the full path to the application(s)." ([rules](https://learn.microsoft.com/en-us/windows/security/operating-system-security/network-security/windows-firewall/rules)). The installer therefore expands `{app}` at install time.

### 5.2 Creating and removing the rule

`netsh` forms taken from Microsoft's examples: `netsh advfirewall firewall add rule name="BlockOutIP" protocol=TCP dir=out remoteip=192.168.1.100 action=block` and `netsh advfirewall firewall delete rule name="MyRule"` ([netsh advfirewall](https://learn.microsoft.com/en-us/windows-server/administration/windows-commands/netsh-advfirewall); "Rule name should be unique and can't be "all"."); `program="C:\MyApp\MyApp.exe" enable=yes ... profile=domain|private` and `delete rule name=... program="..."` ([Windows Firewall control troubleshooting](https://learn.microsoft.com/en-us/troubleshoot/windows-server/networking/netsh-advfirewall-firewall-control-firewall-behavior); that page's parameter list is deferred to `netsh advfirewall firewall add rule ?`, and its delete examples contain the literal placeholder text `name= rule name`).

PowerShell equivalents: `New-NetFirewallRule -DisplayName ... -Direction Outbound -Action Block -Program <full path> -Profile Any -Enabled True`. `-Program` is "specified as the full path to an application file"; `-Direction` defaults to Inbound; `-Profile` defaults to Any; `-Enabled` takes the strings "True" or "False" ([New-NetFirewallRule](https://learn.microsoft.com/en-us/powershell/module/netsecurity/new-netfirewallrule?view=windowsserver2025-ps)). Delete with `Remove-NetFirewallRule -DisplayName` ([configure with command line](https://learn.microsoft.com/en-us/windows/security/operating-system-security/network-security/windows-firewall/configure-with-command-line)). Verify with `Get-NetFirewallRule -DisplayName ... | Get-NetFirewallApplicationFilter`, the pipeline shown in the cmdlet page's example, which "returns application filter objects associated with the input rules" ([Get-NetFirewallApplicationFilter](https://learn.microsoft.com/en-us/powershell/module/netsecurity/get-netfirewallapplicationfilter?view=windowsserver2025-ps)); the page does not name the output property that holds the path (I expect `Program`, **Unconfirmed**). The `netsh advfirewall` page I read carries no deprecation notice.

### 5.3 From Inno Setup

- `[Run]` entries take `Filename`, `Parameters` ("can include constants"), and `Flags` including `runhidden` and `waituntilterminated` ([Run section](https://jrsoftware.org/ishelp/topic_runsection.htm)). `[UninstallRun]` entries can carry `RunOnceId`, "you can ensure that a particular [UninstallRun] entry will only be executed once during uninstallation" (same page). The `[UninstallRun]` page itself failed to load twice, so **Unconfirmed:** when exactly those entries run relative to file removal. Deleting by rule name (not by program) works whether or not the exe still exists, so the order does not matter for this use.
- `PrivilegesRequired` accepts `admin` or `lowest`; the default is `admin` ([PrivilegesRequired](https://jrsoftware.org/ishelp/topic_setup_privilegesrequired.htm)). Keep it at `admin`: adding firewall rules needs elevation. I did not find a statement about elevation on the netsh or PowerShell pages I read (**Unconfirmed**, but the Inno default covers it).
- `{app}` is "The application directory, which the user selects on the Select Destination Location page of the wizard." On 64-bit Windows, "by default", the `System32` path that `{sys}` returns "maps to the directory containing 32-bit system files, just like on 32-bit Windows" (the page text I received was cut after "maps to", so whether 64-bit install mode changes this is **Unconfirmed**). `{sysnative}` is "On 64-bit Windows, the directory containing 64-bit system files." `{autopf}` is listed among the auto constants and maps to `commonpf` in administrative mode and `userpf` otherwise ([constants](https://jrsoftware.org/ishelp/topic_consts.htm)). The page for `ArchitecturesInstallIn64BitMode` returned an access error, so the exact accepted value (`x64compatible` on newer Inno Setup, `x64` on older) is **Unconfirmed**. Whichever you choose, the Windows probe test (section 7) is what proves the rule really got installed.
- The `[Run]` page does not say what Setup does when a program exits with a non-zero code or cannot be started (**Unconfirmed**; the page only covers `skipifdoesntexist` for a missing `Filename`). So do not assume a failed `netsh` call stops the install: verify the rule in a test. `runhidden` "will launch the program in a hidden window" and `waituntilterminated` "will wait until the process has completely terminated" ([Run section](https://jrsoftware.org/ishelp/topic_runsection.htm)). Silent installs for test machines use `/VERYSILENT /SUPPRESSMSGBOXES /NORESTART /LOG /DIR=...` ([setup command line](https://jrsoftware.org/ishelp/topic_setupcmdline.htm)).
- Upgrades re-run `add rule` and, since names "should be unique", add a `delete rule` first (a delete of a missing rule fails harmlessly).

### 5.4 Does the rule cover everything the process does?

- It matches the process image path, so all DLLs loaded into `Crosswalk.exe` (Qt, lxml, the Geosupport DLL) are covered by it (**Inference** from "application rules"; not run).
- It does not cover other programs the app starts (for example a browser launched by `ShellExecute`), and **Unconfirmed** whether it covers I/O performed by system components on the app's behalf, such as the SMB or WebDAV client when the app opens `\\server\share\file.csv`. The guard denies UNC and `@SSL`/`DavWWWRoot` paths at the `open` event as compensation (1.3).
- Whether the firewall filters loopback traffic is **Unconfirmed**; do not use `127.0.0.1` in the probe test.
- Whether a blocked `connect()` fails immediately or times out is **Unconfirmed**; the probe test accepts either, with a short timeout.
- Auditing blocked connections (event 5157) is the usual Windows facility, but the Microsoft pages for it returned access errors, so I cannot cite them ([event 5157](https://learn.microsoft.com/en-us/windows/security/threat-protection/auditing/event-5157), unread).

### 5.5 Corporate-managed firewalls

- "The rule-merging policy settings either allow or prevent local administrators from creating their own firewall rules in addition to those rules obtained from CSP or GPO." "Administrators may disable *LocalPolicyMerge* in high-security environments ... This setting can impact some applications and services that automatically generate a local firewall policy upon installation." "Local Group Policy firewall rules and settings are applied even when rule merging is disabled through MDM or Group Policy." ([rules](https://learn.microsoft.com/en-us/windows/security/operating-system-security/network-security/windows-firewall/rules))
- So on a locked-down machine the installer's local rule may be ignored. Provide IT with the three facts (program path, direction out and in, action block) so they can deploy it with GPO or Intune, and check the effective policy: `ActiveStore` is "the currently active policy, which is the sum of all policy stores that apply to the computer" ([New-NetFirewallRule, -PolicyStore](https://learn.microsoft.com/en-us/powershell/module/netsecurity/new-netfirewallrule?view=windowsserver2025-ps)). That a locally created rule is shown inactive in `ActiveStore` under restrictive merge settings is **Unconfirmed**.
- Anything that turns the firewall off (a user, an administrator, or policy) also turns this layer off. The other layers are why that is not fatal.

---

## 6. Other Windows layers (what is practical)

- **Low integrity level (Mandatory Integrity Control).** Windows has four levels: low, medium, high, system; "a principal with a low integrity level cannot write to an object with a medium integrity level, even if that object's DACL allows write access" ([MIC](https://learn.microsoft.com/en-us/windows/win32/secauthz/mandatory-integrity-control)). The page says nothing about network access, so whether a low-IL process can reach the network is **Unconfirmed** from primary sources and I did not rely on it. It would also block writes to the user's normal files, which a data-cleaning tool needs.
- **AppContainer.** Its network isolation section describes "Isolating the application from network resources beyond those specifically allocated"; "Granular access can be granted for Internet access, Intranet access, and acting as a server" ([AppContainer isolation](https://learn.microsoft.com/en-us/windows/win32/secauthz/appcontainer-isolation)). The capabilities include `internetClient` ("apps can receive incoming data from the Internet"), `internetClientServer`, and `privateNetworkClientServer`, about which the page says "On Windows, this capability does not provide access to the Internet". The page calls `internetClient` and `enterpriseAuthentication` "examples of capabilities that apply only to AppContainer apps", because "a Medium IL app is already running as the user; so an app like that can already perform those operations without requiring those capabilities" ([app capability declarations](https://learn.microsoft.com/en-us/windows/apps/package-and-deploy/app-capability-declarations)). Neither AppContainer page states what network access a container with no capabilities has, so default-deny is **Unconfirmed** as a documented sentence (the isolation page does describe the goal as "Isolating the application from network resources beyond those specifically allocated"). An unpackaged app "can run in an app container, too", but you must create the AppContainer profile and call the Win32 APIs yourself, "it can be complicated", and "if you are in an app container, then the integrity level (IL) is always low"; legacy, unmodified ACL objects "block access requests from AppContainer processes by default" ([AppContainer for legacy apps](https://learn.microsoft.com/en-us/windows/win32/secauthz/appcontainer-for-legacy-applications-)). For an app that must open arbitrary user CSV and Excel files and Geosupport's files, that means a broker design or ACL changes. **Practical advice:** skip it.
- **App Control for Business (WDAC) / AppLocker.** "App Control was introduced with Windows 10 and allows organizations to control which drivers and applications are allowed to run on their Windows clients." Rules can be based on signer, file hash, path, and managed installer; policies "can be created and applied on any client edition of Windows 10 or Windows 11"; they deploy through MDM, Configuration Manager, PowerShell or Group Policy ([overview](https://learn.microsoft.com/en-us/windows/security/application-security/application-control/app-control-for-business/appcontrol-and-applocker-overview)). The page says nothing about network access control, so **Inference:** it limits what code can run, not what connections an allowed program makes, and it is not a substitute for the firewall rule. It is useful for an IT-managed fleet to allow only the signed `Crosswalk.exe` and block tools the app could otherwise be pointed at.
- **Windows Sandbox for testing.** A `.wsb` file's `<Networking>Disable</Networking>` "Disables networking in the sandbox"; `Default` "enables networking by creating a virtual switch on the host"; the feature "can be used with Windows 10 build 18342 or Windows 11" ([wsb file options](https://learn.microsoft.com/en-us/windows/security/application-security/application-isolation/windows-sandbox/windows-sandbox-configure-using-wsb-file)). Use it to check that the installed app works with no network at all. That shows the app does not depend on the network, not that it cannot use one.


---

## 7. Proving it with tests: what runs in Linux CI and what needs Windows

The rule I used: a test must be able to fail. Each layer below has a check, and for the important ones I ran a negative control (a deliberately broken input) to see it fail (T12).

### 7.1 Test inventory

| Check | What a pass shows | Linux cloud CI? | Evidence |
|---|---|---|---|
| Guard behavior, 3.12 and 3.13 (`test_guard_runtime.py`, 9 tests, fresh `python -I` per case) | Denied events raise, local files do not, known gaps stay known | Yes | T12: 20 of 20 on 3.12; the 9 guard tests also pass on 3.13 |
| Windows-only events (`_winapi.CreateFile`, `_winapi.CreateProcess`) | The hook's logic handles them | Partly: simulated with `sys.audit()`. The real events come from `_winapi` and need Windows | One test in the file above |
| Static scan of app source (`test_static_scan.py`) | No forbidden imports, URL or UNC literals, `openUrl`, `QDesktopServices`, `QProcess`, `subprocess`, `os.startfile` | Yes | Negative control: source with `import socket`, `QDesktopServices` and a URL fails 4 tests (T12) |
| Lockfile checks (same file) | Every pin has a hash, no VCS or URL lines, no forbidden distribution, and the set of pins equals the approved set exactly | Yes | Negative control: a lock with one extra package fails 2 tests (T12) |
| Lock resolves for Windows | Every pin has a `win_amd64` / `cp312` wheel whose hash is in the lock | Yes (`pip download --platform ...`) | T13: all 11 wheels downloaded under `--require-hashes` |
| Runtime import graph (`test_import_graph.py`) | Importing the app's real import graph loads no network module | Yes, with `QT_QPA_PLATFORM=offscreen`; a bare CI image may lack system graphics libraries (**Unconfirmed**, it worked in my sandbox) | T8: 832 modules, none forbidden. It runs the Linux wheels, so the Windows-only code paths in `PySide6/__init__.py` and the `win32` branches of libraries are not exercised |
| Bundle tests (`test_bundle.py`): PYZ and COLLECT tables, output-folder walk, model-file suffixes, warn file | The shipped folder contains none of the forbidden modules or files | Yes on a Linux build; the real check needs a **Windows build** | T9, T12: hardened build passes; default build fails 2 of 5 (negative control) |
| PE import scan of a Windows output folder (`pe_net_imports.py`, run inside `test_bundle.py`) | Only allowlisted binaries import `ws2_32`, `winhttp`, `iphlpapi` and friends | Yes, if a Windows-built folder is available (it reads files with `pefile`, no Windows needed). Passes trivially on a Linux folder | T11, T12: a raw simulated Windows tree fails (`Qt6Network.dll`, `_socket.pyd`, `_ssl.pyd`, `_overlapped.pyd`, `_multiprocessing.pyd`, ...); the tree with those deleted passes. This is a simulation by deletion, not real PyInstaller output |
| PE scan of the pinned Windows wheels (dependency-bump alarm) | A new pin did not add a network-importing binary | Yes (same scanner on the wheels downloaded above) | Done by hand in T11; not wired into the test suite |
| Firewall control and treatment probe | The rule really blocks a program | **Needs Windows**, admin rights, and a non-loopback target | Not run. Sketch in 7.3 |
| Installer creates and removes the rules | The `.iss` lines work on a real machine | **Needs Windows** (Inno compiler, admin) | Not run |
| Geosupport DLL import table and `ctypes` allowlist | The allowlist matches the real install; the DLL's imports are known | **Needs Windows** and the Geosupport Desktop Edition install | Not run |
| App runs with no network at all | Nothing in the normal workflow needs a network | **Needs Windows**: Windows Sandbox with `<Networking>Disable</Networking>` ([wsb options](https://learn.microsoft.com/en-us/windows/security/application-security/application-isolation/windows-sandbox/windows-sandbox-configure-using-wsb-file)) | Not run. Shows independence from the network, not inability to use one |

PyInstaller output is specific to the OS and Python it ran on: "to prepare a distribution for a different OS ... you run PyInstaller on that OS" ([operating mode](https://pyinstaller.org/en/stable/operating-mode.html), text in [doc/operating-mode.rst](https://github.com/pyinstaller/pyinstaller/blob/v6.22.3/doc/operating-mode.rst)). So a Linux build can test the spec's logic but cannot stand in for the Windows build. The practical pipeline is: build on a Windows runner, upload the folder as a CI artifact, and run the same pytest files against it (on Windows, or on Linux for the file-reading tests).

### 7.2 Things that look like tests but prove less than they seem

- **An audit-hook test proves the hook, not the app.** The hook only fires on events Python raises. All C and C++ code is invisible to it (1.3). The guard tests are evidence for the Python layer only.
- **A Linux bundle test says nothing about Windows-only files.** `Qt6Network.dll` is forbidden only on Windows, because on Linux the PySide6 extension modules link `libQt6Network` (3.2). Conversely a Windows build adds files no Linux test can see.
- **A PE import scan shows capability, not use.** `python312.dll`, `select.pyd` and `Qt6Core.dll` import `ws2_32.dll` in every working build (T11, T14), so "no binary imports winsock" is unreachable. The test uses an allowlist of the five binaries I measured (the list in `offline_rules.py`), and any new entry has to be argued for in review. I measured `python312.dll` and `select.pyd` on the conda-forge Windows build of CPython 3.12.16, not on the python.org installer, because python.org and NuGet were blocked from my sandbox (T14). Re-measure on the real interpreter.
- **A loopback probe can pass for the wrong reason.** I have not confirmed whether Windows Firewall filters loopback traffic (**Unconfirmed**), so the firewall probe must use a non-loopback address and must include a control that connects successfully before the rule exists.
- **Network-free behavior is not network-incapable behavior.** Windows Sandbox with networking disabled shows the app works offline. It does not show it could not go online.

### 7.3 Firewall probe (sketch, not run)

The probe needs its own small executable, built without the audit guard, so that the only thing standing between it and the network is the firewall rule. It must be a separate path from `Crosswalk.exe`, since rules bind to a program path. The test uses exactly the `netsh` line from the installer, with `{app}` replaced, so the installer text is what gets tested.

```python
# tests_windows/test_firewall_probe.py   SKETCH: written against the Microsoft docs, never run on Windows
import socket, subprocess, sys, pathlib, pytest
pytestmark = pytest.mark.skipif(sys.platform != "win32", reason="Windows only")

PROBE = '''
import socket, sys
s = socket.socket(); s.settimeout(3)
try:
    s.connect((sys.argv[1], int(sys.argv[2]))); print("CONNECTED")
except OSError as e:
    print("BLOCKED_OR_FAILED", e.errno)
'''
RULE = "Crosswalk probe (out)"

def run_probe(exe, host, port):
    p = subprocess.run([str(exe), host, str(port)], capture_output=True, text=True, timeout=30)
    return p.stdout.strip()

def test_outbound_block_rule_blocks_only_the_ruled_program(tmp_path):
    probe_src = tmp_path / "probe.py"; probe_src.write_text(PROBE)
    subprocess.run([sys.executable, "-m", "PyInstaller", "--onefile", "--distpath", str(tmp_path / "dist"),
                    "--workpath", str(tmp_path / "work"), "--specpath", str(tmp_path), str(probe_src)], check=True)
    exe = tmp_path / "dist" / "probe.exe"
    # a listener on a NON-loopback address of this machine, in the pytest process (which has no rule)
    host = socket.gethostbyname(socket.gethostname())
    srv = socket.socket(); srv.bind((host, 0)); srv.listen(5); port = srv.getsockname()[1]
    netsh = r"C:\Windows\System32\netsh.exe"
    try:
        # CONTROL: without the rule the probe must connect, otherwise the test says nothing
        assert run_probe(exe, host, port) == "CONNECTED", "control failed: environment cannot connect, result would be vacuous"
        subprocess.run([netsh, "advfirewall", "firewall", "add", "rule", f"name={RULE}", "dir=out", "action=block",
                        f"program={exe}", "enable=yes", "profile=any"], check=True)          # same flags as the .iss
        assert run_probe(exe, host, port).startswith("BLOCKED_OR_FAILED")                   # TREATMENT
    finally:
        subprocess.run([netsh, "advfirewall", "firewall", "delete", "rule", f"name={RULE}"])
        srv.close()
```

Open questions this sketch cannot answer without a Windows run: whether a connection from the machine to its own non-loopback address is evaluated as outbound traffic of `probe.exe` (**Unconfirmed**), whether a blocked `connect()` fails immediately or times out (**Unconfirmed**; the 3 second timeout accepts either), and whether the hosted runner is elevated and allows firewall changes. GitHub's runner overview page says only that Windows runners are Azure virtual machines and is silent on administrator rights and firewall state ([about GitHub-hosted runners](https://docs.github.com/en/actions/using-github-hosted-runners/using-github-hosted-runners/about-github-hosted-runners)), so a self-hosted Windows VM may be needed (**Unconfirmed**).

A second Windows test, after a silent install (`Crosswalk-Setup.exe /VERYSILENT /SUPPRESSMSGBOXES /NORESTART /LOG /DIR=...`, parameters from the [setup command line page](https://jrsoftware.org/ishelp/topic_setupcmdline.htm)), lists the rules with `Get-NetFirewallRule -DisplayName 'Crosswalk offline*'` and pipes them to `Get-NetFirewallApplicationFilter` to compare the program path with the installed `Crosswalk.exe`; after uninstall the list must be empty. Whether the `netsh` `name=` value is what PowerShell reports as `DisplayName` is **Unconfirmed**.

---

## 8. Lockfile: no AI SDKs, no model files, nothing unreviewed

### 8.1 What pip guarantees, and what I tested

- Hash-checking mode "is an all-or-nothing proposition. Specifying `--hash` against _any_ requirement will activate this mode globally." In it, "Hashes are required for _all_ requirements", "Hashes are required for _all_ dependencies. If there is a dependency that is not spelled out and hashed in the requirements file, it will result in an error", and "Requirements must be pinned". `--require-hashes` forces the mode. ([pip secure installs](https://github.com/pypa/pip/blob/main/docs/html/topics/secure-installs.md), the documentation source; the pip.pypa.io page itself returned an access error.)
- The same page recommends `--only-binary :all:` ("Disallow source distributions") and, for installing your own project, `--no-deps`. `pip install --help` (pip 26.2.2) defines `--only-binary=:all:` as "Do not use source packages".
- pip 26.2 added `--no-require-hashes`, which "Hashes are then verified only for requirements where they are provided" (same page). **Contradiction of the "all-or-nothing" rule:** with that flag the mode is no longer all-or-nothing. Always pass `--require-hashes` explicitly and never `--no-require-hashes` in the install script.
- **Tested (T13, pip 26.2.2):** a wrong hash fails with "THESE PACKAGES DO NOT MATCH THE HASHES"; a transitive dependency missing from the lock fails with "In --require-hashes mode, all requirements must have their versions pinned with ==" (for a package that was only a dependency); a pinned requirement with no hash fails with "Hashes are required in --require-hashes mode"; a **range requirement with a valid hash (`six>=1.0 --hash=...`) was accepted**, although the page says "Requirements must be pinned". So pip alone does not enforce the pinning rule; the lockfile test in 8.3 does.
- `pip-compile --generate-hashes` emits the hashed file; pip-tools notes that "As the resulting `requirements.txt` can differ for each environment, users must execute `pip-compile` **on each Python environment separately**" ([pip-tools README](https://github.com/jazzband/pip-tools/blob/main/README.md)). So compile on the Windows build machine (Python 3.12, same as the target) and review the diff against the Linux-compiled file I produced.

### 8.2 What the lock contains

**Tested (T13).** Input `requirements.in`: `pandas`, `numpy`, `openpyxl`, `lxml>=6.1.3`, `python-geosupport`, `PySide6-Essentials`. `pip-compile --allow-unsafe --generate-hashes --strip-extras` (pip-tools 7.6.2, Python 3.12) produced 11 pins with 322 hashes: et-xmlfile 2.0.0, lxml 6.1.3, numpy 2.5.4, openpyxl 3.1.5, pandas 3.1.0, pyside6-essentials 6.12.0, python-dateutil 3.0.0, python-geosupport 1.1.0, shiboken6 6.12.0, six 1.17.0, tzdata 2026.6.

- **Use `PySide6-Essentials`, not `PySide6`.** The `PySide6` meta-package's `Requires-Dist` lists `PySide6_Essentials`, `PySide6_Addons`, `PySide6_WebEngine==6.12.0.140` and `PySide6_Pdf==6.12.0.140` ([PyPI metadata](https://pypi.org/pypi/PySide6/6.12.0/json), outside the named domains; no primary Qt page states the split). Addons carries QtWebEngine, QtWebSockets, QtHttpServer and more. The Essentials wheel still ships `QtNetwork`, `QtQml`, `QtQuick`, `QtSql` and `QtDBus` (T11), which the spec excludes.
- **Cross-platform check.** `pip download --platform win_amd64 --python-version 3.12 --implementation cp --abi cp312 --only-binary=:all: --require-hashes -r requirements.txt -d wheels-win` fetched all 11 wheels with no hash error, so the hashes in the Linux-compiled file cover the Windows wheels (T13). This does not replace compiling on Windows.
- **The lock does not cover build tools.** PyInstaller, `pefile`, `pytest` and `pip-tools` need their own hashed `requirements-build.txt`, installed the same way. They are not shipped, but they run on the build machine and write the files that are shipped.

### 8.3 Tests that keep AI and network packages out

- `test_lockfile_is_hashed_pinned_and_clean`: every pin has at least one `--hash=sha256:`; no `-e`, `git+`, URL or `file:` lines; none of the `FORBIDDEN_DISTS` names (network clients, cloud SDKs, AI SDKs, ML runtimes, `pyside6-addons`).
- `test_lockfile_pins_exactly_the_approved_distributions`: the **allowlist** is the real control. The deny list only gives a clearer message. A new package, even an innocent one, fails the test until a reviewer edits `APPROVED_DISTS` in the same change.
- `test_no_model_or_pickle_files_in_output_folder`: no `.onnx`, `.gguf`, `.ggml`, `.safetensors`, `.pt`, `.pth`, `.h5`, `.tflite`, `.pb`, `.mlmodel`, `.llamafile`, `.keras`, `.joblib`, `.pkl`, `.pickle` in the shipped folder (the suffix list is a heuristic, **Inference**: a model can be renamed, so the allowlisted lock and the PE and import checks matter more).
- Build gate in the spec and `test_no_forbidden_python_modules_in_pyz_or_extensions`: no AI SDK module in the PYZ or as an extension.
- Runtime: the guard refuses to import the same names (`openai`, `anthropic`, `transformers`, `torch`, `onnxruntime`, `ollama`, `litellm`, ...) and everything network-capable. Three independent places hold the lists (spec, guard, rules). That duplication is deliberate; keep it in step by review.

### 8.4 What a lockfile cannot show

It pins what upstream published. It does not review that code. For this stack the packages with real exposure are the compiled ones: numpy, pandas, lxml and PySide6 wheels (checked for network-importing binaries in T11) and `python-geosupport`, a small pure-Python package that I read (about five modules, T8, 4.5). A malicious or compromised release that you pin knowingly is outside what hashes detect. The PE scan, the import-graph test, the firewall and the guard each narrow that, none removes it.

---

## Recommended design

Layers are installed in the order below. Each Python block below is the file I ran, embedded unedited. Only the Inno Setup and Windows probe snippets were not run.

### R1. What goes where

| Path in the repo | Purpose |
|---|---|
| `crosswalk/offline_guard.py` | The fail-closed audit hook (R2) |
| `build/rthook_offline.py` | PyInstaller runtime hook that installs the guard before the app code (R3) |
| `crosswalk.spec` | Excludes, TOC filtering, build gate (R4) |
| `installer/crosswalk.iss` | Firewall rules at install and uninstall (R5) |
| `tools/offline_rules.py`, `tools/pe_net_imports.py` | Single source of truth for "offline" and the PE scanner (R6) |
| `tests/` | The evidence (R6) |
| `requirements.in`, `requirements.txt` | Hashed lock (section 8) |

For development runs from source (no PyInstaller), call `offline_guard.install(...)` as the first statement of `crosswalk/__main__.py` as well. The runtime hook covers frozen builds only. Create the application object as `QApplication([sys.argv[0]])`, so no Qt switch (`-plugin`, `-qmljsdebugger`) can arrive from a command line (3.3).

### R2. The audit hook

Design choices, each tied to a finding above:

- It is an allowlist for `ctypes` (the docs say `ctypes` "should be completely removed or closely monitored") and a deny list for network events (1.2, 1.3).
- Denied imports raise `OfflineImportViolation`, an `ImportError` subclass, so `try: import x / except ImportError:` probes degrade (3.1).
- Sub-interpreter modules are unimportable and set to `None` in `sys.modules` (1.3).
- UNC and WebDAV paths are denied at the `open` event (and at `_winapi.CreateFile` on Windows). Mapped drive letters still pass (1.3).
- `install()` returns the list of violations and accepts a `log` callback, so a Windows smoke run can print every denial.

**`crosswalk/offline_guard.py`**

```python
"""offline_guard: fail-closed audit hook. Import and call install() as the first statement of the app.

Defense in depth, NOT a sandbox (see docs.python.org/3/library/sys.html#sys.addaudithook).
"""
import sys

class OfflineViolation(Exception):
    """Raised before a forbidden operation happens. The operation itself is aborted whether or not callers swallow this."""

class OfflineImportViolation(OfflineViolation, ImportError):
    """A denied import. It is an ImportError so that optional-import probes (try: import x / except ImportError) fall back instead of crashing,
    for example PySide6/__init__.py on Windows, which imports QtNetwork inside try/except ImportError when a PySide6/openssl folder exists."""

def install(allowed_dll_prefixes=(), allowed_symbols=(), log=None, ntpath_mod=None):
    import ntpath as _ntpath, os as _os
    nt = ntpath_mod or _ntpath
    violations = []
    deny_prefixes = ("socket.", "urllib.", "http.client.", "ftplib.", "smtplib.", "poplib.", "imaplib.", "telnetlib.", "webbrowser.")
    deny_exact = frozenset({
        "subprocess.Popen", "os.system", "os.exec", "os.spawn", "os.posix_spawn", "os.fork", "os.forkpty",
        "os.startfile", "os.startfile/2", "winreg.ConnectRegistry",
        "gc.get_objects", "gc.get_referrers", "gc.get_referents",
        "ctypes.addressof", "ctypes.string_at", "ctypes.wstring_at", "ctypes.cdata", "ctypes.cdata/buffer",
        "ctypes.set_exception", "ctypes.call_function",
        "_winapi.CreateProcess",     # Windows-only event behind subprocess; listed in the CPython audit-events table; not exercised on Linux
    })
    deny_modules = frozenset({
        # network-capable stdlib, first import only (the "import" event is not raised for modules already in sys.modules)
        "socket", "_socket", "ssl", "_ssl", "http", "http.client", "http.server", "http.cookiejar", "urllib.request",
        "ftplib", "smtplib", "poplib", "imaplib", "telnetlib", "xmlrpc", "xmlrpc.client", "xmlrpc.server",
        "socketserver", "webbrowser", "asyncio", "_overlapped",     # _overlapped: Windows overlapped/IOCP sockets, a .pyd in python.org builds
        # sub-interpreters do not inherit hooks added with sys.addaudithook
        "_xxsubinterpreters", "_interpreters", "_interpchannels", "_interpqueues", "_xxinterpchannels", "_xxinterpqueues",
        "interpreters", "concurrent.interpreters",
        # third-party clients and AI SDKs
        "requests", "urllib3", "httpx", "aiohttp", "websockets", "websocket", "fsspec", "boto3", "botocore",
        "openai", "anthropic", "google.generativeai", "google.genai", "cohere", "mistralai", "langchain", "llama_index",
        "transformers", "torch", "tensorflow", "onnxruntime", "huggingface_hub", "ollama", "litellm", "PySide6.QtNetwork",
        "PySide6.QtWebEngineCore", "PySide6.QtWebEngineWidgets", "PySide6.QtWebSockets", "PySide6.QtWebChannel",
    })
    # 3.13 builds these sub-interpreter modules into the interpreter. A builtin module is found without an "import" event when it is loaded
    # through importlib.import_module(), so also make them unimportable. (A None entry in sys.modules makes every later import raise ImportError.)
    for _m in ("_xxsubinterpreters", "_interpreters", "_interpchannels", "_interpqueues", "_xxinterpchannels", "_xxinterpqueues"):
        sys.modules.setdefault(_m, None)
    dll_prefixes = tuple(nt.normcase(nt.abspath(p)) for p in allowed_dll_prefixes)
    symbols = frozenset(allowed_symbols)

    def is_remote_path(p):
        if isinstance(p, bytes):
            p = _os.fsdecode(p)
        if not isinstance(p, str):
            return False
        s = p.replace("/", "\\")
        low = s.lower()
        if "@ssl" in low or "davwwwroot" in low:        # WebDAV over HTTP(S) through the Windows WebClient service
            return True
        if low.startswith("\\\\?\\unc\\"):
            return True
        if low.startswith("\\\\?\\") or low.startswith("\\\\.\\"):
            return False
        return low.startswith("\\\\")                   # \\server\share

    def deny(why, exc=OfflineViolation):
        violations.append(why)
        if log is not None:
            log(why)
        raise exc(why)

    def hook(event, args):
        if event == "import":
            name = args[0]
            if name in deny_modules or name.split(".", 1)[0] in deny_modules:
                deny(f"import of {name}", OfflineImportViolation)
            return
        if event == "open" or event == "_winapi.CreateFile":     # CreateFile: Windows-only, same first argument (a path)
            if is_remote_path(args[0]):
                deny(f"{event} of network path {args[0]!r}")
            return
        if event.startswith(deny_prefixes) or event in deny_exact:
            deny(event)
        if event == "ctypes.dlopen":
            name = args[0]
            if name is None:
                return      # POSIX only: `import ctypes` opens the main program as ctypes.pythonapi. Its symbols stay gated by the dlsym allowlist.
            if not dll_prefixes or not isinstance(name, str) or not nt.normcase(nt.abspath(name)).startswith(dll_prefixes):
                deny(f"ctypes.dlopen {name!r}")
        elif event in ("ctypes.dlsym", "ctypes.dlsym/handle"):
            if args[1] not in symbols:
                deny(f"ctypes.dlsym {args[1]!r}")

    sys.addaudithook(hook)
    return violations
```

### R3. Runtime hook

PyInstaller runs a runtime hook "before any other code or module" (2.1). The guard directory for Geosupport is the one place that must be tuned on Windows (4.5): pass the real install directory, and pass `geosupport_path` explicitly to `python-geosupport` so the DLL is never found by a `PATH` search.

**`build/rthook_offline.py`**

```python
# PyInstaller runtime hook: runs before the entry script (pyinstaller.org/en/stable/hooks.html#changing-runtime-behavior)
import sys, os
import offline_guard
_install_dir = os.path.dirname(os.path.abspath(sys.executable))
offline_guard.install(
    allowed_dll_prefixes=[os.path.join(_install_dir, "geosupport")],   # tuned on the real Windows build
    allowed_symbols=["NYCgeo", "geo"],
)
```

### R4. PyInstaller spec

This is the file I built with (Linux, PyInstaller 6.22.3). Before using it for the product: change `name=` to `Crosswalk`, set `console=False` for a windowed app, and replace the entry script. The `win32` branches have not run.

**`crosswalk.spec`**

```python
# -*- mode: python ; coding: utf-8 -*-
# Offline-hardened one-folder build. Run:  pyinstaller --noconfirm --clean crosswalk.spec
import re, sys
from PyInstaller.utils.hooks import collect_data_files

# 1) Python modules that are removed from the import graph (Analysis `excludes`: "ignored (as though they were not found)").
NETWORK_STDLIB = [
    "socket", "_socket", "ssl", "_ssl", "http", "http.client", "http.server", "http.cookies", "http.cookiejar",
    "urllib.request", "urllib.response", "urllib.error", "urllib.robotparser",
    "ftplib", "smtplib", "poplib", "imaplib", "telnetlib", "nntplib", "smtpd",
    "xmlrpc", "xmlrpc.client", "xmlrpc.server", "socketserver", "webbrowser",
    "asyncio", "_asyncio", "_overlapped", "multiprocessing", "_multiprocessing", "concurrent.futures.process",
]
SUBINTERPRETERS = ["_xxsubinterpreters", "_interpreters", "_interpchannels", "_interpqueues", "_xxinterpchannels", "_xxinterpqueues"]
DEV_ONLY = ["unittest", "doctest", "pydoc", "pdb", "test", "tkinter", "_tkinter", "distutils", "setuptools", "pkg_resources", "pip",
            "wheel", "pytest", "_pytest", "IPython", "numpy.testing"]
THIRD_PARTY_NETWORK_AND_AI = [
    "requests", "urllib3", "httpx", "aiohttp", "websockets", "fsspec", "boto3", "botocore", "certifi",
    "openai", "anthropic", "google.generativeai", "google.genai", "cohere", "mistralai", "langchain", "llama_index",
    "transformers", "torch", "tensorflow", "onnxruntime", "huggingface_hub", "ollama", "litellm",
]
QT_EXCLUDED_MODULES = [
    "PySide6.QtNetwork", "PySide6.QtWebEngineCore", "PySide6.QtWebEngineWidgets", "PySide6.QtWebEngineQuick", "PySide6.QtWebSockets",
    "PySide6.QtWebChannel", "PySide6.QtWebView", "PySide6.QtPositioning", "PySide6.QtLocation", "PySide6.QtQml", "PySide6.QtQuick",
    "PySide6.QtQuickWidgets", "PySide6.QtQuick3D", "PySide6.QtHttpServer", "PySide6.QtNetworkAuth", "PySide6.QtRemoteObjects",
    "PySide6.QtBluetooth", "PySide6.QtNfc", "PySide6.QtSql", "PySide6.QtMultimedia", "PySide6.QtMultimediaWidgets", "PySide6.QtDBus",
]
EXCLUDES = NETWORK_STDLIB + SUBINTERPRETERS + DEV_ONLY + THIRD_PARTY_NETWORK_AND_AI + QT_EXCLUDED_MODULES

# 2) Files that must not be in the folder even if a hook collected them as a dependency of something else.
#    (Analysis.binaries / Analysis.datas are plain lists of (dest_name, src_name, typecode): pyinstaller.org/en/stable/advanced-topics.html)
QT_DROP = [
    r"(^|/)plugins/(tls|networkinformation|networkaccess|bearer|generic|qmltooling|sqldrivers|designer|vectorimageformats|platforminputcontexts)/",
    r"(^|/)(lib)?Qt6(WebEngine\w*|WebSockets|WebChannel|Positioning|Location|HttpServer|NetworkAuth|RemoteObjects)\b",
]
if sys.platform == "win32":
    # On Windows the PySide6 wheel's QtCore/QtGui/QtWidgets do not import Qt6Network.dll; on Linux they do, so the app would not start without it.
    QT_DROP += [r"(^|/)Qt6Network\.dll$", r"(^|/)Qt6Qml\w*\.dll$", r"(^|/)Qt6Quick\w*\.dll$"]
def drop(toc, patterns):
    return [e for e in toc if not any(re.search(p, e[0].replace("\\", "/")) for p in patterns)]

a = Analysis(
    ["app/main.py"],
    pathex=["app"],
    hiddenimports=["offline_guard", "secrets", "hmac"],   # secrets/hmac: imported by numpy's compiled random module, invisible to static analysis
    datas=collect_data_files("geosupport"),                  # python-geosupport reads its CSV tables at import time
    runtime_hooks=["app/rthook_offline.py"],     # runs before the entry script (pyinstaller.org/en/stable/usage.html#cmdoption-runtime-hook)
    excludes=EXCLUDES,
    noarchive=False,
)
a.binaries = drop(a.binaries, QT_DROP)
a.datas = drop(a.datas, QT_DROP)
if sys.platform == "win32":
    # libcrypto stays if _hashlib needs it; _ssl.pyd and libssl are not collected once `ssl` is excluded. Review COLLECT-00.toc.
    a.binaries = drop(a.binaries, [r"(^|/)_ssl\.", r"(^|/)libssl"])

# 3) Build gate: fail the build, not the audit, if anything forbidden slipped into the TOC lists.
LEAK_MODULES = set(NETWORK_STDLIB + SUBINTERPRETERS + THIRD_PARTY_NETWORK_AND_AI + QT_EXCLUDED_MODULES)
leaked = sorted({n for n, _src, _t in a.pure if n in LEAK_MODULES})
leaked += sorted({d for d, _src, _t in a.binaries + a.datas if re.search(r"(^|/)(_socket|_ssl|_asyncio|_xxsubinterpreters|_interpreters)[.]", d.replace("\\", "/"))})
if leaked:
    raise SystemExit("OFFLINE GATE FAILED, forbidden entries in the build: " + ", ".join(leaked))
pyz = PYZ(a.pure)
exe = EXE(pyz, a.scripts, [], exclude_binaries=True, name="demo_hardened", console=True, upx=False)
coll = COLLECT(exe, a.binaries, a.datas, strip=False, upx=False, name="demo_hardened")
```

Notes:

- `multiprocessing` is excluded because PyInstaller's own runtime hook imports it and, with the guard first, that import pulled in `socket` and crashed the first unhardened build (2.2).
- `hiddenimports=["secrets", "hmac"]` is needed because numpy's compiled random module imports them (2.1). Expect to find more such cases when the first Windows build runs; the frozen smoke test finds them.
- `email` is deliberately not excluded (2.2).
- Production builds should also sign the exe and installer. That is outside this research (**Unconfirmed**: I did not research code signing or what it does for the firewall rule or App Control).

### R5. Inno Setup: firewall rules

Not compiled, not run. Built from the Inno pages cited in 5.3 and the netsh examples in 5.2. Everything marked "Unconfirmed" in 5.3 applies.

```ini
[Setup]
AppName=Crosswalk
AppVersion=1.0.0
DefaultDirName={autopf}\Crosswalk
PrivilegesRequired=admin
; 64-bit install mode matters for {autopf} and {sys}. The accepted value name (x64compatible on newer Inno Setup, x64 on older) is Unconfirmed: the page returned an access error.
ArchitecturesAllowed=x64compatible
ArchitecturesInstallIn64BitMode=x64compatible

[Files]
Source: "dist\Crosswalk\*"; DestDir: "{app}"; Flags: recursesubdirs ignoreversion

[Run]
; Remove leftovers from an earlier install first (a missing rule makes this fail harmlessly), then add both directions.
Filename: "{sys}\netsh.exe"; Parameters: "advfirewall firewall delete rule name=""Crosswalk offline (out)"""; Flags: runhidden waituntilterminated
Filename: "{sys}\netsh.exe"; Parameters: "advfirewall firewall delete rule name=""Crosswalk offline (in)"""; Flags: runhidden waituntilterminated
Filename: "{sys}\netsh.exe"; Parameters: "advfirewall firewall add rule name=""Crosswalk offline (out)"" dir=out action=block program=""{app}\Crosswalk.exe"" enable=yes profile=any"; Flags: runhidden waituntilterminated
Filename: "{sys}\netsh.exe"; Parameters: "advfirewall firewall add rule name=""Crosswalk offline (in)"" dir=in action=block program=""{app}\Crosswalk.exe"" enable=yes profile=any"; Flags: runhidden waituntilterminated

[UninstallRun]
; Delete by name, not by program, so the order relative to file removal does not matter.
Filename: "{sys}\netsh.exe"; Parameters: "advfirewall firewall delete rule name=""Crosswalk offline (out)"""; Flags: runhidden; RunOnceId: "DelFwOut"
Filename: "{sys}\netsh.exe"; Parameters: "advfirewall firewall delete rule name=""Crosswalk offline (in)"""; Flags: runhidden; RunOnceId: "DelFwIn"
```

Notes: `profile=any` is my expectation for "all profiles" in `netsh` and is **Unconfirmed** on the pages I read (the PowerShell `-Profile` default of `Any` is confirmed, 5.2). `dir=out action=block program=... enable=yes` and `delete rule name=...` follow Microsoft's examples. The PowerShell equivalent for IT teams is `New-NetFirewallRule -DisplayName 'Crosswalk offline (out)' -Direction Outbound -Action Block -Program 'C:\Program Files\Crosswalk\Crosswalk.exe' -Profile Any -Enabled True`, and `Remove-NetFirewallRule -DisplayName ...` to remove it.

### R6. Rules, scanner and tests

`offline_rules.py` holds every list the tests use, so "offline" is defined once.

**`tools/offline_rules.py`**

```python
"""Single source of truth for what 'offline' means. Imported by the tests and by CI scripts."""
import re

FORBIDDEN_MODULES = frozenset({
    # network-capable stdlib
    "socket", "_socket", "ssl", "_ssl", "http.client", "http.server", "http.cookiejar", "urllib.request",
    "ftplib", "smtplib", "poplib", "imaplib", "telnetlib", "xmlrpc.client", "xmlrpc.server", "socketserver",
    "webbrowser", "asyncio", "_overlapped", "multiprocessing", "_multiprocessing",
    # sub-interpreters (audit hooks added with sys.addaudithook do not apply inside them)
    "_xxsubinterpreters", "_interpreters", "_interpchannels", "_interpqueues",
    # third-party network clients and AI SDKs
    "requests", "urllib3", "httpx", "aiohttp", "websockets", "fsspec", "boto3", "botocore",
    "openai", "anthropic", "google.generativeai", "google.genai", "cohere", "mistralai", "langchain", "llama_index",
    "transformers", "torch", "tensorflow", "onnxruntime", "huggingface_hub", "ollama", "litellm",
    # Qt modules that can reach a network
    "PySide6.QtNetwork", "PySide6.QtWebEngineCore", "PySide6.QtWebEngineWidgets", "PySide6.QtWebEngineQuick",
    "PySide6.QtWebSockets", "PySide6.QtWebChannel", "PySide6.QtPositioning", "PySide6.QtHttpServer", "PySide6.QtNetworkAuth",
})

# Distribution names (PEP 503 normalized: lowercase, runs of -_. collapsed to -)
FORBIDDEN_DISTS = frozenset({
    "requests", "urllib3", "httpx", "httpcore", "h11", "aiohttp", "websockets", "websocket-client", "fsspec", "s3fs", "gcsfs", "boto3", "botocore",
    "openai", "anthropic", "google-generativeai", "google-genai", "google-ai-generativelanguage", "cohere", "mistralai", "langchain", "langchain-core",
    "llama-index", "transformers", "tokenizers", "torch", "tensorflow", "keras", "jax", "onnxruntime", "huggingface-hub", "sentence-transformers",
    "ollama", "litellm", "tiktoken", "pyside6-addons", "pyqt6-webengine", "pyqtwebengine",
})

# The allowlist is the real control; FORBIDDEN_DISTS only gives a clearer message for names we know about.
# Adding any package to the lock means editing this set in the same reviewed change.
APPROVED_DISTS = frozenset({
    "et-xmlfile", "lxml", "numpy", "openpyxl", "pandas", "pyside6-essentials", "python-dateutil", "python-geosupport", "shiboken6", "six", "tzdata",
})

FORBIDDEN_FILE_NAME_PARTS = (
    "_socket.", "_ssl.", "libssl", "_asyncio.", "_xxsubinterpreters", "_interpreters", "_interpchannels",
    "QtNetwork", "Qt6WebEngine", "QtWebEngine", "Qt6WebSockets", "Qt6WebChannel", "Qt6Positioning",
    "/plugins/tls/", "/plugins/networkinformation/", "/plugins/networkaccess/", "/plugins/bearer/", "/plugins/generic/", "/plugins/qmltooling/",
)
# On Linux the PySide6 extension modules link libQt6Network, so PyInstaller must keep it (PyInstaller's own Qt hook says so).
# On Windows the same wheel's QtCore/QtGui/QtWidgets do not import Qt6Network.dll, so it must be absent.
WINDOWS_ONLY_FORBIDDEN_FILE_NAME_PARTS = ("Qt6Network", "Qt6Qml", "Qt6Quick")
# Windows only: binaries (lower-case base names) that may import a Windows networking DLL (ws2_32, winhttp, wininet, iphlpapi, ...).
# Anything else that does, for example Qt6Network.dll, _socket.pyd, _ssl.pyd or winhttp users, fails the build.
# Measured on the Windows wheels and the conda-forge Windows build of CPython 3.12 (not the python.org installer): python312.dll and select.pyd import ws2_32; Qt6Core.dll imports ws2_32, mpr and netapi32;
# lxml's etree and objectify extensions embed libxml2 and import ws2_32. Add the Geosupport DLL here only after reading its import table.
PE_NETWORK_IMPORT_ALLOWLIST = frozenset({
    "python312.dll", "select.pyd", "qt6core.dll", "etree.cp312-win_amd64.pyd", "objectify.cp312-win_amd64.pyd",
})
MODEL_FILE_SUFFIXES = (".onnx", ".gguf", ".ggml", ".safetensors", ".pt", ".pth", ".h5", ".hdf5", ".tflite", ".pb", ".mlmodel", ".mar", ".llamafile", ".keras", ".joblib", ".pkl", ".pickle")

URL_RE = re.compile(r"(?i)\b(?:https?|ftp|wss?|sftp|s3|gs)://[^\s'\"<>)]+|\\\\[A-Za-z0-9_.-]+\\[A-Za-z0-9_$.-]+")
URL_ALLOW_PREFIXES = (  # XML namespaces and license identifiers are identifiers, not endpoints
    "http://schemas.openxmlformats.org/", "http://schemas.microsoft.com/", "http://www.w3.org/", "http://purl.org/", "http://www.xml.org/",
)
PIP_REQ_RE = re.compile(r"^([A-Za-z0-9][A-Za-z0-9._-]*)==", re.M)

def normalize_dist(name: str) -> str:
    return re.sub(r"[-_.]+", "-", name).lower()
```

The PE scanner reads import tables with `pefile`, so it runs on Linux against a Windows output folder:

**`tools/pe_net_imports.py`**

```python
"""List binaries (.dll/.pyd/.exe) that import Windows networking DLLs. Pure Python (pefile), runs on Linux against a Windows dist folder."""
import pathlib, sys
import pefile

NET_DLLS = {"ws2_32.dll", "wsock32.dll", "mswsock.dll", "winhttp.dll", "wininet.dll", "urlmon.dll", "iphlpapi.dll", "dnsapi.dll",
            "netapi32.dll", "mpr.dll", "wldap32.dll", "httpapi.dll", "webservices.dll", "rasapi32.dll", "wlanapi.dll", "nlaapi.dll"}

def imported_dlls(path):
    pe = pefile.PE(str(path), fast_load=True)
    pe.parse_data_directories(directories=[pefile.DIRECTORY_ENTRY["IMAGE_DIRECTORY_ENTRY_IMPORT"],
                                           pefile.DIRECTORY_ENTRY["IMAGE_DIRECTORY_ENTRY_DELAY_IMPORT"]])
    names = {e.dll.decode("ascii", "replace").lower() for a in ("DIRECTORY_ENTRY_IMPORT", "DIRECTORY_ENTRY_DELAY_IMPORT") for e in getattr(pe, a, [])}
    pe.close()
    return names

def scan(root):
    out = {}
    for p in sorted(pathlib.Path(root).rglob("*")):
        if p.suffix.lower() in (".dll", ".pyd", ".exe"):
            try:
                hit = imported_dlls(p) & NET_DLLS
            except pefile.PEFormatError:
                continue
            if hit:
                out[p.relative_to(root).as_posix()] = sorted(hit)
    return out

if __name__ == "__main__":
    for f, d in scan(sys.argv[1]).items():
        print(f"{f}: {d}")
```

Test configuration and the app import list used by the import-graph test:

**`tests/conftest.py`**

```python
import os, pathlib, sys
ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))
DIST = pathlib.Path(os.environ.get("CROSSWALK_DIST", ROOT / "dist" / "Crosswalk"))      # PyInstaller one-folder output
BUILD = pathlib.Path(os.environ.get("CROSSWALK_BUILD", ROOT / "build" / "crosswalk"))    # holds PYZ-00.toc, COLLECT-00.toc, warn-*.txt, xref-*.html
LOCK = pathlib.Path(os.environ.get("CROSSWALK_LOCK", ROOT / "requirements.txt"))
```

**`crosswalk/app_imports.py`**

```python
"""Imports the whole app import graph without starting the UI. Used by tests/test_import_graph.py."""
import os
os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
import numpy, pandas, openpyxl                      # noqa: E401,F401
from lxml import etree                             # noqa: F401
from PySide6 import QtCore, QtGui, QtWidgets       # noqa: F401
import geosupport                                  # noqa: F401
```

Guard behavior (each case in a fresh interpreter, because hooks cannot be removed):

**`tests/test_guard_runtime.py`**

```python
"""Layer: in-process audit hook. Runs in a fresh interpreter because audit hooks cannot be removed."""
import json, subprocess, sys, textwrap, pathlib
ROOT = pathlib.Path(__file__).resolve().parents[1]

def run_guarded(body: str, preload=()) -> dict:
    pre = ''.join(f'import {m}\n' for m in preload)
    code = textwrap.dedent(f"""
        import sys, json
        sys.path.insert(0, {str(ROOT / 'crosswalk')!r})
        import offline_guard
        """) + pre + textwrap.dedent(f"""
        offline_guard.install(allowed_dll_prefixes=['/nonexistent'], allowed_symbols=[])
        V = offline_guard.OfflineViolation
        out = {{}}
        def attempt(name, fn):
            try:
                fn(); out[name] = 'NOT BLOCKED'
            except V as e:
                out[name] = 'blocked'
            except BaseException as e:
                out[name] = 'other:' + type(e).__name__
    """) + textwrap.dedent(body) + "\nprint(json.dumps(out))\n"
    p = subprocess.run([sys.executable, "-I", "-c", code], capture_output=True, text=True, timeout=60)
    assert p.returncode == 0, p.stderr
    return json.loads(p.stdout.strip().splitlines()[-1])

def test_socket_and_dns_events_raise():
    # modules are imported BEFORE the guard so that this test exercises the audit-event layer, not the import-deny layer
    r = run_guarded("""
        attempt('socket.socket', lambda: socket.socket())
        attempt('getaddrinfo', lambda: socket.getaddrinfo('localhost', 80))
        attempt('gethostbyname', lambda: socket.gethostbyname('localhost'))
        attempt('create_connection', lambda: socket.create_connection(('127.0.0.1', 9), timeout=1))
    """, preload=["socket"])
    assert set(r.values()) == {"blocked"}, r

def test_http_ftp_smtp_events_raise_when_already_imported():
    r = run_guarded("""
        import urllib.request, http.client, ftplib, smtplib
        attempt('urlopen', lambda: urllib.request.urlopen('http://127.0.0.1:9/', timeout=1))
        attempt('HTTPConnection.connect', lambda: http.client.HTTPConnection('127.0.0.1', 9, timeout=1).connect())
        attempt('FTP.connect', lambda: ftplib.FTP().connect('127.0.0.1', 9, timeout=1))
        attempt('SMTP.connect', lambda: smtplib.SMTP().connect('127.0.0.1', 9))
    """, preload=["urllib.request", "http.client", "ftplib", "smtplib"])
    assert set(r.values()) == {"blocked"}, r

def test_first_import_of_network_modules_raises():
    r = run_guarded("""
        for name in ('socket', 'ssl', 'http.client', 'urllib.request', 'asyncio', 'webbrowser'):
            attempt('import ' + name, lambda n=name: exec('import ' + n))
    """)
    assert set(r.values()) == {"blocked"}, r

def test_denied_import_is_an_importerror_so_optional_import_probes_degrade():
    r = run_guarded("""
        try:
            import socket
            out['probe'] = 'imported'
        except ImportError:
            out['probe'] = 'fell back'
        out['is_violation'] = issubclass(offline_guard.OfflineImportViolation, offline_guard.OfflineViolation)
    """)
    assert r == {"probe": "fell back", "is_violation": True}, r

def test_subinterpreter_modules_are_unimportable():
    # Hooks added with sys.addaudithook do not run inside sub-interpreters, so creating one is a bypass. On 3.13 the modules are builtin,
    # and importlib.import_module() of a builtin module raises no "import" event, hence the sys.modules[name] = None entries.
    r = run_guarded("""
        import importlib
        for name in ('_xxsubinterpreters', '_interpreters', '_interpchannels', '_interpqueues'):
            attempt('importlib ' + name, lambda n=name: importlib.import_module(n))
            attempt('statement ' + name, lambda n=name: exec('import ' + n))
    """)
    assert "NOT BLOCKED" not in r.values(), r

def test_process_creation_and_introspection_raise():
    r = run_guarded("""
        import subprocess, os, gc
        attempt('subprocess', lambda: subprocess.run(['true']))
        attempt('os.system', lambda: os.system('true'))
        attempt('gc.get_objects', lambda: gc.get_objects())
        attempt('gc.get_referrers', lambda: gc.get_referrers(os))
    """, preload=["subprocess", "gc"])
    assert set(r.values()) == {"blocked"}, r

def test_unc_paths_raise_local_paths_do_not():
    r = run_guarded(r"""
        attempt('unc backslash', lambda: open('\\\\server\\share\\x.csv'))
        attempt('unc slash', lambda: open('//server/share/x.csv'))
        attempt('local', lambda: open(__file__ if '__file__' in globals() else sys.executable, 'rb').close())
    """)
    assert r["unc backslash"] == "blocked" and r["unc slash"] == "blocked" and r["local"] == "NOT BLOCKED", r

def test_windows_only_events_are_denied_when_raised():
    # Simulated with sys.audit(): the real events come from _winapi, which exists only on Windows. This checks the hook's logic, not Windows itself.
    r = run_guarded("""
        bs = chr(92)
        unc = bs * 2 + 'server' + bs + 'share' + bs + 'x.csv'
        dav = bs * 2 + 'host@SSL' + bs + 'DavWWWRoot' + bs + 'x.csv'
        local = 'C:' + bs + 'data' + bs + 'x.csv'
        attempt('CreateFile UNC', lambda: sys.audit('_winapi.CreateFile', unc, 0, 0, 0, 0))
        attempt('CreateFile WebDAV', lambda: sys.audit('_winapi.CreateFile', dav, 0, 0, 0, 0))
        attempt('CreateFile local', lambda: sys.audit('_winapi.CreateFile', local, 0, 0, 0, 0))
        attempt('CreateProcess', lambda: sys.audit('_winapi.CreateProcess', None, 'cmd.exe', None))
    """)
    assert r["CreateFile UNC"] == "blocked" and r["CreateFile WebDAV"] == "blocked" and r["CreateProcess"] == "blocked", r
    assert r["CreateFile local"] == "NOT BLOCKED", r

def test_known_gaps_are_documented_here_so_they_stay_known():
    """A guard that quietly stops covering something is worse than a documented gap. These assert today's behavior."""
    r = run_guarded("""
        import importlib, ctypes
        # 1. importlib.import_module of a builtin/pure module does not raise the 'import' event (statement imports do)
        attempt('import_module(webbrowser)', lambda: importlib.import_module('webbrowser'))   # NOT BLOCKED today
        # 2. ctypes calls on already-resolved function pointers raise no event
        attempt('ctypes.memmove', lambda: ctypes.memmove(ctypes.create_string_buffer(2), b'a', 1))
    """)
    assert r["ctypes.memmove"] == "NOT BLOCKED"
```

Bundle contents (PYZ and COLLECT tables, output-folder walk, PE scan):

**`tests/test_bundle.py`**

```python
"""Layer: build-time exclusion. Reads PyInstaller's own build records and walks the real output folder."""
import ast, pathlib, re, zipfile
import pytest
from conftest import BUILD, DIST
import sys
from offline_rules import (FORBIDDEN_MODULES, FORBIDDEN_FILE_NAME_PARTS, WINDOWS_ONLY_FORBIDDEN_FILE_NAME_PARTS, MODEL_FILE_SUFFIXES,
                           PE_NETWORK_IMPORT_ALLOWLIST)

pytestmark = pytest.mark.skipif(not (BUILD / "PYZ-00.toc").exists(), reason="no PyInstaller build in this environment")

def bundled_modules():
    _, entries = ast.literal_eval((BUILD / "PYZ-00.toc").read_text())
    mods = {e[0] for e in entries}
    with zipfile.ZipFile(BUILD / "base_library.zip") as z:
        for n in z.namelist():
            if n.endswith(".pyc"):
                m = n[:-4].replace("/", ".")
                mods.add(m[:-9] if m.endswith(".__init__") else m)
    coll = ast.literal_eval((BUILD / "COLLECT-00.toc").read_text())
    for e in (coll[0] if isinstance(coll, tuple) else coll):
        if isinstance(e, tuple) and len(e) == 3 and e[2] == "EXTENSION":
            mods.add(e[0].replace("\\", "/").replace("/", ".").split(".cpython")[0].split(".cp3")[0].split(".abi3")[0])
    return mods

def test_no_forbidden_python_modules_in_pyz_or_extensions():
    bad = sorted(m for m in bundled_modules() if m in FORBIDDEN_MODULES)
    assert not bad, bad

def test_no_forbidden_files_in_output_folder():
    files = [p.relative_to(DIST).as_posix() for p in DIST.rglob("*") if p.is_file()]
    parts = FORBIDDEN_FILE_NAME_PARTS + (WINDOWS_ONLY_FORBIDDEN_FILE_NAME_PARTS if sys.platform == "win32" else ())
    bad = sorted(f for f in files if any(part.lower() in ("/" + f).lower() for part in parts))
    assert not bad, bad

def test_no_model_or_pickle_files_in_output_folder():
    bad = sorted(p.name for p in DIST.rglob("*") if p.is_file() and p.suffix.lower() in MODEL_FILE_SUFFIXES)
    assert not bad, bad

def test_pyinstaller_warn_file_records_exclusions():
    warn = (BUILD / next(p.name for p in BUILD.glob("warn-*.txt"))).read_text()
    assert "excluded module named" in warn or "missing module named" in warn   # the file is the audit trail for reviewers

def test_only_allowlisted_binaries_import_windows_networking_dlls():
    """Reads PE import tables, so it runs on Linux against a Windows dist folder. On a Linux dist there are no .dll/.pyd files and it passes trivially."""
    pytest.importorskip("pefile")
    from pe_net_imports import scan
    offenders = {f: dlls for f, dlls in scan(DIST).items() if pathlib.PurePosixPath(f).name.lower() not in PE_NETWORK_IMPORT_ALLOWLIST}
    assert not offenders, offenders
```

Runtime import graph:

**`tests/test_import_graph.py`**

```python
"""Layer: runtime import graph. Starts the real app import graph in a fresh interpreter and inspects sys.modules."""
import json, os, subprocess, sys, pathlib
from offline_rules import FORBIDDEN_MODULES
ROOT = pathlib.Path(__file__).resolve().parents[1]

def test_app_import_graph_has_no_network_modules():
    env = dict(os.environ, QT_QPA_PLATFORM="offscreen")
    code = f"import sys, json; sys.path.insert(0, {str(ROOT)!r}); import crosswalk.app_imports; print(json.dumps(sorted(sys.modules)))"
    p = subprocess.run([sys.executable, "-I", "-c", code], capture_output=True, text=True, env=env, cwd=ROOT, timeout=120)
    assert p.returncode == 0, p.stderr[-2000:]
    loaded = set(json.loads(p.stdout.strip().splitlines()[-1]))
    bad = sorted(m for m in loaded if m in FORBIDDEN_MODULES)
    assert not bad, f"forbidden modules imported by the app: {bad}"
```

Source and lockfile hygiene:

**`tests/test_static_scan.py`**

```python
"""Layer: source and lockfile hygiene. Pure text/AST checks, so they run anywhere (Linux CI)."""
import ast, pathlib, re
from conftest import ROOT, LOCK
from offline_rules import FORBIDDEN_MODULES, FORBIDDEN_DISTS, APPROVED_DISTS, URL_RE, URL_ALLOW_PREFIXES, PIP_REQ_RE, normalize_dist

SRC = [p for p in (ROOT / "crosswalk").rglob("*.py")]

def imported_modules(tree):
    for n in ast.walk(tree):
        if isinstance(n, ast.Import):
            for a in n.names: yield a.name
        elif isinstance(n, ast.ImportFrom) and n.module and n.level == 0:
            yield n.module
            for a in n.names: yield f"{n.module}.{a.name}"

def test_no_forbidden_imports_in_app_source():
    bad = []
    for p in SRC:
        if p.name == "offline_guard.py":    # the guard names the modules it forbids as strings, not imports
            continue
        for m in imported_modules(ast.parse(p.read_text())):
            if m in FORBIDDEN_MODULES or m.split(".")[0] in FORBIDDEN_MODULES:
                bad.append((p.name, m))
    assert not bad, bad

def test_no_url_literals_in_app_source():
    bad = []
    for p in SRC:
        if p.name == "offline_guard.py": continue
        for n in ast.walk(ast.parse(p.read_text())):
            if isinstance(n, ast.Constant) and isinstance(n.value, str):
                for m in URL_RE.findall(n.value):
                    if not m.lower().startswith(URL_ALLOW_PREFIXES): bad.append((p.name, m))
    assert not bad, bad

def test_no_desktop_services_or_shell_open_calls():
    pat = re.compile(r"\b(openUrl|QDesktopServices|setOpenExternalLinks|os\.startfile|webbrowser|QProcess|subprocess|os\.system|QNetwork\w*|QWebEngine\w*)\b")
    bad = [(p.name, m.group(0)) for p in SRC if p.name != "offline_guard.py" for m in pat.finditer(p.read_text())]
    assert not bad, bad

def test_lockfile_is_hashed_pinned_and_clean():
    text = LOCK.read_text()
    reqs = PIP_REQ_RE.findall(text)
    assert reqs, "empty lockfile"
    # every pinned requirement carries at least one hash; no VCS / URL / editable lines
    blocks = re.split(r"\n(?=[A-Za-z0-9][A-Za-z0-9._-]*==)", text)
    for b in blocks:
        if PIP_REQ_RE.match(b): assert "--hash=sha256:" in b, b.splitlines()[0]
    assert not re.search(r"^(-e |git\+|https?://|file:)", text, re.M)
    bad = sorted(normalize_dist(r) for r in reqs if normalize_dist(r) in FORBIDDEN_DISTS)
    assert not bad, bad

def test_lockfile_pins_exactly_the_approved_distributions():
    pinned = {normalize_dist(r) for r in PIP_REQ_RE.findall(LOCK.read_text())}
    assert pinned == APPROVED_DISTS, {"unexpected": sorted(pinned - APPROVED_DISTS), "missing": sorted(APPROVED_DISTS - pinned)}
```

### R7. CI commands

Linux job (everything that can run there), then a Windows job. Commands marked * were run in my sandbox in this form; the others are the same steps on another OS.

```bash
python3.12 -m venv .venv && . .venv/bin/activate
pip install --require-hashes --only-binary=:all: --no-deps -r requirements-build.txt -r requirements.txt   # *
# the lock must resolve for the real target
pip download --platform win_amd64 --python-version 3.12 --implementation cp --abi cp312 \
    --only-binary=:all: --require-hashes -r requirements.txt -d wheels-win                                 # *
python -m PyInstaller --noconfirm --clean crosswalk.spec                                                   # * (Linux build)
CROSSWALK_DIST=dist/Crosswalk CROSSWALK_BUILD=build/crosswalk QT_QPA_PLATFORM=offscreen pytest -q          # * 20 passed
# repeat the guard tests on 3.13 if you plan to move
```

```text
Windows job (not run): same install and PyInstaller steps with the Windows interpreter; upload dist\Crosswalk as an artifact;
run pytest with CROSSWALK_DIST pointing at it; compile crosswalk.iss with the Inno compiler; install silently in a VM; run the
firewall probe (7.3); uninstall and check the rules are gone.
```

### R8. What the guard will and will not trip on Windows (read from the Windows wheels, not run)

- numpy 2.5.4 and pandas 3.1.0 on Windows load their bundled DLLs with `os.add_dll_directory` (the delvewheel patch at the top of `numpy/__init__.py` and `pandas/__init__.py`), not with `ctypes`. No `ctypes.dlopen` is expected from them at import. (`os.add_dll_directory` raises its own audit event, which the guard does not deny.) Apart from numpy's own test files, the only Python file in the numpy, pandas, lxml, PySide6 and shiboken6 Windows wheels that references `windll`, `WinDLL` or `LoadLibrary` is `pandas/io/clipboard/__init__.py`, whose loaders are reached only through clipboard functions (**Inference** from the code layout; not run).
- `python-geosupport` is the one `ctypes` user (4.5). Its first call is `ctypes.dlopen` on `nycgeo.dll` and its second `ctypes.dlsym` for `NYCgeo`.
- `subprocess.Popen` and `os.system` are denied. If any library on Windows spawns a process during import or normal use (for example a `platform` fallback), the guard will raise, and the first Windows smoke run will show it in the violation text. I did not find such a path in the Linux runs (T8, T9) and have not read the Windows-specific branches of CPython's `platform` module (**Unconfirmed**).

---

## Open risks

1. **Nothing was run on Windows.** The `win32` branches of the spec, the Qt DLL drop list, the PE allowlist (measured on wheels plus a conda-forge CPython), the Inno lines, the `netsh` syntax, and the firewall behavior are all untested. The first Windows build may need more `hiddenimports`, a different drop list, or a different allowlist.
2. **The firewall layer can be removed or ignored.** An administrator can delete or disable the rule. A restrictive policy can turn off local rule merging, in which case a locally created rule is not applied (5.5); whether it then shows as inactive in `ActiveStore` is Unconfirmed. If the firewall service is off, this layer is off.
3. **Kernel-brokered I/O.** Opening `\\server\share\file.csv` or a WebDAV path makes the SMB or WebClient components do the network work. Whether a per-program rule covers that is Unconfirmed. The guard denies such paths at `open`, but mapped drive letters and any path opened by native code (Qt file dialogs, the Geosupport DLL) are not attributed.
4. **Native code is outside the audit hook.** Qt, libxml2 (with HTTP and FTP client code in the Windows `etree.pyd`), and `nycgeo.dll` can make calls Python never sees. I found no documented reason for Qt Widgets or Geosupport to do so, but I did not find a statement that they never do (3.5, 4.5). I also did not search qtbase for every internal caller of `QDesktopServices::openUrl` (GitHub code search was refused in my environment), so "no Widgets code path opens a URL by itself" is Unconfirmed beyond the two properties checked (`QLabel`, `QTextBrowser`).
5. **Geosupport Desktop Edition.** Its DLL's imports, any license or update checks, and what its installer does are not covered by anything I could read. The NYC Planning guide I read is silent on this. Measure its import table with the PE scanner before adding it to the allowlist.
6. **Sub-interpreters and hostile code.** Anyone who can run arbitrary Python inside the process can bypass the hook (1.3). On Windows the sub-interpreter modules are compiled into `python3xx.dll` and cannot be excluded, so the guard's import deny and `None` entries are the only barrier. This is outside the threat model (accidents, careless libraries), but it limits what "provable" means.
7. **Supply chain.** Hash pins prove "the same bytes as last time", not "safe bytes". PyInstaller, Inno Setup and the other build tools are outside the app lock. New package versions change the PE import picture, so re-run the scan on every bump.
8. **Documentation discrepancies to keep in mind.** PEP 578's event names (1.1), the `ctypes.call_function` description (1.3), lxml's "on by default" for `resolve_entities` (4.1), pip accepting a range requirement in hash mode (8.1), and the netsh troubleshooting page's garbled delete examples (5.2).
9. **Pages I could not read** (access errors from my sandbox): openpyxl documentation, pip.pypa.io secure-installs (read the documentation source instead), GitHub's Windows runner image readme, Microsoft's event 5157 pages (blocked-connection auditing), the Inno `ArchitecturesInstallIn64BitMode` and `[UninstallRun]` pages, and the pandas documentation page for `read_csv` (read the docstring in the source instead). python.org and NuGet downloads were blocked, which is why the Windows interpreter I inspected is the conda-forge build.
10. **Scope of "no AI".** The controls show the shipped app has no AI client, no model file, and no path to an AI service. They say nothing about how the code was written, which is a process question. A deny list of SDK names is incomplete by nature; the exact allowlist in the lock test is the real control.
11. **Python version.** I ran 3.12.3 and 3.13.18. Differences found: `telnetlib` exists only on 3.12; the sub-interpreter module names differ (`_xxsubinterpreters` vs `_interpreters`, `_interpchannels`, `_interpqueues`). I did not research end-of-life dates for 3.12.

---

## Experiment log

All scripts and outputs are from the scratch directory used for this research. Versions: CPython 3.12.3 and 3.13.18 (Linux), PySide6 6.12.0, pandas 3.1.0, numpy 2.5.4, lxml 6.1.3, openpyxl 3.1.5, python-geosupport 1.1.0, PyInstaller 6.22.3, pip 26.2.2, pip-tools 7.6.2.

| ID | What I ran | Result |
|---|---|---|
| T1 | Hook that records every audit event while calling `create_connection`, `urlopen`, `xmlrpc.client`, `ftplib`, `smtplib`, and a UDP `connect()` then `send()` (3.12.3) | Events listed in 1.2. No event for `send()`. `send` on a socket made earlier is also unaudited |
| T2 | The guard against first imports, `importlib.import_module`, and already-imported modules | Statement imports of network modules raise; `import_module` of builtin or pure modules raises no event |
| T3 | Bypass probes on 3.12.3 and 3.13.18: reading the hook's closure, clobbering globals, `ctypes` on pointers resolved earlier, `ctypes.memmove`, `ctypes.cast`, `importlib` paths | Gaps in 1.3. Any exception from the hook aborts the operation even if the exception class is tampered with |
| T4 | Sub-interpreter probes: `_xxsubinterpreters` (3.12), `_interpreters` (3.13) creating a socket in a new interpreter | No events reach the main interpreter's hook, both versions |
| T5 | Monkeypatching `socket.socket` and probing `_socket`, `from socket import socket`, `getaddrinfo`, attribute assignment on the C type | Results in 1.4 |
| T6 | lxml 6.1.3: external entity, `iterparse`, `ETCompatXMLParser`, `resolve_entities=True`, HTTP parse on the Linux wheel, XSLT `document()` with and without `DENY_ALL` | Defaults safe; `http` and `ftp` absent from `LIBXML_FEATURES`; `DENY_ALL` blocks `document('file:///...')` |
| T7 | pandas `read_csv`, `read_excel`, `read_json`, `read_xml`, `read_html`, and numpy `loadtxt` and `genfromtxt` against a loopback HTTP server, `ftp://`, `file://`, `s3://`, local paths, file objects, with the audit events recorded | Section 4.2. Optional network packages (`fsspec`, `s3fs`, `requests`, `bs4`, `html5lib`, `aiohttp`, `urllib3`, `gcsfs`) absent |
| T8 | Import the real app stack in a fresh interpreter and list `sys.modules`; text search of openpyxl, et_xmlfile, python-geosupport for network imports | 832 modules, no network module; no network imports in those three packages |
| T9 | Three Linux PyInstaller builds of a demo app that uses the full stack: default, clean venv, hardened spec; run the hardened frozen app | 1,504 / 909 / 809 PYZ modules; 425 / 417 / 400 COLLECT entries; hardened has no forbidden modules, only `libQt6Network` files; first hardened run crashed on `secrets` until it was added as a hidden import; the guard blocked `socket` through PyInstaller's multiprocessing runtime hook until `multiprocessing` was excluded |
| T10 | Made 82 excluded modules unimportable in a normal interpreter and exercised the stack | Works except `xml.sax.saxutils` / `make_parser`, `email`, `multiprocessing` (2.2) |
| T11 | `pefile` import-table analysis of the 6.12.0 Windows wheels (PySide6-Essentials, PySide6-Addons, shiboken6), lxml 6.1.3, numpy 2.5.4, pandas 3.1.0 for `win_amd64` / `cp312`; plugin closures; Python files of the numpy and pandas wheels read for `ctypes` loading | QtCore/Gui/Widgets closures lack `Qt6Network.dll`; network-reaching plugins listed in 3.3; `Qt6Core.dll`, `etree.pyd`, `objectify.pyd` import `ws2_32`; Essentials ships `QtNetwork.pyd`; numpy and pandas use `os.add_dll_directory` |
| T12 | Pytest suite (20 tests) on the hardened Linux build and on 3.13 (guard tests); negative controls: default build, extra package in the lock, app source with `import socket` / `QDesktopServices` / URL, simulated raw Windows tree | 20 passed; 9 guard tests passed on 3.13; default build failed 2 of 5 bundle tests; extra package failed 2 lock tests; bad source failed 4 tests; raw simulated Windows tree failed the PE test; the same tree with offenders deleted passed |
| T13 | `pip-compile --generate-hashes`; pip hash mode with a tampered hash, a missing transitive pin, an unhashed pin and a range with a hash; `pip download` for `win_amd64` / `cp312` under `--require-hashes` | 11 pins, 322 hashes; behaviors in 8.1; all 11 Windows wheels fetched |
| T14 | Unpacked the conda-forge Windows CPython 3.12.16 (stand-in for python.org) and scanned its PE imports; `strings` on `etree.cp312-win_amd64.pyd` | `python312.dll`, `select.pyd`, `_socket.pyd` (also `iphlpapi`), `_ssl.pyd`, `_overlapped.pyd`, `_multiprocessing.pyd` import `ws2_32`; `_xxsubinterpreters` is not a separate file; `etree.pyd` contains libxml2 HTTP and FTP client strings |

---

## Notes on sources

Sources that are **not** on the list of domains you named, used only where no named domain holds the fact: PyPI (package metadata and the unpacked wheels), the GitHub repositories of qtbase, python-geosupport, Omnibus-Type/Archivo, miketheman/pytest-socket, jazzband/pip-tools, pandas, numpy and pypa/pip (documentation source), the NYC Planning Geosupport guide, GitHub's hosted-runner overview, and the conda-forge package of Windows CPython. Where a fact comes from source code rather than prose documentation, the text says so.

---

## Sources

Every link cited above, grouped by owner. Documentation pages are listed under the domain you named. GitHub entries are source files or documentation sources, pinned to the tag in the URL where one is given. The last group is outside your named list (see "Notes on sources").

### Python

- <https://docs.python.org/3/library/sys.html#sys.addaudithook>
- <https://docs.python.org/3.12/library/telnetlib.html>
- <https://peps.python.org/pep-0578/>
- <https://peps.python.org/pep-0578/#why-not-a-sandbox>
- <https://docs.python.org/3/library/audit_events.html>
- <https://docs.python.org/3.12/library/socket.html>
- <https://docs.python.org/3.12/library/urllib.request.html>
- <https://docs.python.org/3.12/library/http.client.html>
- <https://docs.python.org/3.12/library/ftplib.html>
- <https://docs.python.org/3.12/library/smtplib.html>
- <https://docs.python.org/3.12/library/poplib.html>
- <https://docs.python.org/3.12/library/imaplib.html>
- <https://docs.python.org/3.12/library/webbrowser.html>
- <https://docs.python.org/3.12/library/subprocess.html>
- <https://docs.python.org/3.12/library/os.html>
- <https://docs.python.org/3.12/library/winreg.html>
- <https://docs.python.org/3.12/library/ctypes.html>
- <https://docs.python.org/3.12/library/functions.html#open>

### PyInstaller

- <https://pyinstaller.org/en/stable/usage.html>
- <https://pyinstaller.org/en/stable/spec-files.html>
- <https://pyinstaller.org/en/stable/when-things-go-wrong.html>
- <https://pyinstaller.org/en/stable/advanced-topics.html#the-toc-and-tree-classes>
- <https://pyinstaller.org/en/stable/hooks-config.html>
- <https://pyinstaller.org/en/stable/runtime-information.html>
- <https://pyinstaller.org/en/stable/operating-mode.html>

### Qt

- <https://doc.qt.io/qt-6/qdesktopservices.html>
- <https://doc.qt.io/qt-6/qlabel.html>
- <https://doc.qt.io/qt-6/qtextbrowser.html>
- <https://doc.qt.io/qt-6/qfontdatabase.html>

### Microsoft

- <https://learn.microsoft.com/en-us/windows/security/operating-system-security/network-security/windows-firewall/rules>
- <https://learn.microsoft.com/en-us/troubleshoot/windows-server/networking/netsh-advfirewall-firewall-control-firewall-behavior>
- <https://learn.microsoft.com/en-us/windows/security/application-security/application-isolation/windows-sandbox/windows-sandbox-configure-using-wsb-file>
- <https://learn.microsoft.com/en-us/windows/win32/secauthz/mandatory-integrity-control>
- <https://learn.microsoft.com/en-us/windows/win32/secauthz/appcontainer-for-legacy-applications->
- <https://learn.microsoft.com/en-us/windows/security/application-security/application-control/app-control-for-business/appcontrol-and-applocker-overview>
- <https://learn.microsoft.com/en-us/windows/security/operating-system-security/network-security/windows-firewall/configure>
- <https://learn.microsoft.com/en-us/powershell/module/netsecurity/new-netfirewallrule?view=windowsserver2025-ps>
- <https://learn.microsoft.com/en-us/windows-server/administration/windows-commands/netsh-advfirewall>
- <https://learn.microsoft.com/en-us/windows/security/operating-system-security/network-security/windows-firewall/configure-with-command-line>
- <https://learn.microsoft.com/en-us/powershell/module/netsecurity/get-netfirewallapplicationfilter?view=windowsserver2025-ps>
- <https://learn.microsoft.com/en-us/windows/win32/secauthz/appcontainer-isolation>
- <https://learn.microsoft.com/en-us/windows/apps/package-and-deploy/app-capability-declarations>

### Inno Setup

- <https://jrsoftware.org/ishelp/topic_runsection.htm>
- <https://jrsoftware.org/ishelp/topic_setup_privilegesrequired.htm>
- <https://jrsoftware.org/ishelp/topic_consts.htm>
- <https://jrsoftware.org/ishelp/topic_setupcmdline.htm>

### lxml

- <https://lxml.de/parsing.html>
- <https://lxml.de/resolvers.html>

### Source code on GitHub

- <https://github.com/python/cpython/blob/3.12/PC/config.c>
- <https://github.com/qt/qtbase/blob/v6.12.0/src/gui/CMakeLists.txt>
- <https://github.com/qt/qtbase/blob/v6.12.0/src/plugins/generic/tuiotouch/CMakeLists.txt>
- <https://github.com/lxml/lxml/blob/lxml-6.1.3/CHANGES.txt>
- <https://github.com/pandas-dev/pandas/blob/main/pandas/io/common.py>
- <https://github.com/miketheman/pytest-socket>
- <https://github.com/pypa/pip/blob/main/docs/html/topics/secure-installs.md>
- <https://github.com/jazzband/pip-tools/blob/main/README.md>
- <https://github.com/python/cpython/blob/3.13/PC/config.c>
- <https://github.com/python/cpython/blob/3.12/Modules/socketmodule.c>
- <https://github.com/python/cpython/blob/3.12/Lib/urllib/request.py>
- <https://github.com/python/cpython/blob/3.12/Modules/_ctypes/callproc.c>
- <https://github.com/python/cpython/blob/3.12/Modules/_ctypes/_ctypes.c>
- <https://github.com/python/cpython/blob/3.12/Python/import.c>
- <https://github.com/python/cpython/blob/3.12/Python/importdl.c>
- <https://github.com/python/cpython/blob/3.12/Doc/library/audit_events.rst>
- <https://github.com/python/cpython/blob/3.12/Lib/importlib/__init__.py>
- <https://github.com/qt/qtbase/blob/v6.12.0/src/plugins/platforms/windows/qwindowsservices.cpp>
- <https://github.com/python/cpython/blob/3.12/Lib/socket.py>
- <https://github.com/pyinstaller/pyinstaller/blob/v6.22.3/PyInstaller/building/build_main.py>
- <https://github.com/pyinstaller/pyinstaller/blob/v6.22.3/doc/advanced-topics.rst>
- <https://github.com/pyinstaller/pyinstaller/blob/v6.22.3/PyInstaller/depend/analysis.py>
- <https://github.com/python/cpython/blob/3.12/Lib/subprocess.py>
- <https://github.com/pyinstaller/pyinstaller/blob/v6.22.3/PyInstaller/hooks/rthooks/pyi_rth_multiprocessing.py>
- <https://github.com/python/cpython/blob/3.12/PCbuild/pcbuild.proj>
- <https://github.com/qt/qtbase/blob/v6.12.0/src/widgets/CMakeLists.txt>
- <https://github.com/qt/qtbase/blob/v6.12.0/src/corelib/CMakeLists.txt>
- <https://github.com/pyinstaller/pyinstaller/blob/v6.22.3/PyInstaller/utils/hooks/qt/__init__.py>
- <https://github.com/pyinstaller/pyinstaller/blob/v6.22.3/PyInstaller/utils/hooks/qt/_modules_info.py>
- <https://github.com/qt/qtbase/blob/v6.12.0/src/gui/kernel/qguiapplication.cpp>
- <https://github.com/qt/qtbase/blob/v6.12.0/src/gui/util/qdesktopservices.cpp>
- <https://github.com/qt/qtbase/blob/v6.12.0/src/gui/text/qtextdocument.cpp>
- <https://github.com/Omnibus-Type/Archivo/blob/master/OFL.txt>
- <https://github.com/lxml/lxml/blob/lxml-6.1.3/src/lxml/xslt.pxi>
- <https://github.com/pandas-dev/pandas/blob/main/pandas/io/parsers/readers.py>
- <https://github.com/numpy/numpy/blob/main/numpy/lib/_datasource.py>
- <https://github.com/ishiland/python-geosupport/blob/master/geosupport/platform_utils.py>
- <https://github.com/ishiland/python-geosupport/blob/master/geosupport/geosupport.py>
- <https://github.com/ishiland/python-geosupport/blob/master/geosupport/config.py>
- <https://github.com/ishiland/python-geosupport/blob/master/README.md>
- <https://github.com/pyinstaller/pyinstaller/blob/v6.22.3/doc/operating-mode.rst>

### Outside the domains you named

- <https://pypi.org/pypi/PySide6/6.12.0/json>
- <https://pypi.org/project/PySide6-Essentials/6.12.0/#files>
- <https://pypi.org/project/openpyxl/3.1.5/>
- <https://www.nyc.gov/assets/planning/download/pdf/data-maps/open-data/upg.pdf>
- <https://docs.github.com/en/actions/using-github-hosted-runners/using-github-hosted-runners/about-github-hosted-runners>

### Listed but not read (access error; no claim relies on them)

- <https://learn.microsoft.com/en-us/windows/security/threat-protection/auditing/event-5157>
