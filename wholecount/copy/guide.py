"""The user guide, built from the copy registry by one function (M15 section 1). The app's GuideDialog and
tools/make_docs.py both draw what build_guide() returns, so the two can't differ."""
import json
from dataclasses import dataclass, field
from importlib import resources

from wholecount import copy

GLOSSARY = ("add_your_files", "your_columns", "tidy_up", "match", "process", "fix_problems", "results", "download",
            "set_aside", "copies", "may_be_one_person", "look_up", "setup", "master_id", "record_key", "source_system",
            "run_ticker")
FILE_KEYS = ("final_clean_mapped", "unique_clients", "unique_clients_by_program", "manual_review_needed",
             "set_aside_records", "map_counts", "map_points", "internal_audit_log", "shareable_audit_log",
             "data_quality_report")
FILE_NAMES = ("Final_Clean_Mapped", "Unique_Clients", "Unique_Clients_By_Program", "Manual_Review_Needed",
              "Set_Aside_Records", "Map_Counts", "Map_Points", "Internal_Audit_Log", "Shareable_Audit_Log",
              "Data_Quality_Report")


@dataclass(frozen=True)
class Block:
    kind: str           # p, h3, img, list, line
    text: str = ""
    items: tuple = ()


@dataclass
class Section:
    anchor: str
    title: str
    blocks: list = field(default_factory=list)


@dataclass
class Guide:
    title: str
    sections: list


def expected():
    return json.loads(resources.files("wholecount").joinpath("sample_data/EXPECTED.json").read_text(encoding="utf-8"))


def file_counts():
    """(default, with Map_Points, practice) from the writer's own list of files."""
    from types import SimpleNamespace

    from wholecount.engine.outputs.view import ExportSettings
    from wholecount.engine.outputs.writer import files_to_write

    real, practice = SimpleNamespace(practice=False), SimpleNamespace(practice=True)
    return (len(files_to_write(real, ExportSettings())), len(files_to_write(real, ExportSettings(map_points=True))),
            len(files_to_write(practice, ExportSettings())))


def example_numbers():
    """The numbers for section 9, from the shipped EXPECTED.json: the practice run with the planned decisions."""
    plan = expected()
    after = plan["counts"]["after_decisions"]
    loc = plan["locations"]["practice_run_after_decisions"]
    mapped = loc["mapped_high"] + loc["mapped_low"]
    not_mapped = sum(loc["not_mapped"].values())
    return {"received": after["rows_received"], "counted": after["counted"], "not_counted_yet": after["not_counted_yet"],
            "aside": after["set_aside"], "mapped": mapped, "not_mapped": not_mapped, "goal1": after["goal_1"]["high"],
            "goal2": after["goal_2"]["high"]}


def _fmt(numbers):
    return {k: f"{v:,}" for k, v in numbers.items()}


