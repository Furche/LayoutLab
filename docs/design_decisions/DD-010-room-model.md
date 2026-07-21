# DD-010 — Room Model (Single Space)

**Status:** Accepted  
**Date:** 2026-07-16  
**Accepted:** 2026-07-16
**Version:** 1.0  
**Related:** [DD-003](DD-003-json-only-communication.md) · [DD-006](DD-006-parts-and-finalization.md) · [DD-007](DD-007-clearance-zones.md) · [DD-008](DD-008-constraints-and-layout-analysis.md) · [DD-009](DD-009-ai-execution-boundary.md) · [Future_Ideas.md](../Future_Ideas.md) §13 / §17 · [room_model.md](../room_model.md) · [FC-001](../concepts/FC-001-semantic-direct-manipulation-and-multi-room-editing.md)

------------------------------------------------------------------------

## Acceptance note

**Accepted 2026-07-16** (Alexander — proceed to implementation).

Binding: Room Model (B), not Room Generator; typed scalable footprint; MVP rectangle;
first-class walls/openings/fixed; proposed defaults locked. MVP shipped in plugin **v0.9.0**.

------------------------------------------------------------------------

## Problem

LayoutLab’s Execution Layer can create and analyse **furniture** (generators, Parts,
clearances, `analyze_layout`). The **room** itself is still an accident of Blender:

- Alexander’s reference kids room is hand-modelled meshes (`floor`, `walls`, `door`,
  `window`, `heizung`) with no LayoutLab identity or edit API
- Fixtures and AI workflows assume coordinates in that scene, but cannot
  *author* or *reproduce* the space through the protocol
- Long-term capture sources (measures, floor plan, scan, video) need a **shared
  internal representation** — not “whatever meshes happen to be in the .blend”

Two approaches were considered:

| | **A — Room Generator** | **B — Room Model** |
|---|---|---|
| Analogy | `bed_basic` / `run_generator` | Durable domain state + mutate ops |
| Lifecycle | Params → rebuild whole room | Create → edit → sync to runtime |
| Fit for capture/import | Reconstruct params, regenerate | Write into same model |
| Edit story | Awkward for moving one window | Natural: `update_opening`, … |

**Choice:** **B**. A room is not furniture. Rooms become complex (non-rectangular
plans, many openings, fixed fabric). Starting simple is fine; the **schema and
operations must scale** without a second architecture.

------------------------------------------------------------------------

## Scope

### In scope (DD-010)

- Decision: **Room Model** over Room Generator for space authoring
- Responsibility split: Room Model vs furniture generators vs clearances vs analysis
- Conceptual entities for a **single space** (one room)
- **Scalability principles** (simple MVP, extensible footprint / fabric)
- MVP entity set and operation families (contract-level, not full JSON schema yet)
- Relationship to Blender runtime (adapter, not source of truth)
- What success looks like for replacing the hand-modelled reference room
- Implementation order **after** acceptance

### Out of scope (this DD)

- Standalone app, mobile scanner, LiDAR, floor-plan OCR, CAD/IFC import
- Multi-room apartments, shared walls, multi-floor buildings (Future_Ideas §13 / §17 stages 2–3)
- Layout variants as first-class project objects (future DD-011)
- Full rewrite of `analyze_layout` (room-as-blocker may follow; not required to *accept* this DD)
- Changing DD-007 / DD-008 responsibility split
- Binding JSON field names (may be sketched; finalised in `json_protocol.md` at implementation)

------------------------------------------------------------------------

## Decision

### 1. Core statement

> **A room is an editable LayoutLab domain model (Room Model), not a furniture
> generator. Geometry in Blender is a runtime projection of that model.
> Capture and import paths will eventually write into the same model.**

Furniture generators (`bed_basic`, …) stay unchanged: they create furniture
objects *inside* a space; they do not own walls or openings.

**Follow-on concept:** FC-001 specifies the product behaviour for semantic wall
editing, temporary invalid states, Undo/Redo and multiple independent rooms. It
extends this accepted single-space foundation and requires separate DDs before
implementation; it does not amend DD-010's current contract.

### 2. Responsibility split

```
Room Model     →  walls, openings, fixed fabric, room bounds / height
Furniture gens →  beds, wardrobes, desks (Parts, clearances)
Export         →  layoutlab.room (+ existing furniture / clearance blocks)
Analyzer       →  reads room + furniture + clearances (later room blockers)
```

| Layer | Creates room fabric? | Creates furniture? | Judges layout? |
|---|---|---|---|
| Room Model (DD-010) | **Yes** | No | No |
| Generators (DD-001…) | No | **Yes** | No |
| Clearance (DD-007) | No | Zones on furniture | No |
| Analysis (DD-008) | No | No | **Yes** (reads all) |

