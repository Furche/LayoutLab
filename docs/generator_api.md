# LayoutLab Generator API Reference

Version: 0.6.0 (Contract)

> Functions available to generators via `generate(params, api)`.
> Source: `layoutlab/api/` (after Phase C split) · implemented in v0.5.0

**Status markers:** `[IMPLEMENTED]` · `[EXCEPTION]` · `[PLANNED]`

Related: `LayoutLab_Generator_Specification.md`, `docs/how_to_write_generators.md`, `docs/json_protocol.md`

------------------------------------------------------------------------

# 1. Overview

Every generator receives an **`api` dict** as the second argument to `generate(params, api)`.

Generators must use **only** these functions — not direct Blender scene manipulation unless no API exists (discouraged; see `bpy` exception below).

```python
def generate(params, api):
    cb = api["create_box"]
    cb("MY_obj", [0, 0, 0], [1, 1, 1], role="example")
```

------------------------------------------------------------------------

# 2. API Dict Keys (v0.6)

| Key | Type | Status |
|---|---|---|
| `begin_part` | function | `[IMPLEMENTED]` |
| `end_part` | function | `[IMPLEMENTED]` |
| `finish` | function | `[IMPLEMENTED]` |
| `create_box` | function | `[IMPLEMENTED]` |
| `create_label` | function | `[IMPLEMENTED]` |
| `ensure_material` | function | `[IMPLEMENTED]` |
| `get_or_create_collection` | function | `[IMPLEMENTED]` |
| `delete_collection_objects` | function | `[IMPLEMENTED]` |
| `delete_prefix` | function | `[IMPLEMENTED]` |
| `math` | module | `[IMPLEMENTED]` |
| `bpy` | module | `[EXCEPTION]` — prefer API functions |

------------------------------------------------------------------------

# 3. Part Lifecycle `[IMPLEMENTED]` (v0.6)

Generators structure furniture as **Parts**. Each Part may create many meshes; the API joins them into one Blender object.

## 3.1 `begin_part` `[IMPLEMENTED]`

```python
api["begin_part"](part_id, main=False, dynamic=False, role=None)
```

| Parameter | Type | Default | Description |
|---|---|---|---|
| `part_id` | str | required | Stable id (`"body"`, `"door_1"`, …) |
| `main` | bool | `False` | Exactly one Main Part per furniture piece |
| `dynamic` | bool | `False` | Moving Part — stays separate after finalize |
| `role` | str or None | `None` | Default `layoutlab_role` for the finalized Part |

**Returns:** `part_id`

Must be called before `create_box` / `create_label` during `execute_generator()`.

---

## 3.2 `end_part` `[IMPLEMENTED]`

```python
api["end_part"]()
```

Finalizes the current Part: joins build meshes → one object named `{params.name}_{part_id}`.

**Returns:** finalized `bpy.types.Object` or `None` if Part had no geometry.

---

## 3.3 `finish` `[IMPLEMENTED]`

```python
summary = api["finish"]()
```

Called once at the end of `generate()`:

- Closes any open Part
- Writes `layoutlab_*` metadata on all Part objects
- Parents non-main Parts to the Main Part (world transform preserved)
- Returns summary dict: `parts`, `main_part`, `object_count`

The engine also calls `finish()` if the generator omits it.

**Generators must not call `bpy.ops.object.join()`** — finalization is API-owned.

### Parenting and coordinates `[IMPLEMENTED]` (v0.6.1)

Generators place build meshes in **world coordinates** (absolute from `params.location`).
At `finish()`, non-main Parts are parented to the Main Part via
`parent_preserve_world_transform` in `layoutlab/api/transforms.py`:

- World matrix is preserved (no visible jump).
- `matrix_local = parent.matrix_world.inverted() @ child.matrix_world`
- Generators must **not** set `child.parent` or matrix hacks themselves.

See `docs/units_and_coordinates.md` §4.1 and DD-006.

See `docs/design_decisions/DD-006-parts-and-finalization.md`.

------------------------------------------------------------------------

# 4. Geometry

## 4.1 `create_box` `[IMPLEMENTED]`

