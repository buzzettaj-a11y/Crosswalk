"""Writing a review file, editing it like a person would, and reading it back through M01's reader."""
import csv
import io
import pathlib

from tests.support.outputs import write
from wholecount.engine.outputs.corrections_in import read_corrections
from wholecount.engine.read.reader import read_path
from wholecount.session.export import build_view


def review_grid(s, folder):
    write(s, folder)
    raw = (pathlib.Path(folder) / "Manual_Review_Needed.csv").read_bytes().decode("utf-8-sig")
    return [list(r) for r in csv.reader(io.StringIO(raw))]


def save_grid(grid, path):
    with open(path, "w", newline="", encoding="utf-8") as f:
        csv.writer(f).writerows(grid)
    return path


def read_back(s, grid, path, mac=None):
    save_grid(grid, path)
    rf = read_path(pathlib.Path(path))
    return read_corrections(rf.grids[0].rows, mac or s.secret.mac, build_view(s), pathlib.Path(path).name, rf.fingerprint)


def cell(grid, rk, column, value=None):
    h = grid[0]
    for row in grid[1:]:
        if row[h.index("Record_Key")] == rk:
            if value is not None:
                row[h.index(column)] = value
            return row[h.index(column)]
    raise KeyError(rk)
