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
> - `[IMPLEMENTED]` — works in `layoutlab_chatgpt_helper_v05.py` today
> - `[PLANNED]` — not yet implemented; do not assume availability

Reference code: `layoutlab_chatgpt_helper_v05.py`, `layoutlab_util.py`

Related: `docs/units_and_coordinates.md`, `docs/design_decisions/DD-003-json-only-communication.md`

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

Parsing implementation: `layoutlab_util.parse_commands_payload()`

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
    "length": 12,
    "width": 20,
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

See `generators/bed_basic.md` for full documentation.

| Parameter | Default | Unit | Description |
|---|---|---|---|
| `name` | `"BED_basic"` | — | Prefix for all component object names |
| `location` | `[0, 0, 0]` | Blender units | Min corner of footprint at floor (see units doc) |
| `length` | `20` | Blender units | Extent along **+X** (min 3) |
| `width` | `12` | Blender units | Extent along **+Y** (min 3) |
| `collection` | `"layout_tests"` | — | Target collection |
| `head_side` | `"y_max"` | — | `y_max`, `y_min`, `x_max`, `x_min` |
| `leg_height` | `2.5` | Blender units | — |
| `frame_height` | `1.0` | Blender units | — |
| `mattress_height` | `2.0` | Blender units | — |
| `rail_thickness` | `0.35` | Blender units | Capped at 20% of width/length |
| `post_size` | `0.45` | Blender units | Capped at 25% of width/length |
| `mattress_inset` | `0.45` | Blender units | Capped at 20% of width/length |
| `headboard_height` | `4.2` | Blender units | — |
| `footboard_height` | `2.2` | Blender units | — |
| `frame_color` | `[0.72, 0.55, 0.35, 1]` | RGBA 0–1 | — |
| `mattress_color` | `[0.86, 0.86, 0.82, 0.65]` | RGBA 0–1 | — |
| `pillow_color` | `[0.95, 0.95, 0.92, 1]` | RGBA 0–1 | — |

**Component roles** set on meshes (`layoutlab_role`):

`bed_post`, `bed_frame`, `bed_mattress`, `bed_headboard`, `bed_footboard`, `bed_pillow`, `label`

**Standard size example:** `length: 12, width: 20` → 120 × 200 cm at 1 unit = 10 cm.

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

Same fields as `create_box`, except:

| Aspect | Value |
|---|---|
| `role` | Always `"clearance"` (ignores input) |
| Default `color` | `[0.2, 0.8, 1.0, 0.22]` |
| Default `display_type` | `"WIRE"` |
| Default `dimensions[2]` | `0.1` |

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

**Note:** moves **one** Blender object. Generated furniture consists of many meshes — moving the logical bed requires moving each component or re-running the generator. `[PLANNED]` semantic/group move.

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

## 5.12 Planned Commands

| Action | Purpose |
|---|---|
| `regenerate` | Update params on existing logical object |
| `run_generator_batch` | Shared undo group |
| `set_parameter` | Param change + regenerate |
| `analyze_layout` | Constraint/clearance analysis |
| `compare_variants` | Layout diff |
| `create_collection` | Collection management |
| `group_objects` | Semantic object identity |

------------------------------------------------------------------------

# 6. Scene Export (Plugin → AI)

## 6.1 Schema `[IMPLEMENTED]`

```json
{
  "layoutlab_version": "0.5.0",
  "unit": "METRIC",
  "unit_scale": 1.0,
  "scene": "Scene",
  "generator_dir": "/path/to/layoutlab_generators",
  "generators": [],
  "note": "Coordinates/dimensions are Blender units. In Alexander's room: 1 unit ≈ 10 cm.",
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
  "custom_properties": { "layoutlab_role": "bed_mattress" }
}
```

| Field | Notes |
|---|---|
| `location` | Object origin; 4 decimal places |
| `dimensions` | World-space AABB size |
| `world_bbox_corners` | 8 world corners |
| `custom_properties` | string/int/float/bool only |

Semantic grouping (`layoutlab_object_id`, generator params on export): `[PLANNED]`

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

All command coordinates and dimensions are **Blender scene units** — never auto-converted.

**Project convention:** 1 unit ≈ 10 cm in the reference room.

Full specification: **`docs/units_and_coordinates.md`**

------------------------------------------------------------------------

# 9. Custom Properties

## 9.1 `layoutlab_role` `[IMPLEMENTED]`

Set by `create_box`, `create_clearance`, `create_label`, and generators.

Examples: `bed_mattress`, `bed_post`, `clearance`, `label`

## 9.2 Planned Identity Schema

`layoutlab_object_id`, `layoutlab_generator`, `layoutlab_params`, `layoutlab_component` — `[PLANNED]`

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
        "length": 12,
        "width": 20,
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
        "width": 20,
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
