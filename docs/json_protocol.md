# LayoutLab JSON Protocol

Version: 0.5.0 (Draft)

> This document describes how external agents (ChatGPT, Cursor, scripts) communicate
> with the LayoutLab Blender plugin.
>
> **Status markers used throughout this document:**
>
> - `[IMPLEMENTED]` — works in `layoutlab_chatgpt_helper_v05.py` today
> - `[PLANNED]` — not yet implemented; listed for forward compatibility only

------------------------------------------------------------------------

# 1. Overview

LayoutLab uses JSON as the **only** communication channel between AI and plugin.

- No Python snippets sent directly to Blender operators
- No Blender-specific scripting in AI responses intended for execution

Two directions exist:

| Direction | Purpose | Status |
|---|---|---|
| **Commands → Plugin** | AI instructs Blender to create, move, or modify the scene | `[IMPLEMENTED]` |
| **Scene ← Plugin** | Plugin exports scene state back to AI | `[IMPLEMENTED]` |

Reference implementation: `layoutlab_chatgpt_helper_v05.py`

------------------------------------------------------------------------

# 2. Protocol Version

| Field | Value | Status |
|---|---|---|
| `layoutlab_version` in scene export | `"0.5.0"` | `[IMPLEMENTED]` |
| `protocol_version` in command payloads | — | `[PLANNED]` |
| Version negotiation / migration | — | `[PLANNED]` |

Until `protocol_version` exists, agents should assume **v0.5 behaviour** as described here.

------------------------------------------------------------------------

# 3. Command Input

## 3.1 Envelope Format `[IMPLEMENTED]`

Commands are applied via **Apply Commands** in the LayoutLab panel.
Source: clipboard (default) or Blender text block `LayoutLab_Commands`.

The payload must be valid JSON in one of two forms:

**Form A — object with commands array (preferred):**

```json
{
  "commands": [
    { "action": "run_generator", "generator": "bed_basic", "params": { } }
  ]
}
```

**Form B — bare array:**

```json
[
  { "action": "create_box", "name": "TEST", "location": [0, 0, 0], "dimensions": [1, 1, 1] }
]
```

## 3.2 Execution Semantics `[IMPLEMENTED]`

- Commands run **sequentially** in array order.
- Each command is independent; later commands see effects of earlier ones.
- **Partial success:** failed commands do not stop the batch. Failures are collected; successful commands still apply.
- Failed command index and traceback are printed to the Blender console.
- Invalid top-level JSON (parse error) cancels the entire batch.

## 3.3 Result Reporting `[IMPLEMENTED]`

- Successful commands that return a value append to an internal results list (printed to console).
- No structured JSON result is returned to the AI automatically — `[PLANNED]`

## 3.4 Structured Error Response `[PLANNED]`

```json
{
  "results": [ ],
  "errors": [
    { "index": 0, "action": "move", "message": "Object not found: MISSING" }
  ]
}
```

------------------------------------------------------------------------

# 4. Command Reference

Every command is a JSON object with a required `"action"` field.

Object references accept either `"object"` or `"name"` as the key — both are equivalent. `[IMPLEMENTED]`

------------------------------------------------------------------------

## 4.1 `run_generator` `[IMPLEMENTED]`

Executes a parametric generator by name.

```json
{
  "action": "run_generator",
  "generator": "bed_basic",
  "params": {
    "name": "BED_120x200",
    "location": [68.3, 197.7, 0],
    "length": 12,
    "width": 20,
    "head_side": "y_max",
    "collection": "layout_tests"
  }
}
```

| Field | Required | Type | Description |
|---|---|---|---|
| `generator` | yes | string | Generator name (sanitized to `[a-zA-Z0-9_]`) |
| `params` | no | object | Passed to `generate(params, api)`; defaults to `{}` |

**Return value (console):** generator-specific dict, e.g. `{"created": "...", "type": "bed_basic", "size": [12, 20]}`

### Known generator: `bed_basic` `[IMPLEMENTED]`

