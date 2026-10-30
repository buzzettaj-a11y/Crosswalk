# Stage strip

The pinned row of nine stages plus Undo that replaces the hover rail. Each item is three lines: the number and technical name in `strip-kicker`, the plain name in `stage-name`, and a live caption saying what the stage holds right now. The caption is data, never decoration.

Four states. Current: `blue-100` fill, `blue-500` underline, `blue-700` text. Done with work: `ink` underline. Nothing to decide: `line-2` underline, so it reads as settled without pretending work happened. Not yet: no underline and a `muted` name. Undo sits at the right end behind a hairline, 176px wide, and names the decision it will take back. Under 1360 wide the names drop to 11.5px and Undo to 150px; the two longest names may wrap to a second line and the strip grows to fit. It never scrolls.
