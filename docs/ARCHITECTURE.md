# LayoutLab Architecture

Version: 0.5.0 (Living Document)

> This document maps **what exists today** (v0.5 prototype) against **where the
> project is going** (target architecture). When code and documentation disagree,
> discuss the architecture first — then change the code.
>
> **Status markers:**
>
> - `[IMPLEMENTED]` — exists in `layoutlab/` addon today
> - `[PLANNED]` — agreed direction, not yet built
> - `[EXCEPTION]` — deliberate v0.5 shortcut; must not become permanent without a DD

Related documents:

- `AI_CONTEXT.md` — mental model and vocabulary
- `docs/json_protocol.md` — AI ↔ plugin JSON contract
- `docs/documentation_map.md` — which document to update when (maintenance index)
- `LayoutLab_Master_Design_Document.md` — vision, roadmap, team roles
- `LayoutLab_Generator_Specification.md` — generator authoring rules

------------------------------------------------------------------------

# 1. System Purpose

LayoutLab is a **semantic, parametric interior planning engine**.

Blender is the current editor. It is not the product.

```
User Intent → Object Knowledge → Generator → Components → Geometry → Mesh
```

Geometry is the last step. See `AI_CONTEXT.md` for the full mental model.

------------------------------------------------------------------------

# 2. Target Architecture

Five layers with strict responsibility boundaries. `[IMPLEMENTED]` as separate modules in `layoutlab/` (Phase C, 2026-07).

```
┌─────────────────────────────────────────────────────────┐
│  Layer 1: Blender UI                                    │
│  Panel, operators, generator browser                    │
│  Knows: user actions, scene context                     │
│  Does NOT know: furniture rules                         │
├─────────────────────────────────────────────────────────┤
│  Layer 2: Main Plugin                                   │
│  JSON import/export, command dispatch, logging          │
│  Knows: protocol, generator registry                    │
│  Does NOT know: how a bed works                         │
├─────────────────────────────────────────────────────────┤
│  Layer 3: Generator Engine                              │
│  Load, validate, execute generators                     │
│  Knows: generator lifecycle, API injection              │
│  Does NOT know: UI, specific furniture                  │
├─────────────────────────────────────────────────────────┤
│  Layer 4: Generators                                    │
│  Parametric object knowledge                            │
│  Knows: one object type (bed, wardrobe, …)              │
│  Does NOT know: UI, scene analysis, other generators    │
├─────────────────────────────────────────────────────────┤
│  Layer 5: Scene                                         │
│  Blender objects, collections, custom properties        │
│  Meshes are the current representation of knowledge     │
└─────────────────────────────────────────────────────────┘
```

**Communication rule:** layers talk only through defined interfaces (JSON protocol, Generator API). `[IMPLEMENTED]` for JSON + API and module boundaries.

## 2.1 AI execution boundary `[PROPOSED]` — DD-009

A specialized AI *could* drive Blender directly via Python. LayoutLab **still requires a plugin** because core behaviour must be deterministic, testable, and model-independent.

```
┌─────────────────────────────────────────────────────────┐
│  Planning layer (AI / user intent)                      │
│  WHAT: which furniture, params, layout variants         │
├─────────────────────────────────────────────────────────┤
│  LayoutLab execution layer (plugin + engine)            │
│  HOW: object_id, parts, parenting, regenerate,          │
│       clearances, analyze_layout, export                │
├─────────────────────────────────────────────────────────┤
│  Blender (editor host)                                  │
└─────────────────────────────────────────────────────────┘
```

| Mode | Status | Description |
|---|---|---|
| **Standard** | Today | AI → JSON protocol → plugin → Blender |
| **Bridge** | Future Idea | Local agent; same ops, no clipboard — see DD-009 |
| **Expert** | Future Idea | Opt-in direct bpy; not production default |

Full decision: [DD-009](design_decisions/DD-009-ai-execution-boundary.md). Transport detail: [DD-003](design_decisions/DD-003-json-only-communication.md).

