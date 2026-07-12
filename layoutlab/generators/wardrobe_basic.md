# wardrobe_basic Generator

## Purpose

`wardrobe_basic` creates a simple parametric wardrobe from semantic components rather than a single scaled box.

It is intended as a second canonical generator after `bed_basic`, focused on storage furniture.

## Metadata

```python
GENERATOR_NAME = "wardrobe_basic"
GENERATOR_CATEGORY = "Storage"
GENERATOR_VERSION = "0.2"
```

## Parts (v0.6)

| Part id | Type | Final object | Contents |
|---|---|---|---|
| `body` | **main** | `{name}_body` | sides, top, bottom, back, shelves (joined) |
| `door_1`, `door_2`, … | **dynamic** | `{name}_door_1`, … | door panel + handle (joined per door) |
| `clearance_front_access` | static | `{name}_clearance_front_access` | front usage zone (`front_access`, optional) |
| `label` | static | `{name}_label` | text label |

Dynamic door Parts are parented to `body` — move body, doors follow; doors stay separate for animation.

**Front / clearance:** Default **`front_side: y_min`** — doors and clearance in **−Y** (back panel at +Y).
Use **`front_side: y_max`** when the back sits on the south wall (`y_min`): doors and clearance open **+Y** into the room.

## Coordinate Convention

- `location` is the min corner of the wardrobe footprint at floor level.
- `width` extends along +X.
- `depth` extends along +Y.
- `height` extends along +Z.
- Doors are placed on the front side at `y_min`.

In Alexander's reference room convention, `1 unit ≈ 10 cm`.

## Component Roles (build meshes)

| Role | Build content |
|---|---|
| `wardrobe_side` | side panels |
| `wardrobe_top` | top panel |
| `wardrobe_bottom` | bottom panel |
| `wardrobe_back` | back panel |
| `wardrobe_shelf` | internal shelves |
| `wardrobe_door` | door panels |
| `wardrobe_handle` | handles |
| `clearance` | front usage clearance |
| `label` | text label |

## Parameters

| Parameter | Default | Description |
|---|---:|---|
| `name` | `"WARDROBE_basic"` | Prefix for all Part object names |
| `location` | `[0, 0, 0]` | Min corner of footprint |
| `collection` | `"layout_tests"` | Target collection |
| `width` | `8.0` | Wardrobe width along X |
| `depth` | `4.0` | Wardrobe depth along Y |
| `height` | `15.0` | Wardrobe height along Z |
| `door_count` | auto | 1/2/3 doors depending on width; explicit value capped at 4 |
| `shelf_count` | auto | Number of internal shelves; explicit value capped at 8 |
| `show_clearance` | `True` | Creates front usage clearance |
| `front_side` | `"y_min"` | Door face: `y_min` (default) or `y_max` (back on south wall) |
| `clearance_depth` | `6.0` | Front clearance depth |
| `panel_thickness` | `0.25` | Side/top/bottom thickness |
| `back_thickness` | `0.15` | Back panel thickness |
| `shelf_thickness` | `0.18` | Shelf thickness |
| `door_thickness` | `0.18` | Door thickness |
| `carcass_color` | wood RGBA | Carcass material color |
| `door_color` | light wood RGBA | Door material color |
| `shelf_color` | wood RGBA | Shelf material color |
| `handle_color` | dark RGBA | Handle material color |
| `clearance_color` | blue transparent RGBA | Clearance material color |

## Example JSON

```json
{
  "commands": [
    {
      "action": "run_generator",
      "generator": "wardrobe_basic",
      "params": {
        "name": "WARDROBE_80x40x150",
        "location": [90, 196.8, 0],
        "width": 8,
        "depth": 4,
        "height": 15,
        "collection": "layout_tests",
        "show_clearance": true
      }
    }
  ]
}
```

## Design Notes

This generator follows the LayoutLab generator rules:

- no UI
- no scene analysis
- no direct `bpy`
- Parts API (`begin_part` / `end_part` / `finish`) — see `docs/object_model.md`
- semantic roles for every build mesh
- fallback behaviour for unusual dimensions
- front clearance as early semantic usage area
