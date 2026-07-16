# LayoutLab JSON Protocol

Version: **0.5.0** (Contract)

> **This document is the binding contract** between external agents (ChatGPT,
> Cursor, scripts) and the LayoutLab Blender plugin.
>
> If behaviour differs from this document, treat it as a **bug** — fix the code
> or update this document deliberately (with changelog entry).
>
> **Status markers:**
>
> - `[IMPLEMENTED]` — works in `layoutlab/` addon today
> - `[PLANNED]` — not yet implemented; do not assume availability

Reference code: `layoutlab/__init__.py`, `layoutlab/util.py`

Related: `docs/units_and_coordinates.md`, [DD-003](design_decisions/DD-003-json-only-communication.md) (transport), [DD-009](design_decisions/DD-009-ai-execution-boundary.md) (execution boundary — **Accepted**)

------------------------------------------------------------------------

# 1. Overview

LayoutLab uses JSON as the **only** communication channel between AI and plugin.

| Direction | Trigger | Status |
|---|---|---|
| **Commands → Plugin** | Panel → *Apply Commands* | `[IMPLEMENTED]` |
| **Scene ← Plugin** | Panel → *Copy Scene Layout* / *Copy Selected* | `[IMPLEMENTED]` |
| **Generator list ← Plugin** | Panel → *Copy List* | `[IMPLEMENTED]` |

**Not allowed:** Python snippets for direct Blender execution (except `save_generator.code`).

------------------------------------------------------------------------

# 2. Protocol Version

| Field | Location | Value | Status |
|---|---|---|---|
| `layoutlab_version` | Scene export | `"0.5.0"` | `[IMPLEMENTED]` |
| `protocol_version` | Command payload | — | `[PLANNED]` |

Until `protocol_version` exists, agents must assume **v0.5.0** behaviour exactly as documented here.

------------------------------------------------------------------------

# 3. Command Input

## 3.1 Source `[IMPLEMENTED]`

| Source | Setting | Default text block |
|---|---|---|
| System clipboard | `layoutlab_command_source = CLIPBOARD` | — |
| Blender text block | `layoutlab_command_source = TEXT` | `LayoutLab_Commands` |

Panel: *LayoutLab → Apply ChatGPT Commands*

## 3.2 Envelope Format `[IMPLEMENTED]`

Valid JSON in one of two forms:

**Form A — object with `commands` array (preferred):**

```json
{
  "commands": [
    { "action": "run_generator", "generator": "bed_basic", "params": {} }
  ]
}
```

**Form B — bare array:**

```json
[
  { "action": "create_box", "name": "TEST", "location": [0, 0, 0], "dimensions": [1, 1, 1] }
]
```

| Input | Result |
|---|---|
| `{"commands": []}` | Valid no-op |
| `{}` | Valid no-op (empty command list) |
| Invalid JSON | Entire batch cancelled; error shown in UI |
| `{"commands": "text"}` | Error: expected list |

Parsing implementation: `layoutlab.util.parse_commands_payload()`

## 3.3 Execution Semantics `[IMPLEMENTED]`

1. Commands run **sequentially** in array order.
2. Later commands see scene effects of earlier commands.
3. **Partial success:** one failed command does not stop the batch.
4. Failures: index + traceback printed to **Blender system console**.
5. UI report: `WARNING` if any command failed, else `INFO`.
6. Successful return values collected internally and printed to console as JSON.

## 3.4 Result Reporting `[IMPLEMENTED]`

| Outcome | Where |
|---|---|
| Success values | Blender console (`LayoutLab results:`) |
| Errors | Blender console (`LayoutLab errors:`) |
| Structured JSON reply to AI | `[PLANNED]` |

## 3.5 Error Behaviour Summary `[IMPLEMENTED]`

| Condition | Behaviour |
|---|---|
| Unknown `action` | Command fails; batch continues |
| Missing required field | Command fails (typically `KeyError`) |
| `move` / `rotate_z` / `hide` / `show` on missing object | Command fails |
| `delete` on missing object | Silent success |
| `delete_generator` on missing file | Silent success |
| `run_generator` on unknown generator | Command fails: `Generator not found` |
| Invalid generator code | Command fails at `exec` or missing `generate()` |

