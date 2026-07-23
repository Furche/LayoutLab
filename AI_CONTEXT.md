# AI_CONTEXT.md

Version: 1.2 · Updated: 2026-07-23

> This document is not a specification. It is the mental model behind
> LayoutLab. Read this to understand how the project "thinks".

**Binding reading order for agents:** `00_READ_THIS_FIRST.md` → this file →
[`docs/ROADMAP.md`](docs/ROADMAP.md) → Active Feature Concept → Accepted DDs →
[`docs/HANDOFF.md`](docs/HANDOFF.md) (as-built / session). Priorities live only in
`docs/ROADMAP.md`.

------------------------------------------------------------------------

# What is LayoutLab?

LayoutLab is an engine for **semantic interior planning** — long-term, it translates
**human requirements for a space into spatial solutions**.

It is **not** a mesh editor or a furniture placer.

Meshes are only one possible representation of knowledge.

The core asset is knowledge. Furniture is a *means*, not the end goal.

> LayoutLab optimizes spatial solutions for human needs — not furniture for its own sake.

See [docs/Future_Ideas.md](docs/Future_Ideas.md) §1 for the sharpened product vision.

**Product surface today:** the **standalone web viewer** (`viewer/`) talking to **LayoutLab Core**
(`layoutlab/` + `server/`) over HTTP/JSON ([DD-014](docs/design_decisions/DD-014-standalone-runtime-path.md)).
Blender remains a supported **runtime adapter**, not the primary place we ship UX.

Large cross-cutting features mature through a stable concept layer:

```text
Future Idea -> Feature Concept (docs/concepts/) -> DD(s) -> work packages -> code
```

Feature Concepts own coherent product behaviour and user flows. DDs own binding
architectural choices; as-built contracts own implemented fields and commands.

------------------------------------------------------------------------

# Core Mental Model

Traditional CAD:

User → Mesh → Edit Mesh

LayoutLab (long-term):

User → Intent → Requirements → Spatial Project → Planning →
Variants → Execution → Analysis → Solution

Object knowledge still sits under execution:

Object Knowledge → Generator → Components → Geometry → Mesh

**Today** the user-facing loop is:

```text
Viewer (UX)  ←→  Core HTTP API  ←→  Spatial Project (rooms[], revision, analysis)
```

Planning (candidates / shortlist / chat) and semantic edit commands already run against Core.
Viewer direct manipulation (gizmos, drag → preview/commit) is shipped; next product work is
in [`docs/ROADMAP.md`](docs/ROADMAP.md) (Active). Behaviour: [FC-001](docs/concepts/FC-001-semantic-direct-manipulation-and-multi-room-editing.md).

Geometry is the final step, not the first.

------------------------------------------------------------------------

# Vocabulary

## Object

Something that has meaning.

Examples:

-   Bed
-   Wardrobe
-   Door
-   Window
-   Desk

Not:

Cube_001

------------------------------------------------------------------------

## Generator

A rule system that knows how one object works.

A generator creates geometry from parameters.

------------------------------------------------------------------------

## Component

Reusable building block.

Examples:

-   Leg
-   Shelf
-   Panel
-   Mattress
-   Pillow
-   Handle
-   Drawer
-   Rail
-   Ladder

Components should become increasingly reusable.

------------------------------------------------------------------------

## Constraint

A rule that limits valid layouts.

Examples:

-   Door swing
-   Walking space
-   Window access
-   Radiator clearance
-   Headroom
-   Safety distances

------------------------------------------------------------------------

## Clearance

Invisible geometry describing required free space.

Eventually every object should be able to generate its own clearance
zones.

------------------------------------------------------------------------

# Product vocabulary (partially shipped)

> Spatial Project / independent rooms are **implemented** in Core ([DD-020](docs/design_decisions/DD-020-spatial-project-independent-rooms.md), `0.10.40`).
> Multi-floor buildings, shared walls, and persisted named variants remain Future Vision.

| Term | Status | Rough meaning |
|---|---|---|
| **Spatial Project** | Shipped (MVP) | Authoring root: `project_id`, `revision`, `rooms[]` |
| **Room** | Shipped (DD-010) | Independent rectangle space + fabric + furniture membership |
| **Opening / Fixed Element** | Shipped | Wall-hosted; may be `ACTIVE` / `INACTIVE_OUTSIDE_WALL` |
| **Requirement / Capability** | Planning slice | Used in recipes / evaluation — not a full requirements UI |
| **Variant (ephemeral)** | Shipped | Planning candidates + shortlist (DD-011/017) |
| **Variant (persisted)** | Future | Named project/room alternatives |
| **Property / Building / Floor** | Future | Multi-storey / site model |
| **Capture Source / Confidence** | Future | Scan/photo reconstruction trust |

------------------------------------------------------------------------

# What Makes LayoutLab Different?

Most tools describe geometry.

LayoutLab describes objects.

This difference affects every architectural decision.

