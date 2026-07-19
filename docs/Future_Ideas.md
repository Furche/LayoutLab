# Future Ideas

> Living document. Ideas only — not commitments.  
> **Last reorganized:** 2026-07-16 (standalone end-to-end product experience, spatial project model, mobile capture)

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

**Status:** Future Vision (sharpened 2026-07-12; end-user product experience 2026-07-16)

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

### Standalone product experience (long-term)

**Status:** Future Vision — **not** current implementation

Long-term, LayoutLab should be usable as a **standalone application**. The end user should need neither Blender expertise nor copying JSON between tools.

From the user’s perspective, LayoutLab is one coherent surface:

- integrated conversation with an AI
- own 2D/3D viewport
- project and space management
- requirements and human needs
- existing furniture
- layout variants
- analysis and explanations
- apply, discard, and compare solutions

**Blender remains the fully supported reference runtime today.** The standalone app is product vision, not an implementation task. Details: §12–§18. Runtime adapters: §11.

### Relationship to today

Today the product still speaks largely in generators and JSON commands inside Blender — that is correct for the current phase (Execution Layer). This vision describes **where the product is heading**, not what to build next.

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

**Status:** Future Vision (partial foundations: DD-008 **Implemented**)

### Variant generation and comparison

**Status:** Future Vision

Beyond placing one layout, LayoutLab could:

- generate multiple layout variants
- score and rank them
- explain trade-offs (“more play area, less storage”)

Depends on: stable `analyze_layout` (DD-008 **Implemented**), richer evaluation rules, Intent/Planning layers (§9).

Variants should become **first-class objects** of the Spatial Project Model — not accidental full-scene copies. See §16 and **[DD-011](design_decisions/DD-011-layout-variants-and-comparison.md)** (**Accepted**: Planning v1 ephemeral candidates + rank; full project variants later).

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

**Depends on:** stable `analyze_layout` (DD-008 **Implemented**), bridge MVP (§7), undo transaction support in plugin.

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

**Status:** Mix — JSON **Implemented** (DD-003); bridge **Future Vision**; integrated AI product UI **Future Vision**

### Intent, Planning, Execution (layer separation)

**Status:** Future Vision — architecture direction, not implemented as product layers

| Layer | Responsibility | Today |
|---|---|---|
| **Intent** | User goals, natural language, requirements | AI / user (outside plugin) |
| **Planning** | Generate variants, evaluate, discard, improve | Future — not in plugin |
| **Execution** | Deterministic LayoutLab operations | Plugin + JSON protocol **Implemented** |

The current JSON API belongs to the **Execution Layer** only. A future AI bridge or in-app AI must **not** merge these layers — it forwards defined operations; it does not replace planning logic inside the addon without a DD.

See [DD-009](design_decisions/DD-009-ai-execution-boundary.md) (**Accepted**): AI plans WHAT; plugin executes HOW.

### Integrated AI conversation (product experience)

**Status:** Future Vision — possible later **DD-012**

In a future standalone LayoutLab app, the user talks to an AI **inside** the product — not in an external chat that pastes JSON into Blender.

Example intent:

> “This children’s room must work for two children. The existing wardrobe stays. Keep as much play area as possible. An adult must be able to sit for bedtime.”

The AI should then:

1. Derive requirements  
2. Ask for missing information  
3. Analyse room and existing furniture  
4. Develop several layout variants  
5. Have LayoutLab Core **check** those variants (execution + analysis APIs)  
6. Correct errors using analysis findings  
7. Present best results in the viewport  
8. Explain trade-offs in plain language  

**Hard boundary (unchanged from DD-009):** the AI is **not** a free Blender-Python agent. Deterministic execution stays LayoutLab property.

**Provider policy (undecided):** AI provider should be **swappable**; LayoutLab must not be locked to one vendor or model. Auth, API keys, local models, subscriptions, privacy, and cloud vs local processing need **separate future decisions** — do not invent them here.

End-to-end empty-app journey: §12.

### AI–Plugin Direct Communication

**Status:** Future Vision (documented in DD-009 — not implemented)

Today the user copies JSON between chat and Blender.

Future: a **local LayoutLab Bridge** so the AI (or in-app agent) calls defined operations without clipboard.

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
- `analyze_layout` (**Implemented** in plugin; bridge still Future Vision)

The bridge forwards to the addon / Core; it does not reimplement generator logic.

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

**Status:** **Implemented** (DD-007 Accepted)

Objects generate invisible usage volumes.

**Examples:**

- Bed → entrance area
- Wardrobe → door swing / front access
- Door → opening radius
- Desk → chair movement area

These are not collisions. They describe how an object is used.

