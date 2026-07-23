# LayoutLab — Product Roadmap

**Status:** Binding · **Updated:** 2026-07-23 (`0.10.63` oriented attachments; WP-07 DD-021 Proposed)

> **This file is the only authoritative source for product priorities and work order.**
>
> Feature *behaviour* lives in Feature Concepts (`docs/concepts/`). Binding *architecture*
> lives in Design Decisions (`docs/design_decisions/`). Session *as-built hints* live in
> [`HANDOFF.md`](HANDOFF.md). Do not copy those here — link them.

**Agent reading order:**

1. [`00_READ_THIS_FIRST.md`](../00_READ_THIS_FIRST.md)
2. [`AI_CONTEXT.md`](../AI_CONTEXT.md)
3. **This file** (`docs/ROADMAP.md`)
4. The Feature Concept linked by the **Active** entry
5. Related **Accepted** Design Decisions
6. [`HANDOFF.md`](HANDOFF.md) for technical as-built state and session notes

Long-term vision phases (not the working queue): [`LayoutLab_Master_Design_Document.md`](../LayoutLab_Master_Design_Document.md) §17.

------------------------------------------------------------------------

## 1. Implemented Foundations

| ID / name | Notes |
|---|---|
| JSON commands + scene export | [DD-003](design_decisions/DD-003-json-only-communication.md) · [`json_protocol.md`](json_protocol.md) |
| Parametric generators + regeneration | [DD-001](design_decisions/DD-001-generators-are-parametric-assets.md) / [DD-002](design_decisions/DD-002-generators-rebuild-instead-of-scale.md) |
| Clearances + layout analysis | [DD-007](design_decisions/DD-007-clearance-zones.md) / [DD-008](design_decisions/DD-008-constraints-and-layout-analysis.md) · soft metrics [DD-015](design_decisions/DD-015-soft-metrics-and-tradeoffs.md) |
| Room Model (single space, rectangle MVP) | [DD-010](design_decisions/DD-010-room-model.md) · [`room_model.md`](room_model.md) |
| Standalone Core HTTP + Viewer | [DD-014](design_decisions/DD-014-standalone-runtime-path.md) |
| AI chat / agent path (Core tools, Apply-Gate) | [DD-009](design_decisions/DD-009-ai-execution-boundary.md) · [`agent_tool_contract.md`](agent_tool_contract.md) |
| Deterministic layout recipes | [DD-016](design_decisions/DD-016-deterministic-layout-recipes.md) · e.g. `bedroom_basic` |
| Candidate expansion + soft ranking | [DD-011](design_decisions/DD-011-layout-variants-and-comparison.md) · `plan_layout` (`0.10.24`) |
| Evaluation schema, shortlist, revision | [DD-017](design_decisions/DD-017-collaborative-planning-and-contextual-evaluation.md) · `0.10.25`–`0.10.33` |
| Experimental AI aesthetics (opt-in) | `0.10.34` / `0.10.35` |
| FC-001/WP-01 — DD package | [DD-018](design_decisions/DD-018-semantic-transactions-and-authority.md) · [DD-019](design_decisions/DD-019-semantic-direct-manipulation.md) · [DD-020](design_decisions/DD-020-spatial-project-independent-rooms.md) **Accepted** |
| FC-001/WP-02 — semantic transactions | `0.10.36` · [FC-001](concepts/FC-001-semantic-direct-manipulation-and-multi-room-editing.md) |
| FC-001/WP-03 — furniture ops | `0.10.37` · [DD-019](design_decisions/DD-019-semantic-direct-manipulation.md) |
| FC-001/WP-04 — parametric resize | `0.10.38` |
| FC-001/WP-05 — wall/corner + inactive openings | `0.10.39` |
| FC-001/WP-06 — Spatial Project / independent rooms | `0.10.40` · [DD-020](design_decisions/DD-020-spatial-project-independent-rooms.md) |
| Viewer multi-room UX | `0.10.41`–`0.10.42` (focus / floorplan / meta) |
| Viewer direct manipulation → Core | `0.10.43`–`0.10.57` (preview/commit, wall/corner, selection gizmos, overlay/pick polish) |
| Viewer planning feedback polish | `0.10.58` — proposed vs committed (banner, reason, proposal findings, Inspector Planning, Apply-Gate copy) |
| Room Z-rotate | `0.10.60`–`0.10.63` — Core `rotate_room` + Viewer ring; oriented openings/fixed; pick/preview fixes |

**Begriffsklärung (heute vs. später):**

