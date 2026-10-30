# Crosswalk

The style guide for the client data tool. It runs offline, on one machine, for someone who does this a few times a year. Every rule here exists so that person can see where they are, what needs them, and what has already been decided, without reading a paragraph to find out.

This is the source of truth for the look. When the look changes, this changes in the same pass.

## Principles

1. **Color means something or it is not there.** Three hues, three meanings. Nothing is colored to look finished.
2. **The numbers never leave the screen.** The ledger holds rows in, where they stand, the two counts and location confidence, on every stage.
3. **Plain words first, the precise word beside it.** A stage is called Fix problems. Its kicker says REVIEW. One vocabulary, no mode switch.
4. **Square, flat, one pixel.** No radius, no shadow, no gradient. Borders separate things. A 3px rule on the top or bottom marks state. Never on the left.
5. **Real controls, drawn as real controls.** A button is a `<button>`. A choice is a `<select>` with a `<label>`. Text is at least 4.5:1 on whatever is behind it.

## Color

Warm gray ground (`bg-page`), white cards (`bg-card`), near-black ink (`ink`). The grays are toned, not neutral, so the page reads as paper rather than a spreadsheet.

Three signal hues, each with one meaning. They sit at the same lightness and chroma so none of them shouts over the others.

| Hue | Means | Where it appears |
| --- | --- | --- |
| `blue-500` | **Needs you.** A decision is waiting, or this is where you are. | Primary buttons, links, the current stage's underline, open rows in the ledger, the NEEDS YOU tag, callouts that ask for a decision. |
| `green-500` | **A person decided.** A human confirmed, split, renamed, approved or added this. | Confirmed tags, decided rows, a step added by you, a link confirmed by a reviewer. |
| `amber-500` | **Looks wrong.** The tool read the data and it does not fit. | A matched column that does not look like its field, a header row that looks like a title, a source with no program column, a value that differs where it should agree. |

Rules that follow from the table:

- A row that passed every check is `ink`, not green. Green is reserved for what a person did, because that is the accountability thread the audit log records.
- Amber names the thing that is off. Blue names where you act on it. A matching card with a bad column has an amber callout and a blue button inside it. They are never the same color.
- Set aside, removed, nothing to decide: `line-2` and `bg-surface`. Gray means settled and out of the way.
- Solid fills carry white text only on the 500 step. Tints (`*-100`) carry the 700 step of the same hue, or `ink`, or `muted`. All pairs clear 4.5:1.
- Source identity is not a color. A source is marked by a letter in a 16px ink square, the same letter for the same source on every stage of the batch. Color would collide with the three meanings above and would run out at nine tables.

### The ledger bar

A stacked bar, 10px tall, `line` border: clean in `ink`, still open in `blue-500`, set aside in `line-2`. The three numbers under it always add up to rows received, and the line under them says so.

## Type

Archivo, hosted from Google Fonts, in 400, 600 and 800. The app vendors the files for offline use; the system falls back to the system sans with the same weights.

Everything that labels is 800. Everything that explains is 400. There is no 600 in the current screens; keep it for a mid-weight if one is ever needed.

Kickers and tags are uppercase with tracking. Nothing else is uppercase.

Numbers that are compared sit in tabular figures.

## Spacing and shape

Multiples of four. Cards pad 14 to 16px. Rows in a list sit 5 to 8px apart with a 1px `line` border each. Sibling controls are laid out with flex and `gap`, never margins.

Radius is zero everywhere. The system is square and that is its character.

## Components

### Top bar

48px, `ink` fill, `on-dark` text. Mark, wordmark, then status on the right: offline, geocoder, when progress was last saved. Below 1360 wide, Close Crosswalk moves here as a bordered quiet button.

### Stage strip

One row, nine items plus Undo, pinned. Each item has three lines: strip-kicker (number and technical name), stage-name (plain name), caption (what it holds right now). States:

| State | Underline | Name | Fill |
| --- | --- | --- | --- |
| Current | `blue-500` | `blue-700` | `blue-100` |
| Done, had work | `ink` | `ink` | none |
| Nothing to decide | `line-2` | `ink` | none |
| Not yet | none | `muted` | none |

The third line is data, not decoration: "45 matched, 2 look wrong", "1,232 rows open", "nothing to decide". Undo sits at the right end, separated by a hairline, and names the decision it takes back. At 1440 wide each item is 140px; under 1360 the longest names may wrap to a second line and the strip grows to fit. It never scrolls.

### Ledger

