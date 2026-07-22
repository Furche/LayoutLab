# DD-019 — Semantic Direct Manipulation

**Status:** Accepted
**Date:** 2026-07-22
**Accepted:** 2026-07-22
**Version:** 1.0
**Related:** [FC-001](../concepts/FC-001-semantic-direct-manipulation-and-multi-room-editing.md) · [DD-002](DD-002-generators-rebuild-mesh.md) · [DD-010](DD-010-room-model.md) · [DD-018](DD-018-semantic-transactions-and-authority.md) · [DD-020](DD-020-spatial-project-independent-rooms.md)

------------------------------------------------------------------------

## Acceptance note

**Accepted 2026-07-22** (Alexander). Locked defaults:

- Wall-hosted **fixed elements** follow opening-like **inactive** (not delete) semantics.
- **Duplicate room includes** invalid associated furniture and inactive openings/fixed elements.
- WP-03 starts **single-select**; multi-select follows once that path is stable.

FC-001/WP-03…WP-05 implement against this DD (after DD-018 for commits).

------------------------------------------------------------------------

## Decision summary (Accepted)

Viewport editing updates **semantic LayoutLab state**, not raw meshes. Furniture
moves/rotates in room XY / around Z with a support relation (`support_ref`, MVP =
`room_floor`). Resize changes generator parameters and regenerates (DD-002). Wall
moves preserve furniture world positions; invalid furniture stays assigned and
turns red. Openings stay wall-hosted; swallowed openings become inactive, not
deleted. No silent repair.

Product behaviour detail remains in FC-001; this DD locks architectural
invariants and schema ownership for the manipulation path.

------------------------------------------------------------------------

## Problem

Users must edit rooms and furniture directly. If the Viewer or Blender treats
meshes as authoritative, LayoutLab loses regenerate, analysis, planning and AI
Apply consistency.

FC-001 already defines behaviour. Missing is a binding architecture choice:
where transforms live, how invalidity relates to membership, and that
manipulation commits only via DD-018 transactions.

------------------------------------------------------------------------

## Scope

### In scope

- Semantic vs mesh editing boundary
- Furniture transform + `support_ref` (MVP floor)
- Parametric resize / regeneration
- Wall/corner edit effects on furniture and openings
- Invalid vs inactive states
- Fixed elements on walls (inactive when swallowed)
- Duplicate semantics for invalid membership

### Out of scope

- Transaction/Undo machinery (DD-018)
- Multi-room project container (DD-020) — single-room ops must work first
- Advanced supports / stacking (FC-001/WP-07)
- Shared-wall topology, polygons as first milestone
- Full CAD constraint solver

------------------------------------------------------------------------

## Decision

### 1. Core statement

> **Direct manipulation mutates semantic domain properties. Runtime geometry is a
> deterministic projection. Invalid and inactive states preserve data; LayoutLab
> never silently repairs, relocates or deletes to “fix” a manual edit.**

### 2. Schema ownership

| Concern | Owner |
|---|---|
| Furniture pose, `support_ref`, membership, validity | Core semantic objects |
| Generator params + regenerate | Generators + engine (DD-001/002) |
| Walls, openings, fixed fabric | Room Model (DD-010) extended by ops in WP-05 |
| Preview/commit of edits | DD-018 transactions |
| Binding field names | Contracts at WP-03…WP-05 |

### 3. Furniture manipulation (MVP)

- Select; translate in room XY; rotate about Z.
- `support_ref = room_floor` (semantic attachment, not a hard-coded `z = 0` only).
- Later supports (`table.surface_top`, shelves, walls, ceiling) are allowed by the
  model but **not** in WP-03/04.
- User may commit invalid (red) positions; validity recalculates after changes.
- Orange “functionally weak” feedback may use soft metrics; it does not block commit.

### 4. Parametric resize

- Handles / numeric fields edit **generator parameters**.
- Object regenerates (DD-002). Naive mesh scale is not semantic resize.
- Unusual but constructible dimensions are accepted with documented generator
  fallbacks/warnings — not silent substitution of standard sizes.
- Preview may use simplified geometry; full regenerate on commit (DD-018).

### 5. Wall / boundary edits and furniture

