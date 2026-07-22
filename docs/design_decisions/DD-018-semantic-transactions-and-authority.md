# DD-018 — Semantic Transactions, Revisions and Authority

**Status:** Accepted
**Date:** 2026-07-22
**Accepted:** 2026-07-22
**Version:** 1.0
**Related:** [FC-001](../concepts/FC-001-semantic-direct-manipulation-and-multi-room-editing.md) · [DD-003](DD-003-json-only-communication.md) · [DD-009](DD-009-ai-execution-boundary.md) · [DD-014](DD-014-standalone-runtime-path.md) · [DD-017](DD-017-collaborative-planning-and-contextual-evaluation.md) · [DD-019](DD-019-semantic-direct-manipulation.md) · [DD-020](DD-020-spatial-project-independent-rooms.md)

------------------------------------------------------------------------

## Acceptance note

**Accepted 2026-07-22** (Alexander). Locked defaults:

- Undo is **session-scoped**, configurable, default depth **≥ 50** steps.
- Project `revision` is an **integer counter** (not a content hash).
- Full-scene import commits as **one** `import` transaction and advances revision.

FC-001/WP-02 may implement this DD. Binding field names land in contracts during WP-02.

------------------------------------------------------------------------

## Decision summary (Accepted)

All authoritative mutations to LayoutLab domain state go through **semantic
transactions** owned by Core. User gestures, AI Apply, planner writes and imports
share one revision timeline. Preview is non-authoritative until commit. One
committed gesture or one applied AI candidate equals one Undo unit. Stale AI
proposals (`base_revision` mismatch) must not apply blindly.

Binding field names land in contracts at implementation (`json_protocol.md` /
session model). This DD locks ownership and behaviour.

------------------------------------------------------------------------

## Problem

Today mutations arrive via JSON commands, agent Apply, and Blender/session undo
without a shared semantic revision model. FC-001 requires:

- reversible manual edits and AI Apply on one timeline;
- preview during drag without flooding Undo;
- protection of manual work from stale or unprotected AI overwrites;
- no parallel “viewport truth” vs “Core truth”.

Without a DD, implementers risk Blender-only undo, command lists without
revisions, or AI that reapplies outdated candidates after the user moved furniture.

------------------------------------------------------------------------

## Scope

### In scope

- Transaction / revision / Undo / Redo authority model
- Preview vs commit
- Actor and provenance
- Stale proposal protection (`base_revision`)
- Relationship to DD-009 (AI plans WHAT; Core executes HOW) and DD-017 (clone → validate → Apply)
- Schema ownership: where authoritative state lives

### Out of scope

- Concrete JSON schema field freeze (implementation of FC-001/WP-02)
- Direct-manipulation gestures (DD-019)
- Multi-room project identity (DD-020)
- Persisted project variants (Future Ideas §16)
- Blender Expert Mode / desktop Bridge product shell

------------------------------------------------------------------------

## Decision

### 1. Core statement

> **Core owns the authoritative project revision. Every committed mutation is a
> semantic transaction with actor, base revision and result revision. Viewports
> and AI clients propose or preview; they do not hold a second source of truth.**

### 2. Schema ownership

| Concern | Owner |
|---|---|
| Authoritative project / room / object state | **LayoutLab Core** |
| Binding command & export fields | `json_protocol.md` / `room_model.md` / object contracts at WP-02+ |
| Product behaviour & invariants | FC-001 |
| Architectural locks in this package | DD-018 / DD-019 / DD-020 |
| Runtime adapters (Blender, Viewer) | Project Core state; may hold ephemeral preview only |

No viewport-only semantic state may survive a commit without a Core transaction.

### 3. Transaction model

A committed transaction records at least:

```text
actor: user | ai | planner | system | import
action
base_revision
result_revision
operations
description
timestamp
```

Rules:

- `result_revision` is monotonically increasing per project (exact encoding left to WP-02).
- Undo restores the project to the pre-transaction revision for that step.
- Redo reapplies the **same committed semantic operations** against the revision
  produced by that Undo — it must not re-invoke AI, recipe search or repair heuristics.
- Applying one AI candidate (possibly many underlying object ops) is **one** transaction
  and **one** Undo unit.
- One completed user gesture (e.g. drag release) is **one** transaction and **one** Undo unit.

### 4. Preview vs commit

```text
begin preview  -> non-authoritative view of pending ops
update preview -> may update ephemeral geometry / validation hints
commit         -> one transaction; revision advances
cancel         -> discard preview; revision unchanged
```

Preview must not create Undo steps. Validation during preview may show invalid/red
states without committing them.

### 5. Authority and AI safety

- AI proposals carry `base_revision` of the project they were computed against.
- If current revision ≠ `base_revision`, Core **must** revalidate or regenerate;
  blind apply is forbidden.
- `protected_from_ai` on objects or properties is a hard constraint at Apply time.
- Provenance records last writer (`user` | `ai` | `planner` | `import` | `system`).
- Manual `user` provenance must not be silently overwritten by AI assumptions.
- Internal AI/planner attempts continue on **cloned** state (DD-017); only explicit
  user Apply commits a transaction to the live project.

### 6. Actors vs locks

| Property | Meaning |
|---|---|
| `locked` | User cannot edit (UI / command reject) |
| `protected_from_ai` | AI Apply cannot change object/property |
| `visible` / `included_in_analysis` | Orthogonal; see FC-001 §9 |

These remain separate flags (FC-001). This DD only requires that transaction
application honour them.

------------------------------------------------------------------------

## Alternatives considered

| Alternative | Why rejected |
|---|---|
| Blender Undo as sole history | Not portable to Core/Viewer; not semantic |
| Command log without revisions | Cannot detect stale AI proposals reliably |
| Separate AI sandbox project forever | Breaks “one authority model”; Apply would still need revisions |
| Auto-merge stale proposals | Violates FC-001; risks overwriting manual work |

------------------------------------------------------------------------

## Consequences

**Positive**

- Manual and AI edits share one reversible timeline.
- Stale proposals become detectable.
- WP-02 can implement without inventing a second authority story.

**Trade-offs**

- Core must keep a session Undo history (default ≥ 50 steps).
- Adapters must map gestures to preview/commit, not raw mesh ops.

**Follow-on**

- FC-001/WP-02 implements this DD.
- DD-019 / DD-020 assume this boundary.

------------------------------------------------------------------------

## Resolved review questions

1. **Undo depth:** session-only; configurable; default ≥ 50.
2. **Full-scene import:** one `import` transaction; revision advances (does not reset to a parallel timeline).
3. **Revision encoding:** integer counter per project.

------------------------------------------------------------------------

## Implementation order (after Accept)

1. Core revision + in-memory transaction / Undo log (session; depth ≥ 50 default).
2. Preview session API; commit/cancel.
3. Wire AI Apply and command batches through transactions.
4. Stale `base_revision` checks + `protected_from_ai` enforcement.
5. Contracts + tests; no viewport-only authority.

------------------------------------------------------------------------

## History

| Ver | Date | Note |
|---|---|---|
| 0.1 | 2026-07-22 | Proposed — FC-001/WP-01 decomposition |
| 1.0 | 2026-07-22 | **Accepted** — session Undo ≥ 50; integer revision; import = one transaction |
| 1.1 | 2026-07-22 | Implemented in Core `0.10.36` (FC-001/WP-02): `commit_commands`, preview, Undo/Redo, stale `base_revision` |
