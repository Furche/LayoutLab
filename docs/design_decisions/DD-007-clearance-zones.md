# DD-007 — Clearance Zones

**Status:** Accepted  
**Date:** 2026-07-10  
**Version:** 0.7.0 (target)  
**Related:** [DD-006](DD-006-parts-and-finalization.md) (Parts) · **Not** [DD-008](DD-008-constraints-and-layout-analysis.md) (Constraints — separate)

------------------------------------------------------------------------

## Problem

LayoutLab furniture already emits **usage volumes** in ad-hoc form:

- `wardrobe_basic` builds a wireframe `clearance` Part in front of the carcass
- JSON `create_clearance` creates standalone wire boxes with `layoutlab_role = "clearance"`

There is no shared **semantic model** for these zones:

- naming is inconsistent (`clearance` vs future `bed_entry`)
- meaning of dimensions and placement is implicit in generator code
- export does not describe zones in a machine-readable way
- there is no distinction between **describing** a zone and **judging** a layout

If we combine “zone geometry” and “layout rules” in one design, we risk locking
in an `analyze_layout` API before the clearance schema is stable.

------------------------------------------------------------------------

## Scope

### In scope (DD-007)

- Definition of a **Clearance Zone** as furniture-generated, semantically named volume
- Identity, metadata, coordinates, and export schema
- Relationship to the **Parts** model (DD-006)
- Direction for `create_clearance()` as the central generator API
- Implementation order

### Out of scope (→ DD-008)

- Constraint types (`must_be_clear`, `minimum_free_width`, …)
- Layout quality / pass-fail evaluation
- `analyze_layout` command and return format
- Walkway graphs, collision engines, scoring

**Rule:** A Clearance Zone does **not** state whether a layout is good or bad.
That is the job of a **Constraint Engine** (DD-008), which **reads** clearances.

------------------------------------------------------------------------

## Decision

### 1. What is a Clearance Zone?

A **Clearance Zone** is a **semantically named usage volume** produced by a
generator (or JSON command) on behalf of a furniture piece.

It describes **how space around the object is intended to be used**, not
physical solid geometry.

Example `clearance_name` values (conventions, not a closed enum — **short names,
reused across furniture instances**):

| `clearance_name` | Typical purpose |
|---|---|
| `front_access` | Space in front of doors to open and stand |
| `door_swing` | Arc or box swept by a door leaf |
| `bed_entry` | Preferred approach side at mattress height |
| `chair_pullout` | Space to pull a chair back from a desk |
| `headroom` | Vertical clearance above sleeping surface |

Many wardrobes may all use `front_access`. Names stay semantic; uniqueness is
scoped to the owning furniture instance (see §2).

### 2. Clearance identity

Three related identifiers:

| Field | Scope | Description |
|---|---|---|
| `clearance_id` | **Globally unique** | Technical id, auto-generated (UUID or stable hash) |
| `clearance_name` | **Unique per `object_id`** | Semantic name within one furniture instance |
| Composite ref | — | `object_id` + `:` + `clearance_name` for internal references |

**Uniqueness rule:** `(object_id, clearance_name)` must be unique.

Example addressing:

```json
{
  "object_id": "aa9f1113-45ad-4006-bab3-9f46c8f91742",
  "clearance_name": "front_access",
  "clearance_id": "c7e2…"
}
```

Composite reference string (internal / logs): `aa9f1113-…:front_access`

**Rejected:** globally unique `clearance_name` values such as `wardrobe_17_front_access`
— they obscure semantics and force artificial suffixes.

### 3. What a Clearance describes

Each zone carries **descriptive** metadata:

| Field | Meaning |
|---|---|
| **Shape** | v1: axis-aligned box; long-term: general shape model (see §9) |
| **Local placement** | Transform **relative to Main Part** coordinate system |
| **Purpose** | Intent category (e.g. `door_access`, `sleep_entry`) |
| **Priority** | Relative importance when zones compete (integer; higher = more important) |
| **Requirement** | Declarative severity label — interpretation in DD-008 |

#### Requirement labels (v1)

