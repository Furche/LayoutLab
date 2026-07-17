# LayoutLab Viewer (Phase A)

Read-only web viewer for LayoutLab **export JSON** ([DD-014](../docs/design_decisions/DD-014-standalone-runtime-path.md), [json_protocol §6.4](../docs/json_protocol.md)).

**Stack:** Vite + Three.js (implementer choice among Three.js / Babylon).

## Run

```bash
cd viewer
npm install
npm run dev
```

Open the printed local URL (default `http://localhost:5173`).

On start the viewer loads `tests/fixtures/reference_kids_room_export.json`.

**From Blender:** LayoutLab → **Copy Scene Layout** → in the viewer click **Paste export** (or press ⌘V / Ctrl+V). If the browser blocks clipboard access, a paste dialog opens.

Also: **Kids room (findings)** for the intentional violations demo, or **Open file…** for a `.json` on disk.

## What it shows

- Room floor / wall panels (inward quads) / fixed elements
- Furniture boxes
- Clearance + opening wires (toggles in sidebar)
- `analysis` summary + findings list when present

## Notes

- Coordinates are Blender scene units (Z-up); the scene root maps them to Three.js Y-up.
- This is **not** a Blender replacement and does not execute commands (Phase B).
