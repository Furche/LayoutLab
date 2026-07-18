"""Hard solid collisions: furniture must not penetrate walls (not a waivable tradeoff)."""

from __future__ import annotations

from ..util import aabb_intersects, axis_aligned_bounds_from_points

CONSTRAINT_TYPE_SOLID_WALL = "solid_wall_penetration"

# Minimum wall thickness for AABB tests (walls are display-thin otherwise).
MIN_SOLID_THICKNESS = 0.05
# Ignore tiny overlaps from floating-point / flush placement.
OVERLAP_EPS = 0.02


def _furniture_roots(session, collection: str):
    out = []
    for obj in session.mesh_store.objects:
        if obj.collection != collection:
            continue
        if obj.get("layoutlab_clearance_name"):
            continue
        if (obj.get("layoutlab_role") or "") == "label" or obj.type == "FONT":
            continue
        if not obj.get("layoutlab_generator"):
            continue
        if obj.parent is not None and obj.parent.get("layoutlab_generator"):
            continue
        out.append(obj)
    return out


def _shrink_bounds(bounds, eps=OVERLAP_EPS):
    """Shrink furniture AABB slightly so flush-to-wall is OK, through-wall is not."""
    mn = list(bounds["min"])
    mx = list(bounds["max"])
    for i in range(3):
        if float(mx[i]) - float(mn[i]) > 2 * eps:
            mn[i] = float(mn[i]) + eps
            mx[i] = float(mx[i]) - eps
    return {"min": mn, "max": mx}


def wall_panel_solid_bounds(model, wall, panel):
    """AABB for a wall panel extruded inward by wall thickness."""
    from ..core import room as room_core

    thickness = max(
        float(model.get("wall_thickness") or room_core.DEFAULT_WALL_THICKNESS),
        MIN_SOLID_THICKNESS,
    )
    corners = panel.get("corners") or []
    if len(corners) < 3:
        return None
    xs = [float(c[0]) for c in corners]
    ys = [float(c[1]) for c in corners]
    zs = [float(c[2]) for c in corners]
    mn = [min(xs), min(ys), min(zs)]
    mx = [max(xs), max(ys), max(zs)]
    side = wall.get("side")
    # Extrude into the room so furniture sitting in the wall volume is caught.
    if side == "south":
        mx[1] = mn[1] + thickness
    elif side == "north":
        mn[1] = mx[1] - thickness
    elif side == "west":
        mx[0] = mn[0] + thickness
    elif side == "east":
        mn[0] = mx[0] - thickness
    else:
        return None
    # Ensure non-zero thickness on all axes for aabb_intersects
    for i in range(3):
        if mx[i] <= mn[i]:
            mx[i] = mn[i] + 0.001
    return {"min": mn, "max": mx}


def analyze_solid_wall_collisions(session) -> list:
    """Error findings when furniture AABB penetrates wall solids (openings already cut)."""
    from ..core import room as room_core

    findings = []
    for model in session._rooms.values():
        collection = model.get("collection") or "layoutlab_room"
        furniture = _furniture_roots(session, collection)
        if not furniture:
            continue

        wall_solids = []
        for wall in model.get("walls") or []:
            for index, panel in enumerate(room_core.wall_display_panels(model, wall)):
                bounds = wall_panel_solid_bounds(model, wall, panel)
                if not bounds:
                    continue
                wall_solids.append(
                    {
                        "side": wall.get("side"),
                        "panel": index,
                        "bounds": bounds,
                    }
                )

        for obj in furniture:
            raw = axis_aligned_bounds_from_points(obj.world_bbox_corners())
            fb = _shrink_bounds(raw)
            hits = []
            for solid in wall_solids:
                if aabb_intersects(fb, solid["bounds"]):
                    hits.append({"wall_side": solid["side"], "panel": solid["panel"]})
            if not hits:
                continue
            sides = sorted({h["wall_side"] for h in hits if h.get("wall_side")})
            findings.append(
                {
                    "severity": "error",
                    "constraint_type": CONSTRAINT_TYPE_SOLID_WALL,
                    "non_negotiable": True,
                    "message": (
                        f"Furniture '{obj.name}' intersects wall solid "
                        f"({', '.join(sides) or 'wall'}) — physically invalid, not a tradeoff"
                    ),
                    "object_ref": {
                        "name": obj.name,
                        "object_id": obj.get("layoutlab_object_id") or "",
                        "generator": obj.get("layoutlab_generator") or "",
                    },
                    "walls": hits,
                }
            )
    return findings