| Parameter | Default | Description |
|---|---|---|
| `name` | `"BED_basic"` | Object name prefix |
| `location` | `[0, 0, 0]` | Origin `[x, y, z]` in Blender units |
| `length` | `20` | Bed length (min 3) |
| `width` | `12` | Bed width (min 3) |
| `collection` | `"layout_tests"` | Target Blender collection |
| `head_side` | `"y_max"` | Headboard side: `y_max`, `y_min`, `x_max`, or other (= `x_min`) |
| `leg_height` | `2.5` | Leg height |
| `frame_height` | `1.0` | Frame rail height |
| `mattress_height` | `2.0` | Mattress thickness |
| `rail_thickness` | `0.35` | Frame rail thickness (capped relative to size) |
| `post_size` | `0.45` | Corner post size (capped relative to size) |
| `mattress_inset` | `0.45` | Mattress inset from frame |
| `headboard_height` | `4.2` | Headboard height |
| `footboard_height` | `2.2` | Footboard height |
| `frame_color` | `[0.72, 0.55, 0.35, 1]` | RGBA |
| `mattress_color` | `[0.86, 0.86, 0.82, 0.65]` | RGBA |
| `pillow_color` | `[0.95, 0.95, 0.92, 1]` | RGBA |

### `regenerate` (same generator, updated params) `[PLANNED]`

Replace an existing generated object in place without manual delete.

------------------------------------------------------------------------

## 4.2 `save_generator` `[IMPLEMENTED]`

Saves Python generator source code to the user generator directory.

```json
{
  "action": "save_generator",
  "code": "GENERATOR_NAME = \"my_bed\"\n..."
}
```

| Field | Required | Type | Description |
|---|---|---|---|
| `code` | yes | string | Full Python source; must contain `GENERATOR_NAME = "..."` and `def generate(params, api)` |

**Return value:** `{"saved_generator": "<name>", "path": "<absolute path>"}`

Generator files are stored at:

`~/Library/Application Support/Blender/<version>/scripts/addons/layoutlab_generators/<name>.py`

(macOS path; OS-dependent via Blender user scripts directory)

### Generator validation before save `[PLANNED]`

Syntax check, required metadata fields, forbidden patterns.

------------------------------------------------------------------------

## 4.3 `delete_generator` `[IMPLEMENTED]`

```json
{
  "action": "delete_generator",
  "generator": "bed_basic"
}
```

**Return value:** `{"deleted_generator": "<name>"}`

No error if file does not exist.

------------------------------------------------------------------------

## 4.4 `create_box` `[IMPLEMENTED]`

Creates a axis-aligned box mesh.

```json
{
  "action": "create_box",
  "name": "WALL_north",
  "location": [0, 0, 0],
  "dimensions": [10, 0.2, 2.5],
  "color": [0.8, 0.8, 0.8, 1],
  "collection": "layout_tests",
  "role": "wall",
  "display_type": null
}
```

| Field | Required | Default | Description |
|---|---|---|---|
| `name` | yes | — | Blender object name |
| `location` | no | `[0, 0, 0]` | Box origin `[x, y, z]` |
| `dimensions` | no | `[1, 1, 1]` | Size `[dx, dy, dz]` |
| `color` | no | `[0.8, 0.8, 0.8, 1]` | RGBA material color |
| `collection` | no | `"layout_tests"` | Target collection |
| `role` | no | `null` | Stored as custom property `layoutlab_role` |
| `display_type` | no | `null` | Blender viewport display mode (e.g. `"WIRE"`) |

------------------------------------------------------------------------

## 4.5 `create_clearance` `[IMPLEMENTED]`

Creates a clearance zone (wireframe box with semantic role).

```json
{
  "action": "create_clearance",
  "name": "CLEARANCE_bed_access",
  "location": [68.3, 197.7, 0],
  "dimensions": [12, 7, 0.1],
  "color": [0.2, 0.8, 1.0, 0.22],
  "collection": "layout_tests",
  "display_type": "WIRE"
}
```

Same fields as `create_box`, except:

- `role` is always set to `"clearance"` (not overridable)
- Default `color`: `[0.2, 0.8, 1.0, 0.22]`
- Default `display_type`: `"WIRE"`
- Default `dimensions[2]`: `0.1` (thin slab)

### Auto-generated clearance from generators `[PLANNED]`

Generators emit their own clearance zones via API, not manual JSON commands.

------------------------------------------------------------------------

## 4.6 `delete_collection_objects` `[IMPLEMENTED]`

Removes all objects in a collection (collection itself remains).

```json
{
  "action": "delete_collection_objects",
  "collection": "layout_tests"
}
```

------------------------------------------------------------------------

## 4.7 `delete_prefix` `[IMPLEMENTED]`

Removes all scene objects whose names start with a prefix.

```json
{
  "action": "delete_prefix",
  "prefix": "BED_"
}
```

------------------------------------------------------------------------

## 4.8 `move` `[IMPLEMENTED]`

```json
{
  "action": "move",
  "object": "BED_120x200_mattress",
  "location": [70.0, 200.0, 0]
}
```

