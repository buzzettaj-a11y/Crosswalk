"""C-27: two runs of the same files added in a different order give the same data files and the same counts.

SPEC 4.3 gives each file a letter in the order it was added, and SPEC 9.1 prints that letter in three files: Source_Letter
in Manual_Review_Needed, the Table column of Data_Quality_Report, and Source_Records in the two people files. So those three
cells are removed before comparing. Everything else, row order included, must be identical, and a file with no letter must
be identical byte for byte. The audit logs record the add order on purpose and aren't compared.
"""
import csv
import io
import re

import pytest

from tests.acceptance import drive

LETTER_FREE = ("PRACTICE_Final_Clean_Mapped.csv", "PRACTICE_Set_Aside_Records.csv")


@pytest.fixture(scope="module")
def two_orders(tmp_path_factory):
    base = tmp_path_factory.mktemp("order")
    a, _ = drive.fast_path(drive.copy_inputs(base / "in_a"), base / "out_a")
    b, _ = drive.fast_path(drive.copy_inputs(base / "in_b", tuple(reversed(drive.NAMES))), base / "out_b")
    return (a, base / "out_a"), (b, base / "out_b")


def without_letters(path):
    rows = list(csv.reader(io.StringIO(path.read_bytes().decode("utf-8-sig"))))
    head = rows[0]
    drop = {head.index("Source_Letter")} if "Source_Letter" in head else set()
    out = []
    for row in rows:
        cells = []
        for i, cell in enumerate(row):
            if i in drop:
                continue
            if head[i] == "Table":
                cell = re.sub(r"^[A-Z]+\.", ".", cell)
            if head[i] == "Source_Records":
                cell = re.sub(r"(^|; )[A-Z]+ :: ", r"\1", cell)
            cells.append(cell)
        out.append(cells)
    return out


def test_the_letters_really_differ(two_orders):
    """The comparison would be empty if the two runs had the same letters."""
    (_, fa), (_, fb) = two_orders
    assert (fa / "PRACTICE_Unique_Clients.csv").read_bytes() != (fb / "PRACTICE_Unique_Clients.csv").read_bytes()


def test_the_counts_are_identical(two_orders):
    (a, _), (b, _) = two_orders
    assert a.results.counts == b.results.counts
    assert a.results.balance.total("received") == b.results.balance.total("received")


def test_files_without_letters_are_byte_identical(two_orders):
    (_, fa), (_, fb) = two_orders
    for name in LETTER_FREE:
        assert (fa / name).read_bytes() == (fb / name).read_bytes(), name


def test_every_data_file_is_identical_apart_from_letters(two_orders):
    (_, fa), (_, fb) = two_orders
    names = sorted(p.name for p in fa.glob("*.csv"))
    assert names == sorted(p.name for p in fb.glob("*.csv")) and len(names) == 6
    for name in names:
        assert without_letters(fa / name) == without_letters(fb / name), name
