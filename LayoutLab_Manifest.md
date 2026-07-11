# LayoutLab Manifest

*Why this project exists.*

------------------------------------------------------------------------

# We are not building a Blender addon.

We are building a new way to think about interior planning — and, long-term,
a way to **translate human requirements for a space into spatial solutions**.

Blender is currently our editor.

It is **not** the product.

------------------------------------------------------------------------

# The Problem

Today's room planners think in meshes.

Move mesh.

Scale mesh.

Duplicate mesh.

Real furniture does not work like that.

A bed is not a cube.

A wardrobe is not a scaled box.

A kitchen is not a collection of meshes.

They all have rules.

------------------------------------------------------------------------

# Our Belief

Objects should understand what they are.

A bed knows

-   where its legs belong
-   where the mattress belongs
-   how many pillows it should have
-   how it changes when it becomes wider
-   what happens if it becomes a loft bed

A wardrobe knows

-   where shelves belong
-   where doors belong
-   when another door becomes necessary

The mesh is only the visible result.

The knowledge is the asset.

------------------------------------------------------------------------

# Why AI?

Traditional software waits for commands.

LayoutLab should understand intent.

Instead of saying

> Move object by 34 cm.

The user should be able to say

> Make enough room for a second child.

or

> Keep as much play area as possible while two children can sleep here.

That requires understanding **problems and goals first** — furniture is only a means.
Semantic objects and spatial rules make that possible. Not meshes.

------------------------------------------------------------------------

# Why Blender?

Because Blender already provides

-   an excellent viewport
-   snapping
-   collections
-   asset workflows
-   Python
-   geometry tools

We stand on the shoulders of Blender instead of reinventing them.

------------------------------------------------------------------------

# Long-Term Vision

One day LayoutLab should answer questions like:

-   Does this room work for two children?
-   Can an adult still sit beside the bed?
-   Is there enough storage?
-   Where is unused space?
-   Can I fit another wardrobe?
-   Is there enough daylight?
-   Which layout is objectively better?
-   Can a wheelchair user move safely here?
-   Are paths clear for someone with visual impairment?

**Guiding principle (long-term):** LayoutLab optimizes spatial solutions for human
needs — not furniture for its own sake.

Details and status markers: [docs/Future_Ideas.md](docs/Future_Ideas.md) §1 Product Vision.
Current implementation remains the Execution Layer (generators, JSON, analysis).

------------------------------------------------------------------------

# Design Principles

1.  Model knowledge instead of geometry.

2.  Everything should be parameter driven.

3.  Rules are more valuable than meshes.

4.  A generator represents expertise.

5.  Simplicity beats cleverness.

6.  Architecture before implementation.

7.  Every important decision should be documented.

------------------------------------------------------------------------

# Success Criteria

If, in a few years, someone can design an entire apartment simply by
talking to LayoutLab---

without manually editing hundreds of meshes---

then this project has succeeded.

------------------------------------------------------------------------

# Final Thought

LayoutLab is not about drawing furniture.

It is about turning human requirements into workable spatial solutions.

Furniture, layout, and custom constructions are means — not the goal.

Once the software understands objects and room functions,

creating geometry becomes the easier part.
