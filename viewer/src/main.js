import * as THREE from "three";
import { OrbitControls } from "three/addons/controls/OrbitControls.js";
import {
  buildSceneFromExport,
  clearGroup,
  fitCameraToRoot,
  setCameraPreset,
} from "./scene.js";
import kidsRoomFixture from "../../tests/fixtures/reference_kids_room_export.json";
import kidsRoomFindings from "../../tests/fixtures/reference_kids_room_export_findings.json";

const el = {
  viewport: document.getElementById("viewport"),
  meta: document.getElementById("meta"),
  selection: document.getElementById("selection"),
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
  dropHint: document.getElementById("drop-hint"),
  viewControls: document.querySelector(".view-controls"),
};

const HIGHLIGHT = 0xffcc66;
const FINDING_ERROR = 0xe06c75;
const FINDING_WARN = 0xe5c07b;

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

const raycaster = new THREE.Raycaster();
const pointer = new THREE.Vector2();

let layers = { clearances: null, openings: null, solids: null };
let sceneRoot = null;
let lastFit = null;
let selected = null;
let findingMeshes = [];
let pointerDown = null;

function setStatus(msg, kind = "") {
  el.status.textContent = msg;
  el.status.classList.remove("ok", "error", "warn");
  if (kind) el.status.classList.add(kind);
}