------------------------------------------------------------------------

# Runtimes: Viewer first, Blender as adapter

| Layer | Role today |
|---|---|
| **`viewer/`** | **Primary product surface** — inspect, chat/plan, apply commands, iterate layouts |
| **`server/` + `layoutlab/` Core** | Authority: Spatial Project, generators, analyze, transactions, Undo |
| **Blender addon** | First/legacy runtime adapter — still useful for mesh QA and generator authoring; **not** where new UX lands by default |

The **LayoutLab Core** (generators, object model, protocols, analysis, room ops) stays as
independent from Blender as practical. Blender-specific code belongs in the **runtime adapter**
(`api/`, `plugin/`, bpy glue). See [docs/Future_Ideas.md](docs/Future_Ideas.md) §11 and
[DD-014](docs/design_decisions/DD-014-standalone-runtime-path.md) (**Accepted** — Phase A + B + B2).

**Rule for new work:**

1. Prefer Viewer + Core HTTP unless the task is explicitly Blender/generator-authoring.
2. Ask: *Is this LayoutLab property or Blender/Three.js property?*
3. Mutations go through Core commands / revision (DD-018) — never invent a second authority in the Viewer.

No custom render engine; the Viewer uses Three.js.

------------------------------------------------------------------------

# AI's Role

The AI should think like an interior designer and systems architect.

Not like a scripting assistant.

The AI should always ask:

"What is the general rule?"

before asking

"What code should I write?"

## Execution boundary (DD-009)

LayoutLab separates **planning** from **execution**:

| Role | Responsibility |
|---|---|
| **AI / planning client** | User intent, variants, *what* to place or change |
| **LayoutLab Core** | Deterministic *how* — generators, parts, metadata, clearances, analysis, room/furniture ops |

The Viewer (and optionally Blender) are **clients** of Core. The AI must **not** re-implement
Core rules in ad-hoc scripts each session. It uses the **LayoutLab protocol** (JSON / HTTP).

Direct Blender control by AI is a possible **future Expert Mode** only — not the standard path.
See [DD-009](docs/design_decisions/DD-009-ai-execution-boundary.md) (**Accepted**).

Rules live in versioned software (Core, generators, DDs), not only in prompts.

------------------------------------------------------------------------

# Evolution Path

**Layer 1 — Execution / Core (shipped foundation):** generators, parts, regenerate, clearances,
analyze, semantic transactions, furniture/room ops, Spatial Project MVP

**Layer 2 — Planning (shipped slice):** candidates, evaluate, shortlist, chat Apply

**Layer 2b — Standalone UX (current focus):** Viewer as product — multi-room display,
direct manipulation (preview/commit), clearer planning feedback

**Layer 3 — Problem solving (long-term):** understand requirements, choose solution types

```text
Today (product loop)

Viewer UX → Core commands → Spatial Project export → Viewer scene

Long-term

Intent → Requirements → Spatial Project → Planning → Variants →
Execution → Analysis → Solution
```

Knowledge becomes the highest abstraction.

------------------------------------------------------------------------

# Design Priorities

1.  Correct architecture
2.  Clear APIs (Core contracts)
3.  Viewer UX that respects Core authority
4.  Parametric behaviour
5.  Reusability
6.  Readability
7.  Performance

Performance matters, but only after architecture is solid.

------------------------------------------------------------------------

# Anti-Patterns

Avoid:

-   Hardcoded dimensions
-   Blind scaling
-   UI logic inside generators
-   Generator-specific hacks in the core
-   Duplicate implementations of the same concept
-   **Viewer-only truth** (local transforms that never commit to Core)
-   Treating Blender as the default place for new product features

If two generators solve the same problem differently, consider
extracting a reusable component.

------------------------------------------------------------------------

# Questions Every AI Should Ask

Before implementing:

-   Does this belong in the **Viewer**, **Core**, or a **Blender adapter**?
-   Is this knowledge or geometry?
-   Can this become reusable?
-   Is this object-specific or generic?
-   Will this still work with 200 generators?
-   Does this belong in the core or inside one generator?
-   **Which documents must be updated?** (see `docs/documentation_map.md`)

------------------------------------------------------------------------

# Future Possibilities

The architecture should be flexible enough to support problem-first planning for:

-   accessibility and diverse human needs
-   functional room design (sleeping, playing, circulation, …)
-   custom furniture synthesis (within scope limits — no structural engineering in current roadmap)
-   furniture, kitchens, bathrooms, offices, gardens, campers, apartments, complete buildings

Without redesigning the execution engine. Details: [docs/Future_Ideas.md](docs/Future_Ideas.md).

------------------------------------------------------------------------

# Philosophy

The project should evolve by making concepts more general.

Not by accumulating exceptions.

------------------------------------------------------------------------

# Final Thought

If an object understands what it is,

then almost every other feature becomes easier.

That idea is the foundation of LayoutLab.