------------------------------------------------------------------------

# 3. As-Built: v0.5 Prototype

## 3.1 Current Repository Layout `[IMPLEMENTED]`

```
LayoutLab/
├── 00_READ_THIS_FIRST.md
├── AI_CONTEXT.md
├── LayoutLab_Manifest.md
├── LayoutLab_Master_Design_Document.md
├── LayoutLab_Generator_Specification.md
├── layoutlab/                         ← Blender addon package
│   ├── __init__.py                    # bl_info, register(), re-exports
│   ├── util.py
│   ├── diagnostics.py
│   ├── plugin/                        # panel, operators, properties
│   ├── engine/                        # registry, executor
│   ├── api/                           # geometry, materials, collections
│   ├── protocol/                      # commands, export
│   └── generators/
│       └── bed_basic.py
├── tests/
│   └── test_layoutlab_util.py
└── docs/
    ├── documentation_map.md
    ├── json_protocol.md
    ├── generator_api.md
    ├── how_to_write_generators.md    [IMPLEMENTED]
    ├── object_model.md
```

## 3.2 Module Map `[IMPLEMENTED]`

Layers are split into modules (Phase C):

| Module | Target layer | Responsibility |
|---|---|---|
| `layoutlab/plugin/` | Blender UI + thin orchestration | Panel, operators, browser properties |
| `layoutlab/protocol/` | Plugin (JSON) | Scene export, command parser, action dispatch |
| `layoutlab/engine/` | Engine | Generator paths, metadata, `exec()` loader, `execute_generator()` |
| `layoutlab/api/` | API | `create_box`, `create_label`, collections, materials, delete helpers |
| `layoutlab/util.py` | Shared | Pure-Python JSON parsing, metadata inference (testable without bpy) |

## 3.3 Runtime Layout `[IMPLEMENTED]`

| Location | Contents |
|---|---|
| Git repo | Addon source + documentation |
| Blender addons dir | Installed `layoutlab/` folder (copy or symlink) `[IMPLEMENTED]` |
| `…/scripts/addons/layoutlab_generators/` | Runtime generator `.py` files (outside repo) `[IMPLEMENTED]` `[EXCEPTION]` |
| Blender scene | Meshes, collections, `layoutlab_role` custom props `[IMPLEMENTED]` |

## 3.4 What v0.5 Actually Delivers

Phase 1 features from the Master Design Document:

| Feature | Status |
|---|---|
| JSON command input (clipboard / text block) | `[IMPLEMENTED]` |
| Scene JSON export | `[IMPLEMENTED]` |
| Generator browser (asset-browser-like popup) | `[IMPLEMENTED]` |
| Parametric `bed_basic` generator | `[IMPLEMENTED]` |
| Generator save/load via JSON + UI | `[IMPLEMENTED]` |
| Clearance boxes via `create_clearance` | `[IMPLEMENTED]` |
| Separated module structure | `[IMPLEMENTED]` |
| Generators versioned in repo | `[IMPLEMENTED]` (bundled in `layoutlab/generators/`, synced on register) |
| Semantic object identity in scene | `[IMPLEMENTED]` (v0.5.1) |
| Parts model + join-on-finalize | `[IMPLEMENTED]` (v0.6) |
| Automated tests | `[IMPLEMENTED]` (util/metadata; bpy integration manual) |

------------------------------------------------------------------------

# 4. Data Flow

## 4.1 AI → Scene (Commands) `[IMPLEMENTED]`

```
ChatGPT / Agent
    │  JSON { "commands": [...] }
    ▼
Clipboard or Text Block
    │  Apply Commands operator
    ▼
apply_commands_json()
    │  sequential dispatch
    ▼
apply_single_command()  ──→  run_generator ──→ execute_generator()
    │                              │
    │                              ▼
    │                         generate(params, api)
    │                              │
    ▼                              ▼
create_box / move / …         Geometry API ──→ Blender Scene
```

