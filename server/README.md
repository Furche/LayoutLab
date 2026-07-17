# LayoutLab Core server (DD-014 Phase B)

Local Python HTTP service that applies **Room Model** commands and returns a
`viewer_schema` export JSON. No Blender / `bpy` required.

## Start

From the repo root:

```bash
python -m server
```

Or:

```bash
python server/app.py
```

Listens on `http://127.0.0.1:8765` by default.

## Endpoints

| Method | Path | Body | Response |
|---|---|---|---|
| `GET` | `/health` | — | `{ "ok": true, ... }` |
| `POST` | `/v1/commands` | `{ "commands": [ ... ] }` | `{ "ok", "results", "export" }` |

CORS is enabled for the Vite viewer (`http://localhost:5173`).

## Room + generator write slice (Phase B / B2)

Supported actions: `create_room`, openings, fixed elements, `delete_collection_objects`,
`delete_prefix`, `run_generator` (bundled generators: `bed_basic`, `desk_basic`, `wardrobe_basic`),
`analyze_layout`.

Export always includes live `analysis` (clearance overlaps). Not yet: undo, `regenerate`.

## Example

```bash
curl -s http://127.0.0.1:8765/health

curl -s -X POST http://127.0.0.1:8765/v1/commands \
  -H 'Content-Type: application/json' \
  -d @tests/fixtures/reference_kids_room_commands.json
```

## Viewer

```bash
cd viewer && npm run dev
```

Use **Empty test room (Core)** or **Furnished test room (Core)** (Core URL default
`http://127.0.0.1:8765`).
