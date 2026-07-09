# Design Decisions

Formal record of significant LayoutLab architecture and product decisions.

Each decision follows the format: **Problem → Decision → Alternatives → Consequences**.

New decisions use the next sequential number: `DD-006`, `DD-007`, …

| ID | Title | Status | Date |
|---|---|---|---|
| [DD-001](DD-001-generators-are-parametric-assets.md) | Generators are parametric assets | Accepted | 2026-07-09 |
| [DD-002](DD-002-generators-rebuild-mesh.md) | Generators rebuild mesh (no blind scaling) | Accepted | 2026-07-09 |
| [DD-003](DD-003-json-only-communication.md) | Communication exclusively via JSON | Accepted | 2026-07-09 |
| [DD-004](DD-004-asset-browser-ui.md) | UI oriented on Asset Browser | Accepted | 2026-07-09 |
| [DD-005](DD-005-generator-metadata.md) | Generators carry metadata constants | Accepted | 2026-07-09 |

When implementing anything that touches APIs, JSON protocol, generator behaviour,
or UI patterns — check this index first.
