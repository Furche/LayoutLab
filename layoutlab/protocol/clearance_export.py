"""Clearance export helpers (DD-007)."""

from mathutils import Vector

from ..api.units import from_bu_vec
from ..util import (
    axis_aligned_bounds_from_points,
    box_bounds_from_corner_and_dimensions,
    parse_clearance_params_json,
)


def _round_v3(values):
    return [round(float(values[0]), 4), round(float(values[1]), 4), round(float(values[2]), 4)]


def world_bounds_from_object(obj):
    """Axis-aligned bounds in Blender scene units (for analyze_layout)."""
    if not hasattr(obj, "bound_box"):
        return {"min": [0.0, 0.0, 0.0], "max": [0.0, 0.0, 0.0]}
    corners = [obj.matrix_world @ Vector(corner) for corner in obj.bound_box]
    return axis_aligned_bounds_from_points([_round_v3(c) for c in corners])


def local_bounds_from_object(obj):
    """Bounds in Main Part space — from stored transform or parent inverse.

    Stored clearance transforms are LayoutLab units; mesh-derived fallback is
    converted to LayoutLab units for export consistency.
    """
    stored = parse_clearance_params_json(obj.get("layoutlab_clearance_params"))
    local_transform = stored.get("local_transform")
    if isinstance(local_transform, dict):
        location = local_transform.get("location")
        dimensions = local_transform.get("dimensions")
        if location is not None and dimensions is not None:
            return box_bounds_from_corner_and_dimensions(location, dimensions)

    parent = obj.parent
    if parent and hasattr(obj, "bound_box"):
        inv = parent.matrix_world.inverted()
        corners = [inv @ (obj.matrix_world @ Vector(corner)) for corner in obj.bound_box]
        return axis_aligned_bounds_from_points(
            [_round_v3(from_bu_vec(c)) for c in corners]
        )

    wb = world_bounds_from_object(obj)
    return {
        "min": _round_v3(from_bu_vec(wb["min"])),
        "max": _round_v3(from_bu_vec(wb["max"])),
    }


def clearance_export_block_from_object(obj):
    clearance_name = obj.get("layoutlab_clearance_name")
    if not clearance_name:
        return None

    stored = parse_clearance_params_json(obj.get("layoutlab_clearance_params"))
    local_transform = stored.get("local_transform") if isinstance(stored.get("local_transform"), dict) else None
    params = {k: v for k, v in stored.items() if k != "local_transform"}

    wb = world_bounds_from_object(obj)
    block = {
        "clearance_id": obj.get("layoutlab_clearance_id", ""),
        "clearance_name": clearance_name,
        "purpose": obj.get("layoutlab_clearance_purpose", ""),
        "requirement": obj.get("layoutlab_clearance_requirement", "preferred"),
        "priority": int(obj.get("layoutlab_clearance_priority", 0) or 0),
        "params": params,
        "shape": (local_transform or {}).get("shape", "box"),
        "local_bounds": local_bounds_from_object(obj),
        "world_bounds": {
            "min": _round_v3(from_bu_vec(wb["min"])),
            "max": _round_v3(from_bu_vec(wb["max"])),
        },
    }

    if local_transform:
        block["local_transform"] = {
            "location": _round_v3(local_transform.get("location", [0, 0, 0])),
            "rotation": [round(float(r), 4) for r in local_transform.get("rotation", [0, 0, 0])],
            "dimensions": _round_v3(local_transform.get("dimensions", [0, 0, 0])),
            "shape": local_transform.get("shape", "box"),
        }

    return block
