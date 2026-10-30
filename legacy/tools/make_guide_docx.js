// Build docs/Crosswalk_User_Guide.docx from ui/help.json and docs/screenshots/.
//   node tools/make_guide_docx.js
// The same text drives the help buttons in the app, so the guide cannot
// disagree with what the app says.
const fs = require("fs");
const path = require("path");
const {
  Document, Packer, Paragraph, TextRun, HeadingLevel, ImageRun, PageBreak,
  TableOfContents, AlignmentType, LevelFormat, Table, TableRow, TableCell,
  WidthType, ShadingType, BorderStyle,
} = require("docx");

const ROOT = path.resolve(__dirname, "..");
const HELP = JSON.parse(fs.readFileSync(path.join(ROOT, "ui", "help.json"), "utf8"));
const SHOTS = path.join(ROOT, "docs", "screenshots");
const OUT = path.join(ROOT, "docs", "Crosswalk_User_Guide.docx");

const ORDER = ["check", "sources", "schema", "prepare", "map", "programs", "run",
  "review", "queue", "summary", "export", "audit"];
const SHOT_OF = {
  check: "00_check.png", sources: "01_sources.png", schema: "02_schema.png",
  prepare: "03_prepare.png", map: "04_map.png", programs: "05_programs.png",
  run: "06_run.png", review: "07_review.png", queue: "07c_queue.png",
  summary: "08_summary.png", export: "09_export.png", audit: "10_audit.png",
};
const EXTRA_SHOTS = {
  sources: ["01b_sources_showdata.png", "Show data: the first rows, with the header row ticked."],
  programs: ["05b_programs_preview.png", "The preview of both counts, program by program."],
  review: ["07b_review_duplicates.png", "Duplicates within a file, shown side by side."],
};

const P = (text, opts = {}) => new Paragraph({
  children: [new TextRun({ text, ...(opts.run || {}) })],
  spacing: { after: 120 }, ...(opts.para || {}),
});
const H1 = (t) => new Paragraph({ text: t, heading: HeadingLevel.HEADING_1, spacing: { before: 320, after: 160 } });
const H2 = (t) => new Paragraph({ text: t, heading: HeadingLevel.HEADING_2, spacing: { before: 240, after: 120 } });
const H3 = (t) => new Paragraph({ text: t, heading: HeadingLevel.HEADING_3, spacing: { before: 180, after: 80 } });
const LABEL = (label, text) => new Paragraph({
  children: [new TextRun({ text: label + " ", bold: true }), new TextRun({ text })],
  spacing: { after: 140 },
});
const BULLET = (text) => new Paragraph({ text, numbering: { reference: "bullets", level: 0 }, spacing: { after: 60 } });
const NUM = (text) => new Paragraph({ text, numbering: { reference: "steps", level: 0 }, spacing: { after: 60 } });

function image(file, caption) {
  const p = path.join(SHOTS, file);
  if (!fs.existsSync(p)) return [];
  const buf = fs.readFileSync(p);
  // fit inside the text width (6.5in = 624px at 96dpi); keep the ratio from the PNG header
  const w = buf.readUInt32BE(16), h = buf.readUInt32BE(20);
  const width = 624, height = Math.round(h * (624 / w));
  return [
    new Paragraph({ children: [new ImageRun({ type: "png", data: buf, transformation: { width, height } })], spacing: { after: 60 }, alignment: AlignmentType.CENTER }),
    new Paragraph({ children: [new TextRun({ text: caption, italics: true, size: 18, color: "555555" })], alignment: AlignmentType.CENTER, spacing: { after: 200 } }),
  ];
}

const children = [];
children.push(new Paragraph({ children: [new TextRun({ text: "Crosswalk", bold: true, size: 64 })], spacing: { before: 2400, after: 200 } }));
children.push(new Paragraph({ children: [new TextRun({ text: "User guide", size: 40 })], spacing: { after: 400 } }));
children.push(P("How to take the client lists your systems export and turn them into two numbers you can stand behind: how many people you serve, and how many in each program."));
children.push(P("Built from the same text as the help buttons inside the app, so this guide and the app never disagree. Regenerate it with node tools/make_guide_docx.js after taking fresh screenshots with python tools/take_screenshots.py.", { run: { size: 18, color: "555555" } }));
children.push(new Paragraph({ children: [new PageBreak()] }));
children.push(H1("Contents"));
children.push(new TableOfContents("Contents", { hyperlink: true, headingStyleRange: "1-2" }));
children.push(new Paragraph({ children: [new PageBreak()] }));

