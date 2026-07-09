# LayoutLab

**Semantic, parametric interior planning for Blender.**

LayoutLab is not a furniture placement addon. It is an engine where objects understand what they are — beds know where legs belong, wardrobes know when they need another door — and geometry is generated from rules, not blind mesh scaling.

Blender 4.0+ is the current editor. The long-term goal: plan entire rooms by describing intent to an AI, without manually editing hundreds of meshes.

> *"LayoutLab does not create meshes. LayoutLab describes objects."*

**Status:** v0.5 prototype — functional, monolithic, pre-architecture-split.

Repository: https://github.com/Furche/LayoutLab

------------------------------------------------------------------------

## What works today (v0.5)

- JSON command exchange with ChatGPT (clipboard or text block)
- Scene export as JSON (full scene or selection)
- Generator browser (asset-browser-like)
- Parametric `bed_basic` generator (legs, frame, mattress, pillows)
- Save, load, and delete generators via UI or JSON
- Clearance boxes via `create_clearance` command

See [docs/json_protocol.md](docs/json_protocol.md) for the full command reference.

------------------------------------------------------------------------

## Requirements

- **Blender 4.0 or newer**
- No external Python packages

------------------------------------------------------------------------

## Installation

### Option A — Copy (simple)

1. Clone this repository:
   ```bash
   git clone https://github.com/Furche/LayoutLab.git
   ```
2. Copy `layoutlab_chatgpt_helper_v05.py` into your Blender addons folder:
   - **macOS:** `~/Library/Application Support/Blender/<version>/scripts/addons/`
   - **Linux:** `~/.config/blender/<version>/scripts/addons/`
   - **Windows:** `%APPDATA%\Blender Foundation\Blender\<version>\scripts\addons\`
3. Restart Blender (or refresh addons).
4. Enable **LayoutLab ChatGPT Helper** in *Edit → Preferences → Add-ons*.

### Option B — Symlink (development)

```bash
ln -s /path/to/LayoutLab/layoutlab_chatgpt_helper_v05.py \
  ~/Library/Application\ Support/Blender/4.2/scripts/addons/layoutlab_chatgpt_helper_v05.py
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

> **Units:** coordinates are Blender scene units. In the reference room scene, **1 unit ≈ 10 cm** (not enforced by the plugin — see planned `docs/units_and_coordinates.md`).

------------------------------------------------------------------------

## Documentation

Read in this order:

| # | Document | Purpose |
|---|---|---|
| 1 | [00_READ_THIS_FIRST.md](00_READ_THIS_FIRST.md) | Team roles, dev rules, how AI agents should work |
| 2 | [AI_CONTEXT.md](AI_CONTEXT.md) | Mental model, vocabulary, design priorities |
| 3 | [LayoutLab_Manifest.md](LayoutLab_Manifest.md) | Why this project exists |
| 4 | [LayoutLab_Master_Design_Document.md](LayoutLab_Master_Design_Document.md) | Vision, roadmap, architecture overview |
| 5 | [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md) | As-built v0.5 vs. target architecture, migration plan |
| 6 | [docs/json_protocol.md](docs/json_protocol.md) | JSON command and export specification |
| 7 | [LayoutLab_Generator_Specification.md](LayoutLab_Generator_Specification.md) | How to write generators |

------------------------------------------------------------------------

## Project Structure

```
LayoutLab/
├── layoutlab_chatgpt_helper_v05.py   # Entire addon (v0.5 monolith)
├── 00_READ_THIS_FIRST.md
├── AI_CONTEXT.md
├── LayoutLab_Manifest.md
├── LayoutLab_Master_Design_Document.md
├── LayoutLab_Generator_Specification.md
└── docs/
    ├── ARCHITECTURE.md
    └── json_protocol.md
```

**Generators at runtime** are stored outside this repo:

```
<Blender scripts>/addons/layoutlab_generators/*.py
```

Install via the UI or `save_generator` JSON command. Moving generators into the repository is planned.

------------------------------------------------------------------------

## Architecture (short)

Five target layers — today all in one file:

```
Blender UI  →  Main Plugin  →  Generator Engine  →  Generators  →  Scene
```

- **Plugin** handles JSON and knows no furniture logic.
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
| **0** | Documentation foundation | In progress |
| **1** | Generators in repo, tests, API docs | Planned |
| **2** | Monolith → module split | Planned |
| **3** | Clearance, collision, paths, undo | Planned |
| **4** | AI layout evaluation, full apartment planning | Planned |

Full roadmap: [LayoutLab_Master_Design_Document.md](LayoutLab_Master_Design_Document.md) §17

------------------------------------------------------------------------

## License

Not yet specified.
