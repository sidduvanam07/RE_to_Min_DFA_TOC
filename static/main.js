/* static/main.js — Automata Toolchain frontend logic */
"use strict";

// ── Setup Cytoscape dagre ───────────────────────────────────────
cytoscape.use(cytoscapeDagre);

const CY      = {};   // key -> cytoscape instance
const CY_DATA = {};   // key -> pending data (lazy render)
let activeResCard = null;

// ── Cytoscape stylesheet ────────────────────────────────────────
function cyStyle() {
  return [
    { selector: ".ghost", style: { opacity: 0, width: 1, height: 1, label: "" } },

    { selector: "node:not(.ghost)", style: {
        shape: "ellipse", width: 58, height: 58,
        "background-color": "#0e1120",
        "border-color": "#3a4068", "border-width": 2,
        label: "data(id)", color: "#9aa3c8",
        "font-family": "JetBrains Mono, monospace", "font-size": 11,
        "text-valign": "center", "text-halign": "center",
        "text-wrap": "wrap", "text-max-width": 54
    }},

    { selector: ".n-start", style: {
        "border-color": "#5ef6ff", "border-width": 2.5,
        "background-color": "rgba(94,246,255,0.09)", color: "#5ef6ff"
    }},
    { selector: ".n-accept", style: {
        "border-color": "#3dffa0", "border-width": 3,
        "background-color": "rgba(61,255,160,0.09)", color: "#3dffa0"
    }},
    { selector: ".n-start.n-accept", style: {
        "border-color": "#b97fff",
        "background-color": "rgba(185,127,255,0.1)", color: "#d4aaff"
    }},

    { selector: "edge", style: {
        "curve-style": "bezier",
        "target-arrow-shape": "vee",
        "target-arrow-color": "rgba(124,106,255,0.75)",
        "line-color": "rgba(124,106,255,0.45)", width: 1.5,
        label: "data(lbl)", color: "#8892bb",
        "font-family": "JetBrains Mono, monospace", "font-size": 10,
        "text-background-color": "#080b14", "text-background-opacity": 0.9,
        "text-background-padding": "3px", "edge-text-rotation": "autorotate"
    }},
    { selector: ".e-eps", style: {
        "line-style": "dashed",
        "line-color": "rgba(124,106,255,0.3)",
        "target-arrow-color": "rgba(124,106,255,0.4)",
        color: "rgba(124,106,255,0.9)", width: 1
    }},
    { selector: ".e-start", style: {
        "curve-style": "straight",
        "target-arrow-shape": "vee",
        "target-arrow-color": "#5ef6ff", "line-color": "#5ef6ff",
        width: 1.5, label: "", opacity: 0.6
    }},
    { selector: ".e-self", style: {
        "curve-style": "loop",
        "loop-direction": "-45deg", "loop-sweep": "45deg"
    }},

    // Path highlight
    { selector: ".hl-node", style: {
        "border-color": "#ffcc5e", "border-width": 3.5,
        "background-color": "rgba(255,204,94,0.15)", color: "#ffcc5e"
    }},
    { selector: ".hl-edge", style: {
        "line-color": "#ffcc5e", "target-arrow-color": "#ffcc5e",
        color: "#ffcc5e", width: 3
    }},
  ];
}

// ── Build Cytoscape elements from API data ──────────────────────
function buildElems(data) {
  const elems = [];
  const acceptSet = new Set(data.accept);

  // Invisible ghost node for the start arrow
  elems.push({ data: { id: "__s__" }, classes: "ghost" });

  // State nodes
  for (const s of data.states) {
    const cls = [
      s === data.start   ? "n-start"  : "",
      acceptSet.has(s)   ? "n-accept" : "",
    ].filter(Boolean).join(" ");
    elems.push({ data: { id: s }, classes: cls });
  }

  // Entry edge
  elems.push({ data: { id: "__se__", source: "__s__", target: data.start, lbl: "" }, classes: "e-start" });

  // Group parallel transitions by (from, to)
  const edgeMap = {};
  for (const t of data.transitions) {
    const k = t.from + "|||" + t.to;
    if (!edgeMap[k]) edgeMap[k] = { from: t.from, to: t.to, syms: [] };
    const sym = t.symbol === "eps" ? "\u03b5" : t.symbol;
    if (!edgeMap[k].syms.includes(sym)) edgeMap[k].syms.push(sym);
  }

  let ei = 0;
  for (const e of Object.values(edgeMap)) {
    const selfLoop = e.from === e.to;
    const allEps   = e.syms.every(x => x === "\u03b5");
    const cls = [selfLoop ? "e-self" : "", allEps ? "e-eps" : ""].filter(Boolean).join(" ");
    elems.push({
      data: { id: "e" + ei++, source: e.from, target: e.to, lbl: e.syms.join(", ") },
      classes: cls,
    });
  }
  return elems;
}

