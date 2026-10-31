"""Opening a source file in the program Windows uses for it (SPEC 12.6). The one file the static scan lets call os.startfile.

Only a file added to this batch can be opened, and it is registered with the guard first. Nothing is sent anywhere.
"""
import os
import pathlib
import sys


class NotInBatch(Exception):
    pass


def open_source_file(path, batch_paths):
    p = pathlib.Path(path).resolve()
    if p not in {pathlib.Path(x).resolve() for x in batch_paths}:
        raise NotInBatch(str(p.name))
    if sys.platform != "win32":
        return False
    from wholecount.guard import allow_open_file

    allow_open_file(str(p))
    os.startfile(str(p))  # noqa: S606  the operator asked, after a confirm
    return True