------------------------------------------------------------------------

# 4. Command Index

| Action | Purpose | Returns value |
|---|---|---|
| `run_generator` | Execute parametric generator | yes (generator dict) |
| `save_generator` | Save generator Python source | yes |
| `delete_generator` | Delete generator file | yes |
| `create_box` | Create box mesh | yes (Blender object) |
| `create_clearance` | Create clearance zone | yes (Blender object) |
| `delete_collection_objects` | Remove all objects in collection | no |
| `delete_prefix` | Remove objects by name prefix | no |
| `move` | Set object location | no |
| `rotate_z` | Rotate object around Z | no |
| `delete` | Remove object | no |
| `hide` | Hide in viewport and render | no |
| `show` | Show in viewport and render | no |

Object references: use `"object"` **or** `"name"` — equivalent. `[IMPLEMENTED]`

------------------------------------------------------------------------

# 5. Command Reference

## 5.1 `run_generator` `[IMPLEMENTED]`

```json
{
  "action": "run_generator",
  "generator": "bed_basic",
  "params": {
    "name": "BED_120x200",
    "location": [68.3, 197.7, 0],
    "length": 1.2,
    "width": 2.0,
    "head_side": "y_max",
    "collection": "layout_tests"
  }
}
```

| Field | Required | Type | Description |
|---|---|---|---|
| `action` | yes | `"run_generator"` | — |
| `generator` | yes | string | Generator name → sanitized to `[a-zA-Z0-9_]` |
| `params` | no | object | Passed to `generate(params, api)`; default `{}` |

**Prerequisite:** generator file must exist in the user generator directory.
On addon register, bundled generators from `generators/` are copied if missing.
Use panel → *Install Default* or `save_generator` to install.

**Return (console):** generator-specific dict, e.g.:

```json
{ "created": "BED_120x200", "type": "bed_basic", "size": [12, 20] }
```

### Generator params: `bed_basic` `[IMPLEMENTED]`

See `layoutlab/generators/bed_basic.md` for full documentation.

| Parameter | Default | Unit | Description |
|---|---|---|---|
| `name` | `"BED_basic"` | — | Prefix for all component object names |
| `location` | `[0, 0, 0]` | Blender units | Min corner of footprint at floor (see units doc) |
| `length` | `20` | Blender units | Extent along **+X** (min 3) |
| `width` | `12` | Blender units | Extent along **+Y** (min 3) |
| `collection` | `"layout_tests"` | — | Target collection |
| `head_side` | `"y_max"` | — | `y_max`, `y_min`, `x_max`, `x_min` |
| `leg_height` | `2.5` | Blender units | Post height below frame loop; posts extend to frame top |
| `frame_height` | `1.0` | Blender units | Height of frame loop (rails + footboard + headboard base) |
| `mattress_height` | `2.0` | Blender units | — |
| `rail_thickness` | `0.35` | Blender units | Capped at 20% of width/length |
| `post_size` | `0.45` | Blender units | Capped at 25% of width/length |
| `headboard_height` | `3.2` | Blender units | Decorative rise **above frame top** (v0.5+); alias `headboard_rise` |
| `frame_color` | `[0.72, 0.55, 0.35, 1]` | RGBA 0–1 | — |
| `mattress_color` | `[0.86, 0.86, 0.82, 0.65]` | RGBA 0–1 | — |
| `pillow_color` | `[0.95, 0.95, 0.92, 1]` | RGBA 0–1 | — |

**Component roles** set on meshes (`layoutlab_role`):

`bed_post`, `bed_frame`, `bed_mattress`, `bed_headboard`, `bed_footboard`, `bed_pillow`, `label`

**Standard size example:** `length: 1.2, width: 2.0` → 120 × 200 cm (Metric, 1 unit = 1 m).

------------------------------------------------------------------------

## 5.2 `save_generator` `[IMPLEMENTED]`

