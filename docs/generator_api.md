# LayoutLab Generator API Reference

Version: 0.5.0 (Contract)

> Functions available to generators via `generate(params, api)`.
> Source: `layoutlab/api/` (after Phase C split) · implemented in v0.5.0

**Status markers:** `[IMPLEMENTED]` · `[EXCEPTION]` · `[PLANNED]`

Related: `LayoutLab_Generator_Specification.md`, `docs/json_protocol.md`

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

# 2. API Dict Keys (v0.5)

| Key | Type | Status |
|---|---|---|
| `create_box` | function | `[IMPLEMENTED]` |
| `create_label` | function | `[IMPLEMENTED]` |
| `ensure_material` | function | `[IMPLEMENTED]` |
| `get_or_create_collection` | function | `[IMPLEMENTED]` |
| `delete_collection_objects` | function | `[IMPLEMENTED]` |
| `delete_prefix` | function | `[IMPLEMENTED]` |
| `math` | module | `[IMPLEMENTED]` |
| `bpy` | module | `[EXCEPTION]` — prefer API functions |

------------------------------------------------------------------------

# 3. Geometry

## 3.1 `create_box` `[IMPLEMENTED]`

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

## 3.2 `create_label` `[IMPLEMENTED]`

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

## 3.3 `create_clearance` `[PLANNED]`

Wrapper planned for clearance boxes (wireframe, `role="clearance"`).  
Until then, use `create_box(..., role="clearance", display_type="WIRE")` or JSON `create_clearance`.

------------------------------------------------------------------------

# 4. Materials

## 4.1 `ensure_material` `[IMPLEMENTED]`

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

# 5. Collections

## 5.1 `get_or_create_collection` `[IMPLEMENTED]`

```python
col = api["get_or_create_collection"](name)
```

Creates collection if missing and links it to the scene root.

**Returns:** `bpy.types.Collection`

---

## 5.2 `delete_collection_objects` `[IMPLEMENTED]`

```python
api["delete_collection_objects"](collection_name)
```

Removes all objects in the collection. Collection itself remains.

**Returns:** `None`

---

## 5.3 `delete_prefix` `[IMPLEMENTED]`

```python
api["delete_prefix"](prefix)
```

Removes all scene objects whose names **start with** `prefix`.

**Returns:** `None`

**Typical use:** delete `{name}_*` before regenerating an object group.

------------------------------------------------------------------------

# 6. Standard Modules

## 6.1 `math` `[IMPLEMENTED]`

Standard Python `math` module (radians, min, max, …).

---

## 6.2 `bpy` `[EXCEPTION]`

Full Blender Python API exposed for v0.5 prototype only.

**Do not use in new generators** unless the LayoutLab API has no equivalent.  
Target: API-only access (see `docs/ARCHITECTURE.md` §7).

------------------------------------------------------------------------

# 7. Planned API Functions

| Function | Purpose |
|---|---|
| `create_clearance(...)` | Semantic clearance zone helper |
| `create_component(...)` | Named component with object-model metadata |
| `create_profile(...)` | 2D profile extrusion |
| `create_mesh(...)` | Arbitrary mesh from verts/faces |
| `set_object_metadata(...)` | Write `layoutlab_object_id`, params (see object_model.md) |

------------------------------------------------------------------------

# 8. Conventions for Generator Authors

1. **Naming:** `{params.name}_{component_suffix}` for all component objects.
2. **Roles:** Set `layoutlab_role` on every mesh (see `docs/object_model.md`).
3. **Collection:** Respect `params.get("collection", "layout_tests")`.
4. **Location:** Use `params.get("location", [0, 0, 0])` as footprint min corner.
5. **Return value:** Return a dict with at least `created`, `type`, and useful params (e.g. `size`).
6. **No UI:** Never create panels, operators, or read `bpy.context` for user state.

------------------------------------------------------------------------

# 9. Example (bed_basic pattern)

```python
def generate(params, api):
    name = params.get("name", "BED_basic")
    x, y, z = params.get("location", [0, 0, 0])
    collection = params.get("collection", "layout_tests")
    cb = api["create_box"]

    cb(f"{name}_mattress", [x, y, z], [10, 20, 2],
       [0.86, 0.86, 0.82, 0.65], collection, "bed_mattress", None)

    return {"created": name, "type": "bed_basic", "size": [10, 20]}
```

------------------------------------------------------------------------

# 10. Changelog

| Version | Date | Changes |
|---|---|---|
| 0.5.0 | 2026-07-10 | Initial API reference from v0.5 implementation |