Do **not** use `hard` / `soft` on the same axis as semantic purpose — they mix
“how mandatory” with “what the zone means.”

| Value | Meaning (declarative) |
|---|---|
| `required` | Violation = functional impairment (e.g. door cannot open) |
| `preferred` | Violation possible but reduces usability (e.g. comfortable standing room) |

**Later (optional):** `informational` — zone for documentation only, no constraint.

A single furniture piece may emit **overlapping zones** at different requirement
levels (e.g. wardrobe: `door_swing` = `required`, `front_access` = `preferred`).

### 4. Clearance is not a Constraint

```
Generator  →  emits Clearance Zone(s)     [DD-007]
Analyzer   →  evaluates Constraint rules    [DD-008]
```

| Layer | Responsibility |
|---|---|
| **Generator** | Knows object-specific rules for *where* zones belong; builds geometry + metadata |
| **Clearance API** | Creates consistent wire volumes, Parts, and metadata |
| **Constraint Engine** | Reads clearances + scene geometry; reports violations / warnings |

Never embed layout verdicts inside clearance creation.

### 5. Relationship to Parts (DD-006)

Clearance zones are **static Parts** parented to the Main Part:

```
WARDROBE_80_body (main)
  ├─ WARDROBE_80_clearance_front_access   layoutlab_part: clearance_front_access
  └─ WARDROBE_80_clearance_door_swing     layoutlab_part: clearance_door_swing
```

v1 rules:

- One Part per logical zone; `part_id` may mirror `clearance_name` (e.g. `clearance_front_access`)
- Display: `WIRE`, `show_in_front = True`
- **Local shape data is relative to Main Part**, not to the clearance mesh origin

Alternative rejected for v1: metadata-only without mesh — wireframes aid debugging.

### 6. Flexible generator-side zone definitions

Generators declare **multiple named zones** with parameters. No engine-fixed
“bed entrance” rule.

Example generator params (illustrative):

```json
{
  "clearances": [
    {
      "clearance_name": "bed_entry",
      "side": "left",
      "requirement": "preferred",
      "depth": 6.0
    }
  ]
}
```

**Bed caution:** Entry side, depth, foot-end access — product decisions for
`bed_basic` + DD-008. `bed_basic` adopts clearances only after wardrobe reference
implementation (step 9).

### 7. Metadata on Clearance Parts (v1)

Custom properties on finalized clearance objects:

| Property | Type | Description |
|---|---|---|
| `layoutlab_role` | string | `"clearance"` |
| `layoutlab_clearance_id` | string | Globally unique id |
| `layoutlab_clearance_name` | string | Semantic name; unique per `object_id` |
| `layoutlab_clearance_purpose` | string | Intent category |
| `layoutlab_clearance_requirement` | string | `required` \| `preferred` |
| `layoutlab_clearance_priority` | int | Default `0` |
| `layoutlab_clearance_params` | string (JSON) | Generator-specific params (`side`, `depth`, …) |

Inherited: `layoutlab_object_id`, `layoutlab_generator`, `layoutlab_part`, `layoutlab_part_type`.

### 8. Central API: `create_clearance()`

Replace ad-hoc `create_box(..., role="clearance", display_type="WIRE")` with:

```python
api["create_clearance"](
    name,
    local_location,
    dimensions,
    clearance_name="front_access",
    purpose="door_access",
    requirement="preferred",
    priority=0,
    params={"depth": 6.0},
    collection="layout_tests",
)
```

- `local_location` / dimensions expressed in **Main Part local space** (API converts to world for mesh creation during generation)
- Assigns `clearance_id` automatically
- JSON command `create_clearance` calls the same internal helper

### 9. Shape and coordinates

#### v1: box + bounds

Export and internal storage use **both** local and world bounds:

```json
{
  "clearance_id": "c7e2…",
  "clearance_name": "front_access",
  "object_id": "aa9f1113-…",
  "requirement": "preferred",
  "purpose": "door_access",
  "local_bounds": {
    "min": [0.0, -6.0, 0.0],
    "max": [8.0, 0.0, 20.0]
  },
  "world_bounds": {
    "min": [99.0, 199.0, 0.0],
    "max": [107.0, 205.0, 20.0]
  }
}
```

