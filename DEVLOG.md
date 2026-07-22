# Devlog

Why important decisions were made — complement to `CHANGELOG.md` (what changed).

------------------------------------------------------------------------

## 2026-07-22 — Selection-based transform gizmos (`0.10.46`)

**Why:** Mode switching (Orbit/Move/Rotate) forced users to hunt for the right
tool; CAD-style gizmos on the selection match the expected “click then
manipulate” flow.

**How:** Selecting furniture or a room shows move arrows, a Z rotate ring
(furniture), and scale böppel; gestures still commit through Core preview.

------------------------------------------------------------------------

## 2026-07-22 — Viewer wall/corner gizmos (`0.10.45`)

**Why:** Wall drag worked but was invisible — users had to discover that walls
themselves were the grab target. FC-001 calls for explicit wall/corner tools.

**How:** Move mode draws wall (blue) and corner (amber) handles from room
footprints; gestures go through Core preview/commit (`move_wall` / `move_corner`).

------------------------------------------------------------------------

## 2026-07-22 — Viewer wall drag + furniture pick (`0.10.44`)

**Why:** Move mode ignored walls (only furniture), but walls were the easiest
meshes to select — drag felt broken.

**How:** Wall parallel drag → `move_wall` preview/commit; raycast prefers
furniture when present; expose `wall_side` on viewer meshes.

------------------------------------------------------------------------

## 2026-07-22 — Viewer direct manipulation Move/Rotate (`0.10.43`)

**Why:** FC-001 / DD-019 Core ops exist; the Viewer still could not drive
preview→commit gestures. Without that, Spatial Project editing stays chat-only.

**How:** Orbit/Move/Rotate toolbar; floor-plane XY drag and Z rotate through
`/v1/preview/begin|update|commit|cancel`; Undo/Redo against Core.

------------------------------------------------------------------------

## 2026-07-22 — Viewer room selection (`0.10.42`)

**Why:** After multi-room Core export, the Viewer still treated the scene as one
undifferentiated mesh pile. Agents and users need to focus a room before direct
manipulation and planning feedback make sense.

**How:** Inspector room list + floorplan for the active room; dim other rooms in
3D; pick sync; Core multi-room example command set.

------------------------------------------------------------------------

## 2026-07-22 — Viewer meta multi-room + hide_room furniture omit (`0.10.41`)

**Why:** Review of WP-06 found hidden rooms still exported member furniture, and the
Viewer meta/floorplan assumed `rooms[0]`. Fix export parity for hide; show project +
all room names in meta; floorplan selects first visible room.

------------------------------------------------------------------------

## 2026-07-22 — Product focus: Standalone Viewer first

**Why:** Day-to-day work is the web Viewer + Core HTTP, not new Blender plugin UX.
Keeping AI_CONTEXT on “Blender first / no viewer planned” was misleading agents.

**How:** AI_CONTEXT v1.1, HANDOFF next-steps, `.cursor/rules/layoutlab-agent.mdc`,
viewer README. FC-001 Core remains the backend; Viewer UX is the active product track.

------------------------------------------------------------------------

## 2026-07-22 — FC-001/WP-06: Spatial Project / independent rooms (0.10.40)

**Why:** DD-020 makes the Spatial Project the only durable root (`rooms[]`, n=1 normal)
with independent multi-room transforms and whole-room move participation rules.

**How:** `project_id` on session/export; `move_room` / `duplicate_room` / room flags;
VALID furniture follows room translate, INVALID stays world-fixed; `local_location` on
export. Shared walls / apartment topology remain later.

------------------------------------------------------------------------

## 2026-07-22 — FC-001/WP-05: wall/corner resize + inactive openings (0.10.39)

**Why:** DD-019 requires wall edits that preserve furniture world pose, keep
swallowed openings/fixed elements as inactive (not deleted), and mark invalid
furniture without silent repair.

**How:** `move_wall` / `move_corner` + attachment reconcile; viewer skips inactive
meshes; `refresh_all_validity` after footprint changes. Next: WP-06 Spatial Project.

------------------------------------------------------------------------

## 2026-07-22 — FC-001/WP-04: parametric resize via regenerate (0.10.38)

**Why:** DD-019 forbids mesh-scale resize; furniture size changes must edit generator
parameters and rebuild (DD-002). Headless Core lacked `regenerate` — only Blender had it.

