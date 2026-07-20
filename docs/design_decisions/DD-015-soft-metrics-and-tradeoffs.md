# DD-015 — Soft Metrics and Rule Tradeoffs (AI ↔ LayoutLab)

**Status:** Accepted  
**Date:** 2026-07-18  
**Accepted:** 2026-07-20  
**Related:** [DD-007](DD-007-clearance-zones.md) · [DD-008](DD-008-constraints-and-layout-analysis.md) · [DD-009](DD-009-ai-execution-boundary.md) · [DD-017](DD-017-collaborative-planning-and-contextual-evaluation.md) · [agent_tool_contract.md](../agent_tool_contract.md)

------------------------------------------------------------------------

## Decision summary (Accepted)

Locks the split: **Core measures** soft usability proxies + non-negotiable solid collisions; **AI chooses/explains** tradeoffs via `expected_risks`; **User consents** on Apply. v1 does not server-block Apply on soft/hard findings (Viewer warns; `solid_wall_penetration` blocks Apply in the Viewer).

Shipped: `soft_packing`, `opening_access`, `solid_wall_penetration`; dry-run `soft_summary`; agent `quality` preview; Viewer confirm UX.

### Amendment — 2026-07-21 (DD-017 Accepted)

“No aesthetics score” remains binding for **deterministic Core metrics**. DD-017 adds a separate,
optional, probabilistic AI-aesthetics channel only after validity and functional shortlisting. It
cannot compensate for invalidity, unwaived severe-veto findings, or materially worse functional
quality. The Core continues to own measurable findings and signed/context-weighted score components;
the AI channel owns rubric-based visual comparison, confidence, provenance, and explanation.

Existing v1 soft metrics and Apply behavior remain unchanged until the DD-017 evaluation schema is
implemented. Signed components, veto thresholds, and functional-equivalence bands require their
versioned implementation contract rather than ad-hoc prompt values.

------------------------------------------------------------------------

## Problem

Clearance analysis (DD-008) answers *zone blocked?* but not *does this room feel usable?*  
The agent often packs furniture like a warehouse. Users need soft, measurable quality signals, and the AI must be allowed to **bend hard rules** when a compromise is in the user’s interest — with transparency, not silent violation.

## Decision

### 1. Responsibility

| Layer | Owner | Role |
|---|---|---|
| Hard validity | LayoutLab | Allowlist, params, execution |
| Hard spatial | LayoutLab | `required` clearances → `error` findings |
| Soft measurable | LayoutLab | Soft metrics → `warning` / `info` findings |
| Judgment / tradeoffs | AI | Choose layout, explain compromises |
| Consent | User | Apply (waiver by applying with documented risks) |

> LayoutLab **measures and reports**. The AI **chooses and explains**. The User **confirms**.

### 2. Soft metrics (v1)

Emitted by headless `analyze_layout` / `analyze_session` alongside clearance findings:

| `constraint_type` | Meaning | Typical severity |
|---|---|---|
| `soft_packing` | Furniture XY footprint / room footprint | info ≥ 0.35, warning ≥ 0.48 |
| `opening_access` | Inward access box in front of door/window overlaps furniture | warning |
| `solid_wall_penetration` | Furniture AABB intersects wall solid (openings cut out) | **error, non-negotiable** |

`solid_wall_penetration` is **physically invalid**, not a tradeoff — AI must replan; Viewer blocks Apply (`quality.blocks_apply`).

No aesthetics score. No “73% good layout.”

### 3. Rule bending (tradeoffs)

- Hard findings **remain** findings; Core does **not** auto-clear them.
- AI may propose a layout that still has hard errors when the user goal otherwise fails.
- Proposal **must** then fill `expected_risks` (and preferably `assumes`) in human language.
- **v1 Apply:** Core does not block Apply. Viewer warns when `expected_risks` or dry-run/quality errors exist; user Apply = consent.
- Future: optional server `accept_risks` gate.

### 4. Agent behaviour

1. Prefer replan on soft warnings.  
2. On hard errors: try alternatives first.  
3. If compromise needed: explain tradeoff, set `expected_risks`, leave Apply to the user.  
4. Never claim a hard violation is “OK” without stating the cost.

## Alternatives considered

- **Core blocks Apply on any error** — rejected for v1; prevents necessary compromises.  
- **AI-only soft heuristics in prompt** — rejected as sole approach; not testable/deterministic.  
- **Aesthetic ML score** — out of scope.

## Consequences

- Analysis payload grows with soft findings; exporters/viewers should tolerate unknown `constraint_type`.  
- Agent contract and system prompt must require `expected_risks` on hard compromise.  
- Soft metrics are **proxies** for comfort/usability, not a substitute for user taste.

## Implementation notes

- Soft analysis lives in headless path first (`layoutlab/runtime` + `layoutlab/core`).  
- `dry_run_commands` returns `soft_summary` plus slim findings.  
- Agent turn may attach a `quality` preview from an automatic dry-run of the final proposal.

------------------------------------------------------------------------

## History

| Ver | Date | Note |
|---|---|---|
| 0.1 | 2026-07-18 | Proposed |
| 1.0 | 2026-07-20 | **Accepted** — soft metrics + tradeoff contract locked; shipped in Core/Viewer |
