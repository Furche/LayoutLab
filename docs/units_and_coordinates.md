# Units and Coordinates

Version: 0.9.3

> Defines how LayoutLab interprets space in Blender scenes.
> Required reading before writing generators, JSON commands, or interpreting scene export.

**Status markers:**

- `[IMPLEMENTED]` — used in v0.5 prototype today
- `[PLANNED]` — agreed convention, not yet enforced by plugin
- `[CONVENTION]` — project standard for the reference room; not auto-detected

------------------------------------------------------------------------

# 1. Overview

LayoutLab uses **Blender scene units** for all coordinates and dimensions.
Values in JSON commands and scene export are **never auto-converted** to
centimetres or metres by the plugin.

Real-world meaning comes from a **project convention** that agents and
generators must respect explicitly.

------------------------------------------------------------------------

# 2. Scale Convention

## 2.1 LayoutLab units `[IMPLEMENTED]`

Protocol, JSON commands, generator params, and scene export use **LayoutLab units**:

```
1 LayoutLab unit = 10 cm = 0.1 m
```

Examples:

| Real size | LayoutLab units |
|---|---|
| 120 cm | `12` |
| 200 cm | `20` |
| 35 cm | `3.5` |
| 2.5 m ceiling | `25` |
| 75 cm radiator | `7.5` |

## 2.2 Adaptation to scene units `[IMPLEMENTED]`

The plugin **does not change** Blender scene unit settings. It converts at the geometry boundary:

```
bu = ll * 0.1 / scale_length
ll = bu * scale_length / 0.1
```

| Scene `scale_length` | Meaning | `height: 7.5` becomes |
|---|---|---|
| `1.0` (fresh default) | 1 BU = 1 m | `0.75` BU ≈ 75 cm |
| `0.1` | 1 BU = 10 cm | `7.5` BU (identity) |

Applied in `create_box`, `create_quad`, `create_label`, `move`, and clearance placement. Export reports LayoutLab units again, plus:

```json
"scale_convention": "1_unit_equals_10cm",
"bu_per_ll_unit": 0.1,
"unit_scale": 1.0
```

**Old reference scenes** that were modelled as 10 cm per BU while leaving `scale_length=1.0` should set **Unit Scale = 0.1** once (meshes unchanged, display correct, conversion factor = 1).

## 2.3 Formal Enforcement `[IMPLEMENTED]` (partial)

| Feature | Status |
|---|---|
| `scale_convention` / `bu_per_ll_unit` in scene export | `[IMPLEMENTED]` |
| LL ↔ BU conversion on create/export | `[IMPLEMENTED]` |
| Validation warning on unit mismatch | `[PLANNED]` |
| Generator params in real-world units (cm) with separate conversion layer | Not needed — LL units are the protocol |

**Decision:** keep LayoutLab units end-to-end in JSON; adapt mesh size to the active scene.

------------------------------------------------------------------------

# 3. Coordinate System

## 3.1 Axes `[IMPLEMENTED]` (Blender standard)

```
        Z  (up / height)
        │
        │
        └────── Y
       /
      /
     X
```

| Axis | Typical use in LayoutLab |
|---|---|
| **X** | Room width / object length (along X) |
| **Y** | Room depth / object width (along Y) |
| **Z** | Height (floor = Z 0) |

Right-handed coordinate system. Rotations use Blender Euler angles in degrees
on export (`rotation_euler_deg`).

## 3.2 Floor Plane `[CONVENTION]`

- Floor is at **Z = 0** unless the scene deliberately offsets the room.
- Furniture `location[2]` is typically `0` — objects are placed on the floor.
- Vertical dimensions (leg height, mattress thickness) extend in +Z.

## 3.3 Room Origin `[CONVENTION]`

- Room origin (0, 0, 0) is a **fixed corner of the reference room** — not auto-defined by the plugin.
- AI must use exported object positions relative to existing geometry, not assume origin placement.
- Formal room boundary export `[PLANNED]`.

------------------------------------------------------------------------

# 4. Object Placement

## 4.1 Location Semantics `[IMPLEMENTED]`

`location: [x, y, z]` in JSON commands and generator params is the **world-space
minimum corner** of the furniture footprint on the floor — the anchor of the
**Main Part** after finalization.

```
params.location  →  Main Part object origin (world) after join
                 →  all generator math uses absolute world coords from this point
```

Generators compute Part build meshes in **world coordinates** (each `create_box`
location is absolute). The Part API parents non-main Parts to the Main Part and
converts their transforms to **local space** without changing world position.

See `layoutlab/api/transforms.py` — `parent_preserve_world_transform`.

### Parts coordinate model (v0.6.1) `[IMPLEMENTED]`

| Stage | Coordinate space |
|---|---|
| Generator `create_box` / `create_label` | World (absolute from `params.location`) |
| After `end_part()` join | World (each Part is an independent object) |
| After `finish()` parenting | Child Parts: local relative to Main Part; world unchanged |
| User moves Main Part | Entire furniture follows (children inherit transform) |

**Regenerate policy:** `regenerate` rebuilds from stored `params.location`. A
manual move of the Main Part is **not** preserved unless `params.location` is
updated. No double offset on regenerate — only a possible jump back to param location.

## 4.2 Location Semantics — create_box `[IMPLEMENTED]`

```
create_box(name, [x, y, z], [dx, dy, dz])
         origin ──→ extends +X by dx, +Y by dy, +Z by dz
```

Not the centre of the object. Not the room centre.

## 4.3 Dimensions `[IMPLEMENTED]`

`dimensions: [dx, dy, dz]` — size along X, Y, Z respectively.

Always positive values. Rotation changes world orientation but export reports
axis-aligned bounding box dimensions.

## 4.4 Rotation `[IMPLEMENTED]`

