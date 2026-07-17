import json
import math

from mathutils import Vector

from .. import bl_info
from ..engine.registry import addon_user_dir, list_generators_meta
from .semantic import layoutlab_block_from_object
from .viewer_export import VIEWER_SCHEMA, parse_corners_json, viewer_block_for_role


def v3(values):
    return [round(float(values[0]), 4), round(float(values[1]), 4), round(float(values[2]), 4)]


def mesh_world_quad_corners(obj):
    """World-space corners for a single quad mesh (face vertex order)."""
    if obj.type != "MESH" or not obj.data or len(obj.data.vertices) < 4:
        return None
    mesh = obj.data
    if len(mesh.polygons) == 1 and len(mesh.polygons[0].vertices) >= 4:
        idxs = list(mesh.polygons[0].vertices)[:4]
    else:
        idxs = list(range(4))
    return [v3(obj.matrix_world @ mesh.vertices[i].co) for i in idxs]


def viewer_block_from_object(obj):
    role = obj.get("layoutlab_role") or ""
    corners = parse_corners_json(obj.get("layoutlab_viewer_corners"))
    if corners is None and role == "room_wall":
        corners = mesh_world_quad_corners(obj)
    display_type = getattr(obj, "display_type", None)
    return viewer_block_for_role(role, corners=corners, display_type=display_type)


def object_to_dict(obj):
    world_corners = []
    if hasattr(obj, "bound_box"):
        world_corners = [obj.matrix_world @ Vector(corner) for corner in obj.bound_box]
    data = {
        "name": obj.name,
        "type": obj.type,
        "collection": obj.users_collection[0].name if obj.users_collection else "",
        "location": v3(obj.location),
        "rotation_euler_deg": [
            round(math.degrees(obj.rotation_euler.x), 3),
            round(math.degrees(obj.rotation_euler.y), 3),
            round(math.degrees(obj.rotation_euler.z), 3),
        ],
        "scale": v3(obj.scale),
        "dimensions": v3(obj.dimensions) if hasattr(obj, "dimensions") else [0, 0, 0],
        "visible": bool(obj.visible_get()),
        "world_bbox_corners": [v3(c) for c in world_corners],
        "custom_properties": {k: obj[k] for k in obj.keys() if isinstance(obj[k], (str, int, float, bool))},
    }
    layoutlab = layoutlab_block_from_object(obj)
    if layoutlab:
        data["layoutlab"] = layoutlab
    viewer = viewer_block_from_object(obj)
    if viewer:
        data["viewer"] = viewer
    return data


def layout_export_json(context, selected_only=False):
    scene = context.scene
    objs = context.selected_objects if selected_only else scene.objects
    version = ".".join(str(v) for v in bl_info["version"])
    from ..api.room_sync import list_room_models
    from ..core.room import export_room_block

    rooms = [export_room_block(m) for m in list_room_models()]
    data = {
        "layoutlab_version": version,
        "viewer_schema": VIEWER_SCHEMA,
        "unit": scene.unit_settings.system,
        "unit_scale": scene.unit_settings.scale_length,
        "scene": scene.name,
        "generator_dir": str(addon_user_dir()),
        "generators": list_generators_meta(),
        "note": (
            "Coordinates/dimensions are Blender scene units (native). "
            "With Metric and unit_scale=1.0, 1 unit = 1 meter."
        ),
        "rooms": rooms,
        "objects": [object_to_dict(o) for o in objs if o.type in {"MESH", "EMPTY", "CURVE", "FONT"}],
    }
    return json.dumps(data, indent=2, ensure_ascii=False)