```python
obj = api["create_box"](
    name,
    location,
    dimensions,
    color=(0.8, 0.8, 0.8, 1),
    collection="layout_tests",
    role=None,
    display_type=None,
)
```

Creates an axis-aligned box mesh.

| Parameter | Type | Default | Description |
|---|---|---|---|
| `name` | str | required | Unique Blender object name |
| `location` | `[x, y, z]` | required | Min corner of box (see units doc) |
| `dimensions` | `[dx, dy, dz]` | required | Size along X, Y, Z |
| `color` | `[r, g, b, a]` | `(0.8, 0.8, 0.8, 1)` | RGBA 0–1; falsy skips material |
| `collection` | str | `"layout_tests"` | Target collection |
| `role` | str or None | `None` | Sets custom property `layoutlab_role` |
| `display_type` | str or None | `None` | Blender display: `"WIRE"`, `"SOLID"`, `"BOUNDS"`, … |

**Returns:** `bpy.types.Object` (mesh)

**Notes:**

- Material name: `MAT_{name}` (shared if same name reused)
- Box geometry origin is min corner; object `location` is set to `location`

---

## 4.2 `create_label` `[IMPLEMENTED]`

```python
obj = api["create_label"](
    name,
    location,
    text,
    collection="layout_tests",
    size=0.35,
)
```

Creates a text curve object (FONT).

| Parameter | Type | Default |
|---|---|---|
| `name` | str | required |
| `location` | `[x, y, z]` | required |
| `text` | str | required |
| `collection` | str | `"layout_tests"` |
| `size` | float | `0.35` |

**Returns:** `bpy.types.Object` (curve)

**Side effects:** Always sets `layoutlab_role = "label"`.

---

## 4.3 `create_clearance` `[IMPLEMENTED]`

See [DD-007](../design_decisions/DD-007-clearance-zones.md).

```python
obj = api["create_clearance"](
    name,
    dimensions,
    local_location=[0, -6, 0],
    clearance_name="front_access",
    purpose="door_access",
    requirement="preferred",
    priority=0,
    params={"depth": 6.0},
    color=(0.2, 0.8, 1.0, 0.22),
    collection="layout_tests",
)
```

| Parameter | Type | Default | Description |
|---|---|---|---|
| `name` | str | — | Build mesh name |
| `dimensions` | `[dx, dy, dz]` | — | Box size |
| `local_location` | `[x, y, z]` | — | **Preferred:** Main Part local space |
| `location` | `[x, y, z]` | — | World space (standalone JSON / fallback) |
| `clearance_name` | str | **required** | Semantic id unique per furniture instance |
| `purpose` | str | `""` | Intent category |
| `requirement` | str | `"preferred"` | `required` \| `preferred` |
| `priority` | int | `0` | Higher = more important |
| `params` | dict | `None` | Generator-specific params (stored as JSON) |
| `color` | RGBA | blue transparent | Wire material |
| `collection` | str | `"layout_tests"` | Target collection |
| `display_type` | str | `"WIRE"` | Blender display mode |

**Returns:** `bpy.types.Object`

**Side effects:** Sets `layoutlab_clearance_id`, `layoutlab_clearance_name`, `layoutlab_clearance_requirement`, `layoutlab_clearance_params` (includes `local_transform`), `layoutlab_role = "clearance"`, `show_in_front = True`.

JSON command `create_clearance` uses the same implementation.

------------------------------------------------------------------------

# 5. Materials

## 5.1 `ensure_material` `[IMPLEMENTED]`

```python
mat = api["ensure_material"](name, color)
```

| Parameter | Type | Description |
|---|---|---|
| `name` | str | Material name in `bpy.data.materials` |
| `color` | `[r, g, b, a]` | Diffuse color; alpha `< 1` enables transparency nodes |

**Returns:** `bpy.types.Material`

Usually called indirectly via `create_box(..., color=...)`.

------------------------------------------------------------------------

# 6. Collections

## 6.1 `get_or_create_collection` `[IMPLEMENTED]`

```python
col = api["get_or_create_collection"](name)
```

Creates collection if missing and links it to the scene root.

**Returns:** `bpy.types.Collection`

---

