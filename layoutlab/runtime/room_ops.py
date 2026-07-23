"""Spatial Project room ops (DD-020 / FC-001/WP-06 + room Z-rotate).

Independent rooms: transform participation, duplicate, flags, delete with members.
Furniture remains stored in world space; local = R(-rz)·(world - origin).
"""

from __future__ import annotations

import copy
import uuid
from typing import Any

from ..core import room as room_core
from . import furniture_ops


def _new_id() -> str:
    return str(uuid.uuid4())


def room_flags(model: dict) -> dict:
    return {
        "visible": bool(model.get("visible", True)),
        "locked": bool(model.get("locked", False)),
        "included_in_analysis": bool(model.get("included_in_analysis", True)),
        "protected_from_ai": bool(model.get("protected_from_ai", False)),
    }


def ensure_room_defaults(model: dict) -> dict:
    """Stamp DD-020 MVP flags on a room model (in place)."""
    model.setdefault("visible", True)
    model.setdefault("locked", False)
    model.setdefault("included_in_analysis", True)
    model.setdefault("protected_from_ai", False)
    model.setdefault("rotation_z_deg", 0.0)
    return model


def local_location(world_xyz, model: dict) -> list[float]:
    return room_core.room_world_to_local(model, world_xyz)


def world_from_local(local_xyz, model: dict) -> list[float]:
    return room_core.room_local_to_world(model, local_xyz)


def furniture_ids_for_room(store, room_id: str) -> list[str]:
    rid = str(room_id)
    seen: set[str] = set()
    out: list[str] = []
    for obj in store.objects:
        if not furniture_ops.is_furniture_part(obj):
            continue
        if obj.get("layoutlab_room_id") != rid:
            continue
        oid = obj.get("layoutlab_object_id")
        if not oid or oid in seen:
            continue
        seen.add(oid)
        out.append(str(oid))
    return out


def _require_room_unlocked(model: dict, *, action: str) -> None:
    if model.get("locked"):
        raise ValueError(f"room is locked: cannot {action} ({model.get('room_id')})")


def _resolve_live(session, room_ref) -> dict:
    if isinstance(room_ref, dict) and room_ref.get("room_id") and room_ref.get("room_id") in session._rooms:
        # Prefer live session model even if a deepcopy/export block was passed.
        return session._rooms[room_ref["room_id"]]
    if isinstance(room_ref, str):
        return session._resolve({"room_id": room_ref, "room": room_ref})
    return session._resolve(room_ref if isinstance(room_ref, dict) else {"room_id": room_ref})


def translate_room_origin(model: dict, dx: float, dy: float, dz: float = 0.0) -> list[float]:
    """Shift room fabric origin; walls/openings follow via footprint rebuild."""
    ox, oy, oz = (float(v) for v in model["origin"])
    new_origin = [ox + float(dx), oy + float(dy), oz + float(dz)]
    room_core.update_room_model(model, {"location": new_origin})
    return new_origin


def apply_room_transform_participation(
    session,
    model: dict,
    *,
    dx: float = 0.0,
    dy: float = 0.0,
    dz: float = 0.0,
    pivot_xy=None,
    degrees: float = 0.0,
) -> dict[str, list[str]]:
    """Move/rotate VALID furniture with the room; leave INVALID at world pose.

    Uses stored validity stamps from *before* the fabric change (do not refresh first).
    Translation: ``dx/dy/dz``. Rotation: spin furniture by ``degrees`` then orbit
    its location around ``pivot_xy`` by the same delta.
    """
    room_id = model["room_id"]
    followed: list[str] = []
    left_behind: list[str] = []
    store = session.mesh_store
    deg = float(degrees)
    do_rotate = pivot_xy is not None and abs(deg) >= 1e-12
    px = py = None
    if do_rotate:
        px, py = float(pivot_xy[0]), float(pivot_xy[1])

    for oid in furniture_ids_for_room(store, room_id):
        main = furniture_ops.main_part(store, oid)
        if main is None:
            continue
        state = furniture_ops.validity_of(main)
        if state != furniture_ops.VALIDITY_VALID:
            left_behind.append(oid)
            continue

        if do_rotate:
            # Spin in place, then orbit footprint center around room pivot.
            furniture_ops.rotate_object_z(
                session, oid, degrees=deg, absolute=False, honour_lock=False
            )
            main = furniture_ops.main_part(store, oid)
            params = furniture_ops._parse_params(main)
            gen = main.get("layoutlab_generator")
            hx, hy = furniture_ops.footprint_half_xy(params, gen)
            loc = [
                float(main.location.x),
                float(main.location.y),
                float(main.location.z),
            ]
            center = furniture_ops.corner_to_center(loc, hx, hy, float(main.rotation_z_deg or 0.0))
            rx, ry = room_core.rotate_z_xy(center[0] - px, center[1] - py, deg)
            new_center = [px + rx, py + ry, center[2]]
            new_loc = furniture_ops.center_to_corner(
                new_center, hx, hy, float(main.rotation_z_deg or 0.0)
            )
            furniture_ops.move_object(session, oid, new_loc, honour_lock=False)
        else:
            furniture_ops.move_object(
                session,
                oid,
                [
                    float(main.location.x) + float(dx),
                    float(main.location.y) + float(dy),
                    float(main.location.z) + float(dz),
                ],
                honour_lock=False,
            )
        followed.append(oid)

    furniture_ops.refresh_all_validity(store, session._rooms)
    return {"followed": followed, "left_behind": left_behind}


