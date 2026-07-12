# Future Ideas

> Living document. Ideas only — not commitments.  
> **Last reorganized:** 2026-07-12 (product vision sharpened — no roadmap or implementation change)

## Purpose

This document captures promising concepts before they become architecture or code.

**Rule:**

```
Idea → Discussion → Design Decision → Architecture → Implementation
```

Never skip these steps.

## Why this exists

LayoutLab is evolving quickly. Cursor can implement ideas faster than we fully understand them — a strength, but also a risk. Some ideas look like features but are parts of a much larger architectural concept. Those ideas belong here first.

**Status markers used in this document:**

| Marker | Meaning |
|---|---|
| **Implemented** | Exists in plugin/code today (may reference a DD) |
| **Planned** | Agreed direction with a DD (Proposed or Accepted), not yet built |
| **Future Vision** | Long-term product direction — no DD, no implementation yet |
| **Experimental Idea** | Exploratory — may be rejected or merged later |

**Important:** Expanding this vision does **not** change the current development course. Generators, Parts, `object_id`, regeneration, clearances, constraints, analysis, and the JSON protocol remain the necessary foundation (Execution Layer). See §9 Long-term Architecture.

------------------------------------------------------------------------

# 1. Product Vision

**Status:** Future Vision (sharpened 2026-07-12)

LayoutLab is **not** primarily a furniture generator or furniture placer.

Its purpose is to **translate human requirements for a space into spatial solutions**.

The user should not have to think in technical operations or furniture types. They describe their problem in natural language.

**Examples of user intent (not furniture commands):**

- “The room should work for two children.”
- “Keep as much free play area as possible.”
- “An adult should be able to sit comfortably for bedtime.”
- “The existing wardrobe must stay.”
- “The radiator and window must remain accessible.”
- “The person uses a wheelchair and needs enough movement space.”
- “A blind person should be able to move safely.”
- “There must be no low protruding edges at head height.”

**Furniture is not the goal.** It is one possible *means* to satisfy requirements.

### Guiding principle

> LayoutLab does not optimize furniture.  
> LayoutLab optimizes spatial solutions for human needs.

Furniture, room layout, and custom constructions are different *means* to reach that goal.

### Relationship to today

Today the product still speaks largely in generators and JSON commands — that is correct for the current phase. This vision describes **where the product is heading**, not what to build next.

------------------------------------------------------------------------

# 2. Problem-first Planning

**Status:** Future Vision — not implemented

The user describes **goals and problems**, not necessarily furniture.

**Examples:**

- more play area
- two sleeping places
- more storage
- barrier-free movement
- safe navigation
- existing furniture must stay
- budget or material limits

LayoutLab derives spatial requirements from these statements.

### Problem-first workflow (long-term)

1. Understand user requirements
2. Capture room and existing furniture
3. Derive constraints and priorities
4. Develop possible solutions
5. Evaluate variants
6. Propose the best solution
7. **Only then** generate concrete furniture and layout operations

**Not:** “Create a loft bed.”  
**Instead:** “Provide a sleeping place, keep maximum play area, and do not block window or radiator.”

A loft bed is then only one possible solution among others.

### Solution Search Space

**Status:** Future Vision

LayoutLab should eventually compare different solution *types*:

| Approach | Example |
|---|---|
| Rearrange existing furniture | Move wardrobe to free wall |
| Regenerate / parametrically adjust | Narrower bed, same generator |
| Suggest suitable standard furniture | Catalog match (future) |
| Generate parametric furniture | `run_generator` today |
| Design individual furniture | Custom generator / synthesis |
| Integrated construction | Built-in loft, suspended structure |

The system should explain **why** a variant was chosen or rejected.

------------------------------------------------------------------------

# 3. Functional Room Design

**Status:** Future Vision — no binding data model yet

Rooms are described by **functions**, not only by object lists.

**Example functions:**

| Function | Notes |
|---|---|
| sleeping | Places, access, supervision |
| playing | Clear floor area |
| working | Desk, light, storage |
| storage | Reachable, age-appropriate |
| accessibility | Circulation, widths, heights |
| safety | Edges, head clearance, stability |
| daylight | Window access, obstruction |
| comfort | Ergonomics, climate |
| supervision | Sight lines (e.g. parent at bedside) |
| circulation | Paths, no dead ends |

Furniture is understood as objects that **provide capabilities**.

**Example — bed (functional view, not mesh view):**

- provides a sleeping place
- requires access (clearance)
- occupies floor area
- may optionally provide storage (loft, drawers)

This complements the current Parts/generator model; it does not replace it.

------------------------------------------------------------------------

# 4. Accessibility and Human Needs

**Status:** Future Vision — requires future Design Decisions

LayoutLab should eventually support **user profiles** and special requirements.

**Example profiles / needs:**

