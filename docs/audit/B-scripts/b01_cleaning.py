from _common import *
tests = {
 "NULL": "NULL", "N/A": "N/A", "none": "none", "dash": "-", "double dash": "--", "em dash": "—",
 "zero": "0", "NA": "NA", "TBD": "TBD", "unknown": "unknown", "n.a.": "n.a.", "?": "?", "xx": "XXX", "blank-ish nbsp": " ",
 "nbsp inside": "Main St", "tab": "Ana\tMaria", "zwsp": "Ana​Maria", "zwj": "Ana‍Maria", "bom": "﻿Ana",
 "soft hyphen": "Ana­Maria", "leading apostrophe": "'07030", "leading apostrophe name": "'Ana", "lrm": "‎Ana",
 "ctrl": "Ana\x00Maria", "smart quote O'Brien": "O’Brien", "nbsp-only-null": " N/A ", "#REF!": "#REF!", "#VALUE!": "#VALUE!",
 "nat": "NaT", "NaN": "NaN", "<NA>": "<NA>", "undefined": "undefined", "UNKNOWN": "UNKNOWN",
}
for k, v in tests.items():
    out = engine.clean_cell(v)
    print(f"{k:28} {v!r:22} -> {out!r}")