def move_room(
    session,
    room_ref,
    *,
    dx: float = 0.0,
    dy: float = 0.0,
    dz: float = 0.0,
    honour_lock: bool = True,
) -> dict:
    """Translate an independent room in world XY (and optional Z)."""
    model = _resolve_live(session, room_ref)
    ensure_room_defaults(model)
    if honour_lock:
        _require_room_unlocked(model, action="move_room")

    dx, dy, dz = float(dx), float(dy), float(dz)
    if abs(dx) < 1e-12 and abs(dy) < 1e-12 and abs(dz) < 1e-12:
        return {
            "room_id": model["room_id"],
            "origin": list(model["origin"]),
            "rotation_z_deg": float(model.get("rotation_z_deg") or 0.0),
            "followed": [],
            "left_behind": [],
            "unchanged": True,
        }

    translate_room_origin(model, dx, dy, dz)
    participation = apply_room_transform_participation(session, model, dx=dx, dy=dy, dz=dz)
    return {
        "room_id": model["room_id"],
        "name": model.get("name"),
        "origin": list(model["origin"]),
        "rotation_z_deg": float(model.get("rotation_z_deg") or 0.0),
        "dx": dx,
        "dy": dy,
        "dz": dz,
        **participation,
        "world_bounds": room_core.room_world_bounds(model),
    }


def rotate_room(
    session,
    room_ref,
    *,
    degrees: float,
    absolute: bool = False,
    honour_lock: bool = True,
) -> dict:
    """Rotate room about Z around footprint center; fabric + VALID furniture follow.

    Footprint stays locally axis-aligned; ``rotation_z_deg`` and ``origin`` update so
    the center stays fixed. Openings/fixed keep wall-local offsets.
    """
    model = _resolve_live(session, room_ref)
    ensure_room_defaults(model)
    if honour_lock:
        _require_room_unlocked(model, action="rotate_room")

    old_rz = float(model.get("rotation_z_deg") or 0.0)
    if absolute:
        new_rz = room_core.normalize_rotation_z_deg(degrees)
        delta = new_rz - old_rz
        # Shortest signed delta on circle
        if delta > 180.0:
            delta -= 360.0
        elif delta <= -180.0:
            delta += 360.0
    else:
        delta = float(degrees)
        new_rz = room_core.normalize_rotation_z_deg(old_rz + delta)

    if abs(delta) < 1e-12:
        return {
            "room_id": model["room_id"],
            "origin": list(model["origin"]),
            "rotation_z_deg": old_rz,
            "degrees": 0.0,
            "followed": [],
            "left_behind": [],
            "unchanged": True,
        }

    pivot = room_core.room_footprint_center(model)
    width = float(model["footprint"]["width"])
    depth = float(model["footprint"]["depth"])
    # New origin = center - R(new_rz)·(w/2, d/2)
    half_x, half_y = room_core.rotate_z_xy(width * 0.5, depth * 0.5, new_rz)
    new_origin = [
        float(pivot[0]) - half_x,
        float(pivot[1]) - half_y,
        float(model["origin"][2]) if len(model["origin"]) > 2 else 0.0,
    ]

    model["origin"] = new_origin
    model["rotation_z_deg"] = new_rz
    room_core._apply_rectangle_footprint(model, existing=model.get("walls"))

    participation = apply_room_transform_participation(
        session, model, pivot_xy=pivot, degrees=delta
    )
    return {
        "room_id": model["room_id"],
        "name": model.get("name"),
        "origin": list(model["origin"]),
        "rotation_z_deg": new_rz,
        "degrees": delta,
        "pivot": [float(pivot[0]), float(pivot[1]), float(pivot[2]) if len(pivot) > 2 else 0.0],
        **participation,
        "world_bounds": room_core.room_world_bounds(model),
    }