children.push(H1("Before you start"));
children.push(P("Crosswalk takes the client lists your systems export, cleans them into one shape, places every address on the map, works out which records are the same person, and gives you two numbers: how many people you serve in all, and how many in each program. Nothing leaves your computer and nothing is written to disk until you download it."));
children.push(H2("Starting and stopping"));
children.push(BULLET("Windows: double-click Crosswalk.vbs. Mac: double-click Crosswalk.command. It opens in your browser."));
children.push(BULLET("The first time takes a minute or two while it downloads what it needs. That is the only step that uses the internet."));
children.push(BULLET("To stop, press Close Crosswalk at the foot of the menu. Closing the browser works too; the tool notices and stops on its own."));
children.push(BULLET("If it will not start, a message says why. The usual cause is Python not being installed; the message says where to get it."));
children.push(H2("Getting around"));
children.push(BULLET("The stages run down the left. The menu is a narrow strip; rest on it or press the grip to open it, and press the grip again to pin it."));
children.push(BULLET("Guided uses plain words. Advanced uses the precise terms and shows every control. Only the words change. The switch is at the foot of the menu."));
children.push(BULLET("Every stage and every complex element has a small ? button. Press it for what that thing is for and how to use it."));
children.push(BULLET("Undo the last change sits at the foot of the menu on every stage; the review stage has its own Undo last decision."));
children.push(BULLET("Try it with example data, on the first stage, loads made-up files so you can practice without touching client data."));

children.push(new Paragraph({ children: [new PageBreak()] }));
children.push(H1("The stages"));
ORDER.forEach((key, i) => {
  const e = HELP.stages[key];
  children.push(H2(`${i}. ${e.title}`));
  children.push(LABEL("Why this exists.", e.purpose));
  children.push(LABEL("What to do.", e.how));
  children.push(...image(SHOT_OF[key], e.title));
  if (EXTRA_SHOTS[key]) children.push(...image(EXTRA_SHOTS[key][0], EXTRA_SHOTS[key][1]));
});

children.push(new Paragraph({ children: [new PageBreak()] }));
children.push(H1("The elements that need a closer look"));
Object.values(HELP.elements).forEach(e => {
  children.push(H2(e.title));
  children.push(LABEL("Why this exists.", e.purpose));
  children.push(LABEL("What to do.", e.how));
});
children.push(...image("11_help.png", "A help panel, opened from a ? button."));

children.push(new Paragraph({ children: [new PageBreak()] }));
children.push(H1("Workflows"));
children.push(H2("A first run, end to end"));
["Add your files. Untick anything that is a summary rather than a list of people.",
 "On Match your columns, read the warnings; a wrong column is the mistake that matters most.",
 "On Programs, group the spellings and preview the counts until the program list looks right.",
 "Process.",
 "On Fix problems, work the groups: look ZIPs up, decide duplicates, accept or set aside. Apply once.",
 "On Results, decide any open pairs. The counts are final when none are open.",
 "Download the files, and save the set-up for next time."].forEach(s => children.push(NUM(s)));
children.push(H2("The quick run"));
children.push(P("Add your files, then press Process everything and show me what needs fixing. It stops only when something would make the run wrong, and says what."));
children.push(H2("Next quarter"));
children.push(P("Add the new files, load the saved set-up, read what fitted and what did not, then run."));
children.push(H2("When a file has no program column"));
children.push(P("On Match your columns, under Fill a field for this source only, type the program. Every row of that file counts under it."));
children.push(H2("When the tool cannot place an address"));
children.push(P("On the review group, look the ZIPs up from the street. A street in several ZIPs needs a house number; one the engine does not know needs a person."));
children.push(H2("When something looks wrong in the numbers"));
children.push(P("Open the audit trail from the menu. Filter by the file or search by the identifier: every change and every decision that touched that row is listed, by identifier and column name only."));