See `docs/json_protocol.md` for the full command reference.

## 4.2 Scene → AI (Export) `[IMPLEMENTED]`

```
Blender Scene (objects, collections)
    │
    ▼
object_to_dict()  per object
    │
    ▼
layout_export_json()  + generator metadata
    │
    ▼
System Clipboard  →  ChatGPT / Agent
```

Export is **geometry-centric**. Generator name and params are not yet attached to exported objects. `[PLANNED]`

## 4.3 Generator Lifecycle `[IMPLEMENTED]`

```
                    ┌──────────────────────────────────┐
                    │  layoutlab_generators/*.py       │
                    │  (Blender user scripts dir)      │
                    └───────────────┬──────────────────┘
                                    │
          save_generator (JSON)     │     Install Default / Save from Text
          ──────────────────────────┤─────────────────────────────
                                    │
                                    ▼
                         list_generators_meta()
                                    │
                    ┌───────────────┴──────────────┐
                    ▼                              ▼
            Generator Browser              Scene export
                    │
                    ▼
            execute_generator(name, params)
                    │
                    ▼
              exec(code) → generate(params, api)
                    │
                    ▼
              Meshes in Blender collection
```

### Target lifecycle `[PLANNED]`

```
Repo generators/  →  validate  →  install/sync  →  runtime cache
                                         │
                                         ▼
                              regenerate(object_id, new_params)
```

------------------------------------------------------------------------

# 5. Subsystem Responsibilities

## 5.1 Main Plugin `[IMPLEMENTED]`

| Responsibility | Module / functions |
|---|---|
| JSON parsing | `protocol/commands.py` — `apply_commands_json`, `get_commands_text` |
| Command routing | `protocol/commands.py` — `apply_single_command` |
| Scene export | `protocol/export.py` — `layout_export_json`, `object_to_dict` |
| Generator file management | `engine/registry.py` — save/load; delete via commands |
| Logging | `print()` to Blender console |

Does **not** contain furniture logic. `[IMPLEMENTED]`

## 5.2 Generator Engine `[IMPLEMENTED]`

| Responsibility | Module / functions |
|---|---|
| Load generator source | `engine/registry.py` — `read_generator_code`; `engine/executor.py` — `exec()` |
| Inject API | `engine/executor.py` — `execute_generator` + `api/build_generator_api()` |
| Metadata discovery | `util.py` + `engine/registry.py` — `list_generators_meta` |
| Name validation | `util.py` — `sanitize_generator_name` |

Does **not** contain UI. `[IMPLEMENTED]`

## 5.3 LayoutLab API `[IMPLEMENTED]`

Functions passed to generators via the `api` dict (`layoutlab/api/`):

| Function | Purpose |
|---|---|
| `begin_part` | Start a furniture Part (main / dynamic / static) |
| `end_part` | Finalize Part — join build meshes |
| `finish` | Metadata, parenting, session close |
| `create_box` | Axis-aligned mesh box |
| `create_label` | Text curve label |
| `ensure_material` | Get or create colored material |
| `get_or_create_collection` | Collection management |
| `delete_collection_objects` | Bulk delete in collection |
| `delete_prefix` | Bulk delete by name prefix |
| `bpy` | `[EXCEPTION]` direct Blender access exposed |
| `math` | Standard math module |

Planned additions: `create_component`, `create_profile`, `create_mesh`. `[PLANNED]`  
`create_clearance` — `[IMPLEMENTED]` v0.7 (DD-007).

Full reference: `docs/generator_api.md` `[IMPLEMENTED]`

## 5.4 Generators `[IMPLEMENTED]` (partial)

- Bundled template: `layoutlab/generators/bed_basic.py` (synced to user dir on register)
- User-created generators stored as `.py` files outside repo
- Contract: `generate(params, api)` + metadata constants
- Spec: `LayoutLab_Generator_Specification.md`

## 5.5 Blender UI `[IMPLEMENTED]`

