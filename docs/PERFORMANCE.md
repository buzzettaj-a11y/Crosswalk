# Performance

SPEC 15 sets the budgets, and they're measured on Joe's Windows machine with Geosupport installed. Linux CI tracks the same numbers on the fake geocoder as a regression alarm, never as pass or fail. `tests/perf/budgets.toml` holds the budgets as numbers.

## How to measure

1. `make perf` builds the 19,000-row set with `tools/make_large_set.py`, runs it through the real session calls with `python -m wholecount.dev perf`, and writes `build/perf-report.txt` with `tools/perf_report.py`. On a computer with Geosupport it uses Geosupport. CI adds `PERF_FLAGS=--fake`.
2. On Windows, `tools\perf\measure_startup.ps1` starts the installed `Wholecount.exe` five times and prints the median time to the main window.
3. Paste both outputs on the pull request.

The perf command prints counts only: integer labels and one backend word.

## Joe's Windows machine, with Geosupport

Not yet measured. These rows fill in after Joe runs `make perf` and the startup script.

| Action | Budget | Measured |
| --- | --- | --- |
| Start to first screen | 3,000 ms | not yet measured |
| Add 15 files, 19,000 rows | 10,000 ms | not yet measured |
| Process 19,000 rows with Geosupport | 90,000 ms | not yet measured |
| Any click that doesn't start a job | 200 ms | not yet measured |
| Preview the counts, 19,000 rows | 10,000 ms | not yet measured |
| Download all output files | 10,000 ms | not yet measured |
| Memory, 19,000-row batch | 1,536 MB | not yet measured |

## Linux, fake geocoder

The cloud session, 2026-10-31, with the set from `--seed 20261030 --rows 19000 --files 15`. These numbers are the CI baseline in `tests/perf/baseline.json`. They aren't the Windows numbers, and the Process time isn't the Geosupport time.

| Action | Budget | Measured | Status |
| --- | --- | --- | --- |
| Add 15 files, 19,000 rows | 10,000 ms | 3,135 ms | ok |
| Process 19,000 rows | 90,000 ms | 31,573 ms | not accepted (fake geocoder) |
| Slowest stage switch | 200 ms | 3,534 ms | over |
| One decision | 200 ms | 9,141 ms | over |
| Preview the counts | 10,000 ms | 8,653 ms | ok |
| Download all output files | 10,000 ms | 3,155 ms | ok |
| Peak memory | 1,536 MB | 411 MB | ok |

## What was over, and what changed

The first full run had three rows over. Four local fixes, each with a test that the results are unchanged:

- **Download stage, 27.7 s to draw.** Match_Confidence was worked out one person at a time over every proposal and record. `master_match_confidences` now does it in one pass. The stage also built every output table twice per visit, and the export plan is now reused while its inputs are the same.
- **Download, 12.5 s.** The same one-pass confidence brought it to 3.2 s.
- **One decision, about 33 s.** A decision re-ran tidying, matching, standardizing, placing and the copy search, which no decision changes. A run after a decision now reuses them, and the name helpers keep recent answers in memory. That brought it to about 9 s.

## Still over

- **One decision: 9.1 s against 200 ms.** Each decision re-runs identity, programs and the counts over the whole batch, on the main thread, so the window waits. The five slowest functions in the profile of one decision on 19,000 rows (`cProfile`, cumulative):
  1. `wholecount.engine.identity.resolve`, 8.2 s, 3.2 s of it in its own loop
  2. `wholecount.engine.pipeline.copy_row`, 2.3 s over 38,000 calls
  3. `wholecount.engine.identity.score_pair`, 2.1 s over 67,600 calls
  4. `wholecount.engine.pipeline.person_row`, 1.3 s
  5. `wholecount.engine.addresskey.address_key`, 1.0 s

  Getting under 200 ms needs identity to rerun only the people a decision touches, or the decision to run as a job with its own progress. Both change how decisions flow, so neither is done here.
- **Slowest stage switch: 3.5 s against 200 ms.** It's the Download stage, which builds the export plan once per change so it can show each file's rows. The other eight stages draw in 0.1 to 0.7 s on 19,000 rows.
