import * as THREE from "three";
import { OrbitControls } from "three/addons/controls/OrbitControls.js";
import {
  buildSceneFromExport,
  clearGroup,
  computeFit,
  fitCameraToRoot,
  getFitViewPose,
  getPresetPose,
} from "./scene.js";
import { renderFloorplanSvg } from "./floorplan.js";
import {
  buildSelectionGizmos,
  furnitureBounds,
  isGizmoMesh,
  resizeParamsForAxis,
  roomMoveCommand,
  resizeCommand,
} from "./gizmos.js";
import {
  createPreviewClient,
  findMeshForObjectId,
  hitBlenderFloorXY,
  isFurnitureMesh,
  isWallMesh,
  moveCommand,
  MOVE_THROTTLE_MS,
  poseFromExport,
  rotateCommand,
  ROTATE_DEG_PER_PX,
  wallDeltaFromDrag,
  wallMoveCommand,
  cornerMoveCommand,
} from "./manipulate.js";
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
  btnCoreEmpty: document.getElementById("btn-core-empty"),
  btnCoreFurnished: document.getElementById("btn-core-furnished"),
  btnCoreMultiroom: document.getElementById("btn-core-multiroom"),
  btnCoreCommands: document.getElementById("btn-core-commands"),
  coreUrl: document.getElementById("core-url"),
  coreVersion: document.getElementById("core-version"),
  pasteDialog: document.getElementById("paste-dialog"),
  pasteForm: document.getElementById("paste-form"),
  pasteText: document.getElementById("paste-text"),
  commandsDialog: document.getElementById("commands-dialog"),
  commandsForm: document.getElementById("commands-form"),
  commandsText: document.getElementById("commands-text"),
  toggleClearances: document.getElementById("toggle-clearances"),
  toggleOpenings: document.getElementById("toggle-openings"),
  dropHint: document.getElementById("drop-hint"),
  viewControls: document.querySelector(".view-controls"),
  chatLog: document.getElementById("chat-log"),
  chatForm: document.getElementById("chat-form"),
  chatInput: document.getElementById("chat-input"),
  chatProposalBar: document.getElementById("chat-proposal-bar"),
  chatProposalMeta: document.getElementById("chat-proposal-meta"),
  chatShortlist: document.getElementById("chat-shortlist"),
  btnChatApply: document.getElementById("btn-chat-apply"),
  btnChatView: document.getElementById("btn-chat-view"),
  btnChatDiscard: document.getElementById("btn-chat-discard"),
  commandsViewDialog: document.getElementById("commands-view-dialog"),
  commandsViewMeta: document.getElementById("commands-view-meta"),
  commandsViewJson: document.getElementById("commands-view-json"),
  btnCommandsViewApply: document.getElementById("btn-commands-view-apply"),
  llmApiKey: document.getElementById("llm-api-key"),
  llmModel: document.getElementById("llm-model"),
  llmBaseUrl: document.getElementById("llm-base-url"),
  btnLlmClear: document.getElementById("btn-llm-clear"),
  btnSettings: document.getElementById("btn-settings"),
  settingsPopover: document.getElementById("settings-popover"),
  inspector: document.getElementById("inspector"),
  btnInspectorToggle: document.getElementById("btn-inspector-toggle"),
  roomList: document.getElementById("room-list"),
  roomFloorplan: document.getElementById("room-floorplan"),
  btnUndo: document.getElementById("btn-undo"),
  btnRedo: document.getElementById("btn-redo"),
};

/** Same shell as layoutlab/plugin/test_rooms.py empty_test_room_commands(). */
const EMPTY_TEST_ROOM_COMMANDS = {
  commands: [
    { action: "delete_collection_objects", collection: "layoutlab_room" },
    {
      action: "create_room",
      params: {
        name: "KIDS_ROOM",
        location: [0, 0, 0],
        width: 4.2,
        depth: 2.18,
        height: 2.6,
        wall_thickness: 0.02,
        collection: "layoutlab_room",
      },
    },
    {
      action: "add_opening",
      params: {
        room: "KIDS_ROOM",
        opening_name: "window_west",
        kind: "window",
        wall_side: "west",
        offset: 0.48054,
        width: 1.22946,
        height: 1.47,
        sill_height: 0.88,
      },
    },
    {
      action: "add_opening",
      params: {
        room: "KIDS_ROOM",
        opening_name: "door_east",
        kind: "door",
        wall_side: "east",
        offset: 0.24866,
        width: 0.70801,
        height: 1.84453,
      },
    },
    {
      action: "add_fixed_element",
      params: {
        room: "KIDS_ROOM",
        fixed_name: "heizung",
        kind: "radiator",
        wall_side: "west",
        offset: 0.56494,
        width: 1.1,
        depth: 0.1,
        height: 0.75,
      },
    },
  ],
};

/** Same as layoutlab/plugin/test_rooms.py furnished_test_room_commands(). */
const FURNISHED_TEST_ROOM_COMMANDS = {
  commands: [
    ...EMPTY_TEST_ROOM_COMMANDS.commands,
    {
      action: "run_generator",
      generator: "bed_basic",
      params: {
        name: "BED_120x200",
        location: [0.15, 0.09, 0],
        length: 1.2,
        width: 2.0,
        head_side: "y_max",
        clearances: [
          {
            clearance_name: "bed_entry",
            side: "right",
            depth: 0.5,
            requirement: "preferred",
          },
        ],
        collection: "layoutlab_room",
      },
    },
    {
      action: "run_generator",
      generator: "desk_basic",
      params: {
        name: "DESK_120x60",
        location: [2.7, 1.58, 0],
        width: 1.2,
        depth: 0.6,
        height: 0.75,
        show_clearance: true,
        collection: "layoutlab_room",
      },
    },
  ],
};

/** Two independent rooms for Spatial Project / room-selection UX. */
const MULTI_ROOM_DEMO_COMMANDS = {
  commands: [
    { action: "delete_collection_objects", collection: "layoutlab_room" },
    {
      action: "create_room",
      params: {
        name: "KIDS_ROOM",
        location: [0, 0, 0],
        width: 4.2,
        depth: 2.18,
        height: 2.6,
        wall_thickness: 0.02,
        collection: "layoutlab_room",
      },
    },
    {
      action: "add_opening",
      params: {
        room: "KIDS_ROOM",
        opening_name: "door_east",
        kind: "door",
        wall_side: "east",
        offset: 0.25,
        width: 0.7,
        height: 1.84,
      },
    },
    {
      action: "create_room",
      params: {
        name: "STUDY",
        location: [6, 0, 0],
        width: 3.2,
        depth: 2.8,
        height: 2.6,
        wall_thickness: 0.02,
        collection: "layoutlab_room",
      },
    },
    {
      action: "add_opening",
      params: {
        room: "STUDY",
        opening_name: "window_north",
        kind: "window",
        wall_side: "north",
        offset: 0.6,
        width: 1.4,
        height: 1.2,
        sill_height: 0.9,
      },
    },
    {
      action: "run_generator",
      generator: "desk_basic",
      params: {
        name: "DESK_STUDY",
        location: [6.3, 1.8, 0],
        width: 1.2,
        depth: 0.6,
        height: 0.75,
        show_clearance: true,
        collection: "layoutlab_room",
      },
    },
  ],
};

const CORE_URL_KEY = "layoutlab_core_url";
const LLM_SETTINGS_KEY = "layoutlab_llm_settings";

function getCoreUrl() {
  const fromInput = (el.coreUrl?.value || "").trim().replace(/\/$/, "");
  if (fromInput) return fromInput;
  return "http://127.0.0.1:8765";
}

function loadStoredCoreUrl() {
  if (!el.coreUrl) return;
  try {
    const stored = localStorage.getItem(CORE_URL_KEY);
    if (stored) el.coreUrl.value = stored;
  } catch {
    /* ignore */
  }
}

function persistCoreUrl() {
  if (!el.coreUrl) return;
  try {
    localStorage.setItem(CORE_URL_KEY, getCoreUrl());
  } catch {
    /* ignore */
  }
}

function setCoreVersionDisplay(version, { offline = false } = {}) {
  if (!el.coreVersion) return;
  if (offline) {
    el.coreVersion.textContent = "offline";
    el.coreVersion.classList.add("offline");
    el.coreVersion.title = "Core nicht erreichbar";
    return;
  }
  el.coreVersion.classList.remove("offline");
  el.coreVersion.textContent = version ? `v${version}` : "…";
  el.coreVersion.title = version ? `LayoutLab Core ${version}` : "Core version";
}

async function refreshCoreVersion() {
  const base = getCoreUrl();
  try {
    const response = await fetch(`${base}/health`);
    if (!response.ok) {
      setCoreVersionDisplay(null, { offline: true });
      return null;
    }
    const data = await response.json();
    const ver = data.core_version || null;
    setCoreVersionDisplay(ver);
    return ver;
  } catch {
    setCoreVersionDisplay(null, { offline: true });
    return null;
  }
}

