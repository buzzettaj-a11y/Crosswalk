"""
Crosswalk launcher.

Started by double-clicking Crosswalk.vbs on Windows, Crosswalk.command on a
Mac, or Crosswalk.sh on Linux. It is written so that the person launching the
tool never needs a terminal and never has to read a stack trace.

It does five things, and explains itself in plain words if any of them fail:

  1. checks the Python it is running on is new enough
  2. installs what the tool needs, once, on the first run only
  3. picks a free port, so a second copy or another program does not collide
  4. starts the server and waits until it is actually answering
  5. opens the browser at the right address

Anything that goes wrong is shown in a message box and written to
launch-log.txt next to this file, so a problem can be reported without needing
to reproduce it.
"""
from __future__ import annotations

import json
import os
import socket
import subprocess
import sys
import threading
import time
import urllib.error
import urllib.request
import webbrowser

HERE = os.path.dirname(os.path.abspath(__file__))


class _LogStream:
    """
    Somewhere for output to go when there is no console.

    Started by double-clicking, the tool runs under pythonw, which gives it no
    standard output at all: sys.stdout is None. Any library that reaches for it
    then fails, and uvicorn does exactly that when it sets up its own logging.
    Sending that output to the log file keeps those libraries working and keeps
    anything they say where it can be read afterward.
    """

    def __init__(self, path):
        self._path = path

    def write(self, text):
        """Write to the log file, standing in for a console that is not there."""
        if not text:
            return
        try:
            with open(self._path, "a", encoding="utf-8") as fh:
                fh.write(text)
        except OSError:
            pass

    def flush(self):
        """Nothing to flush; the log is written line by line."""
        pass

    def isatty(self):
        """Never a terminal, so no color codes."""
        return False          # never a terminal, so no color codes

    def fileno(self):
        """There is no file descriptor when running without a console."""
        raise OSError("no file descriptor when running without a console")


def _ensure_streams(path):
    """Give the process an output stream when it was started without one."""
    if sys.stdout is None:
        sys.stdout = _LogStream(path)
    if sys.stderr is None:
        sys.stderr = _LogStream(path)
LOG = os.path.join(HERE, "launch-log.txt")
READY_MARK = os.path.join(HERE, ".installed")
PID_FILE = os.path.join(HERE, "crosswalk.pid")
GRACE_AFTER_CLOSE = 15      # seconds to wait for a closed window to come back
IDLE_LIMIT = 45             # seconds of silence before stopping regardless.
                            # The page checks in every 10 seconds, so this is
                            # four missed check-ins: long enough to survive a
                            # slow reload, short enough that a closed browser
                            # does not leave the tool running for long.
NEEDED = ["fastapi", "uvicorn", "pandas", "numpy", "openpyxl", "lxml",
          "thefuzz", "multipart"]
MIN_PYTHON = (3, 9)


_ensure_streams(os.path.join(HERE, "launch-log.txt"))


def log(message):
    """Write one line to the launch log, and to the screen when there is one."""
    line = f"{time.strftime('%Y-%m-%d %H:%M:%S')}  {message}"
    try:
        with open(LOG, "a", encoding="utf-8") as fh:
            fh.write(line + "\n")
    except OSError:
        pass
    # Only echo to the screen when there is a real one. Without a console the
    # stream already points at this same file, and printing would double it.
    if not isinstance(sys.stdout, _LogStream):
        try:
            print(line, flush=True)
        except Exception:
            pass


def tell(title, message, is_error=True):
    """
    Say something to a person who has no terminal open.

    A native message box is used where one is available. Everything is written
    to the log as well, so the words are recoverable afterward either way.
    """
    log(f"{title}: {message}")
    try:
        if sys.platform.startswith("win"):
            import ctypes
            flags = 0x10 if is_error else 0x40      # error icon or info icon
            ctypes.windll.user32.MessageBoxW(0, message, title, flags)
            return
        if sys.platform == "darwin":
            subprocess.run(
                ["osascript", "-e",
                 f'display dialog {json.dumps(message)} with title '
                 f'{json.dumps(title)} buttons {{"OK"}} default button 1'],
                check=False, capture_output=True)
            return
    except Exception:
        pass
    try:                                            # a last resort that is still a window
        import tkinter
        from tkinter import messagebox
        root = tkinter.Tk()
        root.withdraw()
        (messagebox.showerror if is_error else messagebox.showinfo)(title, message)
        root.destroy()
    except Exception:
        pass


def check_python():
    """Refuse to start on a Python too old to run the tool, saying which to install."""
    if sys.version_info < MIN_PYTHON:
        tell("Crosswalk cannot start",
             "Crosswalk needs Python "
             f"{MIN_PYTHON[0]}.{MIN_PYTHON[1]} or newer, and this computer is "
             f"running {sys.version.split()[0]}.\n\n"
             "Install a newer Python from python.org, tick 'Add python.exe to "
             "PATH' during setup, then try again.")
        sys.exit(1)


