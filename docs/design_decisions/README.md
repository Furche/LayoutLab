# Design Decisions

Formal record of significant LayoutLab architecture and product decisions.

Each decision follows the format: **Problem → Decision → Alternatives → Consequences**.

New decisions use the next sequential number: `DD-006`, `DD-007`, …

**When to create a DD:** see [docs/documentation_map.md](../documentation_map.md) (Design decisions section).

| ID | Title | Status | Date |
|---|---|---|---|
| [DD-001](DD-001-generators-are-parametric-assets.md) | Generators are parametric assets | Accepted | 2026-07-09 |
| [DD-002](DD-002-generators-rebuild-mesh.md) | Generators rebuild mesh (no blind scaling) | Accepted | 2026-07-09 |
| [DD-003](DD-003-json-only-communication.md) | Communication exclusively via JSON | Accepted | 2026-07-09 |
| [DD-004](DD-004-asset-browser-ui.md) | UI oriented on Asset Browser | Accepted | 2026-07-09 |
| [DD-005](DD-005-generator-metadata.md) | Generators carry metadata constants | Accepted | 2026-07-09 |
| [DD-006](DD-006-parts-and-finalization.md) | Parts model, join-on-finalize, main/dynamic parts | Accepted | 2026-07-10 |
| [DD-007](DD-007-clearance-zones.md) | Clearance zones (descriptive usage volumes) | Accepted | 2026-07-10 |
| [DD-008](DD-008-constraints-and-layout-analysis.md) | Constraints and layout analysis | Accepted | 2026-07-12 |
| [DD-009](DD-009-ai-execution-boundary.md) | AI execution boundary; plugin responsibility | Accepted | 2026-07-12 |
| [DD-010](DD-010-room-model.md) | Room Model (single space) — editable space, not room generator | **Accepted** | 2026-07-16 |
| [DD-014](DD-014-standalone-runtime-path.md) | Standalone runtime path (viewer → write adapter) | **Accepted — Phase A + B (room)** | 2026-07-17 |

When implementing anything that touches APIs, JSON protocol, generator behaviour,
or UI patterns — check this index first.

**Reserved (not created):** Future_Ideas §19 may later use DD-011 … DD-013 for
Variants, Integrated AI, Capture Pipeline. **DD-014** is now the Standalone Runtime
path (Phase A + Phase B room write Accepted; multi-space Spatial Project remains a later DD).
Do not invent files for remaining reserved IDs until an actual proposal is written.
