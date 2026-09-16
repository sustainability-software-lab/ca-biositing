/**
 * dashboard_click_export.js
 * -------------------------
 * Click-to-export UI for CA Biositing Vega-Lite dashboards.
 *
 * This file is inlined into each dashboard HTML by inject_click_export.py.
 * It defines window.attachClickExport(view) which is called after vegaEmbed
 * resolves, wiring up the click listener and rendering the export UI.
 *
 * IMPORTANT: This script is placed in <head> so it is parsed before the
 * vegaEmbed body script. window.attachClickExport is defined immediately
 * (synchronously) so it is available when the vegaEmbed Promise resolves.
 * DOM manipulation is deferred to DOMContentLoaded so that document.body
 * exists before we try to append elements.
 *
 * LBNL Brand Colors:
 *   Deep Blue:  #00313C
 *   Teal:       #00B5E2
 *   Red:        #E31837
 *   Light Gray: #D1D3D4
 *
 * Features:
 *   1. Fixed-position floating sidebar panel (#cab-float-panel + #cab-float-tray)
 *      anchored to the right side of the viewport. Collapses via toggle button.
 *      Falls back to bottom-of-page layout on narrow viewports (<768px).
 *   2. Ctrl+Click / Cmd+Click: immediately add clicked point to table.
 *      Shift+Click: add to table AND copy to clipboard.
 *      Regular click: show in pinned panel (existing behaviour).
 *   3. updateTrayCount() keeps the tray counter in sync; flashTray() shows
 *      brief confirmation messages in the tray.
 */
