# LayoutLab — Product Roadmap

**Status:** Binding · **Updated:** 2026-07-27 (FC-002/WP-02 routing polish `0.10.87`)

> **This file is the only authoritative source for product priorities and work order.**
>
> Feature *behaviour* lives in Feature Concepts (`docs/concepts/`). Binding *architecture*
> lives in Design Decisions (`docs/design_decisions/`). Session *as-built hints* live in
> [`HANDOFF.md`](HANDOFF.md). Do not copy those here — link them.

**Agent reading order:**

1. [`00_READ_THIS_FIRST.md`](../00_READ_THIS_FIRST.md)
2. [`AI_CONTEXT.md`](../AI_CONTEXT.md)
3. **This file** (`docs/ROADMAP.md`) — start with **§0 Product map**, then **§2 Active**
4. The Feature Concept linked by the **Active** entry
5. Related **Accepted** Design Decisions
6. [`HANDOFF.md`](HANDOFF.md) for technical as-built state and session notes

Long-term vision phases (not the working queue): [`LayoutLab_Master_Design_Document.md`](../LayoutLab_Master_Design_Document.md) §17.

------------------------------------------------------------------------

## 0. Product map

One-page answer to: **what are we doing now**, **what is done**, **is a topic planned at all?**

Status legend:

| Status | Meaning |
|---|---|
| **Done** | Scoped work shipped (FC may still list intentional non-goals as later) |
| **Next** | Active work — see §2 |
| **Queued** | Ordered after Active — see §3 |
| **Partial** | FC/slice exists; some WPs shipped, theme not Active |
| **Later** | Named on this roadmap; needs FC/DD or waits behind queue — not started |
| **Deferred** | Explicitly out of scope for now — see §6 |
| **Idea only** | Vision / Future Ideas; **not** scheduled here |

| Thema | Art | Status | Geplant? | Detail |
|---|---|---|---|---|
| [FC-001](concepts/FC-001-semantic-direct-manipulation-and-multi-room-editing.md) Semantic direct manipulation + multi-room | Feature Concept | **Done** (WP-01…WP-07) | Yes — closed | Non-goals (shared walls, polygon, physics stacking, …) → Later / Deferred |
| [FC-002](concepts/FC-002-conversational-design-collaboration-and-styling.md) Conversation, collaboration & styling | Feature Concept | **Next** (Active; WP-A…WP-02 done) | Yes — **Active theme** | WP-03 now; WP-04…WP-07 in §3 · [DD-022](design_decisions/DD-022-conversational-collaboration-contracts.md) Accepted |
| AI-01 Evaluation scoring v0.2 | Competence slice | **Done** (`0.10.80`) | Yes — closed | §1 |
| AI-02 `kids_room_basic` | Competence slice | **Done** (`0.10.81`) | Yes — closed | §1 |
| AI-03 Trade-off explanation | Competence slice | **Later** | Yes — after FC-002 | §5 · DD-017 #9 |
| AI-04 Allowlist expansion | Competence slice | **Later** | Yes — after AI-03 | §5 |
| AI-05 Circulation soft metric | Competence slice | **Later** | Yes — after AI-04 | §5 |
| AI-06 Walkway / navigation | Future FC | **Later** | Yes — after AI-05; *create FC* | §5 · no FC file yet |
| AI-07 Persisted variants | Future FC | **Later** | Yes — after AI-06; *create FC/DD* | §5 · no FC file yet |
| AI-08 Problem-first Intent | Competence slice | **Later** | Yes — after AI-07 | §5 |
| AI-09 Automatic repair proposals | Competence slice | **Later** | Yes — after AI-08 | §5 |
| Polygon rooms | Room-model extension | **Later** | Yes — named | §5 · DD-010 next; no FC |
| AI aesthetics privacy stage 1 | Refinement | **Done** (`0.10.79`) | Yes — closed | §4 |
| AI aesthetics privacy stage 2 | Refinement | **Deferred** | Yes — deferred until production offer | §4 / §6 |
| Shortlist comparison UX polish | Refinement | **Later** | On demand | §4 — not Active |
| Further recipes (beyond kids room) | Refinement | **Idea only** | **No** — only when product asks | §4 |
| Capture / LiDAR / floor-plan OCR | Vision | **Deferred** | Explicitly not now | §6 · [`Future_Ideas.md`](Future_Ideas.md) |
| Shared walls / connected topology | Vision | **Deferred** | Explicitly not now | §6 |
| Multi-floor / building model | Vision | **Deferred** | Explicitly not now | §6 |
| Product catalog / IKEA import | Vision | **Deferred** | Explicitly not now | §6 |
| Asset-browser polish (DD-004) | Planned DD | **Deferred** | DD exists `[PLANNED]`; not queued | §6 |
| Cloud / auth / sync | Vision | **Deferred** | Explicitly not now | §6 |