// ── Launch / refresh Cytoscape instance ────────────────────────
function launchCy(key) {
  if (!CY_DATA[key]) return;
  if (CY[key]) CY[key].destroy();

  CY[key] = cytoscape({
    container: document.getElementById("cy-" + key),
    elements:  buildElems(CY_DATA[key]),
    style:     cyStyle(),
    layout: {
      name: "dagre", rankDir: "LR",
      nodeSep: 60, rankSep: 130, padding: 48,
      animate: true, animationDuration: 450,
    },
    wheelSensitivity: 0.3, minZoom: 0.25, maxZoom: 4,
  });

  delete CY_DATA[key];
}

// ── Diagram controls ────────────────────────────────────────────
function fitDiagram(key) {
  if (CY[key]) CY[key].fit(40);
}
function resetDiagram(key) {
  if (CY[key]) { CY[key].fit(40); CY[key].elements().removeClass("hl-node hl-edge"); }
}

// ── Tab switching ───────────────────────────────────────────────
function switchTab(key, view) {
  const panel = document.getElementById("panel-" + key);
  panel.querySelectorAll(".tab-btn").forEach(b => b.classList.remove("active"));
  panel.querySelectorAll(".tab-pane").forEach(p => p.classList.remove("active"));

  const btn = [...panel.querySelectorAll(".tab-btn")]
    .find(b => b.textContent.toLowerCase().includes(view === "table" ? "table" : "diagram"));
  if (btn) btn.classList.add("active");

  const pane = document.getElementById(key + "-" + view);
  if (pane) pane.classList.add("active");

  if (view === "diagram") {
    if (CY_DATA[key]) launchCy(key);
    else if (CY[key]) { CY[key].resize(); CY[key].fit(40); }
  }
}

// ── Helpers ─────────────────────────────────────────────────────
function esc(s) {
  return s.replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;");
}

// ── Render automaton (table + store diagram data) ───────────────
function renderAutomaton(key, data) {
  const acceptSet = new Set(data.accept);

  document.getElementById(key + "-title").textContent = data.label;
  document.getElementById(key + "-stats").textContent =
    data.states.length + " states · " + data.transitions.length + " transitions";

  // Pill row
  const pillsEl = document.getElementById(key + "-pills");
  pillsEl.innerHTML = data.states.map(s => {
    const isS = s === data.start, isA = acceptSet.has(s);
    const cls = (isS && isA) ? "pill-sa" : isS ? "pill-s" : isA ? "pill-a" : "pill-n";
    const lbl = (isS ? "\u25b6 " : "") + s + (isA ? " \u2605" : "");
    return `<span class="pill ${cls}">${lbl}</span>`;
  }).join("");

  // Table rows
  const tbody = document.getElementById(key + "-tbody");
  if (!data.transitions.length) {
    tbody.innerHTML = `<tr><td colspan="3" style="color:var(--muted);padding:.7rem .65rem">No transitions</td></tr>`;
  } else {
    tbody.innerHTML = data.transitions.map(t => {
      const acc = acceptSet.has(t.from);
      const sym = t.symbol === "eps"
        ? `<span class="td-eps">\u03b5</span>`
        : `<code>${esc(t.symbol)}</code>`;
      return `<tr>
        <td class="${acc ? "td-accept" : ""}">${t.from}${acc ? " \u2605" : ""}</td>
        <td>${sym}</td>
        <td>${t.to}${acceptSet.has(t.to) ? " \u2605" : ""}</td>
      </tr>`;
    }).join("");
  }

  // Store for lazy diagram render
  CY_DATA[key] = data;
}

