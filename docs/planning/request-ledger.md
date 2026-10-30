# Request ledger, Crosswalk rebuild plan (2026-10-30)

Source: Joe's /route message.

| # | Ask, in Joe's words | Type | Task |
| --- | --- | --- | --- |
| R1 | "how can i recreate this" | Build | T6 |
| R2 | "provide a confidence level to the user as they use the system" | Build | T4 |
| R3 | "more progress bars as individual processes are processing in the app" | Build | T3 |
| R4 | "as progress is moving, show messages explaining in a few words what is processing. nothing long and obstructive" | Build | T3 |
| R5 | "i want it to be clear whats happening" | Vision | all |
| R6 | "i want to hand this off to claude code in the cloud, so i need extremely detailed plan for this project" | Build | T6 |
| R7 | "analyse the current product and find where it is making mistakes or hallucinating" | Build | T1 |
| R8 | "make sure the application can run locally without being influenced by AI" | Change | T2 |
| R9 | "or reach out to any AI or the internet at all. there should be no capabilities to reach the internet" | Change | T2 |
| R10 | "make sure the system is easy to follow" | Vision | all |
| R11 | "understand what will happen to data" | Build | T5 |
| R12 | "Also I want research done to rename this product. Crosswalk gives a sexual orientation vibe" (added mid-stream, in the T1 answer) | Build | T7 |

## Steering

- S1. Claude Code in the cloud does the building. This chat produces the plan, not the code (from R6).
- S2. The plan has to be extremely detailed, enough for Code to work without guessing (from R6).

## Implied

- I1. The current source code. The audit (R7) and any rebuild need it, and it isn't in the project. -> T1
- I2. A GitHub repo. Claude Code in the cloud works from a repo, and none exists for Crosswalk. -> T6
- I3. A definition of what confidence is computed from, using only deterministic facts the engine already has (checks passed, geocode confidence, identity scores, open pairs). -> T4
- I4. Finer progress events from the engine. Today it reports per file, not per step or row, so more bars need the engine to say more. -> T3
- I5. Proof that the app can't reach the network, as a test that fails if any outbound connection is attempted. -> T2
- I6. The local web server port (127.0.0.1) is itself a network listener. "No capabilities to reach the internet" likely means replacing it with the pywebview bridge, as fix plan phase 2 already proposes. -> T2

## Tasks, in order

- T1. Audit the current build for mistakes and hallucinations (R7, I1)
- T2. Offline and AI-free, provably (R8, R9, I5, I6)
- T3. Progress bars per process with short messages (R3, R4, I4)
- T4. Confidence level as the user works (R2, I3)
- T5. Show what happens to the data (R11)
- T7. Research a new product name, shortlist of 5 (R12). Runs before T6 so the spec uses the new name.
- T6. Detailed rebuild spec and Claude Code handoff (R1, R6, I2)

Vision R5 and R10 apply to every task. Steering S1 and S2 apply to every task.

The message didn't trail off.
