/* Crosswalk front end. Vanilla JS, no build step, fully offline.
   State mirrors the prototype's logic class; every number comes from the API. */

const UI = {
  screen: "check",
  chrome: null,
  data: null,
  // local view state
  openGroup: null, gQ: "", gPage: 0,
  openTable: null, previewPane: null,
  qFilter: "pending", qPage: 0, qSel: 0, qEdits: {},
  activeTable: 0,
  addOp: { type: "clean", table: "", cols: [], col: "", case: "none",
           sanitize: false, strip_punct: false, delimLabel: "Comma  ,",
           delimCustom: "", maxsplit: 0, names: "" },
  runPoll: null,
  copied: false,
  sessions: null,
  resumeNotice: null,
  exampleNotice: null,
  undoNotice: null,
  confirmClose: false, beat: null, fixNotice: null, express: null,
  fillFor: null, fillData: null, fillPage: 0, qExtraCols: {},
  railOpen: false, railPinned: false, progSel: null, progWork: null, help: null, helpOpen: null,
  pendingGroups: {}, pendingDups: [],
  proposals: null, propPage: 0,
  sortCheck: { sort: "", dir: "asc" },
  sortPreview: { sort: "", dir: "asc" },
  sortGroup: { sort: "", dir: "asc" },
  sortQueue: { sort: "", dir: "asc" },
  sortCols: { sort: "", dir: "asc" },
  reviewTallies: null,
  qSelected: {}, qAllMatching: false, qNotice: "",
  qProblem: "", qSource: "", qQ: "", qPer: 12,
  confirmReset: false,
};

const SCREEN_BY_STAGE = ["check", "sources", "schema", "prepare", "map",
                         "programs", "run", "review", "summary", "export"];

/* ---------------- api ---------------- */
/* ---------------- busy: every request shows itself ----------------
   A thin bar at the top appears while any request is in flight, so a click
   is never followed by nothing. If the server is processing rows it says
   which phase and how far along, from its own progress; otherwise it just
   says it is working. */
let _pending = 0, _busyPoll = null;

function _busyShow() {
  const el = document.getElementById("busy");
  if (!el) return;
  el.hidden = false;
  document.getElementById("busy-text").textContent = "Working";
  el.querySelector(".busy-bar").classList.add("indeterminate");
  el.querySelector(".busy-bar i").style.width = "";
  if (!_busyPoll) {
    _busyPoll = setInterval(async () => {
      if (_pending <= 0) return;
      try {
        const r = await fetch("/api/run/status", { cache: "no-store" });
        const st = await r.json();
        if (st && st.state === "running") {
          _workingShow(st, _busyTitle || "Processing");
        }
      } catch (e) {}
    }, 350);
  }
}

let _busyTitle = "";
function _busyHide() {
  if (_pending > 0 || _runWatch) return;       // something still going
  const el = document.getElementById("busy");
  if (el) el.hidden = true;
  _workingHide();
  _busyTitle = "";
  if (_busyPoll) { clearInterval(_busyPoll); _busyPoll = null; }
}

/* While the server is processing in the background (a run started from the
   Process stage or the fast path), the bar follows its progress even though
   no request of ours is waiting. */
/* While the server is processing rows, the screen is grayed out and one calm
   card says what is happening: which file, which phase, and how many steps
   of the batch are left. The message changes once per file, not per row; the
   bar underneath moves on its own. */
function _workingShow(st, title) {
  const el = document.getElementById("working");
  if (!el) return;
  el.hidden = false;
  document.getElementById("working-title").textContent = title || "Processing";
  document.getElementById("working-msg").textContent = st.message || st.phase || "Getting ready";
  const left = st.steps_total
    ? (st.steps_left > 0 ? `${nf(st.steps_left)} of ${nf(st.steps_total)} steps left` : "Almost done")
    : "";
  document.getElementById("working-left").textContent = left;
  document.getElementById("working-fill").style.width = `${Math.max(3, Math.min(100, st.progress || 0))}%`;
}
function _workingHide() {
  const el = document.getElementById("working");
  if (el) el.hidden = true;
}

let _runWatch = null;
function watchRun(onDone, title) {
  if (_runWatch) return;
  _runWatch = setInterval(async () => {
    try {
      const r = await fetch("/api/run/status", { cache: "no-store" });
      const st = await r.json();
      if (st.state === "running") { _workingShow(st, title); return; }
      clearInterval(_runWatch); _runWatch = null;
      _workingHide();
      _busyHide();
      if (onDone) onDone(st);
    } catch (e) {}
  }, 300);
}

async function api(path, body, title) {
  if (title) _busyTitle = title;
  const opts = body === undefined ? {} : {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
  };
  _pending += 1;
  const t = setTimeout(_busyShow, 120);        // a fast answer never flickers
  try {
    const r = await fetch(path, opts);
    return await r.json().catch(() => ({}));
  } finally {
    clearTimeout(t);
    _pending -= 1;
    if (_pending <= 0) { _pending = 0; _busyHide(); }
  }
}

async function load(screen) {
  const changed = UI.screen !== screen;
  UI.screen = screen;
  const out = await api(`/api/ui?screen=${screen}`);
  UI.chrome = out.chrome;
  UI.data = out;
  if ((screen === "sources" || screen === "export") && !UI.setups) {
    UI.setups = await api("/api/setups");
  }
  render();
  // a different screen starts at the top; the same screen redrawn stays put
  if (changed) window.scrollTo(0, 0);
}

/* ---------------- icons (inline, stroke on currentColor) ---------------- */
const I = {
  menu: `<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M4 7h16M4 12h16M4 17h16"/></svg>`,
  close: `<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M6 6l12 12M18 6L6 18"/></svg>`,
  check: '<svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.4" stroke-linecap="square"><path d="M4 12.5l5 5L20 6.5"/></svg>',
  arrow: '<svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.2" stroke-linecap="square"><path d="M4 12h15M13 6l6 6-6 6"/></svg>',
  alert: '<svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.2" stroke-linejoin="round"><path d="M12 3L2 20h20L12 3z"/><path d="M12 10v4M12 17v.5"/></svg>',
  upload: '<svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.2" stroke-linecap="square"><path d="M12 16V4M6 9l6-6 6 6M4 20h16"/></svg>',
  download: '<svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.2" stroke-linecap="square"><path d="M12 4v12M6 11l6 6 6-6M4 20h16"/></svg>',
  search: '<svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.2"><circle cx="10.5" cy="10.5" r="6.5"/><path d="M15.5 15.5L21 21"/></svg>',
  shield: '<svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M12 3l8 3v6c0 5-3.5 8-8 9-4.5-1-8-4-8-9V6l8-3z"/></svg>',
};

/* ---------------- sorting ---------------- */
// One place decides how a sortable header looks and what clicking it does, so
// every grid in the app behaves the same way: click to sort, click again to
// reverse.
function sortHead(label, key, state, action, extraClass) {
  const on = state && state.sort === key;
  const dir = on ? (state.dir === "desc" ? "desc" : "asc") : "";
  const arrow = on ? (dir === "desc" ? " \u25be" : " \u25b4") : "";
  return `<th class="sortable ${on ? "sorted" : ""} ${extraClass || ""}"
    data-sortkey="${esc(key)}" data-sortaction="${esc(action)}"
    data-sortdir="${on && dir === "asc" ? "desc" : "asc"}"
    title="Sort by ${esc(label)}">${esc(label)}${arrow}</th>`;
}

// Sorting a table the browser already holds in full, used where there are no
// pages to fetch.
function sortRows(rows, state, getters) {
  if (!state || !state.sort) return rows;
  const get = getters[state.sort] || (r => "");
  const rev = state.dir === "desc" ? -1 : 1;
  return rows.slice().sort((a, b) => {
    const x = get(a), y = get(b);
    if (typeof x === "number" && typeof y === "number") return (x - y) * rev;
    return String(x).toLowerCase().localeCompare(String(y).toLowerCase()) * rev;
  });
}

function toggleSort(state, key, dir) {
  state.sort = key;
  state.dir = dir;
}