| Field | Required | Description |
|---|---|---|
| `object` or `name` | yes | Target object name |
| `location` | yes | New `[x, y, z]` |

**Error:** raises if object not found.

### Semantic move (`move_to_make_space`) `[PLANNED]`

Move based on intent, not absolute coordinates.

------------------------------------------------------------------------

## 4.9 `rotate_z` `[IMPLEMENTED]`

```json
{
  "action": "rotate_z",
  "object": "BED_120x200",
  "degrees": 90
}
```

| Field | Required | Description |
|---|---|---|
| `object` or `name` | yes | Target object name |
| `degrees` | yes | Rotation around Z axis in degrees |

**Error:** raises if object not found.

### Full `rotate` (3-axis) `[PLANNED]`

------------------------------------------------------------------------

## 4.10 `delete` `[IMPLEMENTED]`

```json
{
  "action": "delete",
  "object": "TEST_BOX"
}
```

Silently succeeds if object does not exist.

------------------------------------------------------------------------

## 4.11 `hide` / `show` `[IMPLEMENTED]`

```json
{ "action": "hide", "object": "CLEARANCE_bed_access" }
{ "action": "show", "object": "CLEARANCE_bed_access" }
```

Sets both `hide_viewport` and `hide_render`.

**Error:** raises if object not found.

------------------------------------------------------------------------

## 4.12 Planned Commands (not in v0.5)

| Action | Purpose | Status |
|---|---|---|
| `run_generator_batch` | Multiple generators in one logical operation with shared undo | `[PLANNED]` |
| `set_parameter` | Update params on an existing generated object and regenerate | `[PLANNED]` |
| `analyze_layout` | Return clearance violations, paths, storage metrics | `[PLANNED]` |
| `compare_variants` | Diff two layout states | `[PLANNED]` |
| `create_collection` | Explicit collection management | `[PLANNED]` |
| `group_objects` | Link meshes to a LayoutLab object identity | `[PLANNED]` |

------------------------------------------------------------------------

# 5. Scene Export (Plugin → AI)

## 5.1 Trigger `[IMPLEMENTED]`

LayoutLab panel → **Copy Scene Layout** or **Copy Selected**

Copies JSON to system clipboard.

## 5.2 Export Schema `[IMPLEMENTED]`

```json
{
  "layoutlab_version": "0.5.0",
  "unit": "METRIC",
  "unit_scale": 1.0,
  "scene": "Scene",
  "generator_dir": "/path/to/layoutlab_generators",
  "generators": [ ],
  "note": "Coordinates/dimensions are Blender units. In Alexander's room: 1 unit ≈ 10 cm.",
  "objects": [ ]
}
```

| Field | Type | Description |
|---|---|---|
| `layoutlab_version` | string | Plugin version |
| `unit` | string | Blender unit system (`METRIC`, `IMPERIAL`, `NONE`) |
| `unit_scale` | number | Blender scale length |
| `scene` | string | Scene name |
| `generator_dir` | string | Absolute path to generator storage |
| `generators` | array | All registered generators (metadata only) |
| `note` | string | Human-readable unit hint (project-specific) |
| `objects` | array | Scene objects (see below) |

### Generator metadata entry `[IMPLEMENTED]`

```json
{
  "name": "bed_basic",
  "category": "Beds",
  "description": "Parametric low bed with legs, frame, mattress...",
  "version": "0.1",
  "icon": "BED",
  "path": "/absolute/path/to/bed_basic.py"
}
```

## 5.3 Object Entry `[IMPLEMENTED]`

Only objects of type `MESH`, `EMPTY`, `CURVE`, or `FONT` are exported.

```json
{
  "name": "BED_120x200_mattress",
  "type": "MESH",
  "collection": "layout_tests",
  "location": [68.75, 198.15, 3.55],
  "rotation_euler_deg": [0.0, 0.0, 0.0],
  "scale": [1.0, 1.0, 1.0],
  "dimensions": [11.1, 19.1, 2.0],
  "visible": true,
  "world_bbox_corners": [ [68.75, 198.15, 3.55], "..." ],
  "custom_properties": {
    "layoutlab_role": "bed_mattress"
  }
}
```

| Field | Description |
|---|---|
| `location` | Object origin, rounded to 4 decimals |
| `rotation_euler_deg` | Euler rotation in degrees |
| `dimensions` | World-space bounding dimensions |
| `world_bbox_corners` | 8 corner points of world bounding box |
| `custom_properties` | Only string/int/float/bool custom props |

