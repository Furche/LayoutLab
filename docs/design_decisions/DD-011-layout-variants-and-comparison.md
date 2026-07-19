# DD-011 — Layout Variants and Comparison (Planning v1)

**Status:** Proposed  
**Date:** 2026-07-20  
**Related:** [DD-008](DD-008-constraints-and-layout-analysis.md) · [DD-009](DD-009-ai-execution-boundary.md) · [DD-015](DD-015-soft-metrics-and-tradeoffs.md) · [DD-016](DD-016-deterministic-layout-recipes.md) · [Future_Ideas.md](../Future_Ideas.md) §5 / §16 · [agent_tool_contract.md](../agent_tool_contract.md)

------------------------------------------------------------------------

## Problem

DD-016 shipped **Planning Layer v0**: `plan_layout` + `bedroom_basic` produce one deterministic command set. That fixed reliability (testable, often 0 hard errors), but collapsed two different concepts — and tied “recipe” too tightly to a **room type label**.

| Concept | What it should mean |
|---|---|
| **Recipe** | A **strategy for solving a room-planning problem** (goal + constraints + legal option space) — not one layout, and not merely “Schlafzimmer” |
| **Solution / candidate** | One concrete arrangement inside that strategy (locations, orientations, openings placement) |

Today `bedroom_basic` is effectively a single solution for one room type. Users experience nearly identical rooms. Symptom heuristics in the agent cannot invent diversity without inventing free geometry (violates DD-009).

If DD-011 only “makes bedroom_basic emit 3 bed walls,” it improves one generator. The real value of this DD is to lock the **Planner architecture** for every future strategy — room-type *and* goal-oriented.

Future_Ideas §5 / §16 already describe generate → score → explain. Soft metrics (DD-015) and analyze (DD-008) exist. Missing piece: a **Planner** that expands a recipe into candidates, evaluates them in Core, and selects.

------------------------------------------------------------------------

## Decision (Proposed)

### 1. Vocabulary (normative)

#### Recipe (core definition)

A **recipe** is a named, deterministic **planning strategy**: how Core explores solutions for a stated planning problem.

It answers: *Given requirements (and optional priorities), what legal moves exist, and how do we turn them into concrete layouts?*

A recipe includes (conceptually):

- **Goal / objective** — what “good” means for this strategy (may be room-use or quality-oriented)
- **Applicability** — when the agent/Core may select it (requirements.room_type, tags, priorities, …)
- **Option space** — finite axes the Planner may expand (wall affinities, furniture sets, circulation bias, …)
- **Hard rules** — what every candidate must obey (clearances, door strip, generator allowlist, …)
- **Evaluation bias** (optional) — which soft metrics weigh more under this strategy

A recipe does **not** equal one layout. Expanding it yields **candidates**; ranking yields a **selection**.

#### Recipe identity is goal-oriented, not room-type-only

Room types are **one common kind** of recipe family — not the definition of “recipe”:

| Kind | Examples (illustrative) |
|---|---|
| Room-use strategies | `bedroom_basic`, `kids_room`, `home_office`, `living_room` |
| Goal / quality strategies (later) | `maximize_play_area`, `accessible_layout`, `daylight_workspace`, `maximize_storage` |

Same physical room can be planned under different recipes (e.g. kids room + maximize play area). Requirements describe the **problem instance**; the recipe describes the **solution strategy**.

v0 name `bedroom_basic` remains valid as the first **room-use** recipe. DD-011 must not force all future recipes to be `*_room` labels.

#### Other terms

- **Candidate** — one complete, apply-ready `commands[]` plus metadata (`candidate_id`, strategy label within the recipe, analysis summary, soft summary, rank inputs).
- **Selection** — Core-chosen (or preference-biased) winning candidate for the proposal; must include a short **why** (human language from measured tradeoffs, not aesthetics).
- **Variant** (product sense, later) — first-class Spatial Project object for side-by-side UX / favourites (Future_Ideas §16). **Out of v1** — v1 candidates are ephemeral planning outputs, not persisted project variants.