**How:** `regenerate` / `set_parameter` / `resize` merge params, delete+rebuild same
`object_id`, restore pose/flags. Next: WP-05 wall/opening edits.

------------------------------------------------------------------------

## 2026-07-22 — FC-001/WP-03: semantic furniture ops in Core (0.10.37)

**Why:** DD-019 requires viewport edits to mutate semantic furniture state (pose,
`support_ref`, flags, validity), not raw meshes. WP-03 delivers the Core command
surface so Viewer gestures (later) and AI/user Apply share one path with DD-018
transactions.

**How:** `furniture_ops` + MeshObject Z-rotation; `move`/`rotate_z`/duplicate/delete/
hide/lock by `object_id`; floor support MVP; invalid positions stay assigned.
Selection is ephemeral (no revision). Parametric resize = WP-04; walls = WP-05.

------------------------------------------------------------------------

## 2026-07-22 — FC-001/WP-02: semantic transactions in Core (0.10.36)

**Why:** DD-018 requires one authoritative mutation path so manual edits and AI Apply share
a revision timeline, preview does not flood Undo, and stale proposals cannot overwrite
newer user work. Blender Undo stays out of Core authority.

**How:** `commit_commands` is the live path (`POST /v1/commands`); `apply_commands` remains
internal for clones/dry-run. Integer `revision`, session Undo ≥ 50, Redo reapplies stored
operations, proposals stamp `base_revision`.

**Next:** FC-001/WP-03 (direct furniture manipulation) against DD-019.

------------------------------------------------------------------------

## 2026-07-22 — DD-018 / DD-019 / DD-020 Accepted (FC-001/WP-01)

**Accepted defaults:** session Undo ≥ 50 + integer project revision; duplicate includes
invalid associated objects; wall-hosted fixed elements become inactive (not deleted);
Spatial Project with `rooms[]` is the only durable format (n = 1 normal; no legacy
single-room export support).

**Next:** FC-001/WP-02 implementation against DD-018.

------------------------------------------------------------------------

## 2026-07-22 — FC-001/WP-01: Proposed DD-018 / DD-019 / DD-020

**Why:** FC-001 behaviour is locked, but implementation must not start without binding
architecture. WP-01 splits the concept into three DDs: semantic transactions
and authority (018), direct manipulation invariants (019), and Spatial Project with
independent rooms only (020). DD-010 stays the single-space foundation.

------------------------------------------------------------------------

## 2026-07-22 — Refinement product decisions (docs only)

**Decisions:** (1) Viewer score explanation remains Refinement — MVP soft warnings /
selection reason / aesthetic tip; target = short pros/cons then optional expandable detail,
not a metrics dashboard. (2) Further recipes are strictly on-demand; no second recipe
scheduled; `kids_room` is only a candidate. (3) AI-aesthetics privacy is two-stage —
minimum transfer/provider/cost/experimental disclosure whenever the flag runs; full consent
UX only before default-on or production. None of these block FC-001/WP-01.

------------------------------------------------------------------------

## 2026-07-22 — Roadmap consolidation (docs only)

**Problem:** MDD §17 still showed Clearance, Constraints, Variants, Undo, Optimierer and
Wohnungsplanung as open checkboxes long after those foundations (or partial slices) shipped.
HANDOFF duplicated a long historical checklist; Future_Ideas still called Viewer/chat/variants
“not built”; DD-017 Implementation Order left shipped steps unmarked.

**Decision:** Make MDD §17 the ordered product roadmap (Implemented → Active WP-01 → Queued
WP-02…06 → Refinement → Later concepts → Explicitly Deferred). HANDOFF keeps only the active
focus. Distinguish ephemeral candidates from persisted variants; replace “Undo für Generatoren”
with FC-001/WP-02; leave DD-004/003 polish markers as deferred, not active work.

------------------------------------------------------------------------

## 2026-07-22 — Feature Concepts between Future Ideas and Design Decisions

**Problem:** Direct viewport manipulation, parametric furniture editing, multi-room state,
Undo/Redo and AI authority form one product capability but cross several architectural
decisions. `Future_Ideas.md` was too broad for the complete behaviour, while one giant DD
would mix independent choices and implementation order.

**Decision:** Add `docs/concepts/` with stable `FC-xxx` identifiers. A Feature Concept owns
the coherent user flow, domain behaviour and decomposition; resulting DDs own binding
architecture, and roadmap work packages reference the concept instead of copying it.

