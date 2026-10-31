"""Wholecount.exe --self-check --self-check-out DIR (M14 section 3).

A windowed exe has no console, and a frozen build's biggest risk is a module missing only when frozen. This runs a fixed list
of checks and writes DIR/result.json and DIR/files/ and nothing else. The JSON holds check IDs, ok or failed, and counts. It
holds no string from any data file (H8). Expected counts come from the shipped sample_data/EXPECTED.json, so the Linux
source run and the frozen Windows exe must agree. It uses the same calls the stages and the tests use.
"""
import json
import os
import pathlib
import sys

WINDOWS = sys.platform == "win32"
CHECKS = ("guard.installed", "guard.denies_socket") + (("guard.denies_unc",) if WINDOWS else ()) + (
    "fonts.archivo", "copy.registry", "settings.load", "data.zip_table", "data.districts", "data.sample_reference",
    "readers.csv", "readers.tsv", "readers.xlsx", "readers.json", "readers.xml", "geosupport.import", "pipeline.sample",
    "outputs.nine_files") + (("secret.roundtrip", "dpapi.roundtrip") if WINDOWS else ()) + (
    "ui.build", "licenses.present", "modules.none_loaded")
EXAMPLES = {"readers.csv": "example_clinic.csv", "readers.tsv": "example_partner.tsv", "readers.xlsx": "example_housing.xlsx",
            "readers.json": "example_portal.json", "readers.xml": "example_state.xml"}
NINE = ("Final_Clean_Mapped", "Unique_Clients", "Unique_Clients_By_Program", "Manual_Review_Needed", "Set_Aside_Records",
        "Data_Quality_Report", "Internal_Audit_Log", "Shareable_Audit_Log", "Map_Counts")


class SelfCheckRefused(Exception):
    pass


def _sample_dir():
    from importlib import resources

    return pathlib.Path(str(resources.files("wholecount").joinpath("sample_data")))


def _expected():
    return json.loads((_sample_dir() / "EXPECTED.json").read_text(encoding="utf-8"))


def _licenses_dir():
    base = getattr(sys, "_MEIPASS", None)
    return pathlib.Path(base) / "licenses" if base else pathlib.Path(__file__).resolve().parents[1] / "licenses"


# The checks. Each returns a dict of counts (possibly empty) or raises.

def guard_installed(ctx):
    from wholecount import guard

    assert guard.INSTALLED
    return {}


def guard_denies_socket(ctx):
    # The frozen build has no socket module, so the audit event is raised directly. socket is never imported here.
    from wholecount.guard import OfflineViolation
    from wholecount.guard.probe import socket_connect

    try:
        socket_connect()
    except OfflineViolation:
        return {}
    raise AssertionError("socket.connect was not denied")


def guard_denies_unc(ctx):
    from wholecount.guard import OfflineViolation
    from wholecount.guard.probe import open_network_path

    try:
        open_network_path()
    except OfflineViolation:
        return {}
    raise AssertionError("a network path was not denied")


def fonts_archivo(ctx):
    from wholecount.ui.theme import apply

    _app(ctx)
    apply.load_fonts()
    ok = sum(1 for v in apply.FONT_STATUS.values() if v)
    assert ok == 3
    return {"fonts_loaded": ok}


def copy_registry(ctx):
    from wholecount import copy

    assert copy.get("app.version_line", version="0")
    return {}


def settings_load(ctx):
    from wholecount.settings.loader import load

    return {"settings_files": sum(1 for n in ("identity", "programs", "privacy", "calibration", "geo") if load(n))}


def data_zip_table(ctx):
    from wholecount.engine.geo.zips import borough_for_zip, nyc_zips

    assert borough_for_zip("11004") and not borough_for_zip("11580")
    return {"zip_codes": len(nyc_zips())}


def data_districts(ctx):
    from wholecount.engine.geo.backend import district_paths
    from wholecount.engine.geo.districts import DistrictIndex

    paths = district_paths()
    idx = DistrictIndex.from_files(paths)
    at_sea = idx.assign(40.40, -73.70)
    assert at_sea.senate is None and at_sea.assembly is None and at_sea.council is None
    if paths:                                   # a point in Manhattan gets a district once the files ship
        inside = idx.assign(40.7128, -74.0060)
        assert inside.senate or inside.assembly or inside.council
    return {"district_files": len(paths)}


