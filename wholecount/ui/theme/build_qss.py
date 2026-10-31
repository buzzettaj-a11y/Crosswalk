"""Tokens to QSS (SPEC 11.2). A pure function; `python -m wholecount.ui.theme.build_qss --out build/theme.qss` writes it for
inspection. Square corners, 1px borders, 3px rules only at top or bottom, a focus border on every interactive class."""
import argparse
import pathlib


def _colors(tokens):
    return {t["name"]: t["value"] for t in tokens["color"]["tokens"]}


def _types(tokens):
    out = {}
    for g in tokens["type"]["groups"]:
        for s in g["styles"]:
            out[s["name"]] = s
    return out


ROLE_COLOR = {"kicker": "muted", "h2": "ink", "count-lg": "ink", "count": "ink", "count-row": "ink", "body": "ink",
              "row-title": "ink", "note": "muted", "caption": "muted", "micro": "muted", "strip-kicker": "muted",
              "stage-name": "ink", "column-head": "muted"}


def build_qss(tokens):
    c = _colors(tokens)
    t = _types(tokens)
    out = []
    add = out.append
    add(f"QWidget {{ background: transparent; color: {c['ink']}; }}")
    add(f"QMainWindow, QWidget#centralRoot {{ background: {c['bg-page']}; }}")
    add(f"QScrollArea, QScrollArea > QWidget > QWidget#stageBody {{ background: {c['bg-page']}; border: 0px; }}")
    add(f"QToolTip {{ background: {c['bg-card']}; color: {c['ink']}; border: 1px solid {c['line']}; border-radius: 0px; }}")
    # Labels by role, then tone.
    for role, color_name in ROLE_COLOR.items():
        s = t.get(role) or t.get("kicker")
        size = s["fontSize"] if role in t else "10px"
        add(f'QLabel[role="{role}"] {{ color: {c[color_name]}; font-size: {size}; font-weight: {s["fontWeight"]}; }}')
    add(f'QLabel[role="link"] {{ color: {c["blue-500"]}; font-size: 12px; font-weight: 800; }}')
    add(f'QLabel[role="link"][tone="amber"] {{ color: {c["amber-700"]}; }}')
    add(f'QLabel[role="band-word"] {{ color: {c["ink"]}; font-size: 13px; font-weight: 800; }}')
    add(f'QLabel[role="h3"] {{ color: {c["ink"]}; font-size: 15px; font-weight: 800; }}')
    add(f'QLabel[role="level"] {{ color: {c["ink"]}; font-size: 18px; font-weight: 800; }}')
    add(f'QLabel[role="wordmark"] {{ color: {c["on-dark"]}; font-size: 14px; font-weight: 800; }}')
    add(f'QLabel[role="status"] {{ color: {c["on-dark-muted"]}; font-size: 11.5px; }}')
    add(f'QLabel[role="ledger-kicker"] {{ color: {c["muted"]}; font-size: 9.5px; font-weight: 800; }}')
    add(f'QLabel[role="ledger-kicker"][tone="blue"] {{ color: {c["blue-500"]}; }}')
    add(f'QLabel[role="band-kicker"] {{ color: {c["muted"]}; font-size: 9px; font-weight: 800; }}')
    add(f'QLabel[role="band-kicker"][tone="blue"] {{ color: {c["blue-500"]}; }}')
    add(f'QLabel[role="band-line"] {{ color: {c["ink"]}; font-size: 12.5px; }}')
    add(f'QLabel[role="strip-caption"] {{ color: {c["muted"]}; font-size: 10.5px; }}')
    add(f'QLabel[role="ticker"] {{ color: {c["ink"]}; font-size: 12px; font-weight: 800; }}')
    add(f'QLabel[role="ticker-msg"] {{ color: {c["muted"]}; font-size: 12px; }}')
    add(f'QLabel[role="box-title"] {{ color: {c["ink"]}; font-size: 13px; font-weight: 800; }}')
    add(f'QLabel[role="drawer-title"] {{ color: {c["ink"]}; font-size: 21px; font-weight: 800; }}')
    add(f'QLabel[role="dl-label"] {{ color: {c["ink"]}; font-size: 12px; font-weight: 800; }}')
    add(f'QLabel[role="dl-text"] {{ color: {c["ink-2"]}; font-size: 12px; }}')
    add(f"QScrollBar:vertical {{ background: {c['bg-card']}; width: 10px; border: 0px; margin: 0px; }}")
    add(f"QScrollBar::handle:vertical {{ background: {c['line-2']}; min-height: 24px; border: 0px; }}")
    add(f"QScrollBar::handle:vertical:hover {{ background: {c['muted']}; }}")
    add("QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical { height: 0px; border: 0px; }")
    add("QScrollBar::add-page:vertical, QScrollBar::sub-page:vertical { background: transparent; }")
    for tone, name in (("muted", "muted"), ("ink-2", "ink-2"), ("amber", "amber-700"), ("blue", "blue-700"), ("ink", "ink"),
                       ("on-dark", "on-dark"), ("on-dark-muted", "on-dark-muted"), ("green", "green-700")):
        add(f'QLabel[tone="{tone}"] {{ color: {c[name]}; }}')
    # Buttons.
    base = "border-radius: 0px; min-height: 36px; padding: 0px 14px; font-weight: 800;"
    add(f'QPushButton {{ {base} background: {c["bg-card"]}; color: {c["ink"]}; border: 1px solid {c["line-2"]}; }}')
    add(f'QPushButton[kind="primary"] {{ background: {c["blue-500"]}; color: #ffffff; border: 1px solid {c["blue-500"]}; }}')
    add(f'QPushButton[kind="secondary"] {{ background: {c["bg-card"]}; color: {c["ink"]}; border: 1px solid {c["line-2"]}; }}')
    add(f'QPushButton[kind="quiet"] {{ background: transparent; color: {c["blue-500"]}; border: 1px solid transparent; '
        f'padding: 0px 4px; }}')
    add(f'QPushButton[kind="quiet"][tone="lesser"] {{ color: {c["ink-2"]}; }}')
    add(f'QPushButton[kind="quiet"][tone="nav"] {{ color: {c["blue-500"]}; }}')
    add(f'QPushButton[kind="quiet"][tone="dark"] {{ color: {c["on-dark"]}; border: 1px solid {c["muted"]}; }}')
    add(f'QPushButton[kind="quiet"][tone="amber"] {{ color: {c["amber-700"]}; }}')
    add(f'QPushButton[kind="held"] {{ background: {c["bg-surface"]}; color: {c["muted"]}; border: 1px solid {c["line-2"]}; }}')
    add(f'QPushButton:hover {{ border: 1px solid {c["ink-2"]}; }}')
    add(f'QPushButton[kind="primary"]:hover {{ background: {c["blue-700"]}; border: 1px solid {c["blue-700"]}; }}')
    add(f'QPushButton[kind="quiet"]:hover {{ border: 1px solid {c["line"]}; }}')
    add(f'QPushButton[kind="held"]:hover {{ border: 1px solid {c["line-2"]}; }}')
    add(f'QPushButton:focus {{ border: 2px solid {c["blue-500"]}; }}')
    # Strip items paint their own rule; the button itself is flat.
    add(f'QPushButton[strip="item"] {{ background: {c["bg-card"]}; border: 0px; border-right: 1px solid {c["line-soft"]}; '
        f'text-align: left; padding: 0px; min-height: 55px; }}')
    add(f'QPushButton[strip="item"][state="current"] {{ background: {c["blue-100"]}; }}')
    add(f'QPushButton[strip="item"]:hover {{ background: {c["bg-page"]}; }}')
    add(f'QPushButton[strip="item"]:focus {{ border: 2px solid {c["blue-500"]}; }}')
    # Inputs.
    for w in ("QLineEdit", "QComboBox"):
        add(f"{w} {{ background: {c['bg-card']}; color: {c['ink']}; border: 1px solid {c['line-2']}; border-radius: 0px; "
            f"min-height: 36px; padding: 0px 8px; }}")
        add(f"{w}:hover {{ border: 1px solid {c['ink-2']}; }}")
        add(f"{w}:focus {{ border: 2px solid {c['blue-500']}; }}")
    add(f"QCheckBox {{ min-height: 36px; color: {c['ink']}; }}")
    add(f"QCheckBox:hover {{ color: {c['ink']}; }}")
    add(f"QCheckBox:focus {{ border: 2px solid {c['blue-500']}; }}")
    add(f"QCheckBox::indicator {{ width: 16px; height: 16px; border: 1px solid {c['line-2']}; background: {c['bg-card']}; "
        f"border-radius: 0px; }}")
    add(f"QCheckBox::indicator:checked {{ background: {c['blue-500']}; border: 1px solid {c['blue-500']}; }}")
    # Callouts and tags.
    for kind, rule, border in (("needs", "blue-500", "blue-300"), ("decided", "green-500", "green-300"),
                               ("wrong", "amber-500", "amber-300"), ("ink", "ink", "line")):
        add(f'QFrame[callout="{kind}"] {{ background: {c["bg-card"]}; border: 1px solid {c[border]}; '
            f'border-top: 3px solid {c[rule]}; border-radius: 0px; }}')
    tag = t["tag"]
    for kind, bg, fg, border in (("needs", "blue-500", "#ffffff", "blue-500"), ("confirmed", "green-100", "green-700", "green-300"),
                                 ("wrong", "amber-100", "amber-700", "amber-300"), ("neutral", "bg-surface", "ink-2", "line"),
                                 ("practice", "amber-500", "#ffffff", "amber-500")):
        fgv = fg if fg.startswith("#") else c[fg]
        add(f'QLabel[tag="{kind}"] {{ background: {c[bg]}; color: {fgv}; border: 1px solid {c[border]}; border-radius: 0px; '
            f'font-size: {tag["fontSize"]}; font-weight: {tag["fontWeight"]}; padding: 2px 6px; }}')
    # Frame pieces.
    add(f'QFrame#topBar {{ background: {c["ink"]}; border: 0px; }}')
    add(f'QFrame#ticker {{ background: {c["bg-card"]}; border: 0px; border-bottom: 1px solid {c["line"]}; }}')
    add(f'QFrame#ledger {{ background: {c["bg-card"]}; border: 0px; border-right: 1px solid {c["line"]}; }}')
    add(f'QFrame#ledgerFooter {{ background: {c["bg-surface"]}; border: 0px; border-top: 1px solid {c["line"]}; }}')
    add(f'QFrame#band {{ background: {c["bg-card"]}; border: 0px; border-top: 1px solid {c["line"]}; '
        f'border-bottom: 1px solid {c["line"]}; }}')
    add(f'QFrame#strip {{ background: {c["bg-card"]}; border: 0px; border-bottom: 1px solid {c["line"]}; }}')
    add(f'QFrame#drawer {{ background: {c["bg-card"]}; border: 1px solid {c["line"]}; }}')
    add(f'QFrame#dropdown {{ background: {c["bg-card"]}; border: 1px solid {c["line"]}; border-top: 3px solid {c["blue-500"]}; }}')
    add(f'QFrame#dataLine {{ background: {c["bg-card"]}; border: 1px solid {c["line"]}; }}')
    add(f'QFrame#never {{ background: {c["bg-surface"]}; border: 1px solid {c["line"]}; }}')
    add(f'QFrame#tickBox {{ background: {c["blue-100"]}; border: 1px solid {c["blue-300"]}; }}')
    add(f'QFrame#flowBox {{ background: {c["bg-card"]}; border: 1px solid {c["line"]}; }}')
    add(f'QFrame#flowBoxMemory {{ background: {c["bg-card"]}; border: 2px solid {c["ink"]}; }}')
    add(f'QFrame#card {{ background: {c["bg-card"]}; border: 1px solid {c["line"]}; }}')
    add(f'QFrame#dropZone {{ background: {c["bg-card"]}; border: 1px dashed {c["line-2"]}; }}')
    add(f'QFrame#dropZone[drop="ok"] {{ background: {c["blue-100"]}; border: 1px dashed {c["blue-500"]}; }}')
    add(f'QFrame#dropZone[drop="bad"] {{ background: {c["amber-100"]}; border: 1px dashed {c["amber-500"]}; }}')
    add(f'QFrame#holdingBar {{ background: {c["blue-100"]}; border: 1px solid {c["blue-300"]}; }}')
    add(f'QFrame#ruleCard {{ background: {c["bg-card"]}; border: 1px solid {c["line"]}; border-top: 3px solid {c["line"]}; }}')
    add(f'QFrame#ruleCard[selected="true"] {{ background: {c["blue-100"]}; border: 1px solid {c["blue-300"]}; '
        f'border-top: 3px solid {c["blue-500"]}; }}')
    add(f'QFrame#amberRow {{ background: {c["amber-100"]}; border: 1px solid {c["amber-300"]}; }}')
    add(f'QFrame#grayRow {{ background: {c["bg-surface"]}; border: 1px solid {c["line"]}; }}')
    add(f'QFrame#groupHead {{ background: {c["bg-surface"]}; border: 0px; border-bottom: 1px solid {c["line"]}; }}')
    add(f'QComboBox[check="problem"] {{ border: 1px solid {c["amber-300"]}; }}')
    add(f'QTableView {{ background: {c["bg-card"]}; border: 1px solid {c["line"]}; gridline-color: {c["line-soft"]}; '
        f'selection-background-color: {c["blue-100"]}; selection-color: {c["ink"]}; }}')
    add(f'QHeaderView::section {{ background: {c["bg-surface"]}; color: {c["muted"]}; border: 0px; '
        f'border-bottom: 1px solid {c["line"]}; padding: 0px 8px; min-height: 30px; font-size: 10.5px; font-weight: 800; }}')
    add(f'QTableView:focus {{ border: 2px solid {c["blue-500"]}; }}')
    add(f'QTableView:hover {{ border: 1px solid {c["line-2"]}; }}')
    add(f'QSpinBox {{ background: {c["bg-card"]}; color: {c["ink"]}; border: 1px solid {c["line-2"]}; border-radius: 0px; '
        f'min-height: 36px; padding: 0px 8px; }}')
    add(f'QSpinBox:hover {{ border: 1px solid {c["ink-2"]}; }}')
    add(f'QSpinBox:focus {{ border: 2px solid {c["blue-500"]}; }}')
    add(f'QRadioButton {{ min-height: 36px; color: {c["ink"]}; }}')
    add(f'QRadioButton:hover {{ color: {c["ink"]}; }}')
    add(f'QRadioButton:focus {{ border: 2px solid {c["blue-500"]}; }}')
    add(f'QPushButton[kind="segment"] {{ background: {c["bg-card"]}; color: {c["ink"]}; border: 1px solid {c["line-2"]}; }}')
    add(f'QPushButton[kind="segment"][selected="true"] {{ background: {c["ink"]}; color: {c["on-dark"]}; '
        f'border: 1px solid {c["ink"]}; }}')
    add(f'QPushButton[kind="rulecard"] {{ background: {c["bg-card"]}; border: 1px solid {c["line"]}; '
        f'border-top: 3px solid {c["line"]}; text-align: left; padding: 0px; min-height: 100px; }}')
    add(f'QPushButton[kind="rulecard"][selected="true"] {{ background: {c["blue-100"]}; border: 1px solid {c["blue-300"]}; '
        f'border-top: 3px solid {c["blue-500"]}; }}')
    add(f'QPushButton[kind="chip"] {{ background: {c["bg-card"]}; color: {c["ink"]}; border: 1px solid {c["line-2"]}; '
        f'font-weight: 400; padding: 0px 10px; }}')
    add(f'QPushButton[kind="chip"][selected="true"] {{ background: {c["blue-100"]}; border: 1px solid {c["blue-500"]}; }}')
    add(f'QPushButton[kind="chip"][held_chip="true"] {{ background: {c["blue-500"]}; color: #ffffff; '
        f'border: 1px solid {c["blue-500"]}; }}')
    add(f'QFrame#rule {{ background: {c["line-soft"]}; border: 0px; min-height: 1px; max-height: 1px; }}')
    add(f'QFrame#popover {{ background: {c["bg-card"]}; border: 1px solid {c["line"]}; border-top: 3px solid {c["ink"]}; }}')
    return "\n".join(out) + "\n"


def main(argv=None):
    from wholecount.ui.theme import tokens

    ap = argparse.ArgumentParser()
    ap.add_argument("--out", type=pathlib.Path, default=pathlib.Path("build/theme.qss"))
    args = ap.parse_args(argv)
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(build_qss(tokens()), encoding="utf-8")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
