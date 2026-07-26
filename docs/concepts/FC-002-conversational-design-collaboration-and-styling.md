# FC-002 — Conversational Design Collaboration and Styling

**Status:** Active (WP-01 next; WP-A shipped `0.10.83`–`0.10.86`)  
**Date:** 2026-07-25 · **Activated:** 2026-07-26  
**Owner:** Product / Architecture  
**Related:** [DD-009](../design_decisions/DD-009-ai-execution-boundary.md) · [DD-017](../design_decisions/DD-017-collaborative-planning-and-contextual-evaluation.md) · [DD-018](../design_decisions/DD-018-semantic-transactions-and-authority.md) · [DD-019](../design_decisions/DD-019-semantic-direct-manipulation.md) · [DD-021](../design_decisions/DD-021-advanced-support-surfaces.md) · [DD-022](../design_decisions/DD-022-conversational-collaboration-contracts.md) · [FC-001](FC-001-semantic-direct-manipulation-and-multi-room-editing.md) · [ROADMAP](../ROADMAP.md)

------------------------------------------------------------------------

## 1. Purpose

LayoutLab conversations must not treat every user message as an instruction to
produce commands. A user may want to discuss a room, ask for an opinion, compare
their manual edit with an earlier suggestion, explore a style or ask LayoutLab to
decorate a scene.

This concept defines a collaborative conversation in which:

- ordinary conversation can remain conversation;
- observation and advice do not mutate the project;
- manual user edits remain first-class input to the AI;
- requested changes become previewable proposals, never hidden mutations;
- decoration uses semantic assets and support surfaces;
- aesthetic judgement complements, but never overrides, deterministic validity;
- the user remains the final authority.

> The AI is not a command compiler attached to a chat box. It is a design partner
> that can converse, observe, propose, test and explain — while LayoutLab Core
> remains the deterministic authority for project state and spatial validity.

------------------------------------------------------------------------

## 2. Problem

The current thin interaction encourages a one-step interpretation:

```text
User message -> AI commands -> Core validation -> proposal or error
```

That is useful for explicit actions, but it creates several product problems:

1. A casual remark or design question may be misread as an edit request.
2. The user cannot naturally make a manual change and ask, “Is this what you
   meant?”
3. Invalid trial commands can leak into the visible conversation as a failed user
   request instead of being revised internally.
4. “Decorate this room” requires more than object creation: the system must know
   which objects belong on which surfaces, how dense the decoration should be and
   whether the result is visually coherent.
5. Aesthetic advice is subjective and probabilistic, while collisions, supports
   and clearances are objective. Treating both as one undifferentiated score would
   weaken both.

------------------------------------------------------------------------

## 3. Product principles

### 3.1 Not every utterance is an action

Conversation, questions, observations and feedback must be valid outcomes with
zero commands. The absence of commands is not a failure.

### 3.2 Observation before mutation

When the user asks what the AI thinks, the default result is an assessment. The AI
may mention possible improvements, but it creates a proposal only when the user
asks it to act or explicitly accepts an offer to try a change.

### 3.3 Internal negotiation before user-facing proposals

The AI may try candidates, ask Core for analysis and revise them internally. A
candidate that violates hard constraints must not be presented as an applicable
solution. The user sees the best viable result, meaningful alternatives or an
honest explanation that no acceptable solution was found.

### 3.4 Manual and AI edits share one project history

The user may freely edit between conversation turns. The AI observes semantic
revisions and change summaries instead of assuming that its last proposal is still
the current scene. Manual work must never be silently overwritten.

### 3.5 Decoration is semantic placement

Decor objects are not arbitrary meshes placed at guessed coordinates. They have
capabilities, valid supports, orientation needs, spacing rules and aesthetic
preferences. Placement uses Core operations and DD-021 support relations.

### 3.6 Function before aesthetics

Hard validity and functional usability are evaluated first. AI aesthetics is an
optional, labeled opinion used only among viable or explicitly comparable results.
An attractive image cannot compensate for a blocked door, collision or invalid
support.

### 3.7 User authority is explicit

