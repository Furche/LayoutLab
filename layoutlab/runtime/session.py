"""In-memory Layout session: rooms + headless furniture (DD-014 Phase B/B2)."""

from __future__ import annotations

import copy
from typing import Any

from ..core import room as room_core
from ..protocol.viewer_export import (
    MAX_VIEWER_MESH_VERTS,
    SKIP_VIEWER_ROLES,
    VIEWER_SCHEMA,
    round_corner,
    viewer_block_for_role,
)
from .analyze import analyze_session
from .headless_api import execute_generator_headless
from .mesh_store import MeshStore, triangulate_faces

# Keep in sync with layoutlab/__init__.py bl_info version when bumping the plugin.

AGENT_STATE_SCHEMA = "0.1.0"


def empty_agent_state() -> dict:
    """Lightweight session memory — not chat transcript (agent_tool_contract)."""
    return {
        "schema": AGENT_STATE_SCHEMA,
        "goal": None,
        "requirements": None,
        "open_questions": [],
        "last_proposal_id": None,
        "last_analysis_summary": None,
        "last_placement_fp": None,
        "last_reply": None,
        "last_shortlist": None,
        "last_selected_id": None,
    }


LAYOUTLAB_VERSION = "0.10.35"

SESSION_ACTIONS = frozenset(
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
        "delete_prefix",
        "run_generator",
        "analyze_layout",
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
    object_id,
    world_bbox_corners,
    viewer=None,
    extra_props=None,
    entity_id=None,
    obj_type="MESH",
    layoutlab_extra=None,
):
    props = {
        "layoutlab_role": role,
    }
    if object_id:
        props["layoutlab_object_id"] = object_id
    if entity_id:
        props["layoutlab_room_entity_id"] = entity_id
    if extra_props:
        props.update(extra_props)
    layoutlab = {
        "object_id": object_id,
        "role": role,
        "part": (layoutlab_extra or {}).get("part") or role,
    }
    if layoutlab_extra:
        layoutlab.update({k: v for k, v in layoutlab_extra.items() if v is not None})
    data = {
        "name": name,
        "type": obj_type,
        "collection": collection,
        "location": _r3(location),
        "rotation_euler_deg": [0.0, 0.0, 0.0],
        "scale": [1.0, 1.0, 1.0],
        "dimensions": _r3(dimensions),
        "visible": True,
        "world_bbox_corners": [_r3(c) for c in world_bbox_corners],
        "custom_properties": {
            k: v for k, v in props.items() if isinstance(v, (str, int, float, bool))
        },
        "layoutlab": layoutlab,
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
            object_id=room_id,
            world_bbox_corners=_box_corners(floor_loc, floor_dims),
            viewer=viewer_block_for_role("room_floor"),
            extra_props={"layoutlab_room_id": room_id},
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
                    object_id=room_id,
                    world_bbox_corners=corners,
                    viewer=viewer_block_for_role("room_wall", corners=corners),
                    entity_id=wall.get("wall_id"),
                    extra_props={
                        "layoutlab_room_id": room_id,
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
                object_id=room_id,
                world_bbox_corners=_box_corners(loc, dims),
                viewer=viewer_block_for_role("room_opening", display_type="WIRE"),
                entity_id=opening.get("opening_id"),
                extra_props={"layoutlab_room_id": room_id},
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
                object_id=room_id,
                world_bbox_corners=_box_corners(loc, dims),
                viewer=viewer_block_for_role("room_fixed"),
                entity_id=fixed.get("fixed_element_id"),
                extra_props={"layoutlab_room_id": room_id},
            )
        )

    return objects


def _furniture_export_object(obj):
    role = obj.get("layoutlab_role") or ""
    if role in SKIP_VIEWER_ROLES or obj.type == "FONT":
        return None

    object_id = obj.get("layoutlab_object_id")
    world_origin = obj.world_origin()
    dims = obj.dimensions()
    corners = obj.world_bbox_corners()

    display_type = obj.display_type
    is_wire = role == "clearance" or str(display_type).upper() == "WIRE"
    mesh = None
    if not is_wire and obj.vertices and len(obj.vertices) <= MAX_VIEWER_MESH_VERTS:
        mesh = {
            "vertices": [_r3(v) for v in obj.world_vertices()],
            "faces": triangulate_faces(obj.faces),
        }

    viewer = viewer_block_for_role(
        role,
        display_type=display_type if is_wire else None,
        mesh=mesh,
    )

    extra = {
        k: v
        for k, v in obj.props.items()
        if isinstance(v, (str, int, float, bool)) and k != "layoutlab_role"
    }
    if object_id:
        extra["layoutlab_object_id"] = object_id

    return _object_dict(
        name=obj.name,
        collection=obj.collection,
        location=world_origin,
        dimensions=dims,
        role=role or "mesh",
        object_id=object_id,
        world_bbox_corners=corners,
        viewer=viewer,
        extra_props=extra,
        obj_type=obj.type,
        layoutlab_extra={
            "part": obj.get("layoutlab_part"),
            "generator": obj.get("layoutlab_generator"),
            "part_type": obj.get("layoutlab_part_type"),
        },
    )