```json
{
  "action": "save_generator",
  "code": "GENERATOR_NAME = \"my_bed\"\nGENERATOR_CATEGORY = \"Beds\"\n..."
}
```

| Field | Required | Type | Description |
|---|---|---|---|
| `action` | yes | `"save_generator"` | — |
| `code` | yes | string | Full Python source with `GENERATOR_NAME` and `generate(params, api)` |

**Return:**

```json
{ "saved_generator": "my_bed", "path": "/absolute/path/to/my_bed.py" }
```

**Storage path:** `{Blender user scripts}/addons/layoutlab_generators/{name}.py`

(OS-specific; macOS example: `~/Library/Application Support/Blender/<ver>/scripts/addons/layoutlab_generators/`)

Validation before save: `[PLANNED]`

------------------------------------------------------------------------

## 5.3 `delete_generator` `[IMPLEMENTED]`

```json
{ "action": "delete_generator", "generator": "bed_basic" }
```

| Field | Required |
|---|---|
| `generator` | yes |

**Return:** `{ "deleted_generator": "<name>" }` — no error if file absent.

------------------------------------------------------------------------

## 5.4 `create_box` `[IMPLEMENTED]`

```json
{
  "action": "create_box",
  "name": "WALL_north",
  "location": [0, 0, 0],
  "dimensions": [10, 0.2, 2.5],
  "color": [0.8, 0.8, 0.8, 1],
  "collection": "layout_tests",
  "role": "wall",
  "display_type": "WIRE"
}
```

| Field | Required | Default | Description |
|---|---|---|---|
| `name` | yes | — | Blender object name (must be unique) |
| `location` | no | `[0, 0, 0]` | Box min corner `[x, y, z]` |
| `dimensions` | no | `[1, 1, 1]` | `[dx, dy, dz]` along X, Y, Z |
| `color` | no | `[0.8, 0.8, 0.8, 1]` | RGBA; omit material if falsy |
| `collection` | no | `"layout_tests"` | — |
| `role` | no | none | Sets `layoutlab_role` custom property |
| `display_type` | no | none | e.g. `"WIRE"`, `"SOLID"`, `"BOUNDS"` |

------------------------------------------------------------------------

## 5.5 `create_clearance` `[IMPLEMENTED]`

DD-007 clearance zone. Same wire defaults as before; adds semantic metadata.

| Field | Required | Default | Description |
|---|---|---|---|
| `name` | yes | — | Blender object name |
| `dimensions` | no | `[1, 1, 0.1]` | Box size |
| `location` | no | `[0, 0, 0]` | World location (standalone) |
| `clearance_name` | no | `name` | Semantic zone id per furniture instance |
| `purpose` | no | `""` | Intent category |
| `requirement` | no | `"preferred"` | `required` \| `preferred` |
| `priority` | no | `0` | Zone priority |
| `params` | no | — | Extra params (JSON object) |
| `color` | no | `[0.2, 0.8, 1.0, 0.22]` | RGBA |
| `collection` | no | `"layout_tests"` | — |
| `display_type` | no | `"WIRE"` | — |

Sets `layoutlab_clearance_*` custom properties. See `docs/generator_api.md` §4.3.

------------------------------------------------------------------------

## 5.6 `delete_collection_objects` `[IMPLEMENTED]`

```json
{ "action": "delete_collection_objects", "collection": "layout_tests" }
```

| Field | Required |
|---|---|
| `collection` | yes |

Removes objects in collection; collection itself remains. No error if collection missing.

------------------------------------------------------------------------

## 5.7 `delete_prefix` `[IMPLEMENTED]`

```json
{ "action": "delete_prefix", "prefix": "BED_120x200" }
```

| Field | Required |
|---|---|
| `prefix` | yes |

Removes **all scene objects** whose names start with `prefix`. Use before re-running a generator.

------------------------------------------------------------------------

## 5.8 `move` `[IMPLEMENTED]`

```json
{ "action": "move", "object": "BED_120x200_mattress", "location": [70, 200, 0] }
```

| Field | Required |
|---|---|
| `object` or `name` | yes |
| `location` | yes |