| Coordinate set | Role |
|---|---|
| **Local bounds** | Semantic truth of the furniture piece; stable under move/rotate of Main Part; used for regenerate and debugging |
| **World bounds** | Computed at export time; used for overlap checks, room distance, ChatGPT export, diagnostics |

**Critical:** Local bounds/transform are relative to the **Main Part coordinate
system**, not the clearance mesh object origin.

#### Long-term: general shape model

Bounds alone are insufficient for door swings and rotated zones. Target schema:

```json
{
  "shape": "box",
  "local_transform": {
    "location": [0, -6, 0],
    "rotation": [0, 0, 0],
    "dimensions": [8, 6, 20]
  }
}
```

v1 may export boxes via bounds; implementation should not block migrating to
`shape` + `local_transform` without breaking `clearance_id` / naming rules.

### 10. Export schema (v1)

Per clearance Part in scene export:

```json
{
  "name": "WARDROBE_80_clearance_front_access",
  "layoutlab": {
    "object_id": "aa9f1113-…",
    "part": "clearance_front_access",
    "clearance": {
      "clearance_id": "c7e2…",
      "clearance_name": "front_access",
      "purpose": "door_access",
      "requirement": "preferred",
      "priority": 0,
      "params": { "depth": 6.0 },
      "shape": "box",
      "local_transform": {
        "location": [0, -6, 0],
        "rotation": [0, 0, 0],
        "dimensions": [8, 6, 20]
      },
      "local_bounds": { "min": [0, -6, 0], "max": [8, 0, 20] },
      "world_bounds": { "min": [99, 199, 0], "max": [107, 205, 20] }
    }
  }
}
```

Export remains **descriptive only** — no `status: fail` or constraint results.

------------------------------------------------------------------------

## Alternatives considered

| Alternative | Why rejected |
|---|---|
| Merge clearance + constraints in one DD | Too much architecture too early |
| Globally unique `clearance_name` | Obscures semantics; suffix pollution |
| `hard` / `soft` requirement labels | Ambiguous; conflates severity with purpose |
| Local bounds only | Insufficient for scene analysis |
| World bounds only | Unstable for regenerate / furniture-relative semantics |
| Metadata-only, no mesh | Harder to debug in Blender |

------------------------------------------------------------------------

## Consequences

- Wardrobe may emit `front_access` + `door_swing` with different `requirement` levels.
- Export carries furniture-relative **and** scene-absolute geometry.
- DD-008 references clearances by `clearance_id` or `(object_id, clearance_name)`.
- `bed_basic` clearances deferred to implementation step 9.

------------------------------------------------------------------------

## Implementation order

Do **not** start `analyze_layout` until DD-008 is accepted.

| Step | Work | Status |
|---|---|---|
| 1 | README / release tag | Done |
| 2 | DD-007 accepted | **Done** |
| 3 | `create_clearance()` in `layoutlab/api/` | Done |
| 4 | Refactor `wardrobe_basic` (reference: `front_access`, optional `door_swing`) | Done |
| 5 | Export schema for clearances | |
| 6 | Diagnostics for clearance metadata + export | |
| 7 | DD-008: Constraints and layout analysis | |
| 8 | `analyze_layout` | |
| 9 | `bed_basic` multi-zone clearances | |

------------------------------------------------------------------------

## Resolved decisions (2026-07-10)

| Question | Decision |
|---|---|
| Name uniqueness | `clearance_name` unique per `object_id`; `clearance_id` globally unique |
| Requirement labels | `required` \| `preferred`; later optional `informational` |
| Export coordinates | Both `local_bounds` and `world_bounds`; local relative to Main Part |
| Shape evolution | Long-term `shape` + `local_transform`; v1 box acceptable |

------------------------------------------------------------------------

## Document history

| Version | Date | Change |
|---|---|---|
| 0.1 | 2026-07-10 | Initial proposal |
| 1.0 | 2026-07-10 | Accepted — identity, requirement, coordinates resolved |