def set_room_flags(session, room_ref, flags: dict, *, honour_lock: bool = False) -> dict:
    model = _resolve_live(session, room_ref)
    ensure_room_defaults(model)
    allowed = {"locked", "visible", "included_in_analysis", "protected_from_ai"}
    updates = {k: v for k, v in (flags or {}).items() if k in allowed}
    if not updates:
        raise ValueError("set_room_flags requires at least one known flag")
    if honour_lock and model.get("locked"):
        only_unlock = set(updates.keys()) == {"locked"} and updates.get("locked") is False
        if not only_unlock:
            _require_room_unlocked(model, action="set_room_flags")

    if "locked" in updates:
        model["locked"] = bool(updates["locked"])
    if "visible" in updates:
        model["visible"] = bool(updates["visible"])
    if "included_in_analysis" in updates:
        model["included_in_analysis"] = bool(updates["included_in_analysis"])
    if "protected_from_ai" in updates:
        model["protected_from_ai"] = bool(updates["protected_from_ai"])

    return {
        "room_id": model["room_id"],
        "name": model.get("name"),
        **room_flags(model),
    }


def hide_room(session, room_ref, *, hidden: bool = True) -> dict:
    return set_room_flags(session, room_ref, {"visible": not hidden})


def delete_room_with_members(session, room_ref, *, honour_lock: bool = True) -> dict:
    """Remove room fabric and all furniture with matching membership."""
    model = _resolve_live(session, room_ref)
    ensure_room_defaults(model)
    if honour_lock:
        _require_room_unlocked(model, action="delete_room")

    room_id = model["room_id"]
    deleted_objects = []
    for oid in list(furniture_ids_for_room(session.mesh_store, room_id)):
        furniture_ops.delete_object(session, oid, honour_lock=False)
        deleted_objects.append(oid)

    name = model.get("name")
    del session._rooms[room_id]
    return {
        "deleted": name,
        "room_id": room_id,
        "deleted_object_ids": deleted_objects,
    }


def _remap_attachment_ids(model: dict, wall_id_map: dict[str, str]) -> None:
    for opening in model.get("openings", []):
        opening["opening_id"] = _new_id()
        wid = opening.get("wall_id")
        if wid in wall_id_map:
            opening["wall_id"] = wall_id_map[wid]
    for fixed in model.get("fixed_elements", []):
        fixed["fixed_element_id"] = _new_id()
        wid = fixed.get("wall_id")
        if wid in wall_id_map:
            fixed["wall_id"] = wall_id_map[wid]


def duplicate_room(
    session,
    room_ref,
    *,
    offset=(2.0, 0.0, 0.0),
    new_name: str | None = None,
    honour_lock: bool = True,
) -> dict:
    """Deep-copy room fabric + member furniture (incl. invalid + inactive attachments)."""
    src = _resolve_live(session, room_ref)
    ensure_room_defaults(src)
    if honour_lock:
        _require_room_unlocked(src, action="duplicate_room")

    ox = float(offset[0]) if offset is not None else 2.0
    oy = float(offset[1]) if offset is not None and len(offset) > 1 else 0.0
    oz = float(offset[2]) if offset is not None and len(offset) > 2 else 0.0

    clone = copy.deepcopy(src)
    old_room_id = src["room_id"]
    new_room_id = _new_id()
    clone["room_id"] = new_room_id
    clone["name"] = str(new_name or f"{src.get('name', 'ROOM')}_copy")

    wall_id_map: dict[str, str] = {}
    for wall in clone.get("walls", []):
        old_wid = wall.get("wall_id")
        new_wid = _new_id()
        if old_wid:
            wall_id_map[old_wid] = new_wid
        wall["wall_id"] = new_wid

    _remap_attachment_ids(clone, wall_id_map)

    so = src["origin"]
    clone["origin"] = [float(so[0]) + ox, float(so[1]) + oy, float(so[2]) + oz]
    room_core._apply_rectangle_footprint(clone, existing=clone.get("walls"))

    ensure_room_defaults(clone)
    session._store(clone)

    duplicated_objects: list[str] = []
    for oid in furniture_ids_for_room(session.mesh_store, old_room_id):
        result = furniture_ops.duplicate_object(
            session, oid, offset=(ox, oy, oz), honour_lock=False
        )
        new_oid = result.get("object_id")
        if not new_oid:
            continue
        for part in furniture_ops.objects_for_id(session.mesh_store, new_oid):
            part["layoutlab_room_id"] = new_room_id
        duplicated_objects.append(str(new_oid))

    furniture_ops.refresh_all_validity(session.mesh_store, session._rooms)

    return {
        "room_id": new_room_id,
        "name": clone["name"],
        "source_room_id": old_room_id,
        "origin": list(clone["origin"]),
        "duplicated_object_ids": duplicated_objects,
        "opening_count": len(clone.get("openings") or []),
        "fixed_element_count": len(clone.get("fixed_elements") or []),
        "world_bounds": room_core.room_world_bounds(clone),
        **room_flags(clone),
    }


