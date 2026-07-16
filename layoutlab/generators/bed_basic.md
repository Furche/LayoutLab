# bed_basic

Generator reference for the JSON protocol and Generator Specification.

Version: 0.6 · Category: Beds

------------------------------------------------------------------------

## Purpose

Parametric low bed built as a **logical construction stack**: corner posts on the
floor, a raised frame loop, optional decorative headboard above the frame, mattress,
pillows, and a text label. Geometry is rebuilt from parameters — never scaled.

Source: `layoutlab/generators/bed_basic.py`

------------------------------------------------------------------------

## Construction Model (v0.5)

Only the **four corner posts** reach the floor. Everything else sits on the raised
frame band or above it.

```
floor (Z = location[2])
│
├── posts                    leg_height + frame_height (support frame corners)
│
├── frame loop @ frame_bottom_z (= floor + leg_height)
│   ├── side rails (×4)
│   ├── footboard            height = frame_height  (structural end panel)
│   └── headboard base       height = frame_height  (structural end panel)
│
├── headboard rise (optional) @ frame_top_z (= frame_bottom + frame_height)
│   └── decorative panel     height = headboard_height
│
├── mattress                 separate Part
├── pillows                  separate Part(s)
└── label                    separate Part
```

This matches a classic timber bed: posts carry a closed perimeter frame; the
decorative headboard is an extension above that frame, not a second panel from the floor.

### Why not place end boards on the floor?

If the footboard and headboard started at floor level while side rails sit at
`leg_height`, the frame would not form a closed loop at one height — posts would
appear to “pierce” through floating side rails. v0.5 aligns all frame members on
`frame_bottom_z`.

### Future variants

The `BedConstruction` class in the generator is the extension point for:

| Future Part | Stack position |
|---|---|
| Lattenrost (slats) | inside frame loop, below mattress |
| Storage drawers | under frame loop or beside posts |
| Loft / bunk | additional platform Part above frame |
| Tall headboard variants | parametric rise panels or separate `headboard_style` |

New generators should reuse this **stack thinking** rather than scattering absolute Z values.

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
| `location` | `[0, 0, 0]` | Footprint min corner at floor |
| `length` | `20` | X extent; clamped to min `3` |
| `width` | `12` | Y extent; clamped to min `3` |
| `collection` | `"layout_tests"` | Blender collection |
| `head_side` | `"y_max"` | `y_max`, `y_min`, `x_max`, `x_min` |
| `leg_height` | `2.5` | Post height **below** the frame loop (posts still extend through frame band to `frame_top`) |
| `frame_height` | `1.0` | Height of the **frame loop** (side rails, footboard, structural headboard base) |
| `mattress_height` | `2.0` | Mattress thickness |
| `rail_thickness` | `0.35` | Frame member thickness; max 20% of width/length |
| `post_size` | `0.45` | Post cross-section; max 25% of width/length |
| `headboard_height` | `3.2` | **Decorative headboard rise above frame top** (`frame_top_z`). Set `0` for frame-only head end. Alias: `headboard_rise` |
| `frame_color` | `[0.72, 0.55, 0.35, 1]` | RGBA — posts, frame loop, headboard rise |
| `mattress_color` | `[0.86, 0.86, 0.82, 0.65]` | RGBA semi-transparent |
| `pillow_color` | `[0.95, 0.95, 0.92, 1]` | RGBA |

### Clearances (v0.6, DD-007/008)

Optional `clearances` array — wire zones parented to `body`, checked by `analyze_layout`.

| Field | Default | Description |
|---|---|---|
| `clearance_name` | `"bed_entry"` | Semantic name (unique per bed) |
| `side` | `"foot"` | Approach side — see below |
| `depth` | `0.6` | Extension beyond bed edge (meters) |
| `requirement` | `"preferred"` | `required` \| `preferred` |
| `purpose` | `"bed_access"` | Intent label |

**`side` when `head_side` is `y_max`:** `foot` (−Y), `head` (+Y), `left`/`x_min` (−X), `right`/`x_max` (+X).