(function () {
  "use strict";

  // ── State (module-level, available immediately) ───────────────────────────
  /** @type {Array<Object>} rows — each entry is a plain object of field→value */
  var rows = [];

  /** Fields to exclude from display and export */
  var SKIP_KEYS = { jitter: true, __count: true };
  var SKIP_PREFIX = "_";

  /** The datum from the most recently clicked point */
  var currentDatum = null;

  /** Whether the DOM has been set up */
  var domReady = false;

  /** Whether the float panel is collapsed */
  var panelCollapsed = false;

  /** Queue of view instances waiting for DOM to be ready */
  var pendingViews = [];

  // ── Helpers ───────────────────────────────────────────────────────────────

  function filterDatum(datum) {
    var result = {};
    Object.keys(datum).forEach(function (k) {
      if (k.startsWith(SKIP_PREFIX)) return;
      if (SKIP_KEYS[k]) return;
      result[k] = datum[k];
    });
    return result;
  }

  function formatValue(v) {
    if (v === null || v === undefined) return "";
    if (typeof v === "number") {
      return parseFloat(v.toPrecision(6)).toString();
    }
    return String(v);
  }

  function escHtml(s) {
    return String(s)
      .replace(/&/g, "&amp;")
      .replace(/</g, "&lt;")
      .replace(/>/g, "&gt;")
      .replace(/"/g, "&quot;");
  }

  function escAttr(s) {
    return String(s).replace(/&/g, "&amp;").replace(/"/g, "&quot;");
  }

  function csvEscape(s) {
    var str = String(s === null || s === undefined ? "" : s);
    if (
      str.indexOf(",") !== -1 ||
      str.indexOf('"') !== -1 ||
      str.indexOf("\n") !== -1
    ) {
      return '"' + str.replace(/"/g, '""') + '"';
    }
    return str;
  }

  // ── DOM Setup (deferred to DOMContentLoaded) ──────────────────────────────

  function setupDOM() {
    // ── CSS ──────────────────────────────────────────────────────────────────
    var style = document.createElement("style");
    style.textContent = [
      /* ── Base font / shared ── */
      ".cab-click-export, #cab-float-panel, #cab-float-tray {",
      '  font-family: system-ui, -apple-system, "Segoe UI", Roboto, "Helvetica Neue", Arial, sans-serif;',
      "}",

      /* ── Inline (bottom-of-page) container — shown on mobile, hidden on desktop ── */
      ".cab-click-export {",
      "  margin: 1.5rem 0;",
      "  max-width: 1200px;",
      "}",

      /* ── Fixed floating panel (desktop only) ── */
      "#cab-float-panel {",
      "  position: fixed;",
      "  top: 20px;",
      "  right: 16px;",
      "  width: 280px;",
      "  z-index: 1000;",
      "  background: #e8f7fc;",
      "  border: 2px solid #00B5E2;",
      "  border-radius: 8px;",
      "  box-shadow: 0 4px 16px rgba(0,0,0,0.18);",
      "  display: none;" /* hidden until first click */,
      "}",
      "#cab-float-panel-header {",
      "  display: flex;",
      "  align-items: center;",
      "  justify-content: space-between;",
      "  padding: 0.55rem 0.85rem 0.45rem;",
      "  background: #00313C;",
      "  border-radius: 6px 6px 0 0;",
      "  cursor: pointer;",
      "  user-select: none;",
      "}",
      "#cab-float-panel-header h3 {",
      "  color: #fff;",
      "  margin: 0;",
      "  font-size: 0.88rem;",
      "  font-weight: 700;",
      "}",
      "#cab-float-toggle {",
      "  background: none;",
      "  border: none;",
      "  color: #fff;",
      "  font-size: 0.85rem;",
      "  cursor: pointer;",
      "  padding: 0 0.2rem;",
      "  line-height: 1;",
      "}",
      "#cab-float-body {",
      "  padding: 0.75rem 0.85rem 0.85rem;",
      "}",

      /* ── Fixed tray (desktop only) — always visible ── */
      "#cab-float-tray {",
      "  position: fixed;",
      "  right: 16px;",
      "  width: 280px;",
      "  z-index: 999;",
      "  background: #fff;",
      "  border: 2px solid #00B5E2;",
      "  border-radius: 8px;",
      "  box-shadow: 0 4px 16px rgba(0,0,0,0.14);",
      "  padding: 0.6rem 0.85rem;",
      "  display: flex;",
      "  align-items: center;",
      "  justify-content: space-between;",
      "  gap: 0.5rem;",
      "  top: 20px;" /* will be repositioned by JS after panel renders */,
      "}",
      "#cab-tray-count {",
      "  font-size: 0.82rem;",
      "  font-weight: 600;",
      "  color: #00313C;",
      "  flex: 1;",
      "}",
      "#cab-tray-flash {",
      "  font-size: 0.78rem;",
      "  color: #00B5E2;",
      "  font-weight: 700;",
      "  min-width: 60px;",
      "  text-align: right;",
      "}",

      /* ── Pinned panel (used inside float panel AND inline fallback) ── */
      ".cab-pinned-panel {",
      "  background: #e8f7fc;",
      "  border: 2px solid #00B5E2;",
      "  border-radius: 6px;",
      "  padding: 1rem 1.25rem;",
      "  margin-bottom: 1rem;",
      "}",
      ".cab-pinned-panel h3 {",
      "  color: #00313C;",
      "  margin: 0 0 0.6rem;",
      "  font-size: 1rem;",
      "  font-weight: 700;",
      "}",
      ".cab-field-grid {",
      "  display: grid;",
      "  grid-template-columns: 1fr;",
      "  gap: 0.2rem 0;",
      "  margin-bottom: 0.65rem;",
      "}",
      /* Inside float panel, single-column is fine at 280px */
      "#cab-float-body .cab-field-grid {",
      "  grid-template-columns: 1fr;",
      "}",
      /* Inside inline fallback, use auto-fill */
      ".cab-click-export .cab-field-grid {",
      "  grid-template-columns: repeat(auto-fill, minmax(220px, 1fr));",
      "  gap: 0.25rem 1.25rem;",
      "}",
      ".cab-field { font-size: 0.82rem; line-height: 1.45; word-break: break-word; }",
      ".cab-field strong { color: #00313C; }",
      ".cab-notes-row {",
      "  display: flex;",
      "  align-items: center;",
      "  gap: 0.5rem;",
      "  margin-bottom: 0.65rem;",
      "}",
      ".cab-notes-row label { font-size: 0.82rem; font-weight: 600; color: #00313C; white-space: nowrap; }",
      ".cab-notes-input {",
      "  flex: 1;",
      "  padding: 0.3rem 0.6rem;",
      "  border: 1px solid #D1D3D4;",
      "  border-radius: 4px;",
      "  font-size: 0.82rem;",
      "  font-family: inherit;",
      "}",
      ".cab-notes-input:focus { outline: none; border-color: #00B5E2; box-shadow: 0 0 0 2px rgba(0,181,226,0.2); }",
      ".cab-actions { display: flex; gap: 0.5rem; flex-wrap: wrap; }",

      /* ── Table section (always at bottom of page) ── */
      ".cab-table-section h3 { color: #00313C; font-size: 1rem; font-weight: 700; margin: 0; }",
      ".cab-table-header { display: flex; justify-content: space-between; align-items: center; margin-bottom: 0.5rem; }",
      ".cab-table-wrap { overflow-x: auto; }",
      ".cab-table { width: 100%; border-collapse: collapse; font-size: 0.82rem; }",
      ".cab-table th { background: #00313C; color: #fff; padding: 0.4rem 0.65rem; text-align: left; white-space: nowrap; }",
      ".cab-table td { padding: 0.3rem 0.65rem; border-bottom: 1px solid #D1D3D4; vertical-align: middle; }",
      ".cab-table tr:hover td { background: #e8f7fc; }",
      ".cab-table-notes-input {",
      "  width: 100%; min-width: 120px; padding: 0.2rem 0.4rem;",
      "  border: 1px solid #D1D3D4; border-radius: 3px;",
      "  font-size: 0.8rem; font-family: inherit; box-sizing: border-box;",
      "}",
      ".cab-table-notes-input:focus { outline: none; border-color: #00B5E2; }",

      /* ── Buttons ── */
      ".cab-btn {",
      "  padding: 0.35rem 0.8rem; border: none; border-radius: 4px;",
      "  cursor: pointer; font-size: 0.82rem; font-family: inherit;",
      "  font-weight: 600; transition: opacity 0.15s;",
      "}",
      ".cab-btn:hover { opacity: 0.85; }",
      ".cab-btn-primary { background: #00B5E2; color: #fff; }",
      ".cab-btn-success { background: #00313C; color: #fff; }",
      ".cab-btn-danger  { background: #E31837; color: #fff; }",
      ".cab-btn-sm { padding: 0.15rem 0.45rem; font-size: 0.75rem; border-radius: 3px; }",
      ".cab-empty-msg { color: #58595B; font-size: 0.85rem; font-style: italic; padding: 0.5rem 0; }",

      /* ── Keyboard hint ── */
      ".cab-kbd-hint {",
      "  font-size: 0.72rem;",
      "  color: #58595B;",
      "  margin-top: 0.4rem;",
      "  line-height: 1.4;",
      "}",
      ".cab-kbd-hint kbd {",
      "  background: #f0f0f0;",
      "  border: 1px solid #ccc;",
      "  border-radius: 3px;",
      "  padding: 0 3px;",
      "  font-size: 0.7rem;",
      "  font-family: monospace;",
      "}",

      /* ── Mobile: hide fixed elements, show inline panel ── */
      "@media (max-width: 767px) {",
      "  #cab-float-panel { display: none !important; }",
      "  #cab-float-tray  { display: none !important; }",
      "  .cab-click-export { display: block !important; }",
      "}",

      /* ── Desktop: hide inline pinned panel (float panel takes over) ── */
      "@media (min-width: 768px) {",
      "  .cab-click-export .cab-pinned-panel { display: none !important; }",
      "}",
    ].join("\n");
    document.head.appendChild(style);

    // ── Fixed floating panel ───────────────────────────────────────────────
    var floatPanel = document.createElement("div");
    floatPanel.id = "cab-float-panel";
    floatPanel.innerHTML = [
      '<div id="cab-float-panel-header">',
      "  <h3>📌 Last Clicked Point</h3>",
      '  <button id="cab-float-toggle" title="Collapse/expand panel">▼</button>',
      "</div>",
      '<div id="cab-float-body">',
      '  <div class="cab-field-grid" id="cab-float-fields"></div>',
      '  <div class="cab-notes-row">',
      '    <label for="cab-float-notes">Notes:</label>',
      '    <input type="text" id="cab-float-notes" class="cab-notes-input"',
      '           placeholder="Add a note…" />',
      "  </div>",
      '  <div class="cab-actions">',
      '    <button class="cab-btn cab-btn-primary" id="cab-float-copy-btn">📋 Copy</button>',
      '    <button class="cab-btn cab-btn-success" id="cab-float-add-btn">➕ Add</button>',
      "  </div>",
      '  <div class="cab-kbd-hint">',
      "    <kbd>Ctrl</kbd>+click to add instantly &nbsp;·&nbsp; <kbd>Shift</kbd>+click to add &amp; copy",
      "  </div>",
      "</div>",
    ].join("\n");
    document.body.appendChild(floatPanel);

    // ── Fixed tray ────────────────────────────────────────────────────────
    var floatTray = document.createElement("div");
    floatTray.id = "cab-float-tray";
    floatTray.innerHTML = [
      '<span id="cab-tray-count">📋 0 flagged points</span>',
      '<span id="cab-tray-flash"></span>',
      '<button class="cab-btn cab-btn-primary cab-btn-sm" id="cab-tray-export-btn">⬇ CSV</button>',
    ].join("\n");
    document.body.appendChild(floatTray);

    // Position tray below panel (updated whenever panel changes)
    positionTray();

    // ── Inline (bottom-of-page) container ────────────────────────────────
    var container = document.createElement("div");
    container.className = "cab-click-export";
    container.innerHTML = [
      /* Inline pinned panel — only shown on mobile */
      '<div class="cab-pinned-panel" id="cab-pinned" style="display:none">',
      "  <h3>📌 Last Clicked Point</h3>",
      '  <div class="cab-field-grid" id="cab-pinned-fields"></div>',
      '  <div class="cab-notes-row">',
      '    <label for="cab-notes-input">Notes:</label>',
      '    <input type="text" id="cab-notes-input" class="cab-notes-input"',
      '           placeholder="Add a note before adding to table…" />',
      "  </div>",
      '  <div class="cab-actions">',
      '    <button class="cab-btn cab-btn-primary" id="cab-copy-btn">📋 Copy to Clipboard</button>',
      '    <button class="cab-btn cab-btn-success" id="cab-add-btn">➕ Add to Table</button>',
      "  </div>",
      "</div>",
      /* Table section — always at bottom */
      '<div class="cab-table-section">',
      '  <div class="cab-table-header">',
      "    <h3>Selected Points for Export</h3>",
      '    <button class="cab-btn cab-btn-primary" id="cab-export-btn">⬇ Export CSV</button>',
      "  </div>",
      '  <div class="cab-table-wrap">',
      '    <table class="cab-table" id="cab-table">',
      '      <thead id="cab-thead"></thead>',
      '      <tbody id="cab-tbody"></tbody>',
      "    </table>",
      "  </div>",
      '  <div id="cab-empty-msg" class="cab-empty-msg">No points added yet. Click a data point, then press ➕ Add to Table.</div>',
      '  <button class="cab-btn cab-btn-danger" id="cab-clear-btn" style="margin-top:0.6rem">🗑 Clear All</button>',
      "</div>",
    ].join("\n");
    document.body.appendChild(container);

    domReady = true;

    // Wire up any views that were attached before DOM was ready
    pendingViews.forEach(function (view) {
      wireView(view);
    });
    pendingViews = [];
  }

  // ── Tray positioning ──────────────────────────────────────────────────────

  function positionTray() {
    var panel = document.getElementById("cab-float-panel");
    var tray = document.getElementById("cab-float-tray");
    if (!panel || !tray) return;
    // Both elements are position:fixed, so top values are viewport-relative.
    // getBoundingClientRect().bottom is already viewport-relative — do NOT add scrollY.
    var panelVisible = panel.style.display !== "none";
    if (panelVisible) {
      var panelBottom = panel.getBoundingClientRect().bottom;
      tray.style.top = panelBottom + 8 + "px";
    } else {
      tray.style.top = "20px";
    }
  }

  // ── Tray counter & flash ──────────────────────────────────────────────────

  function updateTrayCount() {
    var el = document.getElementById("cab-tray-count");
    if (!el) return;
    var n = rows.length;
    el.textContent = "📋 " + n + " flagged point" + (n === 1 ? "" : "s");
  }

  var _flashTimer = null;
  function flashTray(msg) {
    var el = document.getElementById("cab-tray-flash");
    if (!el) return;
    el.textContent = msg;
    if (_flashTimer) clearTimeout(_flashTimer);
    _flashTimer = setTimeout(function () {
      el.textContent = "";
      _flashTimer = null;
    }, 1800);
  }

  // ── Collapse / expand toggle ──────────────────────────────────────────────

  function setupCollapseToggle() {
    var header = document.getElementById("cab-float-panel-header");
    var body = document.getElementById("cab-float-body");
    var toggle = document.getElementById("cab-float-toggle");
    if (!header || !body || !toggle) return;

    header.addEventListener("click", function () {
      panelCollapsed = !panelCollapsed;
      body.style.display = panelCollapsed ? "none" : "";
      toggle.textContent = panelCollapsed ? "▶" : "▼";
      positionTray();
    });
  }

  // ── Pinned Panel ──────────────────────────────────────────────────────────

  function renderPinned(datum) {
    // Float panel (desktop)
    var floatPanel = document.getElementById("cab-float-panel");
    var floatFields = document.getElementById("cab-float-fields");
    if (floatPanel && floatFields) {
      floatPanel.style.display = "";
      var html = buildFieldsHtml(datum);
      floatFields.innerHTML = html;
      // Expand if collapsed
      if (panelCollapsed) {
        panelCollapsed = false;
        var body = document.getElementById("cab-float-body");
        var toggle = document.getElementById("cab-float-toggle");
        if (body) body.style.display = "";
        if (toggle) toggle.textContent = "▼";
      }
      // Reposition tray after panel becomes visible
      setTimeout(positionTray, 50);
    }

    // Inline panel (mobile fallback)
    var panel = document.getElementById("cab-pinned");
    var fieldsEl = document.getElementById("cab-pinned-fields");
    if (panel && fieldsEl) {
      panel.style.display = "";
      fieldsEl.innerHTML = buildFieldsHtml(datum);
    }
  }

  function buildFieldsHtml(datum) {
    var html = "";
    Object.keys(datum).forEach(function (k) {
      html +=
        '<div class="cab-field"><strong>' +
        escHtml(k) +
        ":</strong> " +
        escHtml(formatValue(datum[k])) +
        "</div>";
    });
    return html;
  }

  // ── Table ─────────────────────────────────────────────────────────────────

  function getColumns() {
    var seen = {};
    var cols = [];
    rows.forEach(function (row) {
      Object.keys(row).forEach(function (k) {
        if (k !== "notes" && !seen[k]) {
          seen[k] = true;
          cols.push(k);
        }
      });
    });
    cols.push("notes");
    return cols;
  }

  function renderTable() {
    var thead = document.getElementById("cab-thead");
    var tbody = document.getElementById("cab-tbody");
    var emptyMsg = document.getElementById("cab-empty-msg");

    if (rows.length === 0) {
      thead.innerHTML = "";
      tbody.innerHTML = "";
      emptyMsg.style.display = "";
      return;
    }

    emptyMsg.style.display = "none";
    var cols = getColumns();

    var thHtml = "<tr>";
    cols.forEach(function (c) {
      thHtml += "<th>" + escHtml(c) + "</th>";
    });
    thHtml += "<th></th></tr>";
    thead.innerHTML = thHtml;

    var tbHtml = "";
    rows.forEach(function (row, idx) {
      tbHtml += "<tr>";
      cols.forEach(function (c) {
        if (c === "notes") {
          tbHtml +=
            '<td><input type="text" class="cab-table-notes-input"' +
            ' data-row="' +
            idx +
            '"' +
            ' value="' +
            escAttr(row.notes || "") +
            '"' +
            ' placeholder="note…" /></td>';
        } else {
          tbHtml += "<td>" + escHtml(formatValue(row[c])) + "</td>";
        }
      });
      tbHtml +=
        '<td><button class="cab-btn cab-btn-danger cab-btn-sm cab-remove-btn" data-row="' +
        idx +
        '">✕</button></td>';
      tbHtml += "</tr>";
    });
    tbody.innerHTML = tbHtml;

    tbody.querySelectorAll(".cab-remove-btn").forEach(function (btn) {
      btn.addEventListener("click", function () {
        rows.splice(parseInt(btn.getAttribute("data-row"), 10), 1);
        renderTable();
        updateTrayCount();
      });
    });

    tbody.querySelectorAll(".cab-table-notes-input").forEach(function (inp) {
      inp.addEventListener("input", function () {
        rows[parseInt(inp.getAttribute("data-row"), 10)].notes = inp.value;
      });
    });
  }

  // ── CSV Export ────────────────────────────────────────────────────────────

  function exportCSV() {
    if (rows.length === 0) {
      alert("No points to export. Add some rows first.");
      return;
    }
    var cols = getColumns();
    var lines = [cols.map(csvEscape).join(",")];
    rows.forEach(function (row) {
      lines.push(
        cols
          .map(function (c) {
            return csvEscape(formatValue(row[c]));
          })
          .join(","),
      );
    });
    var csvStr = lines.join("\r\n");

    var rawTitle = document.title || "dashboard";
    var baseName = rawTitle
      .replace(/[^a-z0-9_\-]/gi, "_")
      .replace(/_+/g, "_")
      .replace(/^_|_$/g, "");
    var filename = (baseName || "flagged_points") + "_flagged.csv";

    var blob = new Blob([csvStr], { type: "text/csv;charset=utf-8;" });
    var url = URL.createObjectURL(blob);
    var a = document.createElement("a");
    a.href = url;
    a.download = filename;
    document.body.appendChild(a);
    a.click();
    document.body.removeChild(a);
    URL.revokeObjectURL(url);
  }

  // ── Clipboard ─────────────────────────────────────────────────────────────

  function copyDatumToClipboard(datum, notesVal) {
    var lines = [];
    Object.keys(datum).forEach(function (k) {
      lines.push(k + ": " + formatValue(datum[k]));
    });
    if (notesVal) lines.push("notes: " + notesVal);
    var text = lines.join("\n");

    if (navigator.clipboard && navigator.clipboard.writeText) {
      navigator.clipboard
        .writeText(text)
        .then(function () {
          flashBtn("cab-copy-btn", "✅ Copied!");
          flashBtn("cab-float-copy-btn", "✅ Copied!");
        })
        .catch(function () {
          fallbackCopy(text);
        });
    } else {
      fallbackCopy(text);
    }
  }

  function copyToClipboard() {
    if (!currentDatum) return;
    // Try float notes first (desktop), fall back to inline notes (mobile)
    var floatNotes = document.getElementById("cab-float-notes");
    var inlineNotes = document.getElementById("cab-notes-input");
    var notesVal =
      (floatNotes && floatNotes.value) ||
      (inlineNotes && inlineNotes.value) ||
      "";
    copyDatumToClipboard(currentDatum, notesVal);
  }

  function fallbackCopy(text) {
    var ta = document.createElement("textarea");
    ta.value = text;
    ta.style.position = "fixed";
    ta.style.top = "-9999px";
    ta.style.left = "-9999px";
    document.body.appendChild(ta);
    ta.focus();
    ta.select();
    try {
      document.execCommand("copy");
      flashBtn("cab-copy-btn", "✅ Copied!");
      flashBtn("cab-float-copy-btn", "✅ Copied!");
    } catch (e) {
      alert("Copy failed. Please copy manually:\n\n" + text);
    }
    document.body.removeChild(ta);
  }

  function flashBtn(id, label) {
    var btn = document.getElementById(id);
    if (!btn) return;
    var orig = btn.textContent;
    btn.textContent = label;
    setTimeout(function () {
      btn.textContent = orig;
    }, 1500);
  }

  // ── View Wiring ───────────────────────────────────────────────────────────

  function wireView(view) {
    // ── Vega click handler ────────────────────────────────────────────────
    view.addEventListener("click", function (event, item) {
      if (!item || !item.datum) return;
      var datum = filterDatum(item.datum);
      if (Object.keys(datum).length === 0) return;

      var isCtrl = event.ctrlKey || event.metaKey;
      var isShift = event.shiftKey;

      if (isCtrl || isShift) {
        // Direct add to table (bypass pinned panel).
        // No page scroll — the tray flash is the feedback.
        rows.push(Object.assign({}, datum, { notes: "" }));
        renderTable();
        updateTrayCount();
        flashTray(isShift ? "✅ Added + copied!" : "✅ Added!");
        if (isShift) {
          copyDatumToClipboard(datum, "");
        }
      } else {
        // Normal: show in pinned panel
        currentDatum = datum;
        // Clear notes inputs
        var floatNotes = document.getElementById("cab-float-notes");
        var inlineNotes = document.getElementById("cab-notes-input");
        if (floatNotes) floatNotes.value = "";
        if (inlineNotes) inlineNotes.value = "";
        renderPinned(datum);
      }
    });

    // ── Float panel buttons ───────────────────────────────────────────────
    var floatAddBtn = document.getElementById("cab-float-add-btn");
    if (floatAddBtn) {
      floatAddBtn.addEventListener("click", function () {
        if (!currentDatum) return;
        var notesEl = document.getElementById("cab-float-notes");
        var notesVal = notesEl ? notesEl.value : "";
        rows.push(Object.assign({}, currentDatum, { notes: notesVal }));
        renderTable();
        updateTrayCount();
        flashTray("✅ Added!");
        var tbl = document.getElementById("cab-table");
        if (tbl) tbl.scrollIntoView({ behavior: "smooth", block: "nearest" });
      });
    }

    var floatCopyBtn = document.getElementById("cab-float-copy-btn");
    if (floatCopyBtn) {
      floatCopyBtn.addEventListener("click", copyToClipboard);
    }

    // ── Inline (mobile) panel buttons ─────────────────────────────────────
    var addBtn = document.getElementById("cab-add-btn");
    if (addBtn) {
      addBtn.addEventListener("click", function () {
        if (!currentDatum) return;
        var notesVal = document.getElementById("cab-notes-input").value;
        rows.push(Object.assign({}, currentDatum, { notes: notesVal }));
        renderTable();
        updateTrayCount();
        document
          .getElementById("cab-table")
          .scrollIntoView({ behavior: "smooth", block: "nearest" });
      });
    }

    var copyBtn = document.getElementById("cab-copy-btn");
    if (copyBtn) {
      copyBtn.addEventListener("click", copyToClipboard);
    }

    // ── Export / clear buttons ────────────────────────────────────────────
    var exportBtn = document.getElementById("cab-export-btn");
    if (exportBtn) exportBtn.addEventListener("click", exportCSV);

    var trayExportBtn = document.getElementById("cab-tray-export-btn");
    if (trayExportBtn) trayExportBtn.addEventListener("click", exportCSV);

    var clearBtn = document.getElementById("cab-clear-btn");
    if (clearBtn) {
      clearBtn.addEventListener("click", function () {
        rows.length = 0;
        currentDatum = null;
        // Hide float panel
        var fp = document.getElementById("cab-float-panel");
        if (fp) fp.style.display = "none";
        // Hide inline panel
        var ip = document.getElementById("cab-pinned");
        if (ip) ip.style.display = "none";
        // Clear notes
        var fn = document.getElementById("cab-float-notes");
        if (fn) fn.value = "";
        var inn = document.getElementById("cab-notes-input");
        if (inn) inn.value = "";
        renderTable();
        updateTrayCount();
        positionTray();
      });
    }

    // ── Collapse toggle ───────────────────────────────────────────────────
    setupCollapseToggle();

    // ── Reposition tray on scroll/resize ─────────────────────────────────
    window.addEventListener("scroll", positionTray, { passive: true });
    window.addEventListener("resize", positionTray, { passive: true });

    // Initial tray count
    updateTrayCount();
  }

  // ── DOMContentLoaded ──────────────────────────────────────────────────────

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", setupDOM);
  } else {
    // Already loaded (shouldn't happen when in <head>, but be safe)
    setupDOM();
  }

  // ── Public API ────────────────────────────────────────────────────────────

  /**
   * Attach the click-to-export UI to a Vega View instance.
   * Called from the patched vegaEmbed().then() chain.
   * Safe to call before DOMContentLoaded — the view will be queued.
   *
   * @param {Object} view - Vega View instance from vegaEmbed result
   */
  window.attachClickExport = function (view) {
    if (domReady) {
      wireView(view);
    } else {
      pendingViews.push(view);
    }
  };
})();
