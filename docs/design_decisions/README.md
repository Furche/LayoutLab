# Design Decisions

Formal record of significant LayoutLab architecture and product decisions.

Each decision follows the format: **Problem → Decision → Alternatives → Consequences**.

New decisions use the next sequential number: `DD-006`, `DD-007`, …

**When to create a DD:** see [docs/documentation_map.md](../documentation_map.md) (Design decisions section).

Complete cross-cutting capabilities are described first as stable
[Feature Concepts](../concepts/README.md). A Feature Concept may lead to several
DDs; it does not make architectural choices binding by itself. Current example:
[FC-001 — Semantic Direct Manipulation and Multi-Room Editing](../concepts/FC-001-semantic-direct-manipulation-and-multi-room-editing.md).

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
| [DD-011](DD-011-layout-variants-and-comparison.md) | Layout variants and comparison (Planning v1; recipe = strategy) | **Accepted** | 2026-07-20 |
| [DD-014](DD-014-standalone-runtime-path.md) | Standalone runtime path (viewer → write adapter) | **Accepted — Phase A + B + B2** | 2026-07-17 |
| [DD-015](DD-015-soft-metrics-and-tradeoffs.md) | Soft metrics and rule tradeoffs (AI ↔ LayoutLab) | **Accepted** | 2026-07-20 |
| [DD-016](DD-016-deterministic-layout-recipes.md) | Deterministic layout recipes (Planning Layer v0) | **Accepted** | 2026-07-20 |
| [DD-017](DD-017-collaborative-planning-and-contextual-evaluation.md) | Collaborative planning and contextual candidate evaluation | **Accepted** | 2026-07-21 |

When implementing anything that touches APIs, JSON protocol, generator behaviour,
or UI patterns — check this index first.

**Reserved (not created):** Future_Ideas §19 may later use DD-012 … DD-013 for
Integrated AI and Capture Pipeline. **DD-011** + **DD-017** are **Accepted** (ephemeral
candidates + collaborative evaluation shipped through `0.10.35`; persisted project variants
remain later). **DD-014** is the Standalone Runtime path (Phase A + B room write + B2
generators Accepted; multi-space Spatial Project via FC-001 → future DD).
Ordered product roadmap: [LayoutLab_Master_Design_Document.md](../../LayoutLab_Master_Design_Document.md) §17.
Agent tools: see [../agent_tool_contract.md](../agent_tool_contract.md).
Do not invent files for remaining reserved IDs until an actual proposal is written.
