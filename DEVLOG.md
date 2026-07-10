# Devlog

Why important decisions were made — complement to `CHANGELOG.md` (what changed).

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
