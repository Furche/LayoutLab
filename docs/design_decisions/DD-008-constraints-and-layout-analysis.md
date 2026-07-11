# DD-008 — Constraints and Layout Analysis

**Status:** Accepted  
**Date:** 2026-07-10  
**Accepted:** 2026-07-12  
**Version:** 0.8.0 (target)  
**Related:** [DD-007](DD-007-clearance-zones.md) (Clearance — input only) · [DD-006](DD-006-parts-and-finalization.md) (Parts)

------------------------------------------------------------------------

## Problem

LayoutLab can now **describe** usage zones (DD-007): generators emit clearances
with `required` / `preferred` labels and export `local_bounds` / `world_bounds`.

Nothing yet **evaluates** whether a layout satisfies those zones:

- Is the wardrobe front access blocked by another bed?
- Is a `preferred` bed entry partially obstructed (warning vs error)?
- Can ChatGPT ask “is this layout OK?” and get a structured answer?

Without a separate **Constraint / Analysis** layer, clearance metadata is inert
or gets misused (e.g. embedding pass/fail in export — rejected in DD-007).

------------------------------------------------------------------------

## Scope

### In scope (DD-008)

- Definition of **Constraint** vs **Clearance** (responsibility boundary)
- How `clearance.requirement` maps to analysis **severity**
- v1 **constraint types** and overlap rules
- `analyze_layout` JSON command — request/response contract
- v1 overlap algorithm (axis-aligned world bounds)
- Implementation order after acceptance
- First product test cases (wardrobe, then bed)

### Out of scope (future DDs / Phase E+)

- Walkway / navigation graph analysis
- Minimum corridor width along a path
- Scoring (“this layout is 73% good”)
- Physics collision
- Room boundary / wall detection (unless explicit room mesh in scene)
- Automatic layout repair / suggestion
- Constraints stored as persistent scene data (v1 derives checks from clearances)

**Rule:** The Constraint Engine **reads** clearances and geometry; it does **not**
create or modify clearance zones.

------------------------------------------------------------------------

## Decision

### 1. Responsibility split (unchanged from DD-007)

```
Generator     →  create_clearance()     →  descriptive zones
Export        →  layoutlab.clearance    →  local + world bounds
Analyzer      →  analyze_layout         →  findings (errors/warnings)
```

| Layer | Creates geometry? | Judges layout? |
|---|---|---|
| Clearance (DD-007) | Yes (wire zone) | No |
| Constraint (DD-008) | No | Yes |

### 2. What is a Constraint?

A **Constraint** is a **check rule** applied at analysis time. It references:

- One or more **Clearance Zones** (by `clearance_id` or `object_id` + `clearance_name`), and/or
- Scene **geometry** (other objects’ bounds)

It produces a **Finding** — never written back onto clearance export.

In v1, most constraints are **implicit**: one check template per clearance zone,
parameterized by that zone’s `requirement` label.

### 3. Mapping `requireance` → severity

Clearance carries declarative `requirement` (DD-007). The analyzer maps violations:

| Clearance `requirement` | Violation severity | Meaning |
|---|---|---|
| `required` | `error` | Functional impairment — zone blocked |
| `preferred` | `warning` | Usable but degraded |
| `informational` (future) | `info` | Optional note only; no fail |

**Rejected:** storing `severity` on the clearance mesh — duplicates responsibility.

### 4. v1 Constraint types

Explicit `constraint_type` strings in findings (extensible enum):

| Type | v1 | Description |
|---|---|---|
| `zone_must_be_clear` | **Yes** | Clearance `world_bounds` must not overlap blocking geometry |
| `minimum_free_width` | No | Needs path/corridor analysis |
| `required_access_path` | No | Needs graph reachability |
| `must_not_overlap_geometry` | **Alias** | Same as `zone_must_be_clear` in v1 (document as alias) |
| `headroom_clear` | No | Until vertical zone semantics defined |

v1 implements **`zone_must_be_clear` only** — one finding per violated clearance.

### 5. What counts as blocking geometry? (v1)

**Blockers:** exported `MESH` objects that:

- Have a `world_bounds` / bbox computable at analysis time, and
- Are **not** part of the same `layoutlab_object_id` as the clearance under test

**Included:** other furniture Main Parts, static Parts, dynamic Parts, standalone meshes.

**Excluded from overlap against clearance of object A:**

- All Parts sharing `A`’s `layoutlab_object_id` (body, mattress, own clearance wire, label)
- The clearance object itself

**Not in v1:** implicit room walls, floor beyond Z=0 plane, non-mesh blockers.

**Overlap test:** axis-aligned intersection of `world_bounds.min/max` (from DD-007 export
logic or recomputed at analysis). Any intersection volume > 0 → violation.

**Future:** overlap threshold, ignore thin mouldings, `informational` partial block.

### 6. `analyze_layout` command

#### Request

```json
{
  "action": "analyze_layout",
  "scope": "scene",
  "collection": "layout_tests",
  "include": ["clearances"]
}
```

| Field | Required | Default | Description |
|---|---|---|---|
| `scope` | no | `"scene"` | `"scene"` \| `"collection"` \| `"selection"` |
| `collection` | if scope=collection | — | Collection name |
| `include` | no | `["clearances"]` | v1: only `"clearances"` supported |

**Rejected for v1:** arbitrary constraint DSL in JSON — checks derive from exported clearances.

#### Response (console / command result)

