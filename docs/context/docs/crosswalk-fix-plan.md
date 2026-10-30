# Crosswalk fix plan

Sep 28, 2026 · @Joe Buzzetta

Most of Crosswalk's problems can be fixed completely. Replacing the local web server with a native window closes the worst security holes in one move. A saved crosswalk and a split between counting and mapping fix the numbers. A few risks can only be reduced, and the scorecard at the end names them.

## At a glance

&#91;embedded content: order of work · 9 blocks in 4 lanes, 3 before the next real run\]

The shaded band is what the next real run needs. Skip the stopgap token and launcher work if Phase 2 ships first. Make the install secret from 5.4 before starting 4.3 to 4.5.

## How to use this plan

This plan is built from the Crosswalk docs, meaning the AI description, TECHNICAL.md, the user guide and the walkthrough deck. I could not see the source code. Where a step says **Check first**, read that part of the code before changing it.

Every fix follows the same layout.

- **Problem.** What is wrong, in a sentence or two.
- **Steps.** Numbered, in the order to do them.
- **Test it.** How to prove the fix works.
- **Result.** Fully fixed, or only reduced and why.

The code samples were run against current releases of FastAPI 0.141, Starlette 1.7, pywebview 6.2 and msoffcrypto-tool 6.0. Pin the versions you test with. Library APIs move.

**Do Phase 1 only if a real client run happens before Phase 2 ships.** Phase 2 removes the web server, which makes the token, host checks and launcher fixes unnecessary. Two Phase 1 items apply either way. Turn off request logging (1.3) and take run.bat out of client builds (1.4).

**Add a test for every fix.** Your docs generator already fails when the docs drift from the code. Phase 6 extends that idea so every promise in the docs points at a test that proves it.

## Phase 1. Stopgap hardening for the current build

Rough effort is 1 to 2 days. These fixes keep the browser-and-server design and close its worst holes.

### 1.1 Require a secret token on every request

**Problem.** Any web page the operator has open can send requests to 127.0.0.1:8765. Routes with no body, like /api/reset and /api/quit, need nothing more to fire.

**Steps.**

1. In launch.py, make a new token on every launch.

```python
import secrets
token = secrets.token_urlsafe(32)
```

2. Hand it to the server. If the server runs as its own process, pass it in the environment variable `CROSSWALK_TOKEN`, along with `CROSSWALK_PORT`. Keep it off the command line, where other accounts can see it in the process list. **Check first** how launch.py starts the server.
3. Open the browser with the token in the URL fragment. Browsers never send the fragment to the server, so it never reaches a log.

```python
webbrowser.open(f"http://127.0.0.1:{port}/#t={token}")
```

4. At the top of app.js, read the token, keep it for reloads, and clear it from the address bar.

```js
const TOKEN = new URLSearchParams(location.hash.slice(1)).get("t")
  || sessionStorage.getItem("cw_t");
if (TOKEN) sessionStorage.setItem("cw_t", TOKEN);
history.replaceState(null, "", location.pathname);
```

5. Send the token on every call. If app.js calls fetch from one helper, add the header there. If not, wrap fetch once.

```js
const _fetch = window.fetch.bind(window);
window.fetch = (url, opts = {}) => _fetch(url, {
  ...opts,
  headers: { ...(opts.headers || {}), "X-Crosswalk-Token": TOKEN },
});
```

6. Plain download links can't carry a header. Switch the export downloads and "open the original file" to fetch plus a blob.

```js
async function download(url, fallbackName) {
  const r = await fetch(url);
  const cd = r.headers.get("content-disposition") || "";
  const name = (/filename="?([^";]+)"?/.exec(cd) || [])[1] || fallbackName;
  const a = document.createElement("a");
  a.href = URL.createObjectURL(await r.blob());
  a.download = name;
  a.click();
  setTimeout(() => URL.revokeObjectURL(a.href), 1000);
}
```

7. The closing call to /api/bye can't use sendBeacon, because sendBeacon can't set headers. Use fetch with keepalive instead.

```js
fetch("/api/bye", { method: "POST", keepalive: true });
```

8. Make the launcher send the header on its own calls to /api/alive and /api/quit.
9. Add the server-side check in 1.2. It handles the token and the origin in one place.

**Test it.** With the tool open, run `curl -X POST http://127.0.0.1:8765/api/reset` from a command prompt. You should get 403, and your work should still be there.

**Result.** Fully fixed for web pages and other Windows accounts. A program running as the operator, or as an administrator, can still read the token. No app can defend against that.

### 1.2 Reject other hosts and other origins

**Problem.** DNS rebinding lets a hostile site point its own domain name at 127.0.0.1. The browser then treats your server as part of that site and lets the page read responses, including the clean export.

**Steps.**

1. Add Starlette's host filter and one middleware that checks the token and the origin together. I ran this against the attacks above. Each was refused and a correct request went through.

```python
import os, secrets
from fastapi import Request
from fastapi.responses import JSONResponse
from starlette.middleware.trustedhost import TrustedHostMiddleware

TOKEN = os.environ["CROSSWALK_TOKEN"]
PORT = int(os.environ["CROSSWALK_PORT"])
ALLOWED_ORIGINS = {f"http://127.0.0.1:{PORT}", f"http://localhost:{PORT}"}

@app.middleware("http")
async def guard(request: Request, call_next):
    if request.url.path.startswith("/api/"):
        sent = request.headers.get("x-crosswalk-token", "")
        if not secrets.compare_digest(sent, TOKEN):
            return JSONResponse({"error": "not allowed"}, status_code=403)
    if request.method != "GET":
        origin = request.headers.get("origin")
        if origin and origin not in ALLOWED_ORIGINS:
            return JSONResponse({"error": "not allowed"}, status_code=403)
        if request.headers.get("sec-fetch-site") == "cross-site":
            return JSONResponse({"error": "not allowed"}, status_code=403)
    return await call_next(request)

app.add_middleware(TrustedHostMiddleware, allowed_hosts=["127.0.0.1", "localhost"])
```

