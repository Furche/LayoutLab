# LayoutLab — Session Handoff

> Living onboarding doc for new chat sessions / agents.
> **Owns:** technical as-built status, versions, gotchas, session notes.
> **Does not own:** product priorities or work order — that is [`ROADMAP.md`](ROADMAP.md).

**Last updated:** 2026-07-23 (Chat thinking indicator `0.10.59`)
**Plugin / Core version:** 0.10.59 · **Branch:** `main`

**Active product work:** [ROADMAP.md §2 Active](ROADMAP.md#2-active) —
**Room Z-rotate**

------------------------------------------------------------------------

# Quick start for a new agent

Binding reading order:

1. [00_READ_THIS_FIRST.md](../00_READ_THIS_FIRST.md)
2. [AI_CONTEXT.md](../AI_CONTEXT.md)
3. [ROADMAP.md](ROADMAP.md) — priorities and work order
4. Feature Concept linked by the **Active** ROADMAP entry
5. Related **Accepted** Design Decisions
6. **This file** — technical as-built and session notes

Respond to Alexander in **German**.

**Repo path:** `/Users/allex/Documents/00_codin/BlenderAddons/LayoutLab`
**Remote:** `https://github.com/Furche/LayoutLab.git`

**Copy-paste prompt for new chat:**

```
LayoutLab — semantic interior planning (Standalone Viewer + Core).
Repo: /Users/allex/Documents/00_codin/BlenderAddons/LayoutLab
Branch: main. Core/plugin v0.10.59.

Lies in dieser Reihenfolge:
1. 00_READ_THIS_FIRST.md
2. AI_CONTEXT.md
3. docs/ROADMAP.md  ← verbindliche Prioritäten
4. Feature Concept des Active-Eintrags
5. zugehörige Accepted DDs
6. docs/HANDOFF.md  ← Ist-Zustand / Gotchas

Aktueller Stand (2026-07-23):
- Produktfokus: Standalone Web Viewer (`viewer/`) + Core HTTP (`server/`)
- FC-001/WP-01…WP-06 ✅; Viewer direct manipulation ✅; planning feedback ✅ (`0.10.58`)
- Active: Room Z-rotate (siehe ROADMAP §2)
- Blender = Runtime-Adapter, kein Default für neue Features
- Core: python3 -m server (:8765); Viewer: cd viewer && npm run dev (:5173)

Bitte auf Deutsch antworten. Keine vollen Diagnostic-Reports inline.
[Nächste Aufgabe hier einfügen]
```

------------------------------------------------------------------------

# What is LayoutLab?

Parametric **semantic interior planning** — long-term: translate human room requirements into spatial solutions (not primarily a furniture placer).

```
User Intent → Viewer UX → Core (rules/commands) → Spatial Project → scene export
```

(Long-term: Intent → Planning → Execution — see [Future_Ideas.md](Future_Ideas.md) §9.)

- **Primary product surface:** standalone web Viewer (`viewer/`) + Core HTTP ([DD-014](design_decisions/DD-014-standalone-runtime-path.md)).
- Blender is a **runtime adapter** (first host / generator QA), **not** where new UX lands by default.
- **AI** communicates via JSON (DD-003); execution boundary [DD-009](design_decisions/DD-009-ai-execution-boundary.md) (**Accepted** — AI plans WHAT, Core executes HOW).

**Viewer:** `cd viewer && npm run dev` (default `:5173`) with Core `python3 -m server` (`:8765`).
**Blender install (optional):** `dist/layoutlab-<version>.zip` → Preferences → Add-ons.
**Generators sync** on Blender register: bundled → `layoutlab_generators/` when bundled version is newer.

**Units:** scene units natively (Metric default: 1 unit = 1 m). See `docs/units_and_coordinates.md`.
**Reference room position (examples):** `[68.3, 197.7, 0]`. Quick Test / Core fixtures often `(0, 0, 0)`.

------------------------------------------------------------------------

# How we work (Alexander + agents)

| Topic | Rule |
|---|---|
| Language | **German** for user communication |
| Architecture | Idea → **Feature Concept** → **DD(s)** → work packages → code. Don't skip DD for binding choices. |
| Priorities | [`ROADMAP.md`](ROADMAP.md) only — do not invent a parallel queue in this file |
| Separation | Clearance (DD-007) ≠ Constraints (DD-008) ≠ AI boundary (DD-009) ≠ Runtime (Blender = first adapter) |
| Commits | Commit/push when user asks or at clear milestone — **not** every tiny edit unasked |
| Cursor role | Implements; does **not** silently change architecture |
| Code style | Minimal diffs, match conventions, no over-engineering |
| Tests | `python3 -m unittest discover -s tests` (no bpy for util tests) |
| Blender QA | Diagnostics in addon — target **18/18 PASS** |
| Agent context | `.cursor/rules/` — Git/PR/LayoutLab-Konventionen; keine vollen Diagnostic-Dumps in Chat |

------------------------------------------------------------------------

# Current versions

| Component | Version |
|---|---|
| Plugin / Core (`layoutlab/__init__.py` `bl_info`) | **0.10.59** |
| `bed_basic` | **0.7.0** — raised frame; optional `bed_entry` clearances; sizes in meters |
| `wardrobe_basic` | **0.7.0** — `front_side`, `create_clearance`, part `clearance_front_access` |
| `desk_basic` | **0.2.0** — tabletop + legs, optional `chair_access` clearance |
| Room Model | **DD-010** — rectangle MVP; see `docs/room_model.md` |
| Latest zip | `dist/layoutlab-0.10.59.zip` (rebuilt on commit when `layoutlab/` changes) |

------------------------------------------------------------------------

# What works today (as-built snapshot)

- Parts model (DD-006); generators `bed_basic`, `wardrobe_basic`, `desk_basic`
- JSON: `run_generator`, `regenerate`, scene export, `create_clearance`, `analyze_layout`
- Planning slice: recipes, candidates, shortlist, Apply-Gate, optional AI aesthetics
- FC-001 Core WP-01…WP-06 (`0.10.36`–`0.10.40`): transactions, furniture ops, resize, wall/corner, Spatial Project
- Viewer multi-room + direct manipulation → Core preview/commit (`0.10.41`–`0.10.57`)
- Viewer planning feedback: proposed vs committed (`0.10.58`)
- Default boot: furnished bedroom via Core; clearances as oriented mesh wireframes
- Bundled generator sync; diagnostic checks; reference kids room fixtures under `tests/fixtures/`

Full ordered foundations list: [ROADMAP.md §1](ROADMAP.md#1-implemented-foundations).

------------------------------------------------------------------------

# Design decisions — status

| DD | Title | Status |
|---|---|---|
| DD-001–006 | Generators, JSON, Parts, … | Accepted |
| [DD-007](design_decisions/DD-007-clearance-zones.md) | Clearance zones | **Accepted** |
| [DD-008](design_decisions/DD-008-constraints-and-layout-analysis.md) | Constraints + `analyze_layout` | **Accepted** |
| [DD-009](design_decisions/DD-009-ai-execution-boundary.md) | AI execution boundary | **Accepted** |
| [DD-010](design_decisions/DD-010-room-model.md) | Room Model (single space) | **Accepted** — MVP shipped |
| [DD-014](design_decisions/DD-014-standalone-runtime-path.md) | Standalone runtime path | **Accepted** |
| [DD-011](design_decisions/DD-011-layout-variants-and-comparison.md) | Variants / Planning v1 | **Accepted** |
| [DD-015](design_decisions/DD-015-soft-metrics-and-tradeoffs.md) | Soft metrics + tradeoffs | **Accepted** |
| [DD-016](design_decisions/DD-016-deterministic-layout-recipes.md) | Layout recipes | **Accepted** |
| [DD-017](design_decisions/DD-017-collaborative-planning-and-contextual-evaluation.md) | Collaborative planning | **Accepted** |
| [DD-018](design_decisions/DD-018-semantic-transactions-and-authority.md) | Semantic transactions | **Accepted** |
| [DD-019](design_decisions/DD-019-semantic-direct-manipulation.md) | Semantic direct manipulation | **Accepted** |
| [DD-020](design_decisions/DD-020-spatial-project-independent-rooms.md) | Spatial Project / independent rooms | **Accepted** |

Index: [design_decisions/README.md](design_decisions/README.md).

------------------------------------------------------------------------

# Repository layout (essential paths)

```
layoutlab/               # Core + Blender addon package
viewer/                  # Standalone web Viewer (Vite + Three.js)
server/                  # Core HTTP
tests/fixtures/
docs/
├── ROADMAP.md           # binding product priorities
├── HANDOFF.md           # this file — session / as-built
├── concepts/            # Feature Concepts (FC-xxx)
├── design_decisions/    # DD-xxx
├── ARCHITECTURE.md
├── json_protocol.md
└── documentation_map.md
CHANGELOG.md · DEVLOG.md · AI_CONTEXT.md
dist/layoutlab-*.zip
```

------------------------------------------------------------------------

# Documentation maintenance

See [documentation_map.md](documentation_map.md).

| Change | Update |
|---|---|
| Priority / Active work / queue | [`ROADMAP.md`](ROADMAP.md) |
| Version, DD status, gotchas, as-built | **This file** + link Active ROADMAP row |
| User-visible feature list | `README.md` summary only |

**Update this HANDOFF.md** when: version bump, DD accepted, or as-built/session notes change.
If **next work** changes, update [`ROADMAP.md`](ROADMAP.md) first, then point here.

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
8. Viewer second overlay pass: keep `autoClear=false` or the scene is wiped.
9. Bed scale axes: X→`length`, Y→`width` for `bed_basic` (`0.10.57`).

------------------------------------------------------------------------

# Document history

| Date | Change |
|---|---|
| 2026-07-23 | `0.10.59` Chat thinking indicator; `0.10.58` planning feedback polish; Active → Room Z-rotate |
| 2026-07-23 | Roadmap ownership moved to `docs/ROADMAP.md`; HANDOFF = session/as-built only |
| 2026-07-23 | `0.10.57` Bed scale axes; Viewer gizmo/overlay polish through `0.10.56` |
| 2026-07-22 | `0.10.46` Selection transform gizmos; product focus Viewer-first |
| 2026-07-22 | FC-001/WP-01…WP-06 shipped (`0.10.36`–`0.10.40`) |
| 2026-07-21 | Planning slice / DD-017 staging through shortlist (`0.10.24`–`0.10.35`) |
| 2026-07-16 | DD-010 Room Model; Future Vision docs |
| 2026-07-12 | DD-009 Accepted; handoff prompt |
| 2026-07-11 | Initial handoff doc created |