| Context | Examples of derived requirements |
|---|---|
| Wheelchair use | Turning circle, passage widths, reachability, no dead ends, operating heights |
| Blindness / visual impairment | Clear paths, no protruding corners, no low obstacles at head/shoulder height, reliable landmarks, predictable furniture along traceable structures |
| Children | Free play area, safe edges, reachable storage, age-appropriate heights, visibility and access |
| Older adults | Fall risk, reach, seating, lighting |
| Limited reach | Lower storage, reachable controls |

**Possible later derivations (not implemented):**

- minimum widths
- turning areas
- safe walkways
- reachable heights
- avoidance of hazardous edges
- clear room structure

These may become constraints, evaluation goals, or user-profile inputs — via future DDs.

------------------------------------------------------------------------

# 5. Planning and Evaluation

**Status:** Future Vision (partial foundations: DD-008 Planned)

### Variant generation and comparison

**Status:** Future Vision

Beyond placing one layout, LayoutLab could:

- generate multiple layout variants
- score and rank them
- explain trade-offs (“more play area, less storage”)

Depends on: stable `analyze_layout` (DD-008), richer evaluation rules, Intent/Planning layers (§9).

### Evaluation Engine

**Status:** Future Vision

Instead of only placing furniture, LayoutLab could evaluate layouts.

**Possible metrics:**

- play area
- storage
- accessibility
- daylight
- walking distances
- adult usability
- child usability

The engine should explain *why* one layout is better.

### Walkway Analysis

**Status:** Experimental Idea

Treat the room as a navigation graph.

**Possible questions:**

- Can every object be reached?
- Is the window accessible?
- Can the radiator be reached?
- Is the room blocked?

Deferred until constraint/clearance foundation (DD-007/008) is stable.

### Preview → Analyze → Revise → Commit

**Status:** Future Vision

Workflow for AI-driven layout iteration:

1. **Preview** — apply command batch in one undo group
2. **Analyze** — run constraint/clearance checks on preview state
3. **Revise** — AI adjusts plan from findings
4. **Commit** or **Discard** — user or policy confirms

**Depends on:** stable `analyze_layout` (DD-008 Planned), bridge MVP (§7), undo transaction support in plugin.

------------------------------------------------------------------------

# 6. Custom Furniture Synthesis

**Status:** Future Vision — explicitly out of scope for current phase

When no existing or purchasable solution fits, LayoutLab could eventually design **individual furniture or room constructions**.

**Possible stages:**

1. Standard furniture (catalog / generator)
2. Parametrically adjusted furniture (`regenerate`)
3. Fully individual furniture (new generator or synthesis)
4. Architecturally integrated solution (built-in, suspended, platform)

**Examples:**

- custom loft bed
- ceiling-suspended structure
- platform / podium
- built-in wardrobe
- multifunctional combination (desk + bed + storage)

### Out of scope (current phase and near-term)

- structural engineering / statics
- building code approval
- professional execution planning
- safety certification
- manufacturing data without further validation

LayoutLab is not becoming a CAD or structural analysis system in the current roadmap.

### Component Library

**Status:** Future Vision

Generators should eventually orchestrate reusable **components** rather than one-off geometry:

- Leg, Panel, Shelf, Mattress, Pillow, Handle, Rail, Ladder, …

Generators become rule systems rather than raw geometry builders. Today: Parts model (DD-006 **Implemented**) is the first step.

------------------------------------------------------------------------

# 7. AI / Plugin Communication

**Status:** Mix — JSON **Implemented** (DD-003); bridge **Future Vision**

### Intent, Planning, Execution (layer separation)

**Status:** Future Vision — architecture direction, not implemented

| Layer | Responsibility | Today |
|---|---|---|
| **Intent** | User goals, natural language, requirements | AI / user (outside plugin) |
| **Planning** | Generate variants, evaluate, discard, improve | Future — not in plugin v0.7 |
| **Execution** | Deterministic LayoutLab operations | Plugin + JSON protocol **Implemented** |

The current JSON API belongs to the **Execution Layer** only. A future AI bridge must **not** merge these layers — it forwards defined operations; it does not replace planning logic inside the addon without a DD.

See [DD-009](design_decisions/DD-009-ai-execution-boundary.md) (**Accepted**): AI plans WHAT; plugin executes HOW.

### AI–Plugin Direct Communication

**Status:** Future Vision (documented in DD-009 — not implemented)

Today the user copies JSON between chat and Blender.

Future: a **local LayoutLab Bridge** so the AI calls defined operations without clipboard.

**Requirements:**

- Same semantic operations as JSON protocol (not a second ad-hoc API)
- Localhost / user-approved connection
- No arbitrary remote Python as default

### Local Agent Bridge

**Status:** Future Vision

A small local process or in-addon listener that exposes:

- `get_scene`
- `list_generators` / `get_generator_schema`
- `preview_operations` / `commit_preview` / `discard_preview`
- `analyze_layout` (after DD-008)