2. Leave the page itself open (`GET /`, `/goodbye` and the files under ui/). It holds no client data.
3. Update the test client to send the token and use `base_url="http://127.0.0.1"`. Otherwise the API suite fails with 400 and 403 errors.

**Test it.** `curl -H "Host: evil.example" http://127.0.0.1:8765/` should return 400. A POST to /api/reset with the right token and `Origin: http://evil.example` should return 403.

**Result.** Fully fixed.

### 1.3 Stop writing requests and errors to the log

**Problem.** Uvicorn logs every request line to stdout, query string included. The launcher sends stdout to launch-log.txt. A reviewer who searches the queue for a client's name writes that name to disk. Error messages can carry cell values too.

**Steps.**

1. Turn off the access log where the server starts.

```python
uvicorn.run(app, host="127.0.0.1", port=port, access_log=False, log_level="warning")
```

2. Log errors by type and code location only.

```python
import logging, traceback
log = logging.getLogger("crosswalk")

def safe_error(exc: BaseException) -> str:
    frames = traceback.extract_tb(exc.__traceback__)[-5:]
    where = " < ".join(f"{f.name}:{f.lineno}" for f in reversed(frames))
    return f"{type(exc).__name__} at {where}"

@app.exception_handler(Exception)
async def on_error(request, exc):
    log.error("%s on %s", safe_error(exc), request.url.path)
    return JSONResponse({"error": "Something went wrong. The log has the details."}, status_code=500)
```

3. Use `safe_error` in `_run_thread` too. That is where processing errors go into the run status and onto the screen.
4. Cap the log size with `logging.handlers.RotatingFileHandler(path, maxBytes=1_000_000, backupCount=2)`.
5. Delete launch-log.txt on every machine that has run Crosswalk. Old copies may hold client names. Ask Stephanie which machines those are.

**Test it.** Search the queue for a made-up name such as "Zyxwv Testperson". Close the tool and search the log for that name. It should not be there. Make this an automated test that drives the API and scans the log.

**Result.** Fully fixed.

### 1.4 Take run.bat out of client builds

**Problem.** run.bat starts the old Streamlit front end. Streamlit leaves `server.address` unset by default, so it listens on every network interface. Its `browser.gatherUsageStats` setting is on by default. One double-click puts the tool on the office network.

**Steps.**

1. Remove run.bat and the Streamlit entry point from the packaged archive. Keep them in the repo for the parity tests.
2. Move Streamlit out of the runtime requirements and into a dev-only requirements file.
3. Add a build test that fails when either one ships.

```python
import zipfile

def test_no_streamlit_in_client_build():
    names = zipfile.ZipFile(ARCHIVE).namelist()
    assert not any(n.endswith("run.bat") or "/streamlit/" in n for n in names)
```

4. For development use, add `.streamlit/config.toml`.

```toml
[server]
address = "127.0.0.1"
headless = true

[browser]
gatherUsageStats = false
```

**Test it.** Unzip the client build and confirm run.bat and Streamlit are gone.

**Result.** Fully fixed.

### 1.5 Stop the launcher from trusting or killing whatever holds the port

**Problem.** The launcher asks whatever answers on port 8765 for its version. It kills an older or unknown one by port, and opens a newer one in the browser. A program posing as a newer Crosswalk receives the uploads. An unrelated program on 8765 gets killed.

**Steps.**

1. On launch, write `%LOCALAPPDATA%\Crosswalk\instance.json` with the process id, port and token. By default only the operator's Windows account can read that folder.
2. To stop an old copy, read that file and call /api/quit with its token.
3. If the old copy doesn't answer, kill it only if its process id is still running and its command line contains crosswalk\_server. `psutil.Process(pid).cmdline()` returns the command line. Windows denies that read for another account's process, which is the behavior you want.
4. Never kill a process that isn't in the instance file. If something else holds the port, pick another port.
5. Only open the browser to a server this launch started.
6. If a copy from before this fix is running, with no instance file, tell the operator to restart the computer. Don't kill it by port.

**Test it.** Run `python -m http.server 8765`, then launch Crosswalk. The other server should keep running, and Crosswalk should open on a different port.

**Result.** Fully fixed. Phase 2 removes the port and this launcher code entirely.

## Phase 2. Replace the local web server with a native window

Rough effort is 3 to 5 days. This one change closes most of the security holes for good. The same page runs inside a desktop window and talks to Python through pywebview's bridge. Nothing listens on a network port, so a web page, another account or an impostor has nothing to connect to.

It also retires the heartbeat, bye, quit and kill-by-port code, plus the cache middleware.

### 2.1 Add pywebview

1. Add `pywebview` to the pinned requirements. On Windows it draws the page with Microsoft Edge WebView2, which ships with Windows 11 and updated Windows 10.
2. In desktop.py, catch any error from starting the window. Show a native message box that says to install the WebView2 Runtime from Microsoft.

### 2.2 Route every API call through one bridge method

**Steps.**

1. Create desktop.py next to crosswalk\_server.py. The bridge runs each request through your FastAPI app in the same process. Your routes and handlers don't change. I tested this pattern with eight calls at once and with multi-file uploads.

```python
import os
from pathlib import Path
import webview
from starlette.testclient import TestClient
from crosswalk_server import app

class Bridge:
    def __init__(self, client):
        self._client = client      # names starting with _ stay hidden from the page
        self._window = None

    def call(self, method, path, body=None):
        r = self._client.request(method, path, json=body)
        ctype = r.headers.get("content-type", "")
        return {"status": r.status_code,
                "json": ctype.startswith("application/json"),
                "body": r.text}
```

2. Open the window with the page inlined. With `html=` and no local URL, pywebview starts no server at all.

