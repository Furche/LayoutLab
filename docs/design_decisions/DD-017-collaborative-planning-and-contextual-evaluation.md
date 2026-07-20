# DD-017 — Collaborative Planning and Contextual Candidate Evaluation

**Status:** Accepted

**Date:** 2026-07-21

**Accepted:** 2026-07-21

**Related:** [DD-008](DD-008-constraints-and-layout-analysis.md) · [DD-009](DD-009-ai-execution-boundary.md) · [DD-011](DD-011-layout-variants-and-comparison.md) · [DD-015](DD-015-soft-metrics-and-tradeoffs.md) · [DD-016](DD-016-deterministic-layout-recipes.md)

------------------------------------------------------------------------

## Decision summary (Accepted)

LayoutLab should plan through an **internal collaboration loop** between AI and Core:

1. The user states goals, needs, and preferences.
2. The AI turns them into structured requirements and chooses search strategies.
3. The AI requests candidates through allowlisted semantic intentions; Core recipes and
   placement tools resolve those intentions into concrete geometry.
4. LayoutLab executes candidates on isolated session clones, validates geometry, and
   returns deterministic findings and score components.
5. Core returns a functional shortlist; the AI may revise weak candidates through the same
   semantic interface and assess aesthetics only on the viable shortlist.
6. The AI recommends and explains; the user compares, adjusts, and makes the final selection.

Candidate quality is evaluated in ordered stages:

1. **Validity** — non-compensable physical and safety failures.
2. **Functional penalties and preferences** — signed, explainable Core scores.
3. **Context weighting** — object role × room use × user priority.
4. **Aesthetic assessment** — structured AI judgment for already viable candidates.

Furniture preferences must survive generation. They therefore belong to semantic object
profiles and instances, **not only to generator implementation code**.

This decision locks the target planning and evaluation contract. Implementation remains staged:
DD-011 candidate expansion may continue, while new profile/role schemas, signed scoring,
selection changes, and AI aesthetics follow the implementation order below.

------------------------------------------------------------------------

## Problem

The current flow can expose a failed one-shot proposal:

```text
User request
    ↓
AI returns commands
    ↓
LayoutLab validates once
    ↓
Invalid result is shown; user must ask again
```

This has three distinct weaknesses.

### 1. Invalid attempts leak into the user experience

Furniture may penetrate walls, overlap other furniture, block doors, or completely block a
wardrobe's required operating space. Validation detects some of these problems, but too late:
the user receives a failure instead of a useful negotiated result.

### 2. LayoutLab can reject, but cannot yet express enough about quality

Two collision-free arrangements are not equally useful. A bed usually prefers its head end
against a wall and benefits from accessible sides. A wardrobe needs opening and standing
space. A desk benefits from chair space and often from daylight. These are not all hard
constraints, and their importance changes with use.

### 3. Functional validity does not equal visual quality

A room can satisfy every measurable clearance and still look accidental, crowded, or
unbalanced. DD-015 deliberately excludes aesthetics from deterministic Core metrics. That
boundary remains useful, but leaves a final comparison dimension unresolved.

------------------------------------------------------------------------

## Decision

### 1. Planning is a collaboration, not a one-shot command handoff

LayoutLab planning has three external participants and two internal planning capabilities:

| Participant / capability | Responsibility |
|---|---|
| **User** | States goals, constraints, taste, and acceptable compromises; approves Apply |
| **AI** | Understands intent, assigns semantic roles, chooses strategies, iterates, compares, explains |
| **Core recipes / placement tools** | Deterministically expand known strategies and resolve semantic placement intentions into geometry |
| **Core execution + analysis** | Applies candidates on clones, validates, measures, scores deterministic components |
| **Viewer** | Shows progress, candidates, tradeoffs, and explicit Apply/Discard controls |

The term **Planner** describes the complete collaboration capability, not a single module. It
must not silently become either a monolithic Core solver or unrestricted LLM coordinate invention.

- For known problems, Core recipes may enumerate bounded candidates as accepted in DD-011.
- The AI may steer search, request alternatives, combine allowlisted preferences, and revise
  semantic intentions based on Core feedback.
- Free, raw coordinates remain an explicit custom override rather than the default planning
  language.
- Core remains authoritative for geometry, validity, deterministic metrics, and mutation.

Selection is layered:

1. Core rejects invalid candidates and produces a deterministic **functional shortlist**.
2. The AI may revise candidates only through allowlisted semantic intentions.
3. The AI compares aesthetics within the viable shortlist and recommends an option.
4. The user makes the final selection and controls Apply.

