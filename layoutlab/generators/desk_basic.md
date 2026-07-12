# desk_basic Generator

## Purpose

`desk_basic` is the third canonical LayoutLab generator — a simple parametric desk
with tabletop, four legs, and an optional **chair-access clearance** zone.

It validates that Parts, `create_clearance`, and `analyze_layout` work for a new
object type without generator-specific analyzer code.

Source: `layoutlab/generators/desk_basic.py`

## Metadata

```python
GENERATOR_NAME = "desk_basic"
GENERATOR_CATEGORY = "Work"
GENERATOR_VERSION = "0.1.0"
```

## Parts

| Part id | Type | Final object | Contents |
|---|---|---|---|
| `body` | **main** | `{name}_body` | tabletop + four legs (joined) |
| `clearance_chair_access` | static | `{name}_clearance_chair_access` | chair zone (`chair_access`, optional) |
| `label` | static | `{name}_label` | text label |

## Coordinate Convention

- `location` is the min corner of the desk footprint at floor level.
- `width` extends along +X.
- `depth` extends along +Y.
- `height` is desktop height along +Z.
- **Front / sitting side** is **`y_min`** (local y = 0).

Clearance `chair_access` sits in **−Y** from the front edge — the space where a
chair is pulled out.

In Alexander's reference room convention, `1 unit ≈ 10 cm`.

## Component Roles (build meshes)

| Role | Build content |
|---|---|
| `desk_top` | tabletop panel |
| `desk_leg` | corner legs |
| `clearance` | chair-access zone |
| `label` | text label |

## Parameters

| Parameter | Default | Description |
|---|---:|---|
| `name` | `"DESK_basic"` | Prefix for all Part object names |
| `location` | `[0, 0, 0]` | Min corner at floor |
| `width` | `12.0` | Desktop width (X), min 4 |
| `depth` | `6.0` | Desktop depth (Y), min 3 |
| `height` | `7.5` | Desktop height (Z), min 5 (~75 cm) |
| `top_thickness` | `0.25` | Tabletop thickness |
| `leg_thickness` | `0.4` | Square leg cross-section |
| `show_clearance` | `true` | Emit `chair_access` zone |
| `clearance_depth` | `6.0` | Chair pull-out depth in −Y |
| `clearance_height` | `7.0` | Zone height from floor (knee/sitting space) |
| `clearance_requirement` | `"required"` | DD-007 label → `error` in analyze when blocked |
| `collection` | `"layout_tests"` | Blender collection name |

## Clearance

| Field | Value |
|---|---|
| `clearance_name` | `chair_access` |
| `purpose` | `seating_access` |
| `requirement` | `required` (default) |
| `local_location` | `[0, -clearance_depth, 0]` |
| `dimensions` | `[width, clearance_depth, clearance_height]` |

Unlike `wardrobe_basic` (`front_access`, `preferred`), the desk uses **`required`**
by default — a blocked chair zone is a functional impairment.

## Example JSON

```json
{
  "action": "run_generator",
  "generator": "desk_basic",
  "params": {
    "name": "DESK_120x60",
    "location": [68.3, 175.0, 0],
    "width": 12,
    "depth": 6,
    "height": 7.5,
    "show_clearance": true,
    "collection": "reference_kids_room"
  }
}
```

## Limits

- No drawers, cable management, or adjustable height — future params or separate generator.
- Legs are simple boxes at corners; no apron panels.
- Single clearance zone only (`chair_access`).