The Apply Gate remains. Suggestions, styling candidates and inferred preferences
are inspectable and reversible. The user may reject, refine or manually modify any
result.

------------------------------------------------------------------------

## 4. Conversational turn model

Every turn should have a semantic interaction kind. The exact protocol belongs in
a later DD/contract; this concept fixes the product behaviour.

| Turn kind | User intent | Expected system behaviour |
|---|---|---|
| `conversation` | Casual discussion, taste, ideas | Natural reply; no commands |
| `question` | Ask about the project or design principles | Answer from project context; no commands by default |
| `observation_request` | “What do you think of this?” | Inspect current revision and explain findings; no commands |
| `feedback` | Accept, reject or qualify an earlier idea | Update semantic conversation state; do not mutate unless requested |
| `planning_request` | Explore options or solve a layout problem | Search/test candidates; present viable proposal(s) |
| `action_request` | Explicitly change the project | Produce a validated proposal behind the Apply Gate |
| `styling_request` | Decorate or visually refine the room | Run the styling candidate loop and present a preview |

These are not rigid UI modes the user must select. The agent infers them and can
ask a short clarification when intent is materially ambiguous:

> “Möchtest du nur meine Einschätzung, oder soll ich eine Variante ausprobieren?”

A structured agent response should distinguish at least:

```text
turn_kind
reply
proposal (optional)
open_question (optional)
observed_revision
```

Free text must not be parsed later to decide whether a mutation exists.

------------------------------------------------------------------------

## 5. Semantic conversation state

Natural collaboration needs more than raw chat history. LayoutLab should maintain a
small, inspectable semantic state containing only durable meaning:

- current design goal;
- hard requirements and soft preferences;
- room use and relevant object roles;
- desired style and decoration density;
- accepted and rejected decisions;
- open questions;
- current object/candidate references (“the bed”, “variant two”);
- last proposal, its base revision and its design intent;
- last observed project revision and relevant findings.

Raw conversation may remain available to the provider during a session, but it is
not the authoritative product state. Important conclusions must be represented
semantically so they can be inspected, corrected and persisted deliberately.

### 5.1 Preference provenance

The system distinguishes:

- explicit user preferences;
- preferences inferred from the current conversation;
- project/room defaults;
- temporary instructions for one proposal.

Inferred preferences are labeled and must not silently become permanent personal
facts. The user can correct or remove them.

### 5.2 Reference resolution

References such as “move it a little left” require stable object/candidate IDs plus
recent conversational focus. If more than one plausible referent exists, the AI
asks rather than guesses.

------------------------------------------------------------------------

## 6. Understanding manual user changes

The user may modify a room or object directly and then ask:

> “Hast du dir das ungefähr so vorgestellt?”

The AI needs four inputs:

1. the previous observed project revision;
2. the design intent of its prior suggestion, if any;
3. the current project revision;
4. a semantic change summary between those revisions.

The change summary should describe domain operations, not mesh differences:

```text
- desk moved 0.45 m toward the window
- bed rotated 90°
- wardrobe width changed from 1.20 m to 1.60 m
- plant placed on desk.surface_top
```

The AI compares the change against intent and current analysis. It can then answer:

- what matches its earlier idea;
- what differs but may be equally good;
- what new conflict or benefit appeared;
- whether it would recommend leaving the scene as-is.

This is observation only. Corrective commands are proposed only after an explicit
action request. DD-018 revisions and FC-001 transactions are the foundation; a
later architecture decision must define the durable change-summary contract.

------------------------------------------------------------------------

## 7. Styling and decoration

### 7.1 Styling request

“Dekoriere das Zimmer” is a high-level goal, not permission for arbitrary clutter.
The AI first uses known project/style preferences. It asks only when a missing
choice would materially change the result, for example minimal versus playful.

It then chooses from available semantic decor assets, develops a small number of
compositions, asks Core to place and validate them, compares the viable results and
presents a preview.

### 7.2 Decor asset semantics

Decor generators should expose capabilities and placement preferences rather than
room-specific coordinates. Examples:

