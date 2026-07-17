"""In-memory Room Model session + headless viewer export (no bpy)."""

from __future__ import annotations

import copy
from typing import Any

from ..core import room as room_core
from ..protocol.viewer_export import VIEWER_SCHEMA, round_corner, viewer_block_for_role

# Keep in sync with layoutlab/__init__.py bl_info version when bumping the plugin.
LAYOUTLAB_VERSION = "0.10.8"

ROOM_ACTIONS = frozenset(
    {
        "create_room",
        "update_room",
        "delete_room",
        "add_opening",
        "update_opening",
        "remove_opening",
        "add_fixed_element",
        "update_fixed_element",
        "remove_fixed_element",
        "delete_collection_objects",
    }
)


def _r3(values):
    return [round(float(v), 4) for v in values]


def _box_corners(loc, dims):
    x, y, z = (float(v) for v in loc)
    dx, dy, dz = (float(v) for v in dims)
    return [
        [x, y, z],
        [x + dx, y, z],
        [x + dx, y + dy, z],
        [x, y + dy, z],
        [x, y, z + dz],
        [x + dx, y, z + dz],
        [x + dx, y + dy, z + dz],
        [x, y + dy, z + dz],
    ]


def _object_dict(
    *,
    name,
    collection,
    location,
    dimensions,
    role,
    room_id,
    world_bbox_corners,
    viewer=None,
    extra_props=None,
    entity_id=None,
):
    props = {
        "layoutlab_role": role,
        "layoutlab_room_id": room_id,
    }
    if entity_id:
        props["layoutlab_room_entity_id"] = entity_id
    if extra_props:
        props.update(extra_props)
    data = {
        "name": name,
        "type": "MESH",
        "collection": collection,
        "location": _r3(location),
        "rotation_euler_deg": [0.0, 0.0, 0.0],
        "scale": [1.0, 1.0, 1.0],
        "dimensions": _r3(dimensions),
        "visible": True,
        "world_bbox_corners": [_r3(c) for c in world_bbox_corners],
        "custom_properties": props,
        "layoutlab": {
            "object_id": room_id,
            "role": role,
            "part": role,
        },
    }
    if viewer:
        data["viewer"] = viewer
    return data


def _room_objects(model):
    """Synthesize viewer objects for one room (floor / wall quads / openings / fixed)."""
    collection = model.get("collection") or "layoutlab_room"
    room_id = model["room_id"]
    prefix = f"{model['name']}_"
    objects = []

    floor_loc, floor_dims = room_core.floor_display_box(model)
    objects.append(
        _object_dict(
            name=f"{prefix}floor",
            collection=collection,
            location=floor_loc,
            dimensions=floor_dims,
            role="room_floor",
            room_id=room_id,
            world_bbox_corners=_box_corners(floor_loc, floor_dims),
            viewer=viewer_block_for_role("room_floor"),
        )
    )

    for wall in model.get("walls", []):
        panels = room_core.wall_display_panels(model, wall)
        for index, panel in enumerate(panels):
            corners = [round_corner(c) for c in panel["corners"]]
            name = (
                f"{prefix}wall_{wall['side']}"
                if len(panels) == 1
                else f"{prefix}wall_{wall['side']}_p{index}"
            )
            xs = [c[0] for c in corners]
            ys = [c[1] for c in corners]
            zs = [c[2] for c in corners]
            loc = [min(xs), min(ys), min(zs)]
            dims = [
                max(xs) - min(xs) or 0.001,
                max(ys) - min(ys) or 0.001,
                max(zs) - min(zs) or 0.001,
            ]
            objects.append(
                _object_dict(
                    name=name,
                    collection=collection,
                    location=loc,
                    dimensions=dims,
                    role="room_wall",
                    room_id=room_id,
                    world_bbox_corners=corners,
                    viewer=viewer_block_for_role("room_wall", corners=corners),
                    entity_id=wall.get("wall_id"),
                    extra_props={
                        "layoutlab_wall_side": wall["side"],
                        "layoutlab_wall_facing": "inward",
                        "layoutlab_wall_panel_index": index,
                    },
                )
            )

    for opening in model.get("openings", []):
        loc, dims = room_core.opening_world_box(model, opening)
        objects.append(
            _object_dict(
                name=f"{prefix}opening_{opening['name']}",
                collection=collection,
                location=loc,
                dimensions=dims,
                role="room_opening",
                room_id=room_id,
                world_bbox_corners=_box_corners(loc, dims),
                viewer=viewer_block_for_role("room_opening", display_type="WIRE"),
                entity_id=opening.get("opening_id"),
            )
        )

    for fixed in model.get("fixed_elements", []):
        loc, dims = room_core.fixed_element_world_box(model, fixed)
        objects.append(
            _object_dict(
                name=f"{prefix}fixed_{fixed['name']}",
                collection=collection,
                location=loc,
                dimensions=dims,
                role="room_fixed",
                room_id=room_id,
                world_bbox_corners=_box_corners(loc, dims),
                viewer=viewer_block_for_role("room_fixed"),
                entity_id=fixed.get("fixed_element_id"),
            )
        )

    return objects


