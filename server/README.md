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
| `GET` | `/health` | — | `{ "ok": true, "chat": "demo"|"llm", ... }` |
| `POST` | `/v1/commands` | `{ "commands": [ ... ] }` | `{ "ok", "results", "export" }` |
| `POST` | `/v1/chat` | `{ "message": "…", "scene"?: {…} }` | `{ "ok", "reply", "commands" }` proposal |

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

## Chat (thin planning)

`POST /v1/chat` with `{ "message": "…", "scene"?: {…} }` returns a **proposal**:
`{ ok, mode, reply, commands }` — it does **not** mutate the session.

Apply only via `POST /v1/commands` (viewer **Apply** button).

| Mode | When |
|---|---|
| `demo` | No API key — keyword intents (empty / furnished kids room, analyze) |
| `llm` | Viewer **LLM-Einstellungen** (API-Key) oder Env `OPENAI_API_KEY` / `LAYOUTLAB_LLM_API_KEY` |

Request body may include:

```json
{
  "message": "…",
  "scene": { … },
  "llm": {
    "api_key": "sk-…",
    "model": "gpt-4o-mini",
    "base_url": "https://api.openai.com/v1"
  }
}
```

Key from the request is preferred over env for that call. The viewer stores the key only in `localStorage`.

## Viewer

```bash
cd viewer && npm run dev
```

Use the sidebar **AI Chat**, or **Empty / Furnished test room (Core)** (Core URL default
`http://127.0.0.1:8765`).
