"""
Wording: the same meaning in two registers.

Guided mode is written for someone who does this a few times a year and does not
think in terms of schemas and mappings. Advanced mode keeps the precise terms,
because a person who has switched to Advanced is asking for control and needs the
words that match what they are controlling.

Nothing about the behavior changes between the two. Only the words do.
"""
from __future__ import annotations

import re

STAGES_TECHNICAL = ["Sources", "Schema", "Prepare", "Map", "Programs", "Run",
                    "Review", "Summary", "Export"]
STAGES_PLAIN = ["Add your files", "Set up your columns", "Tidy up",
                "Match your columns", "Programs", "Process", "Fix problems",
                "Results", "Download"]

CHECK_TECHNICAL = "System check"
CHECK_PLAIN = "Check this computer"


def stages(mode):
    """The stage names in the register asked for."""
    return STAGES_TECHNICAL if mode == "Advanced" else STAGES_PLAIN


def check_stage(mode):
    """The name of the system check stage in the register asked for."""
    return CHECK_TECHNICAL if mode == "Advanced" else CHECK_PLAIN


# Headings and the line under them, per stage, in each register.
HEADINGS = {
    0: {"t": ("System check",
              "Environment diagnostics before any data work. Nothing here reads "
              "client data."),
        "p": ("Check this computer",
              "A few checks before you start. Nothing here opens your files.")},
    1: {"t": ("Sources",
              "Upload the exports. Tables found inside each file are listed "
              "separately and chosen one by one."),
        "p": ("Add your files",
              "Add the files you want to combine. If a file holds more than one "
              "table, you choose which ones to use.")},
    2: {"t": ("Schema",
              "The master shape every row is transformed into and tested "
              "against."),
        "p": ("Set up your columns",
              "These are the columns your finished list will have. The standard "
              "set works for most work.")},
    3: {"t": ("Prepare",
              "Per-file staging that adds columns and never removes them."),
        "p": ("Tidy up",
              "Some files need untangling first, for example an address and a "
              "ZIP squashed into one column. Nothing is deleted.")},
    4: {"t": ("Map",
              "Match each table's columns to the schema. City and State may stay "
              "unmapped, the ZIP fills them."),
        "p": ("Match your columns",
              "Tell the tool which of your columns holds which piece of "
              "information. City and State can be left empty; the ZIP fills "
              "them in.")},
    5: {"t": ("Programs",
              "Which column carries the program in each source, and which "
              "names are one program. The second count depends on this."),
        "p": ("Programs",
              "The count of clients per program is only right if every file's "
              "program column is matched and the same program is spelled one "
              "way. Set that up here and watch the count take shape.")},
    6: {"t": ("Run",
              "Settings, execution, results. Nothing is written to disk."),
        "p": ("Process",
              "Clean, check and locate every row. This all happens on this "
              "computer, and nothing is saved until you download it.")},
    7: {"t": ("Review",
              "Decide the causes in bulk first, then work anything left one row "
              "at a time."),
        "p": ("Fix problems",
              "Rows the tool could not finish on its own. Deal with the common "
              "causes together first, then anything left over one at a time.")},
    8: {"t": ("Summary",
              "The two counts the project asks for, and how they were reached."),
        "p": ("Results",
              "How many people you are working with, counted two ways.")},
    9: {"t": ("Export",
              "The output files. They are written only when you download them."),
        "p": ("Download",
              "Your finished files. Nothing is written until you download it.")},
}


def heading(stage, mode):
    """A stage's heading and the line under it, in the register asked for."""
    h = HEADINGS.get(stage, HEADINGS[0])
    return h["t"] if mode == "Advanced" else h["p"]


# Problem messages the engine produces, rewritten for a reader who did not
# write the engine. The pattern is matched loosely so the wording of an error
# can change without breaking the translation.
PLAIN_PROBLEMS = [
    (r"invalid zip code format.*blank", "This row has no ZIP code."),
    (r"invalid zip code format", "The ZIP code is not five digits."),
    (r"missing zip", "This row has no ZIP code."),
    (r"city could not be determined",
     "The city is blank and could not be worked out from the ZIP."),
    (r"unrecognized city",
     "The city is not one the tool recognizes."),
    (r"city/zip conflict",
     "The city and the ZIP code do not agree with each other."),
    (r"missing address_1", "This row has no street address."),
    (r"same client id",
     "More than one row uses this ID, but the rows are not the same."),
    (r"confirmed duplicate",
     "This is an exact copy of another row with the same ID."),
    (r"could not be matched locally|geosupport",
     "The address could not be found, so it has no location or districts."),
    (r"exceeds max length",
     "This value is longer than the column allows."),
    (r"must be a whole number", "This should be a number."),
    (r"must be a number", "This should be a number."),
    (r"is not a date", "This should be a date."),
    (r"must be yes or no", "This should be yes or no."),
    (r"missing (\w+)", "The {group1} is blank, and it is required."),
]


def plain_problem(text, mode="Guided"):
    """A problem message in the register the operator asked for."""
    if mode == "Advanced":
        return text
    low = (text or "").lower()
    for pattern, plain in PLAIN_PROBLEMS:
        m = re.search(pattern, low)
        if m:
            if "{group1}" in plain and m.groups():
                return plain.replace("{group1}",
                                     m.group(1).replace("_", " ").title())
            return plain
    return text


# Short labels used in several places.
TERMS = {
    "schema": {"t": "schema", "p": "column set-up"},
    "mapping": {"t": "mapping", "p": "column matching"},
    "prep": {"t": "staging step", "p": "tidy-up step"},
    "geocode": {"t": "geocode", "p": "find the location of"},
}


def term(key, mode):
    """A short label in the register asked for."""
    e = TERMS.get(key)
    if not e:
        return key
    return e["t"] if mode == "Advanced" else e["p"]


# How a finished run compares with what a file usually looks like, so a number
# becomes something a person can act on.
def run_context(clean, total, top_group_title=None):
    """
    Say whether a result is normal, and where to look when it is not.

    The band comes from what a reasonably prepared export tends to produce.
    It is guidance, not a rule.
    """
    if not total:
        return {"band": "", "verdict": "", "advice": ""}
    pct = clean / total * 100
    if pct >= 95:
        verdict = f"{pct:.0f}% passed on the first run."
        advice = ""
    elif pct >= 85:
        verdict = f"{pct:.0f}% passed on the first run."
        advice = ""
    elif pct >= 60:
        verdict = f"{pct:.0f}% passed on the first run."
        advice = ("The most common cause of a low result is a column matched to "
                  "the wrong field. Check the warnings on the matching stage "
                  "before working through the problems.")
    else:
        verdict = f"{pct:.0f}% passed on the first run."
        advice = ("Check the column matching first. A single column in the "
                  "wrong place can fail most of a file, and fixing it there is "
                  "far quicker than fixing rows one by one.")
    if top_group_title and pct < 85:
        advice += f" The largest single cause here is: {top_group_title}."
    return {"band": "", "verdict": verdict, "advice": advice}
