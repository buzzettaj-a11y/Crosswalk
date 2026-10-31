"""The record panel (SPEC 8.2): what the problem means, the location, the row as it arrived, unmatched columns on screen
only, records sharing the identifier, a suggestion from the row itself, and the decision buttons. No typing (H7)."""
from PySide6.QtCore import Qt
from PySide6.QtWidgets import QGridLayout, QWidget

from wholecount import copy
from wholecount.session import commands as C
from wholecount.session.pages import problem_title, sharing_identifier, source_path, unmatched_columns
from wholecount.ui.stages.review.dialogs import SetAsideDialog
from wholecount.ui.stages.review.queue import problem_text
from wholecount.ui.widgets.callout import Callout
from wholecount.ui.widgets.style import button, hbox, label, vbox


class RecordPanel(QWidget):
    def __init__(self, window, record_key, show_unmatched, toggle_unmatched, open_key):
        super().__init__()
        self.window_ = window
        self.rk = record_key
        s = window.bridge.session
        r = s.results
        row, o = r.rows[record_key], r.outcomes[record_key]
        lay = vbox(self, (18, 14, 18, 14), 12)
        name = " ".join(v for v in (row.value("First_Name"), row.value("Last_Name")) if v)
        lay.addWidget(label(copy.get("review.record.head", name=name or "-", id=row.value("Client_ID") or "-"),
                            role="h3", name="recordHead"))
        lay.addWidget(label(copy.get("review.record.where", file=r.file_of_record.get(record_key, ""), n=o.row_number,
                                     counted=copy.get("common.yes" if o.counted else "common.no")), role="note"))
        if len(o.reasons) > 1:
            lay.addWidget(label(copy.get("review.record.several", n=len(o.reasons)), role="note"))
        for rid in o.reasons:
            box = vbox(spacing=2)
            box.addWidget(label(copy.get("review.record.means"), role="kicker"))
            box.addWidget(label(problem_title(rid), role="row-title", wrap=True))
            box.addWidget(label(problem_text(rid, "means"), role="note", wrap=True))
            lay.addLayout(box)
        if o.location is not None:
            box = vbox(spacing=2)
            box.addWidget(label(copy.get("review.record.location"), role="kicker"))
            word = copy.get(f"status.confidence.{o.location.confidence}") if o.location.kind == "mapped" \
                else copy.get("status.confidence.not_placed")
            tone = None if o.location.kind == "mapped" and o.location.confidence == "high" else "amber"
            box.addWidget(label(word, role="row-title", tone=tone, name="recordLocation"))
            box.addWidget(label(copy.get(f"geo.reason.{o.location.reason}") if o.location.reason else "", role="note",
                                wrap=True))
            lay.addLayout(box)
        lay.addWidget(label(copy.get("review.record.arrived"), role="kicker"))
        grid = QGridLayout()
        failing = {f for _, f in o.reason_fields}
        i = 0
        for f in [x.key for x in s.schema().enabled_fields()]:
            v = row.value(f)
            grid.addWidget(label(f, role="caption"), i, 0)
            grid.addWidget(label(v, role="row-title" if f in failing else "note", name=f"value_{f}"), i, 1)
            i += 1
        lay.addLayout(grid)
        um = unmatched_columns(s, record_key)
        if um:
            lay.addWidget(label(copy.get("review.record.unmatched_count", n=len(um)), role="kicker"))
            lay.addWidget(label(", ".join(c for c, _ in um), role="note", wrap=True, name="unmatchedNames"))
            lay.addWidget(label(copy.get("review.record.unmatched_out"), role="caption"))
            b = button(copy.get("review.record.show_alongside"), "quiet", "nav", name="showAlongside")
            b.clicked.connect(toggle_unmatched)
            lay.addWidget(b, 0, Qt.AlignLeft)
            if show_unmatched:
                lay.addWidget(label(copy.get("review.record.unmatched"), role="note", tone="amber", wrap=True,
                                    name="unmatchedNote"))
                g = QGridLayout()
                for j, (c, v) in enumerate(um):
                    g.addWidget(label(c, role="caption"), j, 0)
                    g.addWidget(label(v, role="note", name=f"unmatched_{j}"), j, 1)
                lay.addLayout(g)
        others = sharing_identifier(s, record_key)
        if others:
            lay.addWidget(label(copy.get("review.record.sharing", n=len(others) + 1, id=row.value("Client_ID")),
                                role="kicker"))
            for k in others:
                orow = r.rows[k]
                line = hbox(spacing=8)
                line.addWidget(label(f"{r.outcomes[k].row_number}  {orow.value('First_Name')} {orow.value('Last_Name')}  "
                                     f"{orow.value('Address_1')}  {orow.value('Zip')}", role="note"), 1)
                ob = button(copy.get("review.record.open_row", n=r.outcomes[k].row_number), "quiet", "nav",
                            name=f"openRow_{k}")
                ob.clicked.connect(lambda _=False, k=k: open_key(k))
                line.addWidget(ob)
                lay.addLayout(line)
        props = r.fills.get(record_key)
        if props and o.reasons:
            p = props[0]
            c = Callout("needs")
            c.body.addWidget(label(copy.get("review.record.suggested", fill=p.value), role="row-title", tone="blue"))
            c.body.addWidget(label(copy.get("review.fill.why", field=p.field), role="note", wrap=True))
            row_b = hbox(spacing=8)
            ap = button(copy.get("review.record.apply"), "primary", name="applySuggestion")
            ap.clicked.connect(lambda: window.bridge.dispatch(C.AcceptFills([record_key])))
            no = button(copy.get("review.record.not_this"), "quiet", "nav", name="notThis")
            no.clicked.connect(lambda: c.hide())
            window.run_hold.register(ap)
            row_b.addWidget(ap)
            row_b.addWidget(no)
            row_b.addStretch(1)
            c.body.addLayout(row_b)
            lay.addWidget(c)
        acts = hbox(spacing=8)
        if o.reasons and o.set_aside_reason is None:
            ap = button(copy.get("review.bulk.approve"), "primary", name="recordApprove")
            ap.clicked.connect(lambda: window.bridge.dispatch(C.ApproveRows([record_key], "*")))
            acts.addWidget(ap)
            window.run_hold.register(ap)
        aside = button(copy.get("review.bulk.aside"), "secondary", name="recordAside")
        aside.clicked.connect(self._aside)
        window.run_hold.register(aside)
        acts.addWidget(aside)
        if o.set_aside_reason is not None or o.count_status.value in ("counted_approved", "counted_corrected"):
            ro = button(copy.get("review.bulk.reopen"), "secondary", name="recordReopen")
            ro.clicked.connect(lambda: window.bridge.dispatch(C.ReturnToOpen([record_key])))
            window.run_hold.register(ro)
            acts.addWidget(ro)
        opn = button(copy.get("review.open.button"), "quiet", "nav", name="openSource")
        opn.clicked.connect(self.open_source)
        acts.addWidget(opn)
        acts.addStretch(1)
        lay.addLayout(acts)
        self.message = label("", role="caption", name="recordMessage")
        lay.addWidget(self.message)
        lay.addStretch(1)

    def _aside(self):
        d = SetAsideDialog(self.window_, [self.rk])
        self.window_.active_dialog = d
        d.open()
        return d

    def open_source(self):
        import sys

        from wholecount.ui import shell

        s = self.window_.bridge.session
        path = source_path(s, self.rk)
        if path is None:
            return False
        if not self.window_.confirm(copy.get("review.open.title"), (copy.get("review.open.confirm_name", name=path.name),
                                                                   copy.get("review.open.confirm")),
                                    copy.get("review.open.ok"), copy.get("review.cancel")):
            return False
        if sys.platform != "win32":
            self.message.setText(copy.get("review.open.windows_only"))
            return False
        return shell.open_source_file(path, s.setup.paths())
