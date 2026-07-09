# Changelog

All notable changes to LayoutLab are documented here.

Format based on [Keep a Changelog](https://keepachangelog.com/).

------------------------------------------------------------------------

## [Unreleased]

### Added

- `docs/how_to_write_generators.md` — generator developer guide (examples, best practices, debugging)
- Panel: **Paste Generator** — save clipboard script as generator (name from `GENERATOR_NAME`, overwrites if exists)
- `layoutlab/generators/wardrobe_basic.py` + `wardrobe_basic.md` — second bundled generator
- `docs/Future_Ideas.md` — ideas backlog before architecture/implementation

### Changed

- Generator Library panel simplified: browser + paste only (workbench moved to browser popup)

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

[Unreleased]: https://github.com/Furche/LayoutLab/compare/v0.5.1...HEAD
[0.5.1]: https://github.com/Furche/LayoutLab/compare/v0.5.0...v0.5.1
[0.5.0]: https://github.com/Furche/LayoutLab/releases/tag/v0.5.0