def missing_packages():
    """The packages the tool needs that are not installed."""
    missing = []
    for name in NEEDED:
        try:
            __import__(name)
        except Exception:
            missing.append(name)
    return missing


def install_requirements():
    """Install what is missing, once. Later runs skip this entirely."""
    missing = missing_packages()
    if not missing and os.path.exists(READY_MARK):
        return
    if not missing:
        open(READY_MARK, "w").close()
        return

    log(f"first run, installing: {', '.join(missing)}")
    req = os.path.join(HERE, "requirements.txt")
    cmd = [sys.executable, "-m", "pip", "install", "--disable-pip-version-check",
           "-r", req] if os.path.exists(req) else \
          [sys.executable, "-m", "pip", "install", "--disable-pip-version-check",
           *missing]
    try:
        out = subprocess.run(cmd, capture_output=True, text=True, timeout=900)
        log(out.stdout[-4000:])
        if out.returncode != 0:
            log(out.stderr[-4000:])
            tell("Crosswalk could not finish setting up",
                 "The first run needs to download a few components, and that "
                 "did not finish.\n\n"
                 "The most likely reason is no internet connection on this "
                 "computer. This is the only step that needs one; everything "
                 "afterward works offline.\n\n"
                 f"The details were written to:\n{LOG}")
            sys.exit(1)
    except subprocess.TimeoutExpired:
        tell("Crosswalk could not finish setting up",
             "Setting up took too long and was stopped. Check the internet "
             "connection and try again.")
        sys.exit(1)

    still = missing_packages()
    if still:
        tell("Crosswalk could not finish setting up",
             "Some components are still missing after setup: "
             f"{', '.join(still)}.\n\nThe details were written to:\n{LOG}")
        sys.exit(1)
    open(READY_MARK, "w").close()
    log("setup finished")


def free_port(preferred=8765):
    """The usual port when it is free, otherwise any port that is."""
    for port in [preferred] + list(range(8766, 8800)):
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            try:
                s.bind(("127.0.0.1", port))
                return port
            except OSError:
                continue
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.bind(("127.0.0.1", 0))
        return s.getsockname()[1]


def already_running(port):
    """
    The version of the copy answering on this port, "unknown" for a copy too
    old to say, or None when nothing is there.
    """
    try:
        with urllib.request.urlopen(f"http://127.0.0.1:{port}/api/alive",
                                    timeout=1.5) as r:
            if r.status != 200:
                return None
            try:
                return json.loads(r.read().decode("utf-8")).get("version") or "unknown"
            except Exception:
                return "unknown"
    except Exception:
        return None


def _pids_listening_on(port):
    """Process ids listening on a local TCP port, from /proc on Linux."""
    pids = set()
    try:
        want = f"{port:04X}"
        inodes = set()
        with open("/proc/net/tcp") as fh:
            for line in fh.readlines()[1:]:
                parts = line.split()
                if parts[1].endswith(":" + want) and parts[3] == "0A":
                    inodes.add(parts[9])
        if not inodes:
            return pids
        for pid in os.listdir("/proc"):
            if not pid.isdigit():
                continue
            try:
                for fd in os.listdir(f"/proc/{pid}/fd"):
                    link = os.readlink(f"/proc/{pid}/fd/{fd}")
                    if link.startswith("socket:[") and link[8:-1] in inodes:
                        pids.add(pid)
            except OSError:
                continue
    except OSError:
        pass
    return pids


def stop_whatever_holds(port):
    """
    Stop the process listening on this port, whatever it is.

    Used when an older copy of the tool is still running: opening that one
    instead of this one silently hands the person the old version, which is
    what happened when an old folder could not be deleted. The polite request
    is tried first; an old copy ignores it, so the process is then found by
    its port and ended.
    """
    try:
        req = urllib.request.Request(f"http://127.0.0.1:{port}/api/quit",
                                     data=b"{}", method="POST",
                                     headers={"Content-Type": "application/json"})
        urllib.request.urlopen(req, timeout=2)
    except Exception:
        pass
    for _ in range(12):
        if already_running(port) is None:
            return True
        time.sleep(0.25)
    try:
        if sys.platform.startswith("win"):
            out = subprocess.run(["netstat", "-ano", "-p", "tcp"],
                                 capture_output=True, text=True, timeout=10).stdout
            pids = {line.split()[-1] for line in out.splitlines()
                    if f"127.0.0.1:{port}" in line and "LISTENING" in line}
            for pid in pids:
                subprocess.run(["taskkill", "/PID", pid, "/F"],
                               capture_output=True, timeout=10)
        else:
            pids = set()
            # lsof where present, otherwise read the listening socket's owner
            # from /proc, which needs no extra tool
            try:
                out = subprocess.run(["lsof", "-ti", f"tcp:{port}"],
                                     capture_output=True, text=True,
                                     timeout=10).stdout
                pids |= set(out.split())
            except Exception:
                pass
            if not pids:
                pids |= _pids_listening_on(port)
            for pid in pids:
                if pid != str(os.getpid()):
                    subprocess.run(["kill", pid], capture_output=True, timeout=10)
    except Exception as exc:
        log(f"could not stop the process on port {port}: {exc}")
    for _ in range(12):
        if already_running(port) is None:
            return True
        time.sleep(0.25)
    return False