DD-011's deterministic Core winner remains the valid v1 fallback until DD-017 is accepted and
DD-011 is explicitly amended. DD-017 describes the intended target architecture.

This extends DD-009 without weakening it: AI decides **what to try and why**; Core decides
**how it is represented, whether it is physically valid, and what measurable consequences it has**.

#### Semantic intention language

A candidate intention is a structured request from a versioned allowlist. Initial categories may
include:

- recipe id, candidate mode, and recipe options
- allowlisted preference keys and priorities
- allowlisted role assignment
- placement by semantic anchor or relation (`head_against_wall`, `near_window`, `keep_access`)
- regenerate or move through Core-owned placement operations

Raw `location[]` coordinates are not the default planning language. They remain available only as
an explicit, documented custom override, with the same dry-run and validation requirements.
The override must be labeled in structured state and surfaced through `assumes` and, when it
introduces a known compromise, `expected_risks`.
Unknown intentions, preference keys, or roles must fail clearly rather than becoming silent no-ops.

### 2. Internal negotiation loop

The target flow is:

```text
User intent
    ↓
AI derives requirements, roles, priorities, and open questions
    ↓
AI requests candidate intention through allowlisted semantic operations
    ↓
Core dry-runs candidate on an isolated clone
    ↓
Core returns validity + findings + deterministic score breakdown
    ↓
AI accepts, revises, or tries another candidate
    ↓
Core returns a functional shortlist with category vectors and score breakdowns
    ↓
AI optionally revises within the allowlist, compares shortlist aesthetics, and recommends
    ↓
User sees viable options and decides
```

The loop is bounded. Proposed interactive defaults are at most four candidates, at most two
revision rounds after initial evaluation, and a configurable wall-clock timeout. Recipes or batch
workflows may declare different budgets explicitly. If no viable result is found, the AI must
explain the limiting requirements or ask a focused question.
It must not claim success or surface a raw command error as the final answer.

The UI may show concise activity (“Prüfe Laufwege”, “Vergleiche drei Varianten”), but must not
expose hidden chain-of-thought or require the user to interpret internal tool transcripts.

Internally rejected or invalid candidates must never populate `proposal.commands`. A proposal may
contain only a member of the Core functional shortlist or an explicit user selection from that
shortlist; severe compromises additionally require the documented waiver path.

### 3. Candidate contract

A candidate is a proposal, not a duplicated scene:

```text
Candidate =
    commands / semantic operations
  + requirements and assumptions
  + object roles
  + validity and findings
  + deterministic score breakdown
  + optional aesthetic assessment
  + provenance and confidence
```

Illustrative payload:

```json
{
  "candidate_id": "bed_south__storage_north",
  "commands": [],
  "roles": {
    "bed_01": "primary_sleeping_place",
    "desk_01": "secondary_workspace"
  },
  "evaluation": {
    "valid": true,
    "blocking_findings": [],
    "functional": {
      "total": 42,
      "components": []
    },
    "aesthetic": {
      "confidence": 0.72,
      "rubric": {
        "visual_balance": 0.8,
        "composition_clarity": 0.7,
        "perceived_clutter": 0.3
      },
      "derived_sort_key": 0.76
    }
  }
}
```

Exact schemas and numeric ranges require a later implementation contract. The rubric vector is
primary; `derived_sort_key` is an optional probabilistic sorting aid, never an objective quality
claim. Every result remains explainable; a bare “87% good” score is insufficient.

### 4. Furniture preference knowledge

An object type may describe general placement preferences without naming absolute room sides.

Example `bed` profile:

- head end prefers contact with a wall
- two or more accessible entry sides are preferred
- one accessible side is usable but penalized
- avoid blocking openings or circulation

Example `wardrobe` profile:

- back prefers a wall
- door/drawer movement volume must remain usable
- standing access in front is important

Example `desk` profile:

- chair access is important
- daylight may be preferred
- task surface should remain unobstructed

These preferences must **not live only inside generator code**, because LayoutLab must also
evaluate objects after regeneration, manual movement, import, or future catalog placement.

Proposed ownership split:

| Layer | Owns |
|---|---|
| Object-type profile / catalog | Default capabilities, anchors, functional zones, preference rules |
| Generator | Geometry and semantic parts; stamps profile id + supported anchors/zones |
| Object instance | Stable type/profile id, role, parameters, instance overrides |
| Room context | Intended room use and room-level priorities |
| User requirements | Personal priorities and explicit waivers |
| Evaluation engine | Resolves rules, weights context, emits findings and score components |

Generators may seed metadata, but they are not the only source of evaluation knowledge.
At minimum, a durable object instance retains `type`, `profile_id`, allowlisted `role`, generator
parameters, and explicit instance overrides. Capabilities and default preferences remain versioned
in the referenced profile rather than copied into every instance.