The bridge forwards to the addon; it does not reimplement generator logic.

See DD-009 for architecture sketch and security open questions. **Do not implement** without separate bridge DD.

### Optional Direct Blender Expert Mode

**Status:** Experimental Idea (explicitly non-default)

AI may run controlled `bpy` for exploration or one-off debugging when user opts in.

**Rules (from DD-009 Accepted):**

- Not a replacement for LayoutLab API in production workflows
- Must be logged; prefer preview/undo wrapper
- Findings should feed back into generators or protocol, not stay as orphan scripts

Security and sandboxing need a separate DD before implementation.

------------------------------------------------------------------------

# 8. Geometry, Constraints and Analysis

**Status:** Current foundation — **Implemented** / **Planned** (not Future Vision)

This section documents ideas that are **actively being built** or **queued on the roadmap**. They support the Execution Layer and remain necessary regardless of the broader product vision.

### Semantic Objects

**Status:** Future Vision (partially **Implemented** via metadata + Parts)

Today generators create geometry with semantic metadata.

A future object might fully contain:

- Geometry, Components, Parameters
- Constraints, Clearance, Interaction Zones
- Metadata, AI Hints, Evaluation Rules

The mesh is only one representation of the object.

### Clearance System

**Status:** **Implemented** (DD-007 Accepted) — evaluation still Planned (DD-008)

Objects generate invisible usage volumes.

**Examples:**

- Bed → entrance area
- Wardrobe → door swing / front access
- Door → opening radius
- Desk → chair movement area

These are not collisions. They describe how an object is used.

Constraint *evaluation* → DD-008 (**Planned**).

### Constraint System

**Status:** **Implemented** (DD-008 Accepted, v0.8.0) — v1 `zone_must_be_clear` only

Objects expose semantic rules evaluated at analysis time.

**Examples:**

- minimum entrance width
- preferred entrance width
- headroom
- safety distances
- accessibility

Analysis reads clearances; does not create them (DD-009 execution boundary).

------------------------------------------------------------------------

# 9. Long-term Architecture

**Status:** Future Vision — does not replace current five-layer module architecture

### Three product layers (long-term)

| Layer | Phase | Focus |
|---|---|---|
| **Layer 1 — Execution / Geometry** | **Now** | Create, move, regenerate, export, analyze objects |
| **Layer 2 — Planning** | Later | Generate variants, evaluate, discard, improve |
| **Layer 3 — Problem Solving** | Long-term | Understand requirements, choose solution spaces, combine existing / purchasable / custom solutions |

**Current development is Layer 1.** That is correct and unchanged.

### Technical foundation (remains necessary)

All of the following stay required regardless of Layer 2/3:

- Generators, Parts, `object_id`, regeneration
- Clearances (DD-007), Constraints / `analyze_layout` (DD-008)
- JSON protocol (DD-003), execution boundary (DD-009 Accepted)

### Evolution path

```
Today:     Generator → Mesh (with semantic metadata)
Near:      Knowledge → Rules → Generator → Parts → Clearances → Analysis
Long-term: Intent → Planning → Execution → spatial solutions for human needs
```

Knowledge becomes the highest abstraction; furniture commands become one output format among many.

------------------------------------------------------------------------

# 10. Deferred / Experimental Ideas

**Status:** Experimental Idea — not scheduled

Ideas captured for later discussion. No DD, no roadmap slot.

| Idea | Notes |
|---|---|
| Walkway / navigation graph | See §5 — needs stable constraints first |
| IKEA import / product catalog | MDD Phase 3 mention — product search not current scope |
| Asset preview thumbnails | UI polish, not planning core |
| Scoring (“73% good layout”) | After findings engine (DD-008+) |
| Automatic layout repair | AI + planning layer, not execution |
| Room boundary / wall detection | Unless explicit room mesh in scene |
| Physics collision | Rejected for v1 analyzer — semantic AABB sufficient (DD-008) |

### Important observation

Cursor currently implements ideas faster than the architecture matures.

**Not every good idea should immediately become code.**

Promising ideas should be documented here first.

------------------------------------------------------------------------

# Document maintenance

- **Single backlog file** — do not split into multiple Future-Idea documents.
- Update this file when a vision concept matures toward a DD.
- When a DD is Accepted, move factual contract to ARCHITECTURE / json_protocol / object_model; keep only vision summary here.
- Cross-link: [LayoutLab_Manifest.md](../LayoutLab_Manifest.md), [AI_CONTEXT.md](../AI_CONTEXT.md), [ARCHITECTURE.md](ARCHITECTURE.md).

------------------------------------------------------------------------

# Final thought

The goal of this document is not to collect features.

The goal is to protect the architecture while giving ideas — especially **problem-first, human-centred spatial planning** — room to mature.
