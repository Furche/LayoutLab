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

    for opening in model.get("openings", []):
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