```python
def build_page() -> str:
    ui = Path(__file__).parent / "ui"
    html = (ui / "index.html").read_text(encoding="utf-8")
    css = (ui / "styles.css").read_text(encoding="utf-8")
    js = (ui / "app.js").read_text(encoding="utf-8")
    helptext = (ui / "help.json").read_text(encoding="utf-8")
    html = html.replace('<link rel="stylesheet" href="styles.css">', f"<style>{css}</style>")
    html = html.replace('<script src="app.js"></script>',
                        f"<script>window.HELP = {helptext};</script><script>{js}</script>")
    return html

def main():
    with TestClient(app, base_url="http://127.0.0.1") as client:
        bridge = Bridge(client)
        window = webview.create_window("Crosswalk", html=build_page(), js_api=bridge,
                                       width=1400, height=900)
        bridge._window = window
        webview.start(private_mode=True)

if __name__ == "__main__":
    main()
```

3. **Check first** the exact link and script tags in index.html, so the two `replace` calls match them. Inline any images as data URIs. Make app.js read help text from `window.HELP` instead of fetching help.json.
4. Keep the inlined page under 2 MB, which is WebView2's limit for pages passed as a string. If it grows past that, pass `url="ui/index.html"` instead. pywebview then serves the ui folder from its own server on 127.0.0.1. That server holds only the page files, never client data.
5. In app.js, send every request through the bridge from one helper, and start once the bridge is ready. **Check first** where app.js calls fetch today and how it handles non-JSON replies.

```js
async function api(method, path, body) {
  const r = await window.pywebview.api.call(method, path, body ?? null);
  if (r.status >= 400) throw new Error(`Request failed (${r.status})`);
  return r.json ? JSON.parse(r.body) : r.body;
}

window.addEventListener("pywebviewready", () => load("check"));
```

6. Polling /api/run/status keeps working. pywebview runs each bridge call on its own thread, so a poll never waits behind processing.
7. Pin Starlette. Starlette 1.7 warns that TestClient is moving from httpx to a package called httpx2. If you'd rather not ship a test tool, have the bridge call the route handlers directly.

### 2.3 Use native dialogs for files in and out

1. Replace the upload box with an Open dialog. Python reads each file straight from disk.

```python
    def open_files(self):
        paths = self._window.create_file_dialog(
            webview.FileDialog.OPEN, allow_multiple=True,
            file_types=("Data files (*.csv;*.tsv;*.xlsx;*.json;*.xml)",))
        if not paths:
            return None
        files = [("files", (Path(p).name, Path(p).read_bytes())) for p in paths]
        r = self._client.post("/api/sources/upload", files=files)
        return {"status": r.status_code, "json": True, "body": r.text}
```

2. Keep each file's path in `S["uploads"]` instead of its bytes. "Open the original" can then call `os.startfile(path)`, and memory no longer holds a second copy of every file.
3. Save outputs through a Save dialog. Refuse cloud-synced folders unless the operator confirms.

```python
    def save_output(self, which, suggested_name, allow_synced=False):
        dest = self._window.create_file_dialog(webview.FileDialog.SAVE,
                                               save_filename=suggested_name)
        if not dest:
            return {"saved": False}
        dest = dest if isinstance(dest, str) else dest[0]
        warning = synced_folder_warning(dest)
        if warning and not allow_synced:
            return {"saved": False, "warning": warning}
        r = self._client.get("/api/export/file", params={"which": which})
        Path(dest).write_bytes(r.content)
        return {"saved": True, "path": dest}

def synced_folder_warning(path):
    p = os.path.normcase(os.path.abspath(path))
    for var in ("OneDrive", "OneDriveCommercial", "OneDriveConsumer"):
        root = os.environ.get(var)
        if root and p.startswith(os.path.normcase(os.path.abspath(root)) + os.sep):
            return "This folder syncs to OneDrive. Files saved here leave this computer."
    for name in ("dropbox", "google drive", "box"):
        if os.sep + name in p.lower():
            return f"This folder looks like it syncs to {name.title()}."
    return None
```

4. When the page gets a warning back, show it with two buttons. "Pick another folder" calls `save_output` again. "Save there anyway" calls it with `allow_synced=True`.

### 2.4 Delete what the port needed

1. Remove the routes /api/alive, /api/heartbeat, /api/bye, /api/quit and /goodbye. Closing the window ends `webview.start()`, and the process ends with it.
2. Remove `free_port`, `already_running`, `_pids_listening_on`, `stop_whatever_holds`, `wait_until_ready` and crosswalk.pid.
3. Remove the `_no_store` middleware. An inlined page can't go stale.
4. Remove uvicorn from the runtime requirements. Keep FastAPI, which the bridge and your tests both use.
5. Stop a second copy with a Windows named mutex or a locked file in `%LOCALAPPDATA%\Crosswalk`. A second launch shows a message instead of a second window.

6) If you built Phase 1 first, remove its token middleware or have the bridge send the token. Otherwise every bridge call gets a 403.

**Test it.** Run `netstat -ano | findstr LISTENING` before launch and again with the sample files loaded. Nothing new should appear. The API suite should still pass, since the routes are unchanged.

**Result.** Fully fixes website attacks, DNS rebinding, other accounts, port squatting and kill-by-port. A program running as the operator or as an administrator can still read memory. No app prevents that. BitLocker and a locked screen are the defense there (Phase 4).

## Phase 3. Package and ship with no pip install and no VBScript

Rough effort is 2 to 3 days. The goal is one signed folder that runs on a machine with no internet and no Python.

### 3.1 Pin every package with hashes

**Problem.** First launch installs packages from PyPI onto the machine that holds client data. The `.installed` marker means they never update after that. **Check first** whether requirements.txt pins exact versions.

**Steps.**

1. List your top-level packages in requirements.in.
2. Generate the full locked list with a hash for every file.

