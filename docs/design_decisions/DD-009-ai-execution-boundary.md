# DD-009 — AI Execution Boundary and Plugin Responsibility

**Status:** Proposed (awaiting review)  
**Date:** 2026-07-11  
**Version:** —  
**Related:** [DD-003](DD-003-json-only-communication.md) (JSON transport today) · [DD-007](DD-007-clearance-zones.md) · [DD-008](DD-008-constraints-and-layout-analysis.md)

------------------------------------------------------------------------

## Problem

A capable AI with Blender access could, in principle, run Python (`bpy`) directly:
create meshes, parent objects, set custom properties, and approximate everything
LayoutLab does today.

That raises a product question:

> If the AI can drive Blender, why keep a LayoutLab plugin at all?

Without a clear answer, teams drift toward:

- re-implementing parenting, metadata, and regeneration in prompts every session
- inconsistent behaviour across AI models and clients
- untestable “one-off” scripts replacing versioned engine logic
- security and undo risks from arbitrary `exec` in Blender

LayoutLab must document **who decides WHAT** vs **who guarantees HOW**.

------------------------------------------------------------------------

## Scope

### In scope (DD-009)

- Role split: **AI (planning)** vs **LayoutLab plugin (deterministic execution)**
- Why the plugin remains the **preferred execution path**
- Relationship to DD-003 (JSON as current transport — not replaced)
- Future **Hybrid model**: standard API path vs optional Expert Mode
- Future **Bridge** architecture (concept only — no implementation)
- What the plugin must guarantee vs what the AI may improvise

### Out of scope (now)

- Network service, local agent daemon, MCP server implementation
- Remote arbitrary Python execution
- Replacing clipboard JSON workflow in code
- Weakening DD-003 for the standard path

------------------------------------------------------------------------

## Decision

### 1. Core statement

> **The AI plans and selects operations. LayoutLab executes core operations
> through a stable, versioned API with deterministic, testable behaviour.
> Direct Blender manipulation by AI is not the standard path.**

Knowledge and rules live in **software** (plugin, engine, generators, protocol),
not only in prompts or a single model.

### 2. Responsibility matrix

| Concern | AI / planning client | LayoutLab plugin | Blender (via plugin) |
|---|---|---|---|
| Understand user intent | **Yes** | No | No |
| Choose furniture, params, layout variants | **Yes** | No | No |
| `run_generator` / `regenerate` | Invokes | **Executes** | Creates scene |
| Stable `object_id` | Requests via protocol | **Guarantees** | Stores on objects |
| Parts model, join, parenting | — | **Guarantees** | Applies transforms |
| Generator API, metadata, clearances | — | **Guarantees** | Writes properties |
| `analyze_layout` (DD-008) | Interprets findings | **Computes** | Reads scene |
| Export / import JSON | Consumes / sends | **Produces / applies** | — |
| Ad-hoc bpy for one-off hacks | Expert mode only (future) | Not standard | Direct ops |

**AI answers:** “What should happen?”  
**LayoutLab answers:** “Did it happen correctly, reproducibly, and identically next time?”

### 3. Why not AI-only Blender control?

Direct AI → `bpy` must re-solve correctly on every run:

| Area | Risk without plugin |
|---|---|
| Operator context / `exec()` quirks | Fragile transforms, stale matrices |
| Object identity | Broken regenerate, duplicate UUIDs |
| Parenting & Parts (DD-006) | Mattress/clearance drift |
| Generator rules | Duplicated logic in prompts |
| Clearances & constraints (DD-007/008) | Inconsistent analysis |
| Undo / transactions | Hard to batch or roll back |
| Output format | Non-machine-readable ad hoc |
| Multi-model clients | Same intent, different scripts |

Flexible, but **not reliable enough** as the product foundation.

The plugin centralizes versioned, tested logic (diagnostics, unit tests, DDs).

### 4. Standard path: API-first (today)

**Current transport:** JSON commands + JSON export (DD-003).  
**Execution surface:** `docs/json_protocol.md`, Generator API, engine, parts pipeline.

The AI must not be required to re-implement:

- `execute_generator()` lifecycle
- `PartSession.finish()` parenting
- Clearance metadata (DD-007)
- Constraint analysis (DD-008)

It **calls** documented actions; the plugin **owns** implementation.

DD-003 remains valid: no arbitrary Python for LayoutLab workflows in the standard mode.

### 5. Hybrid model (future — not implemented)

Two modes, explicitly separated:

#### Standard mode (default)

- AI uses **only** LayoutLab protocol operations (`run_generator`, `regenerate`, `analyze_layout`, export, …).
- All changes are validatable, replayable, loggable.
- Compatible with any client that speaks JSON (ChatGPT, Cursor, scripts, future bridge).

#### Expert mode (optional, future)

- AI may run **controlled** Blender Python for exploration, debugging, or rare edge cases.
- Must be **opt-in** per session or per command batch.
- Does **not** replace the LayoutLab API for production layout workflows.
- Changes should run inside a **preview / undo transaction** and be **logged**.
- Expert output should ideally be **promoted** into generators or protocol — not remain one-off scripts.

