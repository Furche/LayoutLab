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

**Status:** Vision → partially implemented (DD-007)

Objects generate invisible usage volumes.

Examples:

-   Bed → entrance area
-   Wardrobe → door swing
-   Door → opening radius
-   Desk → chair movement area

These are not collisions.

They describe how an object is used.

Promoted to DD-007. Constraint *evaluation* → DD-008.

------------------------------------------------------------------------

# Constraint System

**Status:** Vision → proposed (DD-008)

Objects expose semantic rules.

Examples:

-   minimum entrance width
-   preferred entrance width
-   headroom
-   safety distances
-   accessibility

Analysis reads clearances; does not create them (DD-009 execution boundary).

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

# AI–Plugin Direct Communication

**Status:** Future Idea (documented in DD-009 — not implemented)

Today the user copies JSON between chat and Blender.

Future: a **local LayoutLab Bridge** so the AI calls defined operations without clipboard.

Requirements:

- Same semantic operations as JSON protocol (not a second ad-hoc API)
- Localhost / user-approved connection
- No arbitrary remote Python as default

------------------------------------------------------------------------

# Local Agent Bridge

**Status:** Future Idea

A small local process or in-addon listener that exposes:

- `get_scene`
- `list_generators` / `get_generator_schema`
- `preview_operations` / `commit_preview` / `discard_preview`
- `analyze_layout` (after DD-008)

The bridge forwards to the addon; it does not reimplement generator logic.

See DD-009 for architecture sketch and security open questions.

------------------------------------------------------------------------

# Preview → Analyze → Revise → Commit

**Status:** Future Idea

Workflow for AI-driven layout iteration:

1. **Preview** — apply command batch in one undo group
2. **Analyze** — run constraint/clearance checks on preview state
3. **Revise** — AI adjusts plan from findings
4. **Commit** or **Discard** — user or policy confirms

Depends on: stable `analyze_layout` (DD-008), bridge MVP, undo transaction support in plugin.

------------------------------------------------------------------------

# Optional Direct Blender Expert Mode

**Status:** Future Idea (explicitly non-default)

AI may run controlled `bpy` for exploration or one-off debugging when user opts in.

Rules (from DD-009):

- Not a replacement for LayoutLab API in production workflows
- Must be logged; prefer preview/undo wrapper
- Findings should feed back into generators or protocol, not stay as orphan scripts

Security and sandboxing need a separate DD before implementation.

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