**How to use:** If a topic is missing from this table, it is **not planned** on the product roadmap (check [`Future_Ideas.md`](Future_Ideas.md) or add a row when you schedule it). §§2–3 remain the only binding work order.

------------------------------------------------------------------------

## 1. Implemented Foundations

| ID / name | Notes |
|---|---|
| JSON commands + scene export | [DD-003](design_decisions/DD-003-json-only-communication.md) · [`json_protocol.md`](json_protocol.md) |
| Parametric generators + regeneration | [DD-001](design_decisions/DD-001-generators-are-parametric-assets.md) / [DD-002](design_decisions/DD-002-generators-rebuild-mesh.md) |
| Clearances + layout analysis | [DD-007](design_decisions/DD-007-clearance-zones.md) / [DD-008](design_decisions/DD-008-constraints-and-layout-analysis.md) · soft metrics [DD-015](design_decisions/DD-015-soft-metrics-and-tradeoffs.md) |
| Room Model (single space, rectangle MVP) | [DD-010](design_decisions/DD-010-room-model.md) · [`room_model.md`](room_model.md) |
| Standalone Core HTTP + Viewer | [DD-014](design_decisions/DD-014-standalone-runtime-path.md) |
| AI chat / agent path (Core tools, Apply-Gate) | [DD-009](design_decisions/DD-009-ai-execution-boundary.md) · [`agent_tool_contract.md`](agent_tool_contract.md) |
| Deterministic layout recipes | [DD-016](design_decisions/DD-016-deterministic-layout-recipes.md) · e.g. `bedroom_basic` |
| Candidate expansion + soft ranking | [DD-011](design_decisions/DD-011-layout-variants-and-comparison.md) · `plan_layout` (`0.10.24`) |
| Evaluation schema, shortlist, revision | [DD-017](design_decisions/DD-017-collaborative-planning-and-contextual-evaluation.md) · `0.10.25`–`0.10.33` |
| Experimental AI aesthetics (opt-in) | `0.10.34` / `0.10.35` |
| AI aesthetics privacy stage 1 | `0.10.79` — transfer/provider/model/cost disclosure when flag on |
| Evaluation schema v0.2 (AI-01) | `0.10.80` — preferred clearances scored; context weights; rank tie-break |
| `kids_room_basic` recipe (AI-02) | `0.10.81` — sleep/play/homework strategies; Kinderzimmer routing |
| Agent blueprint vision | `0.10.82` — multimodal top-down PNG in sketch/dry-run seed (ASCII fallback) |
| FC-002/WP-A conversation-safe turns | `0.10.83` — `turn_kind`, no-command guarantees, `last_observed_revision` |
| Turn-routing follow-up fix | `0.10.84` — accept cues → action; „eingerichtet“ critiques stay conversation |
| Turn-routing furniture actions | `0.10.85` — austauschen/tauschen/drehen → action (no empty command strip) |
| FC-002/WP-A routing stabilize | `0.10.86` — planning goals (`Schlafzimmer mit Fenstern`) vs assessment; recipe fallback restored |
| FC-002/WP-01 architecture package | 2026-07-27 — [DD-022](design_decisions/DD-022-conversational-collaboration-contracts.md) Accepted + DD-017/018/021 amendments |
| FC-002/WP-02 intent routing polish | `0.10.87` — vague asks → clarification; offer follow-ups; `open_question` |
| FC-001/WP-01 — DD package | [DD-018](design_decisions/DD-018-semantic-transactions-and-authority.md) · [DD-019](design_decisions/DD-019-semantic-direct-manipulation.md) · [DD-020](design_decisions/DD-020-spatial-project-independent-rooms.md) **Accepted** |
| FC-001/WP-02 — semantic transactions | `0.10.36` · [FC-001](concepts/FC-001-semantic-direct-manipulation-and-multi-room-editing.md) |
| FC-001/WP-03 — furniture ops | `0.10.37` · [DD-019](design_decisions/DD-019-semantic-direct-manipulation.md) |
| FC-001/WP-04 — parametric resize | `0.10.38` |
| FC-001/WP-05 — wall/corner + inactive openings | `0.10.39` |
| FC-001/WP-06 — Spatial Project / independent rooms | `0.10.40` · [DD-020](design_decisions/DD-020-spatial-project-independent-rooms.md) |
| FC-001/WP-07 — advanced support surfaces | `0.10.64` · [DD-021](design_decisions/DD-021-advanced-support-surfaces.md) |
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
| **FC-002/WP-03** | Semantic conversation state, reference resolution, preference provenance | [FC-002](concepts/FC-002-conversational-design-collaboration-and-styling.md) · [DD-022](design_decisions/DD-022-conversational-collaboration-contracts.md) **Accepted** | **Next** |

