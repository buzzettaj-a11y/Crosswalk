"""Reading a corrections file for the window (SPEC 8.6), through the session layer. Rows match by Record_Key."""
import pathlib


def read_corrections_file(session, path):
    from wholecount.engine.outputs.corrections_in import read_corrections
    from wholecount.engine.read.reader import read_path
    from wholecount.session.export import build_view

    rf = read_path(pathlib.Path(path))
    return read_corrections(rf.grids[0].rows, session.secret.mac, build_view(session), pathlib.Path(path).name,
                            rf.fingerprint)
