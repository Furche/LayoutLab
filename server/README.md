# LayoutLab Core server (DD-014 + agent tools)

Local Python HTTP service that applies **Room Model** / generator commands and returns
`viewer_schema` export JSON. No Blender / `bpy` required.

## Start

From the repo root:

```bash
python3 -m server
```

Listens on `http://127.0.0.1:8765` by default.

## Endpoints

| Method | Path | Body | Response |
|---|---|---|---|
| `GET` | `/health` | — | `{ "ok", "tools", "chat", "session_log", … }` |
| `GET` | `/v1/session/log` | — | last session events (tail) + paths |
| `POST` | `/v1/commands` | `{ "commands": [ … ] }` | `{ "ok", "results", "export" }` |
| `POST` | `/v1/agent/turn` | `{ "message", "llm"?, "history"? }` | proposal (no apply) |
| `POST` | `/v1/tools/{name}` | tool params JSON | tool result |
| `POST` | `/v1/chat` | legacy thin chat | proposal |

## Session log

Each Core start archives the previous transcript to ``logs/PREV_SESSION.md`` (+ ``logs/archive/``)
and starts a fresh current log. Events are flushed to disk **immediately after every**
``/v1/agent/turn`` and ``/v1/commands`` response — not only on shutdown.

CORS is enabled for the Vite viewer (`http://localhost:5173`).

## Agent tools

Contract: [docs/agent_tool_contract.md](../docs/agent_tool_contract.md).

Read tools: `get_scene_summary`, `get_room`, `list_objects`, `get_object`,
`get_analysis`, `list_generators`, `list_supported_actions`.

```bash
curl -s -X POST http://127.0.0.1:8765/v1/tools/get_scene_summary \
  -H 'Content-Type: application/json' -d '{}'
```

With an API key (viewer LLM settings or env), `/v1/agent/turn` runs tool calling and
returns a structured `proposal`. Apply still uses `/v1/commands`.

Without a key, demo intents still work (empty/furnished kids room, schrank, lösche den raum, analyze).

## Room + generator write

Supported: room model, openings, fixed, `run_generator`, `analyze_layout`, deletes.
Export embeds live `analysis`. Not yet: undo, `regenerate`, `dry_run_commands`.

## Viewer

```bash
cd viewer && npm run dev
```

Sidebar **AI Chat** → agent turn; **Apply to Core** commits commands.
