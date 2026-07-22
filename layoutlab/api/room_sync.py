"""Blender adapter: sync Room Model meshes (DD-010)."""

from __future__ import annotations

import json

import bpy

from ..core import room as room_core
from .collections import delete_by_object_id, get_or_create_collection
from .geometry import create_box, create_quad

ROOM_JSON_PROP = "layoutlab_room_json"
FLOOR_COLOR = (0.72, 0.62, 0.48, 1.0)
WALL_COLOR = (0.85, 0.85, 0.82, 1.0)
OPENING_COLOR = (0.45, 0.65, 0.85, 0.55)
FIXED_COLOR = (0.55, 0.55, 0.58, 1.0)


def _prefix(model):
    return f"{model['name']}_"


def _stamp_room_object(obj, model, *, role, entity_id=None, entity_kind=None):
    obj["layoutlab_room_id"] = model["room_id"]
    obj["layoutlab_object_id"] = model["room_id"]
    obj["layoutlab_role"] = role
    obj["layoutlab_part"] = role
    if entity_id:
        obj["layoutlab_room_entity_id"] = entity_id
    if entity_kind:
        obj["layoutlab_room_entity_kind"] = entity_kind
    obj[ROOM_JSON_PROP] = json.dumps(room_core.room_to_dict(model), ensure_ascii=False, sort_keys=True)


def find_room_root(room_id=None, name=None):
    for obj in bpy.data.objects:
        if obj.get("layoutlab_role") != "room_floor":
            continue
        if room_id and obj.get("layoutlab_room_id") == room_id:
            return obj
        if name and obj.name == f"{name}_floor":
            return obj
        if name and obj.get("layoutlab_room_json"):
            try:
                data = json.loads(obj[ROOM_JSON_PROP])
            except Exception:
                continue
            if data.get("name") == name:
                return obj
    return None


def load_room_model(room_id=None, name=None):
    root = find_room_root(room_id=room_id, name=name)
    if not root:
        raise ValueError(f"room not found: {room_id or name}")
    raw = root.get(ROOM_JSON_PROP)
    if not raw:
        raise ValueError(f"room root missing {ROOM_JSON_PROP}")
    return json.loads(raw), root


def list_room_models():
    rooms = []
    seen = set()
    for obj in bpy.data.objects:
        if obj.get("layoutlab_role") != "room_floor":
            continue
        room_id = obj.get("layoutlab_room_id")
        if not room_id or room_id in seen:
            continue
        raw = obj.get(ROOM_JSON_PROP)
        if not raw:
            continue
        try:
            rooms.append(json.loads(raw))
            seen.add(room_id)
        except Exception:
            continue
    return rooms


def delete_room_meshes(room_id):
    return delete_by_object_id(room_id)


def sync_room_to_scene(model):
    """Rebuild all display meshes for a room model. Idempotent."""
    delete_room_meshes(model["room_id"])
    collection = model.get("collection") or "layoutlab_room"
    get_or_create_collection(collection)
    prefix = _prefix(model)

    floor_loc, floor_dims = room_core.floor_display_box(model)
    floor = create_box(
        f"{prefix}floor",
        floor_loc,
        floor_dims,
        color=FLOOR_COLOR,
        collection=collection,
        role="room_floor",
    )
    _stamp_room_object(floor, model, role="room_floor", entity_kind="floor")

    for wall in model.get("walls", []):
        panels = room_core.wall_display_panels(model, wall)
        for index, panel in enumerate(panels):
            name = f"{prefix}wall_{wall['side']}" if len(panels) == 1 else f"{prefix}wall_{wall['side']}_p{index}"
            obj = create_quad(
                name,
                panel["corners"],
                color=WALL_COLOR,
                collection=collection,
                role="room_wall",
                backface_culling=True,
            )
            _stamp_room_object(
                obj,
                model,
                role="room_wall",
                entity_id=wall["wall_id"],
                entity_kind="wall",
            )
            obj["layoutlab_wall_side"] = wall["side"]
            obj["layoutlab_wall_facing"] = "inward"
            obj["layoutlab_wall_panel_index"] = index
            obj["layoutlab_viewer_corners"] = json.dumps(
                [
                    [round(float(c[0]), 4), round(float(c[1]), 4), round(float(c[2]), 4)]
                    for c in panel["corners"]
                ],
                separators=(",", ":"),
            )

    for opening in model.get("openings", []):
        if not room_core.is_attachment_active(opening):
            continue
        loc, dims = room_core.opening_world_box(model, opening)
        obj = create_box(
            f"{prefix}opening_{opening['name']}",
            loc,
            dims,
            color=OPENING_COLOR,
            collection=collection,
            role="room_opening",
            display_type="WIRE",
        )
        _stamp_room_object(
            obj,
            model,
            role="room_opening",
            entity_id=opening["opening_id"],
            entity_kind=opening["kind"],
        )

    for fixed in model.get("fixed_elements", []):
        if not room_core.is_attachment_active(fixed):
            continue
        loc, dims = room_core.fixed_element_world_box(model, fixed)
        obj = create_box(
            f"{prefix}fixed_{fixed['name']}",
            loc,
            dims,
            color=FIXED_COLOR,
            collection=collection,
            role="room_fixed",
        )
        _stamp_room_object(
            obj,
            model,
            role="room_fixed",
            entity_id=fixed["fixed_element_id"],
            entity_kind=fixed["kind"],
        )

    return {
        "room_id": model["room_id"],
        "name": model["name"],
        "created": model["name"],
        "type": "room_model",
        "footprint": model["footprint"],
        "height": model["height"],
        "wall_count": len(model.get("walls", [])),
        "wall_panel_count": sum(
            len(room_core.wall_display_panels(model, wall)) for wall in model.get("walls", [])
        ),
        "opening_count": len(model.get("openings", [])),
        "fixed_element_count": len(model.get("fixed_elements", [])),
        "collection": collection,
        "world_bounds": room_core.room_world_bounds(model),
    }


