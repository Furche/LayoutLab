# DD-014 — Standalone Runtime Path (Viewer → Write Adapter)

**Status:** Accepted — Phase A + Phase B (room write slice)  
**Date:** 2026-07-17  
**Accepted Phase A:** 2026-07-17  
**Accepted Phase B (room write):** 2026-07-17  
**Version:** 0.3  
**Related:** [DD-003](DD-003-json-only-communication.md) · [DD-009](DD-009-ai-execution-boundary.md) · [DD-010](DD-010-room-model.md) · [ARCHITECTURE.md](../ARCHITECTURE.md) §2.2 · [Future_Ideas.md](../Future_Ideas.md) §11–§12 / §18 · [json_protocol.md](../json_protocol.md) §6.4

------------------------------------------------------------------------

## Decision summary (Accepted)

### Phase A

| Topic | Lock |
|---|---|
| Scope | Read-only web viewer of export JSON |
| Host | Web — Three.js (implemented) |
| Findings | Yes, when present in export `analysis` |

### Phase B (room write slice)

| Topic | Lock |
|---|---|
| Core runs as | Local Python HTTP service (`server/`) |
| First write commands | Room Model subset only |
| Geometry path | Headless viewer export from Room Model (no `bpy`) |
| Viewer role | Send commands + replace scene from returned export |
| Generators | Out of this slice (later B2) |
| Blender | Remains reference for generator QA |
| Package | Monorepo: `layoutlab/` + `viewer/` + `server/` |

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
- **Phase B:** second write runtime — room write slice first; generators later (B2)
- What stays Blender-primary until generators run headlessly

### Out of scope (this DD)

- Integrated in-app AI product (possible later **DD-012**)
- Capture / LiDAR / floor-plan OCR (**DD-013**)
- Multi-room apartments / buildings / full Spatial Project (later DD; not this one)
- Layout variants as first-class objects (**DD-011**)
- Immediate large Python refactor “for abstraction alone”
- Replacing Blender as **reference** runtime for generator QA
- Phase B2: `run_generator` / desk/bed without Blender (separate implement slice)

------------------------------------------------------------------------

## Decision (Accepted)

### 1. Core statement

> **LayoutLab Core owns domain state and rules (pure data + logic).  
> Runtimes are adapters. Blender is the first adapter; standalone is the second.  
> Phase A is a read-only viewer of a versioned export.  
> Phase B (room slice) applies Room Model commands via a local Python service  
> and returns the same viewer export contract — not a second Blender.**

DD-009 still holds: AI plans WHAT; Core/adapters execute HOW.

### 2. Phased path

| Phase | Deliverable | Write? | Status |
|---|---|---|---|
| **A — Viewer** | Web app loads LayoutLab export JSON | No | **Accepted + shipped** |
| **B — Room write** | Local Python service applies room commands → export JSON → viewer | Yes (rooms) | **Accepted — implement** |
| **B2 — Generators** | Headless `run_generator` / furniture without Blender | Yes | Later |
| **C — Product shell** | Project UX, in-app AI, capture | Yes | Future |

### 3. Interchange contract

- Export JSON (`json_protocol.md` §6 / §6.4) is the display contract for A and B.
- Phase B service: `POST /v1/commands` → `{ ok, results, export }`.
- Blender remains able to produce the same export for QA.

### 4. Core vs adapter (binding)

| Belongs in Core | Belongs in adapter |
|---|---|
| Room Model, opening panel math | Blender `create_quad` / Three.js meshes |
| Generator param rules (later B2) | Instantiating meshes in host |
| `analyze_layout` overlap rules | Drawing findings in UI |
| JSON command semantics | Clipboard, Blender operators, HTTP |

**Rule:** new domain features land in pure Python / JSON first; adapters only project.

------------------------------------------------------------------------

## Alternatives considered

| Option | Why not (for fastest path) |
|---|---|
| Full standalone editor first | Needs write Core + UI + undo; months before first shareable demo |
| Electron wrapping Blender | Still Blender; not “standalone product” for end users |
| Browser TypeScript Core rewrite | Duplicates Room Model; slower for Python generators |
| Pyodide in browser | Heavier/experimental for this slice |
| Skip viewer, extract all Core now | Large refactor with no user-visible milestone |

------------------------------------------------------------------------

## Consequences

- Phase A viewer + Phase B room service are the standalone path for rooms
- Generators still require Blender until B2
- Monorepo layout locked: `server/` + `viewer/` + `layoutlab/`

------------------------------------------------------------------------

## Implementation order

1. ~~Viewer-minimum export + fixtures + Phase A viewer~~ ✅  
2. ~~Phase B Accept (room write)~~ ✅  
3. Headless room session + `server/` + viewer Core buttons ← **now**  
4. Later B2: generators without Blender  
