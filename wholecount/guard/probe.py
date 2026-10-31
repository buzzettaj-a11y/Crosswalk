"""Probes the self-check uses to show the guard is working (M14). They live in the guard package, which the static scan
exempts because it has to name what it forbids. Each one raises the audit event the guard should refuse."""
import sys

# A network path on the documentation range (RFC 5737). Never reached: the guard refuses the open before Windows sees it.
NETWORK_PATH = r"\\192.0.2.1\share\x.txt"


def socket_connect():
    sys.audit("socket.connect", None, ("192.0.2.1", 80))


def open_network_path():
    open(NETWORK_PATH, "rb")