def export_viewer_scene(session: "RoomSession") -> dict:
    """Build viewer_schema export dict from session rooms + furniture."""
    rooms = [room_core.export_room_block(m) for m in session.list_rooms()]
    objects = []
    for model in session.list_rooms():
        objects.extend(_room_objects(model))
    for obj in session.mesh_store.objects:
        exported = _furniture_export_object(obj)
        if exported:
            objects.append(exported)
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
            "Headless Room Model + generator export (DD-014 Phase B2). "
            "analysis is from analyze_layout at export time."
        ),
        "rooms": rooms,
        "objects": objects,
        "analysis": analyze_session(session, {"scope": "scene", "include": ["clearances"]}),
    }


class RoomSession:
    """In-memory rooms + furniture mesh store."""

    def __init__(self):
        self._rooms: dict[str, dict] = {}
        self.mesh_store = MeshStore()
        self.agent_state = empty_agent_state()

    def clear(self):
        self._rooms.clear()
        self.mesh_store.clear()
        self.agent_state = empty_agent_state()

    def clone(self) -> "RoomSession":
        """Independent copy for dry-run (mutations do not touch the live session)."""
        other = RoomSession()
        other._rooms = copy.deepcopy(self._rooms)
        other.mesh_store = self.mesh_store.clone()
        other.agent_state = copy.deepcopy(self.agent_state)
        return other

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
        if action not in SESSION_ACTIONS:
            raise ValueError(
                f"unsupported action {action!r} in headless session "
                f"(allowed: {sorted(SESSION_ACTIONS)})"
            )

        if action == "delete_collection_objects":
            params = cmd.get("params") if isinstance(cmd.get("params"), dict) else {}
            collection = cmd.get("collection") or params.get("collection")
            if not collection:
                raise ValueError("delete_collection_objects requires collection")
            removed_rooms = [
                rid
                for rid, model in list(self._rooms.items())
                if (model.get("collection") or "layoutlab_room") == collection
            ]
            for rid in removed_rooms:
                del self._rooms[rid]
            removed_meshes = self.mesh_store.delete_collection(collection)
            return {
                "deleted": len(removed_rooms) + removed_meshes,
                "collection": collection,
                "room_ids": removed_rooms,
                "mesh_count": removed_meshes,
            }

        if action == "delete_prefix":
            params = cmd.get("params") if isinstance(cmd.get("params"), dict) else {}
            prefix = cmd.get("prefix") or params.get("prefix")
            if not prefix:
                raise ValueError("delete_prefix requires prefix")
            n = self.mesh_store.delete_prefix(prefix)
            return {"deleted": n, "prefix": prefix}

        if action == "run_generator":
            generator = cmd.get("generator")
            if not generator:
                raise ValueError("run_generator requires generator")
            params = dict(cmd.get("params") or {})
            # Accept flat generator keys (LLM often omits params{}).
            for key in (
                "name",
                "location",
                "width",
                "depth",
                "length",
                "height",
                "head_side",
                "front_side",
                "collection",
                "show_clearance",
                "object_id",
            ):
                if key in cmd and key not in params:
                    params[key] = cmd[key]
            return execute_generator_headless(generator, params, store=self.mesh_store)

        if action == "analyze_layout":
            return analyze_session(self, cmd)

        if action == "create_room":
            params = cmd.get("params") or cmd
            model = room_core.create_room_model(params)
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
                errors.append(
                    {"index": index, "ok": False, "error": str(exc), "action": cmd.get("action")}
                )
                results.append(
                    {"index": index, "ok": False, "error": str(exc), "action": cmd.get("action")}
                )
        ok = not errors
        return {
            "ok": ok,
            "results": results,
            "errors": errors,
            "export": export_viewer_scene(self),
        }
