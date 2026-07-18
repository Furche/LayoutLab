# LayoutLab Agent Tool Contract

**Status:** Design + implementing (Agent-2.3 plan_layout recipes)  
**Version:** `agent_tools` 0.5  
**Date:** 2026-07-19  
**Related:** [DD-009](design_decisions/DD-009-ai-execution-boundary.md) · [DD-015](design_decisions/DD-015-soft-metrics-and-tradeoffs.md) · [DD-016](design_decisions/DD-016-deterministic-layout-recipes.md) · [json_protocol.md](json_protocol.md) · [DD-014](design_decisions/DD-014-standalone-runtime-path.md)

------------------------------------------------------------------------

## Principles

1. **Core = source of truth.** Tools read/validate Core state; they invent no geometry.
2. **Writes are proposals.** Mutating commands appear only in `proposal.commands` and need
   explicit Apply (`POST /v1/commands`) — or later an explicit commit tool.
3. **Seed + tools.** Each agent turn injects a Core scene seed; details load via tools.
4. **Provider-neutral.** Tool name + JSON params + JSON result + structured final proposal.
5. **No meshes** in tool responses (except a future explicit debug tool).
6. **Soft metrics + tradeoffs (DD-015).** Core measures packing / opening access; AI may bend hard
   rules only with documented `expected_risks`; User Apply = consent. Core does not block Apply in v1.

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

**Returns:** DD-008 + DD-015 analysis (`analyzed`, `summary`, `findings`, `soft_summary`, …).
Soft finding types: `soft_packing`, `opening_access`.

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
3. Optional analyze (clearances + soft) + `scene_after` + `soft_summary`.
4. Always includes **`layout_sketch`** (top-down ASCII + `bounds_xy`) for the clone.
5. **Live session is never mutated.**

Enables Plan → Dry-Run → See sketch → Analyze → Revise without committing.

### `get_layout_sketch`

**Params:** `{ "collection"?: string }`

**Returns:** top-down spatial abstraction for the current (or dry-run) scene:

- `ascii` — compact map (`#` wall, `D` door, `W` window, letters = furniture,
  `+` preferred clearance, `*` required clearance, `.` free floor)
- `rooms[].openings` / `rooms[].furniture[].bounds_xy` (+ `head_side` when known)
- `rooms[].clearances[]` with `clearance_name`, `requirement`, `bounds_xy` (default on;
  set `include_clearances: false` to omit)
- `legend`, orientation notes (top = north / +Y)

Not pixels and not the 3D viewport — intentional cheap “eyes” for the LLM.

------------------------------------------------------------------------

## Planning recipes (DD-016 / Agent-2.3)

### `plan_layout`

**Params (v0):**

```json
{
  "recipe": "bedroom_basic",
  "width": 4.0,
  "depth": 3.5,
  "height": 2.5,
  "door": { "wall_side": "east", "width": 0.9 },
  "windows": [{ "wall_side": "south", "width": 1.2, "sill_height": 0.9 }],
  "include_desk": true,
  "include_wardrobe": true,
  "collection": "layoutlab_room"
}
```

**Returns:** `{ ok, recipe, commands, assumes, notes, known_recipes, … }`

Deterministic Core planner — **does not mutate** the live session. Agent should prefer this for
standard bedrooms instead of inventing free `location` / `head_side`. Then
`validate_commands` → `dry_run_commands` on the returned commands.

v0 recipe: **`bedroom_basic`** only (bed + optional wardrobe/desk; door + windows).

------------------------------------------------------------------------

## Turn seed (Agent-2)

Every LLM agent turn injects synthetic tool results before the first model call:

1. `get_scene_summary`
2. `list_generators`
3. `get_layout_sketch`

The model should trust this seed and only call extra read tools when needed.
Prefer `validate_commands` → `dry_run_commands` before a non-empty final proposal.
After dry-run, read `layout_sketch.ascii` + soft warnings and revise if needed.

After the final proposal, Core attaches a **`quality`** preview (automatic dry-run):
`has_hard_errors`, `has_soft_warnings`, `has_expected_risks`, `needs_user_confirm`,
slim findings, plus `layout_sketch_ascii` / legend.

------------------------------------------------------------------------

## Tradeoffs (DD-015)

- Soft warnings → prefer replan.
- Hard errors → try alternatives; if compromise: fill `proposal.expected_risks` and explain.
- Never claim a hard violation is OK without stating the cost.
- Viewer should warn before Apply when `quality.needs_user_confirm` or risks/errors are present.

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
| `POST /v1/agent/turn` | LLM orchestration: seed + tool calls → structured proposal + quality |
| `POST /v1/commands` | Commit / Apply (unchanged; no hard block on findings in v1) |
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
7. Soft metrics + quality preview + tradeoff prompt (DD-015) ✅
8. Layout sketch (top-down ASCII) in seed + dry_run + quality ✅
9. `plan_layout` + `bedroom_basic` recipe (DD-016) ✅
10. Persist light agent state (goal / questions / last findings) ← next
11. More recipes (`kids_room`, `office`) / variants ← later

------------------------------------------------------------------------

## Out of scope (this contract)

- Multi-variant objects (DD-011)
- Free-area heatmaps
- Undo
- MCP as primary bus
- Streaming product / auth (DD-012)
- Dumping full viewer export / meshes into the model context
- Aesthetic ML / numeric “goodness” scores