/* ---------------- utilities ---------------- */
const nf = (n) => Number(n || 0).toLocaleString("en-US");
const esc = (s) => String(s == null ? "" : s)
  .replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;")
  .replace(/"/g, "&quot;");

function el(html) {
  const t = document.createElement("template");
  t.innerHTML = html.trim();
  return t.content;
}

/* ---------------- rail ---------------- */
function renderRail() {
  const c = UI.chrome;
  const rail = document.getElementById("rail");
  const rows = c.stages.map((name, i) => {
    const n = i + 1;
    const unlocked = n <= c.maxStage;
    const current = c.stage === n;
    const done = n < c.stage;
    const meta = c.railMeta[String(n)] || c.railMeta[n] || "";
    return `<button class="stage ${current ? "cur" : ""}" data-goto="${n}"
      ${unlocked ? "" : "disabled"}>
      <span class="stage-n">0${n}</span>
      <span class="stage-body"><span class="stage-name">${name}</span>
        ${meta ? `<span class="stage-meta">${esc(meta)}</span>` : ""}</span>
      ${done ? `<span class="stage-done">${I.check}</span>` : ""}
    </button>`;
  }).join("");

  const chk = c.check;
  const checkLine = chk.fails
    ? `${chk.fails} problem(s) found`
    : chk.warns ? `${chk.warns} item(s) to review` : "everything looks correct";

  rail.innerHTML = `
    <button class="rail-grip" data-act="rail-toggle"
      title="${UI.railOpen ? "Hide the menu" : "Show the menu"}">${UI.railOpen ? I.close : I.menu}</button>
    <div class="rail-top">
      <div class="brandrow"><span class="mark"></span>
        <span class="wordmark">CROSSWALK</span></div>
      <div class="brand-sub">Offline client data cleaning and geocoding</div>
    </div>
    <nav class="rail-stages">${rows}</nav>
    <div class="rail-foot">
      <div class="seg mode-seg" title="Guided uses plain words. Advanced uses the precise terms and shows every control.">
        ${["Guided", "Advanced"].map(m => `
          <label class="seg-opt"><input type="radio" name="mode"
            ${c.mode === m ? "checked" : ""} data-mode="${m}">${m}</label>`).join("")}
      </div>
      <button class="check-line ${chk.status === "fail" ? "bad" : ""}"
        data-goto="0">${I.alert} System check: ${checkLine}</button>
      <div class="foot-note">Nothing leaves this machine. Exports are written
        only when you download them.</div>
      ${c.canUndo ? `<button class="btn btn-secondary restart"
        data-act="undo-change">Undo the last change${c.undoLabel
          ? `: ${esc(c.undoLabel)}` : ""}</button>` : ""}
      <button class="btn btn-secondary restart" data-act="open-audit"
        title="Everything that changed in this session and who changed it, no client data">Audit trail</button>
      <button class="btn btn-secondary restart" data-act="close-app">Close Crosswalk</button>
      <button class="btn btn-secondary restart ${UI.confirmReset ? "armed" : ""}"
        data-act="restart">${UI.confirmReset
          ? "Click again to clear everything" : "Start over"}</button>
      ${UI.confirmReset ? `<div class="foot-note" style="margin-top:6px">
        This clears uploaded files, staging steps, mapping, results and every
        review decision. Downloaded files are not affected.</div>` : ""}
      <div class="stamps">
        ${c.stamps.map(([k, v]) => `<div class="stamp">
          <span class="stamp-k">${k}</span>
          <span class="stamp-v ${k === "BACKEND" && v.indexOf("sample") >= 0 ? "warn" : ""}">${esc(v)}</span>
        </div>`).join("")}
      </div>
    </div>`;
}

/* ---------------- screen chrome ---------------- */
/* ---------------- help ----------------
   Every stage and every complex element has a "?" that opens a short panel:
   what this is for in the real world, and how to use it. The text comes from
   ui/help.json, which the user guide and cheat sheets are also built from. */
function helpBtn(kind, id) {
  return `<button class="helpbtn" data-help="${kind}:${id}" title="What is this for?" aria-label="Help">?</button>`;
}

function vHelpPanel() {
  const h = UI.helpOpen;
  if (!h) return "";
  const [kind, id] = h.split(":");
  const entry = (UI.help && UI.help[kind === "stage" ? "stages" : "elements"] || {})[id];
  if (!entry) return "";
  return `<div class="helpwrap">
    <div class="helpcard">
      <div class="helpcard-head"><b>${esc(entry.title)}</b>
        <button class="btn btn-ghost" data-act="help-close">Close</button></div>
      <div class="helpcard-k">What it is for</div>
      <div class="helpcard-p">${esc(entry.purpose)}</div>
      <div class="helpcard-k">How to use it</div>
      <div class="helpcard-p">${esc(entry.how)}</div>
    </div></div>`;
}

const STAGE_HELP = { 0: "check", 1: "sources", 2: "schema", 3: "prepare", 4: "map",
  5: "programs", 6: "run", 7: "review", 8: "summary", 9: "export" };

function stageHead(stage, actions) {
  const h = (UI.chrome.heading || {})[String(stage)] || ["", ""];
  const total = (UI.chrome.stages || []).length || 8;
  const kick = stage === 0 ? "Stage 00"
    : `Stage ${String(stage).padStart(2, "0")} of ${String(total).padStart(2, "0")}`;
  return header(kick, h[0], h[1],
    `${helpBtn("stage", STAGE_HELP[stage] || "check")}${actions || ""}`);
}

function header(kicker, title, subtitle, actions) {
  return `<div class="shead">
    <div class="shead-text">
      <div class="kicker">${kicker}</div>
      <h2>${title}</h2>
      <div class="ssub">${subtitle}</div>
    </div>
    <div class="shead-actions">${actions || ""}</div>
  </div><div class="hr hr2"></div>`;
}

function continueBtn(label, disabled, act) {
  return `<button class="btn btn-primary" data-act="${act || "continue"}"
    ${disabled ? "disabled" : ""}>${label} ${I.arrow}</button>`;
}

/* ---------------- screens ---------------- */
function vCheck() {
  const d = UI.data.check;
  const v = d.verdict;
  const tag = (s) => s === "ok" ? "tag tag-neutral"
    : s === "warn" ? "tag tag-outline" : "tag tag-accent";
  const word = (s) => s === "ok" ? "ok" : s === "warn" ? "check" : "problem";
  return `
    ${stageHead(0, continueBtn("Continue to Sources"))}
    <div class="band ${v.status === "ok" ? "" : "band-warn"}">
      ${I.alert}<div><b>${v.status === "ok" ? "Ready for real data."
        : "Fine for a trial, not ready for real client data."}</b>
      <div class="band-sub">${esc(v.detail)}</div></div>
    </div>
    <table class="table"><thead><tr>
      ${sortHead("Check", "name", UI.sortCheck, "check")}
      ${sortHead("Status", "status", UI.sortCheck, "check")}
      ${sortHead("Detail", "detail", UI.sortCheck, "check")}
    </tr></thead>
    <tbody>${sortRows(d.checks, UI.sortCheck, {
        name: c => c.name,
        status: c => ({ fail: 0, warn: 1, ok: 2 })[c.status],
        detail: c => c.detail,
      }).map(c => `<tr>
      <td style="white-space:nowrap;font-weight:600">${esc(c.name)}</td>
      <td><span class="${tag(c.status)}">${word(c.status)}</span></td>
      <td class="text-muted" style="font-size:13px">${esc(c.detail)}</td>
    </tr>`).join("")}</tbody></table>
    ${vResume()}
    <div class="card"><div class="card-title">Support report</div>
      <div class="card-body">Version and configuration details only, never
      client data. Safe to paste into a message.</div>
      <div><button class="btn btn-secondary" data-act="copy-report">
        ${UI.copied ? "Copied" : "Copy report"}</button></div>
      <textarea class="input mono" id="report" rows="6" readonly>${esc(d.report)}</textarea>
    </div>`;
}

function vSetups() {
  const s = UI.setups;
  const rep = UI.setupReport;
  const list = !s ? "" : !s.setups.length
    ? `<div class="text-muted" style="font-size:12px">No saved set-ups yet.</div>`
    : `<div class="list">${s.setups.map(x => `
      <div class="lrow ${x.broken ? "off" : ""}">
        <div class="lmain">
          <div class="lline"><span class="lname">${esc(x.name)}</span>
            <span class="text-muted" style="font-size:11.5px">saved ${esc(x.saved_at)}${x.version ? `, version ${esc(x.version)}` : ""}</span></div>
          <div class="ldesc">${x.broken ? `<b>Cannot be read:</b> ${esc(x.broken)}`
            : `${x.files.length} file(s): ${x.files.map(f => esc(f.split(" :: ")[0])).join(", ")}${x.note ? `. ${esc(x.note)}` : ""}`}</div>
        </div>
        ${x.broken ? "" : `<button class="btn btn-secondary" data-setupcheck="${esc(x.name)}"
          title="Check this set-up against the files loaded now and this version of the tool, without changing anything">Check</button>`}
        <button class="btn btn-ghost" data-setupdel="${esc(x.name)}" title="Delete this saved set-up">Delete</button>
      </div>`).join("")}</div>`;
  const report = rep ? `<div class="band ${rep.ok ? "band-ok" : "band-warn"}" style="margin-top:10px">
    ${rep.ok ? I.check : I.alert}<div style="flex:1">
      <b>${rep.ok ? `"${esc(rep.name)}" fits the files loaded now.` : `"${esc(rep.name)}" does not fully fit: ${nf(rep.problems.length)} problem(s).`}</b>
      ${rep.notes.map(n => `<div class="band-sub">${esc(n)}</div>`).join("")}
      ${rep.problems.map(n => `<div class="band-sub"><b>Problem:</b> ${esc(n)}</div>`).join("")}
      ${rep.applies.length ? `<details style="margin-top:6px"><summary style="font-size:12px;cursor:pointer">What will load (${rep.applies.length})</summary>
        <div class="band-sub">${rep.applies.map(esc).join("<br>")}</div></details>` : ""}
      <div style="margin-top:8px;display:flex;gap:8px;flex-wrap:wrap">
        <button class="btn btn-primary" data-setupload="${esc(rep.name)}"
          title="${rep.ok ? "Apply this set-up to the files loaded now" : "Apply the parts that fit; the problems above are skipped, not guessed"}">
          ${rep.ok ? "Load this set-up" : "Load what fits and skip the rest"}</button>
        <button class="btn btn-ghost" data-act="setup-dismiss">Not now</button></div>
    </div></div>` : "";
  return `<div class="card" style="margin-top:14px">
    <div class="card-title">Saved set-ups ${helpBtn("element", "setups")}</div>
    <div class="card-body" style="opacity:1">
      A set-up is the work of configuring a run: which files, the column set-up,
      the tidy-up steps, the matching, the program grouping, what counts as a
      duplicate. Save it once and load it next time instead of doing it again.
      No client data is saved. When you load one, every part is checked against
      the files loaded now and this version of the tool, and anything that no
      longer fits is named rather than applied blindly.</div>
    ${list}${report}
    <div class="addgrid" style="margin-top:10px">
      <label class="field"><label>Save the current set-up as</label>
        <input class="input" id="setupname" placeholder="for example Quarterly crosswalk" value="${esc(UI.setupName || "")}"></label>
      <label class="field"><label>Note (optional)</label>
        <input class="input" id="setupnote" placeholder="what this set-up is for" value="${esc(UI.setupNote || "")}"></label>
      <button class="btn btn-secondary" data-act="setup-save" ${UI.data.sources && UI.data.sources.stats.tables ? "" : "disabled"}
        title="Save everything configured so far, under this name">Save set-up</button>
    </div>
  </div>`;
}

async function loadSetups() {
  UI.setups = await api("/api/setups");
  render();
}

function vExpress() {
  const x = UI.express;
  let body = "";
  if (x && x.running) {
    body = `<div class="band"><div class="spin"></div><div>
      <b>Processing everything.</b></div></div>`;
  } else if (x && x.blockers && x.blockers.length) {
    body = `<div class="band band-warn">${I.alert}<div>
      <b>It cannot run yet.</b>
      ${x.blockers.map(b => `<div class="band-sub">${esc(b.text)}</div>`).join("")}
      <div class="xactions">
        ${x.blockers.every(b => b.missing.length === 1 && b.missing[0] === "Client_ID")
          ? `<button class="btn btn-primary" data-act="express-relax-id">
               Mark Client ID as optional and continue</button>
             <span class="text-muted" style="font-size:11.5px">Files without an
               identifier cannot be checked for exact duplicates, but everything
               else works.</span>`
          : ""}
        <button class="btn btn-secondary" data-goto="4">Match the columns myself</button>
      </div></div></div>`;
  } else if (x && x.warnings && x.warnings.length) {
    body = `<div class="band band-warn">${I.alert}<div>
      <b>It can run, but ${x.warnings.length} matched column(s) do not look right.</b>
      ${x.warnings.map(w => `<div class="band-sub">${esc(w.text)}</div>`).join("")}
      <div class="xactions">
        <button class="btn btn-secondary" data-goto="4">Fix them first</button>
        <button class="btn btn-ghost" data-act="express-anyway">Run anyway</button>
      </div></div></div>`;
  }
  return `<div class="express">
    <div class="express-row">
      <div>
        <div class="express-title">Skip the steps ${helpBtn("element", "express")}</div>
        <div class="express-sub">Tidy up, match the columns and process using
          what the tool proposes, then go straight to the problems. You can
          still visit any stage afterward.</div>
      </div>
      <button class="btn btn-primary" data-act="express" ${x && x.running ? "disabled" : ""}>
        Process everything and show me what needs fixing ${I.arrow}</button>
    </div>
    ${body}
  </div>`;
}

async function expressGo(despite) {
  UI.express = { running: true, phase: "Checking the files" };
  render();
  const ck = await api("/api/express/check");
  if (!ck.ok) {
    UI.express = { blockers: ck.blockers || [], warnings: [], why: ck.why };
    return render();
  }
  if (ck.warnings.length && !despite) {
    UI.express = { warnings: ck.warnings, blockers: [] };
    return render();
  }
  const r = await api("/api/express/run", { despite_warnings: !!despite });
  if (!r.ok) {
    UI.express = { blockers: r.blockers || [], warnings: r.warnings || [] };
    return render();
  }
  UI.express = { running: true, phase: "Processing" };
  render();
  await new Promise(resolve => watchRun(resolve, "Processing everything"));
  UI.express = null;
  UI.chrome = (await api("/api/ui?screen=review")).chrome;
  load("review");
}

function vPreviewPane(key, which) {
  const scrollkey = `preview:${key}:${which}`;
  const p = UI.previewPane;
  if (!p || p.key !== key || p.which !== which) {
    loadPreviewPane(key, which);
    return `<div class="gpreview text-muted">Loading data…</div>`;
  }
  if (!p.data.ok) return `<div class="gpreview text-muted">No data to show.</div>`;
  const d = p.data;
  const head = d.columns.map(c => {
    const isNew = d.added.indexOf(c) >= 0;
    return sortHead(c + (isNew ? " (added)" : ""), c,
                    { sort: d.sort, dir: d.dir }, "preview",
                    isNew ? "colnew" : "");
  }).join("");
  const body = d.rows.map(r => `<tr>${r.map((v, i) => {
    const isNew = d.added.indexOf(d.columns[i]) >= 0;
    return `<td class="mono ${isNew ? "cellnew" : ""}" style="font-size:12px">${esc(v) || '<span class="text-muted">blank</span>'}</td>`;
  }).join("")}</tr>`).join("");
  return `<div class="gpreview">
    <div class="pvtools">
      <span class="text-muted" style="font-size:12px">
        Rows ${nf(d.first)} to ${nf(d.last)} of ${nf(d.total)}
        ${d.added.length ? ` · ${d.added.length} column(s) added by the prepare steps` : ""}</span>
      <span style="flex:1"></span>
      <button class="btn btn-secondary" data-ppage="first" ${d.page === 0 ? "disabled" : ""}>First</button>
      <button class="btn btn-secondary" data-ppage="prev" ${d.page === 0 ? "disabled" : ""}>Prev</button>
      <span class="text-muted mono" style="font-size:12px">${d.page + 1} / ${nf(d.pages)}</span>
      <button class="btn btn-secondary" data-ppage="next" ${d.page >= d.pages - 1 ? "disabled" : ""}>Next</button>
    </div>
    <div class="text-muted" style="font-size:11.5px;margin:4px 0">${nf(d.columns.length)} columns, ${nf(d.total)} rows. The grid scrolls sideways inside its box; the first column stays put.</div>
    <div class="pvscroll pinfirst" data-scrollkey="${esc(scrollkey)}"><table class="table pvtable">
      <thead><tr>${head}</tr></thead><tbody>${body}</tbody></table></div>
  </div>`;
}

async function loadPreviewPane(key, which, page) {
  const pg = page === undefined
    ? (UI.previewPane && UI.previewPane.key === key ? UI.previewPane.data.page : 0)
    : page;
  const s = UI.sortPreview;
  const data = await api(`/api/preview?key=${encodeURIComponent(key)}`
    + `&which=${which}&page=${pg || 0}`
    + `&sort=${encodeURIComponent(s.sort || "")}&dir=${s.dir || "asc"}`);
  UI.previewPane = { key, which, data };
  render();
}

function vResume() {
  const s = UI.sessions;
  if (!s) { loadSessions(); return ""; }
  const rows = (s.sessions || []).map(x => `
    <div class="lrow">
      <div class="lmain">
        <div class="lline"><span class="lname">${esc(x.summary)}</span>
          <span class="tag tag-neutral">${x.expires_in_days} day${x.expires_in_days === 1 ? "" : "s"} left</span></div>
        <div class="ldesc">Saved ${esc((x.saved_at || "").replace("T", " "))}.
          ${x.sources.length ? "Files: " + x.sources.map(esc).join(", ") : "No files recorded."}</div>
      </div>
      <button class="btn btn-secondary" data-resume="${esc(x.id)}">Resume</button>
      <button class="btn btn-ghost" data-dropsession="${esc(x.id)}">Delete</button>
    </div>`).join("");
  return `<div class="card">
    <div class="card-title">Saved progress</div>
    <div class="card-body" style="opacity:1">
      Your schema, staging steps, mapping and review decisions are saved as you
      work, so a closed window does not lose them. Uploaded files are not saved,
      so resuming asks for the same files again and reattaches your decisions to
      them. Saved progress is deleted after ${s.retention_days} days.
    </div>
    <label class="ckline"><button class="ckbox ${s.autosave ? "on" : ""}"
      data-autosave="${s.autosave ? 0 : 1}">${s.autosave ? I.check : ""}</button>
      Save my progress while I work</label>
    ${rows ? `<div class="list">${rows}</div>`
      : '<div class="text-muted" style="font-size:12.5px">No saved progress yet.</div>'}
  </div>`;
}

function qUrl() {
  const s = UI.sortQueue;
  return `/api/queue?filter=${UI.qFilter}&page=${UI.qPage}&sel=${UI.qSel}`
    + `&sort=${encodeURIComponent(s.sort || "")}&dir=${s.dir || "asc"}`
    + `&problem=${encodeURIComponent(UI.qProblem || "")}`
    + `&source=${encodeURIComponent(UI.qSource || "")}`
    + `&q=${encodeURIComponent(UI.qQ || "")}&per=${UI.qPer || 12}`;
}

async function refreshQueue() {
  UI.data.queue = await api(qUrl());
  UI.chrome = (await api("/api/ui?screen=queue")).chrome;
  render();
}

function bulkScope() {
  const q = UI.data.queue;
  if (UI.qAllMatching) {
    return { all_matching: true, filter: UI.qFilter, problem: UI.qProblem,
             source: UI.qSource, q: UI.qQ };
  }
  return { rids: Object.keys(UI.qSelected).filter(k => UI.qSelected[k]) };
}

async function loadSessions() {
  UI.sessions = await api("/api/sessions");
  render();
}

function vSources() {
  const d = UI.data.sources;
  const stats = [["Source files", d.stats.files], ["Tables included", d.stats.tables],
    ["Rows staged", nf(d.stats.rows)], ["Corrections to apply", nf(d.stats.corr), true]];
  const rows = d.tables.map(t => {
    const on = d.included[t.key];
    const open = UI.openTable === t.key;
    return `<div class="lrow-wrap">
      <div class="lrow">
      <button class="ckbox ${on ? "on" : ""}" data-include="${esc(t.key)}"
        data-on="${on ? 0 : 1}">${on ? I.check : ""}</button>
      <div class="lmain">
        <div class="lline"><span class="lname">${esc(t.file)}</span>
          <span class="lrange mono">${esc(t.sheet ? t.sheet + " " : "")}${esc(t.range)}</span>
          <span class="tag ${t.kind === "records" ? "tag-neutral" : "tag-neutral"}">${esc(t.kind)}</span>
          ${t.sensitive.length ? `<span class="tag tag-accent">${esc(t.sensitive[0].toUpperCase())} present</span>` : ""}
          ${t.marker ? `<span class="tag tag-outline">confirm source of truth</span>` : ""}
        </div>
        <div class="ldesc">${nf(t.rows)} rows, ${t.cols} columns, ${t.fill}% filled.
          ${esc(t.reason)}.</div>
      </div>
      ${t.headerWrong ? `<span class="tag tag-accent" title="${esc(t.headerWhy)}">check the header row</span>` : ""}
      <button class="btn btn-ghost" data-table-preview="${esc(t.key)}">
        ${open ? "Hide data" : "Show data"}</button>
      </div>
      ${open ? vHeaderRow(t) + vPreviewPane(t.key, "raw") : ""}
    </div>`;
  }).join("");
  const corr = d.corrections.map(c => `
    <div class="lrow corr-row">
      <div class="lmain"><div class="lline">
        <span class="lname">${esc(c.name)}</span>
        <span class="tag tag-accent">corrections</span></div>
      <div class="ldesc">Recognized as a corrections file (${nf(c.rows)} rows).
        Fixes apply to matching rows, then those rows are re-validated and
        geocoded like any other. Never treated as a source.</div></div>
    </div>`).join("");
  return `
    ${stageHead(1, continueBtn("Continue to Schema", !d.stats.tables))}
    ${UI.fixNotice && UI.screen === "sources" ? `<div class="band band-ok">${I.check}<div><b>${esc(UI.fixNotice)}</b></div></div>` : ""}
    ${UI.exampleNotice ? `<div class="band">${I.check}<div>
      <b>Example data loaded.</b><div class="band-sub">${esc(UI.exampleNotice)}</div>
      </div></div>` : ""}
    ${UI.resumeNotice ? `<div class="band">${I.alert}<div>
      <b>Progress restored.</b><div class="band-sub">
      ${UI.resumeNotice.decisions} review decision(s) and your settings are back.
      Upload the same source files again to continue:
      ${(UI.resumeNotice.sources || []).map(esc).join(", ") || "no files recorded"}.
      </div></div></div>` : ""}
    ${d.stats.tables ? vExpress() : ""}
    ${vSetups()}
    <div class="statstrip">${stats.map(([k, v, warn]) => `
      <div class="stat"><div class="stat-n ${warn && v !== "0" ? "warn" : ""}">${v}</div>
      <div class="stat-k">${k}</div></div>`).join("")}</div>
    <div class="dropzone">
      ${I.upload}
      <div><b>Drop files here, or browse</b>
      <div class="text-muted" style="font-size:12px">csv, tsv, xlsx, json, xml.
      A re-uploaded Manual_Review_Needed file is recognized as corrections.</div></div>
      <label class="btn btn-secondary">Browse
        <input type="file" id="filepick" multiple hidden></label>
      <button class="btn btn-ghost" data-act="example">Try it with example data</button>
    </div>
    <div class="list">${rows || `<div class="lrow"><div class="ldesc">No files yet.</div></div>`}${corr}</div>`;
}

function vSchema() {
  const d = UI.data.schema;
  const ed = d.editable;
  const row = (f, i) => {
    if (!ed) {
      return `<tr>
        <td class="mono text-muted">${i + 1}</td>
        <td style="font-weight:600">${esc(f.label)}</td>
        <td class="text-muted" style="font-size:12.5px">${esc(builtinLogic(f))}</td>
        <td class="mono">${esc(f.dtype || "str")}</td>
        <td class="mono">${lengthText(f)}</td>
        <td class="mono">${esc(f.default || "")}</td>
        <td>${f.required ? '<span class="tag tag-accent">required</span>'
          : f.role === "custom" ? '<span class="tag tag-outline">custom</span>' : ""}</td>
      </tr>`;
    }
    return `<tr>
      <td class="mono text-muted">${i + 1}</td>
      <td><input class="input" data-sf="label" data-i="${i}" value="${esc(f.label)}"></td>
      <td class="text-muted" style="font-size:12px">${esc(builtinLogic(f))}</td>
      <td><select class="input" data-sf="dtype" data-i="${i}">
        ${d.types.map(t => `<option ${t === (f.dtype || "str") ? "selected" : ""}>${t}</option>`).join("")}
      </select></td>
      <td><input class="input mono" type="number" min="0" style="max-width:78px"
        data-sf="length" data-i="${i}" value="${esc(f.length || 0)}"
        title="The longest value this field may hold, counted in characters. 0 means no limit.">
        <div class="fnote">${lengthText(f)}</div></td>
      <td><input class="input mono" data-sf="default" data-i="${i}"
             style="max-width:130px" placeholder="none"
             value="${esc(f.default || "")}">
          ${f.role === "Client_ID" && f.default
            ? '<div class="fnote bad">A shared identifier makes separate people look like duplicates.</div>'
            : ""}</td>
      <td><button class="ckbox ${f.required ? "on" : ""}" data-sreq="${i}"
        data-on="${f.required ? 0 : 1}">${f.required ? I.check : ""}</button></td>
      <td><button class="btn btn-ghost" data-sdel="${i}">Remove</button></td>
    </tr>`;
  };
  return `
    ${stageHead(2, continueBtn("Continue to Prepare"))}
    <div class="twocol">
      <div>
        <table class="table"><thead><tr><th>#</th><th>Field</th>
          <th>Built-in logic</th><th>Type</th><th>Longest value allowed</th>
          <th>Default</th><th>Required</th>
          ${ed ? "<th></th>" : ""}</tr></thead>
        <tbody>${d.fields.map(row).join("")}</tbody></table>
        ${ed ? `<div class="addgrid" style="margin-top:12px">
          <label class="field"><label>Add a custom field</label>
            <input class="input" id="newfield" placeholder="Output header, for example Program"></label>
          <label class="field"><label>Type</label>
            <select class="input" id="newtype">${d.types.map(t => `<option>${t}</option>`).join("")}</select></label>
          <label class="field"><label>Longest value (0 = any)</label>
            <input class="input mono" id="newlen" type="number" min="0" value="0"
              title="The longest value this field may hold, counted in characters."></label>
          <label class="field"><label>Default value</label>
            <input class="input" id="newdefault" placeholder="optional"></label>
          <button class="btn btn-secondary" data-act="add-field">Add field</button>
          <button class="btn btn-ghost" data-act="reset-schema">Reset to default</button>
        </div>
        <div class="text-muted" style="font-size:11.5px;margin-top:8px">
          Built-in roles keep their geocoding and validation under any label.
          New rows are custom passthrough fields: cleaned, length and type
          checked, and carried through to the output. Max length 0 means
          unlimited. A default value fills any field, built-in or custom, when
          the source leaves it blank; it never replaces a value the source
          provided, and every use is recorded in the audit log. A defaulted
          value is still validated: a City default that disagrees with the ZIP
          is sent to review rather than accepted. A value that fails its type or length routes the row to
          review; it is never truncated or coerced.</div>`
        : `<div class="text-muted" style="font-size:12px;margin-top:8px">
          Switch to Advanced to rename labels, change types and lengths, toggle
          required, add custom fields, or remove fields.</div>`}
      </div>
      <div class="sidecol">
        <div class="card"><div class="card-title">How a row is tested</div>
          <div class="rulelist">
            <div><b>Type.</b> A value that is not the declared type routes the
              row to review. Never coerced silently.</div>
            <div><b>Length.</b> Too long routes to review. Never truncated.</div>
            <div><b>Required.</b> A blank required field routes to review.
              City and State may fill from the ZIP.</div>
          </div></div>
        <div class="card"><div class="card-title">Test fit by source</div>
          ${d.fit.map(f => `<div class="fitrow">
            <div class="fitname mono">${esc(shortKey(f.table))}</div>
            <div class="fitbar"><i style="width:${Math.round(f.have / f.total * 100)}%"></i></div>
            <div class="fitn mono">${f.have} of ${f.total}</div>
            ${f.note ? `<div class="fitnote">${esc(f.note)}</div>` : ""}
          </div>`).join("") || '<div class="text-muted">Include tables in Sources first.</div>'}
        </div>
      </div>
    </div>`;
}

function lengthText(f) {
  const n = parseInt(f.length, 10) || 0;
  if (!n) return "any length";
  const eg = {
    Zip: "11201", State: "NY", Middle_Initial: "J",
    Client_ID: "P100200", First_Name: "Ada", Last_Name: "Sample",
    Address_1: "209 Joralemon St", Address_2: "Apt 3L", City: "Brooklyn",
  }[f.role];
  const sample = eg ? `, for example ${eg} is ${eg.length}` : "";
  return `up to ${n} character${n === 1 ? "" : "s"}${sample}`;
}

function builtinLogic(f) {
  const m = {
    First_Name: "kept as entered, junk stripped",
    Middle_Initial: "first letter, uppercased",
    Last_Name: "kept as entered, junk stripped",
    Client_ID: "duplicate key, never fuzzy-matched",
    Address_1: "geocoded, units split out",
    Address_2: "unit line, receives Apt, Fl, Suite",
    City: "borough normalization, fillable from ZIP",
    State: "empty defaults to NY, non-NY flagged",
    Zip: "5 digits, ZIP+4 trimmed, invalid flagged",
  };
  return m[f.role] || "passthrough, cleaned and length-checked";
}

function shortKey(k) {
  const p = String(k).split(" :: ");
  return p.length > 1 ? p.join("  \u00b7  ") : k;
}

function vPrepare() {
  const d = UI.data.prepare;
  const rows = d.ops.map(o => `
    <div class="lrow ${o.removed ? "dim" : ""}">
      <span class="tag ${o.origin === "auto" ? "tag-accent" : "tag-outline"}">${o.origin}</span>
      <div class="lmain">
        <div class="lline"><span class="lrange mono">${esc(shortKey(o.table))}</span>
          <span class="lname">${esc(o.title)}</span></div>
        <div class="ldesc">${esc(o.desc)}</div>
      </div>
      <button class="btn btn-ghost" data-op="${o.id}" data-removed="${o.removed ? 0 : 1}">
        ${o.removed ? "Restore" : "Remove"}</button>
    </div>`).join("");
  return `
    ${stageHead(3, continueBtn("Continue to Map"))}
    <div class="list">${rows || '<div class="lrow"><div class="ldesc">No staging needed. Every table passes through as-is.</div></div>'}</div>
    ${vPrepareAdd(d)}`;
}

function vDedupeRules() {
  const d = UI.data.dupes;
  const fields = UI.data.ruleFields || [];
  if (!d) return "";
  const open = UI.dupOpen || {};

  const fieldChips = fields.map(f => `
    <label class="chip ${d.fields.indexOf(f.role) >= 0 ? "on" : ""}">
      <input type="checkbox" data-dupfield="${esc(f.role)}"
        ${d.fields.indexOf(f.role) >= 0 ? "checked" : ""} style="margin:0">
      ${esc(f.label)}</label>`).join("");

  const tables = d.tables.map(tb => {
    if (tb.missing && tb.missing.length) {
      return `<div class="lrow"><div class="lmain">
        <div class="lline"><span class="lname">${esc(tb.short)}</span>
          <span class="tag tag-outline">cannot check</span></div>
        <div class="ldesc">No column is matched for ${tb.missing.map(esc).join(", ")},
          so this file cannot be checked on these fields.</div></div></div>`;
    }
    if (!tb.total_groups) {
      return `<div class="lrow"><div class="lmain">
        <div class="lline"><span class="lname">${esc(tb.short)}</span>
          <span class="tag tag-neutral">no duplicates</span></div>
        <div class="ldesc">No two rows match on ${tb.matched_on.map(esc).join(", ")}.</div>
        </div></div>`;
    }
    const isOpen = !!open[tb.table];
    const pendingOf = g => {
      const all = (UI.pendingDups || []).find(x => x.table === tb.table && x.all);
      const one = (UI.pendingDups || []).find(x => x.table === tb.table && x.gid === g.gid);
      return one ? one.decision : all ? all.decision : null;
    };
    const groups = isOpen ? tb.groups.map(g => { const p = pendingOf(g); const eff = p !== null ? p : g.decision; const isCopies = typeof eff === "string" && eff.startsWith("copies"); return `
      <div class="dgroup ${isCopies ? "dcopies" : eff === "keep" ? "dkeep" : ""}">
        <div class="pvscroll"><table class="table pvtable"><thead><tr>
          <th>Row</th>${tb.shown.map(c => `<th class="${g.differing.indexOf(c) >= 0 ? "diffcol" : ""}">${esc(c)}</th>`).join("")}
        </tr></thead><tbody>
          ${g.rows.map((r, i) => { const keptRow = (typeof eff === "string" && eff.startsWith("copies:")) ? parseInt(eff.split(":")[1], 10) : (eff === "copies" ? g.rows[0].row : null);
            return `<tr class="${keptRow === r.row ? "keptrow" : ""}">
            <td class="mono text-muted" style="white-space:nowrap">${r.row}
              ${keptRow === r.row ? `<span class="tag tag-accent">kept</span>`
                : `<button class="btn btn-ghost" data-dupdecide="${esc(tb.table)}" data-gid="${g.gid}" data-verdict="copies:${r.row}"
                     title="Keep this row and set the other ${g.rows.length - 1} in the group aside">keep this one</button>`}</td>
            ${tb.shown.map(c => `<td class="mono ${g.differing.indexOf(c) >= 0 ? "diffcell" : ""}"
              style="font-size:12px">${esc(r.values[c]) || '<span class="cellblank">blank</span>'}</td>`).join("")}
          </tr>`; }).join("")}
        </tbody></table></div>
        <div class="dgroup-foot">
          <span class="text-muted" style="font-size:11.5px">
            ${g.differing.length
              ? `Differ in ${g.differing.map(esc).join(", ")}.`
              : "Identical in every field shown."}</span>
          <span style="flex:1"></span>
          ${p !== null ? `<span class="tag tag-accent">chosen, not yet applied</span>` : ""}
          <button class="btn ${isCopies ? "btn-primary" : "btn-secondary"}"
            data-dupdecide="${esc(tb.table)}" data-gid="${g.gid}" data-verdict="copies"
            title="Keep the first row of this group and set the others aside. To keep a different row, use 'keep this one' beside it.">
            Copies, keep ${isCopies && eff !== "copies" ? "row " + eff.split(":")[1] : "the first"}</button>
          <button class="btn ${eff === "keep" ? "btn-primary" : "btn-secondary"}"
            data-dupdecide="${esc(tb.table)}" data-gid="${g.gid}" data-verdict="keep">
            Different people, keep all</button>
          ${eff ? `<button class="btn btn-ghost" data-dupdecide="${esc(tb.table)}"
            data-gid="${g.gid}" data-verdict="">undo</button>` : ""}
        </div>
      </div>`; }).join("") : "";
    return `<div class="lrow-wrap">
      <div class="lrow">
        <div class="lmain">
          <div class="lline"><span class="lname">${esc(tb.short)}</span>
            <span class="tag tag-accent">${nf(tb.total_rows)} row(s) in ${nf(tb.total_groups)} group(s)</span>
            ${tb.unreviewed ? `<span class="tag tag-outline">${nf(tb.unreviewed)} to review</span>`
              : `<span class="tag tag-neutral">all reviewed</span>`}</div>
          <div class="ldesc">Matched on ${tb.matched_on.map(esc).join(", ")}.
            ${tb.copies ? `${nf(tb.copies)} group(s) confirmed as copies: ${nf(tb.will_set_aside)} row(s) will be set aside.` : ""}
            ${tb.keep ? ` ${nf(tb.keep)} group(s) kept as different people.` : ""}
            ${tb.unreviewed ? ` Groups not yet reviewed are kept and flagged, never removed.` : ""}</div>
        </div>
        <button class="btn btn-secondary" data-dupopen="${esc(tb.table)}">${isOpen ? "Hide" : "Review"}</button>
      </div>
      ${isOpen ? `<div class="dgroups">
        ${(() => {
          const allP = (UI.pendingDups || []).find(x => x.table === tb.table && x.all);
          const fileChoice = allP ? allP.decision : (tb.copies && tb.copies === tb.total_groups ? "copies" : tb.keep && tb.keep === tb.total_groups ? "keep" : "");
          const aside = tb.groups.reduce((n, g) => n + (g.rows.length - 1), 0) + Math.max(0, (tb.total_groups - tb.groups.length));
          return `<div class="dgroups-bar">
          <span class="text-muted" style="font-size:12px">Decide every group in this file at once:</span>
          <button class="btn ${fileChoice === "copies" ? "btn-primary" : "btn-secondary"}" data-dupall="${esc(tb.table)}" data-verdict="copies"
            title="In every group, the first row (by its order in the file) stays. The other rows are set aside, listed under 'Copies you confirmed', and can be brought back. Nothing is merged.">
            ${fileChoice === "copies" ? "Chosen: " : ""}All are copies, keep the first of each</button>
          <button class="btn ${fileChoice === "keep" ? "btn-primary" : "btn-secondary"}" data-dupall="${esc(tb.table)}" data-verdict="keep"
            title="Every group is left as it is: all rows stay, and the tool will not pair them again.">
            ${fileChoice === "keep" ? "Chosen: " : ""}All are different people, keep every row</button>
          <button class="btn btn-ghost" data-dupall="${esc(tb.table)}" data-verdict="">Clear</button>
        </div>
        ${allP ? `<div class="band ${allP.decision ? "band-warn" : ""}" style="margin:0 0 10px">${I.alert}<div>
          <b>${allP.decision === "copies"
            ? `Chosen for this file: keep the first row of each of the ${nf(tb.total_groups)} group(s) and set the other ${nf(aside)} row(s) aside.`
            : allP.decision === "keep" ? `Chosen for this file: keep every row in all ${nf(tb.total_groups)} group(s); none set aside.`
            : "Decisions for this file will be cleared."}</b>
          <div class="band-sub">Nothing has changed yet. Click "Apply and process again" below to make it so; the rows set aside appear under "Copies you confirmed" and can be brought back.</div>
        </div></div>` : ""}`;
        })()}
        ${groups}
        ${tb.total_groups > tb.groups.length ? `<div class="text-muted" style="font-size:12px;padding:8px 0">
          Showing the ${tb.groups.length} largest of ${nf(tb.total_groups)} groups. The decision for the whole file above covers them all.</div>` : ""}
      </div>` : ""}
    </div>`;
  }).join("");

  return `<div class="card" style="margin-top:16px">
    <div class="card-title">Duplicates within a file ${helpBtn("element", "dupes")}</div>
    <div class="card-body" style="opacity:1">
      ${d.total_groups
        ? `<b>${nf(d.total_rows)} row(s) look like the same person listed more than once in the same file.</b>
           Look at each pair and say whether it is one person or two. Copies you confirm are set aside at once and listed below; nothing is removed until you say so.`
        : `No row in any file matches another row on ${d.fields.map(esc).join(", ")}.`}
    </div>
    <div class="text-muted" style="font-size:12px;margin:-4px 0 10px">
      <b>Copies, keep the first</b> keeps the first row of a group and sets the rest aside: they leave the clean list, are listed under "Copies you confirmed", and can be brought back.
      <b>Different people, keep all</b> leaves every row and stops the tool pairing them again. Either way, nothing is merged and nothing is deleted.</div>
    <div class="field" style="margin-bottom:10px"><label>Two rows are the same person when all of these match</label>
      <div class="chips">${fieldChips}</div>
      <div class="text-muted" style="font-size:11.5px">Case, spacing and punctuation are ignored. A row blank in any of these is never matched. Changing the fields clears the decisions.</div></div>
    <div class="list">${tables}</div>
    ${(UI.pendingDups || []).length ? `<div class="band band-warn applybar" style="margin-top:10px">${I.alert}<div style="flex:1">
      <b>${nf(UI.pendingDups.length)} duplicate decision(s) chosen, not yet applied.</b>
      <div class="band-sub">Decide every group you want, then apply them all at once; the batch is processed again once.</div></div>
      <button class="btn btn-primary" data-act="apply-dups">Apply and process again</button>
      <button class="btn btn-ghost" data-act="clear-dups">Clear</button></div>` : ""}
    ${d.will_set_aside ? `<div class="band band-ok" style="margin-top:10px">${I.check}<div>
      <b>${nf(d.will_set_aside)} row(s) set aside</b>, one kept per confirmed group.
      They are listed under "Copies you confirmed" below and can be brought back.</div></div>` : ""}
  </div>`;
}

function vPrepareAdd(d) {
  const a = UI.addOp;
  if (!a.table || !d.columns[a.table]) a.table = d.tables[0] || "";
  const cols = d.columns[a.table] || [];
  const sel = (key, label, options, width) => `
    <label class="field" ${width ? `style="max-width:${width}px"` : ""}>
      <label>${label}</label>
      <select class="input" data-addop="${key}">
        ${options.map(o => {
          const v = typeof o === "string" ? o : o[0];
          const t = typeof o === "string" ? o : o[1];
          return `<option value="${esc(v)}" ${a[key] === v ? "selected" : ""}>${esc(t)}</option>`;
        }).join("")}
      </select></label>`;

  let body = "";
  if (a.type === "calc_zip") {
    const none = [["", "(none)"]];
    const guess = (pat) => cols.find(c => new RegExp(pat, "i").test(c)) || "";
    if (a.street_col === undefined) a.street_col = guess("street|addr|address") || cols[0] || "";
    if (a.city_col === undefined) a.city_col = guess("^city$|borough|_city$");
    if (a.zip_col === undefined) a.zip_col = guess("^zip|zip_?code|postal|_zip$");
    if (!a.mode) a.mode = "blanks";
    if (!a.calc_name) a.calc_name = "Zip_calculated";
    body = `<div class="addgrid">
      ${sel("street_col", "Street address column", cols)}
      ${sel("city_col", "City or borough column (optional)", none.concat(cols))}
      ${sel("zip_col", "Existing ZIP column (optional)", none.concat(cols))}
      ${sel("mode", "Calculate", [["blanks", "Only where the existing ZIP is blank"], ["always", "For every row"]])}
      <label class="field"><label>New column name</label>
        <input class="input" data-addop="calc_name" value="${esc(a.calc_name)}"></label>
      <button class="btn btn-primary" data-act="add-op" ${a.street_col ? "" : "disabled"}>Add calculated column</button>
    </div>
    <div class="text-muted" style="font-size:11.5px;margin-top:6px">
      ${helpBtn("element", "calc_zip")} Looks each address up with ${esc(d.geocoder || "the reference data")}. Adds
      <b>${esc(a.calc_name)}</b>, with the ZIP where the address settles it, and
      <b>${esc(a.calc_name)}_note</b> with the reason on every row. A street the
      geocoder cannot place, or one that runs through several ZIPs without a
      house number, is left blank and goes to review carrying that reason for
      a person to decide. On the matching stage, match Zip to the new column.
      No value the file already has is changed.</div>`;
  } else if (a.type === "clean") {
    body = `
      <div class="field"><label>Columns to clean
        <span class="pickers">
          <button class="btn btn-ghost" data-pick="all">Select all</button>
          <button class="btn btn-ghost" data-pick="none">Select none</button>
          <button class="btn btn-ghost" data-pick="invert">Invert</button>
          <span class="text-muted" style="font-size:11.5px">
            ${a.cols.length} of ${cols.length} selected</span>
        </span></label>
        <div class="chips">${cols.map(c => `
          <label class="chip ${a.cols.indexOf(c) >= 0 ? "on" : ""}">
            <input type="checkbox" data-opcol="${esc(c)}"
              ${a.cols.indexOf(c) >= 0 ? "checked" : ""} style="margin:0">
            ${esc(c)}</label>`).join("")}</div></div>
      <div class="addgrid">
        ${sel("case", "Case", d.cases)}
        <label class="field"><label>Sanitize junk characters</label>
          <label class="ckline"><input type="checkbox" data-addop-ck="sanitize"
            ${a.sanitize ? "checked" : ""}> control and zero-width characters,
            smart quotes to ASCII. Keeps apostrophes, periods, hyphens.</label></label>
        <label class="field"><label>Strip edge punctuation</label>
          <label class="ckline"><input type="checkbox" data-addop-ck="strip_punct"
            ${a.strip_punct ? "checked" : ""}> leading and trailing only</label></label>
        <button class="btn btn-secondary" data-act="add-op"
          ${a.cols.length ? "" : "disabled"}>Add clean step</button>
      </div>`;
  } else if (a.type === "split_delim") {
    const delims = Object.keys(d.delimiters).map(k => [k, k]).concat([["Custom...", "Custom..."]]);
    body = `<div class="addgrid">
      ${sel("col", "Column", cols)}
      ${sel("delimLabel", "Delimiter", delims)}
      ${a.delimLabel === "Custom..." ? `<label class="field"><label>Custom delimiter</label>
        <input class="input" data-addop="delimCustom" value="${esc(a.delimCustom || "")}"></label>` : ""}
      <label class="field"><label>Max splits (0 = every)</label>
        <input class="input mono" type="number" min="0" data-addop="maxsplit"
          value="${esc(a.maxsplit || 0)}"></label>
      <label class="field"><label>New column names (optional, comma separated)</label>
        <input class="input" data-addop="names" value="${esc(a.names || "")}"></label>
      <button class="btn btn-secondary" data-act="add-op" ${a.col ? "" : "disabled"}>Add split step</button>
    </div>`;
  } else {
    const what = a.type === "split_jammed" ? "Address column" : "Name column";
    const note = a.type === "split_jammed"
      ? "Creates _street, _address2, _city, _state and _zip. The unit goes to _address2. Rows already clean keep the street and leave the new columns blank."
      : "Handles Last, First M and First M Last. A suffix stays with the last name. DiNapoli and O'Brien keep their casing.";
    body = `<div class="addgrid">
      ${sel("col", what, cols)}
      <button class="btn btn-secondary" data-act="add-op" ${a.col ? "" : "disabled"}>Add step</button>
    </div><div class="text-muted" style="font-size:11.5px;margin-top:6px">${note}</div>`;
  }

  return `<div class="card" style="margin-top:16px">
    <div class="card-title">Add an operation</div>
    <div class="addgrid">
      ${sel("type", "Type", [["calc_zip", "Calculated column: ZIP from the address"],
        ["clean", "Clean columns"], ["split_delim", "Split by delimiter"],
        ["split_jammed", "Split jammed address"], ["split_name", "Split jammed name"]])}
      ${sel("table", "Table", d.tables.map(t => [t, shortKey(t)]))}
    </div>
    ${body}
    <div class="text-muted" style="font-size:11.5px">
      Every operation adds columns. Nothing is removed or overwritten, so a step
      can be taken back without losing data.</div>
  </div>`;
}

function vMap() {
  const d = UI.data.map;
  const tables = d.tables;
  if (!tables.length) {
    return header("Stage 04 of 07", "Map", "Include at least one table first.", "");
  }
  UI.activeTable = Math.min(UI.activeTable, tables.length - 1);
  const t = tables[UI.activeTable];
  const left = tables.map((x, i) => `
    <button class="stage ${i === UI.activeTable ? "cur" : ""}" data-table="${i}">
      <span class="stage-body"><span class="stage-name" style="font-size:13px">${esc(shortKey(x.key))}</span>
      <span class="stage-meta">${nf(x.rows)} rows</span></span>
      <span class="mapstat ${x.ready ? "" : "bad"}">${x.confirmed ? "confirmed"
        : x.ready ? "mapped" : "missing required"}</span>
    </button>`).join("");
  const ck = t.check || { status: "ok", summary: "", fields: {} };
  const ckBand = ck.status === "ok" ? "" : `
    <div class="band ${ck.status === "problem" ? "band-warn" : ""}">
      ${I.alert}<div><b>${esc(ck.summary)}</b> ${helpBtn("element", "column_check")}
      <div class="band-sub">The tool reads a sample of each column and says when
      the values do not look like the field. It never blocks you; you may have a
      reason. Nothing else in the tool catches a column in the wrong place.</div>
      </div></div>`;
  const blocker = d.blocked.length ? `
    <div class="band band-warn">${I.alert}<div>
      <b>Run is blocked.</b>
      <div class="band-sub">Required fields are unmapped on:
      ${d.blocked.map(shortKey).map(esc).join(", ")}.</div></div></div>` : "";
  const grid = t.fields.map(f => `
    <div class="field ${f.required && !f.col ? "field-bad" : ""}">
      <label>${esc(f.label)}${f.required ? " · required" : ""}</label>
      <select class="input" data-map-field="${esc(f.role)}">
        <option value="">(none)</option>
        ${t.cols.map(c => `<option value="${esc(c)}" ${c === f.col ? "selected" : ""}>${esc(c)}</option>`).join("")}
      </select>
      <div class="fnote ${f.required && !f.col ? "bad" : ""}">${esc(f.note)}</div>
      ${fieldVerdict(ck.fields[f.role])}
    </div>`).join("");
  return `
    ${stageHead(4, continueBtn("Continue to Programs", d.blocked.length > 0))}
    ${blocker}
    ${ckBand}
    <div class="mapwrap">
      <div class="maplist">${left}</div>
      <div class="mapright">
        <div class="mapgrid">${grid}</div>
        ${vSourceDefaults(t)}
        <div class="band" style="margin-top:14px">${I.shield}<div>
          <b>Unmapped columns never enter the output.</b>
          <div class="band-sub">A date of birth or SSN column left unmapped
          stays out of every export.</div></div></div>
        <div style="display:flex;gap:10px;margin-top:14px;align-items:center;flex-wrap:wrap">
          <button class="btn btn-primary" data-act="confirm-table">
            ${nextUnconfirmed(tables, UI.activeTable) >= 0
              ? "Confirm and next table" : "Confirm this table"}</button>
          <button class="btn btn-secondary" data-table-preview="${esc(t.key)}">
            ${UI.openTable === t.key ? "Hide data" : "Show data"}</button>
          <span class="text-muted" style="font-size:12.5px">
            ${tables.filter(x => x.confirmed).length} of ${tables.length} confirmed,
            ${tables.filter(x => x.ready).length} of ${tables.length} ready</span>
          ${tables.every(x => x.confirmed) && !d.blocked.length
            ? '<span class="tag tag-neutral">every table confirmed</span>' : ""}
        </div>
        ${UI.openTable === t.key ? vPreviewPane(t.key, "prepared") : ""}
      </div>
    </div>`;
}

function vProgramNames(pg) {
  if (!pg || !pg.mapped_on) {
    return `<div class="card" style="margin-top:18px">
      <div class="card-title">Program names</div>
      <div class="card-body" style="opacity:1">
        No program column is matched on any source yet. Match one above and the
        program names found across your files appear here, so the same program
        written differently in each system can be counted as one.</div></div>`;
  }
  const groups = pg.groups || [];
  const canon = groups.map(g => g.canonical);
  const rows = groups.map(g => `
    <div class="pgroup ${g.needs_confirming ? "pending" : ""}">
      <div class="pgroup-head">
        <input class="input pgname" data-pgrename="${esc(g.canonical)}"
          value="${esc(g.canonical)}">
        <span class="pgroup-n mono">${nf(g.rows)} row(s)</span>
      </div>
      ${g.why ? `<div class="pgroup-why">Put together because ${esc(g.why)}.</div>` : ""}
      <div class="pgroup-vars">
        ${g.variants.map(v => `
          <span class="pvar">
            <span class="pvar-name">${esc(v.name)}</span>
            <span class="text-muted mono">${nf(v.rows)}</span>
            ${g.variants.length > 1 ? `
              <button class="btn btn-ghost" data-pgout="${esc(v.name)}"
                title="Count this name on its own">take out</button>` : ""}
            <select class="input pvmove" data-pgmove="${esc(v.name)}">
              <option value="">move to...</option>
              ${canon.filter(c => c !== g.canonical).map(c =>
                `<option value="${esc(c)}">${esc(c)}</option>`).join("")}
            </select>
          </span>`).join("")}
      </div>
    </div>`).join("");

  const pending = groups.filter(g => g.needs_confirming).length;
  const perSource = (pg.sources || []).map(s => `
    <div class="pgsrc ${s.col ? "" : "missing"}">
      <span class="mono">${esc(shortKey(s.key))}</span>
      <span>${s.col
        ? `reads program names from <b>${esc(s.col)}</b>${s.warn ? `, <i>${esc(s.warn)}</i>` : ""}`
        : "<b>has no program column matched</b>, so its rows have no program"}</span>
      <button class="btn btn-ghost" data-table-jump="${esc(s.key)}">change</button>
    </div>`).join("");
  return `<div class="card" style="margin-top:18px">
    <div class="card-title">Program names across your sources
      <button class="btn btn-ghost" data-act="pg-refresh" style="margin-left:10px">Refresh</button>
    </div>
    <div class="pgsources">${perSource}</div>
    <div class="card-body" style="opacity:1">
      Found <b>${nf(pg.distinct)}</b> different program name(s) across
      ${nf(pg.mapped_on)} source(s), which look like <b>${nf(pg.grouped_into)}</b>
      actual program(s). The same program is often written differently in each
      system, and counting the spellings separately would make one program look
      like several.
      ${pending ? ` <b>${pending} group(s) below were put together by the tool
        and are worth a glance.</b>` : ""}
      Rename a group to set the name it is counted under, take a name out if it
      does not belong, or move it to another group.
    </div>
    <div class="pgroups">${rows}</div>
    <div><button class="btn btn-ghost" data-act="pg-reset">
      Go back to what the tool proposed</button></div>
  </div>`;
}

function nextUnconfirmed(tables, from) {
  for (let i = 1; i <= tables.length; i++) {
    const j = (from + i) % tables.length;
    if (j !== from && !tables[j].confirmed) return j;
  }
  return -1;
}

function fieldVerdict(v) {
  if (!v || v.status === "ok") return "";
  const cls = v.status === "problem" ? "fverdict bad" : "fverdict";
  return `<div class="${cls}">${v.status === "problem" ? I.alert : ""}
    <span>${esc(v.message)}
    ${v.examples && v.examples.length
      ? `<br><span class="mono">${v.examples.map(esc).join(" · ")}</span>` : ""}
    </span></div>`;
}

function vHeaderRow(t) {
  if (!t.canSetHeader) return "";
  const peek = t.blockPeek || [];
  const rows = peek.map((r, i) => {
    const n = i + 1;
    const on = t.headerRow === n;
    return `<tr class="${on ? "hrpick" : ""}">
      <td><button class="ckbox ${on ? "on" : ""}" data-headerrow="${n}" data-hrtable="${esc(t.key)}">${on ? I.check : ""}</button></td>
      <td class="mono text-muted">${n}</td>
      ${r.map(v => `<td class="mono" style="font-size:12px">${esc(v) || '<span class="text-muted">blank</span>'}</td>`).join("")}
    </tr>`;
  }).join("");
  return `<div class="hrwrap ${t.headerWrong ? "warn" : ""}">
    <div class="hr-head">
      ${t.headerWrong ? `${I.alert}<div><b>The header row may be wrong:</b> ${esc(t.headerWhy)}.
          Tick the row that holds the column names. ${helpBtn("element", "header_row")}</div>`
        : `<div><b>Column names are read from row ${t.headerRow || "none"}.</b>
          If a title or note sits above the real header, tick the right row. ${helpBtn("element", "header_row")}</div>`}
    </div>
    <div class="pvscroll"><table class="table pvtable"><tbody>
      <tr class="${t.headerRow === 0 ? "hrpick" : ""}">
        <td><button class="ckbox ${t.headerRow === 0 ? "on" : ""}" data-headerrow="0" data-hrtable="${esc(t.key)}">${t.headerRow === 0 ? I.check : ""}</button></td>
        <td class="mono text-muted">none</td>
        <td colspan="9" class="text-muted" style="font-size:12px">
          No header row. Columns are numbered Column_1, Column_2 and so on.</td>
      </tr>
      ${rows}
    </tbody></table></div>
  </div>`;
}

function vSourceDefaults(t) {
  const d = t.defaults || {};
  const fields = t.fields.filter(f => !f.col);
  if (!fields.length) {
    return `<div class="card" style="margin-top:14px">
      <div class="card-title">Fill a field for this source only</div>
      <div class="card-body" style="opacity:1">Every field is mapped for this
      table, so nothing needs filling in.</div></div>`;
  }
  return `<div class="card" style="margin-top:14px">
    <div class="card-title">Fill a field for this source only ${helpBtn("element", "source_defaults")}</div>
    <div class="card-body" style="opacity:1">
      Where one file leaves a field out entirely and you know the value for every
      row in it, set it here. It applies to this table alone, fills only blanks,
      and never replaces a value the file supplied. A value set here wins over a
      default on the schema. Every use is recorded in the audit log.
    </div>
    <div class="mapgrid">${fields.map(f => `
      <label class="field"><label>${esc(f.label)}</label>
        <input class="input" data-srcdefault="${esc(f.role)}"
          placeholder="leave empty for none"
          value="${esc(d[f.role] || "")}"></label>`).join("")}</div>
  </div>`;
}

function progLocal() {
  // A working copy of the program set-up. Every pick, drop, rename and column
  // choice changes this copy; one Apply sends it all. The copy is rebuilt
  // from the server whenever the stage loads fresh.
  const d = UI.data.programs;
  if (!UI.progWork || UI.progWork.stamp !== d.stamp) {
    UI.progWork = {
      stamp: d.stamp,
      dirty: false,
      columns: Object.fromEntries(d.sources.map(s => [s.key, s.col])),
      groups: d.groups.map(g => ({ canonical: g.canonical, why: g.why,
        needs_confirming: g.needs_confirming,
        variants: g.variants.map(v => ({ name: v.name, rows: v.rows, files: v.files })) })),
    };
  }
  return UI.progWork;
}

function progMove(name, into) {
  const w = progLocal();
  let moved = null;
  for (const g of w.groups) {
    const i = g.variants.findIndex(v => v.name === name);
    if (i >= 0) { if (g.canonical === into) return; moved = g.variants.splice(i, 1)[0]; break; }
  }
  if (!moved) return;
  const target = into === "__alone__" ? null : w.groups.find(g => g.canonical === into);
  if (target) target.variants.push(moved);
  else w.groups.push({ canonical: name, why: "", needs_confirming: false, variants: [moved] });
  for (let i = w.groups.length - 1; i >= 0; i--) if (!w.groups[i].variants.length) w.groups.splice(i, 1);
  w.dirty = true;
}

async function progApply() {
  const w = UI.progWork;
  if (!w || !w.dirty) return;
  await api("/api/programs/apply", {
    columns: Object.entries(w.columns).map(([table, column]) => ({ table, column })),
    groups: w.groups.map(g => ({ canonical: g.canonical, names: g.variants.map(v => v.name) })),
  });
  UI.progWork = null;
}

function vPrograms() {
  const d = UI.data.programs;
  if (!d) return stageHead(5, "");
  const w = progLocal();
  const sel = UI.progSel;               // a name picked up, waiting for a group
  const pv = d.preview;
  const pending = w.dirty;

  const sources = d.sources.map(s => `
    <div class="psrc ${w.columns[s.key] ? "" : "missing"}">
      <div class="psrc-name mono">${esc(s.short)}</div>
      <div class="psrc-pick">
        <select class="input" data-progcol="${esc(s.key)}">
          <option value="">(no program column)</option>
          ${s.cols.map(c => `<option value="${esc(c)}" ${c === w.columns[s.key] ? "selected" : ""}>${esc(c)}</option>`).join("")}
        </select>${w.columns[s.key] !== s.col ? `<div class="text-muted" style="font-size:11px">changed, not yet applied</div>` : ""}</div>
      <div class="psrc-info">${s.col
        ? `<span class="text-muted">${nf(s.distinct)} name(s), for example</span> ${s.samples.map(esc).join(" · ")}
           ${s.default ? `<div class="text-muted" style="font-size:11.5px">Blank rows get <b>${esc(s.default)}</b>, the default set for this file on the matching stage.</div>` : ""}
           ${s.warn ? `<div class="fverdict bad">${I.alert}<span>${esc(s.warn)}</span></div>` : ""}`
        : s.default
        ? `<b>No program column.</b> Every one of these ${nf(s.rows)} rows counts under <b>${esc(s.default)}</b>, the default set for this file on the matching stage.`
        : `<b>No program column.</b> These ${nf(s.rows)} rows will be in the overall count but not in any program's count. To give them one, set a default for this file on the matching stage.`}
      </div>
    </div>`).join("");

  const groups = w.groups.map((g, gi) => `
    <div class="pg ${sel ? "target" : ""} ${g.needs_confirming ? "pending" : ""}" data-pgtarget="${esc(g.canonical)}">
      <div class="pg-head">
        <input class="input pgname" data-pgrename="${esc(g.canonical)}" value="${esc(g.canonical)}"
          title="The name this program is counted under. Change it here.">
        <span class="text-muted mono" style="font-size:11.5px">${nf(g.rows)} row(s)</span>
        ${sel && sel !== g.canonical ? `<span class="tag tag-accent">click to move "${esc(sel)}" here</span>` : ""}
      </div>
      <div class="pg-vars">
        ${g.variants.map(v => `
          <button class="pvar2 ${sel === v.name ? "picked" : ""}" data-pgpick="${esc(v.name)}"
            title="${v.files.length ? "In " + esc(v.files.join(", ")) : ""}. Click to pick this name up, then click the group it belongs to.">
            <span>${esc(v.name)}</span>
            <span class="text-muted mono">${nf(v.rows)}</span>
            ${v.files.length ? `<span class="pvar2-files">${v.files.map(esc).join(", ")}</span>` : ""}
          </button>`).join("")}
      </div>
      ${g.why ? `<div class="pg-why">Grouped because ${esc(g.why)}.</div>` : ""}
    </div>`).join("");

  const previewBlock = pv ? `
    <div class="pprev ${d.preview_stale ? "stale" : ""}">
      <div class="pprev-head">
        <div><b>What the counts would be</b> ${helpBtn("element", "program_preview")}
          <span class="text-muted" style="font-size:12px">with the programs as they stood at ${esc(pv.taken_at)}${d.preview_stale ? ", before your latest change" : ""}</span></div>
        <button class="btn ${d.preview_stale ? "btn-primary" : "btn-secondary"}" data-act="prog-preview"
          title="Process the files with the programs as they stand now and show the two counts. Takes a moment; nothing is decided.">
          ${d.preview_stale ? "Refresh the preview" : "Preview again"}</button>
      </div>
      <div class="goals" style="margin:10px 0">
        <div class="goal"><div class="goal-kicker">Goal 1</div><div class="goal-title">Unique clients</div>
          <div class="goal-n">${nf(pv.goal1)}</div>
          <div class="goal-sub">${pv.goal1_low !== pv.goal1_high ? `Between ${nf(pv.goal1_low)} and ${nf(pv.goal1_high)} until open matches are decided on Results.` : "Every person once, across all files."}</div></div>
        <div class="goal"><div class="goal-kicker">Goal 2</div><div class="goal-title">Unique clients by program</div>
          <div class="goal-n">${nf(pv.goal2)}</div>
          <div class="goal-sub">One per person per program. This is the count your grouping shapes.</div></div>
      </div>
      <table class="table"><thead><tr><th>Program, as counted</th><th>Unique clients</th><th>Rows</th></tr></thead>
        <tbody>${pv.programs.map(r => `<tr><td>${esc(r.program)}</td>
          <td class="mono"><b>${nf(r.unique_clients)}</b></td><td class="mono text-muted">${nf(r.rows)}</td></tr>`).join("")}
        ${pv.no_program ? `<tr><td class="text-muted"><i>no program recorded</i></td><td class="mono text-muted">${nf(pv.no_program)}</td><td></td></tr>` : ""}
        </tbody></table>
      <div class="text-muted" style="font-size:11.5px;margin-top:6px">
        Counted from the ${nf(pv.counted_rows)} rows that passed every check; ${nf(pv.review_rows)} rows still need fixing and are not counted yet.
        If two lines below should be one program, pick a name up above and move it. Then refresh.</div>
    </div>` : `
    <div class="pprev">
      <div class="pprev-head">
        <div><b>See what the counts would be</b> ${helpBtn("element", "program_preview")}
          <span class="text-muted" style="font-size:12px">Process the files with the programs as they stand and show both counts, program by program. Takes a moment; nothing is decided.</span></div>
        <button class="btn btn-primary" data-act="prog-preview" ${d.ready ? "" : "disabled"}>Preview the counts</button>
      </div>
      ${d.ready ? "" : `<div class="text-muted" style="font-size:12px;margin-top:6px">Match the required columns first: ${d.blockers.map(esc).join("; ")}.</div>`}
    </div>`;

  return `
    ${stageHead(5, `<button class="btn ${pending ? "btn-primary" : "btn-secondary"}" data-act="prog-apply" ${pending ? "" : "disabled"}
        title="Send every change made on this stage to the tool in one go">
        ${pending ? "Apply changes" : "Nothing to apply"}</button>
      ${continueBtn("Continue to Process", !d.ready)}`)}
    ${pending ? `<div class="band band-warn">${I.alert}<div>
      <b>Changes on this stage have not been applied yet.</b>
      <div class="band-sub">Make all the changes you want, then Apply once. Preview and Continue apply them for you.</div></div></div>` : ""}
    <div class="band">${I.check}<div>
      <b>Goal 2 depends on this stage.</b>
      <div class="band-sub">Clients are counted once per program. If a file's program column is not matched, its people are missing from the per-program count.
      If the same program is spelled two ways, it is counted as two programs. Fix both here, and preview the counts as often as you like.</div></div></div>

    <h3 class="sechead">1. Which column holds the program in each file</h3>
    <div class="psrcs">${sources}</div>

    <h3 class="sechead">2. Which names are the same program ${helpBtn("element", "program_grouping")}
      <span class="text-muted" style="font-weight:400;font-size:12px">
        ${nf(d.distinct)} different name(s) across your files, grouped into ${nf(d.grouped_into)} program(s).
        Click a name to pick it up, then click the group it belongs to. Click its own group to put it down.
        Type over a group's name to change what it is counted under.</span>
      <button class="btn btn-ghost" data-act="pg-reset" title="Go back to the grouping the tool proposed">Start again</button>
    </h3>
    ${sel ? `<div class="band band-warn" style="margin-bottom:8px">${I.alert}<div>
      Holding <b>${esc(sel)}</b>. Click the group it belongs to, or
      <button class="btn btn-ghost" data-act="pg-alone">count it on its own</button>
      <button class="btn btn-ghost" data-act="pg-drop">put it back</button></div></div>` : ""}
    <div class="pgs">${groups || '<div class="text-muted">No program names found yet. Match a program column above.</div>'}</div>

    <h3 class="sechead">3. Preview</h3>
    ${previewBlock}`;
}

function vRun() {
  const d = UI.data.runData;
  const st = d.run;
  const s = d.settings;
  const settings = `
    <div class="statstrip" style="margin-bottom:16px">
      <div class="stat"><div class="stat-k">Geocoder</div>
        <div class="setv ${UI.chrome.backend.indexOf("sample") >= 0 ? "warn" : ""}">${esc(UI.chrome.backend)}</div></div>
      <div class="stat"><div class="stat-k">Require geocode</div>
        <label class="ckline"><button class="ckbox ${s.require_geocode ? "on" : ""}"
          data-set="require_geocode" data-on="${s.require_geocode ? 0 : 1}">
          ${s.require_geocode ? I.check : ""}</button> unmatched rows go to review</label></div>
      <div class="stat"><div class="stat-k">Privacy jitter</div>
        <label class="ckline"><button class="ckbox ${s.jitter ? "on" : ""}"
          data-set="jitter" data-on="${s.jitter ? 0 : 1}">${s.jitter ? I.check : ""}</button>
          150 to 250 ft, stored points only. Districts always use true coordinates.</label></div>
      <div class="stat"><div class="stat-k">Jitter seed</div>
        <input class="input mono" id="seed" value="${esc(s.seed)}" style="max-width:110px"></div>
    </div>
    ${vGdeFields(d)}`;
  let body = "";
  if (st.state === "running") {
    body = `<div class="card"><div class="card-title">${esc(st.phase)}</div>
      <div class="pbar"><i style="width:${st.progress}%"></i></div></div>`;
    schedulePoll();
  } else if (st.state === "error") {
    body = `<div class="band band-warn">${I.alert}<div><b>Run failed.</b>
      <div class="band-sub">${esc(st.error)}</div></div></div>`;
  } else if (st.state === "done" && d.results) {
    const r = d.results;
    const pct = r.input ? Math.round(r.clean / r.input * 100) : 0;
    body = `
      <div class="band band-ok">${I.check}<div>
        <b>${nf(r.clean)} clean + ${nf(r.review)} to fix = ${nf(r.input)} rows received.</b>
        <div class="band-sub">Every row is accounted for.</div>
        <div class="splitbar"><i style="width:${pct}%"></i></div></div></div>
      ${r.context && r.context.verdict ? `
      <div class="band ${r.context.advice ? "band-warn" : ""}">
        ${r.context.advice ? I.alert : I.check}<div>
        <b>${esc(r.context.verdict)}</b>
        ${r.context.advice ? `<div class="band-sub">${esc(r.context.advice)}</div>` : ""}
        <div class="band-sub">${esc(r.context.band)}</div></div></div>` : ""}
      <div class="statstrip">
        <div class="stat"><div class="stat-n">${nf(r.input)}</div><div class="stat-k">rows in</div></div>
        <div class="stat"><div class="stat-n">${nf(r.clean)}</div><div class="stat-k">clean on first pass (${pct}%)</div></div>
        <div class="stat"><div class="stat-n warn">${nf(r.review)}</div><div class="stat-k">flagged for review</div></div>
        <div class="stat"><div class="stat-n">${nf(r.corrections)}</div><div class="stat-k">corrections applied</div></div>
      </div>
      <div class="card"><div class="card-title">Verification is confidence, not just success</div>
        <div class="vgrid">
          <div><b class="mono">${nf(r.verify.high)}</b> verified, high confidence</div>
          <div><b class="mono">${nf(r.verify.low)}</b> verified, low confidence.
            A weak match is never labeled fully verified.</div>
          <div><b class="mono">${nf(r.verify.unmatched)}</b> not matched</div>
          <div><b class="mono">${nf(r.verify.needs)}</b> needs review</div>
        </div></div>
      <div class="card"><div class="card-body" style="opacity:1">
        Identical rows sharing one Client ID were reduced to one, the only
        automatic merge. ${nf(r.dup_groups)} possible-duplicate group(s) are
        marked and never merged.</div></div>`;
  } else {
    body = `<div class="card"><div class="card-body" style="opacity:1">
      Settings above, then process. The run cleans, validates, de-duplicates,
      geocodes, and assigns districts, all on this machine.</div>
      <div><button class="btn btn-primary" data-act="run" ${d.blocked ? "disabled" : ""}>
        Process and validate</button></div></div>`;
  }
  const actions = st.state === "done"
    ? `<button class="btn btn-secondary" data-act="run">Run again</button>
       ${continueBtn("Continue to Review")}`
    : "";
  return `${stageHead(6, actions)}
    ${settings}${body}`;
}

function vGdeFields(d) {
  const cat = d.gdeCatalog || {};
  const sel = d.gdeSelected || [];
  const names = Object.keys(cat);
  if (!names.length) return "";
  const groups = names.map(c => `
    <div class="gdegroup">
      <div class="gdecat">${esc(c)}</div>
      <div class="chips">${cat[c].map(f => `
        <label class="chip ${sel.indexOf(f) >= 0 ? "on" : ""}">
          <input type="checkbox" data-gde="${esc(f)}"
            ${sel.indexOf(f) >= 0 ? "checked" : ""}
            ${d.gdeAvailable ? "" : "disabled"} style="margin:0">
          ${esc(f.replace(/_/g, " "))}</label>`).join("")}</div>
    </div>`).join("");
  return `<div class="card">
    <div class="card-title">Additional Geosupport data points (optional)</div>
    <div class="card-body" style="opacity:1">
      ${d.gdeAvailable
        ? `Tick any extra field to append to the clean export. Latitude,
           longitude and the Senate, Assembly and Council districts are always
           included. ${sel.length ? `<b>${sel.length} selected.</b>` : ""}`
        : `These come from Geosupport Desktop Edition and become selectable once
           it is active. The system check reports its status.`}
    </div>
    ${groups}
  </div>`;
}

function schedulePoll() {
  if (UI.runPoll) return;
  UI.runPoll = setInterval(async () => {
    const st = await api("/api/run/status");
    if (st.state !== "running") {
      clearInterval(UI.runPoll); UI.runPoll = null;
      load("run");
    } else {
      UI.data.runData.run = st;
      render();
    }
  }, 350);
}

function vReview() {
  const d = UI.data.review;
  if (d.tallies) UI.reviewTallies = d.tallies;
  if (!d.tallies) {
    return header("Stage 06 of 07", "Review", "Run the pipeline first.", "");
  }
  const t = d.tallies;
  const strip = `
    <div class="statstrip fives">
      <div class="stat"><div class="stat-n">${nf(t.failed)}</div><div class="stat-k">rows that failed a check</div></div>
      <div class="stat"><div class="stat-n">${nf(t.cleared)}</div><div class="stat-k">cleared by decisions</div></div>
      <div class="stat"><div class="stat-n">${nf(t.queue)}</div><div class="stat-k">in the row-by-row queue</div></div>
      <div class="stat"><div class="stat-n">${nf(t.undecided)}</div><div class="stat-k">in undecided groups</div></div>
      <div class="stat"><div class="stat-n warn">${t.decided} / ${t.groups_total}</div><div class="stat-k">decisions made</div></div>
    </div>`;
  const pend = UI.pendingGroups || {};
  const rows = d.groups.map((g, i) => {
    const decided = g.status !== "pending";
    const chosen = pend[g.id];
    const labelOf = k => k === "accept_all" ? "Accept all as they are"
      : (g.a.k === k ? g.a.label : g.b.k === k ? g.b.label : k);
    const actions = decided
      ? `<span class="tag tag-neutral">${esc(g.outcome || g.status)}</span>`
      : chosen
      ? `<span class="tag tag-accent">will: ${esc(labelOf(chosen))}</span>
         <button class="btn btn-ghost" data-group-undo="${g.id}" title="Take this choice back before it is applied">undo</button>`
      : [g.a, g.b].map(a => `<button class="btn ${a.primary ? "btn-primary" : "btn-secondary"}"
          data-group="${g.id}" data-decision="${a.k}">${esc(a.label)}</button>`).join("")
        + (g.a.k !== "approved" && g.b.k !== "approved" && g.id !== "summary" && g.id !== "duprule"
          ? `<button class="btn btn-ghost" data-group="${g.id}" data-decision="accept_all"
              title="Accept all ${nf(g.count)} rows exactly as they stand. They go into the clean list marked 'Approved as entered by reviewer', and the audit log records the decision on each one.">
              Accept all as they are</button>` : "")
        + `<button class="btn btn-ghost" data-preview="${g.id}">Preview</button>`;
    const preview = UI.openGroup === g.id ? vPreview(g.id) : "";
    return `<div class="grow ${decided ? "dim" : ""}">
      <div class="grow-line">
        <span class="grank ${decided ? "" : "hot"}">${String(i + 1).padStart(2, "0")}</span>
        <div class="lmain"><div class="lline"><span class="lname">${esc(g.title)}</span>
          <span class="tag ${g.confCls === "accent" ? "tag-accent" : "tag-neutral"}">${esc(g.conf)}</span></div>
          <div class="ldesc">${esc(g.desc)}</div>
          ${g.lookup ? `
            <div class="gfill">
              <div class="gfill-line">
                <b>${nf(g.lookup.with_street)} of these ${nf(g.count)} rows have a street address.</b> ${helpBtn("element", "fill_lookup")}
                The tool can look each one up${g.id === "cityunknown"
                  ? " to find the right borough"
                  : " to find its ZIP" + (g.lookup.with_city < g.count ? " and borough" : "")},
                show you every answer, and fill them in together when you approve.
                A street it cannot place, or one that runs through several ZIPs, is left as it is.
              </div>
              <button class="btn ${UI.fillFor === g.id ? "btn-secondary" : "btn-primary"}" data-fillpreview="${esc(g.id)}"
                title="Look every row up and list what would be filled in. Nothing changes until you approve the list.">
                ${UI.fillFor === g.id && UI.fillData ? "Hide the lookup" : `Look up all ${nf(g.lookup.with_street)} from the street`}</button>
              ${UI.fillFor === g.id && UI.fillData ? vFillPreview(g.id) : ""}
            </div>` : ""}
          ${(g.diagnosis || []).map(dx => `
            <div class="gdiag ${dx.kind === "mapping" ? "fixable" : ""}">
              ${I.alert}<div>
                <b>${dx.kind === "mapping" ? "This is a matching problem, and it has a one-click fix."
                  : dx.kind === "unmapped" ? "Nothing is matched for this field."
                  : "The file itself does not carry this field."}</b>
                <div class="gdiag-text">${esc(dx.text)}</div>
                ${dx.kind === "mapping" && dx.better ? `
                  <button class="btn btn-primary" data-fixmap="${esc(dx.source)}"
                    data-fixfield="${esc(dx.field)}" data-fixcol="${esc(dx.better)}">
                    Match ${esc(dx.field)} to '${esc(dx.better)}' and process again</button>`
                  : `<button class="btn btn-secondary" data-goto="4">
                       Open the matching stage</button>`}
              </div></div>`).join("")}
        </div>
        <span class="gcount mono">${nf(g.count)}</span>
        <div class="gactions">${actions}</div>
      </div>${preview}</div>`;
  }).join("");
  return `
    ${stageHead(7, `<button class="btn btn-secondary" data-act="undo">Undo last decision</button>
       ${continueBtn("Finish review", t.undecided > 0, "continue")}`)}
    ${reviewTabs("groups", t)}
    ${Object.keys(pend).length ? `<div class="band band-warn applybar">${I.alert}<div style="flex:1">
      <b>${nf(Object.keys(pend).length)} decision(s) chosen, not yet applied.</b>
      <div class="band-sub">Choose what to do with every group, then apply them all at once.</div></div>
      <button class="btn btn-primary" data-act="apply-groups"
        title="Apply every chosen decision in one go">Apply ${nf(Object.keys(pend).length)} decision(s)</button>
      <button class="btn btn-ghost" data-act="clear-groups">Clear</button></div>` : ""}
    ${UI.fixNotice ? `<div class="band band-ok">${I.check}<div><b>${esc(UI.fixNotice)}</b></div></div>` : ""}
    ${strip}
    ${UI.data.dupes && UI.data.dupes.total_groups ? vDedupeRules() : ""}
    ${UI.data.crossFile ? `<div class="band">${I.check}<div>
      <b>${nf(UI.data.crossFile.rows)} row(s) also appear in another file.</b>
      <div class="band-sub">The same people show up in ${UI.data.crossFile.files.length} files:
        ${UI.data.crossFile.files.map(esc).join(", ")}. That is normal, and nothing to fix.
        The Results stage counts each person once.</div>
      </div></div>` : ""}
    <div class="list">${rows}</div>
    <div class="queueband">
      <div class="stat-n">${nf(t.queue)}</div>
      <div class="lmain"><div class="lname">Row-by-row queue</div>
        <div class="ldesc">One-offs plus anything sent from a group.
        Queue-pending rows go to the review export if left unresolved.</div></div>
      <button class="btn btn-secondary" data-act="open-queue">Open the queue ${I.arrow}</button>
    </div>`;
}

function reviewTabs(active, tallies) {
  const t = tallies || {};
  const undecided = t.groups_total ? (t.groups_total - t.decided) : 0;
  return `<div class="revtabs">
    <button class="revtab ${active === "groups" ? "on" : ""}" data-act="show-groups">
      <span class="revtab-n">1</span>
      <span><b>Grouped decisions</b> ${helpBtn("element", "group_decisions")}
        <span class="revtab-sub">${undecided
          ? `${undecided} of ${t.groups_total} still to decide`
          : `all ${t.groups_total || 0} decided`}</span></span>
    </button>
    <span class="revtab-arrow">${I.arrow}</span>
    <button class="revtab ${active === "queue" ? "on" : ""}" data-act="open-queue">
      <span class="revtab-n">2</span>
      <span><b>Row by row</b>
        <span class="revtab-sub">${nf(t.queue || 0)} row(s) waiting</span></span>
    </button>
  </div>`;
}

function vPreview(gid) {
  const p = UI.previewData;
  if (!p || UI.previewFor !== gid) {
    loadPreview(gid);
    return `<div class="gpreview text-muted">Loading the rows...</div>`;
  }
  const st = { sort: p.sort, dir: p.dir };

  const shape = [
    p.common_problems.length
      ? "Most common: " + p.common_problems
          .map(c => `${esc(c.text)} (${nf(c.n)})`).join(", ")
      : "",
    p.blank_fields.length
      ? "Blank in these rows: " + p.blank_fields
          .map(b => `${esc(b.field)} (${nf(b.n)})`).join(", ")
      : "",
  ].filter(Boolean).join(".  ");

  const head = p.fields.map(f => sortHead(f, f, st, "group")).join("")
    + sortHead("What is wrong", "__problems__", st, "group")
    + sortHead("Source", "__source__", st, "group")
    + "<th>Suggested</th>";

  const body = p.rows.map(r => {
    const cells = p.fields.map(f => {
      const v = r.values[f];
      const empty = !String(v || "").trim();
      return `<td class="mono ${empty ? "cellblank" : ""}" style="font-size:12px">`
        + (empty ? "blank" : esc(v)) + "</td>";
    }).join("");
    const probs = r.problems.map(x =>
      `<div class="probline">${esc(x)}</div>`).join("");
    return `<tr>${cells}
      <td style="font-size:12px">${probs}</td>
      <td class="mono text-muted" style="font-size:11.5px">
        ${esc(r.source)}<br>row ${esc(r.row)}</td>
      <td style="font-size:12px">${esc(r.suggestion)}</td></tr>`;
  }).join("");

  return `<div class="gpreview">
    ${shape ? `<div class="gshape">${shape}</div>` : ""}
    <div class="pvtools">
      <span class="pvsearch">${I.search}<input class="input" id="pvq"
        placeholder="Search any value, problem or file" value="${esc(UI.gQ)}"></span>
      <span class="text-muted" style="font-size:12px">
        Rows ${p.total ? p.page * p.per + 1 : 0} to
        ${Math.min((p.page + 1) * p.per, p.total)} of ${nf(p.total)}</span>
      <button class="btn btn-secondary" data-pv="prev" ${p.page === 0 ? "disabled" : ""}>Prev</button>
      <button class="btn btn-secondary" data-pv="next" ${p.page >= p.pages - 1 ? "disabled" : ""}>Next</button>
    </div>
    <div class="pvscroll"><table class="table pvtable">
      <thead><tr>${head}</tr></thead><tbody>${body}</tbody></table></div>
    <div class="text-muted" style="font-size:11.5px;margin-top:8px">
      Every value is shown exactly as it stands after cleaning. Click a column
      heading to sort the whole group, not just this page.</div>
  </div>`;
}

async function loadPreview(gid) {
  const s = UI.sortGroup;
  const p = await api(`/api/review/preview?gid=${gid}`
    + `&q=${encodeURIComponent(UI.gQ)}&page=${UI.gPage}`
    + `&sort=${encodeURIComponent(s.sort || "")}&dir=${s.dir || "asc"}`);
  UI.previewData = p; UI.previewFor = gid;
  render();
}

function vQueue() {
  const q = UI.data.queue;
  const sel = UI.qSelected || {};
  const selCount = UI.qAllMatching ? q.total
    : Object.keys(sel).filter(k => sel[k]).length;

  const statuses = ["pending", "corrected", "approved", "rejected", "removed"];
  const seg = `<div class="seg">${statuses.map(f => `
    <label class="seg-opt"><input type="radio" name="qf"
      ${q.filter === f ? "checked" : ""} data-qfilter="${f}">
      ${f[0].toUpperCase() + f.slice(1)} (${nf(q.counts[f] || 0)})</label>`).join("")}</div>`;

  // Narrowing a large queue to something workable
  const opt = (list, cur, allLabel) =>
    `<option value="">${allLabel}</option>` + list.map(f =>
      `<option value="${esc(f.value)}" ${cur === f.value ? "selected" : ""}>`
      + `${esc(f.label || f.value)} (${nf(f.n)})</option>`).join("");

  const filters = `<div class="qfilters">
    <label class="field"><label>Problem</label>
      <select class="input" data-qnarrow="problem">
        ${opt(q.facets.problems, q.problem, "Any problem")}</select></label>
    <label class="field"><label>Source file</label>
      <select class="input" data-qnarrow="source">
        ${opt(q.facets.sources, q.source, "Any source")}</select></label>
    <label class="field"><label>Search</label>
      <input class="input" id="qsearch" placeholder="name, address, ZIP, ID"
        value="${esc(q.q || "")}"></label>
    <label class="field"><label>Rows per page</label>
      <select class="input" data-qnarrow="per">
        ${[12, 25, 50, 100].map(n =>
          `<option value="${n}" ${q.per === n ? "selected" : ""}>${n}</option>`).join("")}
      </select></label>
    ${(q.problem || q.source || q.q)
      ? '<button class="btn btn-ghost" data-act="q-clear">Clear filters</button>' : ""}
  </div>`;

  const scope = `<div class="qscope">
    Showing <b>${nf(q.total)}</b> of ${nf(q.queue_total)} row(s) in the queue.
    ${q.total > q.per ? `Page ${q.page + 1} of ${nf(q.pages)}.` : ""}
  </div>`;

  // Batch actions, which is what makes a queue of thousands workable
  const bulk = selCount ? `<div class="qbulk">
    <div class="qbulk-head">
      <b>${nf(selCount)} row(s) selected</b>
      ${!UI.qAllMatching && q.total > q.items.length
        ? `<button class="btn btn-ghost" data-act="q-select-matching">
             Select all ${nf(q.total)} matching these filters</button>` : ""}
      <button class="btn btn-ghost" data-act="q-clear-selection">Clear selection</button>
    </div>
    <div class="qbulk-actions">
      <button class="btn btn-secondary" data-qbulk="approved">Approve as entered</button>
      <button class="btn btn-secondary" data-qbulk="rejected">Reject</button>
      <button class="btn btn-secondary" data-qbulk="removed">Remove from dataset</button>
      <button class="btn btn-ghost" data-qbulk="pending">Put back to pending</button>
    </div>
    <div class="qbulk-actions">
      <button class="btn btn-secondary" data-act="q-keep-one-per-program"
        title="Across every group of records that may be one person, keep one row per person per program and set the rest aside. Same name and date of birth as far as recorded. The same person in two programs is two enrollments, both kept.">
        Keep one of each person in each program</button>
    </div>
    <div class="qbulk-fix">
      <label class="field"><label>Set a field on all selected</label>
        <select class="input" id="qbulkfield">
          ${q.fields.map(f => `<option>${esc(f)}</option>`).join("")}</select></label>
      <label class="field"><label>To this value</label>
        <input class="input" id="qbulkvalue" placeholder="for example Brooklyn"></label>
      <button class="btn btn-primary" data-act="q-bulk-fix">Apply and re-check</button>
    </div>
    <div class="text-muted" style="font-size:11.5px">
      A correction is applied to every selected row and then every row is checked
      again on its own. Rows the correction does not fix stay here with their
      reason, so nothing passes without being validated.
    </div>
  </div>` : "";

  const notice = UI.qNotice
    ? `<div class="band band-ok">${I.check}<div><b>${esc(UI.qNotice)}</b></div></div>`
    : "";

  const allOnPage = q.items.length &&
    q.items.every(i => UI.qAllMatching || sel[i.rid]);
  const items = q.items.map((it, i) => `
    <div class="qrow ${i === q.sel ? "cur" : ""}">
      <button class="ckbox ${UI.qAllMatching || sel[it.rid] ? "on" : ""}"
        data-qcheck="${esc(it.rid)}">${UI.qAllMatching || sel[it.rid] ? I.check : ""}</button>
      <button class="qrow-main" data-qsel="${i}">
        <span class="qrow-top">
          <span class="qrow-id mono">${esc(it.id || "no id")}</span>
          <span class="qrow-name">${esc(it.name || "(no name)")}</span>
          <span class="tag tag-neutral">${esc(it.status)}</span></span>
        <span class="qrow-addr mono">${esc(it.address || "no address")}
          ${it.city ? esc(it.city) : '<i class="cellblank">no city</i>'}
          ${it.zip ? esc(it.zip) : '<i class="cellblank">no ZIP</i>'}</span>
        <span class="qrow-why">${esc(it.reason.slice(0, 110))}</span>
        <span class="qrow-src mono">${esc(it.lineage)}</span>
      </button>
    </div>`).join("");

  let detail = `<div class="text-muted" style="padding:24px">
    Nothing matches these filters.</div>`;
  if (q.detail) detail = vQueueDetail(q.detail);

  return `
    ${stageHead(7, continueBtn("Finish review"))}
    ${reviewTabs("queue", UI.reviewTallies)}
    ${notice}
    ${seg}
    ${filters}
    ${scope}
    ${bulk}
    <div class="qwrap">
      <div class="qlist">
        <div class="qselall">
          <button class="ckbox ${allOnPage ? "on" : ""}" data-act="q-select-page">
            ${allOnPage ? I.check : ""}</button>
          <span class="text-muted" style="font-size:12px">Select the ${q.items.length} row(s) on this page</span>
        </div>
        ${items || `<div class="qempty">
          <b>No rows match these filters.</b>
          ${q.queue_total
            ? `The queue still holds ${nf(q.queue_total)} row(s) in total.
               ${(q.problem || q.source || q.q)
                 ? "Clear the filters to see them."
                 : "Try another status tab."}`
            : "Every row has been dealt with."}
          ${(q.problem || q.source || q.q)
            ? '<div style="margin-top:10px"><button class="btn btn-secondary" data-act="q-clear">Clear filters</button></div>'
            : ""}
        </div>`}
        <div class="qpage">
          <button class="btn btn-secondary" data-qpage="prev" ${q.page === 0 ? "disabled" : ""}>Prev</button>
          <span class="text-muted" style="font-size:12px">Page ${q.page + 1} of ${nf(q.pages)}</span>
          <button class="btn btn-secondary" data-qpage="next" ${q.page >= q.pages - 1 ? "disabled" : ""}>Next</button>
        </div></div>
      <div class="qdetail">${detail}</div>
    </div>`;
}

function vQueueDetail(it) {
  // What is wrong, in plain words, with what to check before deciding
  const problems = (it.explained || []).map(pb => `
    <div class="qprob">
      <div class="qprob-text">${I.alert} ${esc(pb.text)}</div>
      <div class="qprob-means">${esc(pb.means)}</div>
      ${pb.check && pb.check.length ? `<ul class="qprob-check">
        ${pb.check.map(c => `<li>${esc(c)}</li>`).join("")}</ul>` : ""}
    </div>`).join("");

  // The other records this decision depends on
  let related = "";
  if (it.related) {
    const r = it.related;
    const head = r.fields.map(f =>
      `<th class="${r.differing.indexOf(f) >= 0 ? "diffcol" : ""}">${esc(f)}</th>`).join("");
    const body = r.rows.map(row => `
      <tr class="${row.is_this_one ? "thisrow" : ""}">
        <td class="mono" style="font-size:11px;white-space:nowrap">
          ${row.is_this_one ? '<b>this record</b>' : `
            <button class="btn btn-ghost" style="padding:0 4px;font-size:11px"
              data-gotorid="${esc(row.rid)}">open</button>`}
          <div class="text-muted">${esc(row.source)} row ${esc(row.row)}</div></td>
        ${r.fields.map(f => {
          const v = row.values[f];
          const diff = r.differing.indexOf(f) >= 0;
          return `<td class="mono ${diff ? "diffcell" : ""} ${String(v).trim() ? "" : "cellblank"}"
            style="font-size:12px">${String(v).trim() ? esc(v) : "blank"}</td>`;
        }).join("")}
      </tr>`).join("");
    related = `<div class="qrelated">
      <div class="qrelated-head">${esc(r.reason)}
        ${r.total > r.shown ? ` Showing ${r.shown} of ${nf(r.total)}.` : ""}</div>
      ${r.differing.length ? `<div class="qrelated-diff">
        Fields that differ: <b>${r.differing.map(esc).join(", ")}</b></div>` : ""}
      <div class="pvscroll"><table class="table pvtable">
        <thead><tr><th>Record</th>${head}</tr></thead>
        <tbody>${body}</tbody></table></div>
    </div>`;
  }

  // Fixes the tool can propose, applied in one click
  const sugg = (it.suggestions || []).length ? `<div class="qsugg">
    <div class="qsugg-head">Suggested fixes</div>
    ${it.suggestions.map((s, i) => `
      <div class="qsugg-row">
        <button class="btn btn-secondary" data-suggest="${i}"
          title="${esc(s.why)} Applies at once and checks the row again.">${esc(s.label)}</button>
        <span class="text-muted" style="font-size:11.5px">${esc(s.why)}</span>
      </div>`).join("")}
  </div>` : "";

  // The original row, which is where a value hiding in an unmapped column shows.
  // Clicking a column adds it to the record view below, so it can be read
  // alongside the matched fields.
  const shown = UI.qExtraCols || {};
  const unmapped = (it.unmapped || []).length ? `
    <div class="qunmapped">
      <b>Columns in the source that are not matched.</b>
      Click one to show it with the record below.
      <div class="chips" style="margin-top:6px">${it.unmapped.map(u =>
        `<button class="chip ${shown[u.column] ? "on" : ""}" data-showcol="${esc(u.column)}"
           title="Show ${esc(u.column)} with this record">${esc(u.column)}: ${esc(u.value.slice(0, 40))}</button>`).join("")}</div>
    </div>` : "";

  const extraRows = Object.keys(shown).filter(c => shown[c]).map(c => {
    const raw = (it.raw || []).find(r => r.column === c);
    return `<tr class="extrarow">
      <td style="font-weight:600;font-size:12.5px">${esc(c)}
        <span class="tag tag-outline">source column</span></td>
      <td class="mono" style="font-size:12.5px">${raw && String(raw.value).trim() ? esc(raw.value) : "blank"}</td>
    </tr>`;
  }).join("");

  const raw = (it.raw || []).length ? `
    <details class="qraw"><summary>The original row, exactly as it arrived
      (${it.raw.length} columns)</summary>
      <div class="pvscroll"><table class="table pvtable"><tbody>
      ${it.raw.map(r => `<tr><td class="mono" style="font-size:11.5px;white-space:nowrap">${esc(r.column)}</td>
        <td class="mono ${String(r.value).trim() ? "" : "cellblank"}" style="font-size:12px">
        ${String(r.value).trim() ? esc(r.value) : "blank"}</td></tr>`).join("")}
      </tbody></table></div></details>` : "";

  const srcName = (it.source || "").split(" :: ")[0];
  const fills = (it.fills || []);
  const fillable = fills.filter(f => f.value);
  const fillBlock = fills.length ? `<div class="qsugg">
    <div class="qsugg-head">Missing location data the tool can fill from this row</div>
    ${fills.map(f => f.value
      ? `<div class="qsugg-row"><span><b>${esc(f.field)}</b> would be <b class="mono">${esc(f.value)}</b>
           <span class="text-muted" style="font-size:11.5px">(${esc(f.why)})</span></span></div>`
      : `<div class="qsugg-row"><span><b>${esc(f.field)}</b> cannot be filled:
           <span class="text-muted" style="font-size:11.5px">${esc(f.why)}</span></span></div>`).join("")}
    ${fillable.length ? `<button class="btn btn-primary" data-qfill="${esc(it.rid)}"
        title="Fill in the values shown above, then check this row again. Recorded in the audit log.">
        Fill these in and check again</button>` : ""}
  </div>` : "";

  const keepBlock = it.related ? `<div class="qsugg">
    <div class="qsugg-head">These may be one person. Keep one row.</div>
    <div class="text-muted" style="font-size:12px;margin-bottom:8px">
      Choose the row to keep; the others in this group are set aside, listed with
      the reason, and can be brought back. Nothing is merged.</div>
    ${it.related.rows.map(r => `<div class="qsugg-row">
      <button class="btn ${r.is_this_one ? "btn-primary" : "btn-secondary"}" data-keeprow="${esc(r.rid)}"
        title="Keep this row and set the other ${it.related.rows.length - 1} aside">
        Keep ${r.is_this_one ? "this record" : `row ${esc(r.row)} of ${esc(r.source.split(" :: ")[0])}`}</button>
      <span class="text-muted mono" style="font-size:11.5px">${esc(r.values.First_Name)} ${esc(r.values.Last_Name)}, ${esc(r.values.Address_1)}</span>
    </div>`).join("")}
  </div>` : "";

  return `
    <div class="qd-head"><b>${esc(it.id || "(no id)")}</b> ${esc(it.name)}
      <span class="text-muted" style="font-size:12px"> · ${esc(it.lineage)}</span>
      <a class="btn btn-ghost" style="margin-left:auto" href="/api/source/file?name=${encodeURIComponent(srcName)}"
         title="Download the original file, exactly as it was loaded">Open the source file</a>
      <span class="tag tag-neutral">${esc(it.status)}</span></div>
    ${problems}
    ${related}
    ${fillBlock}
    ${keepBlock}
    ${sugg}
    ${unmapped}
    <div class="qd-sub">This record, as it stands after cleaning</div>
    <table class="table"><thead><tr><th>Field</th><th>Value</th></tr></thead>
    <tbody>${it.fields.map(f => `<tr>
      <td style="font-weight:600;font-size:12.5px">${esc(f.label)}</td>
      <td class="mono ${String(f.working).trim() ? "" : "cellblank"}" style="font-size:12.5px">
        ${String(f.working).trim() ? esc(f.working) : "blank"}</td>
    </tr>`).join("")}${extraRows}</tbody></table>
    ${raw}
    <div style="display:flex;gap:8px;margin-top:12px;flex-wrap:wrap">
      <button class="btn btn-secondary" data-qact="approved"
        title="Accept this row exactly as it stands. It goes into the clean list.">Accept as it is</button>
      <button class="btn btn-secondary" data-qact="rejected"
        title="Leave this row out of the clean list and keep it on the review list for later.">Leave for later</button>
      <button class="btn btn-ghost" data-qact="removed"
        title="Set this row aside. It is not deleted: it goes to the Set Aside file with the reason, and can be brought back.">Set aside</button>
    </div>
    <div class="text-muted" style="font-size:11.5px;margin-top:8px">
      Values are never edited here one by one. The tool fills in missing
      location data it can derive, splits jammed values, and keeps one of a
      group of copies; each of those is recorded. Anything else is fixed at the
      source and loaded again.</div>`;
}

function vFillPreview(gid) {
  const f = UI.fillData;
  if (!f) return "";
  if (!f.fillable && !f.stuck) return `<div class="gpreview text-muted">Nothing in this group is missing a ZIP, city or state that the tool could fill.</div>`;
  const fields = Object.entries(f.by_field).map(([k, n]) => `${nf(n)} ${k}`).join(", ");
  const rows = f.items.map(it => `<tr>
    <td>${esc(it.name)}</td>
    <td class="mono" style="font-size:12px">${esc(it.address)}</td>
    <td class="mono" style="font-size:12px">${esc(it.city) || '<span class="cellblank">blank</span>'}</td>
    <td class="mono" style="font-size:12px">${esc(it.zip) || '<span class="cellblank">blank</span>'}</td>
    <td style="font-size:12px">${it.proposals.filter(p => p.value).map(p =>
      `<div><b>${esc(p.field)}</b> \u2192 <b class="mono">${esc(p.value)}</b>
       <span class="text-muted">${esc(p.why)}</span></div>`).join("")}</td>
    <td class="mono text-muted" style="font-size:11px">${esc(it.source)} row ${esc(it.row)}</td>
  </tr>`).join("");
  return `<div class="gpreview">
    <div class="gshape">
      <b>${nf(f.fillable)} row(s) can be filled in</b>${fields ? ` (${fields})` : ""}${f.stuck ? `, and ${nf(f.stuck)} cannot, because the street is unknown or runs through several ZIPs.` : "."}
      Each value comes from the row's own street and city and the reference data. Check the list, then approve.
    </div>
    <div class="pvscroll"><table class="table pvtable"><thead><tr>
      <th>Name</th><th>Street</th><th>City</th><th>ZIP</th><th>Would be filled</th><th>Source</th>
    </tr></thead><tbody>${rows}</tbody></table></div>
    <div class="pvtools">
      <span class="text-muted" style="font-size:12px">Page ${f.page + 1} of ${nf(f.pages)}</span>
      <button class="btn btn-secondary" data-fillpage="prev" data-gid="${esc(gid)}" ${f.page === 0 ? "disabled" : ""}>Prev</button>
      <button class="btn btn-secondary" data-fillpage="next" data-gid="${esc(gid)}" ${f.page >= f.pages - 1 ? "disabled" : ""}>Next</button>
      <span style="flex:1"></span>
      ${f.fillable ? `<button class="btn btn-primary" data-fillapply="${esc(gid)}"
        title="Fill in every value listed, on all ${nf(f.fillable)} rows, then check each row again. Every fill is recorded.">
        Approve: fill in all ${nf(f.fillable)} and check again</button>` : ""}
    </div>
    ${f.stuck_sample.length ? `<div class="text-muted" style="font-size:11.5px;margin-top:8px">
      Cannot be filled, for example: ${f.stuck_sample.map(s =>
        `${esc(s.address)} (${esc(s.proposals[0].why)})`).join("; ")}</div>` : ""}
  </div>`;
}

function vSummary() {
  const d = UI.data.summary;
  if (!d.ready) {
    return `${stageHead(8, "")}
      <div class="band">${I.alert}<div><b>Nothing has been processed yet.</b>
      <div class="band-sub">Process your files first, then the counts appear
      here.</div></div></div>`;
  }
  const g1 = d.goal1, g2 = d.goal2;
  const openRange = g1.open > 0;

  const headline = `<div class="goals">
    <div class="goal">
      <div class="goal-kicker">Goal 1</div>
      <div class="goal-title">Unique clients</div>
      <div class="goal-n">${nf(g1.count)}</div>
      <div class="goal-sub">${openRange
        ? `Between ${nf(g1.low)} and ${nf(g1.high)} until the
           ${nf(g1.open)} open question(s) below are decided.`
        : "Every person counted once, however many systems they appear in."}</div>
    </div>
    <div class="goal">
      <div class="goal-kicker">Goal 2</div>
      <div class="goal-title">Unique clients by program</div>
      <div class="goal-n">${nf(g2.count)}</div>
      <div class="goal-sub">The same person counted once in each program they
        take part in.</div>
    </div>
  </div>`;

  // per-program bars, so where the people are is visible at a glance
  const maxProg = Math.max(1, ...Object.values(g2.totals || {}));
  const progRows = (g2.programs || []).map(pname => {
    const n = g2.totals[pname] || 0;
    return `<div class="progrow">
      <div class="progname">${esc(pname)}</div>
      <div class="progbar"><i style="width:${Math.round(n / maxProg * 100)}%"></i></div>
      <div class="progn mono">${nf(n)}</div>
    </div>`;
  }).join("");

  const people = (g2.rows || []).length ? `
    <table class="table"><thead><tr>
      <th>Person</th><th>Name</th><th>Programs</th><th>Counts as</th>
    </tr></thead><tbody>
      ${g2.rows.map(r => `<tr>
        <td class="mono">${esc(r.master_id)}</td>
        <td>${esc(r.name)}</td>
        <td>${r.programs.map(esc).join(", ")}</td>
        <td class="mono">${r.count}</td></tr>`).join("")}
    </tbody></table>
    ${g2.more ? `<div class="text-muted" style="font-size:12px">
      and ${nf(g2.more)} more, all included in the counts and in the download.</div>` : ""}`
    : `<div class="text-muted" style="font-size:12.5px">
       No programs were recorded on these rows, so the second count cannot be
       broken down. Map a program or service area column on the matching stage
       to see it.</div>`;

  const openBlock = openRange ? `
    <div class="band band-warn">${I.alert}<div>
      <b>${nf(g1.open)} pair(s) of records may be the same person.</b> ${helpBtn("element", "identity")}
      <div class="band-sub">The tool never merges people on a guess. Until these
      are decided the client count is a range rather than a single number.
      Deciding them closes it.</div>
      <div style="margin-top:8px">
        <button class="btn btn-primary" data-act="open-proposals">
          Decide them now ${I.arrow}</button></div>
    </div></div>` : `
    <div class="band band-ok">${I.check}<div>
      <b>Nothing is left to decide, so this count is final.</b>
      <div class="band-sub">${nf(g1.auto)} link(s) were joined on evidence that
      could not reasonably be coincidence, and ${nf(g1.confirmed)} were confirmed
      by a person.</div></div></div>`;

  const rows = d.rows;
  return `
    ${stageHead(8, `<a class="btn btn-secondary" href="/api/summary" target="_blank">
       Open a page to print or share</a>
       ${continueBtn("Continue to the files")}`)}
    ${headline}
    ${openBlock}
    <div class="twocol">
      <div>
        <h3 class="sechead">Where the people are</h3>
        <div class="progwrap">${progRows || `<div class="text-muted">No programs recorded.</div>`}</div>
        <h3 class="sechead">Each person, and the programs they count in</h3>
        ${people}
      </div>
      <div class="sidecol">
        <div class="card"><div class="card-title">Rows behind these counts</div>
          <div class="rulelist">
            <div><b>${nf(rows.input)}</b> rows received</div>
            <div><b>${nf(rows.clean)}</b> clean and counted</div>
            <div><b>${nf(rows.review)}</b> still need work, not counted</div>
            <div><b>${nf(rows.aside)}</b> set aside</div>
          </div>
          <div class="text-muted" style="font-size:11.5px">
            Only rows that passed every check are counted as people. A row still
            in review has not been accepted into the dataset.</div>
        </div>
        <div class="card"><div class="card-title">Location confidence</div>
          <div class="rulelist">
            <div><b>${nf(d.verify.high)}</b> verified, high confidence</div>
            <div><b>${nf(d.verify.low)}</b> verified, low confidence</div>
            <div><b>${nf(d.verify.unmatched)}</b> not matched</div>
          </div></div>
        ${g2.no_program ? `<div class="card"><div class="card-title">Without a program</div>
          <div class="card-body" style="opacity:1">${nf(g2.no_program)} counted
          person(s) have no program recorded, so they are in the first count but
          not the second.</div></div>` : ""}
      </div>
    </div>`;
}

function vProposals() {
  const p = UI.proposals;
  if (!p) { loadProposals(); return `${stageHead(8, "")}
    <div class="text-muted" style="padding:20px">Loading the open questions...</div>`; }
  const items = p.items.map(it => `
    <div class="prop">
      <div class="prop-head">${I.alert} <b>${esc(it.reason)}</b></div>
      <div class="pvscroll"><table class="table pvtable">
        <thead><tr><th>Record</th><th>Name</th><th>Date of birth</th>
          <th>Address</th><th>System</th><th>Program</th><th>ID</th></tr></thead>
        <tbody>
          ${[it.a, it.b].map(s => `<tr>
            <td class="mono text-muted" style="font-size:11px">${esc(s.rid.split("||")[0])}</td>
            <td><b>${esc(s.name)}</b></td>
            <td class="mono">${esc(s.dob) || '<i class="cellblank">not recorded</i>'}</td>
            <td class="mono" style="font-size:12px">${esc(s.address)}</td>
            <td class="mono" style="font-size:12px">${esc(s.system)}</td>
            <td>${esc(s.program)}</td>
            <td class="mono" style="font-size:12px">${esc(s.client_id)}</td>
          </tr>`).join("")}
        </tbody></table></div>
      <div class="prop-ev">
        <b>What agrees:</b> ${it.evidence.map(esc).join("; ")}.
        ${it.cautions.length ? `<br><b>What to check:</b> ${it.cautions.map(esc).join("; ")}.` : ""}
      </div>
      <div class="prop-actions">
        <button class="btn btn-primary" data-idsame="${esc(it.pair[0])}"
          data-idb="${esc(it.pair[1])}">These are the same person</button>
        <button class="btn btn-secondary" data-iddiff="${esc(it.pair[0])}"
          data-idb="${esc(it.pair[1])}">These are different people</button>
      </div>
    </div>`).join("");
  return `
    ${stageHead(8, `<button class="btn btn-secondary" data-act="back-summary">
      Back to the results</button>`)}
    <div class="band">${I.alert}<div>
      <b>${nf(p.total)} pair(s) still to decide.</b>
      <div class="band-sub">Each of these could be one person recorded twice, or
      two people who happen to look alike. The tool will not choose for you,
      because merging two people who are not the same cannot be undone in the
      data you hand on.</div></div></div>
    ${items || '<div class="text-muted" style="padding:20px">Nothing left to decide.</div>'}
    <div class="qpage">
      <button class="btn btn-secondary" data-ppg="prev" ${p.page === 0 ? "disabled" : ""}>Prev</button>
      <span class="text-muted" style="font-size:12px">Page ${p.page + 1} of ${nf(p.pages)}</span>
      <button class="btn btn-secondary" data-ppg="next" ${p.page >= p.pages - 1 ? "disabled" : ""}>Next</button>
    </div>`;
}

async function loadProposals() {
  UI.proposals = await api(`/api/identity/proposals?page=${UI.propPage || 0}`);
  render();
}

function vAudit() {
  const a = UI.auditData;
  const f = UI.auditFilter || (UI.auditFilter = { q: "", kind: "", source: "", page: 0 });
  const sources = (UI.chrome.sources || []);
  const list = !a ? `<div class="text-muted" style="padding:20px">Loading the trail...</div>` : `
    <div class="text-muted" style="font-size:12px;margin:8px 0">
      ${nf(a.total)} entries${a.counts["set-up"] ? `, ${nf(a.counts["set-up"])} about the set-up` : ""}${a.counts.engine ? `, ${nf(a.counts.engine)} changes made while processing` : ""}${a.counts.decision ? `, ${nf(a.counts.decision)} decisions by a reviewer` : ""}.
      Identifiers and column names only; never a name, address or value.</div>
    <div class="pvscroll" data-scrollkey="audit"><table class="table pvtable"><thead><tr>
      <th>Kind</th><th>File</th><th>Row</th><th>Identifier</th><th>What happened</th></tr></thead>
      <tbody>${a.items.map(i => `<tr>
        <td><span class="tag ${i.kind === "decision" ? "tag-accent" : i.kind === "engine" ? "tag-neutral" : "tag-outline"}">${esc(i.kind)}</span></td>
        <td class="mono" style="font-size:11.5px">${esc(i.source || "")}</td>
        <td class="mono text-muted">${i.row !== undefined && i.row !== null ? esc(i.row) : ""}</td>
        <td class="mono" style="font-size:11.5px">${esc(i.id || "")}</td>
        <td style="font-size:12.5px">${esc(i.text)}</td></tr>`).join("")}</tbody></table></div>
    <div class="qpage">
      <button class="btn btn-secondary" data-auditpage="prev" ${a.page === 0 ? "disabled" : ""}>Prev</button>
      <span class="text-muted" style="font-size:12px">Page ${a.page + 1} of ${nf(a.pages)}</span>
      <button class="btn btn-secondary" data-auditpage="next" ${a.page >= a.pages - 1 ? "disabled" : ""}>Next</button>
    </div>`;
  return `
    ${header("Audit trail", "Everything that changed, and who or what changed it",
      "The set-up of the run, every change the engine made to a row, and every decision a reviewer took, as they stand right now. Nothing here is client data.",
      `<a class="btn btn-secondary" href="/api/export/file?which=audit" title="The full trail as a text file, safe to share">Download the full trail</a>
       <button class="btn btn-ghost" data-act="audit-back">Back</button>`)}
    <div class="qfilters">
      <label class="field"><label>Kind</label>
        <select class="input" data-auditf="kind">
          <option value="" ${f.kind === "" ? "selected" : ""}>Everything</option>
          <option value="set-up" ${f.kind === "set-up" ? "selected" : ""}>The set-up</option>
          <option value="engine" ${f.kind === "engine" ? "selected" : ""}>Changes made while processing</option>
          <option value="decision" ${f.kind === "decision" ? "selected" : ""}>Decisions by a reviewer</option>
        </select></label>
      <label class="field"><label>File</label>
        <select class="input" data-auditf="source">
          <option value="" ${f.source === "" ? "selected" : ""}>Every file</option>
          ${sources.map(s => `<option value="${esc(s)}" ${f.source === s ? "selected" : ""}>${esc(s)}</option>`).join("")}
        </select></label>
      <label class="field"><label>Search (identifier or words)</label>
        <input class="input" id="auditq" value="${esc(f.q)}" placeholder="for example E100, or ZIP"></label>
    </div>
    ${list}`;
}

async function loadAudit() {
  const f = UI.auditFilter || (UI.auditFilter = { q: "", kind: "", source: "", page: 0 });
  UI.auditData = await api(`/api/audit?q=${encodeURIComponent(f.q)}&kind=${encodeURIComponent(f.kind)}&source=${encodeURIComponent(f.source)}&page=${f.page}`);
  render();
}

function vExport() {
  const d = UI.data.export;
  if (!d.ready) {
    return `${stageHead(9, "")}
      <div class="band">${I.alert}<div><b>Nothing has been processed yet.</b>
      <div class="band-sub">Process your files first, then come back. If you
      just started over, add your files again.</div></div></div>`;
  }
  const r = d.recon;
  const files = [
    ["unique_clients", "Unique_Clients", `One row per person, counted once
      however many systems they appear in. This is the first count the project
      asks for.`, true],
    ["unique_by_program", "Unique_Clients_By_Program", `One row per person per
      program. A person in three programs appears three times. This is the
      second count.`, true],
    ["aside", "Set_Aside_Records", `${nf(r.aside)} row(s) you set aside: copies,
      summary rows and anything excluded, each with the reason. Nothing is
      deleted; this is where it went.`],
    ["clean", "Final_Clean_Mapped", `${nf(r.clean)} rows. The validated,
      geocoded master list${r.kept ? `, including ${nf(r.kept)} kept as entered by a reviewer` : ""}.`],
    ["review", "Manual_Review_Needed", `${nf(r.review + r.aside)} rows with
      original values, reasons, and resolution status. Fix the orig:: columns
      and re-upload; corrections never bypass validation.`],
    ["audit", "Secure_Audit_Log.txt",
      "Every transformation and decision, by system ID only. No names, no addresses."],
    ["quality", "Data_Quality_Report.csv", "Per-file counts and the top issue."],
  ];
  return `
    ${stageHead(9, `<button class="btn btn-secondary" data-act="open-audit"
      title="Everything that changed in this session and who changed it, no client data">Audit trail</button>`)}
    <div class="band band-ok">${I.check}<div>
      <b>The books balance: ${nf(r.clean)} clean + ${nf(r.review)} still needing
      work + ${nf(r.aside)} set aside = ${nf(r.input)} input rows.</b>
      <div class="band-sub">Live numbers from your actual decisions.
      The server asserts this and fails loudly if it ever breaks.</div></div></div>
    <div class="seg">${["CSV", "Excel", "JSON"].map(f => `
      <label class="seg-opt"><input type="radio" name="fmt"
        ${d.fmt === f ? "checked" : ""} data-fmt="${f}">${f}</label>`).join("")}</div>
    ${d.advanced ? `<div class="sortbar">
      <span class="text-muted" style="font-size:11.5px">Order</span>
      ${[["", "As exported"], ["name", "By name"], ["on", "Included first"]].map(([k, lbl]) => `
        <button class="chip ${UI.sortCols.sort === k ? "on" : ""}"
          data-sortkey="${k}" data-sortaction="cols"
          data-sortdir="${UI.sortCols.sort === k && UI.sortCols.dir === "asc" ? "desc" : "asc"}">
          ${lbl}</button>`).join("")}
    </div>
    <div class="chips">${sortRows(d.cols, UI.sortCols,
        { name: c => c.name, on: c => (c.on ? 0 : 1) }).map(c => `
      <button class="chip ${c.on ? "on" : ""}" data-col="${esc(c.name)}"
        data-on="${c.on ? 0 : 1}"><span class="ckbox ${c.on ? "on" : ""}"
        style="width:12px;height:12px">${c.on ? I.check : ""}</span>${esc(c.name)}</button>`).join("")}
      </div>` : ""}
    ${vSetups()}
    <div class="card" style="margin-top:14px">
      <div class="card-title">A page you can print or hand on</div>
      <div class="card-body" style="opacity:1">
        A one page summary of this batch: what came in, what is ready, what still
        needs work, and what happens next. It holds counts only, never client
        records, so it is safe to share or attach to a report.</div>
      <div><a class="btn btn-secondary" href="/api/summary" target="_blank">
        Open the summary page</a></div>
    </div>
    <div class="list" style="margin-top:14px">${files.map(([k, name, desc, primary]) => `
      <div class="lrow"><div class="lmain">
        <div class="lline"><span class="lname">${esc(name)}</span></div>
        <div class="ldesc">${esc(desc)}</div></div>
        <a class="btn ${primary ? "btn-primary" : "btn-secondary"}"
          href="/api/export/file?which=${k}" download>${I.download} Download</a>
      </div>`).join("")}</div>`;
}

async function saveSchema() {
  await api("/api/schema", { schema: UI.data.schema.fields });
  return load("schema");
}

/* ---------------- render + events ---------------- */
let _railTimer = null;
function railHover() {
  if (document.body.dataset.railHover) return;
  document.body.dataset.railHover = "1";
  document.addEventListener("mouseover", e => {
    const inRail = !!e.target.closest(".rail");
    if (inRail && !UI.railOpen && !_railTimer) {
      // a held hover opens it; a pass-through does not
      _railTimer = setTimeout(() => { _railTimer = null; UI.railOpen = true; render(); }, 380);
    }
  });
  document.addEventListener("mouseout", e => {
    const toRail = e.relatedTarget && e.relatedTarget.closest && e.relatedTarget.closest(".rail");
    if (toRail) return;
    if (!e.target.closest(".rail")) return;
    if (_railTimer) { clearTimeout(_railTimer); _railTimer = null; }
    if (UI.railOpen && !UI.railPinned) { UI.railOpen = false; render(); }
  });
}

function render() {
  renderRail();
  const railEl = document.querySelector(".rail");
  if (railEl) {
    railEl.classList.toggle("open", !!UI.railOpen);
    railHover();
  }
  const c = document.getElementById("content");
  const v = { check: vCheck, sources: vSources, schema: vSchema, audit: vAudit,
    prepare: vPrepare, map: vMap, programs: vPrograms, run: vRun, review: vReview,
    queue: vQueue, summary: vSummary, proposals: vProposals,
    export: vExport }[UI.screen];

  // Redrawing rebuilds every grid, which would throw away where each one was
  // scrolled. A person paging through wide data while looking at the last
  // columns must stay on those columns, so each grid's position is kept by
  // its place on the screen and put back after the redraw. The page's own
  // scroll position is kept the same way.
  const kept = {};
  c.querySelectorAll(".pvscroll").forEach((el, i) => {
    const key = el.dataset.scrollkey || `${UI.screen}#${i}`;
    if (el.scrollLeft || el.scrollTop) kept[key] = { x: el.scrollLeft, y: el.scrollTop };
  });
  const pageY = window.scrollY, sameScreen = UI._lastScreen === UI.screen;
  UI._lastScreen = UI.screen;

  c.innerHTML = (v ? v() : "") + vHelpPanel();

  c.querySelectorAll(".pvscroll").forEach((el, i) => {
    const key = el.dataset.scrollkey || `${UI.screen}#${i}`;
    const k = kept[key];
    if (k) { el.scrollLeft = k.x; el.scrollTop = k.y; }
  });
  if (sameScreen) window.scrollTo(0, pageY);
}