Imported or catalog furniture should map to a profile by explicit type/catalog metadata first,
then reviewed type/name matching, and finally manual assignment. Unresolved objects receive an
`unknown` profile: they may participate in collision analysis, but receive no invented semantic
preference score until classified.

### 5. Capabilities, roles, and context

**Capability** describes what an object provides or requires regardless of room context: sleeping
capacity, openable doors, supported entry sides, chair access, storage, or a usable work surface.

**Role** describes why that capability matters in this planning problem: primary sleeping place,
guest sleeping place, primary dining place, secondary workspace, and so on.

Object type alone is insufficient. The same furniture can perform different roles:

```yaml
type: sofa_bed
role: guest_sleeping_place
room_use: living_room
```

versus:

```yaml
type: bed
role: primary_sleeping_place
room_use: bedroom
```

Likewise, a table may be a primary dining place, a kitchen work surface, or a secondary
occasional seat. Rules may remain stable while their importance changes.

Effective weight is conceptually derived from:

```text
rule base weight
× object-role importance
× room-use relevance
× user priority
```

Roles used by Core scoring come from a small, versioned allowlist. The AI may infer an allowlisted
role from conversation, but it must store the assignment in structured state so Core scoring does
not depend on prose or hidden model context. Unknown high-impact roles (especially a room's primary
function) require clarification before recommendation. Low-impact or still-unclassified objects may
use a visible neutral fallback after clarification is attempted. Unknown roles never silently create
a new scoring key.

### 6. Ordered evaluation model

Evaluation uses ordered gates. Later stages cannot compensate for failure at an earlier gate.

| State | Meaning |
|---|---|
| **Invalid** | Non-compensable physical/safety failure; reject or revise |
| **Valid with severe penalty** | Usable only with a major compromise; never top recommendation without explicit waiver |
| **Valid but suboptimal** | Works, but violates one or more ordinary preferences |
| **Preferred** | Strong deterministic functional/context result |
| **Aesthetically preferred** | AI preference among functionally comparable viable candidates |
| **User-approved compromise** | User knowingly accepts documented severe penalties via Apply |

#### Stage A — Validity (non-compensable)

Examples:

- solid furniture penetrates a wall
- furniture intersects another solid object beyond allowed contact
- a required room door cannot operate
- a mandatory safety clearance is violated
- an object is outside the valid room footprint

An invalid candidate is rejected or revised. It does not become acceptable because it looks good.

Initial classification principle:

| Always invalid (KO) | Severe but potentially waivable |
|---|---|
| Wall penetration or object outside room footprint | Wardrobe access substantially reduced but still usable |
| Disallowed solid-solid intersection | Only one bed entry side accessible |
| Required room door cannot operate | Poor standing or circulation comfort |
| Mandatory safety/required clearance fails | Awkward residual space or weak daylight relation |
| An object's required operating part is completely blocked | Partial opening/access reduction explicitly modeled as waivable |

For example, a completely blocked wardrobe door is invalid when the modeled required operating
clearance cannot function. Reduced opening angle or inconvenient standing space may be a severe,
waivable functional penalty. Classification is explicit per rule and linked to DD-008 severity;
it is never inferred only from a final numeric total.

By default, a failed DD-008 `required` clearance maps to Stage A invalidity. A failed `preferred`
clearance maps to Stage B and may become ordinary or severe depending on its declared rule severity.
Any exception to this mapping must be explicit and versioned.

#### Stage B — Functional penalties and preferences

Valid candidates receive signed, explainable components. Negative values are intentional:
one severe defect can outweigh several minor advantages.

Illustrative components:

```text
bed head against wall                  +20
two accessible bed sides              +15
only one accessible bed side          -25
wardrobe access substantially reduced -60
desk benefits from daylight            +8
awkward unusable residual space        -10
```

Scores begin from a neutral baseline. Positive and negative contributions are reported rather
than hidden inside stars. The Core must also expose category vectors (for example circulation,
accessibility, comfort, object usability) so a single total does not erase tradeoffs.

Anti-compensation is mandatory. Evaluation v1 must define severity bands and veto thresholds:
a severe component cannot be hidden by accumulating many minor benefits. A candidate crossing a
severe-veto threshold is excluded from the default top recommendation unless the risk is explicitly
documented in `expected_risks` and accepted by the user. Positive contribution caps or category
dominance rules may supplement this. The total score remains a sorting aid, never the sole verdict.

#### Stage C — Context weighting

