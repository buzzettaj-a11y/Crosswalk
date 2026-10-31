"""Synced and network folders (SPEC 9.1, fix plan 2.3). The path and environment only; a mapped drive can't be seen (12.5)."""
import ntpath
import re

SYNC_NAMES = {"dropbox": "dropbox", "google drive": "google_drive", "my drive": "google_drive", "box": "box", "box sync": "box"}
ONEDRIVE_VARS = ("OneDrive", "OneDriveCommercial", "OneDriveConsumer")


def _parts(path):
    return [p for p in re.split(r"[\\/]+", path) if p]


def _under(path, root):
    p, r = ntpath.normcase(ntpath.normpath(path)), ntpath.normcase(ntpath.normpath(root))
    return p == r or p.startswith(r.rstrip("\\") + "\\")


def folder_warning(path, environ):
    """onedrive, dropbox, google_drive, box, network, or None."""
    if path.startswith("\\\\") or path.startswith("//"):
        return "network"
    for var in ONEDRIVE_VARS:
        root = environ.get(var)
        if root and _under(path, root):
            return "onedrive"
    for part in _parts(path):
        low = part.lower()
        if low == "onedrive" or low.startswith("onedrive - "):
            return "onedrive"
        if low in SYNC_NAMES:
            return SYNC_NAMES[low]
    return None
