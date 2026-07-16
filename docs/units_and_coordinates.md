# Units and Coordinates

Version: 0.10.0

> Defines how LayoutLab interprets space in Blender scenes.
> Required reading before writing generators, JSON commands, or interpreting scene export.

**Status markers:**

- `[IMPLEMENTED]` — used today
- `[PLANNED]` — agreed convention, not yet enforced by plugin
- `[CONVENTION]` — project standard

------------------------------------------------------------------------

# 1. Overview

LayoutLab uses **Blender scene units natively** — the same numbers you see in Blender.
JSON commands, generator params, and scene export are **not converted**.

With Blender’s default Metric setup (`unit_scale = 1.0`), **1 unit = 1 meter**.

------------------------------------------------------------------------

# 2. Scale

## 2.1 Native Blender units `[IMPLEMENTED]`

| Real size | JSON / params (Metric, scale 1.0) |
|---|---|
| 120 cm bed length | `1.2` |
| 200 cm bed width | `2.0` |
| 75 cm desk/radiator height | `0.75` |
| 2.6 m ceiling | `2.6` |
| 4.2 × 2.18 m room | `width: 4.2`, `depth: 2.18` |

## 2.2 Plugin behaviour `[IMPLEMENTED]`

- No LayoutLab-specific unit conversion layer.
- Export reports `unit` / `unit_scale` from the scene for context.
- If you change Blender’s Unit Scale, you are changing how Blender *displays* sizes; mesh numbers stay in Blender Units.

## 2.3 Breaking change (v0.10)

Previous versions used a project convention of **1 unit ≈ 10 cm**. Those values were **÷10** for native meters (e.g. `height: 7.5` → `0.75`).

------------------------------------------------------------------------

# 3. Coordinate System

## 3.1 Axes `[IMPLEMENTED]` (Blender standard)

| Axis | Typical use in LayoutLab |
|---|---|
| **X** | Room width / object length (along X) |
| **Y** | Room depth / object width (along Y) |
| **Z** | Height (floor = Z 0) |

## 3.2 Floor Plane `[CONVENTION]`

- Floor is at **Z = 0** unless the scene deliberately offsets the room.
- Furniture `location[2]` is typically `0`.

## 3.3 Room Origin `[CONVENTION]`

- Default room origin is **`[0, 0, 0]`**.

------------------------------------------------------------------------

# 4. Object Placement

## 4.1 Location Semantics `[IMPLEMENTED]`

`location: [x, y, z]` is the **world-space minimum corner** of the furniture footprint on the floor.

## 4.2 create_box `[IMPLEMENTED]`

```
create_box(name, [x, y, z], [dx, dy, dz])
         origin ──→ extends +X by dx, +Y by dy, +Z by dz
```

## 4.3 Dimensions `[IMPLEMENTED]`

`dimensions: [dx, dy, dz]` — size along X, Y, Z. Always positive.

------------------------------------------------------------------------

# 5. Furniture Conventions

### Standard bed sizes (Metric, 1 unit = 1 m)

| Name | length (X) | width (Y) | Real size |
|---|---|---|---|
| Single 90×200 | `0.9` | `2.0` | 90 × 200 cm |
| Standard 120×200 | `1.2` | `2.0` | 120 × 200 cm |
| Queen 140×200 | `1.4` | `2.0` | 140 × 200 cm |
| King 180×200 | `1.8` | `2.0` | 180 × 200 cm |

------------------------------------------------------------------------

# 6. Export

```json
{
  "unit": "METRIC",
  "unit_scale": 1.0,
  "note": "Coordinates/dimensions are Blender scene units (native). With Metric and unit_scale=1.0, 1 unit = 1 meter."
}
```

AI should treat export values as Blender units matching the scene.

------------------------------------------------------------------------

# 7. Common Mistakes

| Mistake | Correct approach |
|---|---|
| Using old 10 cm units (`height: 7.5`) | Use meters: `height: 0.75` |
| Using object centre as `location` | Use min corner at floor |
| Scaling mesh instead of params | Change generator params and re-run |

------------------------------------------------------------------------

# 8. Changelog

| Version | Date | Changes |
|---|---|---|
| 0.10.0 | 2026-07-17 | Native Blender units; drop 10 cm convention and conversion layer |
| 0.9.3 | 2026-07-17 | (superseded) temporary LL↔BU conversion via scale_length |
| 0.6.1 | 2026-07-10 | Parts parenting coordinate model |
| 0.5.0 | 2026-07-09 | Initial document |
