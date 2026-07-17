import * as THREE from "three";
import { OrbitControls } from "three/addons/controls/OrbitControls.js";
import { buildSceneFromExport, clearGroup, fitCameraToRoot } from "./scene.js";
import kidsRoomFixture from "../../tests/fixtures/reference_kids_room_export.json";
import kidsRoomFindings from "../../tests/fixtures/reference_kids_room_export_findings.json";

const el = {
  viewport: document.getElementById("viewport"),
  meta: document.getElementById("meta"),
  summary: document.getElementById("summary"),
  findings: document.getElementById("findings"),
  objectCount: document.getElementById("object-count"),
  status: document.getElementById("status"),
  fileInput: document.getElementById("file-input"),
  btnPaste: document.getElementById("btn-paste"),
  btnFixture: document.getElementById("btn-fixture"),
  btnFindings: document.getElementById("btn-findings"),
  pasteDialog: document.getElementById("paste-dialog"),
  pasteForm: document.getElementById("paste-form"),
  pasteText: document.getElementById("paste-text"),
  toggleClearances: document.getElementById("toggle-clearances"),
  toggleOpenings: document.getElementById("toggle-openings"),
};

const renderer = new THREE.WebGLRenderer({ antialias: true, alpha: true });
renderer.setPixelRatio(Math.min(window.devicePixelRatio, 2));
renderer.setClearColor(0x000000, 0);
el.viewport.appendChild(renderer.domElement);

const scene = new THREE.Scene();
const camera = new THREE.PerspectiveCamera(50, 1, 0.05, 200);
const controls = new OrbitControls(camera, renderer.domElement);
controls.enableDamping = true;
controls.dampingFactor = 0.08;

const hemi = new THREE.HemisphereLight(0xdde6f2, 0x2a3038, 0.85);
scene.add(hemi);
const key = new THREE.DirectionalLight(0xffffff, 0.75);
key.position.set(4, 8, 3);
scene.add(key);

const content = new THREE.Group();
content.name = "content";
scene.add(content);

let layers = { clearances: null, openings: null };

function setStatus(msg) {
  el.status.textContent = msg;
}

function renderMeta(data, sourceLabel) {
  const rooms = data.rooms || [];
  const roomName = rooms[0]?.name || "—";
  const rows = [
    ["Source", sourceLabel],
    ["Scene", data.scene || "—"],
    ["Version", data.layoutlab_version || "—"],
    ["Viewer schema", data.viewer_schema || "—"],
    ["Unit", `${data.unit || "?"} · scale ${data.unit_scale ?? "?"}`],
    ["Room", roomName],
  ];
  el.meta.innerHTML = rows
    .map(([k, v]) => `<dt>${escapeHtml(k)}</dt><dd>${escapeHtml(String(v))}</dd>`)
    .join("");
}

function renderAnalysis(data) {
  const analysis = data.analysis;
  el.findings.innerHTML = "";
  el.summary.innerHTML = "";

  if (!analysis || analysis.analyzed === false) {
    el.summary.innerHTML = `<span class="chip">No analysis in export</span>`;
    return;
  }

  const s = analysis.summary || {};
  const errors = s.errors ?? 0;
  const warnings = s.warnings ?? 0;
  const info = s.info ?? 0;
  const chips = [];
  if (errors === 0 && warnings === 0 && info === 0) {
    chips.push(`<span class="chip ok">Clean · 0 findings</span>`);
  } else {
    if (errors) chips.push(`<span class="chip error">${errors} errors</span>`);
    if (warnings) chips.push(`<span class="chip warning">${warnings} warnings</span>`);
    if (info) chips.push(`<span class="chip info">${info} info</span>`);
  }
  el.summary.innerHTML = chips.join("");

  const findings = analysis.findings || [];
  if (!findings.length) {
    el.findings.innerHTML = `<li class="muted" style="border:none;background:transparent;padding:0">No violations reported.</li>`;
    return;
  }

  for (const f of findings) {
    const sev = f.severity || "warning";
    const overlaps = (f.overlaps || [])
      .map((o) => o.name || o.object_name || o.role || o.object_id)
      .filter(Boolean);
    const li = document.createElement("li");
    li.innerHTML = `
      <div class="sev ${escapeHtml(sev)}">${escapeHtml(sev)}</div>
      <div>${escapeHtml(f.message || f.constraint_type || "Finding")}</div>
      ${
        overlaps.length
          ? `<div class="muted" style="margin-top:0.3rem">vs ${escapeHtml(overlaps.join(", "))}</div>`
          : ""
      }
    `;
    el.findings.appendChild(li);
  }
}

function escapeHtml(s) {
  return String(s)
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;")
    .replaceAll('"', "&quot;");
}

function applyLayerVisibility() {
  if (layers.clearances) layers.clearances.visible = el.toggleClearances.checked;
  if (layers.openings) layers.openings.visible = el.toggleOpenings.checked;
}