### Constraint System

**Status:** **Implemented** (DD-008 Accepted, v0.8.0) — v1 `zone_must_be_clear` only

Objects expose semantic rules evaluated at analysis time.

**Examples:**

- minimum entrance width
- preferred entrance width
- headroom
- safety distances
- accessibility

Analysis reads clearances; does not create them (DD-009 execution boundary). Room-as-blocker and tiered multi-zone access groups remain future extensions (not standalone product work).

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
Long-term: Intent → Requirements → Spatial Project → Planning → Variants
           → Execution → Analysis → Solution
```

Knowledge becomes the highest abstraction; furniture commands become one output format among many. Spatial Project / Property / Building concepts: §13 (Future Vision only).

------------------------------------------------------------------------

# 11. Blender-independent LayoutLab Runtime and Viewport

**Status:** Future Vision / Architectural Option — **not implemented**, no DD required yet

### Core idea

Blender is understood as the **first LayoutLab runtime** (Blender Backend / Adapter), not necessarily the permanent product centre.

Long-term target shape:

```
LayoutLab Core
    ├── Desktop / Web Standalone Editor   ← Future Vision (authoring + AI + variants)
    ├── Mobile Capture Client             ← Future Vision (scan / confirm; not full editor)
    ├── Blender Runtime / Adapter         ← today (primary, fully supported)
    └── optional Read-only Viewer         ← early experiment possible; existing 3D framework
```

### LayoutLab Core (domain logic)

Furniture and layout knowledge that should survive a runtime change:

- Project / room / object models (semantic) — see §13
- Generators, Parts, parameters, stable `object_id`
- Clearances, constraints, layout analysis rules
- Protocols and data models (JSON export schema, command contract)
- Variant and planning logic (future — §16)

### Blender Runtime (adapter today)

Blender-specific implementation — acceptable here, not in Core:

- `bpy` mesh/object creation, collections, materials
- Parenting, selection, undo, viewport display
- Addon UI (panel, operators, diagnostics harness)
- Scene import/export **into** Blender data blocks

### Architectural rule (from 2026-07-12)

Before new features, ask:

> **Is this LayoutLab property or Blender property?**

| LayoutLab | Blender Runtime |
|---|---|
| Clearance semantics, overlap rules | Wire mesh display, `show_in_front` |
| `object_id`, params merge policy | `bpy.data.objects`, parenting |
| JSON command contract | Clipboard, text blocks, operators |
| Generator rules | `create_box` mesh instantiation |

**Does not mean:** immediate full abstraction or refactor.  
**Does mean:** no *new* unnecessary `bpy` coupling; document existing coupling; implement new Core logic as pure Python / neutral data where practical.

### Neutral scene description (direction)

Generators should eventually be able to emit a **runtime-neutral description** (furniture, parts, primitives, transforms, material refs, metadata, clearances) that any adapter translates — Blender first.

**Not implementing now.** Current export JSON (`layoutlab` blocks, bounds) is the first neutral artifact; generators still call `api["create_box"]` directly.

### Future viewport (standalone authoring, not only viewer)

A later **own viewport** would use an **existing 3D technology** — **not** a custom GPU render engine from scratch.

- **Phase A (DD-014 Accepted):** read-only **web** viewer of export JSON (Three.js or Babylon); show findings when present. Contract: `json_protocol.md` §6.4; fixture `reference_kids_room_export.json`.
- **Long-term product:** full LayoutLab application with authoring, integrated AI, variants, and analysis — not “viewer only” (Phase B+).

### Explicitly out of scope now

- Phase B write adapter (until separate Accept)
- Separate product fork / replacing Blender as reference runtime
- Custom render engine
- Large refactor for abstraction alone
- Mobile scanner, cloud sync (see §18)

### When a formal DD becomes necessary

| Topic | Possible later DD |
|---|---|
| Project / multi-room / multi-floor model | **DD-010** — Project and Spatial Model |
| Variants as first-class objects | **DD-011** — Layout Variants and Comparison |
| In-app AI product experience | **DD-012** — Integrated AI Product Experience |
| Capture / reconstruction pipeline | **DD-013** — Capture and Reconstruction Pipeline |
| Neutral authoring model + second write runtime | **DD-014** — [Accepted — Phase A](design_decisions/DD-014-standalone-runtime-path.md) (web viewer next; Phase B later) |

Do **not** create or accept these DDs until implementation is actually planned. Until then: document here + `ARCHITECTURE.md` §2.2.

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
| Room boundary / wall detection | Unless explicit room mesh in scene; related to §13–§14 |
| Physics collision | Rejected for v1 analyzer — semantic AABB sufficient (DD-008) |
| **Read-only export viewer** | **DD-014 Phase A** — Accepted; scaffold next (web / Three.js|Babylon) |

### Important observation

Cursor currently implements ideas faster than the architecture matures.

**Not every good idea should immediately become code.**

Promising ideas should be documented here first.

------------------------------------------------------------------------

# 12. Standalone Product Experience and End-to-End User Journey

**Status:** Future Vision — no implementation

### Goal

The user does **not** build a Blender scene. They describe a property, what already exists, and a spatial problem. LayoutLab returns checkable solutions.

### Possible conversation from an empty app

AI: “Do you want to plan a single room, an apartment, or a whole building?”

User: “A children’s room for my eight-year-old. Full re-furnishing.”

AI: “Do you already have a digital room model, a floor plan, or shall we capture the room together?”

User: “I have a photo of the floor plan.”

AI: “I recognise a room with these dimensions, one door and two windows. Two measurements are ambiguous — please confirm the marked places.”

After confirmation, LayoutLab creates the spatial foundation. The AI then asks, among other things:

- Who uses the space?
- What must the room achieve?
- Which furniture exists / must stay?
- Priorities and constraints?
- Budget, material, or safety limits?
- One variant or several?

Integrated AI behaviour: §7. Spatial hierarchy: §13. Capture paths: §14.

------------------------------------------------------------------------

# 13. Spatial Project Model

**Status:** Future Vision — **not** a binding schema; single-space Room Model → [DD-010](design_decisions/DD-010-room-model.md) (**Proposed**)

LayoutLab must not assume a project is always exactly one room. **DD-010** starts with
**one editable space** (Room Model). The hierarchy below remains the longer-term target.

Conceptual hierarchy (illustrative only):

```
Project
└── Property
    ├── Building
    │   ├── Floor
    │   │   ├── Space / Room
    │   │   │   ├── Walls
    │   │   │   ├── Openings (Doors, Windows)
    │   │   │   ├── Fixed Elements (Radiators, Columns, Shafts, Built-ins)
    │   │   │   ├── Furniture
    │   │   │   └── Layout Variants
    │   │   ├── Corridors / Circulation
    │   │   └── Stairs
    │   └── additional floors
    └── optional outdoor areas later
