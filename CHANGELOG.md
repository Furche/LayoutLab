# Changelog

All notable changes to LayoutLab are documented here.

Format based on [Keep a Changelog](https://keepachangelog.com/).

------------------------------------------------------------------------

## [Unreleased]

### Added

- `docs/documentation_map.md` — index of all docs: purpose, audience, update triggers, overlap rules
- Mandatory **Documentation Update Checklist** in `00_READ_THIS_FIRST.md`
- `docs/generator_api.md` — Generator API reference
- `docs/object_model.md` — semantic object model (current + target)
- `generators/bed_basic.py` — version-controlled parametric bed generator
- `layoutlab_util.py` — pure-Python helpers (metadata inference, JSON parsing)
- `tests/test_layoutlab_util.py` — unit tests for registry and protocol parsing
- Bundled generator sync on addon register (copies missing generators to user dir)
- `CHANGELOG.md` and `DEVLOG.md`
- `layoutlab/diagnostics.py` — console diagnostic checks with shareable report
- Module split: `layoutlab/api/`, `engine/`, `protocol/`, `plugin/`

### Fixed

- JSON command parsing for bare array payloads (list form) — previously raised `AttributeError`

### Changed

- `00_READ_THIS_FIRST.md`, `AI_CONTEXT.md`, `README.md` — doc maintenance process and outdated structure/roadmap
- `scripts/build_addon_zip.py` — builds `dist/layoutlab-<version>.zip` for Blender Install…
- Blender addon packaged as `layoutlab/` folder (`__init__.py`)
- `layoutlab_util.py` → `layoutlab/util.py`
- `generators/` → `layoutlab/generators/`
- `docs/ARCHITECTURE.md` — Phase B/C complete, module map, A.6/A.7 implemented

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

[Unreleased]: https://github.com/Furche/LayoutLab/compare/v0.5.0...HEAD
[0.5.0]: https://github.com/Furche/LayoutLab/releases/tag/v0.5.0