children.push(new Paragraph({ children: [new PageBreak()] }));
children.push(H1("Cheat sheets"));
children.push(P("One page each, for when you know what you want and need to be reminded how. The same pages are in docs/cheatsheets/ as text."));
const SHEETS = {
  "The two counts": { stages: ["summary"], elements: ["identity", "program_grouping", "program_preview"] },
  "Matching columns": { stages: ["map"], elements: ["column_check", "header_row", "source_defaults"] },
  "Programs": { stages: ["programs"], elements: ["program_grouping", "program_preview"] },
  "Fixing problems": { stages: ["review", "queue"], elements: ["group_decisions", "fill_lookup", "dupes"] },
  "Duplicates": { stages: [], elements: ["dupes", "identity"] },
  "Set-ups and the audit trail": { stages: ["audit"], elements: ["setups", "express", "calc_zip"] },
};
Object.entries(SHEETS).forEach(([title, s]) => {
  children.push(new Paragraph({ children: [new PageBreak()] }));
  children.push(H2(`Cheat sheet: ${title}`));
  const rows = [];
  [...s.stages.map(k => HELP.stages[k]), ...s.elements.map(k => HELP.elements[k])].forEach(e => {
    rows.push(new TableRow({ children: [
      new TableCell({ width: { size: 2400, type: WidthType.DXA }, shading: { type: ShadingType.CLEAR, fill: "EEF3F7" },
        children: [new Paragraph({ children: [new TextRun({ text: e.title, bold: true })] })] }),
      new TableCell({ width: { size: 3500, type: WidthType.DXA }, children: [new Paragraph({ text: e.purpose })] }),
      new TableCell({ width: { size: 3460, type: WidthType.DXA }, children: [new Paragraph({ text: e.how })] }),
    ] }));
  });
  children.push(new Table({
    width: { size: 9360, type: WidthType.DXA }, columnWidths: [2400, 3500, 3460],
    rows: [new TableRow({ tableHeader: true, children: ["What", "For", "Do"].map((h, i) => new TableCell({
      width: { size: [2400, 3500, 3460][i], type: WidthType.DXA }, shading: { type: ShadingType.CLEAR, fill: "1F3B63" },
      children: [new Paragraph({ children: [new TextRun({ text: h, bold: true, color: "FFFFFF" })] })] })) }), ...rows],
  }));
});

const doc = new Document({
  creator: "Crosswalk", title: "Crosswalk user guide",
  styles: { default: { document: { run: { font: "Calibri", size: 22 } } },
    paragraphStyles: [
      { id: "Heading1", name: "Heading 1", basedOn: "Normal", next: "Normal", quickFormat: true, run: { size: 36, bold: true, font: "Cambria", color: "1F3B63" } },
      { id: "Heading2", name: "Heading 2", basedOn: "Normal", next: "Normal", quickFormat: true, run: { size: 28, bold: true, font: "Cambria", color: "2F5F88" } },
      { id: "Heading3", name: "Heading 3", basedOn: "Normal", next: "Normal", quickFormat: true, run: { size: 24, bold: true } },
    ] },
  numbering: { config: [
    { reference: "bullets", levels: [{ level: 0, format: LevelFormat.BULLET, text: "\u2022", alignment: AlignmentType.LEFT, style: { paragraph: { indent: { left: 720, hanging: 360 } } } }] },
    { reference: "steps", levels: [{ level: 0, format: LevelFormat.DECIMAL, text: "%1.", alignment: AlignmentType.LEFT, style: { paragraph: { indent: { left: 720, hanging: 360 } } } }] },
  ] },
  sections: [{ properties: { page: { size: { width: 12240, height: 15840 }, margin: { top: 1440, right: 1440, bottom: 1440, left: 1440 } } }, children }],
});

Packer.toBuffer(doc).then(buf => { fs.writeFileSync(OUT, buf); console.log("wrote", path.relative(ROOT, OUT)); });