When a wall moves (enlarge or shrink):

- Furniture **world** positions are preserved (not auto-arranged or scaled).
- If the room-local origin changes, local furniture transforms are recomputed so
  world pose stays invariant.
- Furniture that intersects a wall or lies outside remains **assigned** to the
  room and becomes **invalid** (e.g. `INVALID_INTERSECTS_WALL`, `INVALID_OUTSIDE_ROOM`).
- When fully valid again, validity returns to `VALID` automatically.

Membership, validity and transform participation remain distinct (FC-001 §5;
whole-room move rules apply once DD-020 room transforms exist — for single-room
MVP, room move still uses the same participation rules).

### 6. Openings

- Openings are hosted by a stable `wall_id` with offset/width/height/… and `state`.
- Host wall parallel move: openings move with the wall; offset unchanged.
- Adjacent walls lengthen/shorten; openings on those walls keep **world** position;
  `offset_along_wall` is recomputed.
- If an opening falls beyond the remaining segment: not deleted; `INACTIVE_OUTSIDE_WALL`;
  hidden in render; restored automatically when the wall is long enough again.

### 7. Fixed elements

Wall-hosted fixed elements (e.g. radiators) follow **opening-like host rules**:

- move with host wall;
- world-position / offset recomputation on adjacent shortening;
- become **inactive** (not deleted) when swallowed by shortening;
- restore when geometry allows.

If a fixed element is not wall-hosted, treat it like furniture for world-preserve
and invalidity during boundary edits.

### 8. Duplicate

- Duplicate room or furniture assigns new stable IDs and rewrites internal refs.
- **Duplicate room includes invalid but still associated furniture** and inactive
  openings/fixed elements (data-preserving; user can clean up).
- Duplicate does not copy unrelated world orphans from other rooms.

### 9. Common flags

Rooms and furniture support hide/show, analysis include/exclude, edit lock, and
`protected_from_ai` as separate properties (FC-001 §9). Manipulation ops honour
`locked`; AI Apply honour `protected_from_ai` (DD-018).

------------------------------------------------------------------------

## Alternatives considered

| Alternative | Why rejected |
|---|---|
| Mesh editing as source of truth | Breaks regenerate, analysis, AI |
| Auto-repair on wall shrink | Violates FC-001 preserve-intent |
| Delete swallowed openings | Data loss; FC-001 forbids |
| Fixed Z=0 without `support_ref` | Blocks later surfaces; brittle |
| Mesh scale for “resize” | Conflicts DD-002 |

------------------------------------------------------------------------

## Consequences

**Positive**

- Direct edit path stays aligned with generators and analysis.
- Invalid/inactive model enables fearless wall editing.

**Trade-offs**

- Validation and visualisation cost on every boundary commit.
- Generators must document resize fallbacks clearly.

**Follow-on**

- WP-03 furniture select/move/rotate; WP-04 parametric resize; WP-05 walls/openings.
- Requires DD-018 for commit-based gestures.

------------------------------------------------------------------------

## Resolved review questions

1. **Duplicate includes invalid** — yes (Accepted).
2. **Fixed elements → inactive** — yes, opening-like (Accepted).
3. **WP-03 selection** — single-select first; multi-select as follow-up.

------------------------------------------------------------------------

## Implementation order (after Accept)

1. Depends on DD-018 for commit boundary.
2. WP-03 → WP-04 → WP-05 as in FC-001 (WP-05 may proceed after DD-018 + this DD
   without waiting for WP-04).
3. Update `room_model.md` / object contracts / tests with each WP.

------------------------------------------------------------------------

## History

| Ver | Date | Note |
|---|---|---|
| 0.1 | 2026-07-22 | Proposed — FC-001/WP-01 decomposition |
| 1.0 | 2026-07-22 | **Accepted** — duplicate+invalid; fixed inactive; single-select WP-03 |
| 1.1 | 2026-07-22 | WP-03 implemented in Core `0.10.37` (select/move/rotate_z/dup/delete/hide/lock + validity) |
| 1.2 | 2026-07-22 | WP-04 implemented in Core `0.10.38` (`regenerate` / `set_parameter` / `resize`) |