document.addEventListener("click", async (e) => {
  // a click on the help backdrop, outside the card, closes the help
  if (e.target.classList && e.target.classList.contains("helpwrap")) {
    UI.helpOpen = null; render(); return;
  }
  // a click anywhere outside the menu closes it, unless it was pinned open
  if (UI.railOpen && !UI.railPinned && !e.target.closest(".rail")) {
    UI.railOpen = false; render();
  }
  const held = e.target.closest("button, .chip, .ckbox");
  if (held && !held.disabled) {
    // the clicked control is held until the requests it started are answered
    held.classList.add("is-busy");
    held.disabled = true;
    const release = () => { held.classList.remove("is-busy"); held.disabled = false; };
    setTimeout(function wait() { if (_pending > 0) setTimeout(wait, 100); else release(); }, 150);
  }
  const t = e.target.closest("[data-goto],[data-act],[data-include],[data-op],[data-table],[data-group],[data-preview],[data-pv],[data-qsel],[data-qpage],[data-qact],[data-col],[data-set],[data-pick],[data-help],[data-setupcheck],[data-setupload],[data-setupdel],[data-auditpage],[data-group-undo],[data-pgpick],[data-pgtarget],[data-fillpreview],[data-fillpage],[data-fillapply],[data-qfill],[data-keeprow],[data-showcol],[data-dupopen],[data-dupdecide],[data-dupall],[data-fixmap],[data-table-jump],[data-pgout],[data-idsame],[data-iddiff],[data-ppg],[data-suggest],[data-gotorid],[data-qcheck],[data-qbulk],[data-sortaction],[data-headerrow],[data-resume],[data-dropsession],[data-autosave],[data-table-preview],[data-ppage],[data-sreq],[data-sdel]");
  if (!t) return;

  if (t.dataset.goto !== undefined) {
    const stage = parseInt(t.dataset.goto, 10);
    await api("/api/goto", { stage });
    UI.openGroup = null;
    return load(SCREEN_BY_STAGE[stage]);
  }
  if (t.dataset.include) {
    await api("/api/sources/include", { key: t.dataset.include, on: t.dataset.on === "1" });
    return load("sources");
  }
  if (t.dataset.op) {
    await api("/api/prepare/toggle", { id: t.dataset.op, removed: t.dataset.removed === "1" });
    return load("prepare");
  }
  if (t.dataset.pick) {
    const d = UI.data.prepare;
    const cols = (d.columns[UI.addOp.table] || []).slice();
    if (t.dataset.pick === "all") UI.addOp.cols = cols;
    else if (t.dataset.pick === "none") UI.addOp.cols = [];
    else UI.addOp.cols = cols.filter(c => UI.addOp.cols.indexOf(c) < 0);
    return render();
  }
  if (t.dataset.tableJump !== undefined) {
    const i = UI.data.map.tables.findIndex(x => x.key === t.dataset.tableJump);
    if (i >= 0) UI.activeTable = i;
    window.scrollTo({ top: 0 });
    return render();
  }
  if (t.dataset.fixmap) {
    // One click: fix the matching and run again, so the reviewer does not
    // have to walk back four stages to do what the diagnosis just described.
    await api("/api/map", { table: t.dataset.fixmap, field: t.dataset.fixfield,
                            column: t.dataset.fixcol });
    await api("/api/run/start", UI.data.runData
      ? UI.data.runData.settings : { require_geocode: false, jitter: true, seed: 1337 });
    UI.fixNotice = `${t.dataset.fixfield} on ${shortKey(t.dataset.fixmap)} is now matched to '${t.dataset.fixcol}'. Processing again.`;
    for (let i = 0; i < 200; i++) {
      await new Promise(r => setTimeout(r, 300));
      const st = await api("/api/run/status");
      if (st.state !== "running") break;
    }
    return load("review");
  }
  if (t.dataset.fixmap) {
    // One click: fix the matching and run again, so the reviewer does not
    // walk back four stages to do what the diagnosis just described.
    await api("/api/map", { table: t.dataset.fixmap, field: t.dataset.fixfield,
                            column: t.dataset.fixcol });
    const settings = (UI.data.runData && UI.data.runData.settings)
      || { require_geocode: false, jitter: true, seed: 1337 };
    await api("/api/run/start", settings);
    UI.fixNotice = `${t.dataset.fixfield} on ${shortKey(t.dataset.fixmap)} is now matched to '${t.dataset.fixcol}'. Processed again.`;
    for (let i = 0; i < 300; i++) {
      await new Promise(r => setTimeout(r, 300));
      const st = await api("/api/run/status");
      if (st.state !== "running") break;
    }
    return load("review");
  }
  if (t.dataset.tableJump !== undefined) {
    const i = UI.data.map.tables.findIndex(x => x.key === t.dataset.tableJump);
    if (i >= 0) UI.activeTable = i;
    window.scrollTo({ top: 0 });
    return render();
  }
  if (t.dataset.dupopen) {
    UI.dupOpen = UI.dupOpen || {};
    UI.dupOpen[t.dataset.dupopen] = !UI.dupOpen[t.dataset.dupopen];
    return render();
  }
  if (t.dataset.dupdecide) {
    UI.pendingDups = UI.pendingDups || [];
    UI.pendingDups = UI.pendingDups.filter(x => !(x.table === t.dataset.dupdecide && x.gid === t.dataset.gid));
    UI.pendingDups.push({ table: t.dataset.dupdecide, gid: t.dataset.gid, decision: t.dataset.verdict });
    return render();
  }
  if (t.dataset.dupall) {
    UI.pendingDups = (UI.pendingDups || []).filter(x => x.table !== t.dataset.dupall);
    UI.pendingDups.push({ table: t.dataset.dupall, all: true, decision: t.dataset.verdict });
    return render();
  }
  if (t.dataset.pgpick !== undefined) {
    // pick a name up, or put it down if it was already held
    UI.progSel = UI.progSel === t.dataset.pgpick ? null : t.dataset.pgpick;
    return render();
  }
  if (t.dataset.pgtarget !== undefined && UI.progSel && !t.closest("[data-pgpick]") && !t.closest("input")) {
    const name = UI.progSel, into = t.dataset.pgtarget;
    UI.progSel = null;
    progMove(name, into);
    return render();
  }
  if (t.dataset.pgout) {
    await api("/api/programs/group",
              { name: t.dataset.pgout, into: "__alone__" });
    return load("map");
  }
  if (t.dataset.idsame || t.dataset.iddiff) {
    const a = t.dataset.idsame || t.dataset.iddiff;
    const verdict = t.dataset.idsame ? "same" : "different";
    await api("/api/identity/decide", { a, b: t.dataset.idb, verdict });
    UI.proposals = null;
    return loadProposals();
  }
  if (t.dataset.ppg) {
    UI.propPage = (UI.propPage || 0) + (t.dataset.ppg === "next" ? 1 : -1);
    UI.proposals = null;
    return loadProposals();
  }
  if (t.dataset.suggest !== undefined) {
    const s = UI.data.queue.detail.suggestions[+t.dataset.suggest];
    if (!s) return;
    const it = UI.data.queue.detail;
    await api("/api/queue/action", { rid: it.rid, action: "corrected", edits: s.edits });
    UI.qNotice = `Applied: ${s.label}. The row was checked again.`;
    return refreshQueue();
  }
  if (t.dataset.help) {
    UI.helpOpen = t.dataset.help;
    return render();
  }
  if (t.dataset.setupcheck) {
    UI.setupReport = await api("/api/setups/check", { name: t.dataset.setupcheck });
    return render();
  }
  if (t.dataset.setupload) {
    const out = await api("/api/setups/load", { name: t.dataset.setupload }, "Loading the set-up");
    UI.setupReport = null; UI.progWork = null;
    UI.fixNotice = out.ok ? `Loaded: ${out.applied.join(", ") || "nothing fitted"}.` : (out.why || "");
    return load(UI.screen);
  }
  if (t.dataset.setupdel) {
    if (!window.confirm(`Delete the saved set-up "${t.dataset.setupdel}"?`)) return;
    await api("/api/setups/delete", { name: t.dataset.setupdel });
    UI.setupReport = null;
    return loadSetups();
  }
  if (t.dataset.auditpage) {
    UI.auditFilter.page += t.dataset.auditpage === "next" ? 1 : -1;
    return loadAudit();
  }
  if (t.dataset.fillpreview) {
    const gid = t.dataset.fillpreview;
    if (UI.fillFor === gid && UI.fillData) { UI.fillFor = null; UI.fillData = null; return render(); }
    UI.fillFor = gid; UI.fillPage = 0;
    UI.fillData = await api(`/api/fill/preview?gid=${gid}&page=0`);
    return render();
  }
  if (t.dataset.fillpage) {
    UI.fillPage = (UI.fillPage || 0) + (t.dataset.fillpage === "next" ? 1 : -1);
    UI.fillData = await api(`/api/fill/preview?gid=${t.dataset.gid}&page=${UI.fillPage}`);
    return render();
  }
  if (t.dataset.fillapply) {
    const out = await api("/api/fill/apply", { gid: t.dataset.fillapply }, "Filling in the approved values");
    UI.fixNotice = `Filled in ${nf(out.filled)} row(s) and checked them again.`;
    UI.fillFor = null; UI.fillData = null;
    return load("review");
  }
  if (t.dataset.qfill) {
    const out = await api("/api/fill/apply", { rids: [t.dataset.qfill] });
    UI.qNotice = out.filled ? "Filled in and checked again." : "Nothing could be filled.";
    return refreshQueue();
  }
  if (t.dataset.keeprow) {
    const out = await api("/api/queue/keep-one", { rid: t.dataset.keeprow });
    UI.qNotice = out.ok ? `Kept one row and set ${out.set_aside} aside.` : (out.why || "");
    return refreshQueue();
  }
  if (t.dataset.showcol) {
    UI.qExtraCols = UI.qExtraCols || {};
    UI.qExtraCols[t.dataset.showcol] = !UI.qExtraCols[t.dataset.showcol];
    return render();
  }
  if (t.dataset.gotorid) {
    // Find the record in the queue and open it, whatever page it sits on.
    const rid = t.dataset.gotorid;
    const all = UI.data.queue.matching_rids || [];
    const at = all.indexOf(rid);
    if (at < 0) {
      UI.qNotice = "That record is not in the current filters. Clear them to reach it.";
      return render();
    }
    UI.qPage = Math.floor(at / (UI.data.queue.per || 12));
    UI.qSel = at % (UI.data.queue.per || 12);
    UI.qEdits = {};
    return refreshQueue();
  }
  if (t.dataset.qcheck) {
    const rid = t.dataset.qcheck;
    if (UI.qAllMatching) {          // a click on a row leaves the whole-set mode
      UI.qAllMatching = false;
      UI.qSelected = {};
      UI.data.queue.items.forEach(i => { UI.qSelected[i.rid] = true; });
    }
    UI.qSelected[rid] = !UI.qSelected[rid];
    return render();
  }
  if (t.dataset.qbulk) {
    const out = await api("/api/queue/bulk",
      { ...bulkScope(), action: t.dataset.qbulk });
    UI.qNotice = out.note || "";
    UI.qSelected = {}; UI.qAllMatching = false; UI.qPage = 0; UI.qSel = 0;
    return refreshQueue();
  }
  if (t.dataset.sortaction) {
    const key = t.dataset.sortkey, dir = t.dataset.sortdir;
    const action = t.dataset.sortaction;
    if (action === "check") { toggleSort(UI.sortCheck, key, dir); return render(); }
    if (action === "cols") { toggleSort(UI.sortCols, key, dir); return render(); }
    if (action === "preview") {
      toggleSort(UI.sortPreview, key, dir);
      const pp = UI.previewPane;
      return loadPreviewPane(pp.key, pp.which, 0);
    }
    if (action === "group") {
      toggleSort(UI.sortGroup, key, dir);
      UI.gPage = 0;
      return loadPreview(UI.openGroup);
    }
    if (action === "queue") {
      toggleSort(UI.sortQueue, key, dir);
      UI.qPage = 0; UI.qSel = 0; UI.qEdits = {};
      UI.data.queue = await api(`/api/queue?filter=${UI.qFilter}&page=0&sel=0`
        + `&sort=${encodeURIComponent(key)}&dir=${dir}`);
      return render();
    }
    return;
  }
  if (t.dataset.resume) {
    const out = await api("/api/sessions/resume", { id: t.dataset.resume });
    UI.sessions = null;
    if (out.ok) {
      UI.resumeNotice = out;
      load("sources");
    }
    return;
  }
  if (t.dataset.dropsession) {
    await api("/api/sessions/delete", { id: t.dataset.dropsession });
    UI.sessions = null;
    return load("check");
  }
  if (t.dataset.autosave !== undefined) {
    await api("/api/sessions/autosave", { on: t.dataset.autosave === "1" });
    UI.sessions = null;
    return load("check");
  }
  if (t.dataset.headerrow !== undefined) {
    const key = t.dataset.hrtable;
    await api("/api/map/header", { key, row: parseInt(t.dataset.headerrow, 10) });
    UI.previewPane = null;
    return load(UI.screen === "map" ? "map" : "sources");
  }
  if (t.dataset.tablePreview) {
    const key = t.dataset.tablePreview;
    UI.openTable = UI.openTable === key ? null : key;
    UI.previewPane = null;
    return render();
  }
  if (t.dataset.ppage) {
    const p = UI.previewPane;
    if (!p) return;
    const to = t.dataset.ppage === "first" ? 0
      : t.dataset.ppage === "next" ? p.data.page + 1 : p.data.page - 1;
    return loadPreviewPane(p.key, p.which, to);
  }
  if (t.dataset.sreq !== undefined) {
    const f = UI.data.schema.fields[+t.dataset.sreq];
    f.required = t.dataset.on === "1";
    return saveSchema();
  }
  if (t.dataset.sdel !== undefined) {
    UI.data.schema.fields.splice(+t.dataset.sdel, 1);
    return saveSchema();
  }
  if (t.dataset.table !== undefined) { UI.activeTable = +t.dataset.table; return render(); }
  if (t.dataset.group) {
    // chosen now, applied together later
    UI.pendingGroups = UI.pendingGroups || {};
    UI.pendingGroups[t.dataset.group] = t.dataset.decision;
    return render();
  }
  if (t.dataset.groupUndo) {
    if (UI.pendingGroups) delete UI.pendingGroups[t.dataset.groupUndo];
    return render();
  }
  if (t.dataset.preview) {
    UI.openGroup = UI.openGroup === t.dataset.preview ? null : t.dataset.preview;
    UI.previewData = null; UI.gQ = ""; UI.gPage = 0;
    return render();
  }
  if (t.dataset.pv) {
    UI.gPage += t.dataset.pv === "next" ? 1 : -1;
    return loadPreview(UI.openGroup);
  }
  if (t.dataset.qsel !== undefined) {
    UI.qSel = +t.dataset.qsel; UI.qEdits = {};
    UI.data.queue = await api(qUrl());
    return render();
  }
  if (t.dataset.qpage) {
    UI.qPage += t.dataset.qpage === "next" ? 1 : -1; UI.qSel = 0; UI.qEdits = {};
    UI.qSel = 0;
    UI.data.queue = await api(qUrl());
    return render();
  }
  if (t.dataset.qact) {
    const rid = UI.data.queue.detail.rid;
    const body = { rid, action: t.dataset.qact };
    if (t.dataset.qact === "corrected") body.edits = UI.qEdits;
    await api("/api/queue/action", body);
    UI.qEdits = {};
    UI.data.queue = await api(qUrl());
    UI.chrome = (await api("/api/ui?screen=queue")).chrome;
    return render();
  }
  if (t.dataset.col) {
    await api("/api/export/col", { name: t.dataset.col, on: t.dataset.on === "1" });
    return load("export");
  }
  if (t.dataset.set) {
    const s = UI.data.runData.settings;
    s[t.dataset.set] = t.dataset.on === "1";
    return render();   // sent with the run request
  }

  switch (t.dataset.act) {
    case "continue": {
      if (UI.screen === "programs") await progApply();
      if (UI.screen === "review") {
        const gd = Object.entries(UI.pendingGroups || {}).map(([gid, decision]) => ({ gid, decision }));
        if (gd.length) { await api("/api/review/decide-many", { decisions: gd }); UI.pendingGroups = {}; }
        if ((UI.pendingDups || []).length) { await api("/api/prepare/dupes/decide", { decisions: UI.pendingDups }); UI.pendingDups = []; }
      }
      const out = await api("/api/continue", {});
      if (out.ok) { UI.openGroup = null; load(SCREEN_BY_STAGE[out.stage]); }
      break;
    }
    case "copy-report": {
      const ta = document.getElementById("report");
      ta.select(); document.execCommand("copy");
      UI.copied = true; render();
      setTimeout(() => { UI.copied = false; render(); }, 1600);
      break;
    }
    case "run": {
      const s = UI.data.runData.settings;
      const seedEl = document.getElementById("seed");
      const out = await api("/api/run/start", {
        require_geocode: s.require_geocode, jitter: s.jitter,
        seed: seedEl ? seedEl.value : s.seed });
      if (out.ok) { watchRun(() => load("run"), "Processing your files"); load("run"); }
      break;
    }
    case "confirm-table": {
      const tables = UI.data.map.tables;
      const key = tables[UI.activeTable].key;
      await api("/api/map/confirm", { table: key });
      // move to the next table still needing confirmation, wrapping around
      tables[UI.activeTable].confirmed = true;
      const nxt = nextUnconfirmed(tables, UI.activeTable);
      if (nxt >= 0) UI.activeTable = nxt;
      UI.openTable = null; UI.previewPane = null;
      load("map");
      break;
    }
    case "add-op": {
      const a = UI.addOp, d = UI.data.prepare;
      let op;
      if (a.type === "calc_zip") {
        op = { type: "calc_zip", street_col: a.street_col, city_col: a.city_col || "",
               zip_col: a.zip_col || "", mode: a.mode || "blanks",
               name: (a.calc_name || "Zip_calculated").trim() || "Zip_calculated" };
      } else if (a.type === "clean") {
        op = { type: "clean", columns: a.cols.slice(), case: a.case || "none",
               sanitize: !!a.sanitize, strip_punct: !!a.strip_punct };
      } else if (a.type === "split_delim") {
        const delim = a.delimLabel === "Custom..."
          ? (a.delimCustom || "") : d.delimiters[a.delimLabel];
        if (!delim) break;
        op = { type: "split_delim", column: a.col, delimiter: delim,
               maxsplit: parseInt(a.maxsplit, 10) || 0,
               names: a.names ? a.names.split(",").map(s => s.trim()) : null };
      } else {
        op = { type: a.type, column: a.col };
      }
      await api("/api/prepare/add", { table: a.table, op });
      UI.addOp.cols = [];
      load("prepare");
      break;
    }
    case "add-field": {
      const label = (document.getElementById("newfield").value || "").trim();
      if (!label) break;
      UI.data.schema.fields.push({
        role: "custom", label,
        dtype: document.getElementById("newtype").value,
        length: parseInt(document.getElementById("newlen").value, 10) || 0,
        default: (document.getElementById("newdefault").value || "").trim(),
        required: false,
      });
      await saveSchema();
      break;
    }
    case "reset-schema":
      await api("/api/schema/reset", {});
      load("schema");
      break;
    case "resume-files": load("sources"); break;
    case "restart": {
      if (!UI.confirmReset) {
        UI.confirmReset = true;
        render();
        clearTimeout(UI._resetT);
        UI._resetT = setTimeout(() => { UI.confirmReset = false; render(); }, 6000);
        break;
      }
      UI.confirmReset = false;
      await api("/api/reset", {});
      // clear every piece of local view state too, so nothing survives
      UI.openGroup = null; UI.openTable = null; UI.previewPane = null;
      UI.previewData = null; UI.previewFor = null;
      UI.gQ = ""; UI.gPage = 0;
      UI.qFilter = "pending"; UI.qPage = 0; UI.qSel = 0; UI.qEdits = {};
      UI.activeTable = 0;
      UI.addOp = { type: "clean", table: "", cols: [], col: "", case: "none",
                   sanitize: false, strip_punct: false, delimLabel: "Comma  ,",
                   delimCustom: "", maxsplit: 0, names: "" };
      if (UI.runPoll) { clearInterval(UI.runPoll); UI.runPoll = null; }
      load("check");
      break;
    }
    case "undo": await api("/api/review/undo", {}); load("review"); break;
    case "open-queue":
      UI.qFilter = "pending"; UI.qPage = 0; UI.qSel = 0;
      UI.qSelected = {}; UI.qAllMatching = false; UI.qNotice = "";
      UI.data.queue = await api(qUrl());
      UI.screen = "queue"; render(); break;
    case "rail-toggle":
      UI.railOpen = !UI.railOpen; UI.railPinned = UI.railOpen;
      render(); break;
    case "close-app": {
      // A plain yes-or-no, rather than a button that changes its own label
      // and changes back if the second click is slow.
      const ok = window.confirm(
        "Close Crosswalk?\n\nAnything you have downloaded is safe, and your "
        + "progress on this batch is saved so you can pick it up next time.");
      if (!ok) break;
      if (UI.beat) clearInterval(UI.beat);
      // The goodbye page asks the tool to stop once it is on screen.
      window.location.href = "/goodbye";
      break;
    }
    case "express": await expressGo(false); break;
    case "express-anyway": await expressGo(true); break;
    case "express-relax-id": {
      const sch = (await api("/api/ui?screen=schema")).schema.fields;
      sch.forEach(f => { if (f.role === "Client_ID") f.required = false; });
      await api("/api/schema", { schema: sch });
      await expressGo(false);
      break;
    }
    case "undo-change": {
      const out = await api("/api/undo", {});
      if (out.ok) UI.undoNotice = `Took back: ${out.label}`;
      UI.previewPane = null;
      load(UI.screen === "queue" ? "review" : UI.screen);
      break;
    }
    case "example": {
      const out = await api("/api/sources/example", {});
      if (out.ok) {
        UI.exampleNotice = `Loaded ${out.loaded.length} example file(s). These
          hold made-up records, so you can practice the whole process without
          using real client data. Start over when you want to clear them.`;
        load("sources");
      }
      break;
    }
    case "show-groups": load("review"); break;
    case "help-close": UI.helpOpen = null; render(); break;
    case "setup-save": {
      const name = (document.getElementById("setupname") || {}).value || "";
      const note = (document.getElementById("setupnote") || {}).value || "";
      const out = await api("/api/setups/save", { name, note });
      UI.setupName = ""; UI.setupNote = "";
      UI.fixNotice = out.ok ? `Saved the set-up "${out.name}".` : (out.why || "");
      UI.setupReport = null;
      await loadSetups(); break;
    }
    case "setup-dismiss": UI.setupReport = null; render(); break;
    case "open-audit": {
      UI.auditReturn = UI.screen; UI.auditData = null; UI.screen = "audit";
      render(); loadAudit(); break;
    }
    case "audit-back": load(UI.auditReturn || "check"); break;
    case "apply-groups": {
      const decisions = Object.entries(UI.pendingGroups || {}).map(([gid, decision]) => ({ gid, decision }));
      if (!decisions.length) break;
      await api("/api/review/decide-many", { decisions }, "Applying your decisions");
      UI.pendingGroups = {}; UI.openGroup = null;
      UI.fixNotice = `Applied ${nf(decisions.length)} decision(s).`;
      load("review"); break;
    }
    case "clear-groups": UI.pendingGroups = {}; render(); break;
    case "apply-dups": {
      const decisions = UI.pendingDups || [];
      if (!decisions.length) break;
      await api("/api/prepare/dupes/decide", { decisions }, "Applying your duplicate decisions");
      UI.pendingDups = [];
      UI.fixNotice = `Applied ${nf(decisions.length)} duplicate decision(s) and processed again.`;
      load("review"); break;
    }
    case "clear-dups": UI.pendingDups = []; render(); break;
    case "open-proposals":
      UI.proposals = null; UI.propPage = 0;
      UI.screen = "proposals"; render(); break;
    case "back-summary": UI.proposals = null; load("summary"); break;
    case "pg-reset": UI.progSel = null; UI.progWork = null; await api("/api/programs/reset", {}); load("programs"); break;
    case "pg-refresh": UI.progWork = null; await api("/api/programs/refresh", {}); load("programs"); break;
    case "pg-alone": {
      const name = UI.progSel; UI.progSel = null;
      progMove(name, "__alone__");
      render(); break;
    }
    case "pg-drop": UI.progSel = null; render(); break;
    case "prog-apply": await progApply(); load("programs"); break;
    case "prog-preview": {
      await progApply();
      const out = await api("/api/programs/preview", {}, "Previewing the counts");
      if (!out.ok) UI.fixNotice = out.why || "";
      load("programs"); break;
    }
    case "q-keep-one-per-program": {
      const out = await api("/api/queue/keep-one-per-program", {});
      UI.qNotice = out.note || "";
      UI.qSelected = {}; UI.qAllMatching = false;
      refreshQueue();
      break;
    }
    case "q-select-page": {
      const q = UI.data.queue;
      const allOn = q.items.every(i => UI.qAllMatching || UI.qSelected[i.rid]);
      UI.qAllMatching = false;
      q.items.forEach(i => { UI.qSelected[i.rid] = !allOn; });
      render();
      break;
    }
    case "q-select-matching": UI.qAllMatching = true; render(); break;
    case "q-clear-selection":
      UI.qSelected = {}; UI.qAllMatching = false; render(); break;
    case "q-clear":
      UI.qProblem = ""; UI.qSource = ""; UI.qQ = ""; UI.qPage = 0; UI.qSel = 0;
      UI.qNotice = ""; refreshQueue(); break;
    case "q-bulk-fix": {
      const field = document.getElementById("qbulkfield").value;
      const value = document.getElementById("qbulkvalue").value;
      if (!String(value).trim()) break;
      const out = await api("/api/queue/bulk",
        { ...bulkScope(), action: "corrected", edits: { [field]: value } });
      UI.qNotice = out.note || "";
      UI.qSelected = {}; UI.qAllMatching = false; UI.qPage = 0; UI.qSel = 0;
      // The corrected rows have left the pending list, so follow them rather
      // than leaving the reviewer looking at an empty page.
      if (out.fixed) { UI.qFilter = "corrected"; UI.qProblem = ""; }
      refreshQueue();
      break;
    }
  }
});