```

### Architecture guardrails (for Core design)

New Core logic should **not** deeply assume:

- one Blender scene ≡ one LayoutLab project
- a project always has exactly one room
- all objects live on a single plane
- variants are only full duplicated Blender scenes

A formal DD is required **before** implementing this model. Current implemented contract remains [object_model.md](object_model.md) (Furniture → Parts in a Blender scene).

------------------------------------------------------------------------

# 14. Capture Paths and Mobile Reconstruction

**Status:** Future Vision — possible later **DD-013**

### Import paths into one common Spatial Model

All paths should eventually feed the same internal Spatial Model (§13):

1. Draw the room manually  
2. State measurements in conversation  
3. Guided wall-by-wall input  
4. Photo or scan of a floor plan  
5. PDF floor plan  
6. CAD / IFC / other plan import  
7. Classify an existing Blender model  
8. Smartphone video  
9. Smartphone depth / LiDAR  
10. Combination of several sources  

### Mobile video and LiDAR capture

Possible workflow:

1. User starts a guided scan in LayoutLab.  
2. App asks them to walk slowly through rooms and connections.  
3. Video, camera poses, and depth (if available) are recorded.  
4. Spatial reconstruction is produced.  
5. Semantic elements are proposed: walls, floor/ceiling, doors, windows, radiators, stairs, built-ins, coarse furniture.  
6. Rooms and floors are linked into one project model.  
7. Uncertain regions are marked.  
8. AI asks for extra takes or manual confirmation.  
9. Only **confirmed** data becomes the trusted planning basis.

Example:

> “The corner behind the wardrobe is not fully visible — please film it again.”  
> “I think this is an 82 cm door — please confirm.”  
> “These two hallway takes do not connect yet — show the living-room transition again.”

### Mobile Capture Client vs full editor

```
LayoutLab Core
├── Desktop / Web Standalone Editor
├── Mobile Capture Client     ← may only: create/select project, scan, photos, measures, sync
└── Blender Runtime / Expert Frontend
```

No platform or stack is chosen here. Confidence rules: §15.

------------------------------------------------------------------------

# 15. Confidence, Verification and Measurement Trust

**Status:** Future Vision — principles only

- Reconstructed facts may carry a **confidence** value.  
- Clear vs uncertain data must be distinguishable.  
- Critical measures should be confirmable or manually correctable.  
- Uncertainty must be shown transparently.  
- AI / scanners must not invent non-visible structure as certain.  
- Furniture recognition is a **proposal**, not unchecked fact.  
- A recognised product (e.g. a specific shelf model) needs user confirmation before exact product data is adopted.  
- Auto-measures help planning; they are **not** automatically valid for construction, statics, or safety-critical work.  
- Professional survey and technical review remain required where those uses apply.

Capture and import must write into a **validation / confirmation** state — not silently into the authoritative project state (see ARCHITECTURE §2.2).

------------------------------------------------------------------------

# 16. Layout Variants as First-Class Objects

**Status:** Future Vision — **DD-011 Accepted** (Planning v1 = ephemeral candidates + rank; full first-class project variants / compare UI still later)

The user should be able to ask: “Show me several sensible solutions.”

A variant may describe, among other things:

- included objects and transforms  
- generator parameters  
- solution strategy used  
- analysis results  
- requirements met or violated  
- scores and trade-offs  
- relation to a base variant  
- user comments / favourites  

**Conceptually:** shared base space + different layout states — not random full Blender scene clones. Temporary side-by-side display in a viewport is fine for UX.

Related: §5 Planning and Evaluation · [DD-011](design_decisions/DD-011-layout-variants-and-comparison.md).

------------------------------------------------------------------------

# 17. Room / Apartment / Building Product Stages

**Status:** Future Vision — possible expansion of the Spatial Model; **not** a binding roadmap

| Stage | Scope (illustrative) |
|---|---|
| **1 — Room Builder** | Single rectangular/polygonal room; height; walls; doors; windows; radiators; fixed obstacles; measures and simple edit — **DD-010 Proposed** (Room Model, not room generator) |
| **2 — Apartment Model** | Connected rooms; shared walls; passages; corridors; variants per room or whole apartment; furniture redistributable across rooms |
| **3 — Building Model** | Multiple floors; stairs; storey heights; shafts; roof slopes; fixed/changeable fabric; outdoor areas later optional |

These stages describe **how far** the Spatial Model might grow. They do **not** replace the current Execution Layer roadmap.

------------------------------------------------------------------------

# 18. Explicitly Not Building Now

**Status:** Binding for current phase — documentation only

Do **not** implement from this vision until separate DDs and explicit product need:

- Standalone desktop or web app  
- Mobile scanner / video reconstruction / LiDAR / photogrammetry / floor-plan OCR  
- Building editor / multi-floor model  
- In-plugin KI chat / provider login  
- Variant system / neutral scene authoring model  
- Sync service / cloud backend  
- Custom render engine  

**Current focus remains:** Blender as primary Execution Runtime — generators, clearances, analysis, JSON protocol.

------------------------------------------------------------------------

# 19. Possible Future Design Decisions (reservation only)

| ID | Title | Status |
|---|---|---|
| [DD-010](design_decisions/DD-010-room-model.md) | Room Model (single space) | **Accepted** (2026-07-16) — MVP in plugin v0.9.0 |
| [DD-011](design_decisions/DD-011-layout-variants-and-comparison.md) | Layout Variants and Comparison | **Accepted** (2026-07-20) — Planning v1: recipe → candidates → rank; implement next |
| DD-012 | Integrated AI Product Experience | **Not created** — reserve when implementing §7 / §12 |
| DD-013 | Capture and Reconstruction Pipeline | **Not created** — reserve when implementing §14–§15 |
| DD-014 | Standalone Runtime Path (viewer → write) | **Accepted — Phase A + B + B2** — [DD-014](design_decisions/DD-014-standalone-runtime-path.md); multi-space Spatial Project still later |

Align numbering with [design_decisions/README.md](design_decisions/README.md) when filing. Do not auto-Accept.

------------------------------------------------------------------------

# Document maintenance

- **Single backlog file** — do not split into multiple Future-Idea documents.
- Update this file when a vision concept matures toward a DD.
- When a DD is Accepted, move factual contract to ARCHITECTURE / json_protocol / object_model; keep only vision summary here.
- Cross-link: [LayoutLab_Manifest.md](../LayoutLab_Manifest.md), [AI_CONTEXT.md](../AI_CONTEXT.md), [ARCHITECTURE.md](ARCHITECTURE.md).
- Capture / Standalone / Spatial vision lives **here**; MDD holds only the product-level summary; ARCHITECTURE holds Core/adapter guardrails.

------------------------------------------------------------------------

# Final thought

The goal of this document is not to collect features.

The goal is to protect the architecture while giving ideas — especially **problem-first, human-centred spatial planning** and a future **standalone, AI-assisted product experience** — room to mature.
