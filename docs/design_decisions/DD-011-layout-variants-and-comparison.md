# DD-011 — Layout Variants and Comparison (Planning v1)

**Status:** Proposed  
**Date:** 2026-07-20  
**Related:** [DD-008](DD-008-constraints-and-layout-analysis.md) · [DD-009](DD-009-ai-execution-boundary.md) · [DD-015](DD-015-soft-metrics-and-tradeoffs.md) · [DD-016](DD-016-deterministic-layout-recipes.md) · [Future_Ideas.md](../Future_Ideas.md) §5 / §16 · [agent_tool_contract.md](../agent_tool_contract.md)

------------------------------------------------------------------------

## Problem

DD-016 shipped **Planning Layer v0**: `plan_layout` + `bedroom_basic` produce one deterministic command set. That fixed reliability (testable, often 0 hard errors), but collapsed two different concepts:

| Concept | What it should mean |
|---|---|
| **Recipe** | Description of a **solution space** (furniture set, wall affinities, clearance rules, allowed options) |
| **Solution / candidate** | One concrete arrangement (locations, `head_side`, openings placement) |

Today `bedroom_basic` is effectively a single solution. Users experience nearly identical rooms. Symptom heuristics in the agent cannot invent diversity without inventing free geometry (violates DD-009).

Future_Ideas §5 / §16 already describe generate → score → explain. Soft metrics (DD-015) and analyze (DD-008) exist. Missing piece: a **Planner** that expands a recipe into candidates, evaluates them in Core, and selects.

------------------------------------------------------------------------

## Decision (Proposed)

### 1. Vocabulary (normative)

- **Recipe** — named planning strategy + parameter space (e.g. `bedroom_basic`). Does **not** equal one layout.
- **Candidate** — one complete, apply-ready `commands[]` plus metadata (`candidate_id`, strategy label, analysis summary, soft summary, rank inputs).
- **Selection** — Core-chosen (or AI-overridden) winning candidate for the proposal; must include a short **why** (human language from measured tradeoffs, not aesthetics).
- **Variant** (product sense, later) — first-class Spatial Project object for side-by-side UX / favourites (Future_Ideas §16). **Out of v1** — v1 candidates are ephemeral planning outputs, not persisted project variants.

### 2. Responsibility (extends DD-009 / DD-016)

| Concern | Owner |
|---|---|
| Intent / requirements / priorities (“mehr Licht”, “Bett an Fenster”) | AI |
| Expand recipe → finite candidate set | **LayoutLab Core (Planner)** |
| Analyze + soft metrics per candidate | LayoutLab Core (DD-008 / DD-015) |
| Rank / select default winner | **LayoutLab Core** (deterministic score from measurements) |
| Explain selection / optional override language | AI (may re-rank only with explicit user priority + documented assumes) |
| Apply / consent | User |

> Recipe defines the **space of legal moves**.  
> Planner enumerates **candidates**.  
> Metrics **judge**.  
> Selection is the **planning act**.

AI does **not** invent candidate coordinates. AI may pass priorities that bias ranking (v1: small allowlisted preference keys).

### 3. Planning v1 scope (narrow)

**In:**

1. Extend `bedroom_basic` from “one layout” to a **candidate generator** with a small, fixed option matrix, e.g.:
   - bed wall: south \| north (and optionally west if room is deep enough)
   - wardrobe / desk relative order on the opposite or adjacent wall
   - window count / sides still driven by requirements (unchanged)
2. New Core capability (tool or `plan_layout` mode):  
   `plan_layout` with `mode: "candidates"` **or** dedicated `plan_candidates`  
   → returns `{ candidates: [...], selected_id, selection_reason, score_breakdown }`  
   Default proposal `commands` = selected candidate.
3. Each candidate is dry-run / analyze evaluated on a **session clone** (same as today). Discard or demote candidates with hard errors / `solid_wall_penetration`.
4. Rank using **existing** soft metrics only (no aesthetic ML, no “73% nice”):
   - fewer hard errors ≫ everything
   - fewer `opening_access` warnings
   - prefer packing in a comfort band (not densest)
   - optional: free floor toward door (simple proxy from soft findings / sketch bounds)
5. Deterministic tie-break (stable sort key) so same requirements → same winner.
6. Agent: prefer candidate planning for bedroom intents; put `selection_reason` into reply / `assumes`; still allow free placement only for explicit custom overrides after a baseline.

