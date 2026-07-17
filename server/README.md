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

## Room write slice

Supported actions: `create_room`, `update_room`, `delete_room`, openings,
fixed elements, `delete_collection_objects`.

Not in this slice: `run_generator`, `analyze_layout`, furniture.

## Example

```bash
curl -s http://127.0.0.1:8765/health

curl -s -X POST http://127.0.0.1:8765/v1/commands \
  -H 'Content-Type: application/json' \
  -d @tests/fixtures/reference_kids_room_shell_commands.json
```

The response `export` field is the same shape the Phase A viewer loads.

## Viewer

```bash
cd viewer && npm run dev
```

Then use **Empty test room (Core)** in the viewer toolbar (Core URL default
`http://127.0.0.1:8765`).