function escapeHtml(s) {
  return String(s)
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;")
    .replaceAll('"', "&quot;");
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

function collectMeshes() {
  const list = [];
  if (!sceneRoot) return list;
  sceneRoot.traverse((obj) => {
    if (obj.isMesh || obj.isLineSegments) list.push(obj);
  });
  return list;
}

function setMeshHighlight(mesh, colorHex) {
  if (!mesh?.material) return;
  const mats = Array.isArray(mesh.material) ? mesh.material : [mesh.material];
  for (const m of mats) {
    if ("color" in m && m.color) {
      if (mesh.userData._savedColor == null) {
        mesh.userData._savedColor = m.color.getHex();
      }
      m.color.setHex(colorHex);
      if ("emissive" in m && m.emissive) {
        if (mesh.userData._savedEmissive == null) {
          mesh.userData._savedEmissive = m.emissive.getHex();
        }
        m.emissive.setHex(colorHex);
        m.emissiveIntensity = 0.25;
      }
    }
  }
}

function clearMeshHighlight(mesh) {
  if (!mesh?.material) return;
  const mats = Array.isArray(mesh.material) ? mesh.material : [mesh.material];
  for (const m of mats) {
    if ("color" in m && m.color && mesh.userData._savedColor != null) {
      m.color.setHex(mesh.userData._savedColor);
    }
    if ("emissive" in m && m.emissive && mesh.userData._savedEmissive != null) {
      m.emissive.setHex(mesh.userData._savedEmissive);
      m.emissiveIntensity = 0;
    }
  }
  delete mesh.userData._savedColor;
  delete mesh.userData._savedEmissive;
}

function clearSelection() {
  if (selected) clearMeshHighlight(selected);
  selected = null;
  el.selection.textContent = "Click an object in the viewport.";
  el.selection.className = "muted";
}

function clearFindingHighlights() {
  for (const mesh of findingMeshes) clearMeshHighlight(mesh);
  findingMeshes = [];
  for (const li of el.findings.querySelectorAll("li.active")) {
    li.classList.remove("active");
  }
}

function selectMesh(mesh) {
  clearFindingHighlights();
  if (selected && selected !== mesh) clearMeshHighlight(selected);
  selected = mesh;
  if (!mesh) {
    clearSelection();
    return;
  }
  setMeshHighlight(mesh, HIGHLIGHT);
  const ud = mesh.userData || {};
  const bits = [
    mesh.name || "object",
    ud.role ? `role ${ud.role}` : null,
    ud.clearance_name ? `clearance ${ud.clearance_name}` : null,
  ].filter(Boolean);
  el.selection.innerHTML = bits.map((b, i) => (i === 0 ? `<strong>${escapeHtml(b)}</strong>` : escapeHtml(b))).join("<br>");
  el.selection.className = "selection-info";
  setStatus(`Selected ${mesh.name}`, "ok");
}

function meshesForFinding(finding) {
  const meshes = collectMeshes();
  const clearanceName = finding?.clearance_ref?.clearance_name || "";
  const objectId = finding?.clearance_ref?.object_id || "";
  const overlapNames = new Set(
    (finding?.overlaps || [])
      .map((o) => o.name || o.object_name)
      .filter(Boolean),
  );
  return meshes.filter((m) => {
    const ud = m.userData || {};
    if (clearanceName && ud.clearance_name === clearanceName && (!objectId || ud.object_id === objectId)) {
      return true;
    }
    if (overlapNames.has(m.name)) return true;
    return false;
  });
}

function highlightFinding(finding, li) {
  clearSelection();
  clearFindingHighlights();
  if (li) li.classList.add("active");
  const color = finding.severity === "error" ? FINDING_ERROR : FINDING_WARN;
  findingMeshes = meshesForFinding(finding);
  for (const mesh of findingMeshes) setMeshHighlight(mesh, color);
  const n = findingMeshes.length;
  setStatus(
    n ? `Finding highlight · ${n} object${n === 1 ? "" : "s"}` : "Finding has no matching meshes",
    n ? (finding.severity === "error" ? "error" : "warn") : "warn",
  );
}

function renderAnalysis(data) {
  const analysis = data.analysis;
  el.findings.innerHTML = "";
  el.summary.innerHTML = "";

  if (!analysis) {
    el.summary.innerHTML = `<span class="chip">No analysis in export</span>`;
    return;
  }
  if (analysis.analyzed === false) {
    el.summary.innerHTML = `<span class="chip warn">Analysis failed</span>`;
    if (analysis.error) {
      el.findings.innerHTML = `<li class="muted" style="border:none;background:transparent;padding:0">${escapeHtml(analysis.error)}</li>`;
    }
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
    li.className = "finding clickable";
    li.tabIndex = 0;
    li.innerHTML = `
      <div class="sev ${escapeHtml(sev)}">${escapeHtml(sev)}</div>
      <div>${escapeHtml(f.message || f.constraint_type || "Finding")}</div>
      ${
        overlaps.length
          ? `<div class="muted" style="margin-top:0.3rem">vs ${escapeHtml(overlaps.join(", "))}</div>`
          : ""
      }
    `;
    const activate = () => highlightFinding(f, li);
    li.addEventListener("click", activate);
    li.addEventListener("keydown", (ev) => {
      if (ev.key === "Enter" || ev.key === " ") {
        ev.preventDefault();
        activate();
      }
    });
    el.findings.appendChild(li);
  }
}

function applyLayerVisibility() {
  if (layers.clearances) layers.clearances.visible = el.toggleClearances.checked;
  if (layers.openings) layers.openings.visible = el.toggleOpenings.checked;
}

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
      "This looks like commands JSON (Apply in Blender). Use Copy Scene Layout, then paste that here.",
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
  clearSelection();
  clearFindingHighlights();
  clearGroup(content);
  const built = buildSceneFromExport(data);
  content.add(built.root);
  sceneRoot = built.root;
  layers = built.layers;
  applyLayerVisibility();
  lastFit = fitCameraToRoot(camera, controls, built.root);
  renderMeta(data, sourceLabel);
  renderAnalysis(data);
  const n = (data.objects || []).length;
  const findings = data.analysis?.findings?.length ?? 0;
  el.objectCount.textContent = `${n} object${n === 1 ? "" : "s"}`;
  const findingNote = data.analysis?.analyzed ? ` · ${findings} finding${findings === 1 ? "" : "s"}` : "";
  setStatus(`Loaded ${sourceLabel} · ${n} objects${findingNote}`, "ok");
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
    setStatus(`Clipboard blocked (${err.message}). Paste into the dialog.`, "warn");
  }
}

function applyCamera(preset) {
  if (!sceneRoot || !lastFit) {
    setStatus("Load a scene first", "warn");
    return;
  }
  if (preset === "fit") {
    lastFit = fitCameraToRoot(camera, controls, sceneRoot);
    setStatus("Camera fit", "ok");
    return;
  }
  setCameraPreset(camera, controls, lastFit, preset);
  setStatus(`Camera ${preset}`, "ok");
}