| UI element | Module / operator |
|---|---|
| Sidebar panel | `plugin/panel.py` — `LAYOUTLAB_PT_panel` |
| Copy scene / selected | `layoutlab.copy_scene` |
| Apply commands | `layoutlab.apply_commands` |
| Generator browser popup | `layoutlab.open_generator_browser` |
| Generator CRUD | new / load / save / delete operators |
| Quick test | `layoutlab.run_selected_generator` |

Design target: Asset Browser feeling. `[IMPLEMENTED]` basic list + filter; thumbnails, favorites `[PLANNED]`

------------------------------------------------------------------------

# 6. Object Model

## 6.1 Conceptual Hierarchy `[IMPLEMENTED]` (v0.6)

```
Room
└── Layout
    └── Furniture Object (e.g. Bed)
        ├── Generator + params
        └── Parts (body, mattress, door_1, …)
            └── Meshes (build-time only)
```

## 6.2 Scene Representation `[IMPLEMENTED]` (v0.6)

A bed is **several Part objects** sharing one `layoutlab_object_id`:

```
BED_120_body          layoutlab_part_type: main
  ├─ BED_120_mattress layoutlab_part_type: static
  ├─ BED_120_pillow_1
  └─ BED_120_label
```

The `body` object is joined from many build meshes (posts, rails, boards).  
User selects and moves `body` — child Parts follow.

## 6.3 Metadata on Part Objects `[IMPLEMENTED]`

| Custom property | Example | Purpose |
|---|---|---|
| `layoutlab_object_id` | `"uuid-…"` | Groups components into one logical object |
| `layoutlab_generator` | `"bed_basic"` | Source generator |
| `layoutlab_generator_version` | `"0.1"` | Generator version used |
| `layoutlab_params` | `{"length": 12, …}` | JSON params for regeneration |
| `layoutlab_part` | `"body"` | Part id |
| `layoutlab_part_type` | `"main"` | main / static / dynamic |
| `layoutlab_component` | `"mattress"` | Same as part id (export compat) |
| `layoutlab_role` | `"bed_mattress"` | `[IMPLEMENTED]` legacy / fine-grained role |

This enables: regenerate, undo, variants, constraint checking.

Detailed schema: `docs/object_model.md` `[IMPLEMENTED]`

------------------------------------------------------------------------

# 7. Deliberate v0.5 Exceptions

These shortcuts are **accepted for the prototype** but must be resolved before scaling to 200 generators.

| Exception | Current behaviour | Target | Risk if kept |
|---|---|---|---|
| **Monolith file** | ~~All layers in one `.py`~~ Split into `layoutlab/` package (Phase C) | Maintain module boundaries | Resolved 2026-07 |
| **Generators outside repo** | User scripts dir | `generators/` in repo | No version control, no review, no CI |
| **`exec()` loading** | Dynamic execution of generator code | Import-based loader with validation | Security, no static analysis |
| **`bpy` in generator API** | Generators can call Blender directly | API-only access | Breaks Blender independence; untestable |
| **Implicit object grouping** | Name prefix convention | `layoutlab_object_id` | Cannot regenerate or update params |
| **Geometry-only export** | Bboxes and roles | Full semantic export | AI cannot reason about intent |
| **No protocol version** | `layoutlab_version` in export only | Bidirectional version field | Silent breaking changes |

Each resolved exception should produce a Design Decision document (`docs/design_decisions/DD-xxx.md`).

------------------------------------------------------------------------

# 8. Target Repository Layout

`[IMPLEMENTED]` — current layout matches target (browser UI lives in `plugin/operators.py` + `plugin/panel.py` instead of separate `browser.py`):

