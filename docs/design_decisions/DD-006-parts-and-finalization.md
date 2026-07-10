# DD-006 — Parts, Finalization, and Main/Dynamic Parts

**Status:** Accepted  
**Date:** 2026-07-10  
**Version:** 0.6.0

------------------------------------------------------------------------

## Problem

The first bundled generators (`bed_basic`, `wardrobe_basic`) worked well internally but created **many separate Blender objects** per furniture piece (posts, rails, mattress, doors, shelves, handles, …).

In Blender this is poor UX:

- Users must select many meshes to move one piece of furniture.
- Outliner clutter scales with component count.
- The logical “one bed / one wardrobe” is not visible in the scene graph.

We also considered grouping via a **root Empty** or **selection promotion** (click mesh → auto-select root). Both were rejected:

| Alternative | Why rejected |
|---|---|
| Root Empty | Technically clean, but users click the Empty—not the furniture mesh. Feels unnatural in Blender. |
| Selection promotion | Fragile, Blender-specific, adds complexity without fixing outliner clutter. |

------------------------------------------------------------------------

## Decision

Introduce a three-level model inside every generator run:

```
Furniture  →  Parts  →  Meshes (build-time only)
```

### Parts

- A **Part** is a logical sub-unit of furniture (e.g. `body`, `mattress`, `door_1`).
- During generation, a Part may create **any number of meshes** via the normal API (`create_box`, `create_label`, …).
- When the Part is closed (`end_part`) or at `finish()`, the API **finalizes** the Part into **exactly one Blender object** (join meshes today; extensible later).
- Final object name: `{params.name}_{part_id}` (e.g. `BED_120_body`, `WARDROBE_80_door_1`).

### Main Part

- Every furniture piece has exactly one **Main Part** (`main=True`, typically `body`).
- This is the object the user selects and moves in Blender.
- All other non-dynamic Parts are **parented to the Main Part** (world transform preserved).

### Dynamic Parts

- Moving elements (doors, drawers, hinges, castors) remain **separate Blender objects** after finalization (`dynamic=True`).
- They are also **parented to the Main Part** so translating the body moves the whole piece, while doors/drawers stay independently animatable.

> **Parenting direction:** Dynamic and static secondary Parts are **children of the Main Part**, not parents of it. This matches Blender’s transform hierarchy: move `body` → everything follows.

### Generator API lifecycle

Generators describe structure; the API performs finalization:

```python
api["begin_part"]("body", main=True, role="bed_frame")
# create_box / create_label …
api["end_part"]()

api["begin_part"]("door_1", dynamic=True, role="wardrobe_door")
# …
api["end_part"]()

api["finish"]()  # metadata, parenting, summary
```

Rules:

- **No `bpy.ops` in generators** — especially no `object.join()`.
- Join, metadata, parenting, and future post-processing (bbox, clearance, thumbnails) live in `layoutlab/api/parts.py`.
- Generators stay **component-oriented internally** (many meshes while building); they do **not** merge into monolithic meshes by hand.

### Metadata

On finalized Part objects:

| Property | Example | Meaning |
|---|---|---|
| `layoutlab_part` | `"body"` | Part id |
| `layoutlab_part_type` | `"main"` / `"static"` / `"dynamic"` | Part category |
| `layoutlab_component` | same as part id | Back-compat with v0.5.1 export |
| `layoutlab_role` | `"bed_frame"` | Fine-grained role from generator |

All Parts share the same `layoutlab_object_id` for regenerate/delete.

------------------------------------------------------------------------

## Consequences

### Positive

- One click on `body` moves the whole bed/wardrobe (children follow).
- Generators remain modular and readable.
- Finalization is centralized and evolvable without touching every generator.
- Dynamic Parts support future animation/rigging.

### Negative / migration

- **Breaking change for generator authors:** `create_box` during `execute_generator()` requires an active Part (`begin_part` first).
- Existing scenes with old multi-mesh beds remain valid; `regenerate` rebuilds with the new Part model.
- Move-by-single-mesh JSON command still moves one object; moving the logical furniture = move Main Part.

### Implementation

- `layoutlab/api/parts.py` — `PartSession`, `begin_part`, `end_part`, `finish`
- `layoutlab/engine/executor.py` — activates session, calls `finish()` after `generate()`
- `layoutlab/generators/bed_basic.py`, `wardrobe_basic.py` — migrated to Parts API

------------------------------------------------------------------------

## Related documents

- `docs/object_model.md` — Furniture → Parts → Meshes
- `docs/generator_api.md` — Part API reference
- `docs/how_to_write_generators.md` — author lifecycle and examples
