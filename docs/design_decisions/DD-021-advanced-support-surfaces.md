# DD-021 — Advanced Support Surfaces and Stacking (WP-07)

**Status:** Proposed  
**Date:** 2026-07-23  
**Version:** 0.1 (draft — not coding until Accepted)  
**Related:** [FC-001](../concepts/FC-001-semantic-direct-manipulation-and-multi-room-editing.md) · [DD-019](DD-019-semantic-direct-manipulation.md) · [DD-002](DD-002-generators-rebuild-mesh.md) · [DD-018](DD-018-semantic-transactions-and-authority.md) · [ROADMAP](../ROADMAP.md) Active WP-07

------------------------------------------------------------------------

## Decision summary (Proposed)

Furniture stays attached via semantic `support_ref`, not free-float Z hacks.
WP-07 extends the MVP `room_floor` relation to **named host surfaces on other
furniture** (first: table/desk top). Children follow host transform participation
rules; invalid support is visible, never silently repaired. No physics stacking,
no wall/ceiling mounts in this milestone.

------------------------------------------------------------------------

## Problem

Today `support_ref = room_floor` and `move` clamps Z to room origin Z
([DD-019](DD-019-semantic-direct-manipulation.md)). Real layouts need objects on
other objects (lamp on desk, box on shelf). Without a binding support model:

- Z becomes ad-hoc mesh editing (breaks regenerate / analysis / AI Apply);
- host move leaves children behind or requires silent repair;
- validity has no language for “off the table but still in the room”.

FC-001 already reserved the extension; WP-07 needs locked architecture before code.

------------------------------------------------------------------------

## Scope

### In scope (WP-07 MVP)

- `support_ref` grammar beyond `room_floor`
- Host **horizontal surfaces** declared by generators (first host: desk/table top)
- Place / reparent child onto a host surface (Core command + transaction)
- Z derived from support surface (not user-free vertical drag as authority)
- XY move constrained or validated against support footprint
- Host move / rotate / resize / regenerate: children with that support **follow**
- Validity when off-surface, host missing, or host inactive/hidden
- Viewer: select child, optional “place on …” / drop-on-surface affordance (minimal)
- Export: `support_ref` + enough surface metadata for Viewer feedback

### Out of scope (explicitly later)

- Physics-based stacking / collision piles
- Wall mounts, ceiling mounts, multi-floor
- Nested stacks deeper than needed for MVP demos (allow chain, but no special UI)
- Arbitrary free Z without a support
- Full CAD constraint solver / snap-to-every-edge polish
- New furniture catalog beyond one host + one small child demo path

------------------------------------------------------------------------

## Decision (proposed locks)

### 1. Core statement

> **Support is a semantic relation. World Z (and optional XY validity) is a
> deterministic projection of `support_ref` + host surface + child pose.
> LayoutLab never invents a new support or silently re-floors an object to
> “fix” a broken attachment.**

### 2. `support_ref` grammar

| Form | Meaning |
|---|---|
| `room_floor` | Current MVP — Z = room origin Z; XY vs room footprint |
| `object:<host_object_id>#<surface_id>` | Child sits on named surface of host furniture |

**Proposed surface_id for MVP:** `surface_top` (desk/table).

Rejected alternatives:

- Opaque string soup without host id (cannot follow host / validate)
- Hard-coded `z = 0.75` in generators (breaks resize / regenerate)
- Parenting only in Viewer Three.js (bypasses Core — forbidden by FC-001)

### 3. Host surfaces (generator contract)

Generators that expose a support surface stamp **stable surface metadata** on the
Main Part (or a dedicated part), e.g.:

```text
layoutlab_surfaces = [
  {
    "id": "surface_top",
    "kind": "horizontal",
    "local_z": <float>,          # top plane in object local space
    "local_min_xy": [x0, y0],    # support footprint in local XY
    "local_max_xy": [x1, y1]
  }
]
```

Exact JSON field names land in `json_protocol.md` / `object_model.md` at
implementation. Surfaces survive regenerate (DD-002): recomputed from params,
same `id`.

**MVP host:** extend `desk_basic` (already has a clear top).  
**MVP child:** any small floor object (e.g. existing generator or a minimal lamp
stub) — prefer reuse over a new catalog item unless needed.

### 4. Pose projection

When `support_ref = object:<host>#surface_top`:

- Child **world Z** = host world surface plane Z (from host pose + `local_z`).
- Child **XY** remains authorable; after each move/rotate, validity checks whether
  the child’s support sample point (default: footprint centre) lies inside the
  host surface footprint (world).
