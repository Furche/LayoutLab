"""Soft layout metrics (DD-015) — packing density + opening access. No bpy."""

from __future__ import annotations

from ..util import aabb_intersects, axis_aligned_bounds_from_points

CONSTRAINT_TYPE_SOFT_PACKING = "soft_packing"
CONSTRAINT_TYPE_OPENING_ACCESS = "opening_access"

# Furniture XY / room XY
PACKING_INFO_RATIO = 0.35
PACKING_WARN_RATIO = 0.48

DOOR_ACCESS_DEPTH = 0.7
WINDOW_ACCESS_DEPTH = 0.45


def _xy_area(bounds) -> float:
    mn = bounds.get("min") or [0, 0, 0]
    mx = bounds.get("max") or [0, 0, 0]
    return max(0.0, float(mx[0]) - float(mn[0])) * max(0.0, float(mx[1]) - float(mn[1]))


def _bounds_from_loc_dims(loc, dims):
    x, y, z = (float(v) for v in loc)
    dx, dy, dz = (float(v) for v in dims)
    return {
        "min": [x, y, z],
        "max": [x + dx, y + dy, z + dz],
    }


def analyze_soft_packing(session) -> list:
    """Return soft_packing findings (0 or 1 per room with furniture)."""
    findings = []
    for model in session._rooms.values():
        fp = model.get("footprint") or {}
        room_w = float(fp.get("width") or 0)
        room_d = float(fp.get("depth") or 0)
        room_area = room_w * room_d
        if room_area <= 1e-9:
            continue

        furniture_area = 0.0
        furniture_names = []
        collection = model.get("collection") or "layoutlab_room"
        for obj in session.mesh_store.objects:
            if obj.collection != collection:
                continue
            if obj.get("layoutlab_clearance_name"):
                continue
            if (obj.get("layoutlab_role") or "") == "label" or obj.type == "FONT":
                continue
            if not obj.get("layoutlab_generator"):
                continue
            # Count main/body-ish once: prefer objects without parent, else all generators
            if obj.parent is not None and obj.parent.get("layoutlab_generator"):
                continue
            bounds = axis_aligned_bounds_from_points(obj.world_bbox_corners())
            furniture_area += _xy_area(bounds)
            furniture_names.append(obj.name)

        if furniture_area <= 0:
            continue

        ratio = furniture_area / room_area
        if ratio < PACKING_INFO_RATIO:
            continue
        severity = "warning" if ratio >= PACKING_WARN_RATIO else "info"
        findings.append(
            {
                "severity": severity,
                "constraint_type": CONSTRAINT_TYPE_SOFT_PACKING,
                "message": (
                    f"Room '{model.get('name')}' packing density {ratio:.0%} "
                    f"(furniture XY / floor); prefer more free floor for comfort"
                ),
                "metrics": {
                    "room": model.get("name"),
                    "room_area": round(room_area, 4),
                    "furniture_area": round(furniture_area, 4),
                    "packing_ratio": round(ratio, 4),
                    "furniture_names": furniture_names[:20],
                },
            }
        )
    return findings


def analyze_opening_access(session) -> list:
    """Warn when furniture overlaps the inward access box of a door/window."""
    from ..core import room as room_core

    findings = []
    for model in session._rooms.values():
        collection = model.get("collection") or "layoutlab_room"
        blockers = []
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
            blockers.append(obj)

        for opening in model.get("openings") or []:
            kind = str(opening.get("kind") or "door").lower()
            depth = DOOR_ACCESS_DEPTH if kind == "door" else WINDOW_ACCESS_DEPTH
            try:
                loc, dims = room_core.opening_access_world_box(model, opening, depth=depth)
            except Exception:
                continue
            access_bounds = _bounds_from_loc_dims(loc, dims)
            overlaps = []
            for obj in blockers:
                ob = axis_aligned_bounds_from_points(obj.world_bbox_corners())
                if aabb_intersects(access_bounds, ob):
                    overlaps.append(
                        {
                            "object_name": obj.name,
                            "name": obj.name,
                            "object_id": obj.get("layoutlab_object_id") or "",
                            "generator": obj.get("layoutlab_generator") or "",
                        }
                    )
            if not overlaps:
                continue
            findings.append(
                {
                    "severity": "warning",
                    "constraint_type": CONSTRAINT_TYPE_OPENING_ACCESS,
                    "message": (
                        f"{kind.title()} '{opening.get('name')}' access zone is blocked "
                        f"(may not open fully / light path reduced)"
                    ),
                    "opening_ref": {
                        "name": opening.get("name"),
                        "kind": kind,
                        "wall_side": opening.get("wall_side"),
                        "room": model.get("name"),
                        "collection": collection,
                    },
                    "overlaps": overlaps,
                }
            )
    return findings


def analyze_soft_metrics(session) -> list:
    findings = []
    findings.extend(analyze_soft_packing(session))
    findings.extend(analyze_opening_access(session))
    return findings


def soft_summary_from_findings(findings) -> dict:
    soft = [
        f
        for f in findings or []
        if f.get("constraint_type") in (CONSTRAINT_TYPE_SOFT_PACKING, CONSTRAINT_TYPE_OPENING_ACCESS)
    ]
    return {
        "count": len(soft),
        "warnings": sum(1 for f in soft if f.get("severity") == "warning"),
        "info": sum(1 for f in soft if f.get("severity") == "info"),
        "types": sorted({f.get("constraint_type") for f in soft if f.get("constraint_type")}),
    }
