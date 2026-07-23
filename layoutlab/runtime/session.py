"""In-memory Layout session: rooms + headless furniture (DD-014 Phase B/B2)."""

from __future__ import annotations

import copy
import uuid
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
from . import furniture_ops
from . import room_ops
from . import support_surfaces
from . import transactions as tx

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


LAYOUTLAB_VERSION = "0.10.67"

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
        "move_wall",
        "move_corner",
        # FC-001/WP-06 Spatial Project / independent rooms
        "move_room",
        "rotate_room",
        "rotate_room_z",
        "duplicate_room",
        "hide_room",
        "show_room",
        "set_room_flags",
        "set_room_locked",
        "delete_collection_objects",
        "delete_prefix",
        "run_generator",
        "analyze_layout",
        # FC-001/WP-03 semantic furniture ops (by object_id)
        "select_object",
        "move",
        "move_object",
        "rotate_z",
        "rotate_object_z",
        "duplicate",
        "delete",
        "hide",
        "show",
        "set_flags",
        "set_object_flags",
        "set_locked",
        "set_support",
        "place_on",
        # FC-001/WP-04 parametric resize
        "regenerate",
        "set_parameter",
        "resize",
    }
)

# Selection is session UI state — apply without Undo / revision bump when alone.
EPHEMERAL_ACTIONS = frozenset({"select_object"})


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
    if not bool(model.get("visible", True)):
        return []
    collection = model.get("collection") or "layoutlab_room"
    room_id = model["room_id"]
    prefix = f"{model['name']}_"
    objects = []

    floor_corners = [round_corner(c) for c in room_core.floor_world_corners(model)]
    floor_loc, floor_dims = room_core.floor_display_box(model)
    objects.append(
        _object_dict(
            name=f"{prefix}floor",
            collection=collection,
            location=floor_loc,
            dimensions=floor_dims,
            role="room_floor",
            object_id=room_id,
            world_bbox_corners=floor_corners,
            viewer=viewer_block_for_role("room_floor", corners=floor_corners),
            extra_props={"layoutlab_room_id": room_id},
            layoutlab_extra={"room_id": room_id},
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
                    layoutlab_extra={"room_id": room_id},
                )
            )

    for opening in model.get("openings", []):
        if not room_core.is_attachment_active(opening):
            continue
        loc, dims = room_core.opening_world_box(model, opening)
        opening_corners = room_core.opening_world_corners(model, opening)
        opening_mesh = room_core.box_mesh_from_corners(opening_corners)
        objects.append(
            _object_dict(
                name=f"{prefix}opening_{opening['name']}",
                collection=collection,
                location=loc,
                dimensions=dims,
                role="room_opening",
                object_id=room_id,
                world_bbox_corners=[round_corner(c) for c in opening_corners],
                viewer=viewer_block_for_role(
                    "room_opening",
                    display_type="WIRE",
                    mesh={
                        "vertices": [_r3(v) for v in opening_mesh["vertices"]],
                        "faces": triangulate_faces(opening_mesh["faces"]),
                    },
                ),
                entity_id=opening.get("opening_id"),
                extra_props={
                    "layoutlab_room_id": room_id,
                    "layoutlab_attachment_state": opening.get("state") or "ACTIVE",
                },
                layoutlab_extra={"room_id": room_id},
            )
        )

    for fixed in model.get("fixed_elements", []):
        if not room_core.is_attachment_active(fixed):
            continue
        loc, dims = room_core.fixed_element_world_box(model, fixed)
        fixed_corners = room_core.fixed_element_world_corners(model, fixed)
        fixed_mesh = room_core.box_mesh_from_corners(fixed_corners)
        objects.append(
            _object_dict(
                name=f"{prefix}fixed_{fixed['name']}",
                collection=collection,
                location=loc,
                dimensions=dims,
                role="room_fixed",
                object_id=room_id,
                world_bbox_corners=[round_corner(c) for c in fixed_corners],
                viewer=viewer_block_for_role(
                    "room_fixed",
                    mesh={
                        "vertices": [_r3(v) for v in fixed_mesh["vertices"]],
                        "faces": triangulate_faces(fixed_mesh["faces"]),
                    },
                ),
                entity_id=fixed.get("fixed_element_id"),
                extra_props={
                    "layoutlab_room_id": room_id,
                    "layoutlab_attachment_state": fixed.get("state") or "ACTIVE",
                },
                layoutlab_extra={"room_id": room_id},
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
    # Clearances always export oriented verts (AABB would look like scale/shear when rotated).
    export_mesh = (not is_wire or role == "clearance") and obj.vertices
    if export_mesh and len(obj.vertices) <= MAX_VIEWER_MESH_VERTS:
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

    rz = float(getattr(obj, "rotation_z_deg", 0.0) or 0.0)
    # Parent-only rotation is on the main part; children export their effective world Z.
    if obj.parent is not None:
        rz = float(getattr(obj.parent, "rotation_z_deg", 0.0) or 0.0) + rz

    data = _object_dict(
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
            "support_ref": obj.get("layoutlab_support_ref") or furniture_ops.SUPPORT_ROOM_FLOOR,
            "support_local_xy": support_surfaces.support_local_xy_of(obj),
            "surfaces": support_surfaces.surfaces_of(obj),
            "room_id": obj.get("layoutlab_room_id"),
            "validity": obj.get("layoutlab_validity") or furniture_ops.VALIDITY_VALID,
            "locked": bool(obj.props.get("locked") or obj.props.get("layoutlab_locked")),
            "included_in_analysis": bool(obj.props.get("included_in_analysis", True)),
            "protected_from_ai": bool(
                obj.props.get("protected_from_ai") or obj.props.get("layoutlab_protected_from_ai")
            ),
        },
    )
    data["rotation_euler_deg"] = [0.0, 0.0, round(rz, 4)]
    data["visible"] = furniture_ops.is_visible(obj)
    return data


def _furniture_export_object_with_room(obj, rooms_by_id: dict):
    exported = _furniture_export_object(obj)
    if not exported:
        return None
    room_id = obj.get("layoutlab_room_id")
    model = rooms_by_id.get(room_id) if room_id else None
    # Hidden rooms omit fabric and member furniture (same visibility rule).
    if model is not None and not bool(model.get("visible", True)):
        return None
    if model is not None:
        local = room_ops.local_location(exported["location"], model)
        exported["local_location"] = _r3(local)
        layoutlab = exported.setdefault("layoutlab", {})
        layoutlab["local_location"] = _r3(local)
        layoutlab["room_id"] = room_id
    return exported


def export_viewer_scene(session: "RoomSession") -> dict:
    """Build Spatial Project viewer export (DD-020): project + rooms[] + objects[]."""
    live_rooms = list(session._rooms.values())
    rooms_by_id = {m["room_id"]: m for m in live_rooms}
    rooms = [room_core.export_room_block(m) for m in live_rooms]
    objects = []
    for model in live_rooms:
        objects.extend(_room_objects(model))
    for obj in session.mesh_store.objects:
        exported = _furniture_export_object_with_room(obj, rooms_by_id)
        if exported:
            objects.append(exported)
    revision = int(getattr(session, "revision", 0) or 0)
    project_id = getattr(session, "project_id", None) or ""
    project_name = getattr(session, "project_name", None) or "Spatial Project"
    return {
        "layoutlab_version": LAYOUTLAB_VERSION,
        "viewer_schema": VIEWER_SCHEMA,
        "unit": "METRIC",
        "unit_scale": 1.0,
        "scene": "SpatialProject",
        "project_id": project_id,
        "project_name": project_name,
        "project": {
            "project_id": project_id,
            "name": project_name,
            "revision": revision,
        },
        "revision": revision,
        "generators": [],
        "note": (
            "Spatial Project export (DD-020). "
            "Coordinates/dimensions are LayoutLab scene units (native). "
            "With Metric and unit_scale=1.0, 1 unit = 1 meter. "
            "Furniture location is world; local_location = world - room.origin. "
            "analysis is from analyze_layout at export time."
        ),
        "rooms": rooms,
        "objects": objects,
        "selected_object_id": getattr(session, "selected_object_id", None),
        "analysis": analyze_session(session, {"scope": "scene", "include": ["clearances"]}),
    }


class RoomSession:
    """In-memory Spatial Project: rooms + furniture with semantic transactions (DD-018/020)."""

    def __init__(self, *, undo_depth: int = tx.DEFAULT_UNDO_DEPTH):
        self.project_id = str(uuid.uuid4())
        self.project_name = "Spatial Project"
        self._rooms: dict[str, dict] = {}
        self.mesh_store = MeshStore()
        self.agent_state = empty_agent_state()
        self.revision = 0
        self._undo = tx.TransactionHistory(max_depth=undo_depth)
        self._redo: list[tx.UndoEntry] = []
        self._preview: dict | None = None
        self.last_transaction: dict | None = None
        self.selected_object_id: str | None = None

    def clear(self):
        self._rooms.clear()
        self.mesh_store.clear()
        self.agent_state = empty_agent_state()
        self.revision = 0
        self._undo.clear()
        self._redo.clear()
        self._preview = None
        self.last_transaction = None
        self.selected_object_id = None

    def clone(self) -> "RoomSession":
        """Independent copy for dry-run (mutations do not touch the live session).

        Clones carry the current revision but an empty Undo/Redo history and no preview.
        """
        other = RoomSession(undo_depth=self._undo.max_depth)
        other.project_id = self.project_id
        other.project_name = self.project_name
        other._rooms = copy.deepcopy(self._rooms)
        other.mesh_store = self.mesh_store.clone()
        other.agent_state = copy.deepcopy(self.agent_state)
        other.revision = int(self.revision)
        other.selected_object_id = self.selected_object_id
        return other

    @property
    def can_undo(self) -> bool:
        return self._undo.can_undo and self._preview is None

    @property
    def can_redo(self) -> bool:
        return bool(self._redo) and self._preview is None

    @property
    def undo_depth(self) -> int:
        return self._undo.max_depth

    @property
    def undo_len(self) -> int:
        return len(self._undo)

    @property
    def redo_len(self) -> int:
        return len(self._redo)

    @property
    def preview_active(self) -> bool:
        return self._preview is not None

    def _snapshot_domain(self) -> dict:
        snap = tx.domain_snapshot(self._rooms, self.mesh_store, self.revision)
        snap["selected_object_id"] = self.selected_object_id
        snap["project_id"] = self.project_id
        snap["project_name"] = self.project_name
        return snap

    def _restore_domain(self, snap: dict) -> None:
        self._rooms = copy.deepcopy(snap["rooms"])
        self.mesh_store = snap["mesh_store"].clone()
        self.revision = int(snap["revision"])
        self.selected_object_id = snap.get("selected_object_id")
        if "project_id" in snap:
            self.project_id = snap["project_id"]
        if "project_name" in snap:
            self.project_name = snap["project_name"]

    def _transaction_payload(self, applied: dict, record: tx.TransactionRecord) -> dict:
        out = dict(applied)
        out["revision"] = self.revision
        out["base_revision"] = record.base_revision
        out["result_revision"] = record.result_revision
        out["transaction"] = record.to_dict()
        out["can_undo"] = self.can_undo
        out["can_redo"] = self.can_redo
        return out

    def _error_payload(
        self,
        *,
        error_code: str,
        error: str,
        extra: dict | None = None,
        status_ok: bool = False,
    ) -> dict:
        payload = {
            "ok": status_ok,
            "error_code": error_code,
            "error": error,
            "revision": self.revision,
            "can_undo": self.can_undo,
            "can_redo": self.can_redo,
            "results": [],
            "errors": [{"ok": False, "error": error, "error_code": error_code}],
            "export": export_viewer_scene(self),
        }
        if extra:
            payload.update(extra)
        return payload

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
        room_ops.ensure_room_defaults(model)
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
            **room_ops.room_flags(model),
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
            result = execute_generator_headless(generator, params, store=self.mesh_store)
            oid = (result or {}).get("object_id")
            if oid:
                furniture_ops.ensure_semantic_defaults(self.mesh_store, self._rooms, oid)
            return result

        if action in (
            "select_object",
            "move",
            "move_object",
            "rotate_z",
            "rotate_object_z",
            "duplicate",
            "delete",
            "hide",
            "show",
            "set_flags",
            "set_object_flags",
            "set_locked",
            "set_support",
            "place_on",
            "regenerate",
            "set_parameter",
            "resize",
        ):
            return furniture_ops.apply_furniture_command(self, cmd)

        if action in (
            "move_room",
            "rotate_room",
            "rotate_room_z",
            "duplicate_room",
            "hide_room",
            "show_room",
            "set_room_flags",
            "set_room_locked",
            "delete_room",
        ):
            return room_ops.apply_room_command(self, cmd)

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
            if model.get("locked"):
                raise ValueError(f"room is locked: cannot update_room ({model.get('room_id')})")
            old_origin = list(model["origin"])
            room_core.update_room_model(model, params)
            new_origin = list(model["origin"])
            dx = float(new_origin[0]) - float(old_origin[0])
            dy = float(new_origin[1]) - float(old_origin[1])
            dz = float(new_origin[2]) - float(old_origin[2])
            if abs(dx) > 1e-12 or abs(dy) > 1e-12 or abs(dz) > 1e-12:
                # Whole-room transform participation (DD-020) when origin changes.
                room_ops.apply_room_transform_participation(
                    self, model, dx=dx, dy=dy, dz=dz
                )
            else:
                furniture_ops.refresh_all_validity(self.mesh_store, self._rooms)
            return self._room_result(model)

        if action == "move_wall":
            params = cmd.get("params") or cmd
            model = self._resolve(params)
            if model.get("locked"):
                raise ValueError(f"room is locked: cannot move_wall ({model.get('room_id')})")
            wall_ref = (
                params.get("wall_id")
                or params.get("wall")
                or params.get("wall_side")
                or cmd.get("wall_id")
                or cmd.get("wall")
                or cmd.get("wall_side")
            )
            if "delta" in params:
                delta = params.get("delta")
            elif "delta" in cmd:
                delta = cmd.get("delta")
            else:
                raise ValueError("move_wall requires delta")
            room_core.move_wall(model, wall_ref, delta)
            furniture_ops.refresh_all_validity(self.mesh_store, self._rooms)
            return self._room_result(model)

        if action == "move_corner":
            params = cmd.get("params") or cmd
            model = self._resolve(params)
            if model.get("locked"):
                raise ValueError(f"room is locked: cannot move_corner ({model.get('room_id')})")
            corner = params.get("corner") or cmd.get("corner")
            dx = params.get("dx", cmd.get("dx", 0.0))
            dy = params.get("dy", cmd.get("dy", 0.0))
            if "delta" in params and isinstance(params.get("delta"), (list, tuple)):
                dx = params["delta"][0]
                dy = params["delta"][1] if len(params["delta"]) > 1 else 0.0
            room_core.move_corner(model, corner, dx=dx, dy=dy)
            furniture_ops.refresh_all_validity(self.mesh_store, self._rooms)
            return self._room_result(model)

        if action == "add_opening":
            params = cmd.get("params") or cmd
            model = self._resolve(params)
            if model.get("locked"):
                raise ValueError(f"room is locked: cannot add_opening ({model.get('room_id')})")
            opening = room_core.add_opening(model, params)
            return {"opening": opening, **self._room_result(model)}

        if action == "update_opening":
            params = cmd.get("params") or cmd
            model = self._resolve(params)
            if model.get("locked"):
                raise ValueError(f"room is locked: cannot update_opening ({model.get('room_id')})")
            opening = room_core.update_opening(model, params)
            return {"opening": opening, **self._room_result(model)}

        if action == "remove_opening":
            params = cmd.get("params") or cmd
            model = self._resolve(params)
            if model.get("locked"):
                raise ValueError(f"room is locked: cannot remove_opening ({model.get('room_id')})")
            removed = room_core.remove_opening(model, params)
            return {"removed": removed, **self._room_result(model)}

        if action == "add_fixed_element":
            params = cmd.get("params") or cmd
            model = self._resolve(params)
            if model.get("locked"):
                raise ValueError(f"room is locked: cannot add_fixed_element ({model.get('room_id')})")
            fixed = room_core.add_fixed_element(model, params)
            return {"fixed_element": fixed, **self._room_result(model)}

        if action == "update_fixed_element":
            params = cmd.get("params") or cmd
            model = self._resolve(params)
            if model.get("locked"):
                raise ValueError(
                    f"room is locked: cannot update_fixed_element ({model.get('room_id')})"
                )
            fixed = room_core.update_fixed_element(model, params)
            return {"fixed_element": fixed, **self._room_result(model)}

        if action == "remove_fixed_element":
            params = cmd.get("params") or cmd
            model = self._resolve(params)
            if model.get("locked"):
                raise ValueError(
                    f"room is locked: cannot remove_fixed_element ({model.get('room_id')})"
                )
            removed = room_core.remove_fixed_element(model, params)
            return {"removed": removed, **self._room_result(model)}

        raise ValueError(f"unhandled action {action!r}")

    def apply_commands(self, commands: list) -> dict:
        """Internal batch apply — does **not** create Undo or advance revision.

        Authoritative mutations must use :meth:`commit_commands` (DD-018).
        """
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
            "revision": self.revision,
        }

    def commit_commands(
        self,
        commands: list,
        *,
        actor: str = "user",
        action: str = "commands",
        description: str = "",
        base_revision: int | None = None,
    ) -> dict:
        """Authoritative commit: one semantic transaction + Undo unit (DD-018)."""
        if self._preview is not None:
            return self._error_payload(
                error_code=tx.ERROR_PREVIEW_ACTIVE,
                error="Cannot commit while a preview is active; commit_preview or cancel_preview first.",
            )

        try:
            actor_norm = tx.normalize_actor(actor)
        except ValueError as exc:
            return self._error_payload(error_code=tx.ERROR_INVALID_ACTOR, error=str(exc))

        if actor_norm == "ai" and base_revision is None:
            return self._error_payload(
                error_code=tx.ERROR_MISSING_BASE_REVISION,
                error="AI Apply requires base_revision (stale-proposal protection).",
                extra={"current_revision": self.revision},
            )

        effective_base = self.revision if base_revision is None else int(base_revision)
        if effective_base != self.revision:
            return self._error_payload(
                error_code=tx.ERROR_STALE_BASE_REVISION,
                error=(
                    f"stale base_revision: proposal base={effective_base} "
                    f"current={self.revision}; revalidate or regenerate."
                ),
                extra={
                    "base_revision": effective_base,
                    "current_revision": self.revision,
                    "note": "Blind apply of stale AI proposals is forbidden (DD-018).",
                },
            )

        ops = list(commands or [])
        if actor_norm == "ai":
            violations = tx.ai_protection_violations(self._rooms, self.mesh_store, ops)
            if violations:
                return self._error_payload(
                    error_code=tx.ERROR_PROTECTED_FROM_AI,
                    error="AI Apply blocked by protected_from_ai.",
                    extra={"violations": violations},
                )

        # Selection-only batches are ephemeral UI state (no Undo / no revision bump).
        if ops and all(
            isinstance(c, dict) and c.get("action") in EPHEMERAL_ACTIONS for c in ops
        ):
            applied = self.apply_commands(ops)
            applied["ephemeral"] = True
            applied["revision"] = self.revision
            applied["can_undo"] = self.can_undo
            applied["can_redo"] = self.can_redo
            return applied

        before = self._snapshot_domain()
        applied = self.apply_commands(ops)
        if not applied.get("ok"):
            self._restore_domain(before)
            out = dict(applied)
            out["ok"] = False
            out["error_code"] = tx.ERROR_COMMIT_FAILED
            out["error"] = "commit aborted; session restored to base revision"
            out["revision"] = self.revision
            out["base_revision"] = effective_base
            out["can_undo"] = self.can_undo
            out["can_redo"] = self.can_redo
            return out

        self.revision = int(self.revision) + 1
        record = tx.TransactionRecord(
            actor=actor_norm,
            action=str(action or "commands"),
            base_revision=effective_base,
            result_revision=self.revision,
            operations=copy.deepcopy(ops),
            description=str(description or ""),
        )
        self._undo.push(tx.UndoEntry(record=record, before=before))
        self._redo.clear()
        self.last_transaction = record.to_dict()
        # Refresh export so revision field matches post-commit state.
        applied["export"] = export_viewer_scene(self)
        return self._transaction_payload(applied, record)

    def begin_preview(
        self,
        commands: list | None = None,
        *,
        actor: str = "user",
        description: str = "",
    ) -> dict:
        """Start a non-authoritative preview (no Undo / no revision bump)."""
        if self._preview is not None:
            return self._error_payload(
                error_code=tx.ERROR_PREVIEW_ACTIVE,
                error="preview already active",
            )
        try:
            actor_norm = tx.normalize_actor(actor)
        except ValueError as exc:
            return self._error_payload(error_code=tx.ERROR_INVALID_ACTOR, error=str(exc))

        base_snapshot = self._snapshot_domain()
        ops = list(commands or [])
        self._preview = {
            "base_snapshot": base_snapshot,
            "base_revision": self.revision,
            "actor": actor_norm,
            "description": str(description or ""),
            "commands": ops,
        }
        if ops:
            applied = self.apply_commands(ops)
            if not applied.get("ok"):
                self._restore_domain(base_snapshot)
                self._preview = None
                out = dict(applied)
                out["preview"] = False
                out["error_code"] = tx.ERROR_COMMIT_FAILED
                out["error"] = "preview begin failed; session unchanged"
                return out
        return {
            "ok": True,
            "preview": True,
            "revision": self.revision,
            "base_revision": base_snapshot["revision"],
            "can_undo": self.can_undo,
            "can_redo": self.can_redo,
            "export": export_viewer_scene(self),
        }

    def update_preview(self, commands: list) -> dict:
        """Replace preview ops from the preview base snapshot (still non-authoritative)."""
        if self._preview is None:
            return self._error_payload(
                error_code=tx.ERROR_NO_PREVIEW,
                error="no active preview",
            )
        self._restore_domain(self._preview["base_snapshot"])
        ops = list(commands or [])
        self._preview["commands"] = ops
        applied = self.apply_commands(ops)
        if not applied.get("ok"):
            self._restore_domain(self._preview["base_snapshot"])
            self._preview["commands"] = []
            out = dict(applied)
            out["preview"] = True
            out["error_code"] = tx.ERROR_COMMIT_FAILED
            out["error"] = "preview update failed; restored preview base"
            out["revision"] = self.revision
            return out
        return {
            "ok": True,
            "preview": True,
            "revision": self.revision,
            "base_revision": self._preview["base_revision"],
            "can_undo": self.can_undo,
            "can_redo": self.can_redo,
            "export": export_viewer_scene(self),
        }

    def cancel_preview(self) -> dict:
        """Discard preview and restore the pre-preview domain state."""
        if self._preview is None:
            return {
                "ok": True,
                "cancelled": False,
                "preview": False,
                "revision": self.revision,
                "export": export_viewer_scene(self),
            }
        self._restore_domain(self._preview["base_snapshot"])
        self._preview = None
        return {
            "ok": True,
            "cancelled": True,
            "preview": False,
            "revision": self.revision,
            "can_undo": self.can_undo,
            "can_redo": self.can_redo,
            "export": export_viewer_scene(self),
        }

    def commit_preview(
        self,
        *,
        action: str | None = None,
        description: str | None = None,
    ) -> dict:
        """Commit the active preview as one transaction (revision advances once)."""
        if self._preview is None:
            return self._error_payload(
                error_code=tx.ERROR_NO_PREVIEW,
                error="no active preview",
            )
        ops = list(self._preview.get("commands") or [])
        actor = self._preview.get("actor") or "user"
        base_revision = self._preview.get("base_revision")
        desc = (
            description
            if description is not None
            else self._preview.get("description") or ""
        )
        act = action or "gesture"
        self._restore_domain(self._preview["base_snapshot"])
        self._preview = None
        return self.commit_commands(
            ops,
            actor=actor,
            action=act,
            description=desc,
            base_revision=base_revision,
        )

    def undo(self) -> dict:
        """Restore the project to the pre-transaction revision for the last commit."""
        if self._preview is not None:
            return self._error_payload(
                error_code=tx.ERROR_PREVIEW_ACTIVE,
                error="Cannot undo while a preview is active; cancel_preview first.",
            )
        entry = self._undo.pop()
        if entry is None:
            return self._error_payload(
                error_code=tx.ERROR_NOTHING_TO_UNDO,
                error="nothing to undo",
            )
        self._restore_domain(entry.before)
        self._redo.append(entry)
        self.last_transaction = None
        return {
            "ok": True,
            "undone": True,
            "revision": self.revision,
            "transaction": entry.record.to_dict(),
            "can_undo": self.can_undo,
            "can_redo": self.can_redo,
            "export": export_viewer_scene(self),
        }

    def redo(self) -> dict:
        """Reapply the same committed semantic operations (no AI / recipe re-invoke)."""
        if self._preview is not None:
            return self._error_payload(
                error_code=tx.ERROR_PREVIEW_ACTIVE,
                error="Cannot redo while a preview is active; cancel_preview first.",
            )
        if not self._redo:
            return self._error_payload(
                error_code=tx.ERROR_NOTHING_TO_REDO,
                error="nothing to redo",
            )
        entry = self._redo.pop()
        before = self._snapshot_domain()
        applied = self.apply_commands(copy.deepcopy(entry.record.operations))
        if not applied.get("ok"):
            self._restore_domain(before)
            out = dict(applied)
            out["ok"] = False
            out["error_code"] = tx.ERROR_COMMIT_FAILED
            out["error"] = "redo failed; session restored"
            out["revision"] = self.revision
            out["can_undo"] = self.can_undo
            out["can_redo"] = self.can_redo
            return out
        self.revision = int(entry.record.result_revision)
        self._undo.push(tx.UndoEntry(record=entry.record, before=before))
        self.last_transaction = entry.record.to_dict()
        applied["export"] = export_viewer_scene(self)
        return {
            "ok": True,
            "redone": True,
            "revision": self.revision,
            "transaction": entry.record.to_dict(),
            "can_undo": self.can_undo,
            "can_redo": self.can_redo,
            "export": applied["export"],
            "results": applied.get("results") or [],
        }
