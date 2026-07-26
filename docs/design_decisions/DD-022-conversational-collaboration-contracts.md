# DD-022 — Conversational Collaboration Contracts (FC-002/WP-01)

**Status:** Proposed  
**Date:** 2026-07-26  
**Version:** 0.1  
**Related:** [FC-002](../concepts/FC-002-conversational-design-collaboration-and-styling.md) · [DD-009](DD-009-ai-execution-boundary.md) · [DD-017](DD-017-collaborative-planning-and-contextual-evaluation.md) · [DD-018](DD-018-semantic-transactions-and-authority.md) · [DD-021](DD-021-advanced-support-surfaces.md) · [`agent_tool_contract.md`](../agent_tool_contract.md) · [ROADMAP](../ROADMAP.md)

------------------------------------------------------------------------

## Acceptance note

**Proposed 2026-07-26** for Alexander Accept. This DD is the FC-002/WP-01 architecture
package for boundaries that do not already belong to DD-017 / DD-018 / DD-021.

Narrow companion amendments (same Accept gate):

- [DD-018](DD-018-semantic-transactions-and-authority.md) §7 — change summaries
- [DD-017](DD-017-collaborative-planning-and-contextual-evaluation.md) — styling evidence boundary
- [DD-021](DD-021-advanced-support-surfaces.md) — decor placement helpers scope

Locked defaults proposed below. Binding field names land in `agent_tool_contract.md` /
`json_protocol.md` during WP-03…WP-06.

------------------------------------------------------------------------

## Decision summary (Proposed)

LayoutLab conversations are a **structured product surface**, not a free-form command
compiler. Core owns inspectable **semantic conversation state** and **revision change
summaries**. The AI may narrate and propose; it never invents project mutations or mesh
diffs. Styling reuses DD-017 evidence + Apply Gate and DD-021 horizontal supports.

------------------------------------------------------------------------

## Problem

FC-002 needs durable answers for:

1. when a turn may emit commands;
2. what “memory” is authoritative vs chat transcript;
3. how the AI sees manual edits since its last observation;
4. where decoration/styling stops being prompt heuristics and starts being Core contracts.

Without a DD, implementers risk parsing free text for mutations, treating the LLM
transcript as product state, reconstructing mesh diffs, or inventing a second aesthetics
channel beside DD-017.

------------------------------------------------------------------------

## Scope

### In scope

- Conversational turn / authority contract (product behaviour; WP-A already shipped)
- Semantic conversation state ownership, persistence tiers, preference provenance
- Change-summary authority (who produces structured ops; depth)
- Styling / decoration architecture boundary (pointers into DD-017 / DD-021)
- Resolution of FC-002 §16 open questions that are architectural (not WP-05 asset audit)

### Out of scope

- LLM routing polish (WP-02)
- Full state schema freeze and reference-resolution UX (WP-03)
- Implementing `summarize_changes` (WP-04)
- Decor generator audit and placement helpers code (WP-05)
- Styling candidate loop and eye-level camera poses (WP-06)
- Taste-profile learning product (WP-07)
- AI-03 Viewer trade-off copy (ROADMAP §5 Later)

------------------------------------------------------------------------

## Decision

### 1. Core statement

> **Conversation is structured. Core owns semantic collaboration state and semantic
> change summaries. Non-mutating turns never emit commands. Mutating turns remain
> proposals behind the Apply Gate. Styling is planning-like candidate work on DD-021
> supports, with DD-017 aesthetics only among viable results.**

### 2. Conversational turn and authority contract

Binding turn kinds (product set; protocol names in `agent_tool_contract.md`):

| Turn kind | Commands allowed? |
|---|---|
| `conversation`, `question`, `observation_request`, `feedback`, `clarification` | **No** |
| `planning_request`, `action_request` | **Yes** (proposal only) |
| `styling_request` | **No** until WP-06; then **Yes** as styling proposal (Apply Gate) |

Rules:

- Intent is inferred; the user does not pick a UI mode. Material ambiguity → short
  clarification, not a guessed mutation (WP-A behaviour remains binding).
- Structured agent results distinguish at least: `turn_kind`, `reply`, optional
  `proposal`, optional `open_question`, `observed_revision`.
- Free text must not be the sole authority for whether a mutation exists.
- DD-009 remains: AI plans WHAT; Core executes HOW. No-command outcomes are valid
  successful turns.

### 3. Semantic conversation state — ownership and tiers

| Tier | Owner | Examples | Persistence |
|---|---|---|---|
| **Project semantic state** | Core | explicit goal/requirements, accepted/rejected decisions user confirmed, explicit taste/style choices | Survives session when project persistence exists; until then same object, session-scoped |
| **Session collaboration state** | Core (`agent_state`) | `last_observed_revision`, last proposal meta, open questions, conversational focus / referents, inferred preferences | Session (and Undo snapshot when included) |
| **Provider context** | Provider / adapter | raw chat transcript | Ephemeral; **not** product authority |

Rules:

- Important conclusions must be represented in Core semantic state so they can be
  inspected, corrected and (when persistence exists) saved deliberately.
- Raw chat may inform a turn; it must not be required later to reconstruct decisions.
- `agent_state` schema evolves versioned (`schema` field); WP-03 expands fields for
  provenance, focus and preference labels without breaking WP-A keys.

