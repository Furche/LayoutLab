# AI_CONTEXT.md

Version: 1.0

> This document is not a specification. It is the mental model behind
> LayoutLab. Read this to understand how the project "thinks".

------------------------------------------------------------------------

# What is LayoutLab?

LayoutLab is an engine for **semantic interior planning** — long-term, it translates
**human requirements for a space into spatial solutions**.

It is **not** a mesh editor or a furniture placer.

Meshes are only one possible representation of knowledge.

The core asset is knowledge. Furniture is a *means*, not the end goal.

> LayoutLab optimizes spatial solutions for human needs — not furniture for its own sake.

See [docs/Future_Ideas.md](docs/Future_Ideas.md) §1 for the sharpened product vision.
**Current work** (generators, JSON, clearances, analysis) is the correct Execution Layer foundation.

------------------------------------------------------------------------

# Core Mental Model

Traditional CAD:

User → Mesh → Edit Mesh

LayoutLab:

User → Intent (problems, goals) → Requirements → Solution space →
Object Knowledge → Generator → Components → Geometry → Mesh

**Today** most interaction still flows through generators and JSON — that is correct
for the current phase. **Long-term**, intent and planning layers sit above execution.

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

# What Makes LayoutLab Different?

Most tools describe geometry.

LayoutLab describes objects.

This difference affects every architectural decision.

------------------------------------------------------------------------

# Blender's Role

Blender is currently the editor.

It is NOT the engine.

The engine should remain as independent from Blender as practical.

If one day a web frontend or another 3D application is used, the core
ideas should remain valid.

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
| **LayoutLab plugin** | Deterministic *how* — generators, parts, metadata, clearances, analysis |

The AI must **not** re-implement Blender parenting, `object_id`, or generator rules in ad-hoc Python each session. It uses the **LayoutLab protocol** (JSON today; future local bridge).

Direct Blender control by AI is a possible **future Expert Mode** only — not the standard path. See [DD-009](docs/design_decisions/DD-009-ai-execution-boundary.md).

Rules live in versioned software (plugin, generators, DDs), not only in prompts.

------------------------------------------------------------------------

# Evolution Path

**Layer 1 — Execution / Geometry (now):** generators, parts, regenerate, clearances, analyze

**Layer 2 — Planning (future):** variants, evaluate, discard, improve

**Layer 3 — Problem solving (long-term):** understand requirements, choose solution types

Today

Generator → Mesh

Future

Intent → Planning → Execution → spatial solutions for human needs

Knowledge → Rules → Generator → Components → Constraints → Geometry → Mesh

Knowledge becomes the highest abstraction.

------------------------------------------------------------------------

# Design Priorities

1.  Correct architecture
2.  Clear APIs
3.  Parametric behaviour
4.  Reusability
5.  Readability
6.  Performance

Performance matters, but only after architecture is solid.

------------------------------------------------------------------------

# Anti-Patterns

Avoid:

-   Hardcoded dimensions
-   Blind scaling
-   UI logic inside generators
-   Generator-specific hacks in the core
-   Duplicate implementations of the same concept

If two generators solve the same problem differently, consider
extracting a reusable component.

------------------------------------------------------------------------

# Questions Every AI Should Ask

Before implementing:

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