```
pip-compile --generate-hashes requirements.in
```

3. Install in the build environment with `pip install --require-hashes -r requirements.txt`. pip refuses any file whose hash doesn't match.
4. Run `pip-audit -r requirements.txt` before every release. Fix each finding or write down why it doesn't apply.

**Test it.** Make the release build fail when pip-audit reports anything unaddressed.

**Result.** Fully fixed for tampered downloads. New vulnerabilities keep appearing, so the audit runs on every release.

### 3.2 Bundle Python and the packages

**Problem.** The tool needs Python installed and runs pip on first launch. The "offline" claim isn't true until this changes.

**Steps.**

1. Build with PyInstaller in one-folder, windowed mode. One-folder starts faster than one-file, which unpacks itself to a temp folder on every launch and trips antivirus more often.

```
pyinstaller --noconfirm --windowed --onedir --name Crosswalk desktop.py
```

2. Move the build settings into a .spec file. List the ui folder, the reference files and the district file as data there. A .spec file avoids separator differences between Windows and other systems.
3. Remove `install_requirements`, `missing_packages`, `check_python` and the .installed marker. The bundle carries its own Python.
4. Keep the check stage for Geosupport and the reference files.
5. Run the full test suite against the built folder, the same way you test the archive today.

**Test it.** On a fresh Windows virtual machine with networking turned off, unzip the build, launch it, load the samples and export every file.

**Result.** Fully fixed. The docs can say offline with no footnote.

### 3.3 Replace the VBS launcher

**Problem.** Crosswalk.vbs starts pythonw through Windows Script Host. Microsoft has deprecated VBScript and plans to turn it off by default around 2027. Security tools often flag wscript starting another program.

**Steps.**

1. Delete Crosswalk.vbs and Stop Crosswalk.vbs. Crosswalk.exe from 3.2 replaces the first. Closing the window replaces the second.
2. Ship a small installer, for example with Inno Setup. It adds a Start menu shortcut and uninstalls cleanly.
3. Drop Crosswalk.command and Crosswalk.sh unless someone runs the tool on a Mac or Linux machine.

**Result.** Fully fixed.

### 3.4 Sign the build

**Problem.** An unsigned program from a zip triggers SmartScreen warnings. Staff learn to click through them, which is a worse habit than any single warning.

**Steps.**

1. Get a code-signing certificate for your business, either from a cloud signing service or as a standard OV certificate.
2. Sign Crosswalk.exe and the installer with a timestamp, so the signature outlives the certificate.

```
signtool sign /fd SHA256 /tr http://timestamp.digicert.com /td SHA256 /a Crosswalk.exe
```

3. Publish the SHA-256 of each release zip in the release notes.

**Test it.** In File Explorer, open the exe's Properties. The Digital Signatures tab should show your business name. In PowerShell, `Get-FileHash .\Crosswalk.zip` should match the release note.

**Result.** Fully fixed.

## Phase 4. Keep client data under control

Rough effort is 3 to 4 days of code, plus an hour with Stephanie on the machine rules in 4.6.

### 4.1 Drop sensitive columns at upload

**Problem.** Columns like SSN, gender and race are pointed out, but they stay loaded until export. They sit in memory, in previews and on the review screens. Some systems also use an SSN as their client ID.

**Steps.**

1. When a table loads, mark columns whose names match the sensitive list as excluded.
2. Drop excluded columns from `S["frames"]` and `S["blocks"]` right after table detection.
3. List the dropped columns by name on the files stage. Add a "Keep this column" switch that asks for a reason and records it in the audit.
4. Check the values in the column matched to Client\_ID. If more than half look like SSNs (nine digits, with or without dashes), stop the run and ask for a different ID column.

```python
import re
SSN = re.compile(r"^\d{3}-?\d{2}-?\d{4}$")

def looks_like_ssn(values) -> bool:
    vals = [v for v in values if v]
    return bool(vals) and sum(bool(SSN.match(v)) for v in vals) / len(vals) > 0.5
```

**Test it.** Add a proof-workbook sheet with an SSN column and an SSN-shaped ID. The first should be dropped. The second should block the run.

**Result.** Fully fixed.

### 4.2 Move and encrypt sessions and set-ups

**Problem.** Sessions and set-ups are saved next to the app, often on a desktop that OneDrive syncs. Sessions hold typed corrections, which are client values.

**Steps.**

1. Save both under `%LOCALAPPDATA%\Crosswalk`. That folder belongs to the operator's account, and OneDrive does not sync it.
2. Encrypt session files with Windows DPAPI, which ties them to the operator's Windows login. pywin32 provides it. DPAPI is Windows only, so this snippet was not run here.

```python
import win32crypt

def protect(data: bytes) -> bytes:
    return win32crypt.CryptProtectData(data, "Crosswalk", None, None, None, 0)

def unprotect(blob: bytes) -> bytes:
    return win32crypt.CryptUnprotectData(blob, None, None, None, 0)[1]
```

3. Keep the seven-day purge for sessions. Decisions that must last move to the crosswalk in 5b.

**Test it.** Save a session, copy its file into another Windows account, and try to resume there. It should fail with a clear message.

**Result.** Fully fixed on disk. Someone logged in as the operator can still open them, which BitLocker and a screen lock cover (4.6).

### 4.3 Shrink and seal the review file

**Problem.** Manual\_Review\_Needed carries every original value so staff can fix rows in Excel. It then gets emailed around and left in Downloads. The corrections file that comes back can change any column, and nothing proves it came from this run.

**Steps.**

1. Cut the file down to what a fixer needs. That means the source system, the Client\_ID, the failing fields, the reason and a row key.
2. Add a run ID and a signature column. Sign each row key with the install secret from 5b, and refuse a corrections file whose signatures don't match.

