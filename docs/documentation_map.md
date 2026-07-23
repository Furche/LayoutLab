# LayoutLab Documentation Map

Version: 1.1

> **Purpose of this document:** Single index of every documentation file in the
> repository — what it owns, who reads it, and **when it must be updated**.
>
> Use this after **every code change** together with the checklist in
> [00_READ_THIS_FIRST.md](../00_READ_THIS_FIRST.md#documentation-update-checklist).
>
> **Priorities:** [`ROADMAP.md`](ROADMAP.md). **As-built / session:** [`HANDOFF.md`](HANDOFF.md).

**Principle:** Documentation is not optional cleanup. It is part of the deliverable.

------------------------------------------------------------------------

# How to use this map

1. Finish (or plan) the code change.
2. Run the **Documentation Update Checklist** in `00_READ_THIS_FIRST.md`.
3. For each “yes”, open the matching row below and update only what that document owns.
4. Record the change in `CHANGELOG.md`; record reasoning in `DEVLOG.md` when non-obvious.

Do **not** duplicate content across documents. Link instead.

------------------------------------------------------------------------

# Document index

## Entry & onboarding

| Document | Purpose | Audience | Owns (responsibility) | Update when… | Typical changes |
|---|---|---|---|---|---|
| [README.md](../README.md) | First contact: install, quick start, doc index, project overview | Humans (Alexander, contributors), new agents | Installation steps, visible features, quick start, high-level structure diagram, roadmap **summary** (link to ROADMAP) | User-visible behaviour changes; install path changes; new panel features; doc reading order changes | New operator in panel; zip install flow; add generator to “what works” list |
| [00_READ_THIS_FIRST.md](../00_READ_THIS_FIRST.md) | Dev rules, team roles, documentation checklist, binding reading order | Cursor, ChatGPT, all implementers | Team roles, implementation philosophy, **mandatory doc checklist**, refactoring rules, agent reading order | Dev process changes; new team role; checklist items added/removed | New “after every PR” rule; architecture approval workflow |
| [AI_CONTEXT.md](../AI_CONTEXT.md) | Mental model, vocabulary, anti-patterns | AI agents (primary), architects | Concepts (Object, Generator, Component, Constraint), design priorities, “questions to ask” | Core vocabulary changes; philosophy shifts; new anti-patterns | New abstraction layer; changed definition of “Object” |

**Boundary:** README = *what users see*. AI_CONTEXT = *how we think*. Do not put install steps in AI_CONTEXT.

------------------------------------------------------------------------

## Vision & product (stable, change rarely)

| Document | Purpose | Audience | Owns | Update when… | Typical changes |
|---|---|---|---|---|---|
| [LayoutLab_Manifest.md](../LayoutLab_Manifest.md) | Why the project exists — belief and problem statement | Everyone | Mission, problem framing, non-goals at vision level | Fundamental product direction changes (rare) | Pivot from “Blender addon” to broader platform |
| [LayoutLab_Master_Design_Document.md](../LayoutLab_Master_Design_Document.md) | Vision, long-term product-phase summary, product architecture overview | PO, architect, senior contributors | Long-term vision wording; **not** the working priority queue | Major product scope / vision change (rare) | Phase wording clarified; non-goal added |
| [docs/ROADMAP.md](ROADMAP.md) | **Binding product priorities and work order** | Everyone, especially agents | Active / Queued / Refinement / Later / Deferred; links to FC/DD | Priority change; milestone completed; item deferred or activated | Active row moves; WP completed → Implemented |
| [docs/Future_Ideas.md](Future_Ideas.md) | **Ideas backlog** — vision concepts before DD/architecture | PO, architect, team | Problem-first vision, **standalone end-to-end experience**, Spatial Project Model, capture/LiDAR, variants, confidence, runtime independence (§11), bridge — **single file** | Vision sharpened; capture/standalone note; idea promoted to DD | §12–§19 standalone / spatial / capture (2026-07-16) |
| [docs/concepts/README.md](concepts/README.md) | Index and lifecycle for complete Feature Concepts | PO, architect, implementers | Stable `FC-xxx` catalogue between Future Ideas and binding DDs | Concept added, status changed, work package or resulting DD linked | `FC-001` added; status becomes Active |
| [docs/concepts/FC-xxx-*.md](concepts/FC-001-semantic-direct-manipulation-and-multi-room-editing.md) | One coherent cross-cutting product capability | PO, UX, architect, implementers | User flows, domain behaviour, invariants, boundaries, decomposition and stable work-package IDs | Agreed behaviour/scope changes; DD or roadmap item derived; MVP implemented | Direct manipulation semantics; multi-room behaviour; `FC-001/WP-03` |
| [docs/HANDOFF.md](HANDOFF.md) | **Session handoff** — as-built status, versions, gotchas | New chat sessions, Cursor, ChatGPT | Version, DD status table, git path, workflow, technical gotchas; **points to Active ROADMAP entry** | Milestone completed; DD accepted; version bump; as-built change | Version bump; new pitfall |

**Boundary:** Manifest = *why*. MDD = *long-term where*. ROADMAP = *what next*. HANDOFF = *as-built now*.
Neither MDD nor HANDOFF lists the working priority queue — that is `docs/ROADMAP.md`.
Neither lists JSON command fields — that is `json_protocol.md`.

**Concept boundary:** Future Ideas = early or broad possibilities. Feature Concepts = one complete,
stable capability ready to split into DDs and work packages. DDs = binding architectural choices.
Roadmap items reference an `FC-xxx` concept; they do not duplicate it.

------------------------------------------------------------------------

## Technical architecture & contracts

| Document | Purpose | Audience | Owns | Update when… | Typical changes |
|---|---|---|---|---|---|
| [docs/ARCHITECTURE.md](ARCHITECTURE.md) | As-built vs target: layers, modules, migration, **runtime coupling**, Spatial Core guardrails | Implementers, architect | Module map, Core vs Blender Runtime (§2.2), layer boundaries, coupling inventory, future multi-room/variant guardrails | Core/adapter documented; spatial guardrails; module split | §2.2 spatial guardrails (2026-07-16) |
| [docs/json_protocol.md](json_protocol.md) | **Binding** JSON command & export contract | AI agents, implementers, ChatGPT | Command actions, params, export schema, `[IMPLEMENTED]`/`[PLANNED]` markers | New/changed/removed command; export field added; breaking JSON change | `regenerate` command; new export field `layoutlab_params` |
| [docs/generator_api.md](generator_api.md) | Generator-facing API reference (`api` dict) | Generator authors, implementers | Function signatures, behaviour, status per API function | New API function; signature/behaviour change; `bpy` exception scope change | `create_component` added; `create_box` gains parameter |
| [docs/object_model.md](object_model.md) | Semantic object representation in scenes (**current implemented contract**) | Architect, implementers, AI | Custom properties schema, grouping rules, target vs current model | New custom prop; grouping strategy change; export semantic block | `layoutlab_object_id` implemented; regenerate workflow |
| [docs/room_model.md](room_model.md) | Room Model authoring contract (DD-010) | AI, implementers | Room entities, commands, export `rooms[]` | Room Model schema/commands change | openings + radiator MVP |

**Boundary:** ARCHITECTURE = structure, phases, and Core/adapter guardrails. Future_Ideas = full Capture/Standalone/Spatial vision. MDD = product-level vision only. json_protocol = wire format. generator_api = Python functions passed to generators. object_model = **current** meaning on meshes until a Spatial Model DD exists.

------------------------------------------------------------------------

## Generator authoring

| Document | Purpose | Audience | Owns | Update when… | Typical changes |
|---|---|---|---|---|---|
| [LayoutLab_Generator_Specification.md](../LayoutLab_Generator_Specification.md) | **Normativer Standard** — Pflichtregeln, Qualitätsbar | Generator authors, ChatGPT, Cursor | Required metadata, `generate()` contract, do/don’t, fallbacks, naming | New generator rule; metadata constant added; quality requirement | Mandatory return dict from `generate()`; new metadata field |
| [docs/how_to_write_generators.md](how_to_write_generators.md) | **Developer guide** — tutorials, examples, workflows, anti-patterns | Humans and AI writing new generators | How-to content, examples (minimal, stool, bed, loft), debugging workflow, best practices | API usage patterns change; new canonical example; best practice added | Regenerate workflow in debugging; new anti-pattern |
| [layoutlab/generators/README.md](../layoutlab/generators/README.md) | Index of bundled generators + short authoring checklist | Contributors | Table of shipped generators; links to per-generator docs | New bundled generator added/removed | `wardrobe_basic` row added |
| [layoutlab/generators/<name>.md](../layoutlab/generators/bed_basic.md) | Per-generator reference (params, components, examples) | AI, authors, testers | One generator’s params, roles, limits, JSON examples | That generator’s params/behaviour/components change | New `head_side` option; pillow count rule changed |

**Boundary:** Specification = normative rules. **how_to_write_generators** = practical guide (examples, workflow). **generator_api.md** = function signatures. **`<name>.md`** = one generator instance. Do not copy full API signatures into the guide — link instead.

------------------------------------------------------------------------

## Design decisions

| Document | Purpose | Audience | Owns | Update when… | Typical changes |
|---|---|---|---|---|---|
| [docs/design_decisions/README.md](design_decisions/README.md) | Index of all DDs | Everyone | DD table with status and links | New DD created or accepted | DD-009 row (Proposed) |
| [docs/design_decisions/DD-xxx-*.md](design_decisions/DD-001-generators-are-parametric-assets.md) | Single irreversible-ish architecture/product decision | Architect, future implementers | Problem, decision, alternatives, consequences for **one** topic | Significant fork in approach (not every bugfix) | DD-006: Parts and finalization |

**When is a DD required?** API shape chosen between real alternatives; protocol breaking change; generator contract change; UI paradigm change. **Not** for: typo fixes, refactors that preserve behaviour, new generator that follows existing rules.

------------------------------------------------------------------------

## Change history & reasoning

| Document | Purpose | Audience | Owns | Update when… | Typical changes |
|---|---|---|---|---|---|
| [CHANGELOG.md](../CHANGELOG.md) | **What** changed (user/contributor facing) | Everyone | Added/changed/fixed/removed per release and Unreleased | Every merged meaningful change | Monolith split; new command |
| [DEVLOG.md](../DEVLOG.md) | **Why** decisions were made; lessons learned | Team, future self | Dated narrative entries for non-obvious choices | Important technical decision; phase completion; rejected alternative worth remembering | Why sync-on-register not overwrite; Phase C gate passed |

**Boundary:** CHANGELOG = facts. DEVLOG = reasoning. Do not put essays in CHANGELOG or release notes in DEVLOG.

------------------------------------------------------------------------

## Code-adjacent (document in README / ARCHITECTURE, not separate guides)

| Location | Documented in | Update when… |
|---|---|---|
| `scripts/build_addon_zip.py` | README Installation | Addon package layout or version source changes |
| `scripts/hooks/post-commit` | README Installation | Hook behaviour changes |
| `tests/test_*.py` | README “Running tests”; ARCHITECTURE test status | New test suite or bpy-free test scope |
| `layoutlab/diagnostics.py` | README Diagnostics | New diagnostic check |

------------------------------------------------------------------------

# Overlap rules (avoid drift)

| Topic | Authoritative document | Others may only… |
|---|---|---|
| JSON commands | `json_protocol.md` | Link; one-line summary in README |
| API functions for generators | `generator_api.md` | Spec may reference by name, not re-list signatures |
| Module / layer structure | `ARCHITECTURE.md` | README: one diagram + link |
| Object properties on meshes | `object_model.md` | ARCHITECTURE: summary table + link |
| Generator authoring rules | `LayoutLab_Generator_Specification.md` | how_to_write_generators: workflow/examples only |
| Generator how-to & examples | `docs/how_to_write_generators.md` | Spec: rules only; API: signatures only |
| Roadmap priorities / work order | `docs/ROADMAP.md` | README: short table + link; MDD §17: long-term phase summary only; HANDOFF: Active link only |
| Cross-cutting feature behaviour | `docs/concepts/FC-xxx-*.md` | Future Ideas / DD / roadmap: summary + link only |
| Migration phase status | `ARCHITECTURE.md` §9 | MDD: high-level only |
| Session as-built / versions / gotchas | `docs/HANDOFF.md` | ROADMAP: Active id only |

If two documents disagree, **stop** — fix the doc or the code before continuing.

------------------------------------------------------------------------

# Quick lookup: “I changed X → update Y”

| Code change | Documents to check (minimum) |
|---|---|
| New JSON command | `json_protocol.md`, `CHANGELOG.md`, maybe `ARCHITECTURE.md`, maybe DD |
| `analyze_layout` / layout analysis | `layout_analysis.py`, `json_protocol.md`, `diagnostics.py`, `CHANGELOG.md` |
| New `api` function | `generator_api.md`, `docs/how_to_write_generators.md`, `LayoutLab_Generator_Specification.md` if rule change, `CHANGELOG.md` |
| New generator | `layoutlab/generators/<name>.py`, `<name>.md`, `generators/README.md`, `CHANGELOG.md` |
| Module refactor | `ARCHITECTURE.md`, `CHANGELOG.md`, `DEVLOG.md` if structural |
| Panel / operator UI | `README.md` (if user-visible), `CHANGELOG.md` |
| Custom property on mesh | `object_model.md`, `json_protocol.md` (export), `CHANGELOG.md` |
| Architecture alternative chosen | New DD + `ARCHITECTURE.md` + `DEVLOG.md` |
| Cross-cutting feature concept agreed | `docs/concepts/FC-xxx-*.md`, concepts index, `docs/ROADMAP.md`, `HANDOFF.md` (Active link) |
| Priority / Active work changed | `docs/ROADMAP.md`, then `HANDOFF.md` Active link, README summary if visible |
| Phase gate completed | `ARCHITECTURE.md`, `docs/ROADMAP.md`, `DEVLOG.md` |

------------------------------------------------------------------------

# Maintenance

This map itself must be updated when:

- A new documentation file is added to the repository
- A document’s responsibility shifts
- A duplicate guide is merged or removed

Owner: whoever adds the file — update this map in the **same commit**.