/** Archive Core session log + clear Core scene on full page load / tab refresh. */
async function resetCoreSessionOnLoad() {
  const base = getCoreUrl();
  persistCoreUrl();
  try {
    const response = await fetch(`${base}/v1/session/reset`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ reason: "viewer_reload", clear_scene: true }),
    });
    if (!response.ok) {
      await refreshCoreVersion();
      return;
    }
    const data = await response.json();
    const ver = data.core_version || "?";
    setCoreVersionDisplay(ver === "?" ? null : ver);
    setStatus(`Core ${ver} · session reset (${data.session_id || "ok"})`);
  } catch {
    setCoreVersionDisplay(null, { offline: true });
    /* Core offline — ignore; chat/commands will surface the error later */
  }
}

function loadLlmSettings() {
  let stored = {};
  try {
    stored = JSON.parse(localStorage.getItem(LLM_SETTINGS_KEY) || "{}") || {};
  } catch {
    stored = {};
  }
  if (el.llmApiKey && stored.api_key) el.llmApiKey.value = stored.api_key;
  if (el.llmModel) el.llmModel.value = stored.model || el.llmModel.value || "gpt-4o-mini";
  if (el.llmBaseUrl) {
    el.llmBaseUrl.value = stored.base_url || el.llmBaseUrl.value || "https://api.openai.com/v1";
  }
}

function persistLlmSettings() {
  const payload = {
    api_key: (el.llmApiKey?.value || "").trim(),
    model: (el.llmModel?.value || "").trim() || "gpt-4o-mini",
    base_url: (el.llmBaseUrl?.value || "").trim() || "https://api.openai.com/v1",
  };
  try {
    localStorage.setItem(LLM_SETTINGS_KEY, JSON.stringify(payload));
  } catch {
    /* ignore */
  }
  return payload;
}

function getLlmConfigForRequest() {
  const settings = persistLlmSettings();
  if (!settings.api_key) return null;
  return {
    api_key: settings.api_key,
    model: settings.model,
    base_url: settings.base_url,
  };
}

async function postCommandsToCore(commandsPayload, sourceLabel) {
  const base = getCoreUrl();
  persistCoreUrl();
  setStatus(`Sending commands to Core (${base})…`);
  let response;
  try {
    response = await fetch(`${base}/v1/commands`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(
        Array.isArray(commandsPayload) ? { commands: commandsPayload } : commandsPayload,
      ),
    });
  } catch (err) {
    throw new Error(
      `Core unreachable at ${base} (${err.message}). Start with: python -m server`,
    );
  }
  let payload;
  try {
    payload = await response.json();
  } catch {
    throw new Error(`Core returned non-JSON (HTTP ${response.status})`);
  }
  if (!payload.export) {
    const detail = payload.error || payload.errors?.[0]?.error || `HTTP ${response.status}`;
    throw new Error(`Core error: ${detail}`);
  }
  if (!payload.ok) {
    const detail = payload.errors?.[0]?.error || "command failed";
    setStatus(`Core reported errors: ${detail}`, "warn");
  }
  liveCoreSession = true;
  loadExportData(payload.export, sourceLabel);
}

async function postCoreJson(path, body = {}) {
  const base = getCoreUrl();
  persistCoreUrl();
  let response;
  try {
    response = await fetch(`${base}${path}`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(body || {}),
    });
  } catch (err) {
    throw new Error(
      `Core unreachable at ${base} (${err.message}). Start with: python -m server`,
    );
  }
  let payload;
  try {
    payload = await response.json();
  } catch {
    throw new Error(`Core returned non-JSON (HTTP ${response.status})`);
  }
  return payload;
}

const previewClient = createPreviewClient({ post: postCoreJson });

let lastExportData = null;
let liveCoreSession = false;
/** @type {{ type: 'furniture'|'room', objectId?: string, roomId?: string } | null} */
let selectionTarget = null;
let gesture = null; // active drag gesture
let lastPreviewPush = 0;
let gizmoGroup = null;
let pendingChatCommands = null;
let pendingChatQuality = null;
let pendingChatProposalPayload = null;
let pendingShortlist = null;
let pendingSelectedId = null;

function sceneSummaryForChat() {
  const data = lastExportData;
  if (!data) return null;
  const analysis = data.analysis || {};
  return {
    rooms: (data.rooms || []).map((r) => ({
      name: r.name,
      width: r.footprint?.width,
      depth: r.footprint?.depth,
      height: r.height,
    })),
    object_count: (data.objects || []).length,
    object_names: (data.objects || []).slice(0, 40).map((o) => o.name),
    analysis_summary: analysis.summary || null,
    findings_count: (analysis.findings || []).length,
  };
}

function appendChatBubble(role, text) {
  if (!el.chatLog) return;
  const div = document.createElement("div");
  div.className = `chat-bubble ${role}`;
  div.textContent = text;
  el.chatLog.appendChild(div);
  el.chatLog.scrollTop = el.chatLog.scrollHeight;
}

function clearChatProposal() {
  pendingChatCommands = null;
  pendingChatQuality = null;
  pendingChatProposalPayload = null;
  pendingShortlist = null;
  pendingSelectedId = null;
  if (el.chatProposalBar) el.chatProposalBar.hidden = true;
  if (el.chatProposalMeta) el.chatProposalMeta.textContent = "";
  if (el.chatShortlist) {
    el.chatShortlist.hidden = true;
    el.chatShortlist.innerHTML = "";
  }
  if (el.commandsViewDialog?.open) el.commandsViewDialog.close();
}

function proposalMetaText(payload, commands) {
  const mode = payload.mode || "plan";
  const tools = (payload.tool_trace || []).length;
  const title = payload.proposal?.title ? ` · ${payload.proposal.title}` : "";
  const risks = payload.proposal?.expected_risks || [];
  const q = payload.quality || {};
  const selected =
    payload.selected_id || payload.planning?.selected_id || pendingSelectedId || "";
  let qualityHint = "";
  if (
    q.needs_user_confirm ||
    risks.length ||
    q.has_hard_errors ||
    q.has_soft_warnings ||
    q.has_solid_collisions
  ) {
    const bits = [];
    if (q.has_solid_collisions) bits.push("WALL HIT");
    if (q.has_hard_errors) bits.push("hard errors");
    if (q.has_soft_warnings) bits.push("soft warnings");
    if (risks.length) bits.push(`${risks.length} risk(s)`);
    qualityHint = ` · ⚠ ${bits.join(", ") || "review"}`;
  }
  const selectedLabel =
    payload.planning?.selected_label_de ||
    pendingShortlist?.find((c) => c.candidate_id === selected)?.label_de ||
    selected;
  const selHint = selectedLabel ? ` · ${selectedLabel}` : "";
  return `${commands.length} command${commands.length === 1 ? "" : "s"}${title}${selHint} · mode=${mode}${tools ? ` · ${tools} tools` : ""}${qualityHint}`;
}

function renderShortlistButtons() {
  if (!el.chatShortlist) return;
  const items = Array.isArray(pendingShortlist) ? pendingShortlist : [];
  el.chatShortlist.innerHTML = "";
  if (items.length < 2) {
    el.chatShortlist.hidden = true;
    return;
  }
  el.chatShortlist.hidden = false;
  items.forEach((item, idx) => {
    const btn = document.createElement("button");
    btn.type = "button";
    btn.className = "chat-shortlist-card";
    const id = item.candidate_id || `option-${idx + 1}`;
    if (id === pendingSelectedId) btn.classList.add("is-selected");
    const label = item.label_de || item.strategy || id;
    const soft = item.quality?.soft_warnings;
    const title = document.createElement("p");
    title.className = "chat-shortlist-card-title";
    title.textContent = `${idx + 1}. ${label}`;
    btn.appendChild(title);
    const meta = document.createElement("p");
    meta.className = "chat-shortlist-card-meta";
    const bits = [];
    if (item.recommended || id === pendingSelectedId) bits.push("Vorschlag");
    if (item.aesthetic_recommended) bits.push("Ästhetik");
    if (soft != null) bits.push(soft === 0 ? "keine Soft-Warnungen" : `${soft} Soft`);
    meta.textContent = bits.join(" · ") || "Shortlist";
    btn.appendChild(meta);
    if (item.viewer_preview) {
      const plan = renderFloorplanSvg(item.viewer_preview);
      if (plan) btn.appendChild(plan);
      else if (item.sketch_ascii) {
        const pre = document.createElement("pre");
        pre.className = "chat-shortlist-card-sketch";
        pre.textContent = item.sketch_ascii;
        btn.appendChild(pre);
      }
    } else if (item.sketch_ascii) {
      const pre = document.createElement("pre");
      pre.className = "chat-shortlist-card-sketch";
      pre.textContent = item.sketch_ascii;
      btn.appendChild(pre);
    }
    btn.title = id;
    btn.addEventListener("click", () => selectShortlistCandidate(id));
    el.chatShortlist.appendChild(btn);
  });
}

