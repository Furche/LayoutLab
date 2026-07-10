# Changelog

All notable changes to LayoutLab are documented here.

Format based on [Keep a Changelog](https://keepachangelog.com/).

------------------------------------------------------------------------

## [Unreleased]

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
