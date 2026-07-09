# LayoutLab Object Model

Version: 0.5.0 (Draft)

> How logical furniture objects are represented in Blender scenes today and where the model is going.

Related: `AI_CONTEXT.md`, `docs/generator_api.md`, `docs/json_protocol.md`

**Status markers:** `[IMPLEMENTED]` · `[PLANNED]`

------------------------------------------------------------------------

# 1. Conceptual Model

```
Room
└── Layout
    ├── Furniture Object     (e.g. one bed — logical unit)
    │   └── Generator + params
    │       └── Components   (mattress, legs, … — Blender meshes)
    ├── Architectural elements (door, window, …)
    └── Clearance areas
```

A **Furniture Object** is not one mesh. It is **generator + parameters + component meshes**.

------------------------------------------------------------------------

# 2. Current Representation (v0.5) `[IMPLEMENTED]`

## 2.1 Implicit grouping

Components share a **name prefix** from `params.name`:

```
BED_120x200_post_xmin_ymin
BED_120x200_mattress
BED_120x200_pillow_1
BED_120x200_label
```

To delete and recreate: `delete_prefix("BED_120x200")` then `run_generator` again.

**Limitation:** No persistent link from mesh back to generator params in the scene.

## 2.2 Custom property: `layoutlab_role` `[IMPLEMENTED]`

Set on every component by generators / API:

| Role (examples) | Meaning |
|---|---|
| `bed_post` | Bed corner post |
| `bed_frame` | Frame rail |
| `bed_mattress` | Mattress volume |
| `bed_headboard` | Headboard |
| `bed_footboard` | Footboard |
| `bed_pillow` | Pillow |
| `label` | Text label |
| `clearance` | Required free space (often wireframe) |
| `wall` | Architectural (manual JSON) |

Exported in scene JSON under `custom_properties.layoutlab_role`.

## 2.3 Generator return value `[IMPLEMENTED]`

```json
{
  "created": "BED_120x200",
  "type": "bed_basic",
  "size": [12, 20]
}
```

Printed to console only — **not** stored on scene objects yet.

## 2.4 Collections `[IMPLEMENTED]`

Objects placed in a Blender collection (default `layout_tests`).  
Collection is **not** the logical object identity — only organization.

------------------------------------------------------------------------

# 3. Target Representation `[PLANNED]`

Every component mesh from a generator should carry:

| Custom property | Type | Example | Purpose |
|---|---|---|---|
| `layoutlab_object_id` | string (UUID) | `"a1b2c3…"` | Groups all components of one logical object |
| `layoutlab_generator` | string | `"bed_basic"` | Source generator name |
| `layoutlab_generator_version` | string | `"0.1"` | Generator version at creation time |
| `layoutlab_params` | string (JSON) | `'{"length":12,...}'` | Full params for regeneration |
| `layoutlab_component` | string | `"mattress"` | Component id within object |
| `layoutlab_role` | string | `"bed_mattress"` | Fine-grained role (keep) |

### Example component (future export)

```json
{
  "name": "BED_120x200_mattress",
  "layoutlab": {
    "object_id": "uuid-here",
    "generator": "bed_basic",
    "generator_version": "0.1",
    "params": { "length": 12, "width": 20, "head_side": "y_max" },
    "component": "mattress",
    "role": "bed_mattress"
  }
}
```

### Enabled features

| Feature | Requires |
|---|---|
| `regenerate` command | `layoutlab_params` + `layoutlab_generator` |
| Semantic export to AI | `layoutlab` block on export |
| Move/rotate logical object | `layoutlab_object_id` grouping |
| Undo generator edit | stored params + generator name |
| Variant comparison | object_id + params diff |

------------------------------------------------------------------------

# 4. Naming Conventions `[IMPLEMENTED]`

Generators **must** follow this pattern (see `bed_basic`):

```
{params.name}_{component_suffix}
```

Examples:

| Suffix | Component |
|---|---|
| `_mattress` | Main sleeping surface |
| `_post_xmin_ymin` | Corner post (position in name) |
| `_pillow_1`, `_pillow_2` | Indexed components |
| `_label` | Text label |

Suffixes are generator-specific but must be **stable and documented** in `{generator}.md`.

------------------------------------------------------------------------

# 5. Clearance Objects `[IMPLEMENTED]`

Clearance is a **special component type**:

- `layoutlab_role = "clearance"`
- Often `display_type = WIRE`
- Semantically: required free space, not solid geometry
- Today: created via JSON `create_clearance` or manual API

Future: generators emit clearance automatically from rules (e.g. 70 cm bed access).

------------------------------------------------------------------------

# 6. Non-LayoutLab Objects

Scene export includes **all** meshes/curves — not only LayoutLab objects.

AI should use:

- `custom_properties.layoutlab_role` — LayoutLab component
- Absence of role — architectural/manual geometry (walls, floor, …)

Future filter: export only objects with `layoutlab_object_id` or `layoutlab_role`.

------------------------------------------------------------------------

# 7. Migration Path

| Phase | Change |
|---|---|
| v0.5 (now) | Name prefix + `layoutlab_role` only |
| v0.6 `[PLANNED]` | API `set_object_metadata()` writes full schema on `create_box` |
| v0.6 `[PLANNED]` | `regenerate` JSON command |
| v0.7 `[PLANNED]` | Semantic block in scene export |
| v0.8 `[PLANNED]` | Deprecate move-by-single-mesh for generated furniture |

Existing scenes without new properties remain valid — generators still work with prefix delete + re-run.

------------------------------------------------------------------------

# 8. bed_basic Reference

See `layoutlab/generators/bed_basic.md` for component list and roles.

Logical object: one `params.name`  
Typical component count: 14 (4 posts, 4 rails, mattress, head/foot board, 1–2 pillows, label)

------------------------------------------------------------------------

# 9. Changelog

| Version | Date | Changes |
|---|---|---|
| 0.5.0 | 2026-07-10 | Initial object model doc (as-built + target) |