Stage B components are weighted by role, room use, and user priority. A poor primary bed in a
bedroom matters more than an imperfect occasional sleep function in a living room. A dining table
is central in a dining room but may be secondary in a kitchen.

Weights influence ranking among viable candidates. They must not downgrade physical validity.

#### Stage D — Aesthetic assessment

Only viable candidates reach aesthetic evaluation. The AI assesses visual composition through a
fixed, structured rubric rather than an unexplained taste score.

Initial rubric candidates:

- visual balance
- composition clarity
- spacing rhythm
- visual hierarchy
- perceived clutter
- quality of residual spaces
- coherence with the requested style

The assessment should include:

- component values
- concise reasons grounded in visible evidence
- confidence
- requested style context
- comparison set / evaluation version

Comparative assessment of candidates under identical presentation conditions is preferred over
isolated absolute scores.

AI aesthetics is experimental and optional in its first implementation. The rubric vector is the
primary result; any combined value is derived and labeled probabilistic. The provider/model,
rubric version, style context, and confidence must be recorded.

### 7. Standardized visual evidence for aesthetics

Aesthetic assessment requires visual evidence, not object names alone. Candidate renders should use:

- identical top-down camera and scale
- identical interior viewpoints and focal lengths
- neutral materials and controlled lighting for layout comparison
- consistent visibility of walls/openings
- optional styled render only when style itself is under evaluation

The system must distinguish **layout aesthetics** from rendering quality. Otherwise lighting,
materials, or camera choice may dominate the score.

AI aesthetics is an opinionated, probabilistic signal. It must be labeled accordingly, carry
confidence, and never be presented as an objective building-code or usability verdict.

Visual evaluation may send room images to a configured model provider. The product must disclose
that transfer, avoid logging images or style prompts by default, respect provider-independent and
local-model paths, and make the feature opt-in where privacy or cost requires it.

An aesthetic result is cacheable when the standardized evidence hash, candidate geometry revision,
model/provider version, rubric version, and style context are identical. Cache reuse must preserve
the original confidence and provenance rather than presenting the result as a fresh evaluation.

### 8. Ranking and selection

Recommended selection order:

1. Reject invalid candidates.
2. Prefer candidates without severe functional penalties.
3. Core ranks deterministic functional/context scores and returns a shortlist (top-k or Pareto set).
4. Optional AI aesthetics may reorder only functionally comparable candidates within a documented
   equivalence band; it cannot promote a materially worse functional candidate.
5. The AI recommends and explains meaningful alternatives; the user selects and controls Apply.

**Functional equivalence band:** candidates are comparable for aesthetic reordering only when they
share the same validity state, have no difference in unwaived severe-veto findings, and lie within a
documented functional band or the same relevant Pareto front across category vectors. The exact
numeric band and Pareto/top-k algorithm belong to the versioned evaluation schema; the principle
does not. Aesthetic preference cannot cross this boundary.

Aesthetics is deliberately the last variable. It cannot “beautify away” a blocked door, wall
penetration, or mandatory clearance failure.

The final ranking may use a composite for sorting, but the product must preserve the underlying
validity state, category vector, signed components, aesthetic rubric, and confidence.

Candidates carrying severe waivable penalties must populate `expected_risks`; existing Viewer
warning and Apply consent behavior from DD-015 remains in force. Invalid candidates remain blocked
and are not offered as ordinary selectable variants.

### 9. User-facing contract

The user should experience a competent negotiation, not trial-and-error command execution:

```text
User: “Ich möchte ein kleines Schlafzimmer mit zwei Fenstern und Möbeln.”

AI (internal): derives requirements and asks Core for candidates.
Core (internal): Candidate A blocks wardrobe access; Candidate B is valid but cramped;
                 Candidate C is valid and scores better for circulation.
AI (internal): requests one refinement of Candidate C and compares aesthetics.

AI → User: “Ich habe drei Anordnungen geprüft. Zwei waren sinnvoll umsetzbar.
            Ich empfehle Variante C: Sie hält Tür und Schrank frei und wirkt ruhiger.
            Variante B lässt mehr Fläche am Fenster, ist aber enger am Bett.”
```

The user may then apply, compare, request a different priority, or relax a requirement.

------------------------------------------------------------------------

## Relationship to existing decisions

