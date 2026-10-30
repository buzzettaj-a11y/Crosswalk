# Audit of the current build

Audited 2026-10-30 against `Crosswalk.zip` (version string 2026.09.17, the renamed build with the hover-rail front end). The old code is in `legacy/` for reference. Nothing in it was changed.

**All 10 of the old build's test suites pass (1,233 checks).** They still miss everything below, because they mostly check that screens answer, not that answers are right.

## The numbers

| Report | What it checked | High | Medium | Low | Total |
| --- | --- | --- | --- | --- | --- |
| [A-claims.md](A-claims.md) | What the screens, launchers and docs say, against what the code does, and every file written to disk | 10 | 10 | 5 | 25 |
| [B-values.md](B-values.md) | Cleaning, parsing, filling, geocoding, matching columns and grouping programs | 23 | 17 | 9 | 49 |
| [C-counts.md](C-counts.md) | Goal 1, Goal 2, the row balance, decisions, undo, sessions, exports and determinism | 11 | 13 | 3 | 27 |
| | | **44** | **40** | **17** | **101** |

Every finding has a reproduction that was actually run, plus the file and line responsible and a requirement for the rewrite. The scripts are in `A-scripts/`, `B-scripts/` and `C-scripts/`. They were written against absolute paths in the audit sandbox, so treat them as worked examples to port into the rewrite's test suite, not as tests to run as is.

**Independent check.** Six High findings were re-proven in a separate script by a different reviewer, without the auditors' helpers: C-01, C-10, B-03, A-01, C-03, and the line of code behind C-01. All six held.

## What it means, in plain words

### 1. The two counts can be wrong while the screen says they're final

- **C-01.** Any pair of records scoring 100 or more is joined into one person without asking. That joins twins, and a father and son with the same name, then shows "this count is final." The cause is `identity.py:442`, where a threshold meant only for "same ID in one system" catches any high score.
- **A-05, C-02.** Two different people who share a Client ID across systems get merged.
- **C-03, C-04.** Process and Undo don't refresh the person matching, so Goal 1 and Goal 2 describe an earlier run. With two people added and Process run again, Goal 1 stayed at 2 instead of 4.
- **C-05.** The fast path skips the program grouping, so Goal 2 comes out higher than it does stage by stage on the same files.
- **B-20.** Program-name proposals nobody confirmed are applied at run time.
- **A-06.** "This count is final" shows while a client is still in review.
- **A-12, C-12.** Goal 2 is shown as one exact number even when open pairs could still move it.

### 2. People's decisions get lost or land on the wrong rows

- **A-07, C-07.** "Preview the counts," Process and the fast path silently wipe every review decision.
- **A-08.** "Saved progress" doesn't bring back person-matching decisions or program groups, and resume says it did.
- **C-06.** A corrections file is applied by row position, so a re-sorted source overwrites other people's rows.
- **C-08.** "Keep this copy" is stored as a row number, so after a re-export the other copy gets kept.

### 3. Rows go missing while the screen says every row is accounted for

- **A-09, C-23.** Rows outside the tables the tool picked, such as rows after a blank line, vanish from every output, and the balance can't catch it.
- **C-15.** The review file also lists set-aside rows, so the three files add up to more than the input.

### 4. Values change wrongly in rows marked clean

Nobody reviews these, because they're marked "Passed every check."

- **Placeholders and text.** "-", "0" and "Homeless" pass as real names, IDs and addresses (B-01). A Windows-encoded CSV turns "José" into "Jos?" with no warning (B-02).
- **ZIP and place.** A Nassau ZIP turns Valley Stream into Queens (B-03). A borough with a New Jersey or junk ZIP passes (B-04). Chelsea, MA becomes Manhattan, and a blank State becomes NY (B-05).
- **Address splitting.** It drops "Concourse" (B-08), breaks "117 - 19 45th Ave" (B-09), silently drops a trailing "c/o Jane Doe" (B-10), and reads a 9-digit ZIP as its last five digits (B-07). The calculated ZIP keeps the first five digits of garbage (B-06).
- **Names.** Particles, double surnames and compound first names split wrong (B-11), and titles and suffixes become names (B-12).
- **Dates of birth.** Day and month get swapped silently, so a day-first file is half wrong (B-13). "1/2/26" becomes 1926 (B-14). Birth dates up to 2100 are accepted (B-15). Any 5-digit string is read as an Excel date (B-16).
- **Column matching.** Auto-mapping picks the first matching column by position, such as an emergency contact's name or a mailing address (B-21). Program gets mapped to a date column (B-22). Split-off columns replace real ones (B-23).

### 5. Locations can be wrong and still look verified

- **B-17, B-35.** A fuzzy match lands on a different building or cross street, then gets labeled "Verified." 111 Main matched 11 Main, and 40 W 100 St matched 100 W 40 St.
- **B-19.** District shapes with holes are treated as solid.
- **B-18, A-14.** The privacy jitter can be undone with the documented seed, and the seed is printed in the audit that's meant to be safe to share.
- **Reference data.** The shipped address file is synthetic, and 81% of its rows contradict their own ZIP.

### 6. Privacy promises that aren't true

- **A-01.** A column nobody mapped, such as an SSN, is written into the review export.
- **A-02, C-22.** The "IDs only" audit log contains names, streets, cities and ZIPs.
- **A-03.** The "counts only" printable summary carries a Client ID and file names.
- **A-04.** "Files are written only when you download them" is false. Saved progress writes to disk from the first upload, on by default, and includes values a reviewer typed.
- **A-10.** "A reviewer can't type a value" is false, and the edited row is then labeled "Passed every check."
- **A-15.** Under the double-click launcher, the launch log captures the whole session's errors, including uploaded file names.

### 7. It crashes on ordinary input

- **C-10.** Process fails for any address the reference file actually knows. The sample files only dodge this because none of their 256 addresses is in it.
- **C-09.** The review screen returns an error whenever a required field is blank.
- **C-11.** The review export fails whenever a summary row exists.

### 8. Internet and AI

- **There's no AI anywhere in this build.** No AI library, model or call was found.
- **The first launch runs `pip install` from the internet** (`launch.py:170-198`). `run.bat` and `run.sh` do it on every start, and they also start Streamlit's web server.
- **Everything else is local, but the app is a web server on 127.0.0.1** that opens the browser. The launcher and Stop scripts kill whatever process holds the port (A-17).

## What the rewrite must do about it

Each finding ends in a rewrite requirement and a test case. `SPEC.md` turns them into rules, and every milestone file lists the finding IDs it closes. A milestone isn't done until the tests ported from its findings pass.
