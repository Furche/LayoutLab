# Changelog

All notable changes to LayoutLab are documented here.

Format based on [Keep a Changelog](https://keepachangelog.com/).

------------------------------------------------------------------------

## [Unreleased]

### Changed

- **Docs roadmap sync:** HANDOFF user priority, Future_Ideas §19, and agent tool contract ordered for post–DD-017 staging (candidates → evaluation schema → shortlist)
- **DD-017 Accepted:** collaborative planning and contextual candidate evaluation contract locked; DD-011 amended to Core functional shortlist → AI recommendation → User selection, and DD-015 clarified that aesthetics remains outside deterministic Core metrics
- **DD-011 Accepted:** Planner foundation locked — recipe = goal-oriented strategy; expand → evaluate → select; v1 via `plan_layout` `mode: "candidates"` (2–4 bedroom strategies first)
- **DD-015 / DD-016 Accepted:** soft metrics + tradeoffs and deterministic layout recipes (`plan_layout` / `bedroom_basic`) locked as architecture
- **agent.py bedroom heuristics → planning/** (`0.10.21`): intent parsing / counts / sizes live in `planning/intent.py`; placement fixes / fingerprints in `planning/placement.py`; `agent.py` keeps thin underscored re-exports for tests

### Added

- **DD-017:** collaborative planning and contextual candidate evaluation — semantic allowlists, capability/role context, validity and anti-compensation, plus optional experimental aesthetics ([DD-017](docs/design_decisions/DD-017-collaborative-planning-and-contextual-evaluation.md))
- **DD-011 Proposed:** Layout variants / Planning v1 — a **recipe** is a goal-oriented planning strategy (not only a room type); Core expands candidates, evaluates with analyze + soft metrics, selects winner ([DD-011](docs/design_decisions/DD-011-layout-variants-and-comparison.md))

### Fixed

- **LLM crash → kids demo:** `location` as dict no longer raises `unhashable type: 'slice'`; bedroom intents fall back to `plan_layout` (not kids-room demo); light `agent_state` persists requirements for „nochmal“ retries

### Added

- **Mini-Requirements → `plan_layout`:** LLM fills structured `requirements` (room size, door/window counts, furniture, bed size); Core maps to recipe geometry; proposal carries `requirements`
- **DD-016 Planning recipes (`agent_tools` 0.5):** tool `plan_layout` + recipe `bedroom_basic` — Core places standard bedroom furniture deterministically; agent prefers recipes over free xy; dry-run target = 0 hard errors on 4×3.5 / 4×4
- **Layout sketch (`agent_tools` 0.4):** `get_layout_sketch` top-down ASCII + `bounds_xy`; included in dry-run, scene seed, quality preview, and session log — spatial eyes for the agent without the 3D viewport

### Fixed

- **Windows vs door wall:** default window placement skips the door wall (avoids east door+window overlap)
- **plan_layout baseline:** after `plan_layout` in a turn, Core re-applies the recipe (reconciled with room size / window_count / bed size from the conversation) so the LLM cannot ship duplicate/overlapping openings
- **Bedroom windows:** `window_count` places non-overlapping windows (south/north first)
- **Bed size requests:** parse `120x200` as Breite×Länge, apply axis-correct dims; honest noop when already that size; no false „Bett an die Wand“ spam when the recipe bed already hugs the wall
- **Bed orientation:** normal 120×200 beds with head on south/north use `length=1.2` (along wall) and `width=2.0` (into room); recipe + wall-snap no longer put the 2 m side along the wall
- **Clearance zones in sketch:** `+` preferred / `*` required painted into ASCII + structured `rooms[].clearances` (default on)
- **Session reset on Viewer refresh:** `POST /v1/session/reset` archives the log and clears the Core scene; Viewer calls it on full page load; `LAST_SESSION.md` header shows `core_version`
- **Viewer Core version badge:** top bar shows live Core version from `/health` (or `offline`)
- **Placement quality:** beds snap to a wall with `head_side`; „besser“-requests force a real rearrange (not identical coords); desks nudged out of east-door strips
- **Observe + hard replan:** observation answers with analysis + layout sketch (overlap callouts); hard clearance errors trigger a replan; desk/bed AABB overlaps are separated; bed length/width normalized along the wall
- **Agent-2 tools:** `validate_commands` + `dry_run_commands` (session clone; live session unchanged); automatic scene seed (`get_scene_summary` + `list_generators`) on each LLM agent turn (`agent_tools` 0.2)
- **DD-015 Soft metrics + tradeoffs (Proposed):** packing density + opening-access findings; dry-run `soft_summary`; agent quality preview; Viewer Apply confirm on hard/soft/risks (`agent_tools` 0.3)
- **Observation queries + solid wall hits:** scene-status questions return no commands; `solid_wall_penetration` is a non-negotiable error and blocks Apply
- **Viewer chat actions:** slim proposal bar above the input (`View commands` / `Apply` / `Discard`); JSON opens in a dialog instead of shrinking the chat log

### Changed

- **Viewer layout:** left panel is chat-only (⚙ settings bottom-left); Scene/Selection/Analysis/Display/Shortcuts live in a collapsed inspector rail on the right edge

### Fixed

- **Command shape (Apply):** `delete_collection_objects` accepts `params.collection`; flat `run_generator` keys are folded into `params` (LLM often omitted top-level `collection` / nested params — Apply failed and furniture ignored placement/`head_side`)
- **Agent placement:** when the user mentions bed head/Kopfende, force `head_side` toward the nearest wall; nudge wardrobe away from an east door; one soft-metric replan when dry-run still warns without `expected_risks`
- **Agent incomplete proposals:** after a turn, Core repairs proposals that claim room+door+bed but only emit `create_room` (forces a second finalize with missing `add_opening` / `bed_basic`)
- **Agent window completeness:** repair now requires `kind=window` openings by requested count (a door alone no longer counts as windows)
- **Viewer chat Enter:** Enter submits the prompt; Shift+Enter inserts a newline

### Added

- **DD-014 Phase B (room write):** Accepted locks — local Python Core HTTP service, Room Model commands only, headless viewer export (no `bpy`); Blender remains generator QA reference ([DD-014](docs/design_decisions/DD-014-standalone-runtime-path.md))
- **Headless room session:** `layoutlab/runtime/session.py` — in-memory Room Model + `export_viewer_scene`
- **Core server:** `server/` — `GET /health`, `POST /v1/commands`, CORS for Vite; `python -m server`
- **Viewer write:** Empty test room (Core) + paste commands → Core URL (`http://127.0.0.1:8765`)
- **DD-014 Phase B2 (generators):** headless `run_generator` via pure mesh store; desk/bed/wardrobe without `bpy`; viewer **Furnished test room (Core)**
- **Headless analyze_layout:** Core export embeds live clearance findings (walls/fixed + furniture); `analyze_layout` command on session
- **Thin AI chat (pre-DD-012):** `POST /v1/chat` proposes commands only; viewer Apply → `/v1/commands`. Demo intents without API key; optional OpenAI-compatible LLM via env
- **Agent tools 0.1:** `docs/agent_tool_contract.md`; `POST /v1/tools/{name}` read tools; `POST /v1/agent/turn` tool-calling agent → structured proposal; viewer uses agent turn
- **DD-014 Accepted — Phase A only:** web export viewer path locked (Three.js/Babylon; show findings); Phase B direction only ([DD-014](docs/design_decisions/DD-014-standalone-runtime-path.md))
- **Viewer-minimum export contract** in `json_protocol.md` §6.4 (`viewer_schema` 0.1.0)
- **Fixture:** `tests/fixtures/reference_kids_room_export.json` — kids room + bed/desk for Phase A viewer
- **Phase A viewer scaffold:** `viewer/` — Vite + Three.js read-only export viewer (fixture + file open, clearances/openings, analysis panel)

### Added

- **Plugin 0.10.4:** scene export emits `viewer_schema` + per-object `viewer` hints (wall quads / clearance wires); walls stamp `layoutlab_viewer_corners`
- **Findings demo fixture:** `tests/fixtures/reference_kids_room_export_findings.json` (1 error + 1 warning) — loadable in viewer
- **Viewer paste:** Paste Blender scene-export JSON from clipboard (button + ⌘V/Ctrl+V, dialog fallback)

### Fixed

- **Quick Test units (v0.10.5):** browser defaults were still pre-metric (`12`/`20`); now meters (`1.2`×`2.0` bed, desk/wardrobe profiles). Stale scene values auto-reset when opening the browser.

### Fixed

- **Viewer placement / desk mesh (v0.10.6):** paste used object `location` as AABB corner (wrong for parented Parts / non-corner origins). Now uses `world_bbox_corners`; furniture exports `viewer.mesh` so desk legs/top match Blender. Labels skipped. `viewer_schema` → `0.1.1`.

### Added

- **Test room buttons (v0.10.7):** Sidebar → Empty / Furnished kids-room (clears `layoutlab_room`, builds reference shell ± bed/desk)

### Added

- **Export embeds analysis (v0.10.8):** `Copy Scene` / `Copy Selected` include live `analyze_layout` under `analysis` for the Phase A viewer

### Changed

- **Viewer polish:** Fit/Iso/Top/Front/Side camera, click-to-select, finding click highlights, drag-drop JSON, clearer paste errors, Examples menu

### Fixed (prior)

- **`analyze_layout` summary:** count `error`/`warning` into `errors`/`warnings` (was stuck at 0)

### Changed (prior)

- Plugin version **0.10.3**

### Added (prior)

- **`analyze_layout` room-aware (v0.10.2):** `room_wall` / `room_fixed` count as blockers; `room_floor` / `room_opening` excluded; overlap entries include `role`; diagnostic `analyze_layout_room_wall`

### Added (prior)

- **Reference fixture:** `reference_kids_room_commands.json` — room shell + bed + desk in meters inside `KIDS_ROOM`

### Added (prior)

- **Constructive wall openings (v0.10.1):** walls split into inward panels around doors/windows (no Boolean); opening wires kept as markers

### Changed (prior)

- Plugin version **0.10.1**
- Opening/fixed defaults in meters (`door` 0.9×2.0, `window` sill 0.8, radiator 0.75)

### Changed (prior)

- **Native Blender units (v0.10.0, breaking):** JSON/generators use scene Blender units directly (Metric default: 1 unit = 1 m). Removed 10 cm convention and the v0.9.3 conversion layer.
- Generator defaults scaled to meters: `bed_basic` 0.7.0, `wardrobe_basic` 0.7.0, `desk_basic` 0.2.0
- Room shell / reference fixtures updated to meter sizes

### Changed (prior)

- Plugin version **0.9.3** — temporary LL↔BU conversion (superseded by 0.10.0)

### Fixed (prior)

- **`create_quad` / room walls:** removed `Mesh.calc_normals()` (removed in Blender 4.x) — walls/openings failed after floor only

### Changed (prior)

- Plugin version **0.9.2**

### Added (prior)

- **Room walls:** inward-facing single-sided planes (backface culling) — see-through from outside
- Default room origin **`[0, 0, 0]`**; kids-room shell fixture updated

### Changed (prior)

- Plugin version **0.9.1**

### Added (prior)

- **DD-010 Accepted + Room Model MVP (v0.9.0):** Core `layoutlab/core/room.py`, Blender sync, JSON commands (`create_room`, openings, fixed elements), export `rooms[]`, diagnostics `room_model_create`, fixture `reference_kids_room_shell_commands.json`

### Changed (prior)

- **Reference fixture:** bed + desk only in real kids room (no duplicate wardrobe — IKEA `kleiderschrank` exists); desk clear of kleiderschrank bbox
- Plugin version **0.8.2**

### Added (prior)
- **Diagnostics:** `desk_clearance_layout`, `analyze_layout_desk_clear`, `analyze_layout_desk_blocked` (22 checks total)
- **Fixture:** `tests/fixtures/reference_kids_room_commands.json` — bed + wardrobe + desk reference layout
- **Unit tests:** `tests/test_desk_basic.py` — chair zone geometry + fixture validation

### Changed (prior)

- Plugin version **0.8.1**

### Changed (prior)

- **Runtime independence (docs):** LayoutLab Core vs Blender Runtime — Future_Ideas §11, ARCHITECTURE §2.2; no implementation
- **bed_basic v0.6.0:** optional `clearances` — `bed_entry` zones; diagnostics bed clear/blocked (18 checks)
- **DD-009 Accepted** (2026-07-12) — AI plans WHAT, plugin executes HOW; bridge/expert deferred to future DDs

### Fixed

- **Diagnostics:** analyze_layout checks now `delete_prefix(DIAG_PREFIX)` for isolated collection; blocked check filters by `furniture_name`
- **analyze_layout:** clearance wire meshes excluded from blocker list (usage zones, not obstacles)
- **Diagnostics:** `from ..api` / `from ..protocol` in `diagnostics.py` → `from .api` / `from .protocol` (7 checks failed with relative import error)

### Added

- **v0.8.0 — `analyze_layout` (DD-008):** `layoutlab/protocol/layout_analysis.py`, `zone_must_be_clear` AABB overlap, JSON command wired in `commands.py`
- **Diagnostics:** `analyze_layout_clear`, `analyze_layout_blocked` (16 checks total)
- **Unit tests:** `aabb_intersects`, `requirement_to_severity` in `tests/test_layout_analysis.py`
- **DD-008 Accepted** with resolved review decisions (2026-07-12)

### Added (prior)

- **DD-009 proposed:** AI execution boundary — AI plans, plugin executes; bridge & expert mode as future ideas only

### Added (prior)

- **DD-008 proposed:** Constraint engine + `analyze_layout` — reads DD-007 clearances, emits findings (errors/warnings)

------------------------------------------------------------------------

------------------------------------------------------------------------

## [0.8.0] — 2026-07-12

### Added

- JSON command `analyze_layout` — constraint findings from clearance zones (DD-008)
- `layoutlab/protocol/layout_analysis.py` — `zone_must_be_clear` v1
- Diagnostic checks `analyze_layout_clear`, `analyze_layout_blocked` (16 checks total)
- Pure-Python helpers `aabb_intersects`, `requirement_to_severity` in `util.py`

### Changed

- Plugin version **0.8.0**
- DD-008 status → **Accepted**

------------------------------------------------------------------------

## [0.7.1] — 2026-07-10

### Added

- Scene export: structured `layoutlab.clearance` block with `local_bounds`, `world_bounds`, `local_transform`, `clearance_id`, `clearance_name`, `requirement`
- Diagnostic check `clearance_export` (14 checks total)

### Changed

- Plugin version **0.7.1**

------------------------------------------------------------------------

## [0.7.0] — 2026-07-10

### Added

- **`api["create_clearance"]`** (DD-007): `clearance_id`, `clearance_name`, `requirement` (`required`/`preferred`), `local_transform` in params; `local_location` relative to Main Part
- Unit tests for clearance requirement validation and local/world resolution

### Changed

- **`wardrobe_basic` v0.5.0:** uses `create_clearance`; Part `clearance_front_access` with `front_access` zone
- Diagnostics: wardrobe clearance metadata checks
- Plugin version **0.7.0**

------------------------------------------------------------------------

## [0.6.8] — 2026-07-10

### Changed

- **`bed_basic` v0.5.0 — construction model:** only posts touch the floor; footboard and structural headboard base join the raised frame loop at `frame_bottom_z`; decorative headboard rises above `frame_top_z`
- **`headboard_height`** now means rise above frame top (default `3.2`), not height from floor; **`footboard_height` removed** (footboard height = `frame_height`)
- Generator code refactored with `BedConstruction` stack class
- Documentation: `bed_basic.md`, `json_protocol.md`, `units_and_coordinates.md`, `object_model.md`, `how_to_write_generators.md`

### Breaking

- Existing JSON using pre-0.5 `headboard_height` / `footboard_height` semantics should be reviewed

------------------------------------------------------------------------

## [0.6.7] — 2026-07-10

### Fixed

- `bed_basic`: two pillows divide mattress **length** (X) at head/foot, not mattress width (Y) — fixes second pillow hanging outside the frame on wide beds

### Changed

- `bed_basic` v0.4.2
- Plugin version **0.6.7**

------------------------------------------------------------------------

## [0.6.6] — 2026-07-10

### Fixed

- Part parenting uses ``obj.location`` (not stale ``matrix_world`` inside ``exec()``) for child offsets — fixes mattress on floor and clearance through wardrobe body

### Changed

- Plugin version **0.6.6**

------------------------------------------------------------------------

## [0.6.5] — 2026-07-10

### Fixed

- Part parenting uses frozen `world_at_finalize` matrices for relative offsets (not live `matrix_world` during `exec()`) — fixes mattress/pillows/clearance at non-zero Quick Test locations
- Wardrobe clearance wire box uses full wardrobe height again (was 1.0)

### Changed

- Quick Test default location `(0, 0, 0)` instead of `(68.3, 197.7, 0)`
- `bed_basic` v0.4.1, `wardrobe_basic` v0.4.2
- Plugin version **0.6.5**

------------------------------------------------------------------------

## [0.6.4] — 2026-07-10

### Fixed

- Part parenting uses translation offset (`child.location = world − parent`) for axis-aligned furniture — fixes mattress/pillow appearing at world coords as local coords
- Wardrobe clearance: visual height 1.0 (was 0.1), `show_in_front` for wireframe visibility
- Bed mattress aligned to frame inner edge (`rail` inset, not separate `inset` param)

### Changed

- `bed_basic` / `wardrobe_basic` v0.4
- Diagnostics detect `child.location` looking like world coordinates
- Plugin version **0.6.4**

------------------------------------------------------------------------

## [0.6.3] — 2026-07-10

### Fixed

- Part parenting stores world matrix at `end_part()` and restores it explicitly before setting `matrix_local` — fixes mattress offset while clearance already worked
- Parenting runs once in the engine (`execute_generator`), not from generators calling `api["finish"]()` early

### Changed

- `bed_basic` / `wardrobe_basic` v0.3 — removed redundant `api["finish"]()` (engine finalizes)
- Diagnostics: absolute mattress world-position check at offset location
- Plugin version **0.6.3**

------------------------------------------------------------------------

## [0.6.2] — 2026-07-10

### Fixed

- Part parenting uses Blender `parent_set(keep_transform=True)` so child Parts keep world position when the addon runs inside operators/`exec()` (Blender 5.0)

------------------------------------------------------------------------

## [0.6.1] — 2026-07-10

### Fixed

- Child Part parenting double-translation when `params.location` far from origin — explicit `matrix_local` in `layoutlab/api/transforms.py`
- Mattress, clearance, pillows, labels now stay at generator-intended world positions after `finish()`

### Added

- Transform diagnostic checks (bed layout at origin vs offset, main-part move/rotate follow, wardrobe clearance adjacency, regenerate layout policy)
- `tests/test_transforms.py` — translation comparison helper tests

### Changed

- Join sorts build meshes by location before `object.join()` for stable Main Part origin
- Documentation: coordinate model in `units_and_coordinates.md`, DD-006 amendment, generator specs
- Plugin version **0.6.1**; diagnostics now **13 checks**

------------------------------------------------------------------------

## [0.6.0] — 2026-07-10

### Added

- **Parts architecture:** `begin_part`, `end_part`, `finish` in generator API
- `layoutlab/api/parts.py` — Part session, mesh join, parenting to Main Part
- `layoutlab_part`, `layoutlab_part_type` metadata and export fields
- `docs/design_decisions/DD-006-parts-and-finalization.md`

### Changed

- `bed_basic` and `wardrobe_basic` migrated to Parts API (`GENERATOR_VERSION` 0.2)
- Plugin version **0.6.0**; export `layoutlab_version` from `bl_info`

### Removed

- Per-mesh Blender objects for static generator components (replaced by joined Parts)

------------------------------------------------------------------------

## [0.5.1] — 2026-07-10

### Added

- Semantic object metadata on generator meshes (`layoutlab_object_id`, `layoutlab_generator`, `layoutlab_params`, `layoutlab_component`)
- `regenerate` JSON command — rebuild logical object with param overrides, same object_id
- `layoutlab` block in scene export for objects with identity metadata
- `docs/documentation_map.md` — documentation maintenance index
- Mandatory **Documentation Update Checklist** in `00_READ_THIS_FIRST.md`
- `docs/generator_api.md`, `docs/object_model.md`
- `layoutlab/api/metadata.py`, `layoutlab/protocol/semantic.py`
- Diagnostics: metadata, regenerate, export block checks (9 checks total)
- Unit tests: `merge_generator_params`, `component_suffix_from_name`

### Fixed

- JSON command parsing for bare array payloads (list form) — previously raised `AttributeError`

### Changed

- Plugin version 0.5.1; export `layoutlab_version` 0.5.1
- `execute_generator` returns `object_id` and tags all API-created components
- Module split: `layoutlab/api/`, `engine/`, `protocol/`, `plugin/` (Phase C)
- `00_READ_THIS_FIRST.md`, `AI_CONTEXT.md`, `README.md`, `docs/ARCHITECTURE.md` updated
- Phase C and Phase D marked complete in architecture docs

------------------------------------------------------------------------

## [0.5.0] — 2026-07-09

### Added

- Initial v0.5 prototype (`layoutlab_chatgpt_helper_v05.py`)
- JSON command exchange and scene export
- Generator browser and `bed_basic` generator
- Project vision and architecture documentation
- `docs/json_protocol.md`, `docs/ARCHITECTURE.md`, `docs/units_and_coordinates.md`
- Design decisions DD-001 through DD-005
- `AI_CONTEXT.md`, `README.md`

[Unreleased]: https://github.com/Furche/LayoutLab/compare/v0.6.4...HEAD
[0.6.4]: https://github.com/Furche/LayoutLab/compare/v0.6.3...v0.6.4
[0.6.3]: https://github.com/Furche/LayoutLab/compare/v0.6.2...v0.6.3
[0.6.2]: https://github.com/Furche/LayoutLab/compare/v0.6.1...v0.6.2
[0.6.1]: https://github.com/Furche/LayoutLab/compare/v0.6.0...v0.6.1
[0.6.0]: https://github.com/Furche/LayoutLab/compare/v0.5.1...v0.6.0
[0.5.1]: https://github.com/Furche/LayoutLab/compare/v0.5.0...v0.5.1
[0.5.0]: https://github.com/Furche/LayoutLab/releases/tag/v0.5.0
