# LayoutLab Object Model

Version: 0.6.0

> How logical furniture objects are represented in Blender scenes.

Related: `AI_CONTEXT.md`, `docs/generator_api.md`, `docs/design_decisions/DD-006-parts-and-finalization.md`, `docs/json_protocol.md`

**Status markers:** `[IMPLEMENTED]` · `[PLANNED]`

------------------------------------------------------------------------

# 1. Conceptual Model

```
Room
└── Layout
    └── Furniture Object          (one bed, one wardrobe — logical unit)
        ├── Generator + params
        └── Parts                 (body, mattress, door_1, …)
            └── Meshes            (build-time only — joined per Part)
```

A **Furniture Object** is **generator + parameters + finalized Part objects**.

During a generator run, authors think in **many meshes** (posts, rails, shelves).  
After finalization, the scene contains **one Blender object per Part**.

------------------------------------------------------------------------

# 2. Hierarchy: Furniture → Parts → Meshes

| Level | Lifetime | Blender object? | Example |
|---|---|---|---|
| **Furniture** | Persistent | No (logical) | `BED_120` with shared `layoutlab_object_id` |
| **Part** | Persistent | **Yes** — one object per Part | `BED_120_body`, `BED_120_mattress` |
| **Mesh** | Build-time only | Temporary until Part join | `BED_120__body_post_xmin_ymin` |

### Main Part

Every furniture piece has exactly one **Main Part** (typically `body`):

- Represents the structural body (frame, carcass).
- This is what the user **clicks and moves** in Blender.
- Name: `{params.name}_{part_id}` → `BED_120_body`.

### Static Parts

Non-main Parts that are not animated (mattress, pillows, label, clearance):

- Finalized to one object each.
- **Parented to the Main Part** (world transform preserved).
- Moving the Main Part moves the entire piece.

### Dynamic Parts

Moving elements (doors, drawers, hinges, castors):

- Remain **separate Blender objects** after finalization (`dynamic=True`).
- Also **parented to the Main Part** — follow when the body moves.
- Can be animated independently (door rotation, drawer slide).

See **DD-006** for rejected alternatives (root Empty, selection promotion).

------------------------------------------------------------------------

# 3. Scene Representation (v0.6) `[IMPLEMENTED]`

## 3.1 Example: bed_basic

After `run_generator`:

```
BED_120_body          layoutlab_part: body       layoutlab_part_type: main
  ├─ BED_120_mattress layoutlab_part: mattress   layoutlab_part_type: static
  ├─ BED_120_pillow_1 layoutlab_part: pillow_1   layoutlab_part_type: static
  ├─ BED_120_pillow_2 layoutlab_part: pillow_2   layoutlab_part_type: static
  └─ BED_120_label    layoutlab_part: label      layoutlab_part_type: static
```

The `body` mesh internally joined: 4 posts + 4 rails + headboard + footboard.

## 3.2 Example: wardrobe_basic

```
WARDROBE_80_body       main
  ├─ WARDROBE_80_door_1   dynamic
  ├─ WARDROBE_80_door_2   dynamic
  ├─ WARDROBE_80_clearance static
  └─ WARDROBE_80_label    static
```

Doors stay separate for future animation; shelves are joined into `body`.

------------------------------------------------------------------------

# 4. Custom Properties `[IMPLEMENTED]`

Every **finalized Part object** carries:

| Property | Type | Example | Purpose |
|---|---|---|---|
| `layoutlab_object_id` | string (UUID) | `"a1b2c3…"` | Groups all Parts of one furniture piece |
| `layoutlab_generator` | string | `"bed_basic"` | Source generator |
| `layoutlab_generator_version` | string | `"0.2"` | Generator version at creation |
| `layoutlab_params` | string (JSON) | `'{"length":12,...}'` | Full params for regeneration |
| `layoutlab_part` | string | `"body"` | Part id |
| `layoutlab_part_type` | string | `"main"` / `"static"` / `"dynamic"` | Part category |
| `layoutlab_component` | string | `"body"` | Same as part id (export compat) |
| `layoutlab_role` | string | `"bed_frame"` | Fine-grained role |

Build-time mesh names use `{name}__{part}_{detail}` (double underscore) and are **not** exported as separate logical objects.

### Export block `[IMPLEMENTED]`

```json
{
  "name": "BED_120_mattress",
  "layoutlab": {
    "object_id": "uuid-here",
    "generator": "bed_basic",
    "generator_version": "0.2",
    "params": { "length": 12, "width": 20 },
    "component": "mattress",
    "part": "mattress",
    "part_type": "static",
    "role": "bed_mattress"
  }
}
```

------------------------------------------------------------------------

# 5. Generator Lifecycle vs API Responsibilities

| Responsibility | Generator | LayoutLab API |
|---|---|---|
| Part structure (`body`, doors, …) | yes | — |
| Build meshes per Part | yes (`create_box`, …) | registers meshes |
| Join meshes into Part object | **no** | yes (`end_part` / `finish`) |
| Parent Parts to Main Part | **no** | yes (`finish`) |
| Write `layoutlab_*` metadata | **no** | yes (`finish`) |
| `bpy.ops.object.join()` | **never** | yes (internal) |

Generator pattern:

```python
api["begin_part"]("body", main=True, role="bed_frame")
# … create_box calls …
api["end_part"]()
api["finish"]()
```

------------------------------------------------------------------------

# 6. Operations

| Operation | Behaviour |
|---|---|
| **Move furniture** | Select and move **Main Part** — children follow |
| **Delete furniture** | `delete_prefix(params.name)` or delete by `layoutlab_object_id` |
| **Regenerate** | `regenerate` command — same `object_id`, new Part objects |
| **Export to AI** | One entry per Part object with `layoutlab` block |

------------------------------------------------------------------------

# 7. Clearance Parts `[IMPLEMENTED]`

Clearance may be its own Part (e.g. `clearance` on `wardrobe_basic`):

- `layoutlab_role = "clearance"`
- Often wireframe display
- Parented to Main Part like other static Parts

------------------------------------------------------------------------

# 8. Migration Path

| Phase | Change |
|---|---|
| v0.5.0 | Name prefix + `layoutlab_role`; many meshes per furniture |
| v0.5.1 | `layoutlab_object_id`, params, `regenerate`, export block |
| v0.6.0 `[IMPLEMENTED]` | Parts model — join per Part, Main/Dynamic, parenting |
| v0.7 `[PLANNED]` | JSON `move` by `object_id` (move Main Part + children) |

Legacy scenes without Parts: still deletable via prefix; `regenerate` rebuilds with Parts.

------------------------------------------------------------------------

# 9. Reference Generators

| Generator | Main Part | Dynamic Parts | Static Parts |
|---|---|---|---|
| `bed_basic` | `body` | — | `mattress`, `pillow_*`, `label` |
| `wardrobe_basic` | `body` | `door_*` | `clearance`, `label` |

Details: `layoutlab/generators/bed_basic.md`, `wardrobe_basic.md`

------------------------------------------------------------------------

# 10. Changelog

| Version | Date | Changes |
|---|---|---|
| 0.6.0 | 2026-07-10 | Parts hierarchy; join-on-finalize; main/dynamic; parenting |
| 0.5.1 | 2026-07-10 | Semantic metadata; regenerate; export `layoutlab` block |
| 0.5.0 | 2026-07-10 | Initial object model doc |