**First concept:** FC-001 locks the agreed behaviour, including preserved furniture world
positions during wall resize, visible invalid furniture, reversible inactive openings,
valid-only participation in whole-room moves, semantic regeneration and AI-safe transactions.

------------------------------------------------------------------------

## 2026-07-21 — DD-017 Accepted: collaborative planning and candidate evaluation

**Why:** One-shot AI command proposals exposed invalid attempts to users and had no durable model
for furniture preferences, contextual roles, signed penalties, or aesthetic comparison.

**Decision:** Core validates and produces a deterministic functional shortlist; AI may iterate only
through allowlisted semantic intentions, optionally compares aesthetics among functionally
equivalent viable candidates, and recommends; User selects and controls Apply. Semantic capability
and preference profiles survive generation, while roles and room context determine importance.

**Guardrails:** Invalidity is non-compensable; severe penalties require veto/waiver behavior;
aesthetics remains probabilistic and outside Core metrics. DD-011 and DD-015 received narrow
amendments. No code or evaluation schema shipped in this documentation milestone.

------------------------------------------------------------------------

## 2026-07-19 — DD-016 Planning recipes v0 (`plan_layout`)

**Why:** Endless agent prompt/heuristic patches (sketch, soft/hard replan, AABB nudges)
improved reliability but did not encode “how a human furnishes a bedroom.” Planning must
be a Core layer (Future_Ideas §9), not more LLM xy invention.

**Shipped:** `layoutlab/runtime/planning/bedroom_basic.py`, tool `plan_layout`
(`agent_tools` 0.5), agent prompt prefers recipes, tests dry-run hard errors = 0 on
reference sizes. Wardrobe on north wall (`front_side=y_min`) because `wardrobe_basic`
only supports Y fronts.

**Not shipped:** multi-variant scoring, kids/office recipes, Accept of DD-016.

------------------------------------------------------------------------

## 2026-07-16 — DD-010 Accepted + Room Model MVP (v0.9.0)

**Shipped:** Editable single-space Room Model (not a room generator). Rectangle footprint,
derived walls with stable ids, openings (door/window), radiator fixed element, Blender
mesh sync, export `rooms[]`, diagnostic + kids-room shell fixture.

**Why:** Hand-modelled Blender rooms cannot be the long-term spatial foundation; capture
and planning need a Core model. Started simple, schema typed for polygon later.

**Not shipped:** polygon footprints, multi-room, analyze room-as-blocker, standalone/scanner.

------------------------------------------------------------------------

## 2026-07-16 — DD-010 Proposed (Room Model)

**Question:** Room as `room_basic` generator vs editable Room Model?

**Answer (proposal):** Room Model (B). Rooms become complex; MVP starts with rectangle
footprint but uses typed `footprint.kind`, first-class walls/openings/fixed elements so
polygons and richer fabric can land later without a second architecture.

**Not implemented:** No code until Accepted. No standalone/scanner. No multi-floor.

**Next:** Alexander reviews DD-010 open questions / proposed defaults.

------------------------------------------------------------------------

## 2026-07-16 — Standalone / Spatial / Capture vision (docs only)

**Why:** End-user product vision needed a coherent story beyond “Blender + JSON clipboard”
without derailing Execution Layer work.

**Changed:** `Future_Ideas.md` §1, §7, §11–§19 (standalone UI, integrated AI journey,
Spatial Project Model, capture/LiDAR, confidence, variants, room→building stages,
explicit non-goals, reserved DD-010…014). Light sync: MDD, Manifest, AI_CONTEXT,
ARCHITECTURE §2.2, documentation_map, object_model scope note, README, HANDOFF.

**Not changed:** Roadmap phases, code, json_protocol, generator_api, clearance DDs.
No DDs created. No standalone/scanner/variant implementation.

------------------------------------------------------------------------

## 2026-07-12 — desk_basic v0.1.0 (generator #3)

**Shipped:** `desk_basic` with `chair_access` clearance (`required` → analyze `error` when blocked).
Third canonical generator validates Parts/Clearance/analyze path without analyzer changes.

**Also:** reference kids room fixture (`tests/fixtures/reference_kids_room_commands.json`),
4 new diagnostics (22 total). Plugin 0.8.1.

**Next (agreed):** more furniture or DD-008 second constraint type — not bridge/viewer without DD.

