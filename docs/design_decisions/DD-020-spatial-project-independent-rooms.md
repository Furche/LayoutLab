# DD-020 — Spatial Project and Independent Multi-Room MVP

**Status:** Accepted  
**Date:** 2026-07-22  
**Accepted:** 2026-07-22  
**Version:** 1.0  
**Related:** [FC-001](../concepts/FC-001-semantic-direct-manipulation-and-multi-room-editing.md) · [DD-010](DD-010-room-model.md) · [DD-014](DD-014-standalone-runtime-path.md) · [DD-018](DD-018-semantic-transactions-and-authority.md) · [DD-019](DD-019-semantic-direct-manipulation.md) · [Future_Ideas.md](../Future_Ideas.md) §13

------------------------------------------------------------------------

## Acceptance note

**Accepted 2026-07-22** (Alexander). Locked defaults:

- **One canonical format:** Spatial Project with `rooms[]`. A single room is simply
  `len(rooms) == 1`. No parallel long-lived single-room export schema.
- **No legacy export compatibility window** — old single-room-only export shapes need
  not be supported going forward; WP-06 ships the project format.
- World-space overlap between independent rooms: allowed without hard analyzer error in MVP.
- `protected_from_ai` on rooms and objects in MVP (no project-global flag required).

FC-001/WP-06 implements this DD (after DD-018 for project revisions). WP-03…05 may
run against a project that currently holds one room.

------------------------------------------------------------------------

## Decision summary (Accepted)

The authoring root becomes a **Spatial Project** containing zero or more **rooms**.
DD-010 remains the accepted **single-space Room Model** contract inside each room.
The first multi-room milestone supports **independent rooms** only: stable room IDs,
per-room transforms, room-local furniture coordinates, whole-room move with
valid/invalid participation rules from FC-001. Shared walls, passages and
multi-floor buildings are explicitly later.

------------------------------------------------------------------------

## Problem

DD-010 assumes one editable space. FC-001 and the product vision need multiple
rooms in one project without forcing shared-wall topology in the first version.

Risks without a DD:

- treating Blender collections or Viewer scene graphs as the project model;
- inventing coupled wall graphs too early;
- breaking DD-010 by rewriting single-room semantics instead of nesting them.

------------------------------------------------------------------------

## Scope

### In scope

- Spatial Project as root identity
- Multiple independent rooms (IDs, transforms, contents, flags)
- Room-local vs world transforms
- Whole-room move participation (valid follows; invalid stays world-fixed)
- Single canonical project format (`rooms[]`; n = 1 is normal)
- What is deferred (shared walls, floors, connected topology)

### Out of scope

- Supporting a parallel legacy single-room-only export format
- Shared-wall ownership, coupled edits, passages/corridors
- Multi-floor / building model
- Persisted named variants (Future Ideas §16)
- Polygon footprints (DD-010 Next — later than FC-001 WP-01…WP-05)
- Transaction machinery (DD-018) and gesture semantics (DD-019) beyond room transform rules

------------------------------------------------------------------------

## Decision

### 1. Core statement

> **A Spatial Project is the durable authoring root. Each room is an independent
> DD-010 space with its own transform and contents. The first multi-room MVP does
> not model shared fabric between rooms.**

### 2. Schema ownership

| Concern | Owner |
|---|---|
| Project identity, room list, project revision | Core (DD-018 revisions are per project) |
| Per-room fabric & commands | DD-010 / `room_model.md` (unchanged principles) |
| Room transform & membership | This DD + FC-001 |
| Binding project JSON | Contracts at FC-001/WP-06 |
| Coupled apartment topology | Future DD after this MVP |

DD-010 is **not** rewritten. Multi-room **extends** it by placing Room Models under a project.

### 3. Hierarchy (MVP)

```text
Spatial Project
├── revision / transaction history (DD-018)
├── Room A (DD-010 model + transform + flags)
│   ├── walls / openings / fixed elements
│   └── furniture (room-local transforms)
├── Room B
└── …
```

