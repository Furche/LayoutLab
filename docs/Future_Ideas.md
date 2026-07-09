# Future Ideas

> Living document. Ideas only --- not commitments.

## Purpose

This document captures promising concepts before they become
architecture or code.

Rule:

Idea → Discussion → Design Decision → Architecture → Implementation

Never skip these steps.

------------------------------------------------------------------------

## Why this exists

LayoutLab is evolving quickly.

Cursor can implement ideas faster than we fully understand them.

That is a strength---but also a risk.

Some ideas look like features, but are actually parts of a much larger
architectural concept.

Those ideas belong here first.

------------------------------------------------------------------------

# Semantic Objects

**Status:** Vision

Today generators create geometry.

Tomorrow they may create knowledge.

A future object might contain:

-   Geometry
-   Components
-   Parameters
-   Constraints
-   Clearance
-   Interaction Zones
-   Metadata
-   AI Hints
-   Evaluation Rules

The mesh is only one representation of the object.

------------------------------------------------------------------------

# Clearance System

**Status:** Vision

Objects generate invisible usage volumes.

Examples:

-   Bed → entrance area
-   Wardrobe → door swing
-   Door → opening radius
-   Desk → chair movement area

These are not collisions.

They describe how an object is used.

------------------------------------------------------------------------

# Constraint System

Objects expose semantic rules.

Examples:

-   minimum entrance width
-   preferred entrance width
-   headroom
-   safety distances
-   accessibility

------------------------------------------------------------------------

# Walkway Analysis

Treat the room as a navigation graph.

Possible questions:

-   Can every object be reached?
-   Is the window accessible?
-   Can the radiator be reached?
-   Is the room blocked?

------------------------------------------------------------------------

# Evaluation Engine

Instead of only placing furniture, LayoutLab could evaluate layouts.

Possible metrics:

-   play area
-   storage
-   accessibility
-   daylight
-   walking distances
-   adult usability
-   child usability

The engine should explain *why* one layout is better.

------------------------------------------------------------------------

# Component Library

Generators should eventually orchestrate reusable components:

-   Leg
-   Panel
-   Shelf
-   Mattress
-   Pillow
-   Handle
-   Rail
-   Ladder

Generators become rule systems rather than geometry builders.

------------------------------------------------------------------------

# Important Observation

Cursor currently implements ideas faster than the architecture matures.

Therefore:

**Not every good idea should immediately become code.**

Promising ideas should be documented here first.

------------------------------------------------------------------------

# Final Thought

The goal of this document is not to collect features.

The goal is to protect the architecture while giving ideas room to
mature.