**Open (2026-07-12, from real room test):** Room-aware analysis (walls as blockers); tiered clearance
groups for bed/desk (foot required, sides preferred, at_least_one OK) vs wardrobe single-zone — needs DD-008 v2.

------------------------------------------------------------------------

## 2026-07-12 — Runtime independence (architectural note, docs only)

**Question:** Must LayoutLab live inside Blender forever?

**Answer:** Blender is the **first runtime adapter**, not the permanent product centre.
Core domain logic should avoid new bpy coupling; export JSON is the cross-runtime artifact.
A future read-only viewer (Three.js/Babylon/Godot host) is possible — **no custom render engine**.
No DD until neutral scene model or second write runtime starts.

------------------------------------------------------------------------

## 2026-07-12 — bed_basic v0.6.0 bed_entry clearances

**Shipped:** `clearances` param array on `bed_basic` — `bed_entry` zones by `side` (foot/head/left/right),
`create_clearance` parts parented to body. Diagnostics: bed entry clear + blocked scenarios.

------------------------------------------------------------------------

## 2026-07-12 — DD-009 Accepted (AI execution boundary)

**Core decision:** AI/planning client owns intent and operation selection; LayoutLab plugin
owns deterministic execution (generators, parts, metadata, clearances, analyze_layout).

**Deferred:** Bridge, Expert Mode, MCP — separate DD(s) required. Default assumptions
documented in DD-009 §Deferred decisions (non-binding until bridge DD).

**Not implemented:** No network service, agent, or direct bpy mode.

------------------------------------------------------------------------

## 2026-07-12 — DD-008 Accepted + analyze_layout (v0.8.0)

**Review decisions:** any AABB overlap > 0; blockers MESH only; orphan clearances included;
JSON-only (no UI button).

**Shipped:** `layout_analysis.py`, `analyze_layout` command, diagnostics for clear/blocked
wardrobe+bed scenario. Wardrobe `front_access` (preferred) → warning when bed blocks.

**Next:** `bed_basic` multi-zone clearances (DD-008 step 5); DD-009 review still pending.

------------------------------------------------------------------------

## 2026-07-12 — Product vision sharpened (documentation only)

**Context:** LayoutLab is long-term not a furniture generator but a system that translates
human room requirements into spatial solutions. Furniture is a means, not the goal.

**Changed:** `Future_Ideas.md` reorganized into 10 themed sections; light touch on Manifest,
MDD §1/2/19, AI_CONTEXT, README, ARCHITECTURE §1, HANDOFF, documentation_map.

**Explicitly not changed:** Roadmap phases, DD-007/008, code, no new solvers/synthesis/accessibility engine.

**Layers documented:** Execution (now) → Planning (later) → Problem solving (long-term).

------------------------------------------------------------------------

## 2026-07-11 — DD-009 documentation sync (review package)

**Goal:** DD-009 remains **Proposed** until Alexander reviews; cross-docs reference it
without implying bridge/expert implementation is approved.

**Changed:** Review gate in DD-009; `json_protocol` Related line; ARCHITECTURE Phase E
row for DD-009 (doc only); HANDOFF + documentation_map + MDD §12 status markers.

**Not done:** No Accepted status; no bridge/agent/network/expert code.

------------------------------------------------------------------------

## 2026-07-11 — DD-009 proposed (AI execution boundary)

**Question:** Why keep the plugin if AI could drive Blender directly?

**Answer:** Plugin owns deterministic HOW — object_id, parts, parenting, regenerate,
clearances, analysis, testable protocol. AI owns WHAT. Direct bpy = future Expert Mode
only. Bridge (local, API-only) = future; not implemented.

------------------------------------------------------------------------

## 2026-07-10 — DD-008 proposed (Constraints & analyze_layout)

**Scope:** Separate from DD-007. v1 constraint type `zone_must_be_clear` (AABB overlap).
`required` → error, `preferred` → warning. JSON command `analyze_layout` returns
`findings` + `summary` — never writes to export.

**Gate:** Review open questions → accept → implement layout_analysis.py → diagnostics
→ bed clearances last.

------------------------------------------------------------------------

## 2026-07-10 — Clearance API v0.7 (DD-007 implementation)

**Shipped:** `layoutlab/api/clearance.py` with `create_clearance()`, JSON command
unified, `wardrobe_basic` v0.5 reference (`front_access`, Main Part local coords).

