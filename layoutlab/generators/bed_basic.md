# bed_basic

Generator reference for the JSON protocol and Generator Specification.

Version: 0.2 · Category: Beds

------------------------------------------------------------------------

## Purpose

Parametric low bed: corner posts, frame rails, mattress, headboard, footboard,
pillows, and a text label. Geometry is rebuilt from parameters — never scaled.

Source: `layoutlab/generators/bed_basic.py`

------------------------------------------------------------------------

## Coordinate Model

Aligns with `docs/units_and_coordinates.md`:

| Parameter | Axis | Meaning |
|---|---|---|
| `length` | X | Head-to-foot extent |
| `width` | Y | Side-to-side extent |
| `location` | XYZ | Min corner of footprint at floor (Z = floor) |
| `head_side` | — | Which edge has the headboard |

Sleeping direction is along **Y** when `head_side` is `y_max` or `y_min`.

------------------------------------------------------------------------

## Parameters

| Parameter | Default | Description |
|---|---|---|
| `name` | `"BED_basic"` | Prefix for all Blender object names |
| `location` | `[0, 0, 0]` | Footprint min corner |
| `length` | `20` | X extent; clamped to min `3` |
| `width` | `12` | Y extent; clamped to min `3` |
| `collection` | `"layout_tests"` | Blender collection |
| `head_side` | `"y_max"` | `y_max`, `y_min`, `x_max`, `x_min` |
| `leg_height` | `2.5` | Post height below frame |
| `frame_height` | `1.0` | Rail height |
| `mattress_height` | `2.0` | Mattress thickness |
| `rail_thickness` | `0.35` | Max 20% of width/length |
| `post_size` | `0.45` | Max 25% of width/length |
| `mattress_inset` | `0.45` | Max 20% of width/length |
| `headboard_height` | `4.2` | — |
| `footboard_height` | `2.2` | — |
| `frame_color` | `[0.72, 0.55, 0.35, 1]` | RGBA |
| `mattress_color` | `[0.86, 0.86, 0.82, 0.65]` | RGBA semi-transparent |
| `pillow_color` | `[0.95, 0.95, 0.92, 1]` | RGBA |

------------------------------------------------------------------------

## Rules and Fallbacks

| Condition | Behaviour |
|---|---|
| `width >= 13` (130 cm) | Two pillows |
| `width < 13` | One pillow |
| `rail_thickness`, `post_size`, `mattress_inset` | Capped relative to bed size |
| Missing params | Sensible defaults (no exception) |

Not implemented (future generators):

- Slats (Lattenrost)
- Centre support for very long beds (> 400 cm)
- Loft / bunk variants

------------------------------------------------------------------------

## Parts (v0.6)

Final Blender objects after generator run:

| Part id | Type | Final object name | Contents (joined build meshes) |
|---|---|---|---|
| `body` | **main** | `{name}_body` | 4 posts, 4 rails, headboard, footboard |
| `mattress` | static | `{name}_mattress` | mattress volume |
| `pillow_1`, `pillow_2` | static | `{name}_pillow_1`, … | one pillow each |
| `label` | static | `{name}_label` | text curve |

Build meshes use `{name}__{part}_{detail}` during generation (double underscore).

Static Parts are parented to `body`. User moves `{name}_body` to move the whole bed.

### Roles on build meshes / Parts

| Detail | `layoutlab_role` |
|---|---|
| Corner posts (×4) | `bed_post` |
| Frame rails (×4) | `bed_frame` |
| Mattress | `bed_mattress` |
| Headboard | `bed_headboard` |
| Footboard | `bed_footboard` |
| Pillows | `bed_pillow` |
| Label | `label` |

------------------------------------------------------------------------

## Components (legacy note)

Prior to v0.6 each row above was a separate Blender object. v0.6 joins them per Part — see `docs/object_model.md`.

------------------------------------------------------------------------

## Return Value

```json
{
  "created": "BED_120x200",
  "type": "bed_basic",
  "size": [12, 20]
}
```

`size` is `[length, width]` in Blender units.

------------------------------------------------------------------------

## Examples

### Standard 120 × 200 cm

```json
{
  "action": "run_generator",
  "generator": "bed_basic",
  "params": {
    "name": "BED_120x200",
    "location": [0, 0, 0],
    "length": 12,
    "width": 20,
    "head_side": "y_max",
    "collection": "layout_tests"
  }
}
```

### Single 90 × 200 cm (one pillow)

```json
"params": { "name": "BED_90x200", "length": 9, "width": 20 }
```

------------------------------------------------------------------------

## Known Limitations

- Label is a separate CURVE object; not part of collision geometry
- Magic sizing constants in code (pillow placement, mattress Z offset) — acceptable for v0.1 reference generator
- Slats, centre support, loft variant — not in this generator (see `docs/how_to_write_generators.md` §13.4 for loft pattern)

## Semantic metadata (v0.6)

Part objects receive `layoutlab_object_id`, `layoutlab_part`, `layoutlab_part_type`, etc. at `finish()`.  
Update in place: JSON `regenerate` command (see `docs/json_protocol.md` §5.12).

------------------------------------------------------------------------

## JSON Protocol Reference

See `docs/json_protocol.md` §5.1