## 6.2 `delete_collection_objects` `[IMPLEMENTED]`

```python
api["delete_collection_objects"](collection_name)
```

Removes all objects in the collection. Collection itself remains.

**Returns:** `None`

---

## 6.3 `delete_prefix` `[IMPLEMENTED]`

```python
api["delete_prefix"](prefix)
```

Removes all scene objects whose names **start with** `prefix`.

**Returns:** `None`

**Typical use:** delete `{name}_*` before regenerating an object group.

------------------------------------------------------------------------

# 7. Standard Modules

## 7.1 `math` `[IMPLEMENTED]`

Standard Python `math` module (radians, min, max, …).

---

## 7.2 `bpy` `[EXCEPTION]`

Full Blender Python API exposed for v0.5 prototype only.

**Do not use in new generators** unless the LayoutLab API has no equivalent.  
Target: API-only access (see `docs/ARCHITECTURE.md` §7).

------------------------------------------------------------------------

# 8. Automatic Object Metadata `[IMPLEMENTED]` (v0.6)

When `execute_generator()` runs, the engine activates a metadata context and a Part session.

- **Build meshes** are temporary; they are registered to the active Part.
- **At `finish()`**, metadata is written to each **finalized Part object**:
  - `layoutlab_object_id`, `layoutlab_generator`, `layoutlab_generator_version`
  - `layoutlab_params` (JSON string of full params)
  - `layoutlab_part`, `layoutlab_part_type` (`main` / `static` / `dynamic`)
  - `layoutlab_component` (same as part id)
  - `layoutlab_role` (from Part `role` or per-mesh role)

Generators do **not** call metadata functions directly.  
Implementation: `layoutlab/api/parts.py`, `layoutlab/api/metadata.py`, `layoutlab/engine/executor.py`.

------------------------------------------------------------------------

# 9. Planned API Functions

| Function | Purpose |
|---|---|
| `create_clearance(...)` | Semantic clearance zone helper |
| `create_component(...)` | Named component with explicit metadata |
| `create_profile(...)` | 2D profile extrusion |
| `create_mesh(...)` | Arbitrary mesh from verts/faces |

------------------------------------------------------------------------

# 10. Conventions for Generator Authors

1. **Parts:** One `begin_part` … `end_part` block per logical Part; exactly one `main=True`.
2. **Build mesh names:** `{params.name}__{part_id}_{detail}` (double underscore before part).
3. **Final object names:** `{params.name}_{part_id}` — assigned by API, not by generator.
4. **Roles:** Pass `role=` on `begin_part` and/or per `create_box` call.
5. **Collection:** Respect `params.get("collection", "layout_tests")`.
6. **Location:** Use `params.get("location", [0, 0, 0])` as footprint min corner.
7. **Return value:** Return dict with `created`, `type`, and useful params; engine adds `object_id`, `parts`, `main_part`.
8. **No UI / no bpy.ops:** Never create panels or call Blender operators from generators.

------------------------------------------------------------------------

# 11. Example (bed_basic pattern)

```python
def generate(params, api):
    name = params.get("name", "BED_basic")
    x, y, z = params.get("location", [0, 0, 0])
    collection = params.get("collection", "layout_tests")
    cb = api["create_box"]
    bp, ep = api["begin_part"], api["end_part"]

    bp("body", main=True, role="bed_frame")
    cb(f"{name}__body_frame", [x, y, z], [10, 20, 1], [...], collection, "bed_frame", None)
    ep()

    bp("mattress", role="bed_mattress")
    cb(f"{name}__mattress", [x, y, z + 1], [10, 20, 2], [...], collection, "bed_mattress", None)
    ep()

    api["finish"]()
    return {"created": name, "type": "bed_basic", "size": [10, 20]}
```

------------------------------------------------------------------------

# 12. Changelog

| Version | Date | Changes |
|---|---|---|
| 0.6.1 | 2026-07-10 | Parenting coordinate model documented |
| 0.6.0 | 2026-07-10 | `begin_part`, `end_part`, `finish`; Part-based metadata |
| 0.5.0 | 2026-07-10 | Initial API reference from v0.5 implementation |