**Out of v1:**

- Persisted multi-variant project model / compare UI (full §16)
- Infinite or LLM-sampled random layouts
- New soft metrics beyond DD-015 (may add later via DD-015 amendment)
- Non-bedroom recipes
- Apartment-scale variants

### 4. Candidate payload (sketch)

```json
{
  "ok": true,
  "recipe": "bedroom_basic",
  "requirements": { "...": "..." },
  "candidates": [
    {
      "candidate_id": "bed_south__storage_north",
      "strategy": "bed on south; wardrobe+desk on north",
      "commands": [],
      "quality": {
        "has_hard_errors": false,
        "soft_summary": {},
        "summary": {}
      },
      "score": { "rank": 1, "components": {} }
    }
  ],
  "selected_id": "bed_south__storage_north",
  "selection_reason": "Keine Hard Errors; bessere Tür-/Fensterfreiheit als bed_north.",
  "commands": []
}
```

Exact score component keys live in code + tests; this DD locks **intent**: measurable components only.

### 5. Relationship to DD-016

DD-016 remains valid for v0: a recipe **must** be able to emit at least one valid layout.  
DD-011 **refines** recipes: the primary `plan_layout` path for bedrooms becomes expand → evaluate → select.  
Single-shot `bedroom_basic` (one layout) may remain as `mode: "single"` / internal helper used by the candidate generator.

### 6. What “best” means (v1)

“Best” = **best measured under DD-015 proxies + hard validity**, not taste.  
If two candidates tie on metrics, pick the stable default strategy (document in `assumes`).  
User/AI priority overrides (e.g. `prefer_bed_wall: "north"`) force that family of candidates to the front **before** soft ranking among the remaining set.

------------------------------------------------------------------------

## Alternatives considered

| Option | Why not (for v1) |
|---|---|
| Keep one layout; ask LLM to “vary” xy | Undoes DD-016; untestable |
| Only LLM picks among hand-written JSON templates | Duplicates Core; weak spatial judgment |
| Full Spatial Project variants + compare UI first | Large product surface; blocks planner learning |
| Continuous optimization / ILP solver | Premature; need discrete candidates + metrics first |
| Aesthetic or embedding-based score | Violates DD-015 (“no 73% good layout”) |

------------------------------------------------------------------------

## Consequences

- `agent_tools` bumps when the candidates API ships (likely 0.6).
- Bedroom diversity becomes a **Core** property (option matrix), not chat luck.
- Tests: for fixed requirements, candidate set size ≥ 2; selected candidate has 0 hard errors on reference rooms; ranking is stable across runs.
- Viewer: v1 can keep showing one proposal; optional later “show alternatives” is §16 / product work.
- DD-016 docs should cross-link: recipe ≠ single solution once this is Accepted.

------------------------------------------------------------------------

## Implementation order (after Accept)

1. Factor `bedroom_basic` into shared placement primitives + option matrix → N candidates (commands only, no analyze yet).
2. Evaluate each on session clone; attach quality / soft_summary.
3. Deterministic rank + `selection_reason` strings (German templates OK).
4. Expose via tool (`plan_layout` mode or `plan_candidates`); wire agent + baseline.
5. Tests + session-log: different strategies appear when metrics differ; identical requirements → identical winner.
6. Later: persist variants / compare UI (Future_Ideas §16 product slice) — separate accept if scope grows.

------------------------------------------------------------------------

## Open questions (review)

1. **API shape:** extend `plan_layout` with `mode: "candidates"` vs new tool `plan_candidates`?
2. **How many candidates in v1?** Proposed default: 2–4 bedroom strategies (not dozens).
3. **May the AI override Core selection?** Proposed: only via allowlisted preference keys on requirements; no free re-pick of coordinates.
4. **Return all candidates to the Viewer in v1?** Proposed: no — selected only in `proposal.commands`; full list in tool result / log for debugging.

------------------------------------------------------------------------

## Acceptance

- [ ] Alexander Accept / Reject / Request changes

------------------------------------------------------------------------

## History

| Ver | Date | Note |
|---|---|---|
| 0.1 | 2026-07-20 | Proposed — recipe = solution space; Planner = expand → evaluate → select |
