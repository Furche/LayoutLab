# DD-014 — Standalone Runtime Path (Viewer → Write Adapter)

**Status:** Proposed  
**Date:** 2026-07-17  
**Version:** 0.1  
**Related:** [DD-003](DD-003-json-only-communication.md) · [DD-009](DD-009-ai-execution-boundary.md) · [DD-010](DD-010-room-model.md) · [ARCHITECTURE.md](../ARCHITECTURE.md) §2.2 · [Future_Ideas.md](../Future_Ideas.md) §11–§12 / §18

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

## Decision (proposed)

### 1. Core statement

> **LayoutLab Core owns domain state and rules (pure data + logic).  
> Runtimes are adapters. Blender is the first adapter; standalone is the second.  
> The first standalone deliverable is a read-only viewer of a versioned export —  
> not a second Blender.**

DD-009 still holds: AI plans WHAT; Core/adapters execute HOW. A standalone UI does
not get to invent furniture/room semantics in the front-end.

### 2. Phased path (fastest honest route)

| Phase | Deliverable | Write? | Depends on |
|---|---|---|---|
| **A — Viewer** | App/page loads LayoutLab export JSON; shows room + furniture + clearances + optional findings | No | Frozen export subset + fixtures |
| **B — Write adapter** | Same app (or sibling) applies protocol commands via Core; renders through non-Blender geometry API | Yes | Core command path without `bpy`; geometry backend |
| **C — Product shell** | Project UX, in-app AI, capture (separate DDs) | Yes | B + DD-012/013 as needed |

**Do not start B or C before A is useful.** A proves the contract and unblocks sharing layouts without Blender.

### 3. Interchange contract

- **Source of truth for A:** scene / project **export JSON** (`json_protocol.md`), including `rooms[]`, objects with `layoutlab` blocks, clearance bounds, optional analysis findings.
- Export must carry a **`layoutlab_version`** (already) and document a **viewer-minimum schema** (boxes, wall panels/planes, clearance wires, transforms, ids).
- Blender remains able to **produce** that export; Phase A only **consumes** it.

### 4. Core vs adapter (binding while Proposed → Accepted)

| Belongs in Core | Belongs in adapter |
|---|---|
| Room Model, opening panel math | `create_quad` / mesh materials |
| Generator param rules (sizes, clearances) | Instantiating meshes in host |
| `analyze_layout` overlap rules | Drawing findings in UI |
| JSON command semantics | Clipboard, Blender operators, web HTTP |

**Rule:** new domain features land in pure Python / JSON first; adapters only project.

### 5. What is *not* required before Phase A

- Tiered clearances, more furniture generators, polygon rooms  
- Bridge / MCP / Expert Mode  
- Full Core extraction of every generator (A can render export boxes without re-running generators)

### 6. What *is* required before Phase A implementation

1. This DD **Accepted** (or an explicit “Accept Phase A only” note)
2. Short **viewer schema** appendix in `json_protocol.md` (minimum fields)
3. **≥1 checked-in export fixture** from the kids-room reference layout
4. One-page **framework choice** (host tech) in the implementation PR / follow-up note — not blocking Accept of this DD’s *path*

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

### If Accepted

- Roadmap priority shifts: **Phase A viewer** before more Blender-only features (unless they harden the export contract)
- Blender stays reference for authoring/QA until Phase B
- Future_Ideas §11 “no viewer prototype” is superseded for **Phase A only** once Accept + schema note exist

### If Rejected / deferred

- Continue Blender Execution Layer; standalone remains Future Vision without a path lock

------------------------------------------------------------------------

## Open questions (for Accept)

1. **Phase A host:** web (Three.js/Babylon) vs desktop (e.g. Godot) — preference, or “implementer picks”?
2. **Findings in viewer:** show `analyze_layout` results if present in a sidecar / export extension, or geometry-only for A?
3. **Phase B timing:** same repo monorepo app vs separate `layoutlab-viewer` package — preference?
4. **Accept scope:** Accept full A→B path now, or **Accept Phase A only** and re-propose B later?

------------------------------------------------------------------------

## Implementation order (after Accept)

1. Document viewer-minimum export fields in `json_protocol.md`
2. Add `tests/fixtures/` export snapshot(s) from kids room
3. Scaffold Phase A viewer (read-only)
4. Only then: Core command execution without Blender + geometry adapter (Phase B DD amendment or checklist)

**No code under this DD until Status = Accepted** (or written Phase-A-only Accept).

------------------------------------------------------------------------

## Review checklist

- [ ] Agree Core vs adapter rule
- [ ] Agree Phase A = read-only viewer first
- [ ] Answer open questions (or defer host choice to implementer)
- [ ] Accept / Accept-Phase-A / Reject
