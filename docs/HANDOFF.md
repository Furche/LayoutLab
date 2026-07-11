# LayoutLab — Session Handoff

> Living onboarding doc for new chat sessions / agents.  
> **Update this file** when major milestones, DD status, or next steps change significantly.

**Last updated:** 2026-07-11 (DD-009 doc sync — review package)  
**Plugin version:** 0.7.1 · **Branch:** `main` (sync with `origin/main`)

------------------------------------------------------------------------

# Quick start for a new agent

1. Read [00_READ_THIS_FIRST.md](../00_READ_THIS_FIRST.md) (team roles, doc checklist).
2. Read [AI_CONTEXT.md](../AI_CONTEXT.md) (mental model).
3. Check [design_decisions/README.md](design_decisions/README.md) (DD index — **before** coding).
4. Read this file for **current** status and next steps.
5. Respond to Alexander in **German**.

**Repo path:** `/Users/allex/Documents/00_codin/BlenderAddons/LayoutLab`  
**Remote:** `https://github.com/Furche/LayoutLab.git`

**Copy-paste prompt for new chat:**

```
Projekt: LayoutLab, Blender-Addon.
Repo: /Users/allex/Documents/00_codin/BlenderAddons/LayoutLab
Plugin v0.7.1, bed_basic/wardrobe_basic v0.5.0, main synced mit origin.
DD-007 Accepted (Clearance done). DD-008/009 Proposed.
Nächstes: DD-008 review → analyze_layout → bed clearances.
Deutsch, DD-first, minimal diffs. Lies docs/HANDOFF.md + 00_READ_THIS_FIRST.md.
```

------------------------------------------------------------------------

# What is LayoutLab?

Parametric **semantic interior planning** for Blender — not mesh placement.

```
User Intent → Generator (rules) → Parts API → Blender scene
```

- Blender 4.0+ is the **editor**, not the product.
- **AI** communicates via JSON (DD-003); execution boundary in [DD-009](design_decisions/DD-009-ai-execution-boundary.md) (**Proposed** — AI plans WHAT, plugin executes HOW).
- Today: **JSON** clipboard/text block ([DD-003](design_decisions/DD-003-json-only-communication.md)).

**Install:** `dist/layoutlab-<version>.zip` → Blender Preferences → Add-ons.  
**Generators sync** on register: bundled → `layoutlab_generators/` when bundled version is newer.

**Units:** 1 Blender unit ≈ 10 cm in Alexander's reference room.  
**Reference room position (examples):** `[68.3, 197.7, 0]`. Quick Test default: `(0, 0, 0)`.

------------------------------------------------------------------------

# How we work (Alexander + agents)

| Topic | Rule |
|---|---|
| Language | **German** for user communication |
| Architecture | Idea → **DD** → docs → code. Don't skip DD for big decisions. |
| Separation | Clearance (DD-007) ≠ Constraints (DD-008) ≠ AI boundary (DD-009) |
| Commits | Commit/push when user asks or at clear milestone — **not** every tiny edit unasked |
| Cursor role | Implements; does **not** silently change architecture |
| Code style | Minimal diffs, match conventions, no over-engineering |
| Tests | `python3 -m unittest discover -s tests` (no bpy for util tests) |
| Blender QA | Diagnostics in addon — target **14/14 PASS** |