```
LayoutLab/
├── README.md
├── CHANGELOG.md
├── DEVLOG.md
├── 00_READ_THIS_FIRST.md
├── AI_CONTEXT.md
├── LayoutLab_Manifest.md
├── LayoutLab_Master_Design_Document.md
├── LayoutLab_Generator_Specification.md
│
├── layoutlab/                          # Blender addon package
│   ├── __init__.py                     # bl_info, register(), unregister()
│   ├── plugin/
│   │   ├── panel.py                    # Sidebar panel
│   │   ├── operators.py                # Scene exchange operators
│   │   └── browser.py                  # Generator browser UI
│   ├── engine/
│   │   ├── loader.py                   # Load + validate generators
│   │   ├── executor.py                 # execute_generator()
│   │   └── registry.py                 # Metadata, list, discover
│   ├── api/
│   │   ├── geometry.py                 # create_box, create_label, …
│   │   ├── materials.py                # ensure_material
│   │   └── collections.py              # get_or_create_collection, delete
│   └── protocol/
│       ├── commands.py                 # apply_single_command, dispatch
│       └── export.py                   # layout_export_json, object_to_dict
│
├── generators/                         # Version-controlled generators
│   ├── bed_basic.py
│   └── …
│
├── tests/
│   ├── test_protocol.py
│   ├── test_registry.py
│   └── test_generators.py
│
└── docs/
    ├── documentation_map.md            [IMPLEMENTED]
    ├── ARCHITECTURE.md                 # this file
    ├── json_protocol.md
    ├── generator_api.md                [IMPLEMENTED]
    ├── object_model.md                 [IMPLEMENTED]
    ├── units_and_coordinates.md        [IMPLEMENTED]
    └── design_decisions/
        ├── DD-001-generators-are-parametric-assets.md
        ├── DD-002-generators-rebuild-mesh.md
        ├── DD-003-json-only-communication.md
        ├── DD-004-asset-browser-ui.md
        └── DD-005-generator-metadata.md
```

### Dependency direction (must not be violated)

```
UI  →  Plugin  →  Engine  →  API  →  bpy
                  ↓
              Generators  →  API (never UI, never Plugin)
```

Generators import nothing from `plugin/`. `[IMPLEMENTED]` rule; enforced by convention.

------------------------------------------------------------------------

# 9. Migration Plan

## Phase A — Documentation foundation `[COMPLETE]`

| Step | Document | Status |
|---|---|---|
| A.1 | `docs/json_protocol.md` | `[IMPLEMENTED]` |
| A.2 | `docs/ARCHITECTURE.md` | `[IMPLEMENTED]` |
| A.3 | `README.md` | `[IMPLEMENTED]` |
| A.4 | `docs/design_decisions/DD-001..005` | `[IMPLEMENTED]` |
| A.5 | `docs/units_and_coordinates.md` | `[IMPLEMENTED]` |
| A.6 | `docs/generator_api.md` | `[IMPLEMENTED]` |
| A.7 | `docs/object_model.md` | `[IMPLEMENTED]` |

**Gate:** Do not split the monolith until A.1–A.5 are done. **Passed.**

## Phase B — Structure without behaviour change `[COMPLETE]`

1. Extract `generators/bed_basic.py` from embedded template string — `[IMPLEMENTED]`
2. Add `tests/` for protocol parsing and metadata inference — `[IMPLEMENTED]`
3. Add `CHANGELOG.md` and `DEVLOG.md` — `[IMPLEMENTED]`
4. Sync mechanism: repo generators → runtime dir — `[IMPLEMENTED]` (on register, if missing)

**Gate:** All v0.5 behaviour preserved; tests green.

## Phase C — Monolith split `[COMPLETE]`

1. Create `layoutlab/` package with modules per Section 8 — `[IMPLEMENTED]`
2. Replace `layoutlab_chatgpt_helper_v05.py` with thin wrapper or remove — `[IMPLEMENTED]` (removed; package is entry point)
3. Update Blender install instructions in README — `[IMPLEMENTED]`

**Gate:** Manual test checklist passes (copy scene, apply commands, run generator, browser CRUD).

## Phase D — Semantic object model `[COMPLETE]`