function selectShortlistCandidate(candidateId) {
  const items = Array.isArray(pendingShortlist) ? pendingShortlist : [];
  const chosen = items.find((c) => c.candidate_id === candidateId);
  if (!chosen?.commands?.length) {
    setStatus(`Shortlist-Variante nicht gefunden: ${candidateId}`, "warn");
    return;
  }
  pendingSelectedId = candidateId;
  pendingChatCommands = chosen.commands;
  if (chosen.quality) pendingChatQuality = chosen.quality;
  const label = chosen.label_de || chosen.strategy || candidateId;
  if (pendingChatProposalPayload) {
    pendingChatProposalPayload = {
      ...pendingChatProposalPayload,
      selected_id: candidateId,
      commands: chosen.commands,
      proposal: {
        ...(pendingChatProposalPayload.proposal || {}),
        commands: chosen.commands,
        title: label,
      },
      quality: chosen.quality || pendingChatProposalPayload.quality,
      planning: {
        ...(pendingChatProposalPayload.planning || {}),
        selected_id: candidateId,
        selected_label_de: label,
        selection_reason: `Nutzerwahl: ${label}`,
      },
      shortlist: items.map((c) => ({
        ...c,
        recommended: c.candidate_id === candidateId,
      })),
    };
  }
  if (el.chatProposalMeta) {
    el.chatProposalMeta.textContent = `${proposalMetaText(
      pendingChatProposalPayload || {},
      pendingChatCommands,
    )} — bereit zum Apply`;
  }
  renderShortlistButtons();
  setStatus(`Variante gewählt: ${label} — Apply zum Ausführen`, "ok");
}

function showChatProposal(payload) {
  const commands = payload.proposal?.commands || payload.commands || [];
  pendingChatCommands = commands;
  pendingChatQuality = payload.quality || null;
  pendingChatProposalPayload = payload;
  pendingShortlist = Array.isArray(payload.shortlist) ? payload.shortlist : null;
  pendingSelectedId =
    payload.selected_id ||
    payload.planning?.selected_id ||
    pendingShortlist?.find((c) => c.recommended)?.candidate_id ||
    pendingShortlist?.[0]?.candidate_id ||
    null;
  if (!el.chatProposalBar) return;
  el.chatProposalBar.hidden = false;
  if (el.chatProposalMeta) {
    el.chatProposalMeta.textContent = `${proposalMetaText(payload, commands)} — bereit zum Apply`;
  }
  renderShortlistButtons();
}

function openCommandsView() {
  if (!pendingChatCommands?.length || !el.commandsViewDialog) {
    setStatus("No commands to view", "warn");
    return;
  }
  const payload = pendingChatProposalPayload || {};
  if (el.commandsViewMeta) {
    el.commandsViewMeta.textContent = proposalMetaText(payload, pendingChatCommands);
  }
  if (el.commandsViewJson) {
    el.commandsViewJson.textContent = JSON.stringify(
      {
        questions: payload.questions || [],
        proposal: payload.proposal || { commands: pendingChatCommands },
        quality: payload.quality || undefined,
      },
      null,
      2,
    );
  }
  el.commandsViewDialog.showModal();
}

function applyPendingChatCommands() {
  if (!pendingChatCommands?.length) {
    setStatus("No commands to apply", "warn");
    return;
  }
  const q = pendingChatQuality || {};
  if (q.blocks_apply || q.has_solid_collisions) {
    const msgs = (q.solid_messages || []).slice(0, 3).join("\n") || "Möbel durchdringt Wand.";
    window.alert(
      `Apply blockiert — physikalisch ungültig (kein Kompromiss):\n\n${msgs}\n\nBitte neu planen.`,
    );
    setStatus("Apply blockiert: Wand-Durchdringung", "error");
    return;
  }
  if (q.needs_user_confirm || q.has_hard_errors || q.has_soft_warnings || q.has_expected_risks) {
    const parts = [];
    if (q.has_hard_errors) parts.push("harte Clearance-Fehler");
    if (q.has_soft_warnings) parts.push("Soft-Warnungen (Packung/Öffnungen)");
    if (q.has_expected_risks) parts.push("dokumentierte Kompromisse");
    const detail = parts.length ? parts.join(", ") : "Qualitäts-Hinweise";
    const ok = window.confirm(
      `Apply trotz ${detail}?\n\nLayoutLab führt die Commands aus; Apply gilt als Zustimmung zum Kompromiss.`,
    );
    if (!ok) {
      setStatus("Apply abgebrochen — Proposal unverändert", "warn");
      return;
    }
  }
  const commands = pendingChatCommands;
  const proposal = pendingChatProposalPayload?.proposal || {};
  const baseRevision =
    proposal.base_revision ?? pendingChatProposalPayload?.base_revision ?? null;
  if (el.commandsViewDialog?.open) el.commandsViewDialog.close();
  clearChatProposal();
  const applyBody = {
    commands,
    actor: "ai",
    action: "ai_apply",
    description: proposal.title || "AI Apply",
  };
  if (baseRevision != null) applyBody.base_revision = baseRevision;
  postCommandsToCore(applyBody, "Core · chat Apply")
    .then(() => appendChatBubble("assistant", "Applied to Core."))
    .catch((err) => {
      appendChatBubble("assistant", err.message);
      setStatus(err.message, "error");
    });
}

async function postChatToCore(message) {
  const base = getCoreUrl();
  persistCoreUrl();
  const body = { message, history: chatHistoryForAgent() };
  const llm = getLlmConfigForRequest();
  if (llm) body.llm = llm;
  let response;
  try {
    response = await fetch(`${base}/v1/agent/turn`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(body),
    });
  } catch (err) {
    throw new Error(
      `Core unreachable at ${base} (${err.message}). Start with: python3 -m server`,
    );
  }
  let payload;
  try {
    payload = await response.json();
  } catch {
    throw new Error(`Core agent returned non-JSON (HTTP ${response.status})`);
  }
  if (!payload.ok && !payload.reply) {
    throw new Error(payload.error || `Agent failed (HTTP ${response.status})`);
  }
  return payload;
}

let chatTurnHistory = [];

function chatHistoryForAgent() {
  // Last few user/assistant text turns only (no tool dumps).
  return chatTurnHistory.slice(-8);
}

const HIGHLIGHT = 0xffcc66;
const FINDING_ERROR = 0xe06c75;
const FINDING_WARN = 0xe5c07b;

const renderer = new THREE.WebGLRenderer({ antialias: true, alpha: true });
renderer.setPixelRatio(Math.min(window.devicePixelRatio, 2));
renderer.setClearColor(0x000000, 0);
el.viewport.appendChild(renderer.domElement);

const scene = new THREE.Scene();
const perspCamera = new THREE.PerspectiveCamera(50, 1, 0.05, 200);
const orthoCamera = new THREE.OrthographicCamera(-1, 1, 1, -1, 0.05, 200);
let camera = perspCamera;
let projectionMode = "perspective"; // perspective | orthographic

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
let selectedRoomId = null;
let findingMeshes = [];
let pointerDown = null;
let lastPointerButton = 0;
let lastPointerType = "mouse";
let activeTouchCount = 0;
let camTween = null;

const _lookObj = new THREE.Object3D();

function easeInOutCubic(t) {
  return t < 0.5 ? 4 * t * t * t : 1 - (-2 * t + 2) ** 3 / 2;
}

function cancelCameraTween({ restoreControls = true } = {}) {
  camTween = null;
  if (restoreControls) controls.enabled = true;
}

function animateCameraTo(pose, { projection, durationMs = 480, statusMsg } = {}) {
  if (!pose) return;
  cancelCameraTween({ restoreControls: false });

  const fromPos = camera.position.clone();
  const fromTarget = controls.target.clone();
  const fromUp = camera.up.clone();
  const fromQuat = camera.quaternion.clone();

  if (projection === "orthographic") useOrthographic();
  else if (projection === "perspective") usePerspective();

  // After projection switch, keep starting from the captured pose.
  camera.position.copy(fromPos);
  camera.up.copy(fromUp);
  camera.quaternion.copy(fromQuat);
  controls.target.copy(fromTarget);

  _lookObj.position.copy(pose.position);
  _lookObj.up.copy(pose.up);
  _lookObj.lookAt(pose.target);
  const toQuat = _lookObj.quaternion.clone();

  controls.enabled = false;
  camTween = {
    t0: performance.now(),
    durationMs,
    fromPos,
    fromTarget,
    fromUp,
    fromQuat,
    toPos: pose.position.clone(),
    toTarget: pose.target.clone(),
    toUp: pose.up.clone(),
    toQuat,
    statusMsg,
  };
}