```python
import hmac, hashlib

def row_sig(secret: bytes, run_id: str, row_key: str) -> str:
    msg = f"{run_id}|{row_key}".encode()
    return hmac.new(secret, msg, hashlib.sha256).hexdigest()[:16]
```

3. Accept corrections only to the fields that failed. Refuse any other changed column, and name it.
4. Write each change to the audit as the column name plus a keyed hash of the old and new values. That proves a change happened without storing the value.
5. Offer a password on Excel outputs. msoffcrypto-tool applies Excel's own encryption. I tested this round trip.

```python
import io
from msoffcrypto.format.ooxml import OOXMLFile

def encrypt_xlsx(plain: bytes, password: str) -> bytes:
    out = io.BytesIO()
    OOXMLFile(io.BytesIO(plain)).encrypt(password, out)
    return out.getvalue()
```

6. Show the password once and never store it. Share it by phone, never in the email that carries the file.

**Test it.** Change a field that didn't fail and upload the file. It should be refused. Upload a corrections file from another run. It should be refused. Open an encrypted export in Excel. It should ask for the password.

**Result.** Reduced. Once a file leaves the tool, only people and policy protect it. These steps shrink what's in it and prove where it came from.

### 4.4 Replace the jitter

**Problem.** In Final\_Clean\_Mapped the moved point sits in the same row as the street address, so it protects nothing. When points travel alone, the default seed of 1337 lets anyone rebuild the offsets. A new row order gives new offsets each quarter, and averaging a few releases leads back to the true point.

**Steps.**

1. Take coordinates out of Final\_Clean\_Mapped by default. It already holds the address, so treat it as fully identified data. Keep the districts. Offer exact coordinates as an opt-in column for internal use.
2. Add a Map\_Counts output with no names, addresses or IDs. It holds counts per program by council, assembly and senate district, plus census tract if that Geosupport field is on. Blank out any count below 11, a common small-cell threshold, so small groups can't be singled out.
3. If someone truly needs points, add a Map\_Points file holding only program and point. Move each point by an offset built from the master ID and the install secret. The offset stays the same for a person across runs, so averaging gains nothing. Nobody without the secret can reverse it. This needs the stable master IDs from 5b. I tested these functions.

```python
import hmac, hashlib, math

def stable_offset(secret: bytes, master_id: str, min_ft=150, max_ft=250):
    d = hmac.new(secret, b"jitter|" + master_id.encode(), hashlib.sha256).digest()
    u1 = int.from_bytes(d[:8], "big") / 2**64
    u2 = int.from_bytes(d[8:16], "big") / 2**64
    return min_ft + (max_ft - min_ft) * u1, 2 * math.pi * u2

def move_point(lat, lon, dist_ft, bearing):
    m = dist_ft * 0.3048
    return (lat + m * math.cos(bearing) / 111_320,
            lon + m * math.sin(bearing) / (111_320 * math.cos(math.radians(lat))))
```

4. Remove the seed setting and the 1337 default.
5. Share Map\_Points only inside St. Nicks. In dense blocks, even a keyed offset leaves a person within a few buildings.

**Test it.** Run the same files twice with the rows shuffled. Each master ID should get the same Map\_Points coordinate both times. The seed setting should be gone.

**Result.** Fully fixed for Map\_Counts. Reduced for Map\_Points, since any point near a home carries some risk.

### 4.5 Split the audit log in two

**Problem.** The audit is called "Secure" and "safe to share," but every line carries a Client\_ID and a file name. Anyone with access to ETO or the DYCD system can tell who each line is about.

**Steps.**

1. Rename the current file Internal\_Audit\_Log.txt. Its first line says it contains client identifiers and stays inside St. Nicks.
2. Add Shareable\_Audit\_Log.txt. Replace each Client\_ID with the first 10 characters of a keyed hash from the install secret. Replace file names with Source A, Source B and so on. Only the internal log says which file each letter stands for.
3. Record who made each decision in both logs (5b adds reviewer names).

**Test it.** Scan the shareable log for every Client\_ID and file name in the batch. None should appear.

**Result.** Fully fixed.

### 4.6 Set machine rules with St. Nicks

These are not code changes. Agree them with Stephanie before the next real run.

1. Run Crosswalk on one named computer with BitLocker turned on.
2. Set that computer's screen to lock after 5 minutes or less.
3. Pick one outputs folder outside OneDrive. Make it the save dialog's starting folder.
4. Agree how long outputs are kept. Have the check stage list output files older than that, so the operator deletes them on time.

**Result.** Reduced. These are habits, and the tool can only prompt them.

## Phase 5a. Count every person

Rough effort is 4 to 6 days. These changes fix who gets counted in Goal 1 and Goal 2.

### 5.1 Count people separately from mapping them

**Problem.** Only rows that pass every check count as people. A client with no address, a New Jersey address, or an address Geosupport can't match is left out of Goal 1 unless a reviewer accepts them. In human services, those rows are often people without housing or people who just moved.

**Steps.**

1. Give every row two separate statuses. Countable means the row is a real person record. Mappable means the address passed and was geocoded.
2. Write the countable rule down. A row counts when it has a first and last name, has a Client\_ID or a date of birth, is not a summary row and is not a confirmed copy. The address plays no part.
3. Take the address checks (Address\_1, City, State, Zip and geocoding) off the counting gate. A row that fails only those checks is counted and listed as "Counted, not mapped" with its reason.
4. Accept any US state. Mark outside-NYC addresses "Outside NYC, not mapped" instead of failing them. Change only this check. Keep the jammed-address splitter NY-only, because that rule is what stops St being read as a state.
5. Keep the review stage for problems that block counting, like a missing name, a missing ID and DOB, an ID conflict or a duplicate. Address problems move to their own tab. Fixing them improves the map and never holds up the counts.
6. Run identity resolution over every countable row. **Check first** `_person_records`, which today takes only the clean side.
7. Assert two reconciliations instead of one. Counted plus not counted equals input rows. Mapped plus not mapped equals counted.
8. Show "Counted, no usable address" with its number on Results and on the printable summary.

