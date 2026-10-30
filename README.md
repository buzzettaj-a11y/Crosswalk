# Wholecount

Wholecount (previously Crosswalk) is an offline Windows desktop tool for New York City nonprofits. It takes the client lists an organization exports from its different systems and turns them into one clean master list. Then it produces two numbers:

- **Goal 1, unique clients:** each person counted once across every file.
- **Goal 2, unique clients by program:** each person counted once per program.

It runs entirely on one computer. It has no web server, no browser engine and no AI, and it's built so that it can't reach the internet.

**This repo holds the plan for a full rewrite.** The code doesn't exist yet. Claude Code builds it one milestone at a time.

## Where things are

| Path | What it is |
| --- | --- |
| `SPEC.md` | The specification. It's the source of truth for everything. |
| `CLAUDE.md` | Instructions Claude Code reads at the start of every session |
| `docs/milestones/` | 16 milestones (M00 to M15), in build order, each with its tests, done list and Windows checks |
| `docs/audit/` | The audit of the old build: 101 findings with reproductions. `AUDIT.md` is the summary. |
| `docs/research/` | `offline-enforcement.md` (how the no-internet guarantee works, with citations and tested code) and `rename.md` (the name research) |
| `docs/context/` | The old project's docs: design boards, style guide, build brief, decisions, behavior spec, fix plan, Excel runbook |
| `docs/planning/` | What Joe asked for, the decisions from planning, and the plan review |
| `legacy/` | The old Crosswalk build. It's for reference only, and nothing in it is imported or shipped. |

## How the build runs

1. Claude Code reads `CLAUDE.md`, `SPEC.md` and `docs/milestones/README.md`.
2. It builds one milestone on its own branch, writes a report, opens a pull request, and stops.
3. Joe reads the report, runs the Windows checks, and merges, or asks for changes.
4. Joe tells Claude Code to start the next milestone.

## What can't be guaranteed

These are the limits of the no-internet guarantee. The details are in SPEC section 12.5 and the research.

- An administrator can remove the firewall rule.
- A managed computer can ignore local firewall rules.
- The in-app guard can't see network use from compiled code inside Qt, libxml2 or the Geosupport DLL. The firewall rule is what covers those.
- A file on a mapped network drive looks like a local file. The app reads it like any file and sends nothing back.

## License notes

Wholecount uses PySide6 (LGPL), and Archivo (SIL Open Font License). The installer ships every third-party license in `licenses/`.