### 3. Scalability first, simplicity second

Rooms can be arbitrarily complex. MVP must stay small, but **must not** hard-code
“a room is always one regenerated box.”

#### 3.1 Footprint is typed and versioned

| Phase | Footprint | Notes |
|---|---|---|
| **MVP** | `rectangle` | `width`, `depth`, origin, optional rotation about Z |
| **Next** | `polygon` | Ordered floor vertices (CCW), still single storey |
| **Later** | Multi-contour / holes | Courtyards, pillars as holes — separate extension |

Store `footprint.kind` explicitly (`"rectangle"` | `"polygon"` | …). Clients and
export must not assume rectangle forever.

#### 3.2 Walls are first-class (even when derived)

MVP may **derive** four walls from a rectangle footprint for convenience.

Architecturally:

- Each **Wall** has a stable `wall_id`
- Openings and fixed elements **attach to walls** (or to room + wall ref), not to
  anonymous mesh faces
- Later: freeform wall graphs, non-vertical partitions, split walls — without
  renaming the entity

**Rejected for Core:** “walls exist only as Blender meshes with no ids.”

#### 3.3 Openings and fixed elements are first-class

- **Opening:** `door` | `window` (extensible enum) — host wall, offset along wall,
  width, height, sill height (windows), optional swing/side metadata later
- **Fixed element:** at least `radiator`; later columns, shafts, built-ins via
  same attachment pattern (`fixed_kind` + params)

#### 3.4 Identity and editing

| Field | Scope |
|---|---|
| `room_id` | Globally unique (UUID) |
| `wall_id` / `opening_id` / `fixed_element_id` | Unique within room (or globally — decide at impl; prefer UUID) |

Edits mutate the model; the runtime adapter **rebuilds or updates** display meshes.
Prefer **idempotent sync** from model → scene over silent mesh editing as truth.

#### 3.5 What “Room Generator” may still mean (narrow)

Optional later: **geometry helpers** that turn Opening/Fixed params into meshes
(similar to Parts) — *not* `run_generator("room_basic")` as the room’s source of
truth. Naming: avoid calling the Room Model a “generator” in APIs.

### 4. MVP entity set (sufficient to replace reference room)

Enough to reproduce Alexander’s kids room shell (≈ 4.2 × 2.18 m, door, window,
radiator) via protocol:

| Entity | MVP fields (conceptual) |
|---|---|
| **Room** | `room_id`, name, `footprint` (`kind: rectangle`, width, depth), `height`, origin / transform, unit note |
| **Wall** | `wall_id`, room ref, segment (or edge index on footprint), thickness (default ok) |
| **Opening** | `opening_id`, `kind` door/window, `wall_id`, offset, width, height, sill (window) |
| **FixedElement** | `fixed_element_id`, `kind` radiator, `wall_id`, offset, width, depth, height |

Ceiling/floor may be **derived** display meshes from footprint + height — no need
for separate authoring entities in MVP.

### 5. MVP operation families

Illustrative action names (final names in `json_protocol.md` at implementation):

| Family | MVP | Later (same model) |
|---|---|---|
| Room | `create_room`, `update_room` (size/height/origin), `delete_room` | polygon footprint |
| Openings | `add_opening`, `update_opening`, `remove_opening` | arches, French doors, … |
| Fixed | `add_fixed_element`, `update_fixed_element`, `remove_fixed_element` | columns, shafts |
| Walls | Optional: expose derived walls read-only in export | `split_wall`, `move_wall`, explicit `add_wall` for polygons |

**MVP may omit** free `add_wall` / `move_wall` if rectangle footprint implies four walls.
When footprint becomes polygon, wall ops become essential — design export and ids
so that transition does not break opening refs.

### 6. Blender runtime adapter

- Blender remains primary Execution Runtime (DD-009)
- Room Model is **LayoutLab Core** data; meshes are adapter output
- Suggested collection / roles: e.g. collection `layoutlab_room`, roles
  `room_floor`, `room_wall`, `room_opening`, `room_fixed` (exact names at impl)
- Manual meshes in collection `room` remain valid **legacy / import** input until
  migrated; they are not the long-term contract

### 7. Export

Scene export gains a structured **`layoutlab.room`** (or top-level `rooms[]`) block:

- room identity + footprint + height
- walls with ids and segments / bounds
- openings and fixed elements with host wall refs
- world bounds suitable for future analysis

Descriptive only — no pass/fail (same rule as clearance export, DD-007).