- `rotate_z` command rotates around the object's origin (Z axis, degrees).
- Full 3-axis rotation `[PLANNED]`.
- Generators in v0.5 do not rotate — they align to axes. Use `rotate_z` after generation.

------------------------------------------------------------------------

# 5. Furniture Conventions

## 5.1 Bed (bed_basic) `[IMPLEMENTED]`

Reference generator defining axis usage for sleeping furniture:

| Parameter | Axis | Meaning (default orientation) |
|---|---|---|
| `length` | X | Head-to-foot direction length |
| `width` | Y | Side-to-side width |
| `location` | XYZ | Min corner of bed footprint at floor |
| `head_side` | — | Which edge has the headboard |

### head_side values

| Value | Headboard location |
|---|---|
| `"y_max"` | High Y edge (default) |
| `"y_min"` | Low Y edge |
| `"x_max"` | High X edge |
| other / `"x_min"` | Low X edge |

### Construction heights (v0.5)

Only posts touch the floor. The frame loop (side rails, footboard, structural headboard
base) sits at `location[2] + leg_height` with height `frame_height`. The decorative
headboard panel (`headboard_height`) rises above that frame top. See
`layoutlab/generators/bed_basic.md`.

### Standard bed sizes (reference room, 1 unit = 10 cm)

| Name | length (X) | width (Y) | Real size |
|---|---|---|---|
| Single 90×200 | `9` | `20` | 90 × 200 cm |
| Standard 120×200 | `12` | `20` | 120 × 200 cm |
| Queen 140×200 | `14` | `20` | 140 × 200 cm |
| King 180×200 | `18` | `20` | 180 × 200 cm |

Example from v0.5 quick test / command template:

```json
"location": [68.3, 197.7, 0],
"length": 12,
"width": 20
```

→ 120×200 cm bed at room position (683 cm, 1977 cm) from origin `[CONVENTION]`.

## 5.2 General Furniture `[PLANNED]`

Future generators should document their axis mapping in generator docstrings:

```
length → X, width → Y, height → Z   (default convention)
```

Deviations must be stated explicitly in `GENERATOR_DESCRIPTION`.

------------------------------------------------------------------------

# 6. Collections and Layers

## 6.1 Default Collection `[IMPLEMENTED]`

| Collection | Purpose |
|---|---|
| `layout_tests` | Default for generators and test geometry |

Override via `"collection"` param in commands and generator params.

## 6.2 Room Structure `[PLANNED]`

```
Room
├── layout_structure   (walls, floor, ceiling)
├── layout_furniture   (beds, wardrobes, …)
├── layout_clearance   (invisible clearance zones)
└── layout_annotations (labels, dimensions)
```

v0.5 uses a flat collection model.

------------------------------------------------------------------------

# 7. Clearance Conventions

## 7.1 Clearance Boxes `[IMPLEMENTED]`

- Created via `create_clearance` action or manually with `role: "clearance"`.
- Default: thin in Z (`dimensions[2] = 0.1`), wireframe display.
- Semantically 2D footprint zones on the floor — height is visual only in v0.5.

## 7.2 Standard Clearances `[PLANNED]`

| Zone | Typical size | Purpose |
|---|---|---|
| Bed access side | 70 cm (`7` units) | Adult can walk beside bed |
| Door swing | door width + 10 cm | Opening arc |
| Wardrobe front | 80 cm (`8` units) | Standing access |

Generators will emit these automatically `[PLANNED]`.

------------------------------------------------------------------------

# 8. Export and JSON

## 8.1 Exported Fields `[IMPLEMENTED]`

Scene export includes:

```json
{
  "unit": "METRIC",
  "unit_scale": 1.0,
  "scale_convention": "1_unit_equals_10cm",
  "bu_per_ll_unit": 0.1,
  "note": "Coordinates/dimensions are LayoutLab units (1 unit = 10 cm). …"
}
```

- `location`, `dimensions`, `world_bbox_corners` — LayoutLab units (converted from scene BU).
- `rooms[]` model fields — LayoutLab units (source of truth, not re-derived from mesh).

## 8.2 AI Interpretation Rules

1. Treat all command and export coordinates as LayoutLab units (1 = 10 cm).
2. Read `bu_per_ll_unit` only if you need raw Blender mesh sizes.
3. Use `world_bbox_corners` for collision and spacing calculations.
4. Use `custom_properties.layoutlab_role` to identify component types.
5. When generating commands, output LayoutLab units — the plugin adapts to the scene.

------------------------------------------------------------------------

# 9. Common Mistakes

| Mistake | Correct approach |
|---|---|
| Sending centimetre values as if they were LL units | Divide cm by 10 → LayoutLab units |
| Using object centre as `location` | Use min corner (bottom-left at floor) |
| Scaling generated mesh instead of changing params | Change generator params and re-run |
| Assuming Z floor at non-zero | Check exported object Z values first |
| Mixing head_side without checking orientation | Read existing bed export or ask |
| Expecting scene Unit Scale to be forced to 0.1 | Plugin adapts; set Unit Scale=0.1 only for old 10cm-BU scenes |

------------------------------------------------------------------------

# 10. Changelog

| Version | Date | Changes |
|---|---|---|
| 0.9.3 | 2026-07-17 | Scene-unit adaptation: LL↔BU via `scale_length`; export `scale_convention` |
| 0.6.1 | 2026-07-10 | Parts parenting coordinate model; regenerate location policy |
| 0.5.0 | 2026-07-09 | Initial document based on v0.5 prototype and reference room |

## References

- `docs/json_protocol.md` §7
- `docs/design_decisions/DD-002-generators-rebuild-mesh.md`
- `layoutlab_chatgpt_helper_v05.py` — `bed_basic` template, `layout_export_json`
