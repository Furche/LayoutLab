import json
import math

from mathutils import Vector

from ..engine.registry import addon_user_dir, list_generators_meta


def v3(values):
    return [round(float(values[0]), 4), round(float(values[1]), 4), round(float(values[2]), 4)]


def object_to_dict(obj):
    world_corners = []
    if hasattr(obj, "bound_box"):
        world_corners = [obj.matrix_world @ Vector(corner) for corner in obj.bound_box]
    return {
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


def layout_export_json(context, selected_only=False):
    scene = context.scene
    objs = context.selected_objects if selected_only else scene.objects
    data = {
        "layoutlab_version": "0.5.0",
        "unit": scene.unit_settings.system,
        "unit_scale": scene.unit_settings.scale_length,
        "scene": scene.name,
        "generator_dir": str(addon_user_dir()),
        "generators": list_generators_meta(),
        "note": "Coordinates/dimensions are Blender units. In Alexander's room: 1 unit ≈ 10 cm.",
        "objects": [object_to_dict(o) for o in objs if o.type in {"MESH", "EMPTY", "CURVE", "FONT"}],
    }
    return json.dumps(data, indent=2, ensure_ascii=False)