**Note:** moves **one** Blender object. For generated furniture, move the **Main Part** (`body`) — child Parts follow. `[IMPLEMENTED]` v0.6 parenting; `[PLANNED]` JSON `move` by `object_id`.

**Error if object not found.**

------------------------------------------------------------------------

## 5.9 `rotate_z` `[IMPLEMENTED]`

```json
{ "action": "rotate_z", "object": "BED_120x200_mattress", "degrees": 90 }
```

| Field | Required |
|---|---|
| `object` or `name` | yes |
| `degrees` | yes |

Same single-object limitation as `move`. **Error if object not found.**

------------------------------------------------------------------------

## 5.10 `delete` `[IMPLEMENTED]`

```json
{ "action": "delete", "object": "TEST_BOX" }
```

Silent if object does not exist.

------------------------------------------------------------------------

## 5.11 `hide` / `show` `[IMPLEMENTED]`

```json
{ "action": "hide", "object": "CLEARANCE_bed_access" }
{ "action": "show", "object": "CLEARANCE_bed_access" }
```

Sets `hide_viewport` and `hide_render`. **Error if object not found.**

------------------------------------------------------------------------

## 5.12 `regenerate` `[IMPLEMENTED]`

Rebuild a logical object from stored generator metadata, optionally overriding params.

```json
{
  "action": "regenerate",
  "object_id": "a1b2c3d4-…",
  "params": { "length": 14 }
}
```

**Alternative:** reference any component mesh by name:

```json
{
  "action": "regenerate",
  "object": "BED_120x200_mattress",
  "params": { "width": 22 }
}
```

| Field | Required | Description |
|---|---|---|
| `object_id` | one of `object_id` / `object` | UUID shared by all components |
| `object` | one of `object_id` / `object` | Any component object name |
| `params` | no | Overrides merged into stored `layoutlab_params` |

**Behaviour:**

1. Resolve `object_id` from field or from `object` mesh custom property.
2. Read `layoutlab_generator` and `layoutlab_params` from existing components.
3. Merge `params` overrides into stored params.
4. Delete all meshes with that `layoutlab_object_id`.
5. Re-run generator with merged params; **same `object_id` preserved**.

**Legacy objects** without `layoutlab_object_id` cannot be regenerated — use `delete_prefix` + `run_generator`.

**Return value (console):** `{ "regenerated", "object_id", "generator", "params", … }`

------------------------------------------------------------------------

## 5.13 `analyze_layout` `[IMPLEMENTED]` (DD-008)

Constraint analysis — **reads** exported clearances, **does not** modify scene.

See [DD-008](../design_decisions/DD-008-constraints-and-layout-analysis.md).

```json
{
  "action": "analyze_layout",
  "scope": "scene",
  "collection": "layout_tests"
}
```

| Field | Default | Description |
|---|---|---|
| `scope` | `"scene"` | `"scene"` \| `"collection"` \| `"selection"` |
| `collection` | — | Required when `scope` is `"collection"` |
| `include` | `["clearances"]` | v1: only `"clearances"` supported |

**Return (v1):** `{ "analyzed", "scope", "object_count", "clearance_count", "summary": { "errors", "warnings", "info" }, "findings": [...] }`

Each finding references `clearance_ref` + `overlaps[]`. Severity derives from clearance `requirement` (`required` → error, `preferred` → warning).

**Implementation:** `layoutlab/protocol/layout_analysis.py`

------------------------------------------------------------------------

## 5.14 Room Model commands `[IMPLEMENTED]` (DD-010)

Editable **Room Model** — not a furniture generator. See [room_model.md](room_model.md).

### `create_room`

```json
{
  "action": "create_room",
  "params": {
    "name": "KIDS_ROOM",
    "location": [0, 0, 0],
    "width": 4.2,
    "depth": 2.18,
    "height": 2.6,
    "wall_thickness": 0.02,
    "collection": "layoutlab_room"
  }
}
```

Creates rectangle footprint (`footprint.kind: "rectangle"`), four walls with stable ids, floor + **inward-facing wall planes** (see-through from outside). Default origin `[0, 0, 0]` if `location` omitted.

