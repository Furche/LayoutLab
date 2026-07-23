# DD-021 — Advanced Support Surfaces and Stacking (WP-07)

**Status:** Accepted  
**Date:** 2026-07-23  
**Accepted:** 2026-07-23  
**Version:** 1.0  
**Related:** [FC-001](../concepts/FC-001-semantic-direct-manipulation-and-multi-room-editing.md) · [DD-019](DD-019-semantic-direct-manipulation.md) · [DD-002](DD-002-generators-rebuild-mesh.md) · [DD-018](DD-018-semantic-transactions-and-authority.md) · [ROADMAP](../ROADMAP.md) Active WP-07

------------------------------------------------------------------------

## Acceptance note

**Accepted 2026-07-23** (Alexander). Locked defaults:

1. **On-surface test:** footprint **centre** must lie in the host surface (not full containment).
2. **Host delete:** keep dangling `support_ref` + `INVALID_NO_SUPPORT`; **no** auto-floor.
3. **MVP child:** new minimal **`lamp_basic`** generator.
4. **Host resize / scale:** child keeps its surface-local offset and may become
   **`INVALID_OFF_SUPPORT`** (“lost” from the host) — same no-silent-repair spirit as (2).
   Never clamp/snap the child back onto the surface. Host **move/rotate** still
   **follows** via explicit `support_local_xy`.

------------------------------------------------------------------------

## Decision summary (Accepted)

Furniture stays attached via semantic `support_ref`, not free-float Z hacks.
WP-07 extends the MVP `room_floor` relation to **named host surfaces on other
furniture** (first: desk `surface_top` + lamp). Children follow host move/rotate;
invalid support is visible, never silently repaired. No physics stacking,
no wall/ceiling mounts in this milestone.

------------------------------------------------------------------------

## Problem

Today `support_ref = room_floor` and `move` clamps Z to room origin Z
([DD-019](DD-019-semantic-direct-manipulation.md)). Real layouts need objects on
other objects (lamp on desk). Without a binding support model:

- Z becomes ad-hoc mesh editing (breaks regenerate / analysis / AI Apply);
- host move leaves children behind or requires silent repair;
- validity has no language for “off the table but still in the room”.

------------------------------------------------------------------------

## Scope

### In scope (WP-07 MVP)

- `support_ref` grammar beyond `room_floor`
- Host **horizontal surfaces** declared by generators (`desk_basic` → `surface_top`)
- `lamp_basic` as MVP child
- Place / reparent via Core (`set_support` / `place_on`) + transactions
- Z derived from support surface
- XY validated by centre-in-surface
- Host move / rotate: children **follow** (`support_local_xy`)
- Host resize / regenerate: offset preserved; may become `INVALID_OFF_SUPPORT`
- Host delete: dangling ref + `INVALID_NO_SUPPORT`
- Viewer: inspector shows support; minimal place affordance
- Export: `support_ref`, `support_local_xy`, surface metadata

### Out of scope

- Physics stacking; wall/ceiling mounts; multi-floor
- Full footprint containment; auto-clamp onto surface
- Free Z without support; CAD constraint solver

------------------------------------------------------------------------

## Decision

### 1. Core statement

> **Support is a semantic relation. World Z (and support validity) is a
> deterministic projection of `support_ref` + host surface + child pose.
> LayoutLab never invents a new support or silently re-floors / re-snaps an
> object to “fix” a broken attachment.**

### 2. `support_ref` grammar

| Form | Meaning |
|---|---|
| `room_floor` | Z = room origin Z; XY vs room footprint |
| `object:<host_object_id>#<surface_id>` | Child on named surface of host furniture |

MVP `surface_id`: `surface_top`.

### 3. Host surfaces (generator contract)

```text
layoutlab_surfaces = [
  {
    "id": "surface_top",
    "kind": "horizontal",
    "local_z": <float>,
    "local_min_xy": [x0, y0],
    "local_max_xy": [x1, y1]
  }
]
```

Surfaces survive regenerate (DD-002): same `id`, recomputed from params.

### 4. Pose projection + `support_local_xy`

- Explicit **`support_local_xy`** on the child (surface-local frame).
- World XY/Z projected from host pose + surface + `support_local_xy`.
- Authoring `move` while on a host updates `support_local_xy` from the new world XY
  (then reprojects Z).
- **Centre-in-surface** decides `VALID` vs `INVALID_OFF_SUPPORT`.

### 5. Participation

| Host change | Child with this support |
|---|---|
| move / rotate_z | **Follow** — reproject from `support_local_xy` (+ inherit host Δrz on child rz) |
| resize / regenerate | Keep `support_local_xy`; reproject; may become **`INVALID_OFF_SUPPORT`** |
| delete | Keep world pose + dangling `support_ref` → **`INVALID_NO_SUPPORT`** |
| hide | Child visibility unchanged (own flags) |

### 6. Validity

| Code | When |
|---|---|
| `VALID` | Centre on surface (or floor rules) and existing room rules pass |
| `INVALID_OFF_SUPPORT` | Host/surface exists; centre outside surface |
| `INVALID_NO_SUPPORT` | Host or surface missing |
| `INVALID_OUTSIDE_ROOM` / `INVALID_INTERSECTS_WALL` | Unchanged |

Membership preserved. Red states are commitable (DD-019).

### 7. Commands

- `set_support` — `{ object_id, support_ref }` (+ optional `support_local_xy`)
- `place_on` — `{ object_id, host_object_id, surface_id, location? }`
- `move` — honours active `support_ref`

All via DD-018. No Viewer-only parenting.

### 8. Viewer (minimal)

Inspector shows support; invalid → red validity styling; place affordance as needed.

------------------------------------------------------------------------

## Alternatives rejected

| Option | Why not |
|---|---|
| Free Z as authority | Breaks semantic path |
| Auto-floor on host delete | Silent repair |
| Clamp child onto surface after resize | Silent repair (“lost” must stay visible) |
| Physics / wall mounts | Later |

------------------------------------------------------------------------

## Implementation slices

1. Protocol + Core grammar, `desk_basic` surfaces, `lamp_basic`, `set_support` / `place_on`
2. Follow + validity + tests
3. Viewer inspector / minimal UX
4. Docs + version bump
