# LayoutLab Agent Tool Contract

**Status:** Design + implementing (Agent-1 read tools)  
**Version:** `agent_tools` 0.1  
**Date:** 2026-07-18  
**Related:** [DD-009](design_decisions/DD-009-ai-execution-boundary.md) · [json_protocol.md](json_protocol.md) · [DD-014](design_decisions/DD-014-standalone-runtime-path.md)

------------------------------------------------------------------------

## Principles

1. **Core = source of truth.** Tools read/validate Core state; they invent no geometry.
2. **Writes are proposals.** Mutating commands appear only in `proposal.commands` and need
   explicit Apply (`POST /v1/commands`) — or later an explicit commit tool.
3. **Seed + tools.** Optional small scene seed; details loaded via tools.
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

## Validate / dry-run (Agent-2 — later)

### `validate_commands`

Static checks only (allowlist, required fields, generator exists). No geometry.

### `dry_run_commands`

Clone session → apply commands → optional analyze → discard clone. No live commit.
Enables Plan → Dry-Run → Analyze → Revise without mutating the user session.

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
| `POST /v1/agent/turn` | LLM orchestration: tool calls → structured proposal |
| `POST /v1/commands` | Commit / Apply (unchanged) |
| `POST /v1/chat` | Legacy thin chat (demo + one-shot LLM); keep until agent turn replaces UI |

MCP may later adapt the same tool functions; it is not the primary bus.

------------------------------------------------------------------------

## Implementation order

1. Core tool functions + `POST /v1/tools/{name}` (read tools) ← **now**
2. `POST /v1/agent/turn` with tool calling → structured proposal
3. Viewer uses agent turn; Apply still `/v1/commands`
4. `validate_commands`
5. Session clone + `dry_run_commands`
6. Persist light agent state (goal / questions / last findings)

------------------------------------------------------------------------

## Out of scope (this contract)

- Multi-variant objects (DD-011)
- Free-area heatmaps
- Undo
- MCP as primary bus
- Streaming product / auth (DD-012)
- Dumping full viewer export / meshes into the model context