A 280px column at 1360 wide and up. Sections, each with a kicker: This batch, Where they stand, The two counts (kicker in `blue-500`), Locations. A footer on `bg-surface` holds the system check line, the trust sentence, Close and Start over. Before a run, each section says what it does not know yet in one sentence.

Below 1360 the same numbers become a 44px band under the strip, one group per section, hairlines between, a Details link at the right. Content then takes the full width.

### Two-step header

Two equal cells on `line`, 2px apart. The active step is white with a `blue-500` STEP kicker. The other is `bg-surface` with a muted kicker. Each shows what remains, in numbers. Used in Fix problems (causes, then row by row). A stage with three jobs, like Programs, uses numbered section heads instead, because three cells would crowd the strip and the jobs are read top to bottom, not switched between.

### Numbered sections

A stage with several jobs done in order (Programs: which column, which names, preview) heads each with a bold 14px line that starts with its number, `1. Which column holds the program in each file`. The head carries the section's one-line instruction in `note` beside it and a quiet action at the right (Start again). Sections are separated by their own cards, never by rules.

### Grids

A grid remembers where it was scrolled and which page it was on across a redraw, so Next and Back keep the columns in view. Opening a different stage starts at the top.

### Callouts

A white card with a 3px top rule. Three kinds, by hue:

- Needs you: `blue-300` border, `blue-500` rule. A decision is asked for inside it.
- A person decided: `green-300` border, `green-500` rule. Rare as a card; usually a tag.
- Looks wrong: `amber-300` border, `amber-500` rule, `amber-700` title. The field it is about takes an `amber-300` input border.

Inside a callout, the primary button is always `blue-500`, whatever the callout's hue.

### Buttons

- Primary: `blue-500` fill, white text. One per region.
- Secondary: white fill, `line-2` border, `ink` text.
- Quiet: no fill, no border, underlined, `blue-500` for navigation and `ink-2` for a lesser action.
- Held: `bg-surface` fill, `muted` text, with a caption under it saying what releases it.

Height 36 to 40px. Label in `button` style. Every button says what it does when rested on.

### Tags

Uppercase `tag` style, no radius. Solid `blue-500` with white text for NEEDS YOU. Tinted `green-100` with `green-700` text and `green-300` border for confirmed. Outline `line-2` with `ink-2` text for a neutral fact (RECORDS, proposed by the tool).

### Rows and groups

A group row is: count (`count-row`, 58px min), title and note, actions on the right. Decided rows drop to `bg-surface` with the title in `ink-2` and a confirmed tag in place of buttons. A row that needs nothing is `bg-page` with a plain note.

Tidy up groups its steps by rule, by source or by origin. In every grouping, rows inside a group keep the order they run in. A step that changed nothing (a split that found no jammed rows) is an amber row, because the tool read the data and the step does not fit it.

### Source marks

A 16px `ink` square with a white letter, A through whatever the batch needs, assigned in the order files were added. The same letter follows the source through Tidy up, Match your columns, Programs, Fix problems and the queue. 14px inside a table cell.

### Forms

Labels 800 at 11.5px above the control. Inputs and selects: white, `line-2` border, 8 to 9px padding, 12.5px text. A note under the control in `caption`, muted. A control that looks wrong takes an `amber-300` border.

## Wording

Plain first. Add your files, Set up your columns, Tidy up, Match your columns, Programs, Process, Fix problems, Results, Download. The technical name rides in the kicker: SOURCES, SCHEMA, PREPARE, MAP, PROGRAMS, RUN, REVIEW, SUMMARY, EXPORT.

A problem says what it means and what to check. A button says what it does. A count says what it counts. A held control says what releases it. Every correction says it goes to the audit log.

No emoji. No exclamation marks. Numbers with thousands separators.

## Accessibility

Text at least 4.5:1 on its ground, 3:1 from 24px. The lightest gray for text is `muted`. Buttons are buttons. Inputs have labels. Icon-only controls carry an aria-label. Hit targets 36px or taller on desktop.

## Changes

- 2026-09-29, v1.2.1. American spelling throughout. No change to the look.
- 2026-09-22, v1.2. Nine stages. Programs is its own stage between Match your columns and Process, with three numbered sections and a preview of the counts. The two-step header is used in Fix problems only. Tidy up gains the calculated ZIP column. Grids keep their scroll position.
- 2026-09-22, v1.1. The product is Crosswalk. The old name is retired everywhere, the wordmark reads CROSSWALK and the close button reads Close Crosswalk.
- 2026-09-22, v1. First version. Adds green and amber to the single blue the app shipped with, sets the stage strip states, the ledger, the two-step header and the source marks.