### `add_opening` / `add_fixed_element`

```json
{
  "action": "add_opening",
  "params": {
    "room": "KIDS_ROOM",
    "opening_name": "door_east",
    "kind": "door",
    "wall_side": "east",
    "offset": 2.5,
    "width": 7.08,
    "height": 18.45
  }
}
```

| Field | Notes |
|---|---|
| `room` / `room_id` | Room reference |
| `wall_side` | `south` \| `east` \| `north` \| `west` (or `wall_id`) |
| `offset` | Along wall from SW-biased start (south/north: from west; west/east: from south) |

Also: `update_room`, `delete_room`, `update_opening`, `remove_opening`, `update_fixed_element`, `remove_fixed_element`.

**Export:** top-level `rooms[]` array on scene export.

------------------------------------------------------------------------

## 5.15 Other Planned Commands

| Action | Purpose |
|---|---|
| `run_generator_batch` | Shared undo group |
| `set_parameter` | Param change + regenerate (alias) |
| `compare_variants` | Layout diff |
| `create_collection` | Collection management |
| `group_objects` | Semantic object identity |

------------------------------------------------------------------------

# 6. Scene Export (Plugin → AI)

## 6.1 Schema `[IMPLEMENTED]`

```json
{
  "layoutlab_version": "0.10.0",
  "unit": "METRIC",
  "unit_scale": 1.0,
  "scene": "Scene",
  "generator_dir": "/path/to/layoutlab_generators",
  "generators": [],
  "note": "Coordinates/dimensions are Blender scene units (native). With Metric and unit_scale=1.0, 1 unit = 1 meter.",
  "objects": []
}
```

| Field | Type | Description |
|---|---|---|
| `layoutlab_version` | string | Plugin version |
| `unit` | string | `METRIC`, `IMPERIAL`, or `NONE` |
| `unit_scale` | number | Blender `scale_length` |
| `scene` | string | Scene name |
| `generator_dir` | string | Absolute path to runtime generator storage |
| `generators` | array | Installed generator metadata (see §6.2) |
| `note` | string | Unit hint for this project |
| `objects` | array | Exported objects (see §6.3) |

## 6.2 Generator Metadata Entry `[IMPLEMENTED]`

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

## 6.3 Object Entry `[IMPLEMENTED]`

