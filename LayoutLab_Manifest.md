# LayoutLab Manifest

*Why this project exists.*

------------------------------------------------------------------------

# We are not building a Blender addon.

We are building a new way to think about interior planning.

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

That requires semantic objects.

Not meshes.

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

One day LayoutLab should be able to answer questions like:

-   Does this room work for two children?
-   Can an adult still sit beside the bed?
-   Is there enough storage?
-   Where is unused space?
-   Can I fit another wardrobe?
-   Is there enough daylight?
-   Which layout is objectively better?

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

It is about teaching software how furniture works.

Once the software understands objects,

creating geometry becomes the easy part.