```json
{
  "analyzed": true,
  "scope": "scene",
  "object_count": 12,
  "clearance_count": 1,
  "summary": {
    "errors": 1,
    "warnings": 0,
    "info": 0
  },
  "findings": [
    {
      "severity": "error",
      "constraint_type": "zone_must_be_clear",
      "message": "Required clearance 'front_access' on TEST_WARDROBE is blocked",
      "clearance_ref": {
        "object_id": "aa9f1113-45ad-4006-bab3-9f46c8f91742",
        "clearance_id": "c7e2…",
        "clearance_name": "front_access",
        "furniture_name": "TEST_WARDROBE"
      },
      "overlaps": [
        {
          "object_name": "TEST_BED_body",
          "object_id": "f9752e87-e35e-4c6f-aed7-f987b519e840",
          "part": "body"
        }
      ]
    }
  ]
}
```

| Field | Notes |
|---|---|
| `findings` | Empty list = no violations |
| `severity` | `error` \| `warning` \| `info` |
| `clearance_ref` | Always set for v1 findings |
| `overlaps` | Blocker objects; may be empty if check fails for other reasons |

Export schema **unchanged** — findings are analysis output only, never merged into `layoutlab.clearance`.

### 7. Analysis pipeline (v1)

```
1. Collect objects per scope
2. Build clearance list (objects with layoutlab_clearance_name + bounds)
3. Build blocker list (mesh objects with bounds, indexed by object_id)
4. For each clearance C:
     blockers = meshes where object_id ≠ C.object_id and AABB intersects C.world_bounds
     if blockers non-empty:
       emit finding(severity = map(C.requirement), overlaps = blockers)
5. Aggregate summary counts
```

Implementation module (proposed): `layoutlab/protocol/layout_analysis.py`

Reuse: `clearance_export.world_bounds_from_object`, `layoutlab_block_from_object`

### 8. Product test cases (implementation order)

After DD-008 accepted:

| Step | Work |
|---|---|
| 1 | `layout_analysis.py` — overlap + findings |
| 2 | Wire `analyze_layout` in `protocol/commands.py` |
| 3 | Diagnostic: wardrobe + bed overlap → expect error on `front_access` |
| 4 | Diagnostic: clear layout → zero findings |
| 5 | **`bed_basic`:** emit `bed_entry` clearance(s) per generator params (multi-zone) |
| 6 | Diagnostic: bed entry blocked vs clear |

**Wardrobe first** (step 3–4): `front_access` already exists — no generator change needed for initial analyzer test.

**Bed second** (step 5–6): product rules still TBD (left/right/both, child depth). DD-008 only requires that **when** a bed emits named zones, the analyzer treats them like any other clearance. Generator params example:

```json
{
  "clearances": [
    { "clearance_name": "bed_entry", "side": "left", "requirement": "preferred", "depth": 6.0 }
  ]
}
```

Bed generator logic stays in `bed_basic` — not in the analyzer.

### 9. Relationship to Future Ideas

| Future Idea | DD-008 stance |
|---|---|
| Walkway analysis | Deferred — needs graph, not v1 |
| Evaluation engine / scoring | Deferred — findings first, scores later |
| Constraint objects in scene | Deferred — derive from clearances in v1 |

Promote to new DD when a feature needs persistent constraint definitions independent of clearances.

------------------------------------------------------------------------

## Alternatives considered

| Alternative | Why rejected |
|---|---|
| Embed findings in scene export | Violates DD-007; stale on next export |
| Global constraint config file | Too early; clearances already carry `requirement` |
| Full Bullet/Blender collision | Overkill; semantic AABB sufficient for v1 |
| Single `analyze_layout` DD merged with DD-007 | Already rejected — split worked |
| Only check `required`, ignore `preferred` | Loses nuance; warnings useful for AI |

------------------------------------------------------------------------

## Consequences

- ChatGPT can run `analyze_layout` after placing furniture and read structured errors.
- `required` wardrobe front blocked by bed → `error`; `preferred` bed entry nudged → `warning`.
- New generators only need clearances; analyzer works without generator-specific code.
- Walkway/scoring remain out of scope until a follow-up DD.

------------------------------------------------------------------------

## Open questions (for review)

1. **Partial overlap:** Any intersection counts as violation in v1 — OK, or minimum overlap volume (e.g. 5% of clearance)?
2. **CURVE / label Parts:** Exclude from blockers (recommended: yes — only `MESH`)?
3. **Standalone JSON clearances** without `layoutlab_object_id`: include in analysis as orphan zones, or skip?
4. **`analyze_layout` in UI:** Sidebar button in v0.8, or JSON-only first?

------------------------------------------------------------------------

## Resolved decisions (review 2026-07-12)

| # | Question | Decision |
|---|---|---|
| 1 | Partial overlap | **Any AABB intersection volume > 0** counts as violation in v1 |
| 2 | Blocker types | **Only `MESH`** objects; exclude CURVE/FONT labels |
| 3 | Orphan clearances | **Include** in analysis (no `layoutlab_object_id` skip) |
| 4 | UI in v0.8 | **JSON-only first**; sidebar button deferred |

------------------------------------------------------------------------

## Implementation order (after DD-008 accepted)

| Step | Work |
|---|---|
| 1 | **This DD reviewed and accepted** |
| 2 | `layout_analysis.py` + `zone_must_be_clear` |
| 3 | `analyze_layout` command |
| 4 | Diagnostics (blocked + clear scenarios) |
| 5 | `bed_basic` multi-zone clearances |
| 6 | Bed + wardrobe combined layout diagnostic |

Do **not** implement walkway graph or scoring in the same release as v1 analyzer.

------------------------------------------------------------------------

## Document history

| Version | Date | Change |
|---|---|---|
| 0.1 | 2026-07-10 | Initial proposal — constraints separate from DD-007 clearances |
| 1.0 | 2026-07-12 | Accepted — review decisions resolved; v1 analyzer specified |