def create_room(params):
    model = room_core.create_room_model(params)
    result = sync_room_to_scene(model)
    return result


def _resolve_and_load(params):
    params = params or {}
    room_name = params.get("room") or params.get("room_name")
    if not room_name and not params.get("room_id"):
        # create_room-style: top-level name is the room name
        room_name = params.get("name")
    return load_room_model(room_id=params.get("room_id"), name=room_name)


def update_room(params):
    model, _ = _resolve_and_load(params)
    room_core.update_room_model(model, params)
    return sync_room_to_scene(model)


def delete_room(params):
    model, _ = _resolve_and_load(params)
    removed = delete_room_meshes(model["room_id"])
    return {"deleted_room": model["name"], "room_id": model["room_id"], "removed_objects": removed}


def add_opening(params):
    model, _ = _resolve_and_load(params)
    opening = room_core.add_opening(model, params)
    result = sync_room_to_scene(model)
    result["opening"] = opening
    return result


def update_opening(params):
    model, _ = _resolve_and_load(params)
    opening = room_core.update_opening(model, params)
    result = sync_room_to_scene(model)
    result["opening"] = opening
    return result


def remove_opening(params):
    model, _ = _resolve_and_load(params)
    opening = room_core.remove_opening(model, params)
    result = sync_room_to_scene(model)
    result["removed_opening"] = opening
    return result


def add_fixed_element(params):
    model, _ = _resolve_and_load(params)
    fixed = room_core.add_fixed_element(model, params)
    result = sync_room_to_scene(model)
    result["fixed_element"] = fixed
    return result


def update_fixed_element(params):
    model, _ = _resolve_and_load(params)
    fixed = room_core.update_fixed_element(model, params)
    result = sync_room_to_scene(model)
    result["fixed_element"] = fixed
    return result


def remove_fixed_element(params):
    model, _ = _resolve_and_load(params)
    fixed = room_core.remove_fixed_element(model, params)
    result = sync_room_to_scene(model)
    result["removed_fixed_element"] = fixed
    return result


def move_wall(params):
    model, _ = _resolve_and_load(params)
    wall_ref = params.get("wall_id") or params.get("wall") or params.get("wall_side")
    if "delta" not in params:
        raise ValueError("move_wall requires delta")
    room_core.move_wall(model, wall_ref, params.get("delta"))
    return sync_room_to_scene(model)


def move_corner(params):
    model, _ = _resolve_and_load(params)
    corner = params.get("corner")
    dx = params.get("dx", 0.0)
    dy = params.get("dy", 0.0)
    if isinstance(params.get("delta"), (list, tuple)):
        dx = params["delta"][0]
        dy = params["delta"][1] if len(params["delta"]) > 1 else 0.0
    room_core.move_corner(model, corner, dx=dx, dy=dy)
    return sync_room_to_scene(model)


