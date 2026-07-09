# DD-001: Generators Are Parametric Assets

Status: **Accepted**  
Date: 2026-07-09  
Version: 1.0

------------------------------------------------------------------------

## Problem

Traditional room planners treat furniture as static meshes or scaled primitives.
Changing a bed from 120×200 cm to 140×200 cm means manual editing or blind
uniform scaling — which breaks proportions (post thickness, pillow count, rail
width).

LayoutLab needs a unit of reuse that captures **how an object works**, not
how it happens to look in one scene.

## Decision

A **generator** is the primary asset type in LayoutLab — not the mesh.

- Each generator is a parametric rule system for one object type (or family).
- Generators accept parameters and produce geometry via `generate(params, api)`.
- Generators are stored as `.py` files, browsable like assets.
- The mesh output is disposable; the generator + params are the source of truth.

## Alternatives Considered

| Alternative | Why rejected |
|---|---|
| **Blender mesh assets** | No parametric behaviour; AI cannot change semantic properties |
| **Geometry Nodes presets** | Blender-specific, hard to drive via JSON, limited rule expression in Python |
| **Single universal parametric engine** | Too abstract; loses domain expertise per object type |
| **Procedural plugin with fixed furniture library** | Not extensible; new furniture requires core plugin changes |

## Consequences

**Positive**

- AI can request `"length": 14` instead of rebuilding geometry manually.
- Expertise lives in generators, not in scene files.
- New furniture types are added without changing the main plugin.
- Aligns with long-term vision: generators become knowledge modules.

**Negative / trade-offs**

- Every object type needs its own generator (initial authoring cost).
- Scene files alone are insufficient to recreate layouts — params must be stored too `[PLANNED]`.
- Generators currently live outside the repo `[EXCEPTION]` — versioning gap until Phase B.

## Implementation Status

| Aspect | Status |
|---|---|
| Generator as `.py` file with `generate()` | `[IMPLEMENTED]` v0.5 |
| Generator browser | `[IMPLEMENTED]` v0.5 |
| Params stored on scene objects for regeneration | `[PLANNED]` |
| Generators versioned in repository | `[PLANNED]` |

## References

- `LayoutLab_Generator_Specification.md`
- `AI_CONTEXT.md` — Generator vocabulary
- `docs/ARCHITECTURE.md` §5.4
