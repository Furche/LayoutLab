import json
import math

from mathutils import Vector

from .. import bl_info
from ..engine.registry import addon_user_dir, list_generators_meta
from .semantic import layoutlab_block_from_object
from .viewer_export import (
    MAX_VIEWER_MESH_VERTS,
    SKIP_VIEWER_ROLES,
    VIEWER_SCHEMA,
    WIRE_ROLES,
    parse_corners_json,
    viewer_block_for_role,
)


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


def mesh_world_geometry(obj):
    """World-space triangulated faces for viewer mesh primitive (or None)."""
    if obj.type != "MESH" or not obj.data:
        return None
    mesh = obj.data
    if len(mesh.vertices) == 0 or len(mesh.vertices) > MAX_VIEWER_MESH_VERTS:
        return None
    mw = obj.matrix_world
    vertices = [v3(mw @ v.co) for v in mesh.vertices]
    faces = []
    for poly in mesh.polygons:
        idxs = list(poly.vertices)
        if len(idxs) < 3:
            continue
        for i in range(1, len(idxs) - 1):
            faces.append([idxs[0], idxs[i], idxs[i + 1]])
    if not faces:
        return None
    return {"vertices": vertices, "faces": faces}


def viewer_block_from_object(obj):
    role = obj.get("layoutlab_role") or ""
    if role in SKIP_VIEWER_ROLES:
        return None
    display_type = getattr(obj, "display_type", None)
    is_wire = role in WIRE_ROLES or (display_type and str(display_type).upper() == "WIRE")

    corners = parse_corners_json(obj.get("layoutlab_viewer_corners"))
    if corners is None and role == "room_wall":
        corners = mesh_world_quad_corners(obj)

    mesh = None
    if role == "clearance":
        # Oriented wire mesh — AABB boxes look like scale/shear when furniture rotates.
        mesh = mesh_world_geometry(obj)
    elif not is_wire and role != "room_wall":
        mesh = mesh_world_geometry(obj)

    return viewer_block_for_role(role, corners=corners, display_type=display_type, mesh=mesh)


def object_to_dict(obj):
    world_corners = []
    if hasattr(obj, "bound_box"):
        world_corners = [obj.matrix_world @ Vector(corner) for corner in obj.bound_box]
    world_loc = obj.matrix_world.to_translation()
    world_euler = obj.matrix_world.to_euler("XYZ")
    data = {
        "name": obj.name,
        "type": obj.type,
        "collection": obj.users_collection[0].name if obj.users_collection else "",
        "location": v3(world_loc),
        "rotation_euler_deg": [
            round(math.degrees(world_euler.x), 3),
            round(math.degrees(world_euler.y), 3),
            round(math.degrees(world_euler.z), 3),
        ],
        "scale": v3(obj.matrix_world.to_scale()),
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


def analysis_for_export(context, selected_only=False):
    """Run analyze_layout and return a JSON-serializable analysis block for export."""
    from .layout_analysis import analyze_layout

    cmd = {
        "action": "analyze_layout",
        "scope": "selection" if selected_only else "scene",
        "include": ["clearances"],
    }
    try:
        result = analyze_layout(context, cmd)
        # Alias for viewers that expect overlaps[].name
        for finding in result.get("findings") or []:
            for overlap in finding.get("overlaps") or []:
                if "name" not in overlap and overlap.get("object_name"):
                    overlap["name"] = overlap["object_name"]
        return result
    except Exception as exc:
        return {
            "analyzed": False,
            "scope": cmd["scope"],
            "summary": {"errors": 0, "warnings": 0, "info": 0},
            "findings": [],
            "error": str(exc),
        }


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
        "project_id": scene.get("layoutlab_project_id") or "",
        "project_name": scene.get("layoutlab_project_name") or scene.name,
        "project": {
            "project_id": scene.get("layoutlab_project_id") or "",
            "name": scene.get("layoutlab_project_name") or scene.name,
        },
        "generator_dir": str(addon_user_dir()),
        "generators": list_generators_meta(),
        "note": (
            "Spatial Project export (DD-020). "
            "Coordinates/dimensions are Blender scene units (native). "
            "With Metric and unit_scale=1.0, 1 unit = 1 meter. "
            "location/rotation are world-space; prefer world_bbox_corners / viewer.mesh for display. "
            "analysis is from analyze_layout at export time."
        ),
        "rooms": rooms,
        "objects": [
            object_to_dict(o)
            for o in objs
            if o.type in {"MESH", "EMPTY", "CURVE", "FONT"}
            and (o.get("layoutlab_role") or "") not in SKIP_VIEWER_ROLES
        ],
        "analysis": analysis_for_export(context, selected_only=selected_only),
    }
    return json.dumps(data, indent=2, ensure_ascii=False)