Exported types: `MESH`, `EMPTY`, `CURVE`, `FONT` only.

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
  "world_bbox_corners": [[68.75, 198.15, 3.55], "..."],
  "custom_properties": { "layoutlab_role": "bed_mattress", "layoutlab_object_id": "…" },
  "layoutlab": {
    "object_id": "uuid-here",
    "generator": "bed_basic",
    "generator_version": "0.1",
    "params": { "length": 1.2, "width": 2.0, "head_side": "y_max" },
    "component": "mattress",
    "part": "mattress",
    "part_type": "static",
    "role": "bed_mattress"
  }
}
```

| Field | Notes |
|---|---|
| `location` | Object origin; 4 decimal places |
| `dimensions` | World-space AABB size |
| `world_bbox_corners` | 8 world corners |
| `custom_properties` | string/int/float/bool only (includes all `layoutlab_*` props) |
| `layoutlab` | Present when `layoutlab_object_id` is set `[IMPLEMENTED]` v0.5.1; includes `clearance` sub-block on clearance Parts `[IMPLEMENTED]` v0.7.1 |

------------------------------------------------------------------------

# 7. Generator List Export

Trigger: *Copy List*

```json
{
  "generator_dir": "/path/to/layoutlab_generators",
  "generators": []
}
```

Same generator metadata as §6.2. Does not include scene objects.

------------------------------------------------------------------------

# 8. Units and Coordinates

All command coordinates and dimensions are **Blender scene units** (native).
With Metric and `unit_scale=1.0`, **1 unit = 1 meter**.

Full specification: **`docs/units_and_coordinates.md`**

------------------------------------------------------------------------

# 9. Custom Properties

## 9.1 `layoutlab_role` `[IMPLEMENTED]`

Set by `create_box`, `create_clearance`, `create_label`, and generators.

Examples: `bed_mattress`, `bed_post`, `clearance`, `label`

## 9.2 Identity Schema `[IMPLEMENTED]` (v0.5.1)

Set automatically on meshes created via `run_generator` / `regenerate`:

| Property | Set by | Purpose |
|---|---|---|
| `layoutlab_object_id` | Engine | Groups all components of one logical object |
| `layoutlab_generator` | Engine | Source generator name |
| `layoutlab_generator_version` | Engine | Generator version at creation |
| `layoutlab_params` | Engine | JSON string of full params for regeneration |
| `layoutlab_component` | Engine | Part id (legacy field name) |
| `layoutlab_part` | Engine | Part id `[IMPLEMENTED]` v0.6 |
| `layoutlab_part_type` | Engine | `main` / `static` / `dynamic` `[IMPLEMENTED]` v0.6 |
| `layoutlab_role` | API / generator | Fine-grained role (unchanged) |

### Clearance export `[IMPLEMENTED]` (v0.7.1)

When a Part object has `layoutlab_clearance_name`, export includes:

```json
"layoutlab": {
  "object_id": "…",
  "part": "clearance_front_access",
  "clearance": {
    "clearance_id": "…",
    "clearance_name": "front_access",
    "purpose": "door_access",
    "requirement": "preferred",
    "priority": 0,
    "params": { "depth": 6.0 },
    "shape": "box",
    "local_transform": { "location": [0, -6, 0], "rotation": [0,0,0], "dimensions": [8,6,15] },
    "local_bounds": { "min": [0, -6, 0], "max": [8, 0, 15] },
    "world_bounds": { "min": [50, 114, 0], "max": [58, 120, 15] }
  }
}
```

`local_bounds` are relative to the Main Part; `world_bounds` are computed at export time. See DD-007.

Objects from `create_box` / standalone JSON `create_clearance` without `layoutlab_object_id` do **not** receive the full furniture `layoutlab` block (legacy role-only behaviour).

See `docs/object_model.md` for the full schema.

------------------------------------------------------------------------

# 10. Example Workflows

## 10.1 Replace layout and place bed

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
        "length": 1.2,
        "width": 2.0,
        "head_side": "y_max",
        "collection": "layout_tests"
      }
    }
  ]
}
```

## 10.2 Update bed size (v0.5 pattern)

```json
{
  "commands": [
    { "action": "delete_prefix", "prefix": "BED_120x200" },
    {
      "action": "run_generator",
      "generator": "bed_basic",
      "params": {
        "name": "BED_120x200",
        "location": [68.3, 197.7, 0],
        "length": 14,
        "width": 2.0,
        "head_side": "y_max",
        "collection": "layout_tests"
      }
    }
  ]
}
```

## 10.3 Install generator from AI

```json
{
  "commands": [
    {
      "action": "save_generator",
      "code": "GENERATOR_NAME = \"wardrobe_basic\"\n..."
    },
    {
      "action": "run_generator",
      "generator": "wardrobe_basic",
      "params": { "name": "WARDROBE_1", "location": [0, 0, 0] }
    }
  ]
}
```

------------------------------------------------------------------------

# 11. Rules for AI Agents

1. Use **only** JSON commands defined in this document.
2. Do not send Python for direct Blender execution (except inside `save_generator.code`).
3. Prefer `run_generator` over manual `create_box` when a generator exists.
4. Before re-placing furniture: `delete_prefix` with the object `name` prefix, or `delete_collection_objects`.
5. Read scene export `generators` array before calling unknown generator names.
6. Read `note` and `docs/units_and_coordinates.md` before interpreting sizes.
7. Remember: `move` / `rotate_z` affect **one mesh**, not a logical furniture group.

------------------------------------------------------------------------

# 12. Changelog

| Version | Date | Changes |
|---|---|---|
| 0.5.0 | 2026-07-09 | Initial protocol document |
| 0.5.1 | 2026-07-09 | Contract pass: command index, error table, prerequisites, units cross-link, bed_basic roles, single-object move note, bare-array fix documented |