def build_guide():
    from wholecount.ui.frame.stages import STAGES     # the one stage list; plain Python, no Qt

    g = Guide(copy.get("guide.title"), [])

    s = Section("what", copy.get("guide.what.title"))
    s.blocks += [Block("p", copy.get("guide.what.p1")), Block("p", copy.get("guide.what.p2"))]
    g.sections.append(s)

    s = Section("before", copy.get("guide.before.title"))
    s.blocks += [Block("p", copy.get(f"guide.before.p{i}")) for i in (1, 2, 3, 4)]
    g.sections.append(s)

    s = Section("stages", copy.get("guide.stages.title"))
    s.blocks.append(Block("p", copy.get("guide.stages.p1")))
    for st in STAGES:
        nn, sid, plain = st.nn, st.id, st.plain
        s.blocks.append(Block("h3", f"{nn}. {plain}"))
        s.blocks.append(Block("p", copy.get(f"help.stage.{sid}.purpose") + " " + copy.get(f"help.stage.{sid}.how")))
        s.blocks.append(Block("list", items=tuple(
            f"{copy.get(f'dataline.label.{part}')}: {copy.get(f'dataline.{sid}.{part}')}" for part in ("reads", "changes",
                                                                                                    "writes"))))
        s.blocks.append(Block("p", copy.get("guide.stages.decide", text=copy.get(f"guide.stage.{sid}.decide"))))
        s.blocks.append(Block("p", copy.get("guide.stages.held", text=copy.get(f"guide.stage.{sid}.held"))))
        if sid == "review":
            s.blocks.append(Block("p", copy.get("guide.stage.review.extra")))
        s.blocks.append(Block("img", f"guide/img/{nn}-{sid}.png"))
    g.sections.append(s)

    s = Section("results", copy.get("guide.results.title"))
    s.blocks += [Block("p", copy.get(f"guide.results.{k}")) for k in ("range", "final", "confidence", "balances", "noaddr")]
    g.sections.append(s)

    default, points, practice = file_counts()
    s = Section("files", copy.get("guide.files.title"))
    s.blocks.append(Block("p", copy.get("guide.files.count", default=default, with_points=points, practice=practice)))
    s.blocks.append(Block("list", items=tuple(f"{name}: {copy.get(f'export.file.{key}')}"
                                              for key, name in zip(FILE_KEYS, FILE_NAMES))))
    s.blocks += [Block("p", copy.get(k)) for k in ("guide.files.formats", "guide.files.logs", "guide.files.practice",
                                                   "outputs.folder_callout")]
    g.sections.append(s)

    s = Section("data", copy.get("guide.data.title"))
    for k in ("files", "memory", "out"):
        s.blocks.append(Block("p", copy.get(f"data.box.{k}.title") + ". " + copy.get(f"data.box.{k}.body")))
    s.blocks.append(Block("p", copy.get("data.never.title")))
    s.blocks.append(Block("list", items=tuple(copy.get(f"data.never.{k}") for k in ("internet", "ai", "log", "kept"))))
    s.blocks += [Block("p", copy.get("guide.data.secret")), Block("p", copy.get("settings.secret.body")),
                 Block("p", copy.get("settings.xw.body"))]
    g.sections.append(s)

    s = Section("words", copy.get("guide.words.title"))
    s.blocks.append(Block("list", items=tuple(copy.get(f"glossary.{k}") for k in GLOSSARY)))
    g.sections.append(s)

    s = Section("trouble", copy.get("guide.trouble.title"))
    s.blocks += [Block("p", copy.get(f"guide.trouble.{k}")) for k in ("code", "held", "read", "geo", "firewall")]
    g.sections.append(s)

    s = Section("example", copy.get("guide.example.title"))
    s.blocks += [Block("p", copy.get("guide.example.p1")),
                 Block("p", copy.get("guide.example.numbers", **_fmt(example_numbers())))]
    g.sections.append(s)
    return g


def headings(guide):
    return [s.title for s in guide.sections] + [b.text for s in guide.sections for b in s.blocks if b.kind == "h3"]


def to_markdown(guide):
    out = [f"# {guide.title}", "", f"## {copy.get('guide.contents')}", ""]
    out += [f"{i}. [{s.title}](#{s.anchor})" for i, s in enumerate(guide.sections, 1)]
    for i, s in enumerate(guide.sections, 1):
        out += ["", f'<a id="{s.anchor}"></a>', "", f"## {i}. {s.title}", ""]
        for b in s.blocks:
            if b.kind == "p":
                out += [b.text, ""]
            elif b.kind == "h3":
                out += [f"### {b.text}", ""]
            elif b.kind == "list":
                out += [f"- {x}" for x in b.items] + [""]
            elif b.kind == "img":
                out += [f"![]({b.text})", ""]
    text = "\n".join(out).rstrip() + "\n"
    while "\n\n\n" in text:
        text = text.replace("\n\n\n", "\n\n")
    return text


def to_html(guide):
    """For the app's QTextBrowser. Images belong to the file only, so none are drawn here."""
    import html

    e = html.escape
    out = [f"<h1>{e(guide.title)}</h1>"]
    for i, s in enumerate(guide.sections, 1):
        out.append(f'<h2><a name="{s.anchor}"></a>{i}. {e(s.title)}</h2>')
        for b in s.blocks:
            if b.kind == "p":
                out.append(f"<p>{e(b.text)}</p>")
            elif b.kind == "h3":
                out.append(f"<h3>{e(b.text)}</h3>")
            elif b.kind == "list":
                out.append("<ul>" + "".join(f"<li>{e(x)}</li>" for x in b.items) + "</ul>")
    return "\n".join(out)