### Semantic object export `[PLANNED]`

Export should eventually include:

```json
{
  "layoutlab": {
    "object_id": "uuid",
    "generator": "bed_basic",
    "generator_version": "0.1",
    "params": { "length": 12, "width": 20 },
    "component": "mattress",
    "parent_object": "BED_120x200"
  }
}
```

Currently only `layoutlab_role` on individual meshes is available.

## 5.4 Export Filters `[PLANNED]`

- By collection
- By `layoutlab_role`
- Semantic objects only (exclude raw construction geometry)

------------------------------------------------------------------------

# 6. Generator List Export

## 6.1 Trigger `[IMPLEMENTED]`

LayoutLab panel → **Copy List** (Generator Library section)

## 6.2 Schema `[IMPLEMENTED]`

```json
{
  "generator_dir": "/path/to/layoutlab_generators",
  "generators": [ ]
}
```

Same generator metadata format as scene export.

------------------------------------------------------------------------

# 7. Units and Coordinates

## 7.1 Current Convention `[IMPLEMENTED]`

- All coordinates and dimensions are **Blender scene units**.
- The plugin exports Blender's unit settings but does **not** convert values.
- Project note in export: **1 Blender unit ≈ 10 cm** in Alexander's room scene.
- This convention is **not enforced** by the plugin — agents must respect scene context.

## 7.2 Formal Unit Contract `[PLANNED]`

Documented in `docs/units_and_coordinates.md` (not yet written):

- Canonical real-world mapping
- Axis conventions (length/width/height)
- Room origin definition

------------------------------------------------------------------------

# 8. Custom Properties

## 8.1 `layoutlab_role` `[IMPLEMENTED]`

Set by `create_box`, `create_clearance`, `create_label`, and generators.

Examples: `"bed_mattress"`, `"bed_post"`, `"clearance"`, `"label"`

Used for export filtering and future semantic grouping — `[PLANNED]`

## 8.2 Full Object Identity Schema `[PLANNED]`

| Property | Purpose |
|---|---|
| `layoutlab_object_id` | Groups components into one logical object |
| `layoutlab_generator` | Source generator name |
| `layoutlab_params` | JSON-serialized parameters |
| `layoutlab_component` | Component role within object |

------------------------------------------------------------------------

# 9. Example Workflows

## 9.1 Replace test layout with a bed `[IMPLEMENTED]`

```json
{
  "commands": [
    { "action": "delete_collection_objects", "collection": "layout_tests" },
    {
      "action": "run_generator",
      "generator": "bed_basic",
      "params": {
        "name": "BED_120x200",
        "location": [68.3, 197.7, 0],
        "length": 12,
        "width": 20,
        "head_side": "y_max",
        "collection": "layout_tests"
      }
    }
  ]
}
```

## 9.2 Install a new generator from AI `[IMPLEMENTED]`

```json
{
  "commands": [
    {
      "action": "save_generator",
      "code": "GENERATOR_NAME = \"wardrobe_basic\"\nGENERATOR_CATEGORY = \"Storage\"\n..."
    },
    {
      "action": "run_generator",
      "generator": "wardrobe_basic",
      "params": { "name": "WARDROBE_1", "location": [0, 0, 0], "width": 8, "depth": 6, "height": 20 }
    }
  ]
}
```

## 9.3 AI-driven layout iteration `[PLANNED]`

1. Copy scene → AI analyzes JSON
2. AI returns commands with semantic intent
3. Plugin applies, exports again
4. AI evaluates constraints (clearance, paths)

Steps 1–3 work today at the geometry level. Step 4 requires Phase 2 features.

------------------------------------------------------------------------

# 10. Rules for AI Agents

`[IMPLEMENTED]` — enforced by project policy (see `00_READ_THIS_FIRST.md`, DD-003)

1. Communicate **only** via JSON commands as defined here.
2. Do not send Python code for direct Blender execution (except inside `save_generator.code`).
3. Prefer `run_generator` over manual `create_box` when a generator exists.
4. Use `delete_collection_objects` or `delete_prefix` before regenerating layouts.
5. Always check exported `generators` list before calling unknown generator names.

`[PLANNED]`

6. Include `protocol_version` in every command payload once available.
7. Use semantic object IDs instead of individual mesh names when regenerating.

------------------------------------------------------------------------

# 11. Changelog

| Version | Date | Changes |
|---|---|---|
| 0.5.0 | 2026-07-09 | Initial protocol document based on `layoutlab_chatgpt_helper_v05.py` |