// ── Path highlight on Min DFA diagram ──────────────────────────
function highlightPath(path) {
  if (!CY["minDfa"]) { switchTab("minDfa", "diagram"); return; }
  CY["minDfa"].elements().removeClass("hl-node hl-edge");
  if (!path || !path.length) return;
  const nodes = new Set();
  for (const step of path) {
    nodes.add(step.from); nodes.add(step.to);
    CY["minDfa"].edges(`[source="${step.from}"][target="${step.to}"]`).addClass("hl-edge");
  }
  nodes.forEach(n => CY["minDfa"].nodes(`[id="${n}"]`).addClass("hl-node"));
}

// ── Render test result cards ────────────────────────────────────
function renderResults(results) {
  const grid = document.getElementById("testResults");
  grid.innerHTML = "";

  for (const r of results) {
    const ac = r.accepted;
    const inpHtml = r.input === ""
      ? `<em class="empty">(empty string)</em>`
      : `<span>${esc(r.input)}</span>`;

    let pathHtml = "";
    if (!r.path.length) {
      pathHtml = `<p class="no-path">${r.input === "" ? "Empty — no transitions" : "No valid transition from start"}</p>`;
    } else {
      pathHtml = `<div class="path-steps">` +
        r.path.map(step =>
          `<div class="p-step">
            <span class="st">${step.from}</span>
            <span class="arr">&#8211;[<span class="sym">${step.symbol === "eps" ? "\u03b5" : esc(step.symbol)}</span>]&rarr;</span>
            <span class="st">${step.to}</span>
          </div>`
        ).join("") + `</div>`;
    }

    const card = document.createElement("div");
    card.className = `res-card ${ac ? "accepted" : "rejected"}`;
    card.innerHTML = `
      <div class="res-top">
        <span class="res-input">${inpHtml}</span>
        <span class="verdict ${ac ? "accepted" : "rejected"}">${ac ? "Accepted" : "Rejected"}</span>
      </div>
      ${pathHtml}
      <p class="path-hint">&#128073; Click to highlight path on Min DFA diagram</p>`;

    card.addEventListener("click", () => {
      if (activeResCard) activeResCard.classList.remove("active-path");
      if (activeResCard === card) {
        activeResCard = null;
        resetDiagram("minDfa");
        return;
      }
      activeResCard = card;
      card.classList.add("active-path");
      switchTab("minDfa", "diagram");
      setTimeout(() => highlightPath(r.path), 200);
    });

    grid.appendChild(card);
  }
}

// ── Main pipeline call ──────────────────────────────────────────
async function runPipeline() {
  const regex  = document.getElementById("regex").value.trim();
  const raw    = document.getElementById("inputs").value;
  const inputs = raw.split("\n").map(s => s.trimEnd());
  const btn    = document.getElementById("runBtn");
  const errBox = document.getElementById("errBox");

  errBox.style.display = "none";
  if (!regex) {
    errBox.textContent = "Please enter a regular expression.";
    errBox.style.display = "block";
    return;
  }

  btn.classList.add("loading");
  btn.disabled = true;
  activeResCard = null;

  try {
    const resp = await fetch("/api/run", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ regex, inputs }),
    });
    const data = await resp.json();

    if (data.error) {
      errBox.textContent = "Error: " + data.error;
      errBox.style.display = "block";
      document.getElementById("resultsArea").classList.add("hidden");
      return;
    }

    renderAutomaton("nfa",    data.nfa);
    renderAutomaton("dfa",    data.dfa);
    renderAutomaton("minDfa", data.min_dfa);
    renderResults(data.results);

    // Reset all tabs to table view
    ["nfa", "dfa", "minDfa"].forEach(k => switchTab(k, "table"));

    const area = document.getElementById("resultsArea");
    area.classList.remove("hidden");
    area.scrollIntoView({ behavior: "smooth", block: "start" });

  } catch (e) {
    errBox.textContent = "Network error: " + e.message;
    errBox.style.display = "block";
  } finally {
    btn.classList.remove("loading");
    btn.disabled = false;
  }
}

// Enter key on regex input
document.getElementById("regex")
  .addEventListener("keydown", e => { if (e.key === "Enter") runPipeline(); });