### 8. Relationship to `analyze_layout`

DD-008 v1 stays valid (furniture vs furniture).

**After** Room Model ships and exports bounds:

- Analyzer **may** treat walls / fixed fabric as blockers or “outside room” checks
- That extension can be a follow-up to this DD or a small DD-008 amendment —
  **not** a reason to delay Accepting the Room Model itself

### 9. Success criterion (product)

A JSON command batch creates a room equivalent (for planning purposes) to the
current hand-modelled reference kids room:

- footprint and height match Blender units (Metric: 1 unit = 1 m)
- door on east wall, window on west wall, radiator on west wall
- furniture fixtures (`bed_basic`, `desk_basic`, …) still use existing generators
- no requirement for the old anonymous `walls` / `floor` meshes

------------------------------------------------------------------------

## Alternatives considered

| Alternative | Why rejected / deferred |
|---|---|
| **A — `room_basic` generator** | Wrong lifecycle; poor edit/capture story; encourages “regenerate whole room” |
| Full Property / Building model now | Scope explosion; Future_Ideas stage 2–3; separate later DDs |
| Room = Blender collection conventions only | No Core model; cannot leave Blender cleanly |
| Walls only as mesh, no ids | Breaks stable opening attachment and import merge |
| Polygon-only from day one | Correct long-term, heavier MVP; rectangle is OK **if** `footprint.kind` is extensible |
| Merge room fabric into Clearance/Constraint layers | Violates DD-007/008 splits |

------------------------------------------------------------------------

## Consequences

- New protocol surface and Core module(s) after acceptance
- `object_model.md` gains a real Room branch (not narrative-only)
- Reference fixtures migrate from hand meshes → room commands
- Furniture generators unchanged
- Future capture pipelines have a clear write target
- DD-010 **narrows** the earlier Future_Ideas reservation “DD-010 Project and Spatial Model” to **single-space Room Model**; apartment/building remain future DDs

------------------------------------------------------------------------

## Open questions (for review)

1. **Wall thickness / material:** defaults only in MVP, or required params?
2. **Opening cuts:** semantic bbox on wall sufficient for analysis v1, or must display mesh be boolean-cut?
3. **Coordinate frame:** room-local origin at SW corner (min X/Y) vs world coords only?
4. **Persistence:** model stored only as Blender custom props / text block vs sidecar JSON in project — decide at impl?
5. **Foreign furniture:** existing IKEA meshes stay outside Room Model (yes recommended) — document as non-LayoutLab objects?
6. **`create_room` vs import-from-selection:** classify selected Blender meshes into Room Model in MVP or later?

------------------------------------------------------------------------

## Proposed resolved defaults (subject to review)

| # | Question | Proposed default |
|---|---|---|
| 1 | Footprint MVP | `rectangle` + explicit `footprint.kind` |
| 2 | Walls in MVP | Derived from footprint, stable `wall_id`s, exported |
| 3 | Opening display | Box/slab placeholder OK; boolean cut optional later |
| 4 | Origin | Room origin = footprint min corner at floor Z; openings in wall-local params |
| 5 | IKEA / foreign meshes | Not part of Room Model; analysis may still see them as MESH blockers |
| 6 | Analyze room blockers | **After** room export works — not blocking for Accept |

------------------------------------------------------------------------

## Implementation order (after Accepted)

| Step | Work |
|---|---|
| 1 | This DD reviewed and **Accepted** |
| 2 | Update `object_model.md`, `json_protocol.md`, `documentation_map.md`; optional `docs/room_model.md` |
| 3 | Core room data structures + validation (pure Python where practical) |
| 4 | JSON commands + Blender adapter (create/update/sync meshes) |
| 5 | Export `layoutlab.room` + diagnostic check |
| 6 | Reference kids room fixture as room commands |
| 7 | (Follow-up) `analyze_layout` uses room walls/fixed as blockers |

**Do not start steps 3–7 while status is Proposed.**

------------------------------------------------------------------------

## Document history

| Version | Date | Change |
|---|---|---|
| 0.1 | 2026-07-16 | Initial proposal — Room Model (B) over Room Generator (A); scalable footprint; MVP for reference room |
| 1.0 | 2026-07-16 | **Accepted** — defaults locked; implementation started |

------------------------------------------------------------------------

## Review checklist

- [x] Accept Room Model (B), reject Room Generator as source of truth
- [x] Accept scalability rule: typed footprint, first-class walls/openings/fixed
- [x] Accept MVP = rectangle + openings + radiator, no multi-room
- [x] Agree open-question defaults or revise
- [x] Status → **Accepted** before any implementation
