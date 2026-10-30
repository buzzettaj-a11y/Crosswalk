"""The open-file allowance (SPEC 12.6). One registered path gets one os.startfile(path, "open") call, and nothing else.

The events are raised with sys.audit, the way a real os.startfile raises them, so these run on Linux.
"""
import textwrap

import pytest

from tests.support.guarded import run_guarded

pytestmark = pytest.mark.claim("CL-OFFLINE-01")

CALL = """
def call(path, op='open'):
    sys.audit('os.startfile', path, op)
    sys.audit('os.startfile/2', path, op, None, None, 1)
"""


def test_no_allowance_denies_both_events():
    r = run_guarded("""
        attempt('startfile', lambda: sys.audit('os.startfile', '/data/clients.xlsx', 'open'))
        attempt('startfile/2', lambda: sys.audit('os.startfile/2', '/data/clients.xlsx', 'open', None, None, 1))
    """)
    assert r == {"startfile": "blocked", "startfile/2": "blocked"}, r


def test_allowance_passes_one_pair_then_denies_the_next():
    r = run_guarded(CALL + textwrap.dedent("""
        guard.allow_open_file('/data/clients.xlsx')
        attempt('first call', lambda: call('/data/clients.xlsx'))
        attempt('second call', lambda: call('/data/clients.xlsx'))
        attempt('second call, event 2 only', lambda: sys.audit('os.startfile/2', '/data/clients.xlsx', 'open', None, None, 1))
    """))
    assert r == {"first call": "NOT BLOCKED", "second call": "blocked", "second call, event 2 only": "blocked"}, r


def test_each_event_passes_once_within_the_pair():
    r = run_guarded("""
        guard.allow_open_file('/data/clients.xlsx')
        attempt('event 1', lambda: sys.audit('os.startfile', '/data/clients.xlsx', 'open'))
        attempt('event 1 again', lambda: sys.audit('os.startfile', '/data/clients.xlsx', 'open'))
        attempt('event 2', lambda: sys.audit('os.startfile/2', '/data/clients.xlsx', 'open', None, None, 1))
        attempt('event 2 again', lambda: sys.audit('os.startfile/2', '/data/clients.xlsx', 'open', None, None, 1))
    """)
    assert r == {"event 1": "NOT BLOCKED", "event 1 again": "blocked", "event 2": "NOT BLOCKED", "event 2 again": "blocked"}, r


def test_other_path_and_other_operation_are_denied_and_leave_the_allowance_usable():
    r = run_guarded(CALL + textwrap.dedent("""
        guard.allow_open_file('/data/clients.xlsx')
        attempt('other path', lambda: call('/data/other.xlsx'))
        attempt('print', lambda: call('/data/clients.xlsx', 'print'))
        attempt('no operation', lambda: sys.audit('os.startfile', '/data/clients.xlsx', None))
        attempt('registered path', lambda: call('/data/clients.xlsx'))
    """))
    assert r == {"other path": "blocked", "print": "blocked", "no operation": "blocked", "registered path": "NOT BLOCKED"}, r


# The last case is absolute, so only the URL rule refuses it.
@pytest.mark.parametrize("path", ["clients.xlsx", "data/clients.xlsx", "https://example.com/a.xlsx", r"\\server\share\a.xlsx",
                                  "//server/share/a.xlsx", r"\\host@SSL\DavWWWRoot\a.xlsx",
                                  "/files/https://example.com/a.xlsx"])
def test_allow_open_file_refuses_relative_url_unc_and_webdav_paths(path):
    r = run_guarded(f"""
        try:
            guard.allow_open_file({path!r})
            out['result'] = 'accepted'
        except ValueError:
            out['result'] = 'ValueError'
    """)
    assert r == {"result": "ValueError"}, r


def test_windows_paths_match_across_case_and_slashes():
    r = run_guarded(CALL + textwrap.dedent(r"""
        guard.allow_open_file(r'C:\Data\Clients.xlsx')
        attempt('case and slashes', lambda: call('c:/data/CLIENTS.XLSX'))
        guard.allow_open_file('c:/data/clients.xlsx')
        attempt('backslashes', lambda: call(r'C:\DATA\Clients.xlsx'))
        attempt('spent', lambda: call(r'C:\Data\Clients.xlsx'))
    """), install="offline_guard.install(ntpath_mod=__import__('ntpath'))")
    assert r == {"case and slashes": "NOT BLOCKED", "backslashes": "NOT BLOCKED", "spent": "blocked"}, r


def test_allowance_is_thread_safe():
    """Many threads race for one registered call. Exactly one pair of events gets through."""
    r = run_guarded("""
        import threading
        guard.allow_open_file('/data/clients.xlsx')
        passed = []
        def worker():
            for ev, args in (('os.startfile', ('/data/clients.xlsx', 'open')), ('os.startfile/2', ('/data/clients.xlsx', 'open', None, None, 1))):
                try:
                    sys.audit(ev, *args); passed.append(ev)
                except V:
                    pass
        ts = [threading.Thread(target=worker) for _ in range(16)]
        [t.start() for t in ts]; [t.join() for t in ts]
        out['passed'] = sorted(passed)
    """)
    assert r == {"passed": ["os.startfile", "os.startfile/2"]}, r
