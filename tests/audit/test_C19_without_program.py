"""C-19: the old summary counted records without a program and called them people. It counts people now (PROG-8)."""
from wholecount.engine.programs import TableProgram, people_without_program, program_sources

MASTERS = {"a1": "M-ana", "a2": "M-bo", "a3": "M-di", "b1": "M-ana", "b2": "M-bo"}
PROGRAM = {"a1": "Housing", "a2": "Youth", "a3": "", "b1": None, "b2": None}


def test_people_not_records():
    assert sum(1 for rk in MASTERS if not PROGRAM[rk]) == 3
    assert people_without_program(MASTERS, PROGRAM) == 1
    assert len(set(MASTERS.values())) == 3
    assert len({(MASTERS[rk], PROGRAM[rk]) for rk in MASTERS if PROGRAM[rk]}) == 2


def test_table_with_no_program_column_is_listed():
    _, missing = program_sources([TableProgram("A", "column", "Program", None, 3, (("Housing", 1), ("Youth", 1), ("", 1))),
                                  TableProgram("B", "none", None, None, 2)])
    assert missing == [("B", 2)]