function updateCameraTween(now) {
  if (!camTween) return;
  const u = Math.min(1, (now - camTween.t0) / camTween.durationMs);
  const e = easeInOutCubic(u);
  camera.position.lerpVectors(camTween.fromPos, camTween.toPos, e);
  controls.target.lerpVectors(camTween.fromTarget, camTween.toTarget, e);
  camera.up.copy(camTween.fromUp).lerp(camTween.toUp, e).normalize();
  camera.quaternion.slerpQuaternions(camTween.fromQuat, camTween.toQuat, e);
  camera.updateMatrixWorld();
  if (u >= 1) {
    camera.position.copy(camTween.toPos);
    camera.up.copy(camTween.toUp);
    camera.quaternion.copy(camTween.toQuat);
    controls.target.copy(camTween.toTarget);
    const msg = camTween.statusMsg;
    cancelCameraTween();
    controls.update();
    if (msg) setStatus(msg, "ok");
  }
}

function syncCameraPose(from, to) {
  to.position.copy(from.position);
  to.quaternion.copy(from.quaternion);
  to.up.copy(from.up);
  to.near = from.near;
  to.far = from.far;
}

function updateOrthoFrustum() {
  const w = Math.max(el.viewport.clientWidth, 1);
  const h = Math.max(el.viewport.clientHeight, 1);
  const aspect = w / h;
  const span = lastFit ? lastFit.maxDim * 1.2 : 4;
  const halfH = span / 2;
  const halfW = halfH * aspect;
  orthoCamera.left = -halfW;
  orthoCamera.right = halfW;
  orthoCamera.top = halfH;
  orthoCamera.bottom = -halfH;
  if (lastFit) {
    orthoCamera.near = Math.max(0.01, lastFit.dist / 100);
    orthoCamera.far = lastFit.dist * 20;
  }
  orthoCamera.updateProjectionMatrix();
}

function setActiveCamera(next, { updateControls = true } = {}) {
  if (camera === next) {
    if (next === orthoCamera) updateOrthoFrustum();
    next.updateProjectionMatrix();
    return;
  }
  syncCameraPose(camera, next);
  if (next === orthoCamera) {
    next.zoom = 1;
    updateOrthoFrustum();
  } else {
    next.aspect = Math.max(el.viewport.clientWidth, 1) / Math.max(el.viewport.clientHeight, 1);
  }
  next.updateProjectionMatrix();
  camera = next;
  if (updateControls) {
    controls.object = camera;
    controls.update();
  }
}

function usePerspective({ statusMsg } = {}) {
  if (projectionMode === "perspective" && camera === perspCamera) return;
  projectionMode = "perspective";
  setActiveCamera(perspCamera);
  if (statusMsg) setStatus(statusMsg, "ok");
}

function useOrthographic({ statusMsg } = {}) {
  projectionMode = "orthographic";
  setActiveCamera(orthoCamera);
  if (statusMsg) setStatus(statusMsg, "ok");
}

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
  const rooms = Array.isArray(data.rooms) ? data.rooms : [];
  const visibleRooms = rooms.filter((r) => r && r.visible !== false);
  const roomLabel =
    rooms.length === 0
      ? "—"
      : rooms.length === 1
        ? rooms[0]?.name || "—"
        : `${rooms.length} rooms (${visibleRooms.map((r) => r.name || "?").join(", ") || "—"})`;
  const projectName = data.project_name || data.project?.name || data.scene || "—";
  const revision =
    data.revision ?? data.project?.revision ?? "—";
  const rows = [
    ["Source", sourceLabel],
    ["Project", projectName],
    ["Revision", String(revision)],
    ["Version", data.layoutlab_version || "—"],
    ["Viewer schema", data.viewer_schema || "—"],
    ["Unit", `${data.unit || "?"} · scale ${data.unit_scale ?? "?"}`],
    ["Rooms", roomLabel],
  ];
  el.meta.innerHTML = rows
    .map(([k, v]) => `<dt>${escapeHtml(k)}</dt><dd>${escapeHtml(String(v))}</dd>`)
    .join("");
}

function roomIdOfMesh(mesh) {
  return mesh?.userData?.room_id || "";
}

function setMeshOpacity(mesh, opacity) {
  if (!mesh?.material) return;
  const mats = Array.isArray(mesh.material) ? mesh.material : [mesh.material];
  for (const m of mats) {
    if (!("opacity" in m)) continue;
    if (mesh.userData._baseOpacity == null) {
      mesh.userData._baseOpacity = m.opacity ?? 1;
    }
    m.transparent = true;
    m.opacity = opacity;
    m.depthWrite = opacity >= 0.95;
    m.needsUpdate = true;
  }
}

function restoreMeshOpacity(mesh) {
  if (!mesh?.material) return;
  const mats = Array.isArray(mesh.material) ? mesh.material : [mesh.material];
  const base = mesh.userData._baseOpacity;
  if (base == null) return;
  for (const m of mats) {
    if (!("opacity" in m)) continue;
    m.opacity = base;
    m.transparent = base < 0.99;
    m.depthWrite = base >= 0.95;
    m.needsUpdate = true;
  }
}

function applyRoomFocus() {
  for (const mesh of collectMeshes()) {
    restoreMeshOpacity(mesh);
    if (!selectedRoomId) continue;
    const rid = roomIdOfMesh(mesh);
    if (rid && rid !== selectedRoomId) {
      setMeshOpacity(mesh, 0.18);
    }
  }
}

function fitCameraToRoom(roomId) {
  if (!sceneRoot || !roomId) return false;
  const box = new THREE.Box3();
  let any = false;
  for (const mesh of collectMeshes()) {
    if (roomIdOfMesh(mesh) === roomId) {
      box.expandByObject(mesh);
      any = true;
    }
  }
  if (!any || box.isEmpty()) return false;
  const size = box.getSize(new THREE.Vector3());
  const center = box.getCenter(new THREE.Vector3());
  const maxDim = Math.max(size.x, size.y, size.z, 1);
  const dist = maxDim * 1.35;
  const fit = { center, size, maxDim, dist };
  lastFit = fit;
  projectionMode = "perspective";
  camera = perspCamera;
  controls.object = perspCamera;
  perspCamera.near = Math.max(0.01, dist / 100);
  perspCamera.far = dist * 20;
  animateCameraTo(getFitViewPose(fit), {
    projection: "perspective",
    statusMsg: null,
  });
  return true;
}

function renderSelectedRoomFloorplan(data, roomId) {
  if (!el.roomFloorplan) return;
  el.roomFloorplan.innerHTML = "";
  if (!roomId || !data) {
    el.roomFloorplan.hidden = true;
    return;
  }
  const svg = renderFloorplanSvg(data, { roomId });
  if (!svg) {
    el.roomFloorplan.hidden = true;
    return;
  }
  el.roomFloorplan.appendChild(svg);
  el.roomFloorplan.hidden = false;
}

function selectRoom(roomId, { fit = true, announce = fit, setTarget = announce } = {}) {
  selectedRoomId = roomId || null;
  applyRoomFocus();
  if (setTarget) {
    if (roomId) setSelectionTarget({ type: "room", roomId }, { rebuild: true });
    else setSelectionTarget(null, { rebuild: true });
  } else {
    rebuildGizmos();
  }
  if (el.roomList) {
    for (const btn of el.roomList.querySelectorAll("button[data-room-id]")) {
      const id = btn.dataset.roomId || "";
      btn.classList.toggle("active", id === (selectedRoomId || ""));
    }
  }
  renderSelectedRoomFloorplan(lastExportData, selectedRoomId);
  if (selectedRoomId && fit) {
    const ok = fitCameraToRoom(selectedRoomId);
    const room = (lastExportData?.rooms || []).find((r) => r?.room_id === selectedRoomId);
    const name = room?.name || selectedRoomId;
    if (announce) {
      if (ok) setStatus(`Focused room ${name}`, "ok");
      else if (room?.visible === false) setStatus(`Room ${name} is hidden (no mesh)`, "warn");
      else setStatus(`Room ${name} selected`, "ok");
    }
  } else if (!selectedRoomId) {
    if (fit && sceneRoot) {
      const fitBox = computeFit(sceneRoot);
      if (fitBox) {
        lastFit = fitBox;
        animateCameraTo(getFitViewPose(fitBox), {
          projection: "perspective",
          statusMsg: null,
        });
      }
    }
    if (announce) setStatus("Showing all rooms", "ok");
  }
}

