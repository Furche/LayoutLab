# LayoutLab

**Semantic, parametric interior planning for Blender.**

LayoutLab is not a furniture placement addon. It is an engine where objects understand what they are — beds know where legs belong, wardrobes know when they need another door — and geometry is generated from rules, not blind mesh scaling.

Blender 4.0+ is the current editor. The long-term goal: plan entire rooms by describing intent to an AI, without manually editing hundreds of meshes.

> *"LayoutLab does not create meshes. LayoutLab describes objects."*

**Status:** v0.5.1 — modular addon with semantic object metadata and `regenerate`.

Repository: https://github.com/Furche/LayoutLab

------------------------------------------------------------------------

## What works today (v0.5)

- JSON command exchange with ChatGPT (clipboard or text block)
- Scene export as JSON (full scene or selection)
- Generator browser (asset-browser-like)
- Parametric `bed_basic` generator (legs, frame, mattress, pillows)
- Semantic object metadata (`layoutlab_object_id`, params on meshes)
- `regenerate` JSON command (update params, preserve object identity)
- Save, load, and delete generators via UI or JSON
- Clearance boxes via `create_clearance` command

See [docs/json_protocol.md](docs/json_protocol.md) for the full command reference.

------------------------------------------------------------------------

## Requirements

- **Blender 4.0 or newer**
- No external Python packages

------------------------------------------------------------------------

## Installation

### Option A — Install from zip (recommended)

1. Build the installable zip (or download a release asset from GitHub):
   ```bash
   python3 scripts/build_addon_zip.py
   ```
   Creates `dist/layoutlab-<version>.zip` (e.g. `dist/layoutlab-0.5.0.zip`).

2. In Blender: **Edit → Preferences → Add-ons → Install…**
3. Select the zip file.
4. Enable **LayoutLab** in the add-ons list.

No manual copying into folders — Blender extracts the addon for you.

The zip is rebuilt **automatically** after git commits that change `layoutlab/` (via `scripts/install_git_hooks.sh`).  
Cursor also runs `python3 scripts/build_addon_zip.py` after addon changes during development.

### Diagnostics

After installing, open **LayoutLab → Run Console Checks**.  
The structured report is printed to the system console and copied to the clipboard — send it to Cursor for review.

### Option B — Copy folder

1. Clone this repository:
   ```bash
   git clone https://github.com/Furche/LayoutLab.git
   ```
