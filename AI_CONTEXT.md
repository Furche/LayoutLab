# AI_CONTEXT.md

Version: 1.0

> This document is not a specification. It is the mental model behind
> LayoutLab. Read this to understand how the project "thinks".

------------------------------------------------------------------------

# What is LayoutLab?

LayoutLab is an engine for semantic, parametric interior planning.

It is **not** a mesh editor.

Meshes are only one possible representation of knowledge.

The core asset is knowledge.

------------------------------------------------------------------------

# Core Mental Model

Traditional CAD:

User → Mesh → Edit Mesh

LayoutLab:

User → Intent → Object Knowledge → Generator → Components → Geometry →
Mesh

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

------------------------------------------------------------------------

# Evolution Path

Today

Generator → Mesh

Future

Knowledge → Rules → Generator → Components → Constraints → Geometry
Builder → Mesh

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

------------------------------------------------------------------------

# Future Possibilities

The architecture should be flexible enough to support:

-   furniture
-   kitchens
-   bathrooms
-   offices
-   gardens
-   campers
-   apartments
-   complete buildings

Without redesigning the engine.

------------------------------------------------------------------------

# Philosophy

The project should evolve by making concepts more general.

Not by accumulating exceptions.

------------------------------------------------------------------------

# Final Thought

If an object understands what it is,

then almost every other feature becomes easier.

That idea is the foundation of LayoutLab.
