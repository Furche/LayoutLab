# LayoutLab — Session Handoff

> Living onboarding doc for new chat sessions / agents.  
> **Update this file** when major milestones, DD status, or next steps change significantly.

**Last updated:** 2026-07-22 (shortlist blueprint SVG)  
**Plugin version:** 0.10.33 · **Branch:** `main`

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
LayoutLab — Blender-Addon für semantische Raumplanung (Execution + Planning v0).
Repo: /Users/allex/Documents/00_codin/BlenderAddons/LayoutLab
Branch: main. Plugin v0.10.33.

Lies zuerst AI_CONTEXT.md (Mental Model). Für Architektur: docs/ARCHITECTURE.md.
Aktueller Stand (2026-07-22):
- DD-016 **Accepted**: plan_layout + bedroom_basic (agent_tools 0.5)
- DD-015 **Accepted**: soft metrics + tradeoffs (Ästhetik ≠ Core-Metrik)
- DD-011 **Accepted** + **candidates v1 shipped**: `plan_layout` mode=candidates
- DD-017 **Accepted** + evaluation schema + shortlist + revision + force path
- **Shortlist selection** ✅ (`0.10.29`) · **blueprint SVG cards** ✅ (`0.10.33`, Tür/Fenster/Möbel)
- Nächste Arbeit: optional AI aesthetics (flag); more recipes on demand
- DD-010/014 Accepted: Room Model + Standalone Core HTTP + Viewer
- Core: python3 -m server (:8765); Viewer Vite (:5173)

Bitte auf Deutsch antworten. Keine vollen Diagnostic-Reports inline — nur fehlgeschlagene Checks oder Dateireferenz.
Lies docs/HANDOFF.md für Details.