| Decision | Relationship |
|---|---|
| **DD-008** | Supplies deterministic findings and severity; DD-017 adds ordered candidate evaluation around them. |
| **DD-009** | Boundary remains: AI plans; Core executes and validates. AI iteration uses allowlisted semantic intentions, not unrestricted geometry. |
| **DD-011** | Recipe remains a strategy, not a solution. DD-011's deterministic Core winner remains v1 fallback; DD-017 targets Core functional shortlist → AI recommendation → User selection and therefore requires a later amendment when accepted. |
| **DD-015** | Existing soft metrics remain deterministic v1 proxies. “No aesthetics score” continues to mean no aesthetics as a Core metric; DD-017 adds a separate, optional probabilistic AI channel and requires an amendment when accepted. |
| **DD-016** | Recipes remain deterministic Core tools and one source of candidate intentions. They need not contain every room type, aesthetic rule, or user negotiation. |

If accepted, implementation may require amendments to DD-011 and DD-015 where their v1 wording
currently excludes aesthetic ranking or assigns all default selection to Core. Those accepted v1
contracts remain valid until the amendments and schemas are explicitly reviewed.

------------------------------------------------------------------------

## Alternatives considered

| Alternative | Why rejected |
|---|---|
| One LLM command batch, then validation | Leaks failed attempts to users; weak iteration |
| AI owns all coordinates and scoring | Non-deterministic geometry and unverifiable usability |
| Core-only universal planner | Hard to encode taste, flexible intent, and open-ended strategy without a very large solver |
| Preferences only inside generators | Lost or inaccessible after movement/import; couples evaluation to geometry creation |
| One positive star score | Severe defects can be hidden by minor benefits; poor explainability |
| AI aesthetic score before validation | Allows attractive but unusable layouts to rank highly |
| No aesthetic signal | Functionally valid but visually poor candidates remain indistinguishable |

------------------------------------------------------------------------

## Consequences

- Agent orchestration needs a bounded propose → dry-run → revise loop rather than a single finalization pass.
- Candidate evaluation becomes an explicit product contract, not scattered prompt heuristics.
- Semantic object instances need durable profile and role metadata independent of mesh generation.
- Core scoring must support signed components, severity/gates, context weights, and full breakdowns.
- The Viewer eventually needs progress states and candidate comparison, while Apply remains explicit.
- Aesthetic evaluation introduces model/version variance; standardized evidence, rubrics, confidence,
  caching, and opt-out/provider considerations are required before implementation.
- This architecture supports imported/catalog furniture as long as it can be mapped to a semantic profile.
- DD-011 candidate expansion and existing soft ranking may continue during review; new role schemas,
  signed/context scoring, selection ownership changes, and AI aesthetics wait for acceptance.

------------------------------------------------------------------------

## Remaining questions for implementation review

1. Where is the canonical object preference/capability profile registry stored and versioned,
   and which fields may generators or instances override?
2. Which initial allowlisted roles, semantic intentions, score categories, numeric ranges, and
   severe-veto thresholds form Evaluation v1?
3. How should the intended small combination of Pareto filtering plus top-k limiting be calibrated?
4. Are the proposed interactive budgets (four candidates, two revisions, configurable timeout)
   appropriate after measurement on real rooms?
5. Which standardized camera set and numeric functional-equivalence band are sufficient for the
   first experimental aesthetic comparison?
6. Which evaluation details, privacy/cost disclosures, and provenance fields belong in normal UX
   versus an expert explanation/audit view?

------------------------------------------------------------------------

## Proposed implementation order (not authorized until Accepted)

1. Continue DD-011 candidate expansion and existing soft ranking without introducing DD-017 schemas.
2. Review and accept/amend DD-017; then add narrow DD-011/DD-015 amendments.
3. Define a minimal semantic capability/preference-profile, role, and intention allowlist schema.
4. Add signed deterministic score components, veto rules, and context weights.
5. Implement bounded internal revision and Core functional shortlisting before user-facing proposals.
6. Expose candidate comparison and score breakdown in the Viewer.
7. Prototype standardized renders plus comparative AI aesthetics behind an optional experimental flag.
8. Calibrate rubrics/weights using real rooms and user feedback; avoid hard-coding taste prematurely.

------------------------------------------------------------------------

## History

| Ver | Date | Note |
|---|---|---|
| 0.1 | 2026-07-21 | Proposed — collaborative planning loop, durable furniture preferences, signed/contextual scoring, and AI aesthetics |
| 0.2 | 2026-07-21 | Review revision — Core functional shortlist → AI recommendation → User selection; semantic allowlist, validity table, anti-compensation, capabilities/roles, and experimental aesthetics clarified |
| 0.3 | 2026-07-21 | Acceptance-prep revision — functional equivalence principle, proposal leak guard, DD-008 mapping, high-impact role clarification, override labeling, instance persistence, and aesthetic caching |
| 1.0 | 2026-07-21 | **Accepted** — target contract locked; DD-011/DD-015 amended narrowly; implementation remains staged |
