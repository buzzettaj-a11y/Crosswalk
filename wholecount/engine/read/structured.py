"""JSON and XML records (P-READ-1, P-READ-10). Nested values flatten to dotted keys; the keys are the header."""
import json

from lxml import etree

from wholecount.engine.read.model import UnreadableFile


def _unwrap(data):
    """The record list in a JSON document. A list is the records. An object with exactly one list value uses that list.
    An object whose only value is another object is looked into, so {"export": {"clients": [...]}} finds the clients.
    Any other object is one record."""
    while True:
        if isinstance(data, list):
            return data
        if not isinstance(data, dict):
            return [data]
        lists = [v for v in data.values() if isinstance(v, list)]
        if len(lists) == 1:
            return lists[0]
        if len(data) == 1 and isinstance(next(iter(data.values())), dict):
            data = next(iter(data.values()))
            continue
        return [data]


def _scalar(v):
    if v is None:
        return ""
    if v is True:
        return "true"
    if v is False:
        return "false"
    return str(v)


def _flatten_json(value, prefix, out):
    if isinstance(value, dict):
        for k, v in value.items():
            _flatten_json(v, f"{prefix}.{k}" if prefix else str(k), out)
    elif isinstance(value, list):
        if all(not isinstance(v, (dict, list)) for v in value):
            out[prefix or "value"] = "; ".join(_scalar(v) for v in value)
        else:
            for i, v in enumerate(value, start=1):
                _flatten_json(v, f"{prefix}.{i}" if prefix else str(i), out)
    else:
        out[prefix or "value"] = _scalar(value)


def json_records(data_bytes):
    """[dict, ...] with every number literal kept as typed."""
    try:
        text = data_bytes.decode("utf-8-sig")
        data = json.loads(text, parse_int=str, parse_float=str, parse_constant=str)
    except (UnicodeDecodeError, ValueError):
        raise UnreadableFile("bad_json") from None
    records = []
    for item in _unwrap(data):
        flat = {}
        _flatten_json(item, "", flat)
        records.append(flat)
    return records


def _parser():
    return etree.XMLParser(no_network=True, resolve_entities=False, load_dtd=False, dtd_validation=False, huge_tree=False)


def _flatten_xml(el, path, out):
    for name, value in el.attrib.items():
        _put(out, f"{path}@{name}", value)
    children = [c for c in el if isinstance(c.tag, str)]
    if not children:
        if path:
            _put(out, path, el.text or "")
        return
    for c in children:
        tag = etree.QName(c).localname
        _flatten_xml(c, f"{path}.{tag}" if path else tag, out)


def _put(out, key, value):
    out[key] = f"{out[key]}; {value}" if key in out and out[key] else value


def xml_records(fileobj):
    try:
        root = etree.parse(fileobj, _parser()).getroot()
    except etree.XMLSyntaxError:
        raise UnreadableFile("bad_xml") from None
    nodes = [c for c in root if isinstance(c.tag, str)] or [root]
    records = []
    for node in nodes:
        flat = {}
        _flatten_xml(node, "", flat)
        records.append(flat)
    return records


def records_to_rows(records):
    """(header, rows): the union of keys in first-seen order, and a missing key is an empty cell."""
    header = []
    seen = set()
    for r in records:
        for k in r:
            if k not in seen:
                seen.add(k)
                header.append(k)
    return header, [[r.get(k, "") for k in header] for r in records]