One theme at a time: finish FC-002 WPs before returning to the AI competence queue.
WP-A (`0.10.83`–`0.10.86`), WP-01 (DD-022), and WP-02 routing polish (`0.10.87`) are done.

------------------------------------------------------------------------

## 3. Queued

FC-002 work packages (after WP-03):

| ID | Scope | Entry condition |
|---|---|---|
| FC-002/WP-04 | Manual-change understanding from revisions + semantic operation summaries | After WP-01; needs DD-018 §7 |
| FC-002/WP-05 | Decor capability metadata + semantic placement helpers (DD-021 surfaces) | After WP-01; decor generators audited |
| FC-002/WP-06 | Styling candidate loop (arrange → dry-run → analyze → aesthetic compare → preview) | After WP-02/03/05; DD-017 evidence boundary |
| FC-002/WP-07 | User-controlled taste profile (may retain labeled inferred prefs across projects) | After real WP-06 usage shows need |

Not in this queue (deferred / UX-only): aesthetics privacy stage 2, DM polish, Capture, shared walls.

------------------------------------------------------------------------

## 4. Refinement / On Demand

Not blocking the Active/Queued track. No fixed sprint commitments except the aesthetics privacy minimum below.

**Shortlist / proposal comparison UX (later polish)**

- Current cards + reason + findings are enough for now (`0.10.58`).
- Richer comparison / AI-03 trade-off copy waits until after FC-002 (see §5).

**Further recipes**

- ~~**AI-02** `kids_room_basic`~~ ✅ (`0.10.81`).
- No other recipes scheduled by default.

**AI aesthetics: privacy / provider transparency (two-stage)**

| Stage | When | Content |
|---|---|---|
| **1 — Minimum** | Whenever experimental AI aesthetics is on and images/room data leave the machine | Disclose transfer, provider/model, possible API cost, experimental/optional — **shipped `0.10.79`** (health + proposal + reply) |
| **2 — Full** | Before default-on or production offer | Consent dialogs, detailed settings, default-on policy |

Stage 1 is closed for the opt-in flag. Stage 2 stays deferred.

**Other refinements**

- ~~DD-017 scoring calibration (AI-01)~~ ✅ (`0.10.80`). Further passes after user feedback.

------------------------------------------------------------------------

## 5. Later (after FC-002)

Ordered resume of the AI competence queue and other named themes — **not** active while FC-002 is Active:

| ID / topic | Notes |
|---|---|
| AI-03 Trade-off explanation | Short pros/cons in Viewer (no metrics dashboard) · DD-017 #9 |
| AI-04 Allowlist expansion | More roles / semantic intentions / preference keys |
| AI-05 Circulation soft metric | Lightweight circulation proxy (walkway precursor) |
| AI-06 Walkway / navigation | Needs Feature Concept → DD → impl · [`Future_Ideas.md`](Future_Ideas.md) §5 |
| AI-07 Persisted variants | Save/name/compare/favorite — not ephemeral shortlist; needs FC/DD |
| AI-08 Problem-first Intent | Stronger requirements extraction before placement |
| AI-09 Automatic repair proposals | Explainable replans from findings (never silent) |
| Polygon rooms | DD-010 next (`footprint.kind = polygon`) |

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
| Priority / order / Active entry | **This file** (required) — keep **§0 Product map** in sync |
| Theme done / partial / deferred / newly scheduled | **§0** row status (+ move detail into §1–§6 as needed) |
| Session version, gotchas, as-built | [`HANDOFF.md`](HANDOFF.md) — link the Active ROADMAP row |
| Long-term vision wording only | [`LayoutLab_Master_Design_Document.md`](../LayoutLab_Master_Design_Document.md) §17 summary + link here |
| Feature behaviour | Relevant `docs/concepts/FC-xxx-*.md` |
| Binding architecture | New/updated DD |

If another document disagrees with this file on **what to build next**, this file wins — then fix the other document.
