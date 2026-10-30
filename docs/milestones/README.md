# Milestones

The rewrite happens in 16 milestones, in order. Each one ends with a report and a pull request, and Claude Code stops there until Joe reviews and merges. A milestone is done only when every box in its done list is checked against the real output.

## The order

| # | Milestone | Main spec sections | Audit findings it closes |
| --- | --- | --- | --- |
| M00 | Repo, toolchain, offline guard and copy registry | 2, 3, 12, 13.1, 13.2 | A-20 (by design), copy lint groundwork for A-25 |
| M01 | Reading files and finding tables | 5.1, 6.1 | B-02, B-24, A-09, A-13, C-23 |
| M02 | Fields, source systems and matching columns | 4, 6.2 | B-21, B-22, B-23, B-48, B-49 |
| M03 | Tidy-up steps | 6.3 | B-06, B-07, B-08, B-09, B-10, B-11, B-12, B-29, B-30, B-32, B-33, B-42 |
| M04 | Standardizing fields and checking rows | 6.4, 6.5 | B-01, B-03, B-04, B-05, B-13, B-14, B-15, B-16, B-25, B-26, B-27, B-28, B-31, B-41, B-43, B-44, A-11 |
| M05 | Placing addresses, districts and the privacy offset | 6.6 | B-17, B-18, B-19, B-34, B-35, B-45, B-46, A-14, C-10, C-25 |
| M06 | Copies and the same person across files | 5.3, 6.7, 6.8 | C-01, C-02, A-05, B-36, B-37, B-38, B-39, B-47, C-17, C-20, C-21, C-24 |
| M07 | Programs | 6.9 | B-20, B-40, C-05, C-13, C-19 |
| M08 | Session, decisions, undo, staleness, counting and confidence | 3.4, 5.2, 7, 8, 10.4 | C-03, C-04, C-06, C-07, C-08, C-09, C-12, C-14, C-15, C-16, C-18, A-06, A-07, A-12, A-22 |
| M09 | Outputs, audit trail, printable summary, receipt and saved progress | 9, 10.1 to 10.3 | A-01, A-02, A-03, A-04, A-08, A-10, A-15, A-24, C-11, C-22, C-26, C-27 |
| M10 | The window: theme, frame, ledger, progress and data clarity | 11.1 to 11.4, 11.6 to 11.9 | A-16, A-19, A-21, A-23 |
| M11 | Stages 01 to 05 | 11.5 | A-18 |
| M12 | Stages 06 to 09 | 11.5, 11.6, 11.7, 9.4 | (screens for findings closed in M05 to M09) |
| M13 | Matching calibration, the saved crosswalk and secret backup | 5.1 (backup), 8.8, 10.5 | Fix plan 5.4 and 5.6. It also fills the crosswalk lines on the data notes and the Your data drawer, with claim tests |
| M14 | Build, installer, firewall, signing and Windows CI | 12, 14, 13.6 | A-17, A-20 |
| M15 | Docs, help, acceptance and performance | 13.5, 15, 12.5 | A-25, any audit finding still open |

Spec version 1.1 moved some work into earlier milestones:
- **M01:** the install secret and its storage, behind a `SecretStore` interface. It uses DPAPI on Windows and a test double on Linux, because record keys need the secret from the start.
- **M04:** the two row statuses (P-VAL-1, P-VAL-2).
- **M05:** the map outputs' data (P-GEO-6, P-GEO-7).
- **M08:** reviewer names and the bulk-accept checks in the engine (section 8.7).
- **M09:** the signed review file and the two audit logs.
- **M12:** the reviewer screens.

Every High and Medium audit finding is assigned above. Low findings ride along with the milestone that touches the same code.

## How a milestone runs

1. Create the branch named in the milestone file from the latest `main`.
2. Read the milestone file, the spec sections it names, and the audit findings it lists.
3. For each rule and audit ID, write the failing test, then the code. Commit as you go.
4. Run `make test`, `make offline` and `make copy`. All three must be green.
5. For milestones with screens (M10 and later), run `make screens` and commit the PNGs under `docs/milestones/screens/MNN/`.
6. Write the report, push, open the pull request, and stop.

If something the milestone needs can't be reached from the cloud session, stop and put the question at the top of the report. That covers PyPI, a Python 3.12 build, GitHub Actions, or a public data source. Don't work around it.

## Report format

Write `docs/milestones/MNN-REPORT.md` with these sections, in this order:

```
# MNN report

## Questions for Joe
(Anything blocking or any decision made on a conservative reading. Write "None" if empty.)

## What was built
(Short list, by spec section.)

## Tests
(Counts from make test, make offline, make copy. New test files. Audit IDs closed, with their test names.)

## Done list
(The milestone's done list, every box checked or explained.)

## Windows checks
(The steps from the milestone file, copied so Joe can tick them.)

## Screens
(For UI milestones: links to the PNGs, and any place a screen differs from its board, with the reason.)

## Not done
(Anything left, with the reason. Write "Nothing" if empty.)
```

## Joe's review, for each pull request

1. Read the report, starting with Questions for Joe.
2. For UI milestones, compare the screen PNGs with the boards in `docs/context/design/board-images/`.
3. Run the Windows checks on your machine. Before M14 that means running from source, and the milestone file says how.
4. Reply on the pull request with changes, or merge it. Then tell Claude Code to start the next milestone.

## Milestone file template

Every milestone file uses these sections: Goal, Spec sections, Depends on, Branch, Read first, What to build, Tests to write, Done when, Windows checks for Joe, Out of scope.
