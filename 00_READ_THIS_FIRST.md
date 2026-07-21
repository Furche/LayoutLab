# 00_READ_THIS_FIRST.md

# LayoutLab -- AI Development Guide

Version: 1.0

> This document is the first file every AI developer (Cursor, ChatGPT or
> future agents) should read before making changes to LayoutLab.

------------------------------------------------------------------------

# Purpose

Your primary task is **not writing code**.

Your primary task is **helping to build LayoutLab**.

Code is only one part of that.

Every implementation should improve the product, not only solve today's
problem.

------------------------------------------------------------------------

# Team Roles

## Alexander

Product Owner.

Responsible for:

-   Vision
-   Priorities
-   Final decisions
-   Testing

------------------------------------------------------------------------

## ChatGPT

System Architect.

Responsible for:

-   Architecture
-   APIs
-   Product Design
-   Generator Design
-   Long-term planning
-   Reviews
-   Design Decisions

------------------------------------------------------------------------

## Cursor

Implementation Engineer.

Responsible for:

-   Writing code
-   Refactoring
-   Bug fixing
-   Keeping documentation updated
-   Following the architecture

Cursor should NOT silently redefine the architecture.

If an architectural improvement is discovered:

-   explain it
-   justify it
-   ask for approval

Do not implement major architectural changes automatically.

------------------------------------------------------------------------

# Development Philosophy

Always think in systems.

Never think in files.

Bad question:

> Which file should I edit?

Good question:

> Which subsystem owns this responsibility?

------------------------------------------------------------------------

# Before Implementing Anything

Ask yourself:

1.  Does this already exist?

2.  Can this become a reusable system?

3.  Is this a one-off hack?

4.  Does this belong in the architecture?

Prefer generic solutions over special cases.

------------------------------------------------------------------------

# Architecture First

Never introduce new architecture casually.

If a new concept is required:

1.  Describe it. If it spans several subsystems or user flows, create a stable
    **Feature Concept (`docs/concepts/FC-xxx`)** instead of expanding
    `Future_Ideas.md` indefinitely.

2.  Explain why.

3.  Explain alternatives.

4.  Derive separate DDs for significant architectural choices.

5.  Wait for approval if the change is significant.

Lifecycle for larger features:

```text
Future Idea -> Feature Concept -> Design Decision(s) -> roadmap work packages -> implementation
```

------------------------------------------------------------------------

# Documentation Requirements

Code without documentation is considered incomplete.

**Documentation before implementation** applies to features. **Documentation with
implementation** applies to every change — using the checklist below, not vague
“update docs if needed”.

Full index of every document, its owner scope, and overlap rules:
**[docs/documentation_map.md](docs/documentation_map.md)**

------------------------------------------------------------------------

# Documentation Update Checklist

After **every** code change, actively walk this list. Mark each item **yes**
(update that document) or **no** (explicitly not affected). Do not skip the list.

| # | Document | Update if the change affects… |
|---|---|---|
| 1 | **README.md** | Installation, quick start, visible features, project structure, roadmap summary |
| 2 | **CHANGELOG.md** | Any user-visible or contributor-relevant change (almost always **yes**) |
| 3 | **DEVLOG.md** | Non-obvious technical decision, phase completion, lesson learned, rejected approach |
| 4 | **docs/generator_api.md** | New/changed/removed `api` function or behaviour passed to generators |
| 5 | **LayoutLab_Generator_Specification.md** | Generator authoring rules, metadata constants, quality bar, structure |
| 6 | **docs/how_to_write_generators.md** | Generator workflows, examples, best practices, anti-patterns, debugging |
| 7 | **layoutlab/generators/\<name\>.md** | Params, components, or behaviour of that specific bundled generator |
| 8 | **layoutlab/generators/README.md** | New/removal of a bundled generator in the index |
| 9 | **docs/json_protocol.md** | Commands, parameters, export schema, protocol markers |
| 10 | **docs/ARCHITECTURE.md** | Modules, layers, migration phases, exceptions, as-built map |
| 11 | **docs/object_model.md** | Custom properties, object grouping, semantic export |
| 12 | **docs/units_and_coordinates.md** | Scale, axes, placement conventions |
| 13 | **docs/concepts/FC-xxx-*.md** | Product behaviour or scope of a cross-cutting feature changes; roadmap work package derived |
| 14 | **docs/documentation_map.md** | New doc file added, or document responsibility moved |
| 15 | **AI_CONTEXT.md** | Vocabulary, mental model, team workflow, project philosophy for agents |
| 16 | **LayoutLab_Master_Design_Document.md** | Roadmap phases, product scope (rare) |
| 17 | **Design Decision (DD-xxx)** | Significant fork: new DD + index in `docs/design_decisions/README.md` |

**Minimum for most commits:** CHANGELOG (**yes**) + every other row explicitly
**yes** or **no** in your completion summary.

If a new design principle appears with real alternatives: create **DD-xxx** before
or with the implementation (see Design Decisions below).

A Feature Concept is not a substitute for a DD. It owns the coherent user-facing
capability; DDs own the architectural choices required to implement it.

------------------------------------------------------------------------

# Design Decisions

Use sequential numbering.

Example

DD-008 Generator Components

Include:

Problem

Decision

Alternatives

Consequences

------------------------------------------------------------------------

# Code Quality

Prefer

-   readable
-   modular
-   reusable
-   explicit

Avoid

-   magic numbers
-   duplicated logic
-   unnecessary abstractions
-   premature optimization

------------------------------------------------------------------------

# Generator Rules

Every new generator must:

-   follow Generator Specification
-   expose metadata
-   support parameters
-   contain sensible defaults
-   contain fallbacks

Never simply scale meshes when semantic rules exist.

------------------------------------------------------------------------

# UI Rules

The user should work with objects.

Never expose implementation details unless useful.

Whenever possible:

Asset Browser feeling \> Technical editor feeling.

------------------------------------------------------------------------

# Refactoring Rules

Before refactoring ask:

Will this change

-   APIs?
-   JSON protocol?
-   Generator behaviour?
-   Existing layouts?

If yes:

Describe the impact before changing it.

------------------------------------------------------------------------

# Logging

When finishing work provide:

1.  What changed?

2.  Why?

3.  Risks

4.  **Documentation checklist** — which rows were yes/no (see above)

5.  Next recommended step

Do not only list files.

Explain reasoning.

------------------------------------------------------------------------

# If You Are Unsure

Do not guess.

Leave a clear TODO.

Explain the uncertainty.

A documented uncertainty is better than an undocumented wrong
assumption.

------------------------------------------------------------------------

# Long-Term Thinking

Always assume LayoutLab will grow.

When writing code ask:

"Will this still make sense with 200 generators?"

Not:

"Does it work for today's bed?"

------------------------------------------------------------------------

# Success Criterion

The best implementation is not the shortest one.

It is the one that makes future features easier.

------------------------------------------------------------------------

# Final Rule

Protect the architecture.

Features come and go.

A clean architecture allows thousands of future features.
