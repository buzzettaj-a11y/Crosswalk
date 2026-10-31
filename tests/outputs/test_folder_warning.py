"""OUT-14 (fix plan 2.3): synced and network folders, from the path and environment only."""
import pytest

from wholecount import copy
from wholecount.engine.outputs.folders import folder_warning


@pytest.mark.claim("CL-OUT-10")
@pytest.mark.parametrize("path,env,want", [
    (r"C:\Users\x\Work\file", {"OneDrive": r"C:\Users\x\Work"}, "onedrive"),
    (r"C:\Users\x\OneDrive\y", {}, "onedrive"),
    (r"C:\Users\x\OneDrive - St Nicks\y", {}, "onedrive"),
    (r"C:\Users\x\Dropbox\y", {}, "dropbox"),
    (r"G:\My Drive\y", {}, "google_drive"),
    (r"C:\Users\x\Google Drive\y", {}, "google_drive"),
    (r"C:\Users\x\Box\y", {}, "box"),
    (r"C:\Users\x\Boxes\y", {}, None),
    (r"\\server\share\y", {}, "network"),
    (r"C:\Users\x\Documents", {}, None),
])
def test_kinds(path, env, want):
    assert folder_warning(path, env) == want
    assert copy.get("outputs.folder_callout") == "This folder copies files to other computers. These files hold client data."