### 4. Preference provenance

Every stored preference carries one of:

```text
explicit | inferred | project_default | turn_temporary
```

- `inferred` is labeled and must not silently become permanent personal facts.
- `turn_temporary` dies with the proposal/turn.
- Cross-project psychological profiling is a non-goal (FC-002 §12).
- Retaining inferred taste beyond the current project requires an **explicit** user
  action (WP-07); default is project/session only.

### 5. Reference resolution (architecture only)

Stable object/candidate IDs plus recent focus live in session collaboration state.
If more than one plausible referent exists, the AI asks; it does not guess. Concrete
focus-stack schema is WP-03.

### 6. Revision change summaries (authority)

Companion lock in DD-018 §7. Summary here:

- **Core** produces structured semantic change summaries from committed transaction
  `operations` between two revisions (domain ops, not mesh diffs).
- The AI may narrate those ops; it must not invent operations Core did not record.
- Depth equals the session Undo/history window (default ≥ 50). Outside that window,
  Core reports that history is unavailable — no mesh-diff fallback.
- Observation turns use summaries + analysis; they still emit **no** commands until an
  explicit `action_request` / accepted follow-up.

### 7. Decoration and styling boundary

| Concern | Binding home |
|---|---|
| Horizontal support geometry / validity | DD-021 |
| Functional + aesthetic evaluation channel | DD-017 |
| Decor capability / placement preference metadata | Generators + catalog profile (DD-005 / DD-017 object profiles); audited in WP-05 |
| Placement helpers (`list` surfaces, find positions, `place_on`) | Core extensions under DD-021; names not frozen here |
| Generic `arrange_on_surface` | **Not required** for MVP — candidate positions + `place_on` / batch commands suffice |
| Density budget | Soft collaboration/evaluation signal (WP-06); not a Core hard metric in WP-01 |
| Wall/ceiling mounts, physics | Still out of scope |
| Eye-level camera set | Principle: fixed, deterministic, room/focus-relative poses — **exact set in WP-06** |
| One accepted styling composition | One DD-018 transaction / one Undo unit |

`styling_request` before WP-06 remains acknowledgement-only (WP-A).

### 8. Schema ownership

| Concern | Owner |
|---|---|
| Authoritative project / revision / transactions | Core (DD-018) |
| Semantic collaboration / agent_state | Core |
| Binding tool + turn fields | `agent_tool_contract.md` at WP implementation |
| Product behaviour | FC-002 |
| Architectural locks in this package | **This DD** + DD-017/018/021 amendments |

------------------------------------------------------------------------

## Resolved FC-002 §16 questions

| Question | Decision |
|---|---|
| Which state is project / session / provider? | §3 tiers above |
| How much history for change summaries? | Undo/history window (≥ 50 default); else unavailable |
| Core vs adapter summaries? | **Core** structured ops; AI narrates |
| Safe first decor set? | WP-05 audit (not WP-01) |
| Need generic `arrange_on_surface`? | **No** for MVP |
| Eye-level cameras? | Deterministic fixed set; poses locked in WP-06 |
| Density representation? | Soft signal in collaboration/evaluation (WP-06) |
| Inferred taste beyond project? | Only after explicit user save (WP-07); default no |

------------------------------------------------------------------------

## Alternatives considered

| Alternative | Why rejected |
|---|---|
| Transcript as authoritative memory | Not inspectable/correctable; provider-coupled |
| Mesh-diff change understanding | Non-semantic; breaks regenerate / AI Apply story |
| Adapter-invented change summaries | Diverges from transaction truth |
| Monolithic “FC-002 mega-DD” restating 017/018/021 | FC-002 §13 forbids restating owned boundaries |
| New aesthetics channel for styling | Duplicate of DD-017; privacy/disclosure already defined |
| Require `arrange_on_surface` before any styling | Over-builds; `place_on` + candidates enough |

------------------------------------------------------------------------

## Consequences

**Positive**

- WP-02…WP-07 can implement without re-litigating authority.
- Manual-edit understanding has a deterministic Core source.
- Styling stays inside existing evaluation and support contracts.

**Trade-offs**

- `agent_state` and transaction history become product surfaces that need careful
  schema versioning.
- Change summaries cannot explain edits older than Undo history without a later
  persisted history DD.

**Follow-on**

- Accept → FC-002/WP-01 Done; Active moves to WP-02 (or next queued WP ready to start).
- WP-03…WP-06 implement contracts; no viewport-only collaboration truth.

------------------------------------------------------------------------

## Implementation order (after Accept)

1. Mark WP-01 Done on ROADMAP; keep Active theme = FC-002.
2. WP-02 routing polish against locked turn contract.
3. WP-03 expand `agent_state` (provenance, focus, preferences).
4. WP-04 Core `summarize_changes` (or equivalent) from transaction ops.
5. WP-05 decor metadata + placement helpers.
6. WP-06 styling loop + eye-level evidence set.
7. WP-07 taste profile only after WP-06 usage shows need.

------------------------------------------------------------------------

## History

| Ver | Date | Note |
|---|---|---|
| 0.1 | 2026-07-26 | Proposed — FC-002/WP-01 architecture package |