2. Copy the **`layoutlab/`** folder into your Blender addons directory:
   - **macOS:** `~/Library/Application Support/Blender/<version>/scripts/addons/`
   - **Linux:** `~/.config/blender/<version>/scripts/addons/`
   - **Windows:** `%APPDATA%\Blender Foundation\Blender\<version>\scripts\addons\`

3. Restart Blender (or refresh addons).
4. Enable **LayoutLab** in *Edit → Preferences → Add-ons*.

### Option C — Symlink (development)

```bash
ln -s /path/to/LayoutLab/layoutlab ~/Library/Application\ Support/Blender/4.2/scripts/addons/layoutlab
```

Adjust Blender version path as needed.

------------------------------------------------------------------------

## Quick Start (5 minutes)

1. Open Blender → 3D Viewport → sidebar (**N**) → **LayoutLab** tab.
2. **Generator Library → Install Default** — installs the `bed_basic` generator.
3. **Open Generator Browser** → select `bed_basic` → **Create Test Object**.
4. A parametric bed appears in the `layout_tests` collection.
5. **Copy Scene Layout** — copies scene JSON to clipboard for ChatGPT.

### Apply commands from ChatGPT

1. Copy a JSON command block from ChatGPT (see example below).
2. In the LayoutLab panel: **Apply Commands** (reads from clipboard by default).
3. Check the Blender console (*Window → Toggle System Console*) for results and errors.

**Example command** — replace layout and place a bed:

```json
{
  "commands": [
    { "action": "delete_collection_objects", "collection": "layout_tests" },
    {
      "action": "run_generator",
      "generator": "bed_basic",
      "params": {
        "name": "BED_120x200",
        "location": [0, 0, 0],
        "length": 12,
        "width": 20,
        "head_side": "y_max",
        "collection": "layout_tests"
      }
    }
  ]
}
```

> **Units:** coordinates are Blender scene units. In the reference room scene, **1 unit ≈ 10 cm** — see [docs/units_and_coordinates.md](docs/units_and_coordinates.md).

------------------------------------------------------------------------

## Documentation

Read in this order:

| # | Document | Purpose |
|---|---|---|
| 0 | [docs/documentation_map.md](docs/documentation_map.md) | **Which doc to update when** — maintenance index for all documentation |
| 1 | [00_READ_THIS_FIRST.md](00_READ_THIS_FIRST.md) | Team roles, dev rules, mandatory doc checklist |
| 2 | [AI_CONTEXT.md](AI_CONTEXT.md) | Mental model, vocabulary, design priorities |
| 3 | [LayoutLab_Manifest.md](LayoutLab_Manifest.md) | Why this project exists |
| 4 | [LayoutLab_Master_Design_Document.md](LayoutLab_Master_Design_Document.md) | Vision, roadmap, architecture overview |
| 5 | [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md) | As-built vs. target architecture, migration plan |
| 6 | [docs/json_protocol.md](docs/json_protocol.md) | JSON command and export specification |
| 7 | [docs/generator_api.md](docs/generator_api.md) | Generator API reference (`api` dict) |
| 8 | [docs/object_model.md](docs/object_model.md) | Semantic object representation in scenes |
| 9 | [docs/units_and_coordinates.md](docs/units_and_coordinates.md) | Scale, axes, placement conventions |
| 10 | [docs/design_decisions/](docs/design_decisions/) | Formal architecture decisions (DD-001–005) |
| 11 | [LayoutLab_Generator_Specification.md](LayoutLab_Generator_Specification.md) | How to write generators |

------------------------------------------------------------------------

## Project Structure

```
LayoutLab/                          # repository root
├── layoutlab/                      # Blender addon (copy, symlink, or install zip)
│   ├── __init__.py                 # bl_info, register(), re-exports
│   ├── util.py                     # pure-Python helpers
│   ├── diagnostics.py              # console diagnostic checks
│   ├── plugin/                     # panel, operators, browser properties
│   ├── engine/                     # registry, executor
│   ├── api/                        # geometry, materials, collections
│   ├── protocol/                   # commands, export
│   └── generators/
│       ├── bed_basic.py
│       └── bed_basic.md
├── tests/
│   └── test_layoutlab_util.py
├── scripts/
│   ├── build_addon_zip.py
│   └── hooks/post-commit
├── CHANGELOG.md
├── DEVLOG.md
├── 00_READ_THIS_FIRST.md
├── AI_CONTEXT.md
├── LayoutLab_Manifest.md
├── LayoutLab_Master_Design_Document.md
├── LayoutLab_Generator_Specification.md
└── docs/
    ├── documentation_map.md        # which doc to update when
    ├── ARCHITECTURE.md
    ├── json_protocol.md
    ├── generator_api.md
    ├── object_model.md
    ├── units_and_coordinates.md
    └── design_decisions/
        └── DD-001 … DD-005
```

**Generators at runtime** are copied to Blender's user directory on first load
(if missing). Canonical sources live in `layoutlab/generators/` in this repository.

```
<Blender scripts>/addons/layoutlab_generators/*.py   # runtime copy
```

------------------------------------------------------------------------

## Running tests

From the repository root (no Blender required):

```bash
python -m unittest discover -s tests -v
```

------------------------------------------------------------------------

## Architecture (short)

Five layers — implemented as separate modules in `layoutlab/`:

```
Blender UI (plugin/)  →  Protocol  →  Engine  →  API  →  bpy
                              ↓
                         Generators  →  API only
```

- **Plugin** handles JSON and UI; no furniture logic.
- **Generators** know one object type and call only the LayoutLab API.
- **AI** communicates exclusively via JSON — no Python snippets for direct execution.

Full details: [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md)

------------------------------------------------------------------------

## Team

| Role | Responsibility |
|---|---|
| **Alexander** | Product owner, vision, priorities, testing |
| **ChatGPT** | System architecture, APIs, generator design, reviews |
| **Cursor** | Implementation, refactoring, Blender API, tests |

Cursor implements — it does not silently redefine architecture. See [00_READ_THIS_FIRST.md](00_READ_THIS_FIRST.md).

------------------------------------------------------------------------

## Roadmap (summary)

| Phase | Focus | Status |
|---|---|---|
| **A** | Documentation foundation | Complete |
| **B** | Generators in repo, tests, sync | Complete |
| **C** | Monolith → module split | Complete |
| **D** | Semantic object model, `regenerate` | Complete |
| **E** | Clearance, collision, paths, undo | Planned |

Full roadmap: [LayoutLab_Master_Design_Document.md](LayoutLab_Master_Design_Document.md) §17 · Phase status: [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md) §9

------------------------------------------------------------------------

## License

Not yet specified.
