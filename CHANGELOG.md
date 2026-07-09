# Changelog

All notable changes to LayoutLab are documented here.

Format based on [Keep a Changelog](https://keepachangelog.com/).

------------------------------------------------------------------------

## [Unreleased]

### Added

- `generators/bed_basic.py` — version-controlled parametric bed generator
- `layoutlab_util.py` — pure-Python helpers (metadata inference, JSON parsing)
- `tests/test_layoutlab_util.py` — unit tests for registry and protocol parsing
- Bundled generator sync on addon register (copies missing generators to user dir)
- `CHANGELOG.md` and `DEVLOG.md`

### Fixed

- JSON command parsing for bare array payloads (list form) — previously raised `AttributeError`

### Changed

- `docs/json_protocol.md` — contract pass (v0.5.1): command index, errors, prerequisites
- `generators/bed_basic.py` — named constants, reference doc `generators/bed_basic.md`
- `layoutlab_chatgpt_helper_v05.py` loads `bed_basic` from `generators/` instead of embedded string
- JSON command parsing delegated to `layoutlab_util.parse_commands_payload`

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