### 2. Responsibility (extends DD-009 / DD-016)

| Concern | Owner |
|---|---|
| Intent / requirements / which strategy (“Schlafzimmer”, “mehr Spielfläche”) | AI (maps language → recipe id + requirements / priorities) |
| Expand recipe → finite candidate set | **LayoutLab Core (Planner)** |
| Analyze + soft metrics per candidate | LayoutLab Core (DD-008 / DD-015) |
| Rank / select default winner | **LayoutLab Core** (deterministic score from measurements + recipe evaluation bias) |
| Explain selection / optional override language | AI (may bias only via allowlisted preference keys + documented assumes) |
| Apply / consent | User |

> Recipe = **strategy** (solution space + goal).  
> Planner enumerates **candidates**.  
> Metrics **judge**.  
> Selection is the **planning act**.

AI does **not** invent candidate coordinates. AI chooses (or proposes) **which recipe** and **requirements/priorities**; Core owns expansion and default ranking.

### 3. Planning v1 scope (narrow implementation, wide architecture)

**Architecture lock (this DD):** Recipe = goal-oriented planning strategy; Planner = expand → evaluate → select for **any** recipe.

**Implementation v1 (first concrete slice):**

1. Refactor the existing `bedroom_basic` **room-use** recipe from “one layout” to a **candidate generator** with a small, fixed option matrix, e.g.:
   - bed wall: south \| north (and optionally west if the room is deep enough)
   - wardrobe / desk relative order on the opposite or adjacent wall
   - window count / sides still driven by requirements (unchanged)
2. New Core capability (tool or `plan_layout` mode):  
   `plan_layout` with `mode: "candidates"` **or** dedicated `plan_candidates`  
   → returns `{ recipe, candidates: [...], selected_id, selection_reason, score_breakdown }`  
   Default proposal `commands` = selected candidate.
3. Each candidate is dry-run / analyze evaluated on a **session clone** (same as today). Discard or demote candidates with hard errors / `solid_wall_penetration`.
4. Rank using **existing** soft metrics only (no aesthetic ML, no “73% nice”):
   - fewer hard errors ≫ everything
   - fewer `opening_access` warnings
   - prefer packing in a comfort band (not densest)
   - optional: free floor toward door (simple proxy from soft findings / sketch bounds)
5. Deterministic tie-break (stable sort key) so same recipe + requirements → same winner.
6. Agent: for intents that map to `bedroom_basic`, prefer candidate planning; put `selection_reason` into reply / `assumes`; free placement only for explicit custom overrides after a baseline.

**Out of v1 (but must remain expressible later without a new DD rewrite):**

- Additional room-use recipes (`kids_room`, `home_office`, …)
- Goal recipes (`maximize_play_area`, `accessible_layout`, `daylight_workspace`, …)
- Combining / stacking strategies (composition rules — future)
- Persisted multi-variant project model / compare UI (full §16)
- Infinite or LLM-sampled random layouts
- New soft metrics beyond DD-015 (amend DD-015 if needed)
- Apartment-scale variants

### 4. Candidate payload (sketch)