def apply_room_command(session, cmd: dict) -> Any:
    """Dispatch WP-06 room actions (and enhanced delete_room)."""
    action = cmd.get("action")
    params = cmd.get("params") if isinstance(cmd.get("params"), dict) else {}
    room_ref = {
        "room_id": cmd.get("room_id") or params.get("room_id"),
        "room": cmd.get("room") or params.get("room"),
        "room_name": cmd.get("room_name") or params.get("room_name"),
        "name": cmd.get("name") or params.get("name"),
    }
    room_ref = {k: v for k, v in room_ref.items() if v}

    if action == "move_room":
        model = _resolve_live(session, room_ref or params or cmd)
        if "location" in params or "location" in cmd:
            loc = params.get("location") or cmd.get("location")
            origin = model["origin"]
            dx = float(loc[0]) - float(origin[0])
            dy = float(loc[1]) - float(origin[1])
            dz = (float(loc[2]) - float(origin[2])) if len(loc) > 2 else 0.0
            return move_room(session, model, dx=dx, dy=dy, dz=dz)

        dx = params.get("dx", cmd.get("dx", 0.0))
        dy = params.get("dy", cmd.get("dy", 0.0))
        dz = params.get("dz", cmd.get("dz", 0.0))
        delta = params.get("delta", cmd.get("delta"))
        if isinstance(delta, (list, tuple)):
            dx = delta[0] if len(delta) > 0 else 0.0
            dy = delta[1] if len(delta) > 1 else 0.0
            dz = delta[2] if len(delta) > 2 else 0.0
        return move_room(session, model, dx=dx, dy=dy, dz=dz)

    if action in ("rotate_room", "rotate_room_z"):
        model = _resolve_live(session, room_ref or params or cmd)
        degrees = params.get("degrees", cmd.get("degrees"))
        if degrees is None:
            degrees = params.get("rotation_z_deg", cmd.get("rotation_z_deg"))
        if degrees is None:
            raise ValueError("rotate_room requires degrees")
        absolute = bool(params.get("absolute", cmd.get("absolute", False)))
        if "rotation_z_deg" in params or "rotation_z_deg" in cmd:
            absolute = True
            degrees = params.get("rotation_z_deg", cmd.get("rotation_z_deg"))
        return rotate_room(session, model, degrees=float(degrees), absolute=absolute)

    if action == "duplicate_room":
        offset = cmd.get("offset") or params.get("offset") or (2.0, 0.0, 0.0)
        new_name = cmd.get("new_name") or params.get("new_name")
        # Avoid treating resolve `name` as the clone name.
        ref = dict(room_ref)
        if new_name and ref.get("name") == new_name:
            ref.pop("name", None)
        return duplicate_room(session, ref or params or cmd, offset=offset, new_name=new_name)

    if action in ("set_room_flags", "set_room_locked"):
        flags = dict(params)
        for key in ("locked", "visible", "included_in_analysis", "protected_from_ai"):
            if key in cmd:
                flags[key] = cmd[key]
        if action == "set_room_locked" and "locked" not in flags:
            if "value" in cmd or "value" in params:
                flags["locked"] = bool(cmd.get("value", params.get("value")))
            else:
                flags["locked"] = True
        for drop in ("room_id", "room", "room_name", "name", "object_id"):
            flags.pop(drop, None)
        return set_room_flags(session, room_ref or params or cmd, flags)

    if action == "hide_room":
        return hide_room(session, room_ref or params or cmd, hidden=True)

    if action == "show_room":
        return hide_room(session, room_ref or params or cmd, hidden=False)

    if action == "delete_room":
        return delete_room_with_members(session, room_ref or params or cmd)

    raise ValueError(f"unhandled room action {action!r}")