function renderRooms(data) {
  if (!el.roomList) return;
  const rooms = Array.isArray(data?.rooms) ? data.rooms : [];
  el.roomList.innerHTML = "";
  if (!rooms.length) {
    el.roomList.innerHTML = `<li><p class="room-list-empty">No rooms in export.</p></li>`;
    renderSelectedRoomFloorplan(null, null);
    return;
  }

  const allLi = document.createElement("li");
  const allBtn = document.createElement("button");
  allBtn.type = "button";
  allBtn.dataset.roomId = "";
  allBtn.innerHTML = `<span class="room-name">All rooms</span>`;
  allBtn.classList.toggle("active", !selectedRoomId);
  allBtn.addEventListener("click", () => selectRoom(null, { fit: true }));
  allLi.appendChild(allBtn);
  el.roomList.appendChild(allLi);

  for (const room of rooms) {
    if (!room?.room_id) continue;
    const li = document.createElement("li");
    const btn = document.createElement("button");
    btn.type = "button";
    btn.dataset.roomId = room.room_id;
    const badges = [];
    if (room.visible === false) badges.push("hidden");
    if (room.locked) badges.push("locked");
    const w = room.footprint?.width;
    const d = room.footprint?.depth;
    const size =
      Number.isFinite(Number(w)) && Number.isFinite(Number(d))
        ? `${Number(w).toFixed(2)} × ${Number(d).toFixed(2)} m`
        : "";
    btn.innerHTML =
      `<span class="room-name">${escapeHtml(room.name || room.room_id)}</span>` +
      (badges.length
        ? `<span class="room-badges">${badges.map((b) => escapeHtml(b)).join(" · ")}</span>`
        : "") +
      (size ? `<span class="room-size">${escapeHtml(size)}</span>` : "");
    btn.classList.toggle("active", selectedRoomId === room.room_id);
    btn.addEventListener("click", () => selectRoom(room.room_id, { fit: true }));
    li.appendChild(btn);
    el.roomList.appendChild(li);
  }

  if (selectedRoomId && !rooms.some((r) => r?.room_id === selectedRoomId)) {
    selectedRoomId = null;
  }
  applyRoomFocus();
  renderSelectedRoomFloorplan(data, selectedRoomId);
  if (el.roomList.querySelector("button[data-room-id]")) {
    for (const btn of el.roomList.querySelectorAll("button[data-room-id]")) {
      btn.classList.toggle("active", (btn.dataset.roomId || null) === (selectedRoomId || ""));
    }
  }
}

