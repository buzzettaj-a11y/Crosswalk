# Briefs, Crosswalk rewrite plan (2026-10-30)

Ledger is in `ledger.md`. Every R line maps to a checkbox below.

## Settled for every task

- **Rewrite everything.** New code. The behavior spec (`docs/crosswalk-described-for-an-ai.md`), the proof workbook and the old tests are the answer key, not the old code.
- **Windows only.**
- **Python + Qt (PySide6) native window, no browser engine anywhere in the app.** No local web server and no port. The UI talks to the engine through plain Python calls.
- **Windows installer.** It adds a Windows Firewall rule that blocks the app from the network.
- **Every item in the fix plan gets built in from the start** (all 24).
- **Signing.** Plan for the free route. A self-signed certificate, trusted on client machines by the client's IT through Group Policy or Intune. Leave a switch to move to Azure Artifact Signing later (about $9.99 a month, available to US individuals, and it builds SmartScreen reputation over time rather than instantly).
- **The color rule applies to every screen.** Blue means needs you, green means a person decided, amber means looks wrong, gray means settled. No red.
- **Stage 02 is renamed "Your columns."**
- **Repo.** `buzzettaj-a11y/crosswalk`, private and empty, attached with push access.
- **Plan shape.** A spec plus numbered milestone files in the repo, each with its own tests and done list. Code stops after each milestone for Joe's review.
- **Vision, applies to every task.** It's clear what's happening (R5), and the system is easy to follow (R10).
- **Steering, applies to every task.** Claude Code in the cloud builds it, and this chat only plans (S1). The plan is detailed enough that Code never guesses (S2).

Decided without asking, with reasons:

- No AI anywhere, including the AI rule assistant from the side chat. Joe asked for no AI influence (R8).
- No Streamlit. It's a rewrite, and Streamlit runs its own web server.
- PySide6 rather than PyQt6, because PySide6 is LGPL and safe to hand to clients in a bundled app.
- Python 3.12, PyInstaller one-folder build inside an Inno Setup installer. Inno Setup is free and can add the firewall rule during install.
- The product stays generic for any client. The geocoder stays NYC only (Geosupport Desktop Edition with a local file fallback).
- Cloud Code runs on Linux, so Qt runs headless there for tests and screenshots. Joe does the Windows checks listed at the end of each milestone.

---

## T1. Audit the current build

- **Goal.** Find where the current build gets numbers wrong, changes values it shouldn't, or says things on screen and in the docs that aren't true (R7).
- **Output.** `docs/audit/AUDIT.md` in the repo. Each finding gives the file and line, what's wrong, how it was proven, how bad it is, and what the rewrite does instead. It feeds the spec.
- **Done when:**
  - [ ] R7. Every claim in the docs and on screen is checked against the code.
  - [ ] Wrong counts. Goal 1, Goal 2, the ledger and the row balance are checked on the sample data and the 19,000-row set.
  - [ ] Untrue screen text. Every string in `ui/` and `help.json` is checked against what the code does.
  - [ ] Values changed wrongly. Fills, splits, the jammed address and name parsing, program grouping and identity matching are checked against the proof workbook.
  - [ ] Every finding has a proof, such as a test, a row or a line of code, not just an opinion.
  - [ ] Every place the code could reach the network or an AI is listed, even if it's switched off.
- **Inputs.** The build zip from Joe (still needed). The context package in the repo.
- **Off limits.** Don't fix anything in the old code. The rewrite carries the fixes.
- **Model plan.** `haiku` agents map files and list strings. `sonnet` agents run the old tests and check claims. The chat model judges severity and writes the report.
- **Blocked on.** The source zip.

## T2. Offline and AI-free, provably

- **Goal.** The app can't reach the internet or any AI, and there's a test that proves it (R8, R9).
- **Output.** A spec section plus milestone files for the guard, the build and the installer.
- **Done when:**
  - [ ] R8. No AI code, model, API client or AI setting exists in the repo or the build.
  - [ ] R9. No network capability. There's no server or port. Python's network calls are blocked inside the app at startup. Network modules are stripped from the build where possible. The installer's firewall rule blocks the app's own executable.
  - [ ] Tests fail if any outbound connection, DNS lookup or HTTP library import is attempted, both from source and from the built app.
  - [ ] Every dependency is pinned with hashes. Nothing installs on a client machine.
  - [ ] Fonts (Archivo) and every asset ship inside the build.
  - [ ] All 24 fix plan items are mapped to milestones.
  - [ ] Signing uses a self-signed certificate with IT deployment steps, plus a documented switch to Azure Artifact Signing.
