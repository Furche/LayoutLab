# LayoutLab Documentation Map

Version: 1.0

> **Purpose of this document:** Single index of every documentation file in the
> repository — what it owns, who reads it, and **when it must be updated**.
>
> Use this after **every code change** together with the checklist in
> [00_READ_THIS_FIRST.md](../00_READ_THIS_FIRST.md#documentation-update-checklist).

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
| [README.md](../README.md) | First contact: install, quick start, doc index, project overview | Humans (Alexander, contributors), new agents | Installation steps, visible features, quick start, high-level structure diagram, roadmap **summary** | User-visible behaviour changes; install path changes; new panel features; doc reading order changes | New operator in panel; zip install flow; add generator to “what works” list |
| [00_READ_THIS_FIRST.md](../00_READ_THIS_FIRST.md) | Dev rules, team roles, documentation checklist | Cursor, ChatGPT, all implementers | Team roles, implementation philosophy, **mandatory doc checklist**, refactoring rules | Dev process changes; new team role; checklist items added/removed | New “after every PR” rule; architecture approval workflow |
| [AI_CONTEXT.md](../AI_CONTEXT.md) | Mental model, vocabulary, anti-patterns | AI agents (primary), architects | Concepts (Object, Generator, Component, Constraint), design priorities, “questions to ask” | Core vocabulary changes; philosophy shifts; new anti-patterns | New abstraction layer; changed definition of “Object” |

**Boundary:** README = *what users see*. AI_CONTEXT = *how we think*. Do not put install steps in AI_CONTEXT.

------------------------------------------------------------------------

## Vision & product (stable, change rarely)

| Document | Purpose | Audience | Owns | Update when… | Typical changes |
|---|---|---|---|---|---|
| [LayoutLab_Manifest.md](../LayoutLab_Manifest.md) | Why the project exists — belief and problem statement | Everyone | Mission, problem framing, non-goals at vision level | Fundamental product direction changes (rare) | Pivot from “Blender addon” to broader platform |
| [LayoutLab_Master_Design_Document.md](../LayoutLab_Master_Design_Document.md) | Vision, roadmap phases, product architecture overview | PO, architect, senior contributors | Long-term roadmap, phase definitions, product-level architecture | Roadmap phase completed/added; major product scope change | Phase C marked complete; Phase D scope defined |
| [docs/Future_Ideas.md](Future_Ideas.md) | **Ideas backlog** — vision concepts before DD/architecture | PO, architect, team | Semantic objects, clearance, constraints, evaluation — not commitments | New idea matures enough to document; idea promoted to DD (remove or mark done) | Walkway analysis concept added |
| [docs/HANDOFF.md](HANDOFF.md) | **Session handoff** — current status, next steps, pitfalls for new agents | New chat sessions, Cursor, ChatGPT | Version, DD status (incl. Proposed awaiting review), git path, workflow, next steps, technical gotchas | Milestone completed; DD accepted; version bump; next-steps change; DD review package synced | DD-009 Proposed, review pending |

**Boundary:** Manifest = *why*. MDD = *where we are going*. Neither lists JSON command fields — that is `json_protocol.md`.

------------------------------------------------------------------------

## Technical architecture & contracts

| Document | Purpose | Audience | Owns | Update when… | Typical changes |
|---|---|---|---|---|---|
| [docs/ARCHITECTURE.md](ARCHITECTURE.md) | As-built vs target: layers, modules, migration plan, exceptions | Implementers, architect | Module map, layer boundaries, migration phase status, deliberate v0.5 exceptions | Module split/merge; new layer; phase gate passed; exception resolved | Phase D started; new `layoutlab/` subpackage |
| [docs/json_protocol.md](json_protocol.md) | **Binding** JSON command & export contract | AI agents, implementers, ChatGPT | Command actions, params, export schema, `[IMPLEMENTED]`/`[PLANNED]` markers | New/changed/removed command; export field added; breaking JSON change | `regenerate` command; new export field `layoutlab_params` |
| [docs/generator_api.md](generator_api.md) | Generator-facing API reference (`api` dict) | Generator authors, implementers | Function signatures, behaviour, status per API function | New API function; signature/behaviour change; `bpy` exception scope change | `create_component` added; `create_box` gains parameter |
| [docs/object_model.md](object_model.md) | Semantic object representation in scenes | Architect, implementers, AI | Custom properties schema, grouping rules, target vs current model | New custom prop; grouping strategy change; export semantic block | `layoutlab_object_id` implemented; regenerate workflow |
| [docs/units_and_coordinates.md](units_and_coordinates.md) | Scale, axes, bed/placement conventions | AI, generator authors | Unit scale (1 ≈ 10 cm), axis meanings, reference room conventions | Scale convention changes; axis documentation for new object types | Wardrobe depth axis documented |

**Boundary:** ARCHITECTURE = structure and phases. json_protocol = wire format. generator_api = Python functions passed to generators. object_model = meaning on meshes.

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
| Roadmap phases | `LayoutLab_Master_Design_Document.md` | README: short table + link |
| Migration phase status | `ARCHITECTURE.md` §9 | MDD: high-level only |

If two documents disagree, **stop** — fix the doc or the code before continuing.

------------------------------------------------------------------------

# Quick lookup: “I changed X → update Y”

| Code change | Documents to check (minimum) |
|---|---|
| New JSON command | `json_protocol.md`, `CHANGELOG.md`, maybe `ARCHITECTURE.md`, maybe DD |
| New `api` function | `generator_api.md`, `docs/how_to_write_generators.md`, `LayoutLab_Generator_Specification.md` if rule change, `CHANGELOG.md` |
| New generator | `layoutlab/generators/<name>.py`, `<name>.md`, `generators/README.md`, `CHANGELOG.md` |
| Module refactor | `ARCHITECTURE.md`, `CHANGELOG.md`, `DEVLOG.md` if structural |
| Panel / operator UI | `README.md` (if user-visible), `CHANGELOG.md` |
| Custom property on mesh | `object_model.md`, `json_protocol.md` (export), `CHANGELOG.md` |
| Architecture alternative chosen | New DD + `ARCHITECTURE.md` + `DEVLOG.md` |
| Phase gate completed | `ARCHITECTURE.md`, `README.md` roadmap, `DEVLOG.md` |

------------------------------------------------------------------------

# Maintenance

This map itself must be updated when:

- A new documentation file is added to the repository
- A document’s responsibility shifts
- A duplicate guide is merged or removed

Owner: whoever adds the file — update this map in the **same commit**.