Each room has: stable ID, transform, geometry, contents, visibility, lock,
analysis participation, AI-protection flags as applicable.

### 4. Transforms

Default:

```text
world_transform = room_transform * furniture_local_transform
```

When editing a wall changes the room-local origin, DD-019 recomputes local
furniture transforms to preserve world pose.

### 5. Whole-room move

- **Valid** assigned furniture moves with the room (local layout unchanged).
- **Invalid** assigned furniture stays at world position; membership kept;
  local transform recomputed via inverse of the new room transform.
- When the object is valid inside the room again, it participates in later room moves.
- Invalid objects do **not** become world-owned merely because they are invalid.

### 6. Independence rule (MVP)

Rooms do not share walls, openings or ownership. Moving/resizing Room A never
mutates Room B’s fabric. Overlap in world space may be allowed visually; collision
between rooms is **not** a v1 analyzer hard error unless later specified.

Analysis and planning recipes remain **per room** in the MVP unless a future
recipe explicitly targets multiple rooms.

### 7. Canonical format (no parallel single-room schema)

There is **one** durable authoring/export shape: a Spatial Project with `rooms[]`.

- Today’s product use (`len(rooms) == 1`) is the normal single-room case — not a
  separate format.
- WP-06 introduces the project wrapper as the contract going forward.
- **No requirement** to keep reading or writing a legacy single-room-only export
  shape. Old fixtures/tests are updated when WP-06 lands; they are not a
  compatibility product surface.

### 8. Explicitly later

- Shared walls / apartments / passages
- Multi-floor buildings
- Furniture reassignment workflows across rooms (may appear as small WP-06 follow-ups
  after independent rooms work — not required by this Accept)
- Polygon footprints (schedule after FC-001 WP-01…WP-05 per roadmap)

------------------------------------------------------------------------

## Alternatives considered

| Alternative | Why rejected |
|---|---|
| Rewrite DD-010 into multi-room now | Breaks accepted single-space contract |
| Shared-wall graph in v1 | FC-001 non-goal; too large |
| Scene-graph parenting only | No durable Core project identity |
| Parallel long-lived single-room export | Unnecessary; `rooms` length 1 covers it |
| Legacy export compatibility window | Explicitly not required (Accepted 2026-07-22) |

------------------------------------------------------------------------

## Consequences

**Positive**

- Clear nesting: Project → Rooms (DD-010) → furniture.
- One format for n = 1 and n > 1.
- WP-06 can ship useful multi-room without topology research.

**Trade-offs**

- Users cannot yet model real apartment party walls.
- Overlapping independent rooms need UI clarity.
- Pre-WP-06 fixtures must be updated when the project contract ships.

**Follow-on**

- FC-001/WP-06 implements this DD (with DD-018 for project revisions).
- Direct furniture/wall editing (DD-019) ships first against a one-room project (WP-03…05).

------------------------------------------------------------------------

## Resolved review questions

1. **Legacy single-room format** — not supported; Spatial Project only (Accepted).
2. **World overlap** — allowed without hard analyzer error in MVP.
3. **`protected_from_ai`** — rooms and objects in MVP; no project-global flag required.

------------------------------------------------------------------------

## Implementation order (after Accept)

1. Project container as sole durable format (`rooms[]`; start with n = 1 in practice).
2. Room transform ops + whole-room move participation rules.
3. Create/duplicate/delete/hide/lock rooms.
4. Tests for local↔world invariance and invalid participation.
5. Defer shared-wall DD until product need.

------------------------------------------------------------------------

## History

| Ver | Date | Note |
|---|---|---|
| 0.1 | 2026-07-22 | Proposed — FC-001/WP-01 decomposition |
| 1.0 | 2026-07-22 | **Accepted** — project-only format; no legacy single-room export; independent rooms MVP |
