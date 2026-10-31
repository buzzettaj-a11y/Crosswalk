"""offline_guard: fail-closed audit hook. Import and call install() as the first statement of the app.

Defense in depth, NOT a sandbox (see docs.python.org/3/library/sys.html#sys.addaudithook).
Taken from docs/research/offline-enforcement.md R2. The deny lists are hoisted to module level so tests can read them,
and two things are added: allowed_dll_names (SPEC 12.1, DPAPI's crypt32) and the open-file allowance (SPEC 12.6).
"""
import ntpath as _ntpath
import os as _os
import sys
import threading

INSTALLED = False

DENY_PREFIXES = ("socket.", "urllib.", "http.client.", "ftplib.", "smtplib.", "poplib.", "imaplib.", "telnetlib.", "webbrowser.")
DENY_EXACT = frozenset({
    "subprocess.Popen", "os.system", "os.exec", "os.spawn", "os.posix_spawn", "os.fork", "os.forkpty",
    "os.startfile", "os.startfile/2", "winreg.ConnectRegistry",
    "gc.get_objects", "gc.get_referrers", "gc.get_referents",
    "ctypes.addressof", "ctypes.string_at", "ctypes.wstring_at", "ctypes.cdata", "ctypes.cdata/buffer",
    "ctypes.set_exception", "ctypes.call_function",
    "_winapi.CreateProcess",     # Windows-only event behind subprocess; listed in the CPython audit-events table; not exercised on Linux
})
DENY_MODULES = frozenset({
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
# through importlib.import_module(), so install() also makes them unimportable. (A None entry in sys.modules makes every later import raise ImportError.)
_SUBINTERPRETER_MODULES = ("_xxsubinterpreters", "_interpreters", "_interpchannels", "_interpqueues", "_xxinterpchannels", "_xxinterpqueues")

# The two events one real os.startfile(path, "open") call raises (SPEC 12.6).
STARTFILE_EVENTS = ("os.startfile", "os.startfile/2")


class OfflineViolation(Exception):
    """Raised before a forbidden operation happens. The operation itself is aborted whether or not callers swallow this."""


class OfflineImportViolation(OfflineViolation, ImportError):
    """A denied import. It is an ImportError so that optional-import probes (try: import x / except ImportError) fall back instead of crashing,
    for example PySide6/__init__.py on Windows, which imports QtNetwork inside try/except ImportError when a PySide6/openssl folder exists."""


def _is_remote_path(p):
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


class _OpenFileAllowance:
    """One registered path for one os.startfile(path, "open") call. The call raises both STARTFILE_EVENTS, and each passes once.

    The path module is the one install() was given (ntpath unless a test injects another), so paths compare the way Windows does.
    """

    def __init__(self):
        self._lock = threading.Lock()
        self._path_mod = None
        self._path = None
        self._seen = set()

    def set_path_module(self, mod):
        with self._lock:
            self._path_mod = mod

    def _nt(self):
        return self._path_mod or _ntpath

    def _norm(self, nt, p):
        return nt.normcase(nt.abspath(p))

    def register(self, path):
        if isinstance(path, bytes) or not isinstance(path, str):
            try:
                path = _os.fsdecode(_os.fspath(path))
            except TypeError:
                raise ValueError("open-file allowance needs a path") from None
        if "://" in path:
            raise ValueError("open-file allowance refuses a URL")
        if _is_remote_path(path):
            raise ValueError("open-file allowance refuses a UNC or WebDAV path")
        with self._lock:
            nt = self._nt()
            if not (nt.isabs(path) or _os.path.isabs(path)):
                raise ValueError("open-file allowance needs an absolute path")
            self._path = self._norm(nt, path)
            self._seen = set()

    def permits(self, event, args):
        """True if this event is the registered call. Spends that event only when it permits it; a refusal changes nothing."""
        if len(args) < 2 or args[1] != "open":
            return False
        try:
            p = _os.fsdecode(_os.fspath(args[0]))
        except TypeError:
            return False
        with self._lock:
            if self._path is None or event in self._seen:
                return False
            if self._norm(self._nt(), p) != self._path:
                return False
            self._seen.add(event)
            if self._seen.issuperset(STARTFILE_EVENTS):
                self._path = None
                self._seen = set()
            return True


_allowance = _OpenFileAllowance()


def allow_open_file(path):
    """Let one os.startfile(path, "open") call through the guard (SPEC 12.6). Only wholecount/ui/shell.py calls this.

    Raises ValueError for a relative path, a URL, or a UNC or WebDAV path. Registering again replaces an unspent allowance.
    """
    _allowance.register(path)


def install(allowed_dll_prefixes=(), allowed_symbols=(), log=None, ntpath_mod=None, allowed_dll_names=()):
    global INSTALLED
    nt = ntpath_mod or _ntpath
    _allowance.set_path_module(nt)
    violations = []
    deny_prefixes = DENY_PREFIXES
    deny_exact = DENY_EXACT
    deny_modules = DENY_MODULES
    for _m in _SUBINTERPRETER_MODULES:
        sys.modules.setdefault(_m, None)
    dll_prefixes = tuple(nt.normcase(nt.abspath(p)) for p in allowed_dll_prefixes)
    dll_names = frozenset(n.lower() for n in allowed_dll_names)
    symbols = frozenset(allowed_symbols)
    is_remote_path = _is_remote_path
    allowance = _allowance

    def deny(why, exc=OfflineViolation):
        violations.append(why)
        if log is not None:
            log(why)
        raise exc(why)

    def dll_name_allowed(name):
        # A bare name only: no directory part, compared case-insensitively and exactly.
        return name.lower() in dll_names and "/" not in name and "\\" not in name

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
        if event in STARTFILE_EVENTS and allowance.permits(event, args):
            return
        if event.startswith(deny_prefixes) or event in deny_exact:
            deny(event)
        if event == "ctypes.dlopen":
            name = args[0]
            if name is None:
                return      # POSIX only: `import ctypes` opens the main program as ctypes.pythonapi. Its symbols stay gated by the dlsym allowlist.
            if isinstance(name, str) and dll_name_allowed(name):
                return
            if not dll_prefixes or not isinstance(name, str) or not nt.normcase(nt.abspath(name)).startswith(dll_prefixes):
                deny(f"ctypes.dlopen {name!r}")
        elif event in ("ctypes.dlsym", "ctypes.dlsym/handle"):
            if args[1] not in symbols:
                deny(f"ctypes.dlsym {args[1]!r}")

    sys.addaudithook(hook)
    INSTALLED = True
    return violations