/**
 * Accept Blender clipboard JSON: scene export object.
 * Commands payloads are rejected with a clear error.
 */
function parseExportText(text) {
  const trimmed = String(text || "").trim();
  if (!trimmed) throw new Error("Clipboard / paste is empty");
  let data;
  try {
    data = JSON.parse(trimmed);
  } catch (err) {
    throw new Error(`Not valid JSON (${err.message})`);
  }
  if (Array.isArray(data)) {
    throw new Error("Expected a scene export object, got a JSON array");
  }
  if (!data || typeof data !== "object") {
    throw new Error("Expected a scene export object");
  }
  if (Array.isArray(data.commands) && !Array.isArray(data.objects)) {
    throw new Error(
      "This looks like a commands payload (Apply in Blender). Export the scene first, then paste that JSON here.",
    );
  }
  if (!Array.isArray(data.objects) && !Array.isArray(data.rooms)) {
    throw new Error("Export must include objects[] and/or rooms[]");
  }
  if (!Array.isArray(data.objects)) data.objects = [];
  return data;
}

function loadExportData(data, sourceLabel) {
  if (!data || typeof data !== "object") throw new Error("Invalid export JSON");
  clearGroup(content);
  const built = buildSceneFromExport(data);
  content.add(built.root);
  layers = built.layers;
  applyLayerVisibility();
  fitCameraToRoot(camera, controls, built.root);
  renderMeta(data, sourceLabel);
  renderAnalysis(data);
  const n = (data.objects || []).length;
  el.objectCount.textContent = `${n} exported object${n === 1 ? "" : "s"}`;
  setStatus(`Loaded ${sourceLabel} · ${n} objects`);
}

function loadFromPasteText(text, sourceLabel = "clipboard paste") {
  const data = parseExportText(text);
  loadExportData(data, sourceLabel);
}

async function loadFixture() {
  setStatus("Loading kids-room fixture…");
  loadExportData(kidsRoomFixture, "reference_kids_room_export.json");
}

async function loadFindingsFixture() {
  setStatus("Loading findings demo…");
  loadExportData(kidsRoomFindings, "reference_kids_room_export_findings.json");
}

async function loadFile(file) {
  const text = await file.text();
  loadFromPasteText(text, file.name);
}

function openPasteDialog(prefill = "") {
  el.pasteText.value = prefill;
  el.pasteDialog.showModal();
  el.pasteText.focus();
  el.pasteText.select();
}

async function pasteFromClipboard() {
  setStatus("Reading clipboard…");
  try {
    const text = await navigator.clipboard.readText();
    loadFromPasteText(text, "clipboard");
  } catch (err) {
    openPasteDialog();
    setStatus(`Clipboard blocked (${err.message}). Paste into the dialog.`);
  }
}

function resize() {
  const w = el.viewport.clientWidth;
  const h = el.viewport.clientHeight;
  if (w < 1 || h < 1) return;
  camera.aspect = w / h;
  camera.updateProjectionMatrix();
  renderer.setSize(w, h, false);
}

function frame() {
  controls.update();
  renderer.render(scene, camera);
  requestAnimationFrame(frame);
}

el.btnPaste.addEventListener("click", () => {
  pasteFromClipboard().catch((err) => setStatus(`Error: ${err.message}`));
});

el.pasteForm.addEventListener("submit", (ev) => {
  const submitter = ev.submitter;
  const value = submitter?.value || "cancel";
  if (value !== "load") return;
  ev.preventDefault();
  try {
    loadFromPasteText(el.pasteText.value, "pasted JSON");
    el.pasteDialog.close();
    el.pasteText.value = "";
  } catch (err) {
    setStatus(`Error: ${err.message}`);
  }
});

el.btnFixture.addEventListener("click", () => {
  loadFixture().catch((err) => setStatus(`Error: ${err.message}`));
});

el.btnFindings.addEventListener("click", () => {
  loadFindingsFixture().catch((err) => setStatus(`Error: ${err.message}`));
});

el.fileInput.addEventListener("change", () => {
  const file = el.fileInput.files?.[0];
  if (!file) return;
  loadFile(file).catch((err) => setStatus(`Error: ${err.message}`));
  el.fileInput.value = "";
});

el.toggleClearances.addEventListener("change", applyLayerVisibility);
el.toggleOpenings.addEventListener("change", applyLayerVisibility);

// Global paste when not typing in an input: Blender clipboard → load immediately
window.addEventListener("paste", (ev) => {
  const tag = (ev.target && ev.target.tagName) || "";
  if (tag === "TEXTAREA" || tag === "INPUT") return;
  const text = ev.clipboardData?.getData("text");
  if (!text || !text.trim()) return;
  ev.preventDefault();
  try {
    loadFromPasteText(text, "clipboard paste");
  } catch (err) {
    setStatus(`Error: ${err.message}`);
  }
});

window.addEventListener("resize", resize);
resize();
frame();

loadFixture().catch((err) => setStatus(`Error: ${err.message}`));
