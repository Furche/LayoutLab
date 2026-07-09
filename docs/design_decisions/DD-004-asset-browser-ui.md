# DD-004: UI Oriented on Asset Browser

Status: **Accepted**  
Date: 2026-07-09  
Version: 1.0

------------------------------------------------------------------------

## Problem

LayoutLab users think in objects ("I need a bed"), not in files, Python
modules, or JSON schemas. A technical editor UI (code-first, command-line feel)
would expose implementation details and intimidate non-developers — including
the product owner during daily planning work.

Blender users already understand the **Asset Browser** mental model: browse,
filter, preview, place.

## Decision

LayoutLab's generator library UI should feel like the **Blender Asset Browser**.

- Generators appear in a browsable list with name, category, and description.
- Search and category filters are first-class.
- Primary action is "use this generator" (create object), not "edit code".
- Code editing exists but is secondary (Workbench / Text Editor path).
- Technical panels (JSON, clipboard) are grouped separately from the browser.

v0.5 implements a popup browser with list, filters, metadata panel, and quick
test — not yet a full Asset Browser clone.

## Alternatives Considered

| Alternative | Why rejected |
|---|---|
| **Code-first UI (IDE in Blender)** | Wrong audience; generators are assets, not scripts to users |
| **Simple dropdown per generator** | Does not scale to 200 generators; no metadata visibility |
| **External web catalog** | Breaks Blender workflow; offline use required |
| **Blender native Asset Library integration** | Generators are Python logic, not blend assets — future hybrid possible `[PLANNED]` |

## Consequences

**Positive**

- Consistent UX as generator count grows.
- Metadata (category, description, icon) is visible before use — drives DD-005.
- AI can reference generators by human name, matching what the user sees.
- Aligns with "work with objects, not implementation details" (`00_READ_THIS_FIRST.md`).

**Negative / trade-offs**

- Asset Browser features (thumbnails, drag-drop, favourites) require significant UI work `[PLANNED]`.
- v0.5 browser is a custom popup, not native Asset Browser integration.
- Thumbnail generation needs renderer or pre-rendered previews `[PLANNED]`.

## v0.5 Implementation

| Feature | Status |
|---|---|
| Generator list with category column | `[IMPLEMENTED]` |
| Text search filter | `[IMPLEMENTED]` |
| Category filter | `[IMPLEMENTED]` |
| Metadata panel (name, version, description) | `[IMPLEMENTED]` |
| Quick test (location, length, width) | `[IMPLEMENTED]` |
| Thumbnails | `[PLANNED]` |
| Favourites / recently used | `[PLANNED]` |
| Drag-drop into viewport | `[PLANNED]` |
| Live preview | `[PLANNED]` |

## References

- `LayoutLab_Master_Design_Document.md` §10
- `layoutlab_chatgpt_helper_v05.py` — `LAYOUTLAB_OT_open_generator_browser`
- `docs/ARCHITECTURE.md` §5.5
