"""The PyInstaller exclusion and drop lists and two pure functions (M14 section 2, research R4).

A deliberate second copy of tools/offline_rules.py (research 8.3): the build must not import tools/, and a test keeps the
two in step. Nothing here imports PyInstaller, so the lists are tested without it.
"""
import re

# 1) Python modules removed from the import graph ("ignored, as though they were not found").
NETWORK_STDLIB = [
    "socket", "_socket", "ssl", "_ssl", "http", "http.client", "http.server", "http.cookies", "http.cookiejar",
    "urllib.request", "urllib.response", "urllib.error", "urllib.robotparser",
    "ftplib", "smtplib", "poplib", "imaplib", "telnetlib", "nntplib", "smtpd",
    "xmlrpc", "xmlrpc.client", "xmlrpc.server", "socketserver", "webbrowser",
    "asyncio", "_asyncio", "_overlapped", "multiprocessing", "_multiprocessing", "concurrent.futures.process",
]
SUBINTERPRETERS = ["_xxsubinterpreters", "_interpreters", "_interpchannels", "_interpqueues", "_xxinterpchannels",
                   "_xxinterpqueues"]
DEV_ONLY = ["unittest", "doctest", "pydoc", "pdb", "test", "tkinter", "_tkinter", "distutils", "setuptools", "pkg_resources",
            "pip", "wheel", "pytest", "_pytest", "IPython", "numpy.testing", "pandas.tests", "numpy.tests", "hypothesis",
            "pytestqt",
            # developer tools inside the package: never shipped
            "wholecount.dev", "wholecount.app_imports"]
THIRD_PARTY_NETWORK_AND_AI = [
    "requests", "urllib3", "httpx", "aiohttp", "websockets", "fsspec", "boto3", "botocore", "certifi",
    "openai", "anthropic", "google.generativeai", "google.genai", "cohere", "mistralai", "langchain", "llama_index",
    "transformers", "torch", "tensorflow", "onnxruntime", "huggingface_hub", "ollama", "litellm",
]
QT_EXCLUDED_MODULES = [
    "PySide6.QtNetwork", "PySide6.QtWebEngineCore", "PySide6.QtWebEngineWidgets", "PySide6.QtWebEngineQuick",
    "PySide6.QtWebSockets", "PySide6.QtWebChannel", "PySide6.QtWebView", "PySide6.QtPositioning", "PySide6.QtLocation",
    "PySide6.QtQml", "PySide6.QtQuick", "PySide6.QtQuickWidgets", "PySide6.QtQuick3D", "PySide6.QtHttpServer",
    "PySide6.QtNetworkAuth", "PySide6.QtRemoteObjects", "PySide6.QtBluetooth", "PySide6.QtNfc", "PySide6.QtSql",
    "PySide6.QtMultimedia", "PySide6.QtMultimediaWidgets", "PySide6.QtDBus",
]
EXCLUDES = NETWORK_STDLIB + SUBINTERPRETERS + DEV_ONLY + THIRD_PARTY_NETWORK_AND_AI + QT_EXCLUDED_MODULES

# 2) Files that must not be in the folder even if a hook collected them as a dependency of something else.
QT_DROP = [
    r"(^|/)plugins/(tls|networkinformation|networkaccess|bearer|generic|qmltooling|sqldrivers|designer|vectorimageformats|"
    r"platforminputcontexts)/",
    r"(^|/)(lib)?Qt6(WebEngine\w*|WebSockets|WebChannel|Positioning|Location|HttpServer|NetworkAuth|RemoteObjects)\b",
]
# On Windows the PySide6 wheel's QtCore, QtGui and QtWidgets do not import Qt6Network.dll; on Linux they do, so it stays there.
QT_DROP_WINDOWS = [r"(^|/)Qt6Network\.dll$", r"(^|/)Qt6Qml\w*\.dll$", r"(^|/)Qt6Quick\w*\.dll$", r"(^|/)_ssl\.",
                   r"(^|/)libssl"]

LEAK_MODULES = frozenset(NETWORK_STDLIB + SUBINTERPRETERS + THIRD_PARTY_NETWORK_AND_AI + QT_EXCLUDED_MODULES)
LEAK_FILE_RE = re.compile(r"(^|/)(_socket|_ssl|_asyncio|_xxsubinterpreters|_interpreters)[.]|(^|/)libssl|QtNetwork")
AI_NAMES = ("openai", "anthropic", "cohere", "mistralai", "langchain", "llama_index", "transformers", "torch", "tensorflow",
            "onnxruntime", "huggingface_hub", "ollama", "litellm")
MODEL_SUFFIXES = (".onnx", ".pt", ".pth", ".safetensors", ".gguf", ".h5")
BIN_MAX = 1024 * 1024


def drop(toc, patterns):
    """toc entries whose destination matches none of the patterns. Entries are (dest, src, typecode)."""
    return [e for e in toc if not any(re.search(p, e[0].replace("\\", "/")) for p in patterns)]


def leaked(pure, binaries, datas):
    """The forbidden entries in PyInstaller's tables: a network or AI module in the pure list, or a forbidden file."""
    out = sorted({n for n, _s, _t in pure if n in LEAK_MODULES or n.split(".", 1)[0] in AI_NAMES})
    out += sorted({d for d, _s, _t in list(binaries) + list(datas) if LEAK_FILE_RE.search(d.replace("\\", "/"))})
    return out


def model_files(datas, size_of):
    """Data entries that look like model files: a model suffix, or a .bin over 1 MB. size_of(src) gives a file's size."""
    out = []
    for d, src, _t in datas:
        low = d.lower()
        if low.endswith(MODEL_SUFFIXES) or (low.endswith(".bin") and size_of(src) > BIN_MAX):
            out.append(d)
    return sorted(out)
