"""Build column profiles from literal headers and values, for mapping tests."""
from wholecount.engine.mapping import ColumnRef, _profile, auto_map, check_mapping
from wholecount.engine.schema import default_schema

FILLER = ["x1", "x2", "x3"]


def profiles(cols, values=None, derived=()):
    """cols: header names. values: {header: [values]} for columns that need real values. derived: [(ColumnRef, values)]."""
    values = values or {}
    n = max([len(v) for v in values.values()] + [len(FILLER)])
    out = [_profile(ColumnRef(i, c), values.get(c, (FILLER * n)[:n])) for i, c in enumerate(cols)]
    out += [_profile(ref, v) for ref, v in derived]
    return out


def mapped(cols, values=None, derived=(), schema=None):
    schema = schema or default_schema()
    p = profiles(cols, values, derived)
    return check_mapping(schema, auto_map(schema, p, "t"), p)


def derived_ref(name, source, kind="split", index=100):
    return ColumnRef(index, name, derived=True, derived_from=source, derived_kind=kind)
