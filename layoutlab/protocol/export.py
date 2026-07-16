import json
import math

from mathutils import Vector

from .. import bl_info
from ..api.units import from_bu_vec, unit_export_fields
from ..engine.registry import addon_user_dir, list_generators_meta
from .semantic import layoutlab_block_from_object


def v3(values):
    return [round(float(values[0]), 4), round(float(values[1]), 4), round(float(values[2]), 4)]


def object_to_dict(obj, scale_length=None):
    world_corners = []
    if hasattr(obj, "bound_box"):
        world_corners = [obj.matrix_world @ Vector(corner) for corner in obj.bound_box]
    data = {
        "name": obj.name,
        "type": obj.type,
        "collection": obj.users_collection[0].name if obj.users_collection else "",
        "location": v3(from_bu_vec(obj.location, scale_length=scale_length)),
        "rotation_euler_deg": [
            round(math.degrees(obj.rotation_euler.x), 3),
            round(math.degrees(obj.rotation_euler.y), 3),
            round(math.degrees(obj.rotation_euler.z), 3),
        ],
        "scale": v3(obj.scale),
        "dimensions": v3(from_bu_vec(obj.dimensions, scale_length=scale_length))
        if hasattr(obj, "dimensions")
        else [0, 0, 0],
        "visible": bool(obj.visible_get()),
        "world_bbox_corners": [v3(from_bu_vec(c, scale_length=scale_length)) for c in world_corners],
        "custom_properties": {k: obj[k] for k in obj.keys() if isinstance(obj[k], (str, int, float, bool))},
    }
    layoutlab = layoutlab_block_from_object(obj)
    if layoutlab:
        data["layoutlab"] = layoutlab
    return data


def layout_export_json(context, selected_only=False):
    scene = context.scene
    objs = context.selected_objects if selected_only else scene.objects
    version = ".".join(str(v) for v in bl_info["version"])
    from ..api.room_sync import list_room_models
    from ..core.room import export_room_block

    scale_length = float(scene.unit_settings.scale_length) or 1.0
    rooms = [export_room_block(m) for m in list_room_models()]
    data = {
        "layoutlab_version": version,
        **unit_export_fields(scene),
        "scene": scene.name,
        "generator_dir": str(addon_user_dir()),
        "generators": list_generators_meta(),
        "rooms": rooms,
        "objects": [
            object_to_dict(o, scale_length=scale_length)
            for o in objs
            if o.type in {"MESH", "EMPTY", "CURVE", "FONT"}
        ],
    }
    return json.dumps(data, indent=2, ensure_ascii=False)