function pickObject(clientX, clientY) {
  const rect = renderer.domElement.getBoundingClientRect();
  pointer.x = ((clientX - rect.left) / rect.width) * 2 - 1;
  pointer.y = -((clientY - rect.top) / rect.height) * 2 + 1;
  raycaster.setFromCamera(pointer, camera);
  const hits = raycaster.intersectObjects(collectMeshes(), false);
  return hits[0]?.object || null;
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
  pasteFromClipboard().catch((err) => setStatus(`Error: ${err.message}`, "error"));
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
    setStatus(`Error: ${err.message}`, "error");
  }
});

el.btnFixture.addEventListener("click", () => {
  loadFixture().catch((err) => setStatus(`Error: ${err.message}`, "error"));
});

el.btnFindings.addEventListener("click", () => {
  loadFindingsFixture().catch((err) => setStatus(`Error: ${err.message}`, "error"));
});

el.fileInput.addEventListener("change", () => {
  const file = el.fileInput.files?.[0];
  if (!file) return;
  loadFile(file).catch((err) => setStatus(`Error: ${err.message}`, "error"));
  el.fileInput.value = "";
});

el.toggleClearances.addEventListener("change", applyLayerVisibility);
el.toggleOpenings.addEventListener("change", applyLayerVisibility);

el.viewControls?.addEventListener("click", (ev) => {
  const btn = ev.target.closest("button[data-cam]");
  if (!btn) return;
  applyCamera(btn.dataset.cam);
});

renderer.domElement.addEventListener("pointerdown", (ev) => {
  if (ev.button !== 0) return;
  pointerDown = { x: ev.clientX, y: ev.clientY };
});

renderer.domElement.addEventListener("pointerup", (ev) => {
  if (ev.button !== 0 || !pointerDown) return;
  const dx = ev.clientX - pointerDown.x;
  const dy = ev.clientY - pointerDown.y;
  pointerDown = null;
  if (dx * dx + dy * dy > 16) return; // drag = orbit, not click
  const hit = pickObject(ev.clientX, ev.clientY);
  if (hit) selectMesh(hit);
  else {
    clearSelection();
    clearFindingHighlights();
    setStatus("Selection cleared");
  }
});

// Drag & drop export JSON
["dragenter", "dragover"].forEach((type) => {
  el.viewport.addEventListener(type, (ev) => {
    ev.preventDefault();
    el.dropHint.hidden = false;
    el.viewport.classList.add("drag-over");
  });
});
["dragleave", "drop"].forEach((type) => {
  el.viewport.addEventListener(type, (ev) => {
    ev.preventDefault();
    if (type === "dragleave" && ev.target !== el.viewport) return;
    el.dropHint.hidden = true;
    el.viewport.classList.remove("drag-over");
  });
});
el.viewport.addEventListener("drop", (ev) => {
  ev.preventDefault();
  el.dropHint.hidden = true;
  el.viewport.classList.remove("drag-over");
  const file = ev.dataTransfer?.files?.[0];
  if (file) {
    loadFile(file).catch((err) => setStatus(`Error: ${err.message}`, "error"));
    return;
  }
  const text = ev.dataTransfer?.getData("text");
  if (text?.trim()) {
    try {
      loadFromPasteText(text, "dropped text");
    } catch (err) {
      setStatus(`Error: ${err.message}`, "error");
    }
  }
});

window.addEventListener("paste", (ev) => {
  const tag = (ev.target && ev.target.tagName) || "";
  if (tag === "TEXTAREA" || tag === "INPUT") return;
  const text = ev.clipboardData?.getData("text");
  if (!text || !text.trim()) return;
  ev.preventDefault();
  try {
    loadFromPasteText(text, "clipboard paste");
  } catch (err) {
    setStatus(`Error: ${err.message}`, "error");
  }
});

window.addEventListener("keydown", (ev) => {
  const tag = (ev.target && ev.target.tagName) || "";
  if (tag === "TEXTAREA" || tag === "INPUT") return;
  if (ev.key === "f" || ev.key === "F") {
    ev.preventDefault();
    applyCamera("fit");
  } else if (ev.key === "1") applyCamera("iso");
  else if (ev.key === "2") applyCamera("top");
  else if (ev.key === "3") applyCamera("front");
  else if (ev.key === "4") applyCamera("side");
  else if (ev.key === "Escape") {
    clearSelection();
    clearFindingHighlights();
    setStatus("Selection cleared");
  }
});

window.addEventListener("resize", resize);
resize();
frame();

loadFixture().catch((err) => setStatus(`Error: ${err.message}`, "error"));