**Shipped v0.7.1:** Export `layoutlab.clearance` with local + world bounds; diagnostic check.

**Deferred:** DD-008, `analyze_layout`, bed zones.

------------------------------------------------------------------------

## 2026-07-10 — DD-007 / DD-008 split (Clearance vs Constraints)

**Context:** Phase E must not combine “usage zones” and “layout verdicts” in one design.
Early `analyze_layout` on an unstable schema would force rework.

**Decision:**

1. **DD-007 (Accepted):** Clearance Zones — identity (`clearance_id` + per-object
   `clearance_name`), `required`/`preferred`, local + world bounds, shape model direction.
2. **DD-008 (Placeholder):** Constraint engine + `analyze_layout`.
3. Review questions resolved 2026-07-10 (see DD-007 § Resolved decisions).

**Implementation gate:** DD-007 accepted → API → wardrobe → export → diagnostics → DD-008.

------------------------------------------------------------------------

## 2026-07-10 — bed_basic construction stack (v0.5 / plugin 0.6.8)

**Context:** Footboard and headboard were placed from floor level while side rails sat
at `leg_height`, breaking the visual of a closed timber frame. Height parameters were
ambiguous (`headboard_height` read as “from floor”).

**Decision:**

1. **Construction stack** — `BedConstruction` class models floor → posts → frame loop
   → optional headboard rise → mattress/pillows. Only posts reach the floor.
2. **Frame loop** — side rails, footboard, and structural headboard base share
   `frame_bottom_z` and `frame_height`.
3. **`headboard_height`** — documented as decorative rise above frame top (default 3.2).
   Set `0` for frame-only head end.
4. **Remove `footboard_height`** — footboard is always a frame member.

**Future:** Lattenrost, drawers, and loft variants should extend this stack, not add
ad-hoc Z offsets.

------------------------------------------------------------------------

## 2026-07-10 — Part parenting transform fix (v0.6.1)

**Context:** After DD-006 Parts rollout, mattress and wardrobe clearance appeared far
from the body when `params.location` was away from the world origin. Same bug on
multiple generators → API issue, not generator placement formulas.

**Cause:** `_parent_keep_transform` used `child.matrix_world = saved` after parenting.
In Blender this leaves incorrect `matrix_local` in operator/exec contexts — world
position effectively doubles the parent offset.

**Fix:** `parent_preserve_world_transform` sets
`matrix_local = parent.matrix_world.inverted() @ child.matrix_world` explicitly.
Join meshes sorted by location for predictable Main Part origin.

**Regenerate policy (documented):** Rebuild uses stored `params.location`, not current
Main Part transform. No double offset; manual moves may be reset on regenerate.

**Verification:** 4 new diagnostic checks (13 total) for layout at origin vs offset,
follow on move/rotate, clearance adjacency.

------------------------------------------------------------------------

## 2026-07-10 — DD-006: Parts, finalization, Main/Dynamic Parts

**Context:** First generators (`bed_basic`, `wardrobe_basic`) created 10–20 Blender objects
per furniture piece. Good for generator code, bad UX (selection, outliner, moving).

**Rejected:**

- Root Empty as furniture handle — users click Empty, not mesh.
- Selection promotion — fragile in Blender.

**Decision:**

1. **Furniture → Parts → Meshes** — generators still think in many build meshes; API joins
   each Part to one Blender object at `end_part` / `finish`.
2. **Main Part** (`body`) — the object users move; all other Parts parented as children.
3. **Dynamic Parts** (doors, drawers) — stay separate for animation, also parented to Main.
4. **API owns finalization** — no `bpy.ops` in generators; join/metadata/parenting in
   `layoutlab/api/parts.py` for future extensibility (bbox, clearance, thumbnails).

**Migration:** Generator authors must use `begin_part` / `end_part` / `finish`. Bump to
v0.6.0 — breaking for generator code, not for JSON command protocol.

**Verification:** Diagnostics updated (Part count, main parenting, export `part` fields).

------------------------------------------------------------------------

## 2026-07-10 — Generator Developer Guide

**Context:** Specification and API reference existed, but no single practical
tutorial for humans/AI writing generator #2.

**Decision:** Add `docs/how_to_write_generators.md` as the **how-to layer**;
`LayoutLab_Generator_Specification.md` stays normative; `generator_api.md` stays
signatures-only. Updated documentation_map overlap rules and checklist (row 6).