```json
{
  "ok": true,
  "recipe": "bedroom_basic",
  "recipe_kind": "room_use",
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

`recipe_kind` is optional metadata (`room_use` | `goal` | …) for agents and logs — not a second planner. Exact score component keys live in code + tests; this DD locks **intent**: measurable components only, biased by the recipe’s objective when present.

### 5. Relationship to DD-016

DD-016 remains valid for v0: a recipe **must** be able to emit at least one valid layout.  
DD-016’s `bedroom_basic` is the first recipe instance; DD-011 **generalizes** the recipe concept and makes expand → evaluate → select the primary planning path.  
Single-shot emission may remain as `mode: "single"` / internal helper used by the candidate generator.

### 6. What “best” means (v1)

“Best” = **best measured under DD-015 proxies + hard validity**, optionally weighted by the recipe’s stated objective — not taste.  
If two candidates tie on metrics, pick the stable default strategy (document in `assumes`).  
User/AI priority overrides (e.g. `prefer_bed_wall: "north"`) force that family of candidates to the front **before** soft ranking among the remaining set.

------------------------------------------------------------------------

## Alternatives considered

| Option | Why not (for v1) |
|---|---|
| Keep one layout; ask LLM to “vary” xy | Undoes DD-016; untestable |
| Define recipe = room type forever | Blocks goal strategies; forces parallel architecture later |
| Only LLM picks among hand-written JSON templates | Duplicates Core; weak spatial judgment |
| Full Spatial Project variants + compare UI first | Large product surface; blocks planner learning |
| Continuous optimization / ILP solver | Premature; need discrete candidates + metrics first |
| Aesthetic or embedding-based score | Violates DD-015 (“no 73% good layout”) |

------------------------------------------------------------------------

## Consequences

- This DD is the **foundation for the Planner architecture**, not a bedroom-only feature.
- `agent_tools` bumps when the candidates API ships (likely 0.6).
- Diversity under a recipe becomes a **Core** property (option matrix + rank), not chat luck.
- Tests (v1): for fixed recipe + requirements, candidate set size ≥ 2; selected candidate has 0 hard errors on reference rooms; ranking is stable across runs.
- Later recipes (room-use or goal) plug into the same expand → evaluate → select contract.
- Viewer: v1 can keep showing one proposal; optional later “show alternatives” is §16 / product work.
- DD-016 docs should cross-link: recipe ≠ room type ≠ single solution once this is Accepted.

------------------------------------------------------------------------

## Implementation order (after Accept)

1. Document recipe registry metadata (id, kind, goal tags, applicability) — even if only `bedroom_basic` exists (`kind: "room_use"`, e.g. `goals: ["sleep","storage"]`). Do **not** rename `bedroom_basic`.
2. Factor `bedroom_basic` into shared placement primitives + option matrix → N candidates (commands only, no analyze yet).
3. Evaluate each on session clone; attach quality / soft_summary.
4. Deterministic rank + `selection_reason` strings (German templates OK).
5. Expose via tool (`plan_layout` mode or `plan_candidates`); wire agent + baseline.
6. Tests + session-log: different strategies appear when metrics differ; identical inputs → identical winner.
7. Later: more recipes (room-use and/or goal) on the same contract; persist variants / compare UI (Future_Ideas §16) — separate product slice.

------------------------------------------------------------------------

## Open questions (review)

1. **API shape:** extend `plan_layout` with `mode: "candidates"` vs new tool `plan_candidates`?
2. **How many candidates in v1?** Proposed default: 2–4 strategies per recipe call (not dozens).
3. **May the AI override Core selection?** Proposed: only via allowlisted preference keys on requirements; no free re-pick of coordinates. Recipe **choice** remains an AI/requirements concern.
4. **Return all candidates to the Viewer in v1?** Proposed: no — selected only in `proposal.commands`; full list in tool result / log for debugging.
5. **Recipe naming:** ~~keep `bedroom_basic` vs goal alias?~~ → **Resolved:** keep id `bedroom_basic`; add registry metadata tags (e.g. `goals: ["sleep","storage"]`, `kind: "room_use"`). Goal-oriented recipes later get their own ids (`maximize_play_area`, …), not renames of room-use recipes.

------------------------------------------------------------------------

## Acceptance

- [ ] Alexander Accept / Reject / Request changes

------------------------------------------------------------------------

## History

| Ver | Date | Note |
|---|---|---|
| 0.1 | 2026-07-20 | Proposed — recipe = solution space; Planner = expand → evaluate → select |
| 0.2 | 2026-07-20 | Recipe = goal-oriented planning strategy (not room-type-only); v1 still starts at `bedroom_basic` |