[Nächste Aufgabe hier einfügen]
```

------------------------------------------------------------------------

# What is LayoutLab?

Parametric **semantic interior planning** for Blender — long-term: translate human room requirements into spatial solutions (not primarily a furniture placer).

```
User Intent → Generator (rules) → Parts API → Blender scene
```

(Long-term: Intent → Planning → Execution — see [Future_Ideas.md](Future_Ideas.md) §9.)

- Blender 4.0+ is the **editor**, not the product.
- **AI** communicates via JSON (DD-003); execution boundary [DD-009](design_decisions/DD-009-ai-execution-boundary.md) (**Accepted** — AI plans WHAT, plugin executes HOW).
- Today: **JSON** clipboard/text block ([DD-003](design_decisions/DD-003-json-only-communication.md)).

**Install:** `dist/layoutlab-<version>.zip` → Blender Preferences → Add-ons.  
**Generators sync** on register: bundled → `layoutlab_generators/` when bundled version is newer.

**Units:** Blender scene units natively (Metric default: 1 unit = 1 m). See `docs/units_and_coordinates.md`.  
**Reference room position (examples):** `[68.3, 197.7, 0]`. Quick Test default: `(0, 0, 0)`.

------------------------------------------------------------------------

# How we work (Alexander + agents)

| Topic | Rule |
|---|---|
| Language | **German** for user communication |
| Architecture | Idea → **DD** → docs → code. Don't skip DD for big decisions. |
| Separation | Clearance (DD-007) ≠ Constraints (DD-008) ≠ AI boundary (DD-009) ≠ Runtime (Blender = first adapter, §Future_Ideas §11) |
| Commits | Commit/push when user asks or at clear milestone — **not** every tiny edit unasked |
| Cursor role | Implements; does **not** silently change architecture |
| Code style | Minimal diffs, match conventions, no over-engineering |
| Tests | `python3 -m unittest discover -s tests` (no bpy for util tests) |
| Blender QA | Diagnostics in addon — target **18/18 PASS** |
| Agent context | `.cursor/rules/` — Git/PR/LayoutLab-Konventionen; keine vollen Diagnostic-Dumps in Chat |

Alexander gives precise architecture feedback (e.g. don't merge clearance + constraints in one DD).

------------------------------------------------------------------------

# Current versions

| Component | Version |
|---|---|
| Plugin (`layoutlab/__init__.py` `bl_info`) | **0.10.3** |
| `bed_basic` | **0.7.0** — raised frame construction (`BedConstruction`) + optional `bed_entry` clearances; sizes in meters |
| `wardrobe_basic` | **0.7.0** — `front_side` (`y_min` \| `y_max`), `create_clearance`, part `clearance_front_access`; sizes in meters |
| `desk_basic` | **0.2.0** — tabletop + legs, optional `chair_access` clearance (`required`); sizes in meters |
| Room Model | **DD-010** — rectangle MVP; see `docs/room_model.md` |
| Latest zip | `dist/layoutlab-0.10.3.zip` (rebuilt on commit when `layoutlab/` changes) |

------------------------------------------------------------------------

# What works today

- **Parts model** (DD-006): main `body`, static/dynamic children, join at `finish()`
- **Parenting:** child offsets from `obj.location` (not stale `matrix_world` in `exec()`)
- Generators: `bed_basic`, `wardrobe_basic`, `desk_basic`; generator browser + Quick Test
- JSON: `run_generator`, `regenerate`, scene export, `create_clearance`
- **`api["create_clearance"]`** (DD-007): metadata + Main-Part-local placement
- **`analyze_layout`** JSON command (DD-008): findings from clearance overlap
- Export: `layoutlab.clearance` with `local_bounds` + `world_bounds`
- Bundled generator sync; 22 diagnostic checks
- Reference kids room fixture: `tests/fixtures/reference_kids_room_commands.json`

------------------------------------------------------------------------

# Design decisions — status

| DD | Title | Status |
|---|---|---|
| DD-001–006 | Generators, JSON, Parts, … | Accepted |
| [DD-007](design_decisions/DD-007-clearance-zones.md) | Clearance zones | **Accepted** — impl. steps 1–6 done |
| [DD-008](design_decisions/DD-008-constraints-and-layout-analysis.md) | Constraints + `analyze_layout` | **Accepted** — v1 shipped |
| [DD-009](design_decisions/DD-009-ai-execution-boundary.md) | AI execution boundary | **Accepted** |
| [DD-010](design_decisions/DD-010-room-model.md) | Room Model (single space) | **Accepted** — MVP shipped v0.9.0 |
| [DD-014](design_decisions/DD-014-standalone-runtime-path.md) | Standalone runtime path | **Accepted — Phase A + B + B2** |
| [DD-011](design_decisions/DD-011-layout-variants-and-comparison.md) | Variants / Planning v1 (recipe = strategy) | **Accepted** |
| [DD-015](design_decisions/DD-015-soft-metrics-and-tradeoffs.md) | Soft metrics + tradeoffs | **Accepted** |
| [DD-016](design_decisions/DD-016-deterministic-layout-recipes.md) | Layout recipes (Planning v0) | **Accepted** — `plan_layout` + `bedroom_basic` |
| [DD-017](design_decisions/DD-017-collaborative-planning-and-contextual-evaluation.md) | Collaborative planning + contextual candidate evaluation | **Accepted** — DD-011/DD-015 amended; implementation staged |

### DD-007 (key points)

- `clearance_id` global; `clearance_name` unique per `object_id`
- `requirement`: `required` \| `preferred`
- Export: local bounds (Main Part space) + world bounds (at export time)

### DD-008 (implemented v0.8.0)

- `analyze_layout` JSON command — `zone_must_be_clear`, AABB overlap
- `required` → error, `preferred` → warning
- Diagnostics: clear layout + wardrobe/bed blocked scenario

### DD-009 (Accepted — documentation only, no bridge/expert code)

- AI plans WHAT; plugin executes HOW (deterministic API)
- Bridge + Expert Mode = **Future Idea** — separate DD(s) before implementation
- Deferred defaults documented in DD-009 §Deferred decisions

------------------------------------------------------------------------

# Recent history (newest first)

| Date | Milestone |
|---|---|
| 2026-07-12 | bed_basic v0.6.0 — `bed_entry` clearances + diagnostics |
| 2026-07-12 | Runtime independence documented (Core vs Blender) |
| 2026-07-12 | DD-008/009 Accepted; analyze_layout shipped (v0.8.0) |
| 2026-07-11 | DD-009 proposed — AI vs plugin boundary |
| 2026-07-11 | DD-008 proposed — constraints / analyze_layout |
| 2026-07-10 | v0.7.1 — clearance export + diagnostic |
| 2026-07-10 | v0.7.0 — `create_clearance()` API, wardrobe refactor |
| 2026-07-10 | bed_basic v0.5.0 — construction stack |
| 2026-07-10 | Parenting fixes v0.6.5–0.6.8 |
| 2026-07-10 | DD-007 Accepted |

**Latest commit (at last handoff update):** `f636809` — runtime independence docs

------------------------------------------------------------------------

# Next steps (agreed order)

1. ~~Entschlacken von `agent.py` (Bedroom-Heuristiken → planning/)~~ ✅ (v0.10.21)  
2. ~~**Accept DD-016 / DD-015**~~ ✅ (2026-07-20)  
3. ~~**Accept DD-011**~~ ✅ (2026-07-20)  
4. ~~**Accept DD-017 + amend DD-011/DD-015**~~ ✅ (2026-07-21)
5. ~~DD-011 candidate expansion + soft ranking~~ ✅ (`0.10.24` — `mode: "candidates"`)
6. ~~Define the minimal DD-017 schema contract: profiles/capabilities, roles/intentions, signed categories and veto thresholds~~ ✅ (`0.10.25`)
7. ~~Core functional shortlisting + bounded internal revision~~ ✅ (`0.10.25` shortlist; `0.10.26` revision ≤2 rounds)
8. ~~Core recipe force path (generic registry)~~ ✅ (`0.10.27` — bedroom first mapping)
9. ~~Planning selection surfacing (reply + session log)~~ ✅ (`0.10.28`)
10. ~~Shortlist selection (chat + Viewer)~~ ✅ (`0.10.29`)
11. ~~Shortlist sketch cards (labels + ASCII)~~ ✅ (`0.10.30`)
12. ~~Shortlist 3D thumbnails~~ ✅ (`0.10.31`) → replaced by blueprint SVG
13. ~~Shortlist blueprint SVG~~ ✅ (`0.10.33`)
14. More recipes when needed (room-use or goal) — not Capture/Cloud/Auth

DD-011/015/016/017 **Accepted** · blueprint shortlist cards shipped · next: optional aesthetics / more recipes

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
└── diagnostics.py       # 22 checks

viewer/                  # Phase A read-only web viewer (Vite + Three.js)
├── README.md
├── package.json
└── src/

tests/
├── fixtures/
│   ├── reference_kids_room_commands.json
│   ├── reference_kids_room_export.json
│   └── reference_kids_room_export_findings.json

docs/
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

Living product track — keep in sync with *Next steps* above.

1. ✅ Generator docs, API, modular plugin, browser, regenerate  
2. ✅ Clearance (DD-007) · Constraints / analyze (DD-008) · Room Model (DD-010)  
3. ✅ Standalone Core + Viewer (DD-014) · Soft metrics (DD-015) · Recipes (DD-016)  
4. ✅ Planning foundation: recipes as strategies (DD-011) · collaborative evaluation (DD-017)  
5. ✅ DD-011 candidate expansion + soft ranking (`0.10.24`)  
6. ✅ Minimal DD-017 evaluation schema (profiles/roles/vetos) (`0.10.25`)  
7. ✅ Core functional shortlist + bounded revision (`0.10.26`)  
8. ✅ Core recipe force path / `recipe_routing` (`0.10.27`)  
9. ✅ Planning selection surfacing (`0.10.28`)  
10. ✅ Shortlist selection chat + Viewer (`0.10.29`)  
11. ✅ Shortlist sketch cards (`0.10.30`)  
12. ✅ Shortlist 3D thumbnails (`0.10.31`)  
13. 📋 Optional experimental AI aesthetics (behind flag) · more recipes on demand  
14. 📋 Bridge / capture / multi-space / persisted variants — Future Ideas, separate DDs  

Binding order for agents: **Next steps** (this file) · detail in [DD-017](design_decisions/DD-017-collaborative-planning-and-contextual-evaluation.md) implementation order.

------------------------------------------------------------------------

# Document history

| Date | Change |
|---|---|
| 2026-07-21 | Shortlist 3D thumbnails (`0.10.31`): slim viewer_preview + WebGL cards |
| 2026-07-21 | Shortlist sketch cards (`0.10.30`): label_de + ASCII cards in Viewer |
| 2026-07-21 | Shortlist selection (`0.10.29`): chat + Viewer pick before Apply |
| 2026-07-21 | Planning selection surfacing (`0.10.28`): reply + LAST_SESSION Planning block |
| 2026-07-21 | Core recipe force path (`0.10.27`): recipe_routing + ensure plan_layout |
| 2026-07-21 | DD-017 bounded internal revision (`0.10.26`): ≤2 allowlisted rounds |
| 2026-07-21 | DD-017 evaluation schema v0.1 + functional shortlist (`0.10.25`) |
| 2026-07-21 | DD-011 candidates v1 shipped (`0.10.24`): expand + soft rank |
| 2026-07-21 | Roadmap sync: User priority + Next steps reflect DD-017 Accepted staging |
| 2026-07-21 | DD-017 **Accepted**; DD-011/DD-015 amended; Planner evaluation staged |
| 2026-07-20 | DD-011 **Accepted** — Planner foundation; next = implement candidates |
| 2026-07-20 | DD-011 **Proposed** — recipe as solution space; candidates + rank |
| 2026-07-20 | DD-015 + DD-016 **Accepted**; next focus recipes on demand |
| 2026-07-16 | DD-010 Room Model Proposed; next focus Room Model after Accept |
| 2026-07-16 | Future Vision standalone/spatial/capture (docs only); focus stays Execution Layer |
| 2026-07-12 | Handoff prompt + recent milestones; `.cursor/rules/` note |
| 2026-07-12 | DD-009 Accepted — AI/plugin execution boundary |
| 2026-07-11 | DD-009 doc sync — review gate, cross-doc Proposed markers |
| 2026-07-11 | Initial handoff doc created |