**Test it.** Add proof rows for a client with no address, a client in Hoboken with ZIP 07030, and a client whose address Geosupport can't match. All three should count in Goal 1 and appear under "Counted, not mapped."

**Result.** Fully fixed.

### 5.2 Find people who moved

**Problem.** Date of birth is not in the default schema. Without it, every blocking key leans on address or ZIP. A person at a new address in a second system never gets compared with their old record, so they're counted twice. Even when they do share a block, a name match alone scores 56 points, below the 62-point line.

**Steps.**

1. Add Date\_of\_Birth to `DEFAULT_SCHEMA` as a date field that isn't required.
2. On the Map stage, flag any file with an unmatched column that looks like a birth date, and name the column. Look for header words like dob and birth, and values that parse as dates between 1900 and today.
3. Add one blocking key that needs no address, the surname plus the given name's nickname group. **Check first** the shape `blocking_keys` returns, then add something like this.

```python
for s in surname_tokens(rec.last):
    for g in given_keys(rec.first):
        keys.add(("surname+given", s, g))
```

4. Add a bonus for rare names. Count each surname and given-group pair across the batch. When a pair appears three times or fewer, add points so a name-only match reaches the proposal list. Start at 8 points. Set the real number from the calibration in 5.5. Common names like Maria Rodriguez stay below the line.
5. Show DOB coverage on Results. For example, "Date of birth on 62% of counted rows. Without it, people who moved between systems may be counted twice."
6. Ask Stephanie which systems can include date of birth in their exports, and turn it on for each one.

**Test it.** Add proof rows for one person in two files at different addresses. With DOB, the pair should join or be proposed. With a rare name and no DOB, it should be proposed. With a common name and no DOB, the records stay apart and the summary warns about it.

**Result.** Reduced. With DOB in every file, most people who moved get matched. Without it, some movers with common names will still be counted twice. Only better data fixes that.

### 5.3 Gate the sample reference and record the Geosupport release

**Problem.** Without Geosupport, the tool falls back to a small sample reference file. It says so on the check stage but still produces districts and exports. The Geosupport release in use is not recorded, and district lines change after redistricting.

**Steps.**

1. When the sample reference is active, put PRACTICE in every output file name. Put "Practice run, not for reporting" at the top of the printable summary.
2. Block Map\_Counts, Map\_Points and the district columns in practice runs. Counting still works, since 5.1 no longer depends on geocoding.
3. Record the Geosupport release, for example 25C, on the check stage, in both audit logs and on the printable summary. **Check first** how your Geosupport wrapper reports its version.
4. Warn when the release is more than a year old.

**Test it.** Rename the Geosupport folder and run the samples. Every output name should say PRACTICE, and the district outputs should be blocked.

**Result.** Fully fixed.

## Phase 5b. Remember decisions and prove the matching

Rough effort is 5 to 8 days of code, plus about two days of St. Nicks staff time for the labeling in 5.6.

### 5.4 Keep a saved crosswalk

**Problem.** The tool keeps no memory between runs. Sessions are deleted after seven days. Set-ups don't hold identity or review decisions. Record IDs are built from the file range and row number, so a re-export breaks them. Every quarter someone decides the same pairs again, and every master ID changes.

**Steps.**

1. Make an install secret once, with `secrets.token_bytes(32)`. Protect it with DPAPI (4.2) and save it as `%LOCALAPPDATA%\Crosswalk\key.bin`. Back it up with a passphrase somewhere Stephanie controls. Losing it orphans the crosswalk.
2. Give every record a key that survives re-exports, built from the source system and the Client\_ID. I tested that spacing and case differences give the same key.

```python
import hmac, hashlib

def record_key(secret: bytes, system: str, client_id: str) -> str:
    msg = f"{system.strip().lower()}|{client_id.strip()}".encode()
    return hmac.new(secret, msg, hashlib.sha256).hexdigest()
```

3. For a row with no Client\_ID, build the key from the system, the folded name and the DOB. With no DOB either, add the street and ZIP. Two identical rows then share a key, which is fine, since they are copies.
4. Create crosswalk.db, a SQLite file in the same folder. It holds keys, IDs and decisions, never names or addresses.

```sql
CREATE TABLE person (
  master_id  TEXT PRIMARY KEY,
  created_at TEXT NOT NULL
);
CREATE TABLE record_link (
  record_key TEXT PRIMARY KEY,
  master_id  TEXT NOT NULL REFERENCES person(master_id),
  how        TEXT NOT NULL,   -- same-id, four-facts or reviewer
  decided_by TEXT,
  decided_at TEXT NOT NULL
);
CREATE TABLE pair_verdict (
  key_a      TEXT NOT NULL,   -- the smaller key of the pair
  key_b      TEXT NOT NULL,
  verdict    TEXT NOT NULL CHECK (verdict IN ('same', 'different')),
  decided_by TEXT NOT NULL,
  decided_at TEXT NOT NULL,
  PRIMARY KEY (key_a, key_b)
);
CREATE TABLE merged_into (
  old_master TEXT PRIMARY KEY,
  new_master TEXT NOT NULL,
  merged_at  TEXT NOT NULL
);
```

5. Change `identity.resolve` to start from what is saved.
   1. Load record\_link. Records whose key is known start in their saved master's group.
   2. Replay every "same" verdict as a join. Treat every "different" verdict as a block, so that pair is never proposed again.
   3. Score only the pairs with no saved verdict.
   4. When one group ends up holding two saved masters, keep the older ID and write the other to merged\_into.
   5. Give each new person a new ID, such as CW0004821. Never reuse an ID.
   6. Write every new link and verdict back when the run finishes.