| Asset | Typical capability / preference |
|---|---|
| Laptop | horizontal support; desk/table preferred; usable orientation |
| Monitor | horizontal support; rear zone of desk; faces chair/work position |
| Cup | horizontal support; safe edge distance; avoid equipment overlap |
| Table lamp | horizontal support; cable/access implications may follow later |
| Plant | floor or suitable surface; optional daylight preference |
| Cushion | compatible seating/bed support; soft grouping |
| Rug | room floor; relates to furniture grouping; no door obstruction |
| Wall art | vertical support/mount area; later milestone, not DD-021 MVP |

The generator owns intrinsic object knowledge and available surfaces. Contextual
importance, user taste and room role belong to evaluation/state, as established by
DD-017.

### 7.3 Support and placement tools

The AI should prefer semantic tools such as:

```text
list_decor_assets
get_support_surfaces
find_valid_surface_positions
place_on_surface
arrange_on_surface
render_candidate_views
analyze_candidate
```

Names are illustrative, not a frozen API. Core resolves exact coordinates and
support projection. DD-021 `support_ref` / `support_local_xy` remains authoritative
for implemented horizontal surfaces.

### 7.4 Density and clutter budget

Styling needs an explicit density target (for example sparse, balanced, rich) and a
budget per relevant surface/zone. More decor is not automatically better. The
system should penalize:

- crowded support surfaces;
- blocked functional clearances;
- many unrelated focal points;
- unsafe edge placement;
- repetitive “AI showroom” object patterns;
- decor that hides or harms the room’s primary function.

The user can request “more”, “less”, “warmer” or “cleaner” and receive a revised
proposal rather than a full restart.

------------------------------------------------------------------------

## 8. Aesthetic understanding

LayoutLab Core remains responsible for measurable spatial reality. The AI may add
aesthetic judgement using the DD-017 probabilistic channel.

### 8.1 Fixed comparative rubric

Aesthetic assessment should be comparative and structured, for example:

- visual balance;
- composition clarity;
- spacing rhythm;
- visual hierarchy and focal point;
- perceived clutter;
- proportional coherence;
- consistency with the requested style.

It returns reasons and confidence, not an unexplained “9/10”. It is labeled as a
design assessment, not objective truth.

### 8.2 Evidence

Candidate comparison should use standardized evidence:

- consistent top-down view;
- one or more consistent eye-level views when decoration height matters;
- stable camera, lighting, neutral materials and framing;
- semantic relations and functional analysis alongside images.

Without standardization, the model may score rendering quality or camera angle
instead of the arrangement.

### 8.3 Taste and context

The rubric is filtered through explicit style intent such as cozy, playful,
minimal, Scandinavian, natural, technical or colorful. A later taste profile may
learn from accepted/rejected proposals, but must preserve provenance and user
control.

### 8.4 No aesthetic compensation

Evaluation order is strict:

```text
hard validity
-> functional usability and support rules
-> contextual preferences / penalties
-> viable shortlist
-> optional AI aesthetic comparison
-> user decision
```

Negative functional findings and vetoes from DD-017 cannot be canceled by a high
aesthetic assessment.

------------------------------------------------------------------------

## 9. Collaborative planning loop

The visible conversation represents three authorities with different jobs:

| Participant | Responsibility |
|---|---|
| User | Express goals, edit directly, judge satisfaction, approve changes |
| AI | Converse, interpret intent, choose strategies, compare and explain |
| LayoutLab Core | Execute semantic operations, validate, analyze and preserve state |

Internally, planning may require several rounds:

```text
User request
-> AI derives intent and requirements
-> AI inspects project/state/assets
-> AI develops candidate
-> Core dry-runs, validates and analyzes
-> invalid candidate is rejected internally
-> AI revises or tries another candidate
-> viable candidates are compared
-> optional aesthetic comparison
-> AI presents recommendation and trade-offs
-> User applies, refines, edits manually or declines
```

The user need not see every failed internal attempt, but the UI should show concise
progress such as “prüft Abstände” or “vergleicht zwei Varianten” so the system does
not appear frozen. Detailed diagnostics remain available on demand.

