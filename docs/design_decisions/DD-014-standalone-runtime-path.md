# DD-014 — Standalone Runtime Path (Viewer → Write Adapter)

**Status:** Accepted — Phase A only  
**Date:** 2026-07-17  
**Accepted:** 2026-07-17  
**Version:** 0.2  
**Related:** [DD-003](DD-003-json-only-communication.md) · [DD-009](DD-009-ai-execution-boundary.md) · [DD-010](DD-010-room-model.md) · [ARCHITECTURE.md](../ARCHITECTURE.md) §2.2 · [Future_Ideas.md](../Future_Ideas.md) §11–§12 / §18 · [json_protocol.md](../json_protocol.md) §6.4

------------------------------------------------------------------------

## Decision summary (Accepted)

| Topic | Lock |
|---|---|
| Scope of this Accept | **Phase A only** (read-only viewer). Phase B remains documented direction; re-confirm before implementing write adapter |
| Host for Phase A | **Web** — Three.js or Babylon (implementer picks between these) |
| Findings in viewer | **Yes** — show `analyze_layout` results when present in export |
| Packaging | Blender addon zip ≠ standalone app. Shared **Core** + Blender adapter + Standalone (viewer) adapter; same JSON protocol |

------------------------------------------------------------------------

## Problem

LayoutLab’s Execution Layer works in Blender (Room Model, generators, clearances,
`analyze_layout`). The product direction is a **standalone app** so end users need
neither Blender nor clipboard-JSON.

Without a DD, “go standalone” risks:

- rewriting domain rules inside a new UI stack
- skipping the Core vs Runtime split and coupling a second client to `bpy` habits
- building AI/chat/capture before there is a shareable, versioned scene contract
- confusing **read-only share** with **full authoring runtime**

Alexander wants the shortest path to standalone. This DD locks the **approach and
phase order**, not a tech stack or ship date.

------------------------------------------------------------------------

## Scope

### In scope (DD-014)

- Core vs Runtime Adapter rule (binding for new work)
- Contract for cross-runtime interchange (export / project snapshot)
- **Phase A:** read-only standalone viewer (first shippable non-Blender surface)
- **Phase B:** second write runtime (commands → Core → adapter meshes) — after A
- What stays Blender-primary until B is accepted for implementation
- Open questions that block Accept / Phase A start

### Out of scope (this DD)

- Integrated in-app AI product (possible later **DD-012**)
- Capture / LiDAR / floor-plan OCR (**DD-013**)
- Multi-room apartments / buildings / full Spatial Project (later DD; not this one)
- Layout variants as first-class objects (**DD-011**)
- Choosing Three.js vs Babylon vs Godot / Electron vs web (note in implementation DD or appendix)
- Immediate large Python refactor “for abstraction alone”
- Replacing Blender as **reference** runtime for generator QA

------------------------------------------------------------------------

## Decision (Accepted — Phase A)

### 1. Core statement

> **LayoutLab Core owns domain state and rules (pure data + logic).  
> Runtimes are adapters. Blender is the first adapter; standalone is the second.  
> The first standalone deliverable is a read-only viewer of a versioned export —  
> not a second Blender.**

DD-009 still holds: AI plans WHAT; Core/adapters execute HOW. A standalone UI does
not get to invent furniture/room semantics in the front-end.

### 2. Phased path (fastest honest route)

| Phase | Deliverable | Write? | Status |
|---|---|---|---|
| **A — Viewer** | Web app loads LayoutLab export JSON; shows room + furniture + clearances + findings when present | No | **Accepted — implement next** |
| **B — Write adapter** | Same app (or sibling) applies protocol commands via Core; renders through non-Blender geometry API | Yes | Direction only — re-confirm before code |
| **C — Product shell** | Project UX, in-app AI, capture (separate DDs) | Yes | Future — needs B + DD-012/013 as needed |

**Do not start B or C before A is useful.** A proves the contract and unblocks sharing layouts without Blender.

### 3. Interchange contract

- **Source of truth for A:** scene / project **export JSON** (`json_protocol.md` §6 / §6.4), including `rooms[]`, objects with `layoutlab` blocks, clearance bounds, optional `analysis` findings.
- Export carries **`layoutlab_version`** and **`viewer_schema`** (viewer-minimum: boxes, wall panels/planes, clearance wires, transforms, ids).
- Blender remains able to **produce** that export; Phase A only **consumes** it.
- Reference fixture: `tests/fixtures/reference_kids_room_export.json`

### 4. Core vs adapter (binding)

| Belongs in Core | Belongs in adapter |
|---|---|
| Room Model, opening panel math | `create_quad` / mesh materials / Three.js meshes |
| Generator param rules (sizes, clearances) | Instantiating meshes in host |
| `analyze_layout` overlap rules | Drawing findings in UI |
| JSON command semantics | Clipboard, Blender operators, web file load |

**Rule:** new domain features land in pure Python / JSON first; adapters only project.

### 5. What is *not* required before Phase A

- Tiered clearances, more furniture generators, polygon rooms  
- Bridge / MCP / Expert Mode  
- Full Core extraction of every generator (A can render export boxes without re-running generators)

### 6. Phase A prerequisites (status)

1. ~~This DD Accepted (Phase A only)~~ ✅  
2. ~~Viewer-minimum schema in `json_protocol.md` §6.4~~ ✅  
3. ~~Kids-room export fixture~~ ✅ `reference_kids_room_export.json`  
4. Framework choice (Three.js vs Babylon) — in Phase A scaffold PR, not blocking this Accept

------------------------------------------------------------------------

## Alternatives considered

| Option | Why not (for fastest path) |
|---|---|
| Full standalone editor first | Needs write Core + UI + undo; months before first shareable demo |
| Electron wrapping Blender | Still Blender; not “standalone product” for end users |
| Skip viewer, extract all Core now | Large refactor with no user-visible milestone |
| Wait for capture/AI DDs | Slows path; A does not need them |

------------------------------------------------------------------------

## Consequences

- Roadmap priority: **Phase A web viewer** before more Blender-only features (unless they harden the export contract)
- Blender stays reference for authoring/QA until Phase B is separately accepted for implementation
- Future_Ideas §11 “no viewer prototype” is superseded for **Phase A only**
- Phase B package layout (monorepo vs `layoutlab-viewer`) deferred until B Accept

------------------------------------------------------------------------

## Resolved Accept questions

1. **Phase A host:** Web (Three.js or Babylon — implementer picks)
2. **Findings in viewer:** Yes, when present in export `analysis`
3. **Phase B package:** Deferred until Phase B Accept
4. **Accept scope:** **Phase A only** (this Accept); A→B remains the documented direction

------------------------------------------------------------------------

## Implementation order

1. ~~Viewer-minimum export fields in `json_protocol.md`~~ ✅  
2. ~~Kids-room export fixture~~ ✅  
3. Scaffold Phase A viewer (read-only web) ← **next**  
4. Later: Phase B Accept + Core command path without Blender + geometry adapter