6. Key review and duplicate decisions by record key too. Add the record key beside the existing row ID, and use it for anything saved between runs. Keep the row ID for lookups within a run, since two copies can share one record key.
7. Carry master IDs into the exports, so a person keeps one ID in every quarter's files.
8. Report any period's Goal 1 as the distinct master IDs among that period's records. A fiscal year then rolls up from quarterly runs.

**Test it.** Run a set of files and decide every proposal. Shuffle the rows, add five new people, and run again. Only pairs involving the new people should be open. Every earlier master ID should be unchanged.

**Result.** Fully fixed. This changes the "no client data on disk" rule. The crosswalk holds keyed hashes and IDs, not names, but St. Nicks should approve it first (Phase 7).

### 5.5 Make resume safe

**Problem.** A resumed session replays decisions onto the re-added files by row number. If a re-export has the same row count and a different sort order, old decisions land on different people.

**Steps.**

1. Store the SHA-256 of each source file in the session, using `hashlib.sha256(data).hexdigest()`.
2. On resume, compare the hashes. When a file differs, skip its row-keyed decisions and name the file that changed.
3. After 5.4, decisions are keyed by record. A changed file then loses only the decisions for records that are truly gone.

**Test it.** Save a session, sort one source file by last name, and resume. The tool should skip that file's decisions and say why.

**Result.** Fully fixed.

### 5.6 Calibrate the matching against real pairs

**Problem.** More than 1,200 checks cover the rest of the tool, but the identity weights have never been tested on real data. The deck promises "two numbers you can stand behind." Today that holds for the arithmetic, not the matching.

**Steps.**

1. Run the real batch with the proposal line lowered to 40 points so near misses show up. Don't report from this run.
2. Draw about 400 pairs spread across score bands, roughly 100 each from 40 to 61, 62 to 79, 80 to 99, and 100 or more.
3. Have two St. Nicks staff label each pair as same, different or unsure, working apart. They can check the source systems. Do this on the Crosswalk computer, since the pairs are client data.
4. Settle disagreements together and drop pairs that stay unsure.
5. For each band, measure how often "same" was right. The 40 to 61 band shows how many true matches the 62 line misses.
6. Ask staff for about 50 people they know appear in two systems. Check whether each pair was compared at all. That measures what blocking misses.
7. Set the proposal line so it catches at least 98% of true matches. Keep automatic joins only where at least 99.5% were right. Agree the final targets with Stephanie.
8. Save the labeled pairs as record keys plus score features, with no names. Make them a regression test, so a weight change that hurts accuracy fails the build.
9. Print the measured figures in a methods note on the printable summary.
10. Repeat the labeling once a year and whenever a new source system joins.

**Test it.** The regression test from step 8 passes, and the summary shows the measured figures.

**Result.** Fully fixed as a measurement. The weights can only be as good as the labels.

### 5.7 Record who decided and slow down bulk accepts

**Problem.** "Nothing merged on a guess" moves the guessing to a person. That person is a non-engineer who does this a few times a year, with "Accept all as they are" on almost every group. The audit shows what was accepted but not who accepted it.

**Steps.**

1. Ask for the reviewer's name when review starts. Default to the Windows login from `getpass.getuser()`. Store it on every decision and in both audit logs.
2. Before "Accept all as they are" runs, show five random rows from the group. Ask the reviewer to type the row count and a short reason.
3. Send any bulk accept over 200 rows, and any identity group that joins more than 5 records, to a second reviewer. The second reviewer signs off by name.
4. Add a "Decisions by reviewer" table to the internal audit, with counts by decision type.

**Test it.** Run a bulk accept on a practice batch. The audit should show the reviewer's name, the typed count and the reason.

**Result.** Reduced. The tool can make judgment calls slower and traceable. It can't make them right.

## Phase 6. Make the docs match the product

Rough effort is 1 day, done after the fixes each claim depends on. A funder, auditor or data partner will read every hard rule as a promise. Each one needs to be true and backed by a test.

**Steps.**

1. Create docs/claims.yaml. List each promise once, with the name of the test that proves it.
2. Have make\_docs.py pull the hard rules from that file into TECHNICAL.md, the user guide, the AI description and the deck. The two docs that disagree today then can't drift apart again.
3. Extend test\_docs.py so it fails when a claim has no test, or names a test that doesn't exist.
4. Rename Secure\_Audit\_Log everywhere, including help.json and the screenshots.
5. Replace each claim below once its fix ships.

| Claim today | Replace with | Proved by |
| --- | --- | --- |
| Offline, except a one-time package install | Runs fully offline. The installer carries everything it needs. | Offline VM test (3.2) |
| Nothing is written to disk until you download | Client data is written only to files you save. The crosswalk holds keys and IDs. Sessions are encrypted to your Windows login. | A scan of the app folders for a test name finds nothing (1.3, 4.2) |
| Everything runs on this computer, and nothing leaves it | Everything runs on this computer. Files leave only when someone saves and shares them. | Save-dialog warning test (2.3) |
| The audit trail is PII-safe and safe to share | The internal audit contains client IDs and stays inside St. Nicks. The shareable audit contains none. | Shareable-log scan (4.5) |
| No per-value editing | Values change only through a signed corrections file or a fill from the row's own address. Every change is recorded. | Corrections refusal tests (4.3) |
| Two versions of the auto-join rule | Records join automatically only on the same ID within one system, or when DOB, surname, given name and address all agree. | test\_docs compares the sentence with `_is_auto` |
| No stored point is a client's front door | Map\_Counts carries counts only. Map\_Points moves each point by a secret fixed offset and stays inside St. Nicks. | Shuffled-rows jitter test (4.4) |
| clean + review + set aside = input | Counted plus not counted equals input. Mapped plus not mapped equals counted. | Reconciliation asserts (5.1) |
| Decisions are stored and replayed, so the work is done once | True as written, once the crosswalk exists. | Re-run test (5.4) |
| Two numbers you can stand behind | Add the measured precision and recall, the number of labeled pairs, and the date. | Calibration regression test (5.6) |
| Nothing merged on a guess | Keep it, and add that the audit names who made each call. | Reviewer audit test (5.7) |