If no viable result exists, the AI explains the blocking requirements and asks
which trade-off the user is willing to change. It does not fabricate success.

------------------------------------------------------------------------

## 10. Example conversations

### 10.1 Conversation without action

```text
User: Ich finde den Raum noch etwas kühl. Was meinst du?

AI: Die großen freien Flächen und die gleichmäßigen Abstände wirken eher sachlich.
Mit Textilien, einer Pflanze und einem wärmeren Schwerpunkt am Bett könnte er
gemütlicher wirken. Möchtest du nur Ideen sammeln oder soll ich eine dezente
Variante ausprobieren?
```

No commands are created.

### 10.2 Manual edit followed by comparison

```text
User moves the desk toward the window and rotates the bed.

User: So ungefähr?

AI: Ja — der Schreibtisch erfüllt jetzt die Tageslicht-Idee. Das gedrehte Bett war
nicht Teil meines Vorschlags, funktioniert aber ebenfalls; der freie Bereich in
der Mitte wird sogar größer. Nur die rechte Schranktür hat jetzt wenig Platz.
Soll ich dafür eine kleine Korrektur ausprobieren?
```

No corrective commands exist until the user agrees.

### 10.3 Styling request

```text
User: Dekoriere den Arbeitsplatz bitte gemütlich, aber nicht vollgestellt.

AI (internal): lists decor and desk surfaces, creates two sparse candidates,
Core rejects one because the cup overlaps the laptop clearance, AI revises it,
then compares the viable compositions.

AI: Ich habe eine zurückhaltende Variante vorbereitet: Monitor und Laptop bleiben
funktional, eine kleine Lampe bildet den warmen Schwerpunkt und die Pflanze steht
nicht im Arbeitsbereich. Die Tasse habe ich bewusst weggelassen, damit die Fläche
ruhig bleibt.

[Preview] [Apply] [Discard]
```

------------------------------------------------------------------------

## 11. Authority, safety and privacy

- No conversational reply mutates project state implicitly.
- Every proposed project change carries `base_revision`; stale proposals are not
  auto-merged (DD-018).
- One accepted styling composition is one semantic transaction and one Undo step.
- The AI receives only the project context needed for the turn.
- Visual evidence sent to an external provider follows DD-017 disclosure rules.
- Provider/model and probabilistic aesthetic involvement remain visible.
- Objects marked `protected_from_ai` are never altered by styling proposals.
- User-authored changes made after a proposal are preserved; the AI must re-observe
  before revising.

------------------------------------------------------------------------

## 12. Boundaries and non-goals

This concept does not require:

- an autonomous always-running decorator;
- hidden auto-apply;
- arbitrary Blender/Python or raw mesh edits;
- permanent psychological profiling of the user;
- an objective universal beauty score;
- a full photorealistic renderer;
- wall/ceiling mounting in the first decoration slice;
- physics simulation;
- cloud accounts, subscriptions or cross-user preference sharing;
- exposing every failed candidate in the main chat.

------------------------------------------------------------------------

## 13. Architectural decomposition required before implementation

The concept is coherent enough for decomposition, but it crosses agent state,
conversation contracts, revision history, asset semantics and probabilistic visual
evaluation. It must not become one monolithic agent feature.

At minimum, decomposition should decide:

1. **Conversational turn and authority contract** — [DD-022](../design_decisions/DD-022-conversational-collaboration-contracts.md) (**Proposed**)
2. **Semantic conversation state** — DD-022 (**Proposed**)
3. **Revision change summaries** — [DD-018](../design_decisions/DD-018-semantic-transactions-and-authority.md) §7 amendment (**Proposed**) + DD-022
4. **Decoration affordances** — [DD-021](../design_decisions/DD-021-advanced-support-surfaces.md) §9 amendment (**Proposed**) + WP-05 audit
5. **Styling evidence and evaluation** — [DD-017](../design_decisions/DD-017-collaborative-planning-and-contextual-evaluation.md) FC-002 amendment (**Proposed**) + DD-022

Existing DDs are amended narrowly where they already own a decision. **DD-022** covers
the genuinely new collaboration-state / turn boundary; it does not restate DD-017,
DD-018 or DD-021.