- **Inputs.** `docs/crosswalk-fix-plan.md` and the research output.
- **Model plan.** The chat model writes the guard design. `sonnet` drafts the milestone files.

## T3. Progress bars per process

- **Goal.** While anything processes, each step shows its own bar and a few words saying what's running (R3, R4).
- **Output.** A spec section, a prototype for the look, and a milestone file.
- **Done when:**
  - [ ] R3. One bar per step, with a count, like "Placing addresses, 4,210 of 7,412."
  - [ ] R4. A few-word message per bar, naming the file, and never more than one line.
  - [ ] The screen stays readable while a run goes. Controls that change data are held, with a caption saying why.
  - [ ] Once the run finishes, the bars fold into a short log with each step's time and what it found.
  - [ ] The engine reports progress per step and per row batch, not just per file, and a bar never moves backward.
  - [ ] Every long action has a bar, not just Process. That covers loading files, the preview of counts, lookups, matching people and writing files.
- **Model plan.** The chat model designs the event model. The prototype is built here.

## T4. Confidence level

- **Goal.** The user always sees how sure the tool is, built only from facts the engine checked (R2).
- **Output.** A spec section and a milestone file. The prototype shows the ledger version.
- **Done when:**
  - [ ] R2. The batch confidence is in the ledger at all times, as a word plus the reason, like "High. 6,084 of 7,412 rows passed every check."
  - [ ] Each same-person match shows its own level and the evidence behind it.
  - [ ] Each location shows its own level.
  - [ ] Batch rules. High means at least 95% of rows clean or decided, no open same-person pairs, and at least 95% of addresses placed with high confidence. Low means any of those is under 80%. Otherwise it's Medium. These live in one settings file.
  - [ ] When confidence is Low, Download waits until someone ticks that they've seen it, and the tick goes to the audit log.
  - [ ] No percentages and no letter grades on screen.
- **Decided without asking.** Match and location levels use the engine's existing scores and bands, listed in the spec as starting values to tune.

## T5. Show what happens to the data

- **Goal.** At every point, the user can see what the tool reads, changes, keeps and writes (R11).
- **Output.** A spec section, copy for every stage, and a milestone file.
- **Done when:**
  - [ ] R11. Every stage has one line saying what it reads, changes and writes.
  - [ ] A "Your data" page opens from the ledger, with a simple diagram of where data goes and what's never kept.
  - [ ] A summary before Process says in a few lines what the run will do.
  - [ ] A receipt after Download lists each file written and where it went.
  - [ ] Every sentence is checked against the code by a test. The audit found untrue copy before, so it can't happen again.

## T7. Research a new product name

- **Goal.** Replace "Crosswalk," which reads with an unwanted sexual orientation meaning (R12).
- **Output.** A shortlist of 5 in the chat for Joe to pick from. The pick then gets used in the spec.
- **Done when:**
  - [ ] R12. There are 5 names. Each one is plain, says what the tool does, and suits an organization that serves residents.
  - [ ] Each name is checked for other software with the same or a similar name, for odd or unwanted meanings, and for how it reads in a stage title and on the installer.
  - [ ] Each has one line on why it fits.
- **Model plan.** The chat model does the research inline with web search.

## T6. Rebuild spec and Claude Code handoff

- **Goal.** A plan detailed enough that Claude Code in the cloud rewrites the app without guessing (R1, R6).
- **Output.** These files in the repo:
  - `SPEC.md`
  - `docs/milestones/M01-...md` onward
  - `CLAUDE.md` for Code
  - the context package under `docs/context/`
  - a first prompt for Joe to paste into Code
- **Done when:**
  - [ ] R1. The spec covers every feature in the feature ledger, every hard rule and every audit fix.
  - [ ] R6. Each milestone has its goal, files, tests, done list, and the Windows checks Joe runs.
  - [ ] Code stops after each milestone.
  - [ ] The repo has the pushed context package and spec. Joe approves before anything gets pushed.
- **Blocked on.** T1, which needs the source, and T7, which needs Joe's pick.
