# DD-016 — Deterministic Layout Recipes (Planning Layer v0)

**Status:** Accepted  
**Date:** 2026-07-19  
**Accepted:** 2026-07-20  
**Related:** [DD-008](DD-008-constraints-and-layout-analysis.md) · [DD-009](DD-009-ai-execution-boundary.md) · [DD-015](DD-015-soft-metrics-and-tradeoffs.md) · [Future_Ideas.md](../Future_Ideas.md) §5 / §9 · [agent_tool_contract.md](../agent_tool_contract.md)

------------------------------------------------------------------------

## Decision summary (Accepted)

Locks Planning Layer v0: **AI chooses recipe / requirements**; **Core owns standard bedroom geometry** via `plan_layout` + `bedroom_basic`. Free LLM xy remains only for custom overrides after a recipe baseline.

Shipped beyond the original v0 sketch: mini-`requirements` object, recipe baseline enforcement, light `agent_state`, bedroom intent/placement helpers under `layoutlab/runtime/planning/`. Further recipes (`kids_room`, …) stay future work — not authorized by this accept alone.

------------------------------------------------------------------------

## Problem

The chat agent invents free `location` / `head_side` coordinates. LLMs have weak spatial
priors: they produce fluent plans that fail clearances, float beds in the middle of the room,
or put desks inside beds. Symptom fixes (ASCII sketch, soft/hard replan, AABB nudges) improve
reliability but do **not** encode “how a human furnishes a bedroom.”

Per [AI_CONTEXT.md](../../AI_CONTEXT.md) and Future_Ideas §9, **Planning** is a separate layer
from **Execution**. Today the LLM is doing both badly. We need a first Planning artifact that
is deterministic, testable, and callable by the agent.

------------------------------------------------------------------------

## Decision

### 1. Responsibility (extends DD-009)

| Concern | Owner |
|---|---|
| User intent / recipe choice / tradeoff language | AI |
| Standard layout geometry for known room types | **LayoutLab Core (Planning recipes)** |
| Mesh generation, clearances, analyze | LayoutLab Execution (unchanged) |
| Apply / consent | User |

> AI chooses **which recipe / priorities**. Core computes **where objects go**.  
> Generators still build **how** meshes look.

### 2. Layout recipes (v0)

A **recipe** is a pure function:

```
(room_size, openings_spec, furniture_set, options) → commands[]
```

- Lives under `layoutlab/runtime/planning/` (headless, no `bpy`).
- Output is normal LayoutLab commands (`create_room`, `add_opening`, `run_generator`, …).
- Must be unit-testable: dry-run + analyze → prefer **zero hard errors** for reference sizes.
- v0 ships **`bedroom_basic`** only (bed + wardrobe + optional desk; door + window).

### 3. Agent tool

New tool: **`plan_layout`**

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

**Returns:** `{ ok, recipe, commands, assumes, notes }`

Agent workflow for “Schlafzimmer einrichten”:

1. Ask clarifying questions only when size/use unknown (or use defaults in `assumes`).
2. Call **`plan_layout`** (not free-form xy).
3. `validate` + `dry_run`; if hard errors remain, adjust recipe options or one repair pass.
4. Propose `commands` from the tool — may explain tradeoffs via `expected_risks`.

Free-form `run_generator` placement remains allowed for **custom** user instructions
(“Schreibtisch genau hier”) after a recipe baseline.

### 4. What v0 does *not* include

- Multi-variant scoring (DD-011 territory)
- Full zone graph / walkway solver
- Catalog / purchasable products
- Replacing analyze or generators

### 5. Bedroom_basic placement rules (normative for v0)

For a rectangular room with east door + south window (defaults):

1. **Bed** against south wall, `head_side=y_min`. Human 120×200 → `length=1.2` (X, along wall) and `width=2.0` (Y, into room) — sleep along +Y, not a 2 m-wide short bed.
2. **Wardrobe** on **north** wall (`front_side=y_min` — `wardrobe_basic` only supports Y fronts), toward west, clear of east door.
3. **Desk** on north wall east of wardrobe (or west of door strip) — chair clearance (−Y) into free floor; **never** overlapping bed AABB; keep east door access clear.
4. Always emit `delete_collection_objects` + `create_room` + openings before furniture.

Exact numbers live in code + tests; this DD locks the **intent** of the rules.

------------------------------------------------------------------------

## Alternatives considered

| Option | Why not (for v0) |
|---|---|
| More LLM prompt engineering | Unreliable; not testable; we already hit that wall |
| Only post-hoc AABB nudges | Fixes crashes, not “human” layouts |
| Full optimization solver now | Too heavy; needs recipes + metrics first |
| Keep planning only in the LLM | Violates Future_Ideas layer split; repeats Execution mistakes |

------------------------------------------------------------------------

## Consequences

- Agent tools version bumps (`agent_tools` 0.5).
- Chat quality for bedrooms should jump without more heuristic spam in `agent.py`.
- Symptom helpers (sketch, soft/hard replan) remain as **guards**, not as the planner.
- Accepting this DD authorizes implementing `plan_layout` + `bedroom_basic` without further architecture bikeshedding for v0 scope.

------------------------------------------------------------------------

## Implementation order

1. ~~`layoutlab/runtime/planning/bedroom_basic.py` + tests (dry-run hard errors = 0 on 4×4 / 4×3.5).~~ ✅
2. ~~Tool `plan_layout` + contract docs.~~ ✅
3. ~~Agent system prompt: prefer `plan_layout` for bedroom intents.~~ ✅
4. ~~Slim down free-placement heuristics into `planning/` (intent + placement).~~ ✅ (v0.10.21)
5. Later: more recipes (`kids_room`, `office`) → multi-candidate planning ([DD-011](DD-011-layout-variants-and-comparison.md) **Accepted**).

See also: recipe as goal-oriented strategy in DD-011 (not room-type-only).

------------------------------------------------------------------------

## Acceptance

- [x] **Accepted** 2026-07-20 — Viewer/Core runs show recipe bedrooms with dry-run hard errors = 0 (e.g. furnished bedroom apply on Core 0.10.21).

------------------------------------------------------------------------

## History

| Ver | Date | Note |
|---|---|---|
| 0.1 | 2026-07-19 | Proposed (v0 scope) |
| 1.0 | 2026-07-20 | **Accepted** — `plan_layout` + `bedroom_basic` + requirements/baseline locked |
