// Build docs/Crosswalk_Walkthrough.pptx: one slide per stage, each with its
// screenshot and the help text, and the narration script as speaker notes.
//   node tools/make_deck.js
const fs = require("fs");
const path = require("path");
const pptxgen = require("pptxgenjs");

const ROOT = path.resolve(__dirname, "..");
const HELP = JSON.parse(fs.readFileSync(path.join(ROOT, "ui", "help.json"), "utf8"));
const SHOTS = path.join(ROOT, "docs", "screenshots");
const OUT = path.join(ROOT, "docs", "Crosswalk_Walkthrough.pptx");

const NAVY = "1F3B63", INK = "1D1D1B", MUTED = "5B6470", PALE = "EEF3F7", WHITE = "FFFFFF", ACCENT = "B85042";

const pres = new pptxgen();
pres.layout = "LAYOUT_WIDE";            // 13.33 x 7.5 in
pres.author = "Crosswalk";
pres.title = "Crosswalk walkthrough";

function notesFor(key) {
  // the narration in docs/VIDEO_SCRIPT.md, section by stage
  const script = fs.readFileSync(path.join(ROOT, "docs", "VIDEO_SCRIPT.md"), "utf8");
  const map = { title: "1. What this is for", check: "2. Starting it", sources: "3. Adding your files",
    schema: "4. Columns and tidy-up", prepare: "4. Columns and tidy-up", map: "5. Matching columns",
    programs: "6. Programs", run: "7. Processing", review: "8. Fixing problems", queue: "8. Fixing problems",
    summary: "9. Results", export: "10. Download and next time", audit: "10. Download and next time",
    help: "11. Help is on every screen" };
  const head = map[key];
  if (!head) return "";
  const i = script.indexOf("## " + head);
  if (i < 0) return "";
  const j = script.indexOf("\n## ", i + 3);
  return script.slice(i, j < 0 ? undefined : j).replace(/^## .*\n/, "").replace(/_On screen:.*_\n?/g, "").replace(/_Pause.*_\n?/g, "").replace(/_Point.*_\n?/g, "").replace(/_Open.*_\n?/g, "").replace(/_Pick.*_\n?/g, "").trim();
}

// ---- title
{
  const s = pres.addSlide();
  s.background = { color: NAVY };
  s.addText("Crosswalk", { x: 0.8, y: 2.2, w: 11.7, h: 1.2, fontFace: "Cambria", fontSize: 54, bold: true, color: WHITE, isTextBox: true, margin: 0 });
  s.addText("Two numbers you can stand behind: how many people you serve, and how many in each program.",
    { x: 0.8, y: 3.5, w: 11.7, h: 0.9, fontFace: "Calibri", fontSize: 22, color: "CADCFC", isTextBox: true, margin: 0 });
  s.addText("Offline. Deterministic. Nothing merged on a guess. Every change on the record.",
    { x: 0.8, y: 4.6, w: 11.7, h: 0.6, fontFace: "Calibri", fontSize: 16, italic: true, color: "CADCFC", isTextBox: true, margin: 0 });
  s.addNotes(notesFor("title"));
}

// ---- the journey in one slide
{
  const s = pres.addSlide();
  s.background = { color: WHITE };
  s.addText("The journey", { x: 0.6, y: 0.4, w: 12, h: 0.8, fontFace: "Cambria", fontSize: 36, bold: true, color: NAVY, isTextBox: true, margin: 0 });
  const steps = ["Add your files", "Set up your columns", "Tidy up", "Match your columns", "Programs", "Process", "Fix problems", "Results", "Download"];
  const cols = 3, bw = 3.8, bh = 1.35, gx = 0.35, gy = 0.35, x0 = 0.6, y0 = 1.6;
  steps.forEach((t, i) => {
    const c = i % cols, r = Math.floor(i / cols);
    const x = x0 + c * (bw + gx), y = y0 + r * (bh + gy);
    s.addShape(pres.shapes.ROUNDED_RECTANGLE, { x, y, w: bw, h: bh, fill: { color: PALE }, line: { color: PALE }, rectRadius: 0.12 });
    s.addShape(pres.shapes.OVAL, { x: x + 0.2, y: y + 0.35, w: 0.65, h: 0.65, fill: { color: NAVY }, line: { color: NAVY } });
    s.addText(String(i + 1), { x: x + 0.2, y: y + 0.35, w: 0.65, h: 0.65, fontFace: "Calibri", fontSize: 18, bold: true, color: WHITE, align: "center", valign: "middle", isTextBox: true, margin: 0 });
    s.addText(t, { x: x + 1.05, y: y + 0.3, w: bw - 1.25, h: 0.75, fontFace: "Calibri", fontSize: 18, bold: true, color: INK, valign: "middle", isTextBox: true, margin: 0 });
  });
  s.addText("Or press one button on the first stage and go straight to Fix problems.", { x: 0.6, y: 6.7, w: 12, h: 0.5, fontFace: "Calibri", fontSize: 14, italic: true, color: MUTED, isTextBox: true, margin: 0 });
  s.addNotes("The nine stages. A first run walks all of them; a repeat run with clean files can press one button and go straight to what needs fixing.");
}

// ---- one slide per stage: screenshot left, text right
const ORDER = ["check", "sources", "schema", "prepare", "map", "programs", "run", "review", "queue", "summary", "export", "audit"];
const SHOT_OF = { check: "00_check.png", sources: "01_sources.png", schema: "02_schema.png", prepare: "03_prepare.png",
  map: "04_map.png", programs: "05b_programs_preview.png", run: "06_run.png", review: "07_review.png",
  queue: "07c_queue.png", summary: "08_summary.png", export: "09_export.png", audit: "10_audit.png" };

ORDER.forEach((key, i) => {
  const e = HELP.stages[key];
  const s = pres.addSlide();
  s.background = { color: WHITE };
  s.addText(e.title, { x: 0.6, y: 0.35, w: 12.1, h: 0.75, fontFace: "Cambria", fontSize: 32, bold: true, color: NAVY, isTextBox: true, margin: 0 });
  const shot = path.join(SHOTS, SHOT_OF[key]);
  if (fs.existsSync(shot)) {
    const buf = fs.readFileSync(shot);
    const w = buf.readUInt32BE(16), h = buf.readUInt32BE(20);
    // fit in a 7.2 x 5.6 box, keeping the ratio; tall (full-page) shots are cropped by the box
    let iw = 7.2, ih = iw * h / w;
    const opts = { x: 0.6, y: 1.3, w: iw, h: Math.min(ih, 5.6), data: "image/png;base64," + buf.toString("base64") };
    if (ih > 5.6) opts.sizing = { type: "crop", w: iw, h: 5.6, x: 0, y: 0 };
    s.addImage(opts);
    s.addShape(pres.shapes.RECTANGLE, { x: 0.6, y: 1.3, w: iw, h: Math.min(ih, 5.6), fill: { type: "none" }, line: { color: "D9DEE5", width: 1 } });
  }
  s.addText("WHY THIS EXISTS", { x: 8.2, y: 1.3, w: 4.5, h: 0.35, fontFace: "Calibri", fontSize: 11, bold: true, color: ACCENT, charSpacing: 2, isTextBox: true, margin: 0 });
  s.addText(e.purpose, { x: 8.2, y: 1.65, w: 4.5, h: 2.5, fontFace: "Calibri", fontSize: 13, color: INK, valign: "top", isTextBox: true, margin: 0, fit: "shrink" });
  s.addText("WHAT TO DO", { x: 8.2, y: 4.25, w: 4.5, h: 0.35, fontFace: "Calibri", fontSize: 11, bold: true, color: ACCENT, charSpacing: 2, isTextBox: true, margin: 0 });
  s.addText(e.how, { x: 8.2, y: 4.6, w: 4.5, h: 2.4, fontFace: "Calibri", fontSize: 13, color: INK, valign: "top", isTextBox: true, margin: 0, fit: "shrink" });
  s.addText(`${i + 1} / ${ORDER.length}`, { x: 12.0, y: 7.0, w: 0.9, h: 0.3, fontFace: "Calibri", fontSize: 10, color: MUTED, align: "right", isTextBox: true, margin: 0 });
  s.addNotes(notesFor(key));
});

// ---- help on every screen
{
  const e = HELP.elements.dupes;
  const s = pres.addSlide();
  s.background = { color: WHITE };
  s.addText("Help is on every screen", { x: 0.6, y: 0.35, w: 12.1, h: 0.75, fontFace: "Cambria", fontSize: 32, bold: true, color: NAVY, isTextBox: true, margin: 0 });
  const shot = path.join(SHOTS, "11_help.png");
  if (fs.existsSync(shot)) {
    const buf = fs.readFileSync(shot);
    s.addImage({ x: 0.6, y: 1.3, w: 7.2, h: 5.14, data: "image/png;base64," + buf.toString("base64") });
  }
  s.addText("Every stage and every complex element has a small ? button. Press it for what that thing is for in the real world and how to use it. The user guide is the same text, in order, with pictures.",
    { x: 8.2, y: 1.3, w: 4.5, h: 3, fontFace: "Calibri", fontSize: 14, color: INK, valign: "top", isTextBox: true, margin: 0 });
  s.addNotes(notesFor("help"));
}

// ---- closing
{
  const s = pres.addSlide();
  s.background = { color: NAVY };
  s.addText("Two numbers you can stand behind,\nand a trail that shows how you got them.", { x: 0.8, y: 2.4, w: 11.7, h: 1.8, fontFace: "Cambria", fontSize: 34, bold: true, color: WHITE, isTextBox: true, margin: 0 });
  s.addText("docs/USER_GUIDE.md  ·  docs/cheatsheets/  ·  docs/TECHNICAL.md  ·  the ? on every screen", { x: 0.8, y: 4.6, w: 11.7, h: 0.6, fontFace: "Calibri", fontSize: 16, color: "CADCFC", isTextBox: true, margin: 0 });
  s.addNotes("Where to find more: the user guide, the cheat sheets, the technical documentation for engineers, and the help button on every screen.");
}

pres.writeFile({ fileName: OUT }).then(() => console.log("wrote", path.relative(ROOT, OUT)));
