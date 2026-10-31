"""The printable summary (SPEC 9.3, A-03, A-06). One model; HTML here, and M12 draws the PDF from the same SummaryDoc.

Counts only. File names, and the system names that default from them, appear only when the operator ticks them, and then
only in the sources section. No Client_ID, master ID or person row.
"""
import html
from dataclasses import dataclass

from wholecount import copy
from wholecount.engine.counts import balance_lines


@dataclass(frozen=True)
class SummaryDoc:
    practice: bool
    goal1: tuple                          # (low, high)
    goal2: tuple
    final_line: str
    per_program: tuple                    # (program, low, high)
    balance: tuple                        # sentences
    no_address: tuple                     # (reason word, count)
    confidence: str
    backend_line: str
    settings_lines: tuple
    calibration: str | None
    sources: tuple                        # (letter, file name or "", system or "")
    footer: str


def _range(r):
    return copy.get("counts.range", low=r.low, high=r.high) if r.low != r.high else f"{r.high:,}"


def confidence_sentence(conf):
    if conf.level is None:
        return ""
    head = copy.get(f"confidence.level.{conf.level}")
    if conf.level == "high":
        counted = dict((n, (a, b)) for n, a, b in conf.measures)
        return f"{head}. " + copy.get("confidence.high_reason", counted=counted["counted"][0], received=counted["counted"][1],
                                      high=counted["placed"][0], looked_up=counted["placed"][1])
    parts = [copy.get(f"confidence.part.{code}", **params) for code, params in conf.parts]
    body = parts[0] if len(parts) == 1 else ", ".join(parts[:-1]) + ", and " + parts[-1]
    return f"{head}. {body.rstrip('.')}."


def final_line(counts):
    if counts.final:
        return copy.get("counts.final")
    for code in counts.not_final_codes:
        if code == "rows_not_counted_yet":
            return copy.get("counts.not_final.rows_not_counted_yet", count=counts.not_counted_yet)
        if code == "pairs_open":
            return copy.get("counts.not_final.pairs_open", count=counts.open_pairs)
        if code == "copy_groups_open":
            return copy.get("counts.not_final.copy_groups_open", count=counts.open_copy_groups)
        if code == "programs_unconfirmed":
            return copy.get("counts.not_final.programs_unconfirmed", count=1)
    return ""


def build_summary(view, include_file_names):
    c = view.counts
    locs = c.locations
    sources = tuple((letter, name if include_file_names else "", system if include_file_names else "")
                    for letter, name, system in view.sources)
    return SummaryDoc(
        practice=view.practice,
        goal1=(c.goal1.low, c.goal1.high), goal2=(c.goal2.low, c.goal2.high), final_line=final_line(c),
        per_program=tuple((p, r.low, r.high) for p, r in sorted(c.per_program.items())),
        balance=tuple(copy.get(k, **params) for k, params in balance_lines(view.balance)),
        no_address=tuple((copy.get(f"status.location.reason.{k}"), getattr(locs, k)) for k in
                         ("no_fixed_address", "outside_nyc", "address_problem", "not_found", "no_geocoder")),
        confidence=confidence_sentence(view.confidence),
        backend_line=copy.get("summary.backend", backend=view.backend, release=view.release or "-"),
        settings_lines=(copy.get("summary.dob_coverage", counted=c.dob_coverage[0], total=c.dob_coverage[1]),),
        calibration=None if view.calibration is None else str(view.calibration),
        sources=sources,
        footer=copy.get("summary.footer_names" if include_file_names else "summary.footer_counts"),
    )


def render_summary_html(doc):
    e = html.escape
    out = ["<!DOCTYPE html><html lang=\"en\"><head><meta charset=\"utf-8\"><title>", e(copy.get("summary.title")), "</title>",
           "<style>body{font-family:Segoe UI,Arial,sans-serif;margin:24px;color:#1b1b1b}h1{font-size:20px}h2{font-size:15px;"
           "margin-top:18px}table{border-collapse:collapse}td,th{border:1px solid #bbb;padding:3px 8px;text-align:left}"
           "p.practice{font-weight:bold}</style></head><body>"]
    if doc.practice:
        out.append(f"<p class=\"practice\">{e(copy.get('summary.practice_line'))}</p>")
    out.append(f"<h1>{e(copy.get('summary.title'))}</h1>")
    out.append(f"<p>{e(copy.get('summary.goal1'))}: {e(_pair(doc.goal1))}<br>{e(copy.get('summary.goal2'))}: {e(_pair(doc.goal2))}</p>")
    out.append(f"<p>{e(doc.final_line)}</p>")
    if doc.per_program:
        out.append(f"<h2>{e(copy.get('summary.per_program'))}</h2><table>")
        out += [f"<tr><td>{e(p)}</td><td>{e(_pair((lo, hi)))}</td></tr>" for p, lo, hi in doc.per_program]
        out.append("</table>")
    out.append(f"<h2>{e(copy.get('summary.balance'))}</h2>")
    out += [f"<p>{e(line)}</p>" for line in doc.balance]
    out.append(f"<h2>{e(copy.get('summary.no_address'))}</h2><table>")
    out += [f"<tr><td>{e(w)}</td><td>{n:,}</td></tr>" for w, n in doc.no_address]
    out.append("</table>")
    out.append(f"<h2>{e(copy.get('summary.confidence'))}</h2><p>{e(doc.confidence)}</p>")
    out.append(f"<p>{e(doc.backend_line)}</p>")
    out += [f"<p>{e(line)}</p>" for line in doc.settings_lines]
    if doc.calibration:
        out.append(f"<p>{e(doc.calibration)}</p>")
    out.append(f"<h2>{e(copy.get('summary.sources'))}</h2><table>")
    for letter, name, system in doc.sources:
        out.append(f"<tr><td>{e(letter)}</td><td>{e(name)}</td><td>{e(system)}</td></tr>")
    out.append(f"</table><p>{e(doc.footer)}</p></body></html>")
    return "".join(out)


def _pair(p):
    lo, hi = p
    return copy.get("counts.range", low=lo, high=hi) if lo != hi else f"{hi:,}"
