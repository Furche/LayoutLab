# LayoutLab Core server (DD-014 + agent tools + DD-018 transactions)

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
| `GET` | `/health` | — | `{ "ok", "core_version", "revision", "can_undo", "can_redo", "tools", … }` |
| `GET` | `/v1/session/log` | — | last session events (tail) + paths + `core_version` |
| `POST` | `/v1/session/reset` | `{ "reason"?, "clear_scene"? }` | archive log, start fresh session (viewer calls this on tab refresh) |
| `POST` | `/v1/commands` | `{ "commands", "actor"?, "base_revision"?, "action"?, "description"? }` | commit via `RoomSession.commit_commands` → `{ "ok", "results", "export", "revision", "transaction", … }` |
| `POST` | `/v1/undo` | `{}` | restore previous committed revision |
| `POST` | `/v1/redo` | `{}` | reapply last undone transaction ops |
| `POST` | `/v1/preview/begin` | `{ "commands"?, "actor"?, "description"? }` | non-authoritative preview (no Undo) |
| `POST` | `/v1/preview/update` | `{ "commands" }` | replace preview ops from preview base |
| `POST` | `/v1/preview/commit` | `{ "action"?, "description"? }` | commit preview as one transaction |
| `POST` | `/v1/preview/cancel` | `{}` | discard preview |
| `POST` | `/v1/agent/turn` | `{ "message", "llm"?, "history"? }` | proposal (no apply); includes `base_revision` |
| `POST` | `/v1/tools/{name}` | tool params JSON | tool result |
| `POST` | `/v1/chat` | legacy thin chat | proposal |

### Authoritative Apply (DD-018)

- Live mutations go through **`commit_commands`** (not internal `apply_commands`).
- Integer **`revision`** advances on each successful commit.
- AI Apply should send `actor: "ai"` and `base_revision` from the proposal. Mismatch → `error_code: "stale_base_revision"` (no blind apply).
- If `base_revision` is present and `actor` omitted, the server defaults `actor` to `ai`.
- User / system / import batches may omit `base_revision` (uses current revision).

## Session log

Each Core start (and each Viewer full reload via ``POST /v1/session/reset``) archives the
previous transcript to ``logs/PREV_SESSION.md`` (+ ``logs/archive/``) and starts a fresh
current log. The markdown header includes ``core_version`` from ``layoutlab.bl_info``.

Events are flushed to disk **immediately after every** ``/v1/agent/turn`` and
``/v1/commands`` response — not only on shutdown.

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
returns a structured `proposal` with `base_revision`. Apply still uses `/v1/commands`.

Without a key, demo intents still work (empty/furnished kids room, schrank, lösche den raum, analyze).

## Room + generator write

Supported: room model, openings, fixed, `run_generator`, `analyze_layout`, deletes,
semantic transactions (preview / commit / undo / redo), semantic furniture ops
(`move` / `rotate_z` / duplicate / delete / hide / lock by `object_id`). Export embeds
live `analysis`, `revision`, and furniture `validity` / `support_ref`. Not yet:
headless `regenerate` (WP-04), viewport gizmos, wall resize (WP-05).

## Viewer

```bash
cd viewer && npm run dev
```

Sidebar **AI Chat** → agent turn; **Apply to Core** commits commands with `base_revision`.