document.addEventListener("change", async (e) => {
  const t = e.target;
  if (t.dataset.auditf) {
    UI.auditFilter[t.dataset.auditf] = t.value; UI.auditFilter.page = 0;
    return loadAudit();
  }
  if (t.dataset.dupfield) {
    const cur = (UI.data.dupes && UI.data.dupes.fields || []).slice();
    const f = t.dataset.dupfield, i = cur.indexOf(f);
    if (t.checked && i < 0) cur.push(f);
    if (!t.checked && i >= 0) cur.splice(i, 1);
    if (!cur.length) return render();
    await api("/api/prepare/dupes/fields", { fields: cur });
    return load("review");
  }

  if (t.dataset.pgrename !== undefined) {
    const w = progLocal();
    const g = w.groups.find(x => x.canonical === t.dataset.pgrename);
    if (g && t.value.trim() && t.value.trim() !== g.canonical) { g.canonical = t.value.trim(); w.dirty = true; }
    return render();
  }
  if (t.dataset.progcol !== undefined) {
    const w = progLocal();
    w.columns[t.dataset.progcol] = t.value;
    w.dirty = true;
    return render();
  }
  if (t.dataset.srcdefault !== undefined) {
    const key = UI.data.map.tables[UI.activeTable].key;
    await api("/api/sources/default",
              { key, field: t.dataset.srcdefault, value: t.value });
    return load("map");
  }
  if (t.dataset.sf) {
    const f = UI.data.schema.fields[+t.dataset.i];
    f[t.dataset.sf] = t.dataset.sf === "length"
      ? (parseInt(t.value, 10) || 0) : t.value;
    return saveSchema();
  }
  if (t.dataset.gde) {
    await api("/api/run/gde-field", { name: t.dataset.gde, on: t.checked });
    return load("run");
  }
  if (t.dataset.addop) {
    UI.addOp[t.dataset.addop] = t.value;
    if (t.dataset.addop === "type" || t.dataset.addop === "table") {
      delete UI.addOp.street_col; delete UI.addOp.city_col; delete UI.addOp.zip_col;
      UI.addOp.cols = []; UI.addOp.col = "";
    }
    return render();
  }
  if (t.dataset.addopCk) {
    UI.addOp[t.dataset.addopCk] = t.checked;
    return;
  }
  if (t.dataset.opcol !== undefined) {
    const c = t.dataset.opcol;
    const i = UI.addOp.cols.indexOf(c);
    if (t.checked && i < 0) UI.addOp.cols.push(c);
    if (!t.checked && i >= 0) UI.addOp.cols.splice(i, 1);
    return;
  }
  if (t.dataset.mode) { await api("/api/mode", { mode: t.dataset.mode }); return load(UI.screen); }
  if (t.dataset.qnarrow) {
    const which = t.dataset.qnarrow;
    if (which === "per") UI.qPer = parseInt(t.value, 10) || 12;
    if (which === "problem") UI.qProblem = t.value;
    if (which === "source") UI.qSource = t.value;
    UI.qPage = 0; UI.qSel = 0; UI.qNotice = "";
    UI.qSelected = {}; UI.qAllMatching = false;
    return refreshQueue();
  }
  if (t.dataset.qfilter) {
    UI.qFilter = t.dataset.qfilter; UI.qPage = 0; UI.qSel = 0; UI.qEdits = {};
    UI.qPage = 0; UI.qSel = 0;
    UI.data.queue = await api(qUrl());
    return render();
  }
  if (t.dataset.fmt) { await api("/api/export/format", { fmt: t.dataset.fmt }); return load("export"); }
  if (t.dataset.mapField !== undefined) {
    const key = UI.data.map.tables[UI.activeTable].key;
    await api("/api/map", { table: key, field: t.dataset.mapField, column: t.value });
    return load("map");
  }
  if (t.id === "qsearch") {
    UI.qQ = t.value; UI.qPage = 0; UI.qSel = 0;
    UI.qSelected = {}; UI.qAllMatching = false;
    return refreshQueue();
  }
  if (t.id === "filepick") {
    const fd = new FormData();
    for (const f of t.files) fd.append("files", f);
    await fetch("/api/sources/upload", { method: "POST", body: fd });
    return load("sources");
  }
});