1. Implement `layoutlab_object_id` + `layoutlab_params` on generated meshes — `[IMPLEMENTED]` v0.5.1
2. Extend scene export with semantic `layoutlab` block — `[IMPLEMENTED]`
3. Add `regenerate` command to JSON protocol — `[IMPLEMENTED]`

**Gate:** AI can read a bed from export and recreate it with different params — `[PASSED]` via `regenerate` + export block.

## Phase E — Clearance & constraints `[IN PROGRESS]`

Split into two design decisions (do not merge):

| Sub-phase | DD | Focus | Status |
|---|---|---|---|
| E.1 | [DD-007](design_decisions/DD-007-clearance-zones.md) | Clearance zones — descriptive usage volumes | **Accepted** |
| E.2 | [DD-008](design_decisions/DD-008-constraints-and-layout-analysis.md) | Constraints + `analyze_layout` | **Proposed** |

Implementation order after DD-007 acceptance: API → wardrobe refactor → export → diagnostics → DD-008 → analyze_layout → bed clearances.

See Master Design Document §17 for the full product roadmap.

------------------------------------------------------------------------

# 10. External Dependencies

| Dependency | Role | Status |
|---|---|---|
| **Blender ≥ 4.0** | Editor, runtime, Python host | `[IMPLEMENTED]` |
| **bpy / mathutils** | Blender Python API | `[IMPLEMENTED]` |
| **ChatGPT / AI agents** | Semantic planning via JSON | `[IMPLEMENTED]` |
| **GitHub** | Source control | `[IMPLEMENTED]` |

No external Python packages. `[IMPLEMENTED]` — intentional; keep it that way unless a DD says otherwise.

------------------------------------------------------------------------

# 11. Non-Goals (v0.x)

Not part of current architecture work:

- Photorealistic furniture or materials
- Rendering pipeline
- Physics simulation
- Web frontend (engine should stay portable `[PLANNED]`)
- Real-time collaboration

------------------------------------------------------------------------

# 12. Architecture Decision Index

Referenced in Master Design Document; formal DD files `[PLANNED]`:

| ID | Decision | Status |
|---|---|---|
| DD-001 | Generators are parametric assets | `[ACCEPTED]` — [DD-001](design_decisions/DD-001-generators-are-parametric-assets.md) |
| DD-002 | Generators rebuild mesh (no blind scale) | `[ACCEPTED]` — [DD-002](design_decisions/DD-002-generators-rebuild-mesh.md) |
| DD-003 | Communication exclusively via JSON | `[ACCEPTED]` — [DD-003](design_decisions/DD-003-json-only-communication.md) |
| DD-004 | UI oriented on Asset Browser | `[ACCEPTED]` — [DD-004](design_decisions/DD-004-asset-browser-ui.md) |
| DD-005 | Generators carry metadata constants | `[ACCEPTED]` — [DD-005](design_decisions/DD-005-generator-metadata.md) |
| DD-006–009 | Parts, clearances, constraints, AI boundary | See [design_decisions/README.md](design_decisions/README.md) |

New decisions require a file in `docs/design_decisions/` before implementation.

------------------------------------------------------------------------

# 13. Glossary (quick reference)

| Term | Meaning |
|---|---|
| **Generator** | Rule system: params → geometry for one object type |
| **Component** | Reusable sub-part (leg, shelf, mattress) |
| **API** | Functions generators may call (`create_box`, …) |
| **Protocol** | JSON command/export format (`docs/json_protocol.md`) |
| **Role** | `layoutlab_role` custom property on a mesh |
| **Clearance** | Invisible required free space around an object |

Full vocabulary: `AI_CONTEXT.md`

------------------------------------------------------------------------

# 14. Changelog

| Version | Date | Changes |
|---|---|---|
| 0.5.0 | 2026-07-09 | Initial architecture document (as-built + target + migration) |
| 0.5.1 | 2026-07-09 | Phase A.4–A.5 complete: design decisions + units documented |