| Term | Today | Later |
|---|---|---|
| **Varianten** | Ephemeral planning candidates + shortlist (DD-011/017) | Persisted named project/room variants |
| **Automatische Raumplanung** | Recipe-driven candidates + force path | Full problem-first planner |
| **KI bewertet Layouts** | Deterministic scores + optional AI aesthetics on shortlist | Broader product UX, calibrated rubrics |
| **Möbelbibliothek** | Bundled generators + browser list | Catalog / import / asset polish |
| **Komplette Wohnungsplanung** | Independent multi-room (DD-020 / `0.10.40`) | Connected topology / shared walls |
| **Undo** | Semantic Core transactions (`0.10.36`) | Further history polish as needed |

------------------------------------------------------------------------

## 2. Active

| ID | Scope | Concept / DDs | Status |
|---|---|---|---|
| [FC-001/WP-07](concepts/FC-001-semantic-direct-manipulation-and-multi-room-editing.md#15-derived-work-packages) | Advanced support surfaces / stacking | [FC-001](concepts/FC-001-semantic-direct-manipulation-and-multi-room-editing.md) · [DD-021](design_decisions/DD-021-advanced-support-surfaces.md) **Proposed** — Accept before coding | **Current** |

Product surface remains Standalone Viewer + Core ([`AI_CONTEXT.md`](../AI_CONTEXT.md)). Blender = runtime adapter.

------------------------------------------------------------------------

## 3. Queued

| ID | Scope | Entry condition |
|---|---|---|
| *(none locked)* | — | Promote from Refinement / Later when product asks |

------------------------------------------------------------------------

## 4. Refinement / On Demand

Not blocking the Active/Queued track. No fixed sprint commitments except the aesthetics privacy minimum below.

**Viewer score / trade-off explanation (refinement)**

- MVP today is enough: soft warnings, `selection_reason`, optional aesthetics note — no numbers dashboard.
- Target (staged): short understandable summary of main pros/cons/trade-offs; later optional expandable detail (scores, penalties, vetoes, aesthetics).
- Do not schedule a complex metrics dashboard.

**Shortlist / proposal comparison UX (later polish)**

- Current cards + reason + findings are enough for now (`0.10.58`).
- Later: richer comparison without a metrics dashboard (e.g. clearer trade-offs, optional larger selected-card preview).

**Further recipes (strictly on demand)**

- No second recipe is scheduled by default.
- Only when a real planning scenario outgrows `bedroom_basic`.
- `kids_room` is a plausible candidate, **not** a commitment.

**AI aesthetics: privacy / provider transparency (two-stage)**

| Stage | When | Content |
|---|---|---|
| **1 — Minimum** | Whenever experimental AI aesthetics is on and images/room data leave the machine | Disclose transfer, provider/model, possible API cost, experimental/optional |
| **2 — Full** | Before default-on or production offer | Consent dialogs, detailed settings, default-on policy |

Stage 1 is a known gap for the opt-in flag — aesthetics refinement, **not** FC-001. Stage 2 stays deferred.

**Other refinements**

- Calibrate DD-017 rubrics/weights on real rooms; incorporate user feedback

------------------------------------------------------------------------

## 5. Later Feature Concepts

Need a Feature Concept and/or DD before implementation — **not** active commitments:

| Topic | Notes |
|---|---|
| [FC-001/WP-07](concepts/FC-001-semantic-direct-manipulation-and-multi-room-editing.md#15-derived-work-packages) | Also listed under Queued with late entry — behaviour in FC-001 only |
| Persisted project variants | Save, name, compare, favorite — **not** the same as ephemeral candidates |
| Walkway / navigation analysis | Experimental idea in [`Future_Ideas.md`](Future_Ideas.md) §5 |
| Polygon rooms | DD-010 next (`footprint.kind = polygon`) — after FC-001 WP-01…WP-06 |

------------------------------------------------------------------------

## 6. Explicitly Deferred

Do not build now (detail: [`Future_Ideas.md`](Future_Ideas.md) §18):

- Capture / LiDAR / reconstruction / floor-plan OCR
- Connected rooms, shared-wall topology, passages
- Multi-floor / building model
- IKEA / product catalog import
- Asset-browser polish (thumbnails, favorites, drag-and-drop, live preview) — [DD-004](design_decisions/DD-004-asset-browser-ui.md) `[PLANNED]`, deferred
- Cloud, auth, sync
- Custom render engine
- Full standalone authoring app beyond Viewer + Core chat/edit surface
- AI aesthetics privacy **stage 2** (consent / default-on) — only before a production offer

------------------------------------------------------------------------

## Maintenance

| Change | Update |
|---|---|
| Priority / order / Active entry | **This file** (required) |
| Session version, gotchas, as-built | [`HANDOFF.md`](HANDOFF.md) — link the Active ROADMAP row |
| Long-term vision wording only | [`LayoutLab_Master_Design_Document.md`](../LayoutLab_Master_Design_Document.md) §17 summary + link here |
| Feature behaviour | Relevant `docs/concepts/FC-xxx-*.md` |
| Binding architecture | New/updated DD |

If another document disagrees with this file on **what to build next**, this file wins — then fix the other document.
