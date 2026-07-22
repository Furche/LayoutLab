# LayoutLab Viewer

**Primary product surface** for LayoutLab ([AI_CONTEXT.md](../AI_CONTEXT.md), [DD-014](../docs/design_decisions/DD-014-standalone-runtime-path.md)).

The Viewer talks to **LayoutLab Core** over HTTP (`server/`). Blender is an optional runtime adapter — new UX belongs here by default.

**Stack:** Vite + Three.js.

## Run

```bash
# Terminal 1 — Core
cd /path/to/LayoutLab
python3 -m server
# → http://127.0.0.1:8765

# Terminal 2 — Viewer
cd viewer
npm install
npm run dev
```

Open the printed local URL (default `http://localhost:5173`).

On start the viewer can load `tests/fixtures/reference_kids_room_export.json`, or use **Core** buttons (empty / furnished room) when the server is up.

**From Blender (optional):** LayoutLab → **Copy Scene Layout** → in the viewer click **Paste export** (or ⌘V / Ctrl+V). If the browser blocks clipboard access, a paste dialog opens.

Also: drag-drop a `.json` onto the viewport, or **Examples** for fixtures.

**Viewport:** Fit (perspective) · Iso/Top/Front/Side (orthographic) · orbit returns to perspective · pan/dolly keep ortho · click to select · finding highlights · `F` / `1`–`4` / `Esc`.

## What it shows

- Room floor / wall panels (inward quads) / fixed elements (all rooms in export)
- Furniture boxes / meshes from Core export
- Clearance + opening wires (toggles in sidebar)
- `analysis` summary + findings list when present
- Chat / planning shortlist → Apply against Core (`base_revision`)

## Authority

- Scene truth lives in **Core** (Spatial Project, integer `revision`, Undo).
- Mutations: `POST /v1/commands` (commit) or preview endpoints — not Viewer-local inventing of transforms.
- Export contract: [json_protocol.md](../docs/json_protocol.md) (`viewer_schema`, `rooms[]`, `project_id`).

## Current focus

Viewer UX on top of FC-001 Core (transactions, furniture/room ops, multi-room project):

1. ~~Multi-room meta / visible-room floorplan pick~~ ✅ (`0.10.41`)
2. Room selection UI + project overview (next)
3. Direct manipulation → preview/commit
4. Planning / shortlist feedback polish

See [docs/HANDOFF.md](../docs/HANDOFF.md).