- Child **rotation_z** is independent (MVP); optional “inherit host rz delta”
  only when the host rotates and the child **follows** (see §5).

`move` with floor support keeps today’s Z clamp. `move` with object support
updates XY and reprojects Z from the surface.

### 5. Participation (host changes)

When the host moves / rotates_z / resizes / regenerates:

| Child state | Behaviour |
|---|---|
| `support_ref` points at this host + surface | **Follow** — reproject pose from support (same relative local offset on surface) |
| Other / floor | Unchanged |

Relative offset on surface is stored implicitly as child local XY in **host
surface local frame** (recommended) or recomputed each time from world — pick one
at implement time; prefer **explicit local offset on surface** for stable resize.

If host is **deleted**: children keep world pose, `support_ref` cleared? **No** —
proposed: keep `support_ref` string, mark validity `INVALID_NO_SUPPORT` (or
equivalent), still visible. User re-homes or deletes. No auto-floor.

If host is **hidden**: children remain; visibility policy = child’s own flag
(host hide does not force-hide children in MVP).

### 6. Validity

Extend beyond room footprint / walls:

| Code (proposed names) | When |
|---|---|
| `VALID` | Sample point on surface (or on floor for `room_floor`) and existing room rules |
| `INVALID_OFF_SUPPORT` | Support exists but sample outside surface footprint |
| `INVALID_NO_SUPPORT` | Host/surface missing |
| existing `INVALID_OUTSIDE_ROOM` / `INVALID_INTERSECTS_WALL` | Unchanged |

Off-support does **not** drop room membership. User may commit red states
(DD-019).

Room XY validity while on a host: still evaluated (object can be on a desk that
itself is outside the room).

### 7. Commands (Core)

Proposed additions / extensions (names TBD in protocol):

- `set_support` — `{ object_id, support_ref }` then reproject Z
- `move` — honour active `support_ref` (already partial for floor)
- Optional: `place_on` — `{ object_id, host_object_id, surface_id, location? }` convenience

All via DD-018 preview/commit. No Viewer-only parenting.

### 8. Viewer (minimal)

- Selecting a child shows support in inspector (`room_floor` vs host name/surface).
- Drag on floor vs drag while “snap/place on host” — MVP may be command/button
  first; gizmo drop-target can follow if cheap.
- Invalid support → existing red validity styling.

### 9. Analysis / planning

- Soft metrics / clearances: child clearances remain in world space.
- `plan_layout` / recipes: **no** requirement to place stacked objects in WP-07
  MVP unless a tiny demo fixture helps tests.
- AI tools: expose `support_ref` + `set_support` / `place_on` in tool contract when
  commands land.

------------------------------------------------------------------------

## Alternatives considered

| Option | Why not (for WP-07) |
|---|---|
| Free Z drag as authority | Breaks semantic regenerate / AI; DD-019 already rejected fixed Z=0 without support |
| Blender parenting only | Viewer/Core diverge; FC-001 forbids viewport-only authority |
| Full shelf system + wall mounts | Scope explosion; do after horizontal host works |
| Physics stacking | Out of product mental model for this phase |

------------------------------------------------------------------------

## Open questions (need Accept locks)

1. **Sample point for on-surface test:** footprint centre vs full footprint containment?
   **Recommendation:** centre-in-surface for MVP (simple); full containment later.
2. **Host delete:** keep dangling `support_ref` + `INVALID_NO_SUPPORT` vs clear to
   `room_floor`? **Recommendation:** dangling + invalid (no silent repair).
3. **MVP child object:** reuse existing generator vs tiny `lamp_basic`?
   **Recommendation:** reuse if any small object exists; else minimal lamp stub.
4. **Relative offset storage:** explicit `support_local_xy` on child vs derive each
   time? **Recommendation:** explicit `support_local_xy` (stable under host resize).

------------------------------------------------------------------------

## Implementation slices (after Accept)

1. Protocol + Core: grammar, surfaces stamp on `desk_basic`, `set_support` / move Z
2. Follow participation + validity codes + tests
3. Viewer inspector + minimal place affordance
4. Docs (`json_protocol`, `object_model`, HANDOFF) + version bump

------------------------------------------------------------------------

## Acceptance

**Not accepted yet.** Coding for WP-07 starts only after this DD is **Accepted**
with the open questions locked (or explicitly deferred).
