# Wholecount: instructions for Claude Code

Wholecount (previously Crosswalk) is an offline Windows desktop tool. It merges a nonprofit's client lists from many systems into one master list and counts unique clients overall (Goal 1) and per program (Goal 2). You're rewriting it from scratch.

## Read first, in this order

1. `SPEC.md`. This is the source of truth, and it wins over everything else in the repo.
2. `docs/milestones/README.md`. It covers how milestones work and the order they come in.
3. The milestone file you're working on, in `docs/milestones/`. Then read what that file points to.

Read these when a milestone points you to them:
- `docs/audit/AUDIT.md` and the A, B and C files. They list what the old build got wrong, by ID.
- `docs/research/offline-enforcement.md`. It's the tested design for the no-network guarantee.
- `docs/context/`. It has the design boards, the style guide, the old behavior spec and the project history.
- `legacy/`. That's the old build. Read it to learn what a rule did. Never import from it, copy from it or ship it.

## Hard rules

These are the short form of `SPEC.md` section 2. Breaking one is a bug, even if a test passes.

- **No network capability (H1).** That means no sockets, no HTTP clients, no web server, no port, no browser engine, no `QDesktopServices` and no URL strings in app code. Readers take local file objects only. Don't add a dependency without Joe's approval, and when he approves one, update `tools/offline_rules.py` in the same change.
- **No AI of any kind (H2).** No AI SDKs, models or model files, at runtime or at build time.
- **No client values in the audit, logs or progress messages (H8).** Use record keys, row numbers, field names and counts only. Progress messages use the `ProgressMessage` type, which can't hold a free string.
- **Nothing about clients is written to disk except files the operator downloads (H9).** Saved progress is encrypted and holds decisions, never values.
- **Every row is accounted for (H4),** and nothing is joined on a guess (H5). Automatic joins happen only for the three named reasons in P-ID-3.
- **Originals are kept, and reviewers can't type values (H6, H7).**
- **Decisions are keyed by record key, never by row position (H12).** Results are never shown from out-of-date state (H13).
- **Every user-facing sentence lives in `wholecount/copy/`,** and every factual claim has a test (H11). Use American spelling, plain words, and no em dashes, emoji or exclamation marks (H16). The same goes for docs you write.

When the spec is unclear, take the most conservative reading:
- never join records
- never overwrite a value
- never write to disk
- never contact anything outside the app

Log the choice in your milestone report.

## How to work

- **One milestone at a time.** Work on a branch named `build/mNN-short-name` from `main`, as the milestone file names it.
- **Tests first for rules.** For every P-rule and every audit ID in the milestone, write the failing test, then the code. Audit regression tests go in `tests/audit/`, named after the finding, like `test_B13_day_month_swap.py`. Record each one in `tests/audit/INDEX.md`.
- **Keep the engine free of Qt.** `wholecount/engine/` must not import PySide6. The UI reaches the engine only through `wholecount/session/`.
- **Small commits, one reason each.** Run the whole suite before every commit.
- **When the milestone's done list is complete,** write `docs/milestones/MNN-REPORT.md` in the format in `docs/milestones/README.md`. Then push the branch, open a pull request to `main`, and **stop**. Don't start the next milestone. Joe reviews each one, runs the Windows checks, and merges.
- **If something blocks you,** stop and put the question at the top of the report, rather than guessing at a behavior. Examples are a spec gap, a test you can't make pass without breaking a hard rule, or a dependency you need.

## Commands

The `Makefile` gives these the same names on every platform.

```
python3.12 -m venv .venv && . .venv/bin/activate      # Windows: py -3.12 -m venv .venv; .venv\Scripts\activate
pip install --require-hashes --no-deps -r requirements-dev.lock
make test         # pytest -q, with QT_QPA_PLATFORM=offscreen set for UI tests
make offline      # the offline and AI-free checks only (tests/offline)
make copy         # copy registry checks: claim tests, spelling, no em dashes
make screens      # tools/screens.py: renders every stage to build/screens/*.png at 1440 and 1280 wide
make run          # python -m wholecount
make bundle       # PyInstaller build (from M14), Windows only for the real build
```

## Environment notes

- Cloud sessions run on Linux. Qt runs headless with `QT_QPA_PLATFORM=offscreen`. Windows-only tests live in `tests_windows/`, and they run on the GitHub Actions `windows-latest` workflow (from M14) and on Joe's machine.
- Geosupport Desktop Edition isn't available in the cloud. Use the fake backend in `wholecount/engine/geo/fake.py` for tests. Joe checks the real adapter on Windows.
- The guard (`wholecount/guard/`) is installed as the first statement of `wholecount/__main__.py`. Tests that need it install it in a fresh `python -I` subprocess, as the research describes. Don't install it in the pytest process itself, because pytest's own plugins may need sockets.