def wait_until_ready(port, seconds=90):
    """Wait until the server answers, for up to the seconds given."""
    deadline = time.time() + seconds
    while time.time() < deadline:
        try:
            with urllib.request.urlopen(f"http://127.0.0.1:{port}/api/alive",
                                        timeout=2) as r:
                if r.status == 200:
                    return True
        except Exception:
            time.sleep(0.4)
    return False


def main():
    """Check, install once, pick a port, start the server, open the browser, and stay until the window is gone."""
    log("=" * 60)
    log(f"starting, python {sys.version.split()[0]} at {sys.executable}")
    os.chdir(HERE)
    check_python()

    # This exact version already running is simply opened again. Any other
    # copy, older or unknown, is stopped so that the one double-clicked is the
    # one that runs.
    running = already_running(8765)
    if running is not None:
        from crosswalk_server import VERSION as MINE
        if running == MINE:
            log("this version is already running, opening it")
            webbrowser.open("http://127.0.0.1:8765/")
            return
        log(f"a different copy is running (version {running}); stopping it "
            f"so this one ({MINE}) can start")
        if not stop_whatever_holds(8765):
            tell("Crosswalk cannot start",
                 "Another copy of Crosswalk is already running and could not "
                 "be stopped.\n\nOpen its folder and double-click Stop "
                 "Crosswalk, or end pythonw.exe in Task Manager, then try "
                 "again.")
            sys.exit(1)

    install_requirements()
    port = free_port()
    url = f"http://127.0.0.1:{port}/"
    log(f"serving on {url}")

    try:
        import uvicorn
        import crosswalk_server
    except Exception as exc:
        tell("Crosswalk could not start",
             "The tool's own files could not be loaded.\n\n"
             "Make sure the whole Crosswalk folder was copied, not just the "
             f"shortcut.\n\nDetails:\n{exc}\n\nWritten to:\n{LOG}")
        sys.exit(1)

    crosswalk_server.PORT = port
    # the idle clock starts now, so a browser that never opens cannot leave
    # the tool running in the background forever
    crosswalk_server.LAST_SEEN = time.time()
    # log_config=None stops uvicorn installing its own logging. Its default
    # setup asks whether the output is a terminal, which cannot be answered
    # when the tool was started without a console.
    config = uvicorn.Config(crosswalk_server.api, host="127.0.0.1",
                            port=port, log_level="warning", log_config=None,
                            access_log=False)
    server = uvicorn.Server(config)

    thread = threading.Thread(target=server.run, daemon=True)
    thread.start()

    if not wait_until_ready(port):
        tell("Crosswalk could not start",
             "The tool started but never began answering.\n\n"
             f"The details were written to:\n{LOG}")
        sys.exit(1)

    log("ready, opening the browser")
    try:
        with open(PID_FILE, "w") as fh:
            fh.write(str(os.getpid()))
    except OSError:
        pass
    webbrowser.open(url)

    # Stay alive until the tool is closed from inside it, or the window goes
    # away. A closing window says goodbye, and the tool stops shortly after
    # unless the window comes back, as it does on a reload. If the goodbye
    # never arrived, silence alone is enough after a few minutes.
    try:
        while not getattr(crosswalk_server, "SHUTDOWN", False):
            time.sleep(1)
            now = time.time()
            bye = getattr(crosswalk_server, "BYE_AT", 0)
            last = getattr(crosswalk_server, "LAST_SEEN", 0)
            if bye and now - bye > GRACE_AFTER_CLOSE:
                log("the window closed, stopping")
                break
            if last and now - last > IDLE_LIMIT:
                log("no window for a while, stopping")
                break
    except KeyboardInterrupt:
        pass
    try:
        os.remove(PID_FILE)
    except OSError:
        pass
    log("stopped")


if __name__ == "__main__":
    try:
        main()
    except SystemExit:
        raise
    except Exception as exc:                        # pragma: no cover
        import traceback
        log(traceback.format_exc())
        tell("Crosswalk stopped unexpectedly",
             f"{exc}\n\nThe details were written to:\n{LOG}")
        sys.exit(1)
