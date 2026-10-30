"""Layer: in-process audit hook (H1, H2, SPEC 12.1 layer 4). Each case runs in a fresh interpreter because audit hooks can't be removed.

The first nine tests are the research's (R6). The rest cover what M00 adds.
"""
import pytest

from tests.support.guarded import run_guarded

pytestmark = pytest.mark.claim("CL-OFFLINE-01")


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


# Added in M00

def test_first_import_of_ai_sdks_raises():
    """H2: the guard refuses AI SDK imports even if one were installed. The names don't need to exist for the import event to fire."""
    r = run_guarded("""
        for name in ('openai', 'anthropic', 'transformers', 'torch', 'onnxruntime', 'ollama', 'litellm', 'google.generativeai'):
            attempt('import ' + name, lambda n=name: exec('import ' + n))
    """)
    assert set(r.values()) == {"blocked"}, r


def test_allowed_dll_names_match_bare_names_only():
    """SPEC 12.1: DPAPI's crypt32 is loaded by bare name, which never matches a path prefix."""
    r = run_guarded("""
        bs = chr(92)
        attempt('crypt32', lambda: sys.audit('ctypes.dlopen', 'crypt32'))
        attempt('CRYPT32', lambda: sys.audit('ctypes.dlopen', 'CRYPT32'))
        attempt('crypt32x', lambda: sys.audit('ctypes.dlopen', 'crypt32x'))
        attempt('path', lambda: sys.audit('ctypes.dlopen', 'C:' + bs + 'Windows' + bs + 'System32' + bs + 'crypt32'))
        attempt('slash path', lambda: sys.audit('ctypes.dlopen', '/usr/lib/crypt32'))
        attempt('listed symbol', lambda: sys.audit('ctypes.dlsym', None, 'CryptProtectData'))
        attempt('unlisted symbol', lambda: sys.audit('ctypes.dlsym', None, 'CryptEncrypt'))
    """, install="offline_guard.install(allowed_dll_names=['crypt32'], allowed_symbols=['CryptProtectData'])")
    assert r == {
        "crypt32": "NOT BLOCKED", "CRYPT32": "NOT BLOCKED", "crypt32x": "blocked", "path": "blocked", "slash path": "blocked",
        "listed symbol": "NOT BLOCKED", "unlisted symbol": "blocked",
    }, r


def test_install_returns_and_logs_violations():
    r = run_guarded("""
        logged = []
        v2 = offline_guard.install(log=logged.append)
        out['empty at start'] = (v2 == [])
        attempt('socket', lambda: exec('import socket'))
        out['returned'] = v2
        out['logged'] = logged
    """, install="[]")
    assert r["empty at start"] is True
    assert r["socket"] == "blocked"
    assert r["returned"] == ["import of socket"] and r["logged"] == ["import of socket"], r


def test_install_for_app_merges_the_config_constants():
    r = run_guarded("""
        attempt('crypt32', lambda: sys.audit('ctypes.dlopen', 'crypt32'))
        attempt('kernel32', lambda: sys.audit('ctypes.dlopen', 'kernel32'))
        attempt('other dll', lambda: sys.audit('ctypes.dlopen', 'ws2_32'))
        for s in ('CryptProtectData', 'CryptUnprotectData', 'LocalFree', 'NYCgeo', 'geo'):
            attempt('sym ' + s, lambda s=s: sys.audit('ctypes.dlsym', None, s))
        attempt('sym other', lambda: sys.audit('ctypes.dlsym', None, 'connect'))
        out['installed'] = guard.INSTALLED
    """, install="guard.install_for_app()")
    assert r.pop("installed") is True
    assert r.pop("other dll") == "blocked" and r.pop("sym other") == "blocked", r
    assert set(r.values()) == {"NOT BLOCKED"}, r


def test_guard_is_not_installed_in_the_pytest_process():
    """pytest's plugins may need sockets, so only subprocesses install the guard. Importing the package installs nothing."""
    import wholecount.guard as guard

    assert guard.INSTALLED is False