**Status:** Future Idea only. No implementation until a separate DD after bridge MVP.

### 6. Direct AI ↔ plugin communication (future — not implemented)

Today: user copies JSON between chat and Blender (clipboard / text block).

**Target architecture (conceptual):**

```
AI / Planning Client
        ↕  (structured ops, not raw bpy)
LayoutLab Agent or Bridge  (local)
        ↕  (limited API surface)
Blender Addon (layoutlab/)
        ↕
Blender Scene
```

**Bridge exposes only defined operations**, for example:

| Operation | Purpose |
|---|---|
| `get_scene` | Snapshot for planning |
| `list_generators` | Available assets |
| `get_generator_schema` | Params for a generator |
| `preview_operations` | Apply batch in undo group without commit |
| `analyze_preview` | Run DD-008 checks on preview state |
| `commit_preview` | Keep preview |
| `discard_preview` | Roll back undo group |

**Rejected as default bridge behaviour:** arbitrary remote Python execution.

Transport may evolve (HTTP localhost, MCP, stdio) — **semantic operations stay LayoutLab-defined**.

### 7. What the plugin guarantees (non-exhaustive)

The execution layer must remain deterministic and testable for:

- `layoutlab_object_id` stability across regenerate
- `layoutlab_params` merge policy
- Parts: main / static / dynamic, join-on-finalize (DD-006)
- Parenting without world/local drift
- Generator sync and version metadata
- Clearance creation and export (DD-007)
- Constraint findings (DD-008)
- Structured command results (errors, findings — evolving)

Clients depend on these guarantees; they must not be re-derived in AI prompts.

------------------------------------------------------------------------

## Alternatives considered

| Alternative | Why rejected as standard |
|---|---|
| **AI-only bpy, no plugin** | Non-reproducible; no shared test harness |
| **Plugin as thin JSON → bpy passthrough** | Loses semantic layer; same fragility as AI scripts |
| **All logic in prompts** | Not versioned; model-dependent |
| **Immediate bridge + remote exec** | Security and scope creep before core API stable |
| **Replace DD-003 with MCP only** | Transport can change; boundary decision is separate |

------------------------------------------------------------------------

## Consequences

- New features (clearances, constraints, parts) belong in **plugin/engine**, not prompt instructions.
- Documentation must state AI vs plugin roles explicitly (AI_CONTEXT, ARCHITECTURE, MDD).
- Expert mode and bridge require **future DDs** before code.
- DD-003 is **narrower** (JSON transport); DD-009 is the **strategic** boundary — both apply.

------------------------------------------------------------------------

## Relationship to other DDs

| DD | Relationship |
|---|---|
| DD-003 | How AI sends commands today (JSON). DD-009 explains *why* that layer exists. |
| DD-006 | Parts/parenting — plugin responsibility, not AI reimplementation. |
| DD-007/008 | Clearance/constraint logic — plugin + analyzer, AI interprets results. |

When bridge arrives, DD-003 may gain an amendment (“JSON or bridge RPC”) without changing DD-009’s boundary.

------------------------------------------------------------------------

## Open questions (for review)

### Security

1. **Bridge auth:** localhost-only token, OS user match, or Blender UI approval per session?
2. **Preview scope:** max objects / max commands per preview batch to limit DoS?
3. **Expert mode:** sandbox (restricted builtins), or full `bpy` with explicit user consent only?
4. **Logging:** where do preview/expert transcripts live (file, Blender text block, opt-in)?

### Architecture

5. **Bridge process model:** in-addon socket vs separate Python process vs MCP server?
6. **Schema discovery:** OpenAPI-style generator schemas auto-generated from docs or runtime introspection?
7. **Conflict resolution:** if Expert mode and API both modify scene — who wins?
8. **Offline / privacy:** must bridge work without cloud (default assumption: yes)?

### Product

9. **When is Expert mode worth it?** Only internal dev, or power users too?
10. **Does bridge replace clipboard** entirely, or coexist for manual debugging?

------------------------------------------------------------------------

## Recommended phase for Bridge (non-binding)

| Phase | Focus | Bridge? |
|---|---|---|
| Now – E.2 | Clearances + `analyze_layout` (DD-007/008) | **No** — finish deterministic core |
| E complete | Stable protocol: generate, regenerate, export, analyze | **Plan** bridge DD, schema inventory |
| Post-E / v0.9 | 3+ generators, diagnostics green, param schemas documented | **MVP bridge** — `get_scene`, `run_generator`, `analyze_layout`, undo group |
| v1.0+ | Preview → analyze → revise → commit workflow | **Full preview API** |
| Later | Expert mode | Separate DD + security review |

**Rationale:** Bridge adds value when **clipboard friction** hurts daily use **and** the operation set is stable enough to freeze. Building bridge before DD-008 `analyze_layout` would expose a moving target.

------------------------------------------------------------------------

## Document history

| Version | Date | Change |
|---|---|---|
| 0.1 | 2026-07-11 | Initial proposal — AI vs plugin boundary, hybrid future, bridge concept |