**Result.** Fully fixed, and it stays fixed because the build checks it.

## Phase 7. Governance checks with St. Nicks before the next real run

This takes a few meetings, and it can stop a real run on its own. None of it is code. I'm not a lawyer, so St. Nicks' counsel or compliance lead makes these calls.

**Steps.**

1. List every source system and the agreement that governs its export. That likely means the DYCD participant system, ETO, property management and each partner spreadsheet. Ask Stephanie who owns each one.
2. Ask each owner three questions. May these records be linked with records from other systems? For what purpose? How long may the linked result be kept?
3. Check whether any program's data carries extra rules. Health records can fall under HIPAA. Substance use treatment records can fall under 42 CFR Part 2. Federal grant rules limit sharing client information from domestic violence services. Where any of these apply, leave those files out or get written approval first.
4. Get written approval for the saved crosswalk in 5.4. It is new, and it keeps keyed identifiers from one run to the next.
5. Write a one-page data-handling note. It names who runs Crosswalk, on which computer, where outputs go, who receives them and when they are deleted. Review it once a year.
6. Decide who sees each output. For example, program directors get Map\_Counts and the printable summary. Only the operator and one supervisor see Unique\_Clients and the internal audit.

**Result.** Outside the tool. Crosswalk can record the answers, but it can't give them.

## Scorecard

Of the 24 issues, 18 can be fully fixed, 5 can only be reduced, and 1 sits outside the tool. Use the Progress column to track the work.

| Issue | Fixed in | How to test | Outcome | Progress |
| --- | --- | --- | --- | --- |
| Any website can send requests to the server | 1.1, 1.2, then 2.2 | `curl -X POST .../api/reset` gets 403; after Phase 2, netstat shows no new port | Fully fixed | Not started |
| DNS rebinding lets a hostile page read exports | 1.2, then 2.2 | A request with `Host: evil.example` gets 400 | Fully fixed | Not started |
| Other Windows accounts can reach the server | 1.1, then 2.2 | netstat shows no new listening port | Fully fixed | Not started |
| Launcher trusts or kills whatever holds the port | 1.5, then 2.4 | A server already on 8765 keeps running | Fully fixed | Not started |
| Client names end up in launch-log.txt | 1.3 | A searched test name never appears in the log | Fully fixed | Not started |
| run.bat puts Streamlit on the office network | 1.4 | Build test finds no run.bat or Streamlit | Fully fixed | Not started |
| First launch installs packages from PyPI | 3.1, 3.2 | Offline VM run passes; pip-audit gate is clean | Fully fixed | Not started |
| VBScript launcher | 3.3 | No .vbs files in the build | Fully fixed | Not started |
| Unsigned build | 3.4 | Signature tab shows your business name | Fully fixed | Not started |
| Sensitive columns stay loaded; SSN-shaped IDs pass | 4.1 | Proof sheet drops the SSN column and blocks the SSN-shaped ID | Fully fixed | Not started |
| Sessions saved unencrypted in synced folders | 4.2 | Resume from another Windows account fails | Fully fixed | Not started |
| Review file carries full rows; corrections are unsigned | 4.3 | Foreign or off-target corrections are refused | Reduced | Not started |
| Jitter protects nothing and can be reversed | 4.4 | Shuffled rows give identical Map\_Points; seed setting is gone | Reduced | Not started |
| Audit log is called safe to share | 4.5 | No Client\_ID or file name in the shareable log | Fully fixed | Not started |
| Outputs land on shared or synced machines | 2.3, 4.6 | Save dialog warns on OneDrive; machine rules are signed off | Reduced | Not started |
| Address quality decides who is counted | 5.1 | No-address, New Jersey and unmatched rows all count | Fully fixed | Not started |
| People who moved are counted twice without DOB | 5.2 | Mover proof rows join or are proposed | Reduced | Not started |
| Practice reference yields real-looking districts | 5.3 | Without Geosupport, every output says PRACTICE | Fully fixed | Not started |
| No memory between runs; master IDs change | 5.4 | Shuffled re-run keeps every master ID | Fully fixed | Not started |
| Resume can pin decisions on the wrong people | 5.5 | Resume after sorting a file skips its decisions | Fully fixed | Not started |
| Matching weights have never been measured | 5.6 | Calibration regression test passes | Fully fixed | Not started |
| Bulk accepts with no named reviewer | 5.7 | Audit shows reviewer, typed count and reason | Reduced | Not started |
| Docs promise more than the product does | 6 | test\_docs fails on any claim without a test | Fully fixed | Not started |
| Linking systems may exceed data agreements | 7 | Written approvals are on file | Outside the tool | Not started |

## Sources

- The Crosswalk docs you provided, meaning the AI description, TECHNICAL.md, the user guide and the walkthrough deck.
- Package source code, installed and read for this plan. FastAPI 0.141.1, Starlette 1.7.0 (TrustedHostMiddleware and TestClient), uvicorn 0.54.0 (access log written to stdout), pywebview 6.2.1 (create\_window, start, create\_file\_dialog and bridge threading), Streamlit 1.64.0 (defaults for server.address and browser.gatherUsageStats) and msoffcrypto-tool 6.0.0 (Excel encryption).
- [VBScript deprecation: timelines and next steps](https://techcommunity.microsoft.com/blog/windows-itpro-blog/vbscript-deprecation-timelines-and-next-steps/4148301), Microsoft Windows IT Pro Blog. Search found it, but the page body didn't load here.
- Not verified here. DPAPI through pywin32 is Windows only, and WebView2's 2 MB limit on pages passed as a string needs a Windows machine. Check both before relying on them.