def data_sample_reference(ctx):
    from wholecount.session.frame import sample_backend

    b = sample_backend()
    assert b.name == "reference_sample"
    return {}


def _reader(name):
    def check(ctx):
        from wholecount.engine.read.reader import read_path

        rf = read_path(_sample_dir() / EXAMPLES[name])
        n = len(rf.grids)
        assert n >= 1
        return {f"{name}.grids": n}
    return check


def geosupport_import(ctx):
    import geosupport  # noqa: F401  imports only; never calls

    return {}


def pipeline_sample(ctx):
    s = _example_session(ctx)
    plan = _expected()
    after = plan["counts"]["after_decisions"]
    c = s.counts()
    got = {"rows_received": s.results.balance.total("received"), "counted": c.counted, "not_counted_yet": c.not_counted_yet,
           "set_aside": c.set_aside, "goal_1": c.goal1.high, "goal_2": c.goal2.high,
           "tables": sum(1 for w in s.results.works)}
    want = {"rows_received": after["rows_received"], "counted": after["counted"], "not_counted_yet": after["not_counted_yet"],
            "set_aside": after["set_aside"], "goal_1": after["goal_1"]["high"], "goal_2": after["goal_2"]["high"],
            # A workbook's table counts once its header row is chosen, as the plan's header_rows decisions do.
            "tables": sum(v["tables_included"] for v in plan["files"].values())
            + sum(1 for h in plan["decisions"]["header_rows"] if plan["files"][h["file"]]["tables_included"] == 0)}
    assert got == want, "counts differ from EXPECTED.json"
    assert c.goal1.low == c.goal1.high and c.goal2.low == c.goal2.high
    return got


def outputs_nine_files(ctx):
    from wholecount.engine.outputs.view import ExportSettings
    from wholecount.session.export import download

    s = _example_session(ctx)
    folder = ctx["out"] / "files"
    folder.mkdir(parents=True, exist_ok=True)
    receipt = download(s, folder, ExportSettings(), confirmed_synced=True, overwrite=True)
    rows = {pathlib.Path(f.path).stem: f.rows for f in receipt.files}
    assert sorted(rows) == sorted(NINE), "not the nine default files"
    want = _expected()["outputs"]["no_geocoder_run"]
    for k in ("Final_Clean_Mapped", "Set_Aside_Records", "Manual_Review_Needed", "Unique_Clients", "Unique_Clients_By_Program",
              "Data_Quality_Report"):
        assert rows[k] == want[k], k
    return {"files_written": len(rows)}


def secret_roundtrip(ctx):
    import secrets as _secrets
    import tempfile

    from wholecount.session.secret_store import DpapiSecretStore

    with tempfile.TemporaryDirectory() as d:          # never the real profile
        store = DpapiSecretStore(d)
        value = _secrets.token_bytes(32)
        store.save(value)
        assert store.load() == value
    return {}


def dpapi_roundtrip(ctx):
    from wholecount.session import dpapi

    data = b"wholecount self-check"
    assert dpapi.unprotect(dpapi.protect(data)) == data
    return {}


def ui_build(ctx):
    from wholecount.ui.frame.bridge import SessionBridge
    from wholecount.ui.frame.stages import STAGES
    from wholecount.ui.frame.window import MainWindow

    app = _app(ctx)
    w = MainWindow(SessionBridge(_example_session(ctx), {"saved_progress": False, "reviewer_asked": True}),
                   confirm=lambda *a: False)
    built = 0
    for st in STAGES:
        w.go_to(st.id)
        app.processEvents()
        built += w.stage_widget is not None
    w.closing_confirmed = True
    w.close()
    w.deleteLater()
    app.processEvents()
    assert built == 9
    return {"stages_built": built}


def licenses_present(ctx):
    from wholecount.app_licenses import REQUIRED

    d = _licenses_dir()
    missing = [n for n in REQUIRED if not (d / n).is_file()]
    assert not missing
    return {"license_files": len(list(d.iterdir()))}


def modules_none_loaded(ctx):
    from wholecount.guard.offline_guard import DENY_MODULES

    # The guard puts None under the sub-interpreter names to block them, so only a real module object counts as loaded.
    loaded = [m for m, mod in list(sys.modules.items())
              if mod is not None and (m in DENY_MODULES or m.split(".", 1)[0] in DENY_MODULES)]
    assert not loaded
    return {}