function collectMeshes() {
  const list = [];
  if (!sceneRoot) return list;
  sceneRoot.traverse((obj) => {
    if (obj.userData?.gizmo) return;
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

function clearSelection(opts = {}) {
  if (selected) clearMeshHighlight(selected);
  selected = null;
  if (opts.clearTarget !== false) selectionTarget = null;
  el.selection.textContent = "Click an object or room floor in the viewport.";
  el.selection.className = "muted";
  if (!gesture && opts.clearTarget !== false) rebuildGizmos();
}

function clearFindingHighlights() {
  for (const mesh of findingMeshes) clearMeshHighlight(mesh);
  findingMeshes = [];
  for (const li of el.findings.querySelectorAll("li.active")) {
    li.classList.remove("active");
  }
}

function setSelectionTarget(next, { rebuild = true } = {}) {
  selectionTarget = next;
  if (rebuild && !gesture) rebuildGizmos();
}

function selectMesh(mesh, opts = {}) {
  clearFindingHighlights();
  if (selected && selected !== mesh) clearMeshHighlight(selected);
  selected = mesh;
  if (!mesh) {
    clearSelection();
    return;
  }
  if (!isGizmoMesh(mesh)) {
    setMeshHighlight(mesh, HIGHLIGHT);
  }
  const ud = mesh.userData || {};

  if (!opts.skipTarget && !isGizmoMesh(mesh)) {
    if (isFurnitureMesh(mesh) && ud.object_id) {
      setSelectionTarget({ type: "furniture", objectId: ud.object_id, roomId: ud.room_id || null });
    } else if (ud.role === "room_floor" && ud.room_id) {
      setSelectionTarget({ type: "room", roomId: ud.room_id });
    } else if (isWallMesh(mesh) && ud.room_id) {
      setSelectionTarget({ type: "room", roomId: ud.room_id });
    } else if (ud.room_id && (ud.role === "room_fixed" || ud.role === "room_opening")) {
      setSelectionTarget({ type: "room", roomId: ud.room_id });
    }
  }

  const pose =
    selectionTarget?.type === "furniture" && selectionTarget.objectId
      ? poseFromExport(lastExportData, selectionTarget.objectId)
      : ud.object_id && isFurnitureMesh(mesh)
        ? poseFromExport(lastExportData, ud.object_id)
        : null;
  const bits = [
    mesh.name || "object",
    selectionTarget?.type ? `gizmos: ${selectionTarget.type}` : null,
    ud.gizmo ? `handle ${ud.kind}` : null,
    ud.role ? `role ${ud.role}` : null,
    ud.wall_side || ud.wallSide ? `wall ${ud.wall_side || ud.wallSide}` : null,
    ud.corner ? `corner ${ud.corner}` : null,
    selectionTarget?.objectId ? `id ${selectionTarget.objectId.slice(0, 8)}…` : null,
    (ud.room_id || ud.roomId || selectionTarget?.roomId)
      ? `room ${String(ud.room_id || ud.roomId || selectionTarget.roomId).slice(0, 8)}…`
      : null,
    pose ? `xy ${pose.location[0].toFixed(2)}, ${pose.location[1].toFixed(2)}` : null,
    pose ? `rz ${pose.rotation_z_deg.toFixed(1)}°` : null,
    pose?.validity ? `validity ${pose.validity}` : null,
    ud.clearance_name ? `clearance ${ud.clearance_name}` : null,
  ].filter(Boolean);
  el.selection.innerHTML = bits
    .map((b, i) => (i === 0 ? `<strong>${escapeHtml(b)}</strong>` : escapeHtml(b)))
    .join("<br>");
  el.selection.className = "selection-info";
  if (!opts.quiet) setStatus(`Selected ${mesh.name}`, "ok");
  if (opts.syncRoom !== false) {
    const rid = ud.room_id || ud.roomId || selectionTarget?.roomId;
    if (rid && rid !== selectedRoomId) {
      selectRoom(rid, { fit: false, announce: false, setTarget: false });
    }
  }
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

function loadExportData(data, sourceLabel, opts = {}) {
  if (!data || typeof data !== "object") throw new Error("Invalid export JSON");
  const preserve = Boolean(opts.preserveSelection);
  const preserveRoomId = preserve ? opts.preserveRoomId ?? selectedRoomId : null;
  const preserveCamera = Boolean(opts.preserveCamera ?? preserve);
  const keepTarget =
    opts.preserveTarget
      ? { ...opts.preserveTarget }
      : preserve && selectionTarget
        ? { ...selectionTarget }
        : null;
  lastExportData = data;
  selectedRoomId = null;
  clearSelection({ clearTarget: true });
  clearFindingHighlights();
  clearGroup(content);
  const built = buildSceneFromExport(data);
  content.add(built.root);
  sceneRoot = built.root;
  layers = built.layers;
  applyLayerVisibility();
  if (!preserveCamera) {
    projectionMode = "perspective";
    camera = perspCamera;
    controls.object = perspCamera;
    lastFit = fitCameraToRoot(perspCamera, controls, built.root);
    perspCamera.aspect = Math.max(el.viewport.clientWidth, 1) / Math.max(el.viewport.clientHeight, 1);
    perspCamera.updateProjectionMatrix();
    controls.update();
  }
  renderMeta(data, sourceLabel);
  renderRooms(data);
  renderAnalysis(data);
  if (preserveRoomId) {
    selectRoom(preserveRoomId, { fit: false, announce: false, setTarget: false });
  }
  if (keepTarget) {
    selectionTarget = keepTarget;
    rebuildGizmos();
    if (keepTarget.type === "furniture" && keepTarget.objectId) {
      const mesh = findMeshForObjectId(collectMeshes(), keepTarget.objectId);
      if (mesh) selectMesh(mesh, { syncRoom: false, skipTarget: true, quiet: true });
    } else if (keepTarget.type === "room" && keepTarget.roomId) {
      const floor = collectMeshes().find(
        (m) => m.userData?.role === "room_floor" && m.userData.room_id === keepTarget.roomId,
      );
      if (floor) selectMesh(floor, { syncRoom: false, skipTarget: true, quiet: true });
    }
  } else {
    rebuildGizmos();
  }
  const n = (data.objects || []).length;
  const findings = data.analysis?.findings?.length ?? 0;
  el.objectCount.textContent = `${n} object${n === 1 ? "" : "s"}`;
  if (!opts.quiet) {
    const findingNote = data.analysis?.analyzed
      ? ` · ${findings} finding${findings === 1 ? "" : "s"}`
      : "";
    setStatus(`Loaded ${sourceLabel} · ${n} objects${findingNote}`, "ok");
  }
}

function loadFromPasteText(text, sourceLabel = "clipboard paste") {
  const data = parseExportText(text);
  liveCoreSession = false;
  previewClient.resetLocal();
  loadExportData(data, sourceLabel);
}

async function loadFixture() {
  setStatus("Loading kids-room fixture…");
  liveCoreSession = false;
  previewClient.resetLocal();
  loadExportData(kidsRoomFixture, "reference_kids_room_export.json");
}

async function loadFindingsFixture() {
  setStatus("Loading findings demo…");
  liveCoreSession = false;
  previewClient.resetLocal();
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
  if (!sceneRoot) {
    setStatus("Load a scene first", "warn");
    return;
  }
  if (preset === "fit") {
    const fit = computeFit(sceneRoot);
    if (!fit) {
      setStatus("Nothing to frame", "warn");
      return;
    }
    lastFit = fit;
    if (camera === perspCamera) {
      perspCamera.near = Math.max(0.01, fit.dist / 100);
      perspCamera.far = fit.dist * 20;
    }
    animateCameraTo(getFitViewPose(fit), {
      projection: "perspective",
      statusMsg: "Camera fit · perspective",
    });
    return;
  }
  if (!lastFit) {
    lastFit = computeFit(sceneRoot);
  }
  if (!lastFit) {
    setStatus("Load a scene first", "warn");
    return;
  }
  animateCameraTo(getPresetPose(lastFit, preset), {
    projection: "orthographic",
    statusMsg: `Camera ${preset} · orthographic`,
  });
}

function rebuildGizmos() {
  if (gizmoGroup?.parent) {
    gizmoGroup.parent.remove(gizmoGroup);
    gizmoGroup.traverse((obj) => {
      if (obj.geometry) obj.geometry.dispose();
      if (obj.material) {
        if (Array.isArray(obj.material)) obj.material.forEach((m) => m.dispose());
        else obj.material.dispose();
      }
    });
  }
  gizmoGroup = null;
  if (!sceneRoot || !lastExportData || !selectionTarget) return;
  gizmoGroup = buildSelectionGizmos(lastExportData, selectionTarget);
  sceneRoot.add(gizmoGroup);
}

function findGizmoHandle(roomId, kind, key) {
  if (!gizmoGroup) return null;
  let found = null;
  gizmoGroup.traverse((obj) => {
    if (found || !obj.userData?.gizmo) return;
    if (obj.userData.roomId !== roomId || obj.userData.kind !== kind) return;
    if (kind === "wall" && obj.userData.wallSide === key) found = obj;
    if (kind === "corner" && obj.userData.corner === key) found = obj;
  });
  return found;
}

function pickGizmo(clientX, clientY) {
  if (!gizmoGroup) return null;
  const rect = renderer.domElement.getBoundingClientRect();
  pointer.x = ((clientX - rect.left) / rect.width) * 2 - 1;
  pointer.y = -((clientY - rect.top) / rect.height) * 2 + 1;
  raycaster.setFromCamera(pointer, camera);
  const hits = raycaster.intersectObject(gizmoGroup, true);
  return hits[0]?.object || null;
}

function pickObject(clientX, clientY, { preferFurniture = false } = {}) {
  const gizmo = pickGizmo(clientX, clientY);
  if (gizmo) return gizmo;
  const rect = renderer.domElement.getBoundingClientRect();
  pointer.x = ((clientX - rect.left) / rect.width) * 2 - 1;
  pointer.y = -((clientY - rect.top) / rect.height) * 2 + 1;
  raycaster.setFromCamera(pointer, camera);
  const hits = raycaster.intersectObjects(collectMeshes(), false);
  if (!hits.length) return null;
  if (preferFurniture) {
    const furn = hits.find((h) => isFurnitureMesh(h.object));
    if (furn) return furn.object;
    const floor = hits.find((h) => h.object?.userData?.role === "room_floor");
    if (floor) return floor.object;
    const wall = hits.find((h) => isWallMesh(h.object));
    if (wall) return wall.object;
  }
  return hits[0]?.object || null;
}

function resize() {
  const w = el.viewport.clientWidth;
  const h = el.viewport.clientHeight;
  if (w < 1 || h < 1) return;
  perspCamera.aspect = w / h;
  perspCamera.updateProjectionMatrix();
  if (projectionMode === "orthographic") updateOrthoFrustum();
  else orthoCamera.updateProjectionMatrix();
  renderer.setSize(w, h, false);
}

function frame(now = performance.now()) {
  updateCameraTween(now);
  controls.update();
  renderer.render(scene, camera);
  requestAnimationFrame(frame);
}

el.btnPaste.addEventListener("click", () => {
  pasteFromClipboard().catch((err) => setStatus(`Error: ${err.message}`, "error"));
});

el.btnCoreEmpty?.addEventListener("click", () => {
  postCommandsToCore(EMPTY_TEST_ROOM_COMMANDS, "Core · empty kids room").catch((err) =>
    setStatus(err.message, "error"),
  );
});

el.chatForm?.addEventListener("submit", (ev) => {
  ev.preventDefault();
  const message = (el.chatInput?.value || "").trim();
  if (!message) return;
  appendChatBubble("user", message);
  chatTurnHistory.push({ role: "user", content: message });
  el.chatInput.value = "";
  clearChatProposal();
  setStatus("Agent planning via Core /v1/agent/turn…");
  postChatToCore(message)
    .then((payload) => {
      let reply = payload.reply || payload.error || "(no reply)";
      const qs = payload.questions || [];
      if (qs.length) {
        reply += `\n\nFragen:\n- ${qs.join("\n- ")}`;
      }
      appendChatBubble("assistant", reply);
      chatTurnHistory.push({ role: "assistant", content: reply });
      const commands = payload.proposal?.commands || payload.commands || [];
      if (commands.length) {
        showChatProposal(payload);
        setStatus(`Agent proposal · ${commands.length} commands — Apply to run`, "ok");
      } else {
        setStatus("Agent: no commands proposed", "warn");
      }
    })
    .catch((err) => {
      appendChatBubble("assistant", err.message);
      setStatus(err.message, "error");
    });
});

el.chatInput?.addEventListener("keydown", (ev) => {
  if (ev.key !== "Enter") return;
  if (ev.shiftKey) return; // Shift+Enter = newline
  ev.preventDefault();
  el.chatForm?.requestSubmit();
});

el.btnChatDiscard?.addEventListener("click", () => {
  clearChatProposal();
  setStatus("Chat proposal discarded");
});

el.btnChatView?.addEventListener("click", () => {
  openCommandsView();
});

el.btnChatApply?.addEventListener("click", () => {
  applyPendingChatCommands();
});

el.btnCommandsViewApply?.addEventListener("click", () => {
  applyPendingChatCommands();
});

el.btnCoreFurnished?.addEventListener("click", () => {
  postCommandsToCore(FURNISHED_TEST_ROOM_COMMANDS, "Core · furnished kids room").catch((err) =>
    setStatus(err.message, "error"),
  );
});

el.btnCoreMultiroom?.addEventListener("click", () => {
  postCommandsToCore(MULTI_ROOM_DEMO_COMMANDS, "Core · multi-room demo").catch((err) =>
    setStatus(err.message, "error"),
  );
});

el.btnCoreCommands?.addEventListener("click", () => {
  el.commandsText.value = JSON.stringify(FURNISHED_TEST_ROOM_COMMANDS, null, 2);
  el.commandsDialog.showModal();
  el.commandsText.focus();
});

el.commandsForm?.addEventListener("submit", (ev) => {
  const submitter = ev.submitter;
  const value = submitter?.value || "cancel";
  if (value !== "send") return;
  ev.preventDefault();
  try {
    const parsed = JSON.parse(el.commandsText.value);
    const commands = Array.isArray(parsed) ? parsed : parsed.commands;
    if (!Array.isArray(commands)) throw new Error('JSON must include "commands": [...]');
    postCommandsToCore({ commands }, "Core · pasted commands")
      .then(() => {
        el.commandsDialog.close();
      })
      .catch((err) => setStatus(err.message, "error"));
  } catch (err) {
    setStatus(`Error: ${err.message}`, "error");
  }
});

el.coreUrl?.addEventListener("change", () => {
  persistCoreUrl();
  refreshCoreVersion();
});
loadStoredCoreUrl();
loadLlmSettings();
el.llmApiKey?.addEventListener("change", persistLlmSettings);
el.llmModel?.addEventListener("change", persistLlmSettings);
el.llmBaseUrl?.addEventListener("change", persistLlmSettings);
el.btnLlmClear?.addEventListener("click", () => {
  if (el.llmApiKey) el.llmApiKey.value = "";
  persistLlmSettings();
  setStatus("LLM API-Key gelöscht (lokal)", "ok");
});

function setSettingsOpen(open) {
  if (!el.settingsPopover || !el.btnSettings) return;
  el.settingsPopover.hidden = !open;
  el.btnSettings.setAttribute("aria-expanded", open ? "true" : "false");
}

el.btnSettings?.addEventListener("click", (ev) => {
  ev.stopPropagation();
  const open = el.settingsPopover?.hidden !== false;
  setSettingsOpen(open);
});

document.addEventListener("click", (ev) => {
  if (!el.settingsPopover || el.settingsPopover.hidden) return;
  const t = ev.target;
  if (el.settingsPopover.contains(t) || el.btnSettings?.contains(t)) return;
  setSettingsOpen(false);
});

function setInspectorCollapsed(collapsed) {
  if (!el.inspector || !el.btnInspectorToggle) return;
  el.inspector.dataset.collapsed = collapsed ? "true" : "false";
  el.btnInspectorToggle.setAttribute("aria-expanded", collapsed ? "false" : "true");
  el.btnInspectorToggle.title = collapsed ? "Inspector öffnen" : "Inspector schließen";
  // Wait for CSS grid transition so Three.js picks the new viewport size.
  window.setTimeout(resize, 220);
}

el.btnInspectorToggle?.addEventListener("click", () => {
  const collapsed = el.inspector?.dataset.collapsed !== "false";
  setInspectorCollapsed(!collapsed);
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

function applyExportFromCore(payload, label, opts = {}) {
  if (!payload?.export) {
    const detail = payload?.error || payload?.errors?.[0]?.error || "no export";
    throw new Error(detail);
  }
  liveCoreSession = true;
  loadExportData(payload.export, label, {
    preserveSelection: Boolean(opts.preserveSelection ?? true),
    preserveCamera: true,
    quiet: opts.quiet,
    preserveTarget: opts.preserveTarget ?? selectionTarget,
  });
}

function offsetObjectMeshes(objectId, dx, dy) {
  for (const mesh of collectMeshes()) {
    if (mesh.userData?.object_id === objectId) {
      mesh.position.x += dx;
      mesh.position.y += dy;
    }
  }
}

async function pushGesturePreview(commands, { begin = false } = {}) {
  const result = begin
    ? await previewClient.begin(commands, "viewer gizmo")
    : await previewClient.update(commands);
  if (!result?.ok) {
    const detail = result?.error || result?.errors?.[0]?.error || "preview failed";
    throw new Error(detail);
  }
  applyExportFromCore(result, "Core · preview", { quiet: true });
  return result;
}

function gestureLabel(g) {
  if (!g) return "Edit";
  if (g.kind === "wall") return `Moving ${g.wallSide} wall`;
  if (g.kind === "corner") return `Moving ${g.corner} corner`;
  if (g.kind === "move_axis") return `Moving ${g.target} ${g.axis}`;
  if (g.kind === "rotate_z") return "Rotating";
  if (g.kind === "scale_axis") return `Scaling ${g.axis}`;
  return "Editing";
}

async function endGestureCommit() {
  if (!gesture) return;
  const g = gesture;
  const startX = pointerDown?.x ?? g.startClientX;
  const startY = pointerDown?.y ?? 0;
  const endX = g._clientX ?? startX;
  const endY = g._clientY ?? startY;
  const dragged = Math.hypot(endX - startX, endY - startY) >= 4;
  if (!g.started && !dragged) {
    gesture = null;
    controls.enabled = true;
    return;
  }
  controls.enabled = true;
  try {
    if (!g.started) await ensureGesturePreview();
    if (!gesture?.started && !previewClient.active) {
      gesture = null;
      return;
    }
    const cmds = g.commands();
    gesture = null;
    await pushGesturePreview(cmds);
    const committed = await previewClient.commit(`viewer ${g.kind}`);
    if (!committed?.ok) throw new Error(committed?.error || "commit failed");
    applyExportFromCore(committed, "Core · gizmo commit", { quiet: true });
    setStatus(`${gestureLabel(g)} · revision ${committed.revision}`, "ok");
  } catch (err) {
    gesture = null;
    try {
      const cancelled = await previewClient.cancel();
      if (cancelled?.export) applyExportFromCore(cancelled, "Core · preview cancel", { quiet: true });
    } catch {
      /* ignore */
    }
    setStatus(`Gesture failed: ${err.message}`, "error");
  }
}

async function endGestureCancel() {
  if (!gesture && !previewClient.active) return;
  gesture = null;
  controls.enabled = true;
  try {
    const cancelled = await previewClient.cancel();
    if (cancelled?.export) {
      applyExportFromCore(cancelled, "Core · preview cancel", { quiet: true });
    } else if (lastExportData) {
      loadExportData(lastExportData, "restore", {
        preserveSelection: true,
        preserveCamera: true,
        quiet: true,
      });
    }
    setStatus("Preview cancelled", "warn");
  } catch (err) {
    previewClient.resetLocal();
    setStatus(`Cancel failed: ${err.message}`, "error");
  }
}

async function startGesture(ev, mesh) {
  if (!liveCoreSession) {
    setStatus("Gizmos need a Core scene (Empty / Furnished / Multi-room)", "warn");
    return false;
  }
  if (!isGizmoMesh(mesh)) return false;

  const floor = hitBlenderFloorXY(
    raycaster,
    camera,
    sceneRoot,
    ev.clientX,
    ev.clientY,
    renderer.domElement,
  );
  const ud = mesh.userData || {};
  const kind = ud.kind;

  if (kind === "wall") {
    gesture = {
      kind: "wall",
      roomId: ud.roomId,
      wallSide: String(ud.wallSide || "").toLowerCase(),
      startFloor: floor,
      startClientX: ev.clientX,
      _delta: 0,
      started: false,
      _beginning: false,
      commands() {
        return [wallMoveCommand(this.roomId, this.wallSide, this._delta || 0)];
      },
    };
  } else if (kind === "corner") {
    gesture = {
      kind: "corner",
      roomId: ud.roomId,
      corner: String(ud.corner || "").toLowerCase(),
      startFloor: floor,
      startClientX: ev.clientX,
      _dx: 0,
      _dy: 0,
      started: false,
      _beginning: false,
      commands() {
        return [cornerMoveCommand(this.roomId, this.corner, this._dx || 0, this._dy || 0)];
      },
    };
  } else if (kind === "move_axis") {
    const target = ud.target;
    const axis = ud.axis;
    if (target === "furniture") {
      const pose = poseFromExport(lastExportData, ud.objectId);
      if (!pose) {
        setStatus("Object not found in export", "error");
        return false;
      }
      gesture = {
        kind: "move_axis",
        target: "furniture",
        axis,
        objectId: ud.objectId,
        startPose: pose,
        startFloor: floor,
        startClientX: ev.clientX,
        lastLocal: { x: 0, y: 0 },
        started: false,
        _beginning: false,
        commands() {
          const loc = this._location || this.startPose.location;
          return [moveCommand(this.objectId, loc)];
        },
      };
    } else {
      gesture = {
        kind: "move_axis",
        target: "room",
        axis,
        roomId: ud.roomId,
        startFloor: floor,
        startClientX: ev.clientX,
        _dx: 0,
        _dy: 0,
        started: false,
        _beginning: false,
        commands() {
          return [roomMoveCommand(this.roomId, this._dx || 0, this._dy || 0)];
        },
      };
    }
  } else if (kind === "rotate_z") {
    const pose = poseFromExport(lastExportData, ud.objectId);
    if (!pose) {
      setStatus("Object not found in export", "error");
      return false;
    }
    gesture = {
      kind: "rotate_z",
      objectId: ud.objectId,
      startPose: pose,
      startClientX: ev.clientX,
      startFloor: floor,
      started: false,
      _beginning: false,
      commands() {
        const dx = (this._clientX ?? this.startClientX) - this.startClientX;
        const degrees = this.startPose.rotation_z_deg + dx * ROTATE_DEG_PER_PX;
        return [rotateCommand(this.objectId, degrees)];
      },
    };
  } else if (kind === "scale_axis") {
    const bounds = furnitureBounds(lastExportData, ud.objectId);
    if (!bounds) {
      setStatus("Object bounds missing", "error");
      return false;
    }
    gesture = {
      kind: "scale_axis",
      objectId: ud.objectId,
      axis: ud.axis,
      sign: ud.sign || 1,
      generator: ud.generator || bounds.generator || "",
      startSize: bounds.size,
      startFloor: floor,
      startClientX: ev.clientX,
      _delta: 0,
      started: false,
      _beginning: false,
      commands() {
        const params = resizeParamsForAxis(
          this.generator,
          this.axis,
          this.startSize,
          (this._delta || 0) * (this.sign || 1),
        );
        return [resizeCommand(this.objectId, params)];
      },
    };
  } else {
    return false;
  }

  selectMesh(mesh, { skipTarget: true, quiet: true });
  controls.enabled = false;
  return true;
}

async function ensureGesturePreview() {
  if (!gesture || gesture.started || gesture._beginning) return;
  gesture._beginning = true;
  try {
    await pushGesturePreview(gesture.commands(), { begin: true });
    if (!gesture) return;
    gesture.started = true;
    setStatus(`${gestureLabel(gesture)}… release to commit, Esc to cancel`);
  } catch (err) {
    gesture = null;
    controls.enabled = true;
    setStatus(`Preview begin failed: ${err.message}`, "error");
  } finally {
    if (gesture) gesture._beginning = false;
  }
}

async function updateGesture(ev) {
  if (!gesture) return;
  gesture._clientX = ev.clientX;
  gesture._clientY = ev.clientY;
  const startX = pointerDown?.x ?? gesture.startClientX;
  const startY = pointerDown?.y ?? ev.clientY;
  const dragPx = Math.hypot(ev.clientX - startX, ev.clientY - startY);
  if (!gesture.started && dragPx < 4) return;
  await ensureGesturePreview();
  if (!gesture?.started) return;

  const floor = hitBlenderFloorXY(
    raycaster,
    camera,
    sceneRoot,
    ev.clientX,
    ev.clientY,
    renderer.domElement,
  );

  if (gesture.kind === "wall" && floor && gesture.startFloor) {
    const dx = floor.x - gesture.startFloor.x;
    const dy = floor.y - gesture.startFloor.y;
    gesture._delta = wallDeltaFromDrag(gesture.wallSide, dx, dy);
  } else if (gesture.kind === "corner" && floor && gesture.startFloor) {
    gesture._dx = floor.x - gesture.startFloor.x;
    gesture._dy = floor.y - gesture.startFloor.y;
  } else if (gesture.kind === "move_axis" && floor && gesture.startFloor) {
    let dx = floor.x - gesture.startFloor.x;
    let dy = floor.y - gesture.startFloor.y;
    if (gesture.axis === "x") dy = 0;
    if (gesture.axis === "y") dx = 0;
    if (gesture.target === "furniture") {
      const optimisticDx = dx - gesture.lastLocal.x;
      const optimisticDy = dy - gesture.lastLocal.y;
      if (optimisticDx || optimisticDy) {
        offsetObjectMeshes(gesture.objectId, optimisticDx, optimisticDy);
        gesture.lastLocal = { x: dx, y: dy };
      }
      gesture._location = [
        gesture.startPose.location[0] + dx,
        gesture.startPose.location[1] + dy,
        gesture.startPose.location[2],
      ];
    } else {
      gesture._dx = dx;
      gesture._dy = dy;
    }
  } else if (gesture.kind === "scale_axis" && floor && gesture.startFloor) {
    const dx = floor.x - gesture.startFloor.x;
    const dy = floor.y - gesture.startFloor.y;
    gesture._delta = gesture.axis === "x" ? dx : dy;
  }
  // rotate_z uses client X delta in commands()

  const now = performance.now();
  if (now - lastPreviewPush < MOVE_THROTTLE_MS) return;
  lastPreviewPush = now;
  try {
    await pushGesturePreview(gesture.commands());
    if (gesture.kind === "move_axis" && gesture.target === "furniture") {
      const cur = poseFromExport(lastExportData, gesture.objectId);
      if (cur) {
        gesture.lastLocal = {
          x: cur.location[0] - gesture.startPose.location[0],
          y: cur.location[1] - gesture.startPose.location[1],
        };
      }
    }
  } catch (err) {
    setStatus(`Preview update: ${err.message}`, "warn");
  }
}

async function coreUndo() {
  if (gesture) {
    await endGestureCancel();
    return;
  }
  try {
    const result = await postCoreJson("/v1/undo", {});
    if (!result?.ok) throw new Error(result?.error || "undo failed");
    applyExportFromCore(result, "Core · undo");
    setStatus(`Undo · revision ${result.revision}`, "ok");
  } catch (err) {
    setStatus(err.message, "error");
  }
}

async function coreRedo() {
  if (gesture) return;
  try {
    const result = await postCoreJson("/v1/redo", {});
    if (!result?.ok) throw new Error(result?.error || "redo failed");
    applyExportFromCore(result, "Core · redo");
    setStatus(`Redo · revision ${result.revision}`, "ok");
  } catch (err) {
    setStatus(err.message, "error");
  }
}

el.btnUndo?.addEventListener("click", () => {
  coreUndo().catch((err) => setStatus(err.message, "error"));
});
el.btnRedo?.addEventListener("click", () => {
  coreRedo().catch((err) => setStatus(err.message, "error"));
});

renderer.domElement.addEventListener("pointerdown", (ev) => {
  lastPointerButton = ev.button;
  lastPointerType = ev.pointerType || "mouse";
  if (ev.pointerType === "touch") activeTouchCount += 1;
  if (ev.button !== 0) return;
  pointerDown = { x: ev.clientX, y: ev.clientY };
  const gizmoHit = pickGizmo(ev.clientX, ev.clientY);
  if (!gizmoHit) return;
  ev.preventDefault();
  ev.stopPropagation();
  controls.enabled = false;
  renderer.domElement.setPointerCapture?.(ev.pointerId);
  startGesture(ev, gizmoHit).catch((err) => setStatus(err.message, "error"));
});

renderer.domElement.addEventListener("pointermove", (ev) => {
  if (!gesture) return;
  updateGesture(ev).catch((err) => setStatus(err.message, "warn"));
});

renderer.domElement.addEventListener("pointerup", (ev) => {
  if (ev.pointerType === "touch") activeTouchCount = Math.max(0, activeTouchCount - 1);
  if (ev.button !== 0) return;
  if (gesture) {
    endGestureCommit().catch((err) => setStatus(err.message, "error"));
    pointerDown = null;
    return;
  }
  if (!pointerDown) return;
  const dx = ev.clientX - pointerDown.x;
  const dy = ev.clientY - pointerDown.y;
  pointerDown = null;
  if (dx * dx + dy * dy > 16) return; // drag = orbit, not click
  const hit = pickObject(ev.clientX, ev.clientY, { preferFurniture: true });
  if (hit && !isGizmoMesh(hit)) selectMesh(hit);
  else if (!hit) {
    clearSelection();
    clearFindingHighlights();
    setStatus("Selection cleared");
  }
});

renderer.domElement.addEventListener("pointercancel", () => {
  activeTouchCount = 0;
  if (gesture) {
    endGestureCancel().catch(() => {});
  }
});

// Orbit (rotate) leaves orthographic; dolly/pan keep it.
controls.addEventListener("start", () => {
  if (camTween) cancelCameraTween();
  if (projectionMode !== "orthographic") return;
  let isRotate = false;
  if (lastPointerType === "touch") {
    isRotate = activeTouchCount <= 1;
  } else {
    const map = controls.mouseButtons;
    const action =
      lastPointerButton === 0
        ? map.LEFT
        : lastPointerButton === 1
          ? map.MIDDLE
          : lastPointerButton === 2
            ? map.RIGHT
            : null;
    isRotate = action === THREE.MOUSE.ROTATE;
  }
  if (isRotate) {
    usePerspective({ statusMsg: "Orbit · perspective" });
  }
});
// Drag & drop export JSON (counter avoids flicker on child enter/leave)
let dragDepth = 0;

function showDropOverlay(on) {
  if (on) el.viewport.classList.add("drag-over");
  else el.viewport.classList.remove("drag-over");
}

el.viewport.addEventListener("dragenter", (ev) => {
  ev.preventDefault();
  dragDepth += 1;
  showDropOverlay(true);
});

el.viewport.addEventListener("dragover", (ev) => {
  ev.preventDefault();
  if (ev.dataTransfer) ev.dataTransfer.dropEffect = "copy";
});

el.viewport.addEventListener("dragleave", (ev) => {
  ev.preventDefault();
  dragDepth = Math.max(0, dragDepth - 1);
  if (dragDepth === 0) showDropOverlay(false);
});

el.viewport.addEventListener("drop", (ev) => {
  ev.preventDefault();
  dragDepth = 0;
  showDropOverlay(false);
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
  if ((ev.metaKey || ev.ctrlKey) && (ev.key === "z" || ev.key === "Z")) {
    ev.preventDefault();
    if (ev.shiftKey) coreRedo().catch((err) => setStatus(err.message, "error"));
    else coreUndo().catch((err) => setStatus(err.message, "error"));
    return;
  }
  if (ev.key === "f" || ev.key === "F") {
    ev.preventDefault();
    applyCamera("fit");
  }   else if (ev.key === "1") applyCamera("iso");
  else if (ev.key === "2") applyCamera("top");
  else if (ev.key === "3") applyCamera("front");
  else if (ev.key === "4") applyCamera("side");
  else if (ev.key === "Escape") {
    if (gesture || previewClient.active) {
      endGestureCancel().catch((err) => setStatus(err.message, "error"));
      return;
    }
    clearSelection();
    clearFindingHighlights();
    setStatus("Selection cleared");
  }
});

window.addEventListener("resize", resize);
resize();
frame();

resetCoreSessionOnLoad().finally(() => {
  loadFixture().catch((err) => setStatus(`Error: ${err.message}`, "error"));
});