```json
"clearances": [
  { "clearance_name": "bed_entry", "side": "foot", "requirement": "preferred", "depth": 6.0 }
]
```

Omit `clearances` for no zones (backward compatible).

### Removed / deprecated (v0.5)

| Parameter | Status |
|---|---|
| `footboard_height` | **Removed** — footboard is a frame member with height `frame_height` |
| `mattress_inset` | Unused in code (mattress inset follows `rail_thickness`); kept for forward compatibility in JSON only |
| `headboard_height` (pre-0.5) | **Semantic change** — was height from floor; now rise above frame top. Old JSON values need review. |

### Height reference diagram

```
Z
│     ┌─ headboard rise (headboard_height)
│     │
├─────┴─ frame_top_z  ─── top of posts / frame loop
│ ████  frame band (frame_height) — rails + end boards
│
├─────── frame_bottom_z (= floor + leg_height)
│
│ ████  post (only element touching floor below frame_bottom)
│
└─────── floor_z (= location[2])
```

**Total headboard visual height from floor** = `leg_height + frame_height + headboard_height`.

------------------------------------------------------------------------

## Rules and Fallbacks

| Condition | Behaviour |
|---|---|
| `width >= 13` (130 cm) | Two pillows side-by-side along mattress length (X) at head/foot |
| `width < 13` | One pillow |
| `headboard_height <= 0` | No decorative rise mesh; structural headboard base remains |
| `rail_thickness`, `post_size` | Capped relative to bed size |
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
| `body` | **main** | `{name}_body` | 4 posts, 4 side rails, footboard, headboard base, optional headboard rise |
| `mattress` | static | `{name}_mattress` | mattress volume |
| `pillow_1`, `pillow_2` | static | `{name}_pillow_1`, … | one pillow each |
| `clearance_*` | static | `{name}_clearance_bed_entry`, … | optional entry zones (v0.6) |
| `label` | static | `{name}_label` | text curve |

Build meshes use `{name}__{part}_{detail}` during generation (double underscore).

Static Parts are parented to `body`. User moves `{name}_body` to move the whole bed.

**Coordinates:** All build meshes use **absolute world coordinates** from
`params.location`. The Part API converts child Parts to local space at `finish()`
without changing world position. See `docs/units_and_coordinates.md`.

### Roles on build meshes

| Detail | `layoutlab_role` |
|---|---|
| Corner posts (×4) | `bed_post` |
| Side rails (×4) | `bed_frame` |
| Footboard (structural) | `bed_footboard` |
| Headboard base (structural) | `bed_frame` |
| Headboard rise (decorative) | `bed_headboard` |
| Mattress | `bed_mattress` |
| Pillows | `bed_pillow` |
| Label | `label` |

------------------------------------------------------------------------

## Return Value

```json
{
  "created": "BED_120x200",
  "type": "bed_basic",
  "size": [12, 20],
  "headboard_rise": 3.2
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
    "length": 1.2,
    "width": 2.0,
    "head_side": "y_max",
    "collection": "layout_tests"
  }
}
```

### Frame-only head end (no decorative rise)

```json
"params": { "headboard_height": 0 }
```

### Tall decorative headboard (50 cm above frame top)

```json
"params": { "headboard_height": 5.0 }
```

------------------------------------------------------------------------

## Known Limitations

- Label is a separate CURVE object; not part of collision geometry
- Magic sizing constants for pillow placement and mattress Z inset — acceptable for reference generator
- Slats, centre support, loft variant — not in this generator (see `docs/how_to_write_generators.md` §13.4)

## Semantic metadata (v0.6)

Part objects receive `layoutlab_object_id`, `layoutlab_part`, `layoutlab_part_type`, etc. at `finish()`.  
Update in place: JSON `regenerate` command (see `docs/json_protocol.md` §5.12).

------------------------------------------------------------------------

## JSON Protocol Reference

See `docs/json_protocol.md` §5.1
