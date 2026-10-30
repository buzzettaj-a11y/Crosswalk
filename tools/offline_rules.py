"""Single source of truth for what 'offline' means. Imported by the tests and by CI scripts.

Taken from docs/research/offline-enforcement.md R6. Adding a dependency needs Joe's approval and an edit here in the same change.
"""
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

# Standard library modules later milestones need, which must never be forbidden: sqlite3 for the saved crosswalk (M13),
# and hashlib (with hashlib.scrypt), hmac, secrets and getpass for keys and the install secret backup (M01, M13).
ALLOWED_STDLIB = ("sqlite3", "hashlib", "hmac", "secrets", "getpass")

# Distribution names (PEP 503 normalized: lowercase, runs of -_. collapsed to -)
FORBIDDEN_DISTS = frozenset({
    "requests", "urllib3", "httpx", "httpcore", "h11", "aiohttp", "websockets", "websocket-client", "fsspec", "s3fs", "gcsfs", "boto3", "botocore",
    "openai", "anthropic", "google-generativeai", "google-genai", "google-ai-generativelanguage", "cohere", "mistralai", "langchain", "langchain-core",
    "llama-index", "transformers", "tokenizers", "torch", "tensorflow", "keras", "jax", "onnxruntime", "huggingface-hub", "sentence-transformers",
    "ollama", "litellm", "tiktoken", "pyside6-addons", "pyqt6-webengine", "pyqtwebengine",
    # the old build's server and launcher stack (A-20, SPEC 12.3)
    "streamlit", "fastapi", "uvicorn", "python-multipart", "thefuzz",
})

# The allowlist is the real control; FORBIDDEN_DISTS only gives a clearer message for names we know about.
# Adding any package to the lock means editing this set in the same reviewed change.
APPROVED_DISTS = frozenset({
    "et-xmlfile", "lxml", "numpy", "openpyxl", "pandas", "pyside6-essentials", "python-dateutil", "python-geosupport", "shiboken6", "six", "tzdata",
})

# Development and test tools in requirements-dev.lock that are not runtime pins. Never shipped.
APPROVED_DEV_DISTS = frozenset({
    "colorama", "hypothesis", "iniconfig", "packaging", "pefile", "pluggy", "pygments", "pytest", "pytest-qt", "sortedcontainers",
    "typing-extensions",
})

# os.startfile is forbidden everywhere except this one file, which opens a source file the operator added (SPEC 12.6).
STARTFILE_EXEMPT = ("wholecount/ui/shell.py",)

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
# A .bin file over this size is treated as a possible model file (SPEC 12.2).
MODEL_BIN_MAX_BYTES = 1024 * 1024

URL_RE = re.compile(r"(?i)\b(?:https?|ftp|wss?|sftp|s3|gs)://[^\s'\"<>)]+|\\\\[A-Za-z0-9_.-]+\\[A-Za-z0-9_$.-]+")
URL_ALLOW_PREFIXES = (  # XML namespaces and license identifiers are identifiers, not endpoints
    "http://schemas.openxmlformats.org/", "http://schemas.microsoft.com/", "http://www.w3.org/", "http://purl.org/", "http://www.xml.org/",
)
PIP_REQ_RE = re.compile(r"^([A-Za-z0-9][A-Za-z0-9._-]*)==([^\s\\;]+)", re.M)


def normalize_dist(name: str) -> str:
    return re.sub(r"[-_.]+", "-", name).lower()