document.addEventListener("input", (e) => {
  if (e.target.id === "setupname") { UI.setupName = e.target.value; return; }
  if (e.target.id === "setupnote") { UI.setupNote = e.target.value; return; }
  if (e.target.id === "auditq") {
    UI.auditFilter.q = e.target.value; UI.auditFilter.page = 0;
    clearTimeout(UI._auditT); UI._auditT = setTimeout(loadAudit, 250);
    return;
  }
  const t = e.target;
  if (t.dataset.edit !== undefined) UI.qEdits[t.dataset.edit] = t.value;
  if (t.id === "pvq") {
    UI.gQ = t.value; UI.gPage = 0;
    clearTimeout(UI._pvT);
    UI._pvT = setTimeout(() => loadPreview(UI.openGroup), 220);
  }
});

/* ---------------- boot ---------------- */
// While this window is open the tool is told so every half minute. When the
// window is closed the messages stop, and the tool closes itself rather than
// sitting in the background with no way to reach it.
function startHeartbeat() {
  const beat = () => { fetch("/api/heartbeat").catch(() => {}); };
  beat();
  UI.beat = setInterval(beat, 10000);
  // On the way out, tell the tool so it can stop rather than wait. A reload
  // sends this too, and the next heartbeat cancels it.
  window.addEventListener("pagehide", () => {
    try { navigator.sendBeacon("/api/bye", ""); } catch (e) {}
  });
}

startHeartbeat();
fetch("/static/help.json").then(r => r.json()).then(h => { UI.help = h; }).catch(() => {});
load("check");