------------------------------------------------------------------------

## 14. Derived work packages

These are stable planning references. Binding work order: [`docs/ROADMAP.md`](../ROADMAP.md)
§§2–3 (FC-002 is **Active**).

**Shipped first vertical slice:** `FC-002/WP-A` conversation-safe
turns (`0.10.83`) plus routing stabilizations (`0.10.84`–`0.10.86`).

**WP-A includes:** structured `turn_kind`, no-command for assessment/observation/feedback/
clarification, `planning_request`/`action_request` still reach recipe fallback, accept
follow-ups, furniture swap verbs, and `styling_request` as **acknowledgement only**
(no decor/styling candidate loop yet).

| ID | Work package | Entry condition |
|---|---|---|
| **FC-002/WP-A** | Conversation-safe turn + routing stabilize | Done `0.10.83`–`0.10.86` |
| **FC-002/WP-01** | Architecture package: remaining turn contract details, semantic state ownership, manual-change summaries and styling boundary | **Awaiting Accept** — [DD-022](../design_decisions/DD-022-conversational-collaboration-contracts.md) + DD-017/018/021 amendments |
| **FC-002/WP-02** | Conversation intent routing polish (LLM + clarification UX) | WP-01 Accepted; extends WP-A heuristics |
| **FC-002/WP-03** | Semantic conversation state, reference resolution and preference provenance | WP-01; provider-neutral agent contract |
| **FC-002/WP-04** | Manual-change understanding from project revisions and semantic operation summaries | WP-01; DD-018 §7 change-summary contract |
| **FC-002/WP-05** | Decor capability metadata and semantic placement helpers over DD-021 support surfaces | WP-01; existing decor generators audited |
| **FC-002/WP-06** | Styling candidate loop: arrange, dry-run, analyze, render, aesthetic compare and preview | WP-02/03/05; DD-017 evidence boundary confirmed |
| **FC-002/WP-07** | User-controlled taste profile and learning from accepted/rejected styling proposals | Real WP-06 usage demonstrates need |

**Still open for full FC-002:** WP-01 Accept, then WP-02…WP-07 (manual-change summaries, durable
conversation state, decor helpers, styling candidates, eye-level aesthetics, taste profile).
Automatic decoration does **not** exist yet.

------------------------------------------------------------------------

## 15. Acceptance criteria

### 15.1 First vertical slice (WP-A) — shipped when

1. A user can chat or ask for an assessment without commands being generated.
2. Ambiguous action intent produces a clarification, not a guessed mutation.
3. `turn_kind` and `observed_revision` are structured on the agent result; Core does not
   force `plan_layout` on non-mutating turns.
4. Explicit room planning goals (e.g. „Schlafzimmer mit zwei Fenstern“) still reach
   `planning_request` / recipe fallback and persist requirements for retries.
5. `styling_request` is acknowledged without commands (full styling loop is later WPs).

### 15.2 Full concept MVP — complete when

1. WP-A criteria above.
2. The AI can explain meaningful manual changes since its last observation.
3. An explicit styling request can use a limited decor set and existing horizontal
   support surfaces to produce at least two internally validated candidates.
4. Invalid candidates are revised or discarded before presentation.
5. The AI can compare viable styling candidates using a fixed, disclosed aesthetic
   rubric and standardized evidence.
6. The final proposal remains behind Apply/Discard, is revision-safe and becomes
   one Undoable transaction when accepted.
7. The user can request less/more/different decoration without losing unrelated
   manual edits.

------------------------------------------------------------------------

## 16. Open questions for decomposition

Architectural questions from the original decomposition list are **resolved in
[DD-022](../design_decisions/DD-022-conversational-collaboration-contracts.md)** (Proposed).
Remaining implementation questions (not Accept blockers):

- Which existing decor generators are safe for the first supported asset set? → WP-05
- Exact eye-level camera poses for comparative styling? → WP-06
- Concrete `agent_state` field freeze for provenance/focus? → WP-03
- Concrete `summarize_changes` tool shape? → WP-04