Alexander gives precise architecture feedback (e.g. don't merge clearance + constraints in one DD).

------------------------------------------------------------------------

# Current versions

| Component | Version |
|---|---|
| Plugin (`layoutlab/__init__.py` `bl_info`) | **0.7.1** |
| `bed_basic` | **0.5.0** — raised frame construction (`BedConstruction`) |
| `wardrobe_basic` | **0.5.0** — `create_clearance`, part `clearance_front_access` |
| Latest zip | `dist/layoutlab-0.7.1.zip` (rebuilt on commit when `layoutlab/` changes) |

------------------------------------------------------------------------

# What works today

- **Parts model** (DD-006): main `body`, static/dynamic children, join at `finish()`
- **Parenting:** child offsets from `obj.location` (not stale `matrix_world` in `exec()`)
- Generators: `bed_basic`, `wardrobe_basic`; generator browser + Quick Test
- JSON: `run_generator`, `regenerate`, scene export, `create_clearance`
- **`api["create_clearance"]`** (DD-007): metadata + Main-Part-local placement
- Export: `layoutlab.clearance` with `local_bounds` + `world_bounds`
- Bundled generator sync; 14 diagnostic checks

------------------------------------------------------------------------

# Design decisions — status

| DD | Title | Status |
|---|---|---|
| DD-001–006 | Generators, JSON, Parts, … | Accepted |
| [DD-007](design_decisions/DD-007-clearance-zones.md) | Clearance zones | **Accepted** — impl. steps 1–6 done |
| [DD-008](design_decisions/DD-008-constraints-and-layout-analysis.md) | Constraints + `analyze_layout` | **Proposed** |
| [DD-009](design_decisions/DD-009-ai-execution-boundary.md) | AI execution boundary | **Proposed** |

### DD-007 (key points)

- `clearance_id` global; `clearance_name` unique per `object_id`
- `requirement`: `required` \| `preferred`
- Export: local bounds (Main Part space) + world bounds (at export time)

### DD-008 (next implementation — after Accepted)

- Analyzer reads clearances; emits `findings` (not stored in export)
- v1: `zone_must_be_clear` (AABB overlap)
- JSON `analyze_layout` — **not implemented yet**

### DD-009 (documentation only — **Proposed, awaiting Alexander review**)

- Plugin stays API-first; direct AI→bpy = future Expert Mode only
- Local bridge = **Future Idea** — **do not implement** without new DD + DD-009 Accepted
- Review gate: see DD-009 §Review gate — no status change to Accepted until PO approves

------------------------------------------------------------------------

# Recent history (newest first)

| Date | Milestone |
|---|---|
| 2026-07-11 | DD-009 proposed — AI vs plugin boundary |
| 2026-07-11 | DD-008 proposed — constraints / analyze_layout |
| 2026-07-10 | v0.7.1 — clearance export + diagnostic |
| 2026-07-10 | v0.7.0 — `create_clearance()` API, wardrobe refactor |
| 2026-07-10 | bed_basic v0.5.0 — construction stack |
| 2026-07-10 | Parenting fixes v0.6.5–0.6.8 |
| 2026-07-10 | DD-007 Accepted |

**Latest commit (at last handoff update):** `2c1eb7a` — DD-009

------------------------------------------------------------------------

# Next steps (agreed order)

1. **Review DD-008** → Accepted  
2. **Review DD-009** → Accepted  
3. Implement `layout_analysis.py` + `analyze_layout` (DD-008)  
4. Diagnostics: blocked vs clear layout (wardrobe reference)  
5. **`bed_basic` multi-zone clearances** — only after analyzer works  
6. **Not now:** bridge, expert bpy mode, generator #3, network agent  

------------------------------------------------------------------------

# Repository layout (essential paths)

```
layoutlab/
├── __init__.py          # bl_info version
├── api/                 # parts, clearance, transforms, geometry
├── engine/              # executor, registry (sync)
├── protocol/            # commands, export, semantic, clearance_export
├── generators/          # bed_basic, wardrobe_basic (+ .md each)
├── plugin/              # panel, browser, quick_test
└── diagnostics.py       # 14 checks

docs/
├── design_decisions/    # DD-001 … DD-009
├── HANDOFF.md           # this file
├── json_protocol.md
├── generator_api.md
├── ARCHITECTURE.md
└── documentation_map.md # what to update when

CHANGELOG.md             # what changed
DEVLOG.md                # why changed
AI_CONTEXT.md            # vocabulary
dist/layoutlab-*.zip
```

------------------------------------------------------------------------

# Documentation maintenance

See [documentation_map.md](documentation_map.md). Minimum on most changes:

| Always | Often |
|---|---|
| `CHANGELOG.md` | `json_protocol.md` (JSON/export) |
| | `generator_api.md` (API) |
| | `generators/<name>.md` (generator behaviour) |
| | `DEVLOG.md` (non-obvious why) |
| | `README.md` (user-visible) |
| | New/updated **DD** for architecture |

**Update this HANDOFF.md** when: version bump, DD accepted, or next-steps shift.

------------------------------------------------------------------------

# Git

- **Never** change git config, force-push main, or skip hooks unless user asks.
- Commit messages: English, concise, why-focused.
- Pre-commit hook rebuilds addon zip when `layoutlab/` changes.
- User often expects **push to origin** after completed work.

------------------------------------------------------------------------

# Technical pitfalls (learned in production debugging)

1. Inside generator `exec()`, `matrix_world` is often **stale** — use **`obj.location`** for parenting offsets.
2. Generators must **not** call `api["finish"]()` — engine does in `execute_generator()`.
3. Stale copies in `layoutlab_generators/` — bump `GENERATOR_VERSION` to force sync.
4. Wardrobe clearance: in front of carcass, **−Y**, part `clearance_front_access`, name `front_access`.
5. Bed pillows at `y_max`/`y_min`: divide along mattress **length (X)**, not width.
6. `headboard_height` (bed v0.5+): rise **above frame top**, not from floor.
7. `footboard_height` removed — footboard height = `frame_height`.

------------------------------------------------------------------------

# User roadmap priority (Alexander)

1. ✅ Generator docs, API, modular plugin, browser, regenerate  
2. ✅ Clearance (DD-007 implemented)  
3. 🔄 Constraints + analyze_layout (DD-008)  
4. ⏳ New generators **after** clearance/constraint track  
5. 📋 Bridge / direct AI communication (Future — DD-009)

------------------------------------------------------------------------

# Document history

| Date | Change |
|---|---|
| 2026-07-11 | DD-009 doc sync — review gate, cross-doc Proposed markers |
| 2026-07-11 | Initial handoff doc created |