FUNCS = {"guard.installed": guard_installed, "guard.denies_socket": guard_denies_socket, "guard.denies_unc": guard_denies_unc,
         "fonts.archivo": fonts_archivo, "copy.registry": copy_registry, "settings.load": settings_load,
         "data.zip_table": data_zip_table, "data.districts": data_districts, "data.sample_reference": data_sample_reference,
         "geosupport.import": geosupport_import, "pipeline.sample": pipeline_sample, "outputs.nine_files": outputs_nine_files,
         "secret.roundtrip": secret_roundtrip, "dpapi.roundtrip": dpapi_roundtrip, "ui.build": ui_build,
         "licenses.present": licenses_present, "modules.none_loaded": modules_none_loaded,
         **{k: _reader(k) for k in EXAMPLES}}


# Shared set-up

def _app(ctx):
    if "app" not in ctx:
        os.environ["QT_QPA_PLATFORM"] = "offscreen"
        from PySide6.QtWidgets import QApplication

        ctx["app"] = QApplication.instance() or QApplication([sys.argv[0]])
    return ctx["app"]


def _example_session(ctx):
    """The five example files with the planned decisions in EXPECTED.json, run with no geocoder (not a practice run)."""
    if "session" in ctx:
        return ctx["session"]
    import secrets as _secrets

    from wholecount.engine.geo.backend import NoBackend
    from wholecount.session import commands as C
    from wholecount.session.runner import process
    from wholecount.session.secret_store import InstallSecret
    from wholecount.session.state import Session

    plan = _expected()
    names = sorted(plan["files"])
    s = Session(InstallSecret(_secrets.token_bytes(32)), [_sample_dir() / n for n in names], backend=NoBackend(),
                getuser=lambda: "Self check")
    for h in plan["decisions"]["header_rows"]:
        s.setup.set("tables", (h["file"], 0, "header_row"), h["header_row"])
    process(s)
    r = s.results

    def key(ref):
        name, row = ref
        return next(k for k, rw in r.rows.items() if r.file_of_record[k] == name and rw.row_number == row)
    d = plan["decisions"]
    for g in d["copy_groups"]:
        members = {key(x) for x in g["rows"]}
        grp = next(x for x in s.results.groups if set(x.members) == members)
        s.history.execute(C.KeepOneInCopyGroup(grp.group_id, key(g["keep"])))
    for g in d["same_id_conflicts"]:
        members = {key(x) for x in g["rows"]}
        grp = next(x for x in s.results.groups if set(x.members) == members)
        s.history.execute(C.DecideSameIdConflict(grp.group_id, "different_people"))
    for g in d["program_groups"]:
        s.history.execute(C.DecideProgramGroup("confirm", tuple(g["names"]), g["label"]))
    for p in d["pairs"]:
        a, b = (s.results.person_of_record[key(x)] for x in p["rows"])
        s.history.execute(C.DecidePair(a, b, "same"))
    if s.results.confidence.level == "low":
        s.history.execute(C.AcknowledgeLowConfidence())
    ctx["session"] = s
    return s


def run(out):
    """Runs every check in order and writes out/result.json. Returns 0 when every check is ok."""
    out = pathlib.Path(out)
    out.mkdir(parents=True, exist_ok=True)
    ctx = {"out": out}
    results, counts = {}, {}
    for cid in CHECKS:
        try:
            counts.update({k: int(v) for k, v in (FUNCS[cid](ctx) or {}).items()})
            results[cid] = "ok"
        except Exception:  # noqa: BLE001  a failed check is recorded by its ID only, never by its message (H8)
            results[cid] = "failed"
    data = {"checks": results, "counts": counts, "frozen": bool(getattr(sys, "frozen", False)), "windows": WINDOWS}
    (out / "result.json").write_text(json.dumps(data, indent=2, sort_keys=True), encoding="utf-8")
    return 0 if all(v == "ok" for v in results.values()) else 1


def main(argv):
    """argv after the program name. --self-check needs --self-check-out DIR, or it refuses and writes nothing."""
    if "--self-check-out" not in argv or argv.index("--self-check-out") + 1 >= len(argv):
        raise SelfCheckRefused()
    return run(argv[argv.index("--self-check-out") + 1])
