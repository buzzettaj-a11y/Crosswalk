# Ledger

The permanent panel that keeps the batch's numbers on screen at every stage: this batch, where the rows stand, the two counts, and location confidence. It is the reason no stage repeats a stat strip of its own. At 1360 wide and up it is a 280px white column down the left with a `bg-surface` footer for the system check line, the trust sentence, Close and Start over. Below 1360 it becomes a 44px band under the stage strip with the same numbers in four groups and a Details link, and content takes the full width.

The stacked bar is 10px tall: clean in `ink`, still open in `blue-500`, set aside in `line-2`. The three numbers always add up to rows received and the caption under them says so. The two-counts kicker is the only `blue-500` kicker in the app, because those two numbers are the point of the work. Before a run, each section says in one sentence what it does not know yet rather than showing zeros.