------------------------------------------------------------------------

## 2026-07-10 — Phase D: semantic object model

**Context:** Phase C split complete. Objects were grouped only by name prefix;
export was geometry-only; AI could not update a bed in place.

**Decision:**

1. Engine-level metadata context in `execute_generator()` — all `create_box` /
   `create_label` calls during generator run receive `layoutlab_*` properties
   automatically (generators unchanged).
2. `regenerate` command: resolve by `object_id` or component name, merge param
   overrides, delete by `object_id`, re-run generator with **same UUID**.
3. Export adds structured `layoutlab` block (parallel to flat `custom_properties`).
4. Bump to v0.5.1 (not 0.6) — additive protocol extension, no breaking changes.

**Why not explicit `set_object_metadata()` in generators?**

Less boilerplate; bed_basic needs zero changes; metadata stays consistent.
Optional `component=` kwarg reserved for edge cases.

**Legacy scenes:** Objects without `layoutlab_object_id` still work via
`delete_prefix` + `run_generator`.

**Verification:** Diagnostics extended to 9 checks (metadata + regenerate + export).

------------------------------------------------------------------------

## 2026-07-10 — Documentation maintenance system

**Context:** Phase C complete and diagnostics 8/8. Risk: features ship while docs
(README still said “monolithic”, roadmap phases wrong) drift from code.

**Decision:**

1. Add `docs/documentation_map.md` — single index: purpose, audience, ownership,
   update triggers, overlap rules, quick lookup table.
2. Replace vague “update docs if needed” in `00_READ_THIS_FIRST.md` with a
   **15-row mandatory checklist** after every code change.
3. No separate `how_to_write_generators.md` — `LayoutLab_Generator_Specification.md`
   remains the authoring guide; map documents the split vs `generator_api.md` and
   per-generator `*.md` files to avoid redundancy.

**Why not CONTRIBUTING.md?**

Small team; `00_READ_THIS_FIRST.md` already targets implementers and AI agents.
A second process doc would duplicate the checklist.

**README fixes in same pass:** module structure, roadmap phases A–E, architecture
summary aligned with Phase C.

------------------------------------------------------------------------

## 2026-07-10 — Phase C: monolith split + API/object docs

**Context:** Gate from Phase A required split before scaling. Diagnostics needed
stable re-exports from `layoutlab/__init__.py`.

**Decision:** Split into `api/`, `engine/`, `protocol/`, `plugin/`; browser UI
in `plugin/operators.py` + `panel.py` (no separate `browser.py`). Added
`generator_api.md` and `object_model.md` (A.6/A.7).

**Verification:** Blender 5.0 diagnostics 8/8 PASS after zip install.

------------------------------------------------------------------------

## 2026-07-09 — Phase B: generators in repo, tests, sync

**Context:** Phase A documentation was complete. The monolith still embedded
`bed_basic` as a string and stored runtime generators only in Blender's user
directory — outside git.

**Decision:**

1. Extract `generators/bed_basic.py` as the canonical source.
2. Introduce `layoutlab_util.py` for bpy-free logic testable outside Blender.
3. Sync bundled generators to the user dir on register **only when missing**
   — avoids overwriting user-edited generators in `layoutlab_generators/`.
4. Keep the addon as a single main file for now (Phase C split still pending).

**Update (2026-07-10):** Phase C completed — see entry above.

**Why not load generators directly from repo path at runtime?**

Blender addons often install as a single copied file; the bundled `generators/`
folder must live next to the addon. Sync to the existing user dir reuses the
v0.5 execution path (`exec` from user dir) with minimal behaviour change.

**Next:** Phase C monolith split, or complete A.6/A.7 (`generator_api.md`,
`object_model.md`) before splitting.

------------------------------------------------------------------------

## 2026-07-09 — Phase A: documentation foundation

**Context:** Strong vision docs but no JSON spec, no as-built architecture map,
generators outside version control.

**Outcome:** `json_protocol.md`, `ARCHITECTURE.md`, `README.md`, design
decisions DD-001–005, `units_and_coordinates.md`. Gate passed for structural
code changes.

------------------------------------------------------------------------

## 2026-07-09 — Project bootstrap

**Context:** LayoutLab started as `layoutlab_chatgpt_helper_v05.py` plus vision
documents from ChatGPT/Alexander collaboration.

**Outcome:** Git repository, GitHub remote, initial commit.