def _furniture_mains_for_room(room_id):
    seen = set()
    mains = []
    for obj in bpy.data.objects:
        if obj.get("layoutlab_room_id") != room_id:
            continue
        if obj.get("layoutlab_role") in (
            "room_floor",
            "room_wall",
            "room_opening",
            "room_fixed",
            "label",
        ):
            continue
        oid = obj.get("layoutlab_object_id")
        if not oid or oid in seen:
            continue
        if obj.get("layoutlab_part_type") == "main" or obj.parent is None:
            seen.add(oid)
            mains.append(obj)
    return mains


def move_room(params):
    """Translate room fabric; VALID furniture follows (DD-020). Blender adapter."""
    model, _ = _resolve_and_load(params)
    if model.get("locked"):
        raise ValueError(f"room is locked: cannot move_room ({model.get('room_id')})")
    origin = model["origin"]
    if "location" in params:
        loc = params["location"]
        dx = float(loc[0]) - float(origin[0])
        dy = float(loc[1]) - float(origin[1])
        dz = (float(loc[2]) - float(origin[2])) if len(loc) > 2 else 0.0
    else:
        delta = params.get("delta")
        if isinstance(delta, (list, tuple)):
            dx = float(delta[0]) if len(delta) > 0 else 0.0
            dy = float(delta[1]) if len(delta) > 1 else 0.0
            dz = float(delta[2]) if len(delta) > 2 else 0.0
        else:
            dx = float(params.get("dx", 0.0))
            dy = float(params.get("dy", 0.0))
            dz = float(params.get("dz", 0.0))

    room_id = model["room_id"]
    followed = []
    left_behind = []
    for obj in _furniture_mains_for_room(room_id):
        validity = str(obj.get("layoutlab_validity") or "VALID")
        if validity == "VALID":
            obj.location.x += dx
            obj.location.y += dy
            obj.location.z += dz
            followed.append(obj.get("layoutlab_object_id"))
        else:
            left_behind.append(obj.get("layoutlab_object_id"))

    room_core.update_room_model(
        model,
        {"location": [origin[0] + dx, origin[1] + dy, origin[2] + dz]},
    )
    result = sync_room_to_scene(model)
    result["followed"] = followed
    result["left_behind"] = left_behind
    result["dx"] = dx
    result["dy"] = dy
    result["dz"] = dz
    return result


def set_room_flags(params):
    model, _ = _resolve_and_load(params)
    for key in ("locked", "visible", "included_in_analysis", "protected_from_ai"):
        if key in params:
            model[key] = bool(params[key])
    return sync_room_to_scene(model)


def hide_room(params, *, hidden=True):
    params = dict(params or {})
    params["visible"] = not hidden
    return set_room_flags(params)


def duplicate_room(params):
    """Duplicate room fabric with new ids (furniture not auto-copied in Blender path)."""
    src, _ = _resolve_and_load(params)
    import copy
    import uuid

    clone = copy.deepcopy(src)
    clone["room_id"] = str(uuid.uuid4())
    clone["name"] = str(params.get("new_name") or f"{src.get('name', 'ROOM')}_copy")
    offset = params.get("offset") or [2.0, 0.0, 0.0]
    ox = float(offset[0]) if offset else 2.0
    oy = float(offset[1]) if offset and len(offset) > 1 else 0.0
    oz = float(offset[2]) if offset and len(offset) > 2 else 0.0
    so = src["origin"]
    clone["origin"] = [float(so[0]) + ox, float(so[1]) + oy, float(so[2]) + oz]
    wall_map = {}
    for wall in clone.get("walls", []):
        old = wall.get("wall_id")
        new = str(uuid.uuid4())
        if old:
            wall_map[old] = new
        wall["wall_id"] = new
    for opening in clone.get("openings", []):
        opening["opening_id"] = str(uuid.uuid4())
        if opening.get("wall_id") in wall_map:
            opening["wall_id"] = wall_map[opening["wall_id"]]
    for fixed in clone.get("fixed_elements", []):
        fixed["fixed_element_id"] = str(uuid.uuid4())
        if fixed.get("wall_id") in wall_map:
            fixed["wall_id"] = wall_map[fixed["wall_id"]]
    room_core._apply_rectangle_footprint(clone, existing=clone.get("walls"))
    return sync_room_to_scene(clone)
