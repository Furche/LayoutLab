# LayoutLab Agent Tool Contract

**Status:** Design + implementing (Agent-2 validate / dry-run)  
**Version:** `agent_tools` 0.2  
**Date:** 2026-07-18  
**Related:** [DD-009](design_decisions/DD-009-ai-execution-boundary.md) · [json_protocol.md](json_protocol.md) · [DD-014](design_decisions/DD-014-standalone-runtime-path.md)

------------------------------------------------------------------------

## Principles

1. **Core = source of truth.** Tools read/validate Core state; they invent no geometry.
2. **Writes are proposals.** Mutating commands appear only in `proposal.commands` and need
   explicit Apply (`POST /v1/commands`) — or later an explicit commit tool.
3. **Seed + tools.** Each agent turn injects a Core scene seed; details load via tools.
4. **Provider-neutral.** Tool name + JSON params + JSON result + structured final proposal.
5. **No meshes** in tool responses (except a future explicit debug tool).

DD-009 remains binding: AI plans WHAT; LayoutLab Core executes HOW.

------------------------------------------------------------------------

## Agent state (lightweight)

Not the LLM transcript — a small app/Core state object:

```json
{
  "agent_schema": "0.1.0",
  "goal": "Platz für zwei Kinder",
  "open_questions": [],
  "last_proposal_id": null,
  "last_analysis_summary": null,
  "constraints_noted": []
}
```

*(Persistence of this object is still pending — Agent-3.)*

------------------------------------------------------------------------

## Read tools (Agent-1)

### `get_scene_summary`

**Params:** `{ "collection"?: string }`

**Returns:** rooms (footprint + counts), object_counts, generators_present, analysis summary.
No meshes, no full object lists, no wall panel corners.

### `get_room`

**Params:** `{ "room": "<name|room_id>", "include"?: ["openings","fixed","walls_meta"] }`

**Returns:** origin, height, footprint, walls_meta (side/length/id), openings, fixed_elements,
world_bounds. No display panel corners.

### `list_objects`

**Params:** `{ "collection"?, "roles"?, "generators"?, "limit"? }`

**Returns:** name, object_id, role, part, generator, collection, world_bounds, dimensions.
Clearances include clearance_name + requirement.

### `get_object`

**Params:** `{ "object_id"? , "name"? }` (one required)

**Returns:** list entry fields + params + clearances + parent_object_id when present.

### `get_analysis`

**Params:** `{ "scope": "scene"|"collection", "collection"?, "refresh"?: true }`

**Returns:** DD-008 analysis shape (`analyzed`, `summary`, `findings`, …).

### `list_generators`

**Params:** `{ "names"?: string[] }`

**Returns:** name, category, description, version, key_params (no source code).

### `list_supported_actions`

**Params:** `{}`

**Returns:** allowlisted session actions (same set as headless `RoomSession`).

------------------------------------------------------------------------

## Validate / dry-run (Agent-2)

### `validate_commands`

**Params:** `{ "commands": [ … ] }`

Static checks only (allowlist, required fields, known generators). No geometry.
Returns `{ ok, errors[], warnings[], command_count }`.

### `dry_run_commands`

**Params:** `{ "commands": [ … ], "analyze"?: true, "stop_on_invalid"?: true }`

1. Optionally validate (default stop if invalid).
2. `RoomSession.clone()` → apply commands on the clone.
3. Optional analyze + `scene_after` summary.
4. **Live session is never mutated.**

Enables Plan → Dry-Run → Analyze → Revise without committing.

------------------------------------------------------------------------

## Turn seed (Agent-2)

Every LLM agent turn injects synthetic tool results before the first model call:

1. `get_scene_summary`
2. `list_generators`

The model should trust this seed and only call extra read tools when needed.
Prefer `validate_commands` → `dry_run_commands` before a non-empty final proposal.

------------------------------------------------------------------------

## Final structured proposal

After tool rounds, the model emits:

```json
{
  "reply": "…",
  "questions": [],
  "proposal": {
    "proposal_id": "uuid",
    "title": "…",
    "rationale": "…",
    "assumes": [],
    "commands": [],
    "expected_risks": []
  },
  "suggested_next_tools": []
}
```

UI shows `reply` primarily; Apply sends `proposal.commands` to `POST /v1/commands`.
Core re-sanitizes against the allowlist before apply.

------------------------------------------------------------------------

## HTTP mapping

| Endpoint | Role |
|---|---|
| `POST /v1/tools/{name}` | Deterministic tool execution (testable without LLM) |
| `POST /v1/agent/turn` | LLM orchestration: seed + tool calls → structured proposal |
| `POST /v1/commands` | Commit / Apply (unchanged) |
| `POST /v1/chat` | Legacy thin chat (demo + one-shot LLM); keep until agent turn replaces UI |

MCP may later adapt the same tool functions; it is not the primary bus.

------------------------------------------------------------------------

## Implementation order

1. Core tool functions + `POST /v1/tools/{name}` (read tools) ✅
2. `POST /v1/agent/turn` with tool calling → structured proposal ✅
3. Viewer uses agent turn; Apply still `/v1/commands` ✅
4. `validate_commands` ✅
5. Session clone + `dry_run_commands` ✅
6. Automatic scene seed per turn ✅
7. Persist light agent state (goal / questions / last findings) ← next

------------------------------------------------------------------------

## Out of scope (this contract)

- Multi-variant objects (DD-011)
- Free-area heatmaps
- Undo
- MCP as primary bus
- Streaming product / auth (DD-012)
- Dumping full viewer export / meshes into the model context