def export_viewer_scene(session: "RoomSession") -> dict:
    """Build viewer_schema export dict from session rooms (same shape as Blender export)."""
    rooms = [room_core.export_room_block(m) for m in session.list_rooms()]
    objects = []
    for model in session.list_rooms():
        objects.extend(_room_objects(model))
    return {
        "layoutlab_version": LAYOUTLAB_VERSION,
        "viewer_schema": VIEWER_SCHEMA,
        "unit": "METRIC",
        "unit_scale": 1.0,
        "scene": "RoomSession",
        "generators": [],
        "note": (
            "Coordinates/dimensions are LayoutLab scene units (native). "
            "With Metric and unit_scale=1.0, 1 unit = 1 meter. "
            "Headless Room Model export (DD-014 Phase B)."
        ),
        "rooms": rooms,
        "objects": objects,
        "analysis": {
            "analyzed": False,
            "scope": "scene",
            "summary": {"errors": 0, "warnings": 0, "info": 0},
            "findings": [],
            "note": "analyze_layout not available on headless room session in this slice",
        },
    }


class RoomSession:
    """In-memory store of room models keyed by room_id / name."""

    def __init__(self):
        self._rooms: dict[str, dict] = {}  # room_id -> model

    def clear(self):
        self._rooms.clear()

    def list_rooms(self):
        return [copy.deepcopy(m) for m in self._rooms.values()]

    def get_by_name(self, name):
        for model in self._rooms.values():
            if model.get("name") == name:
                return model
        return None

    def get_by_id(self, room_id):
        return self._rooms.get(room_id)

    def _resolve(self, params):
        params = params or {}
        room_id = params.get("room_id")
        room_name = params.get("room") or params.get("room_name") or params.get("name")
        if room_id and room_id in self._rooms:
            return self._rooms[room_id]
        if room_name:
            model = self.get_by_name(room_name)
            if model:
                return model
        raise ValueError(f"room not found: {room_id or room_name}")

    def _store(self, model):
        self._rooms[model["room_id"]] = model
        return model

    def _room_result(self, model):
        return {
            "room_id": model["room_id"],
            "name": model["name"],
            "created": model["name"],
            "type": "room_model",
            "footprint": copy.deepcopy(model["footprint"]),
            "height": model["height"],
            "wall_count": len(model.get("walls", [])),
            "wall_panel_count": sum(
                len(room_core.wall_display_panels(model, wall)) for wall in model.get("walls", [])
            ),
            "opening_count": len(model.get("openings", [])),
            "fixed_element_count": len(model.get("fixed_elements", [])),
            "collection": model.get("collection") or "layoutlab_room",
            "world_bounds": room_core.room_world_bounds(model),
        }

    def apply_command(self, cmd: dict) -> Any:
        action = cmd.get("action")
        if action not in ROOM_ACTIONS:
            raise ValueError(
                f"unsupported action {action!r} in room write slice "
                f"(allowed: {sorted(ROOM_ACTIONS)})"
            )

        if action == "delete_collection_objects":
            collection = cmd.get("collection")
            if not collection:
                raise ValueError("delete_collection_objects requires collection")
            removed = [
                rid
                for rid, model in list(self._rooms.items())
                if (model.get("collection") or "layoutlab_room") == collection
            ]
            for rid in removed:
                del self._rooms[rid]
            return {"deleted": len(removed), "collection": collection, "room_ids": removed}

        if action == "create_room":
            params = cmd.get("params") or cmd
            model = room_core.create_room_model(params)
            # Replace existing room with same name in same collection
            existing = self.get_by_name(model["name"])
            if existing and existing.get("collection") == model.get("collection"):
                del self._rooms[existing["room_id"]]
            self._store(model)
            return self._room_result(model)

        if action == "update_room":
            params = cmd.get("params") or cmd
            model = self._resolve(params)
            room_core.update_room_model(model, params)
            return self._room_result(model)

        if action == "delete_room":
            params = cmd.get("params") or cmd
            model = self._resolve(params)
            del self._rooms[model["room_id"]]
            return {"deleted": model["name"], "room_id": model["room_id"]}

        if action == "add_opening":
            params = cmd.get("params") or cmd
            model = self._resolve(params)
            opening = room_core.add_opening(model, params)
            return {"opening": opening, **self._room_result(model)}

        if action == "update_opening":
            params = cmd.get("params") or cmd
            model = self._resolve(params)
            opening = room_core.update_opening(model, params)
            return {"opening": opening, **self._room_result(model)}

        if action == "remove_opening":
            params = cmd.get("params") or cmd
            model = self._resolve(params)
            removed = room_core.remove_opening(model, params)
            return {"removed": removed, **self._room_result(model)}

        if action == "add_fixed_element":
            params = cmd.get("params") or cmd
            model = self._resolve(params)
            fixed = room_core.add_fixed_element(model, params)
            return {"fixed_element": fixed, **self._room_result(model)}

        if action == "update_fixed_element":
            params = cmd.get("params") or cmd
            model = self._resolve(params)
            fixed = room_core.update_fixed_element(model, params)
            return {"fixed_element": fixed, **self._room_result(model)}

        if action == "remove_fixed_element":
            params = cmd.get("params") or cmd
            model = self._resolve(params)
            removed = room_core.remove_fixed_element(model, params)
            return {"removed": removed, **self._room_result(model)}

        raise ValueError(f"unhandled action {action!r}")

    def apply_commands(self, commands: list) -> dict:
        results = []
        errors = []
        for index, cmd in enumerate(commands or []):
            try:
                results.append({"index": index, "ok": True, "result": self.apply_command(cmd)})
            except Exception as exc:
                errors.append({"index": index, "ok": False, "error": str(exc), "action": cmd.get("action")})
                results.append({"index": index, "ok": False, "error": str(exc), "action": cmd.get("action")})
        ok = not errors
        return {
            "ok": ok,
            "results": results,
            "errors": errors,
            "export": export_viewer_scene(self),
        }
