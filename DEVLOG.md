# Devlog

Why important decisions were made — complement to `CHANGELOG.md` (what changed).

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
