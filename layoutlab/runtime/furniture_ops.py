"""Semantic furniture manipulation for headless Core (DD-019 / FC-001/WP-03)."""

from __future__ import annotations

import copy
import json
import uuid
from typing import Any

from ..core import room as room_core
from .mesh_store import MeshObject
from . import support_surfaces as supports

SUPPORT_ROOM_FLOOR = supports.SUPPORT_ROOM_FLOOR

VALIDITY_VALID = "VALID"
VALIDITY_OUTSIDE = "INVALID_OUTSIDE_ROOM"
VALIDITY_WALL = "INVALID_INTERSECTS_WALL"
VALIDITY_OFF_SUPPORT = supports.VALIDITY_OFF_SUPPORT
VALIDITY_NO_SUPPORT = supports.VALIDITY_NO_SUPPORT

# Tolerance for "inside room" / wall AABB tests (meters).
_BOUNDS_EPS = 1e-4
_WALL_HIT_EPS = 0.02


def is_furniture_part(obj: MeshObject) -> bool:
    if not obj.get("layoutlab_object_id"):
        return False
    role = obj.get("layoutlab_role") or ""
    if role in ("room_floor", "room_wall", "room_opening", "room_fixed", "label"):
        return False
    return True


def objects_for_id(store, object_id: str) -> list[MeshObject]:
    oid = str(object_id)
    return [o for o in store.objects if o.get("layoutlab_object_id") == oid]


def main_part(store, object_id: str) -> MeshObject | None:
    parts = objects_for_id(store, object_id)
    if not parts:
        return None
    for obj in parts:
        if obj.get("layoutlab_part_type") == "main":
            return obj
    for obj in parts:
        if obj.parent is None:
            return obj
    return parts[0]


def _parse_params(obj: MeshObject) -> dict:
    raw = obj.get("layoutlab_params")
    if isinstance(raw, dict):
        return dict(raw)
    if isinstance(raw, str) and raw.strip():
        try:
            data = json.loads(raw)
            return data if isinstance(data, dict) else {}
        except json.JSONDecodeError:
            return {}
    return {}


def _write_params(obj: MeshObject, params: dict) -> None:
    obj["layoutlab_params"] = json.dumps(params, ensure_ascii=False, sort_keys=True)


def _flag_bool(obj: MeshObject, key: str, default: bool = False) -> bool:
    if key in obj.props:
        return bool(obj.props.get(key))
    # Accept layoutlab_ prefix aliases.
    alt = f"layoutlab_{key}" if not key.startswith("layoutlab_") else key
    if alt in obj.props:
        return bool(obj.props.get(alt))
    return default


def is_locked(obj: MeshObject) -> bool:
    return _flag_bool(obj, "locked") or _flag_bool(obj, "layoutlab_locked")


def is_visible(obj: MeshObject) -> bool:
    if "visible" in obj.props:
        return bool(obj.props.get("visible"))
    if "layoutlab_visible" in obj.props:
        return bool(obj.props.get("layoutlab_visible"))
    return True


def support_ref(obj: MeshObject) -> str:
    return str(
        obj.get("layoutlab_support_ref")
        or obj.get("support_ref")
        or SUPPORT_ROOM_FLOOR
    )


def validity_of(obj: MeshObject) -> str:
    return str(obj.get("layoutlab_validity") or VALIDITY_VALID)


def ensure_semantic_defaults(store, rooms: dict, object_id: str | None = None) -> None:
    """Stamp support_ref / room membership / flags on furniture after create or load."""
    targets = (
        objects_for_id(store, object_id)
        if object_id
        else [o for o in store.objects if is_furniture_part(o)]
    )
    room_by_collection = {}
    for rid, model in (rooms or {}).items():
        coll = model.get("collection") or "layoutlab_room"
        room_by_collection.setdefault(coll, rid)

    seen_ids = set()
    for obj in targets:
        oid = obj.get("layoutlab_object_id")
        if not oid or oid in seen_ids:
            continue
        seen_ids.add(oid)
        main = main_part(store, oid) or obj
        if not main.get("layoutlab_support_ref"):
            main["layoutlab_support_ref"] = SUPPORT_ROOM_FLOOR
        supports.stamp_host_surfaces(main)
        if "locked" not in main.props and "layoutlab_locked" not in main.props:
            main["locked"] = False
        if "visible" not in main.props and "layoutlab_visible" not in main.props:
            main["visible"] = True
        if "included_in_analysis" not in main.props:
            main["included_in_analysis"] = True
        if "protected_from_ai" not in main.props and "layoutlab_protected_from_ai" not in main.props:
            main["protected_from_ai"] = False
        if not main.get("layoutlab_room_id"):
            rid = room_by_collection.get(main.collection or "layoutlab_room")
            if rid:
                main["layoutlab_room_id"] = rid
        # Mirror key flags onto sibling parts for export consistency.
        for part in objects_for_id(store, oid):
            if part is main:
                continue
            for key in (
                "layoutlab_support_ref",
                "layoutlab_room_id",
                "layoutlab_support_local_xy",
                "locked",
                "visible",
                "included_in_analysis",
                "protected_from_ai",
            ):
                if key in main.props and key not in part.props:
                    part[key] = main.props[key]
        refresh_validity(store, rooms, oid)


def _xy_bbox(obj: MeshObject) -> tuple[float, float, float, float]:
    corners = obj.world_bbox_corners()
    xs = [c[0] for c in corners]
    ys = [c[1] for c in corners]
    return min(xs), min(ys), max(xs), max(ys)


def _aabb_overlap_2d(a, b, eps=_WALL_HIT_EPS) -> bool:
    ax0, ay0, ax1, ay1 = a
    bx0, by0, bx1, by1 = b
    return not (
        ax1 <= bx0 + eps
        or bx1 <= ax0 + eps
        or ay1 <= by0 + eps
        or by1 <= ay0 + eps
    )


def _furniture_solid_bbox(store, object_id: str) -> tuple[float, float, float, float] | None:
    """XY bounds of non-clearance parts (avoid clearance inflating invalidity)."""
    xs: list[float] = []
    ys: list[float] = []
    for obj in objects_for_id(store, object_id):
        role = obj.get("layoutlab_role") or ""
        if role == "clearance" or obj.get("layoutlab_clearance_name"):
            continue
        if str(obj.display_type).upper() == "WIRE" and role != "body":
            # Keep wire body-like parts; skip pure clearance wires already handled.
            if not obj.get("layoutlab_generator"):
                continue
        x0, y0, x1, y1 = _xy_bbox(obj)
        xs.extend([x0, x1])
        ys.extend([y0, y1])
    if not xs:
        main = main_part(store, object_id)
        if not main:
            return None
        return _xy_bbox(main)
    return min(xs), min(ys), max(xs), max(ys)


def compute_validity(store, rooms: dict, object_id: str) -> str:
    main = main_part(store, object_id)
    if not main:
        return VALIDITY_VALID

    # Support-surface checks first (DD-021) — may be off-support while still in room.
    support_state = _compute_support_validity(store, object_id)
    if support_state in (VALIDITY_NO_SUPPORT, VALIDITY_OFF_SUPPORT):
        return support_state

    bbox = _furniture_solid_bbox(store, object_id)
    if not bbox:
        return VALIDITY_VALID

    room_id = main.get("layoutlab_room_id")
    model = None
    if room_id and room_id in (rooms or {}):
        model = rooms[room_id]
    else:
        coll = main.collection or "layoutlab_room"
        for m in (rooms or {}).values():
            if (m.get("collection") or "layoutlab_room") == coll:
                model = m
                break
    if not model:
        return VALIDITY_VALID

    bounds = room_core.room_world_bounds(model)
    rmin = bounds["min"]
    rmax = bounds["max"]
    fx0, fy0, fx1, fy1 = bbox
    # Outside room footprint (XY) — test in room-local frame so rotation works.
    corners_xy = [
        (fx0, fy0),
        (fx1, fy0),
        (fx0, fy1),
        (fx1, fy1),
    ]
    local_pts = [
        room_core.room_world_to_local(model, [x, y, 0.0]) for x, y in corners_xy
    ]
    lx0 = min(p[0] for p in local_pts)
    ly0 = min(p[1] for p in local_pts)
    lx1 = max(p[0] for p in local_pts)
    ly1 = max(p[1] for p in local_pts)
    width = float(model["footprint"]["width"])
    depth = float(model["footprint"]["depth"])
    if (
        lx0 < -_BOUNDS_EPS
        or ly0 < -_BOUNDS_EPS
        or lx1 > width + _BOUNDS_EPS
        or ly1 > depth + _BOUNDS_EPS
    ):
        return VALIDITY_OUTSIDE

    # Intersects wall display panels (inward plane AABBs in local space).
    for wall in model.get("walls") or []:
        for panel in room_core.wall_display_panels(model, wall):
            corners = panel.get("corners") or []
            if len(corners) < 2:
                continue
            local_wall = [
                room_core.room_world_to_local(model, c) for c in corners
            ]
            xs = [c[0] for c in local_wall]
            ys = [c[1] for c in local_wall]
            wall_bb = (min(xs), min(ys), max(xs), max(ys))
            wx0, wy0, wx1, wy1 = wall_bb
            if abs(wx1 - wx0) < _WALL_HIT_EPS:
                mid = 0.5 * (wx0 + wx1)
                wx0, wx1 = mid - _WALL_HIT_EPS, mid + _WALL_HIT_EPS
            if abs(wy1 - wy0) < _WALL_HIT_EPS:
                mid = 0.5 * (wy0 + wy1)
                wy0, wy1 = mid - _WALL_HIT_EPS, mid + _WALL_HIT_EPS
            if _aabb_overlap_2d((lx0, ly0, lx1, ly1), (wx0, wy0, wx1, wy1), eps=0.0):
                return VALIDITY_WALL

    return VALIDITY_VALID


def _compute_support_validity(store, object_id: str) -> str | None:
    """Return support invalidity code, or None when support is floor / ok."""
    main = main_part(store, object_id)
    if not main:
        return None
    ref = support_ref(main)
    if ref == SUPPORT_ROOM_FLOOR:
        return None
    parsed = supports.parse_object_support(ref)
    if not parsed:
        return VALIDITY_NO_SUPPORT
    host_id, surface_id = parsed
    host = main_part(store, host_id)
    if host is None:
        return VALIDITY_NO_SUPPORT
    supports.stamp_host_surfaces(host)
    surface = supports.find_surface(host, surface_id)
    if surface is None:
        return VALIDITY_NO_SUPPORT
    params = _parse_params(main)
    hx, hy = footprint_half_xy(params, main.get("layoutlab_generator"))
    loc = [float(main.location.x), float(main.location.y), float(main.location.z)]
    centre = corner_to_center(loc, hx, hy, float(main.rotation_z_deg or 0.0))
    local_xy = supports.world_xy_to_surface_local(host, surface, centre)
    if not supports.centre_in_surface(surface, local_xy):
        return VALIDITY_OFF_SUPPORT
    return None


def _apply_pose_from_support(session, object_id: str, *, delta_rz: float = 0.0) -> None:
    """Reproject child world pose from support_local_xy + host (DD-021 follow)."""
    store = session.mesh_store
    main = main_part(store, object_id)
    if not main:
        return
    parsed = supports.parse_object_support(support_ref(main))
    if not parsed:
        return
    host_id, surface_id = parsed
    host = main_part(store, host_id)
    if host is None:
        return
    supports.stamp_host_surfaces(host)
    surface = supports.find_surface(host, surface_id)
    if surface is None:
        return
    local_xy = supports.support_local_xy_of(main)
    if local_xy is None:
        # Derive once from current world location (corner).
        local_xy = supports.world_xy_to_surface_local(
            host, surface, [main.location.x, main.location.y]
        )
        supports.set_support_local_xy(main, local_xy)
    wx, wy, wz = supports.surface_local_to_world(host, surface, local_xy)
    # Child location is min-corner; surface maps the corner's XY.
    main.location.x = float(wx)
    main.location.y = float(wy)
    main.location.z = float(wz)
    if abs(delta_rz) > 1e-12:
        main.rotation_z_deg = float(main.rotation_z_deg or 0.0) + float(delta_rz)
        while main.rotation_z_deg <= -180.0:
            main.rotation_z_deg += 360.0
        while main.rotation_z_deg > 180.0:
            main.rotation_z_deg -= 360.0
    params = _parse_params(main)
    params["location"] = [main.location.x, main.location.y, main.location.z]
    params["rotation_z_deg"] = main.rotation_z_deg
    _write_params(main, params)
    for part in objects_for_id(store, object_id):
        if part is not main:
            part["layoutlab_support_ref"] = support_ref(main)
            if main.get("layoutlab_support_local_xy"):
                part["layoutlab_support_local_xy"] = main["layoutlab_support_local_xy"]
            if part.get("layoutlab_params"):
                _write_params(part, params)


def iter_children_on_host(store, host_object_id: str):
    host = str(host_object_id)
    seen = set()
    for obj in store.objects:
        if not is_furniture_part(obj):
            continue
        oid = obj.get("layoutlab_object_id")
        if not oid or oid in seen or oid == host:
            continue
        main = main_part(store, oid)
        if main is None:
            continue
        seen.add(oid)
        parsed = supports.parse_object_support(support_ref(main))
        if parsed and parsed[0] == host:
            yield oid, parsed[1]


def follow_support_children(session, host_object_id: str, *, delta_rz: float = 0.0) -> list[str]:
    """Reproject children on host; detach to floor when centre leaves the surface.

    After host resize, also re-attach floor furniture whose footprint centre lies on
    the host surface again (grow-back).
    """
    store = session.mesh_store
    host_id = str(host_object_id)
    host = main_part(store, host_id)
    if host is None:
        return []
    supports.stamp_host_surfaces(host)

    followed = []
    for child_id, surface_id in list(iter_children_on_host(store, host_id)):
        main = main_part(store, child_id)
        if main is None:
            continue
        surface = supports.find_surface(host, surface_id)
        if surface is None:
            set_support(session, child_id, SUPPORT_ROOM_FLOOR, honour_lock=False)
            continue
        local_xy = supports.support_local_xy_of(main)
        if local_xy is None:
            local_xy = supports.world_xy_to_surface_local(
                host, surface, [main.location.x, main.location.y]
            )
            supports.set_support_local_xy(main, local_xy)
        params = _parse_params(main)
        hx, hy = footprint_half_xy(params, main.get("layoutlab_generator"))
        # Approx footprint centre in surface-local (MVP: ignore child↔host relative rz).
        local_centre = [float(local_xy[0]) + hx, float(local_xy[1]) + hy]
        if not supports.centre_in_surface(surface, local_centre):
            # Detach at current world XY (do not reproject onto a missing surface).
            set_support(session, child_id, SUPPORT_ROOM_FLOOR, honour_lock=False)
            continue
        _apply_pose_from_support(session, child_id, delta_rz=delta_rz)
        refresh_validity(store, session._rooms, child_id)
        followed.append(child_id)
    followed.extend(attach_floor_objects_over_host(session, host_id))
    return followed


def attach_floor_objects_over_host(session, host_object_id: str) -> list[str]:
    """Place room_floor furniture onto host when their footprint centre lies on a surface."""
    store = session.mesh_store
    host_id = str(host_object_id)
    host = main_part(store, host_id)
    if host is None:
        return []
    supports.stamp_host_surfaces(host)
    host_surfaces = supports.surfaces_of(host)
    if not host_surfaces:
        return []

    attached = []
    seen = set()
    for obj in store.objects:
        if not is_furniture_part(obj):
            continue
        oid = obj.get("layoutlab_object_id")
        if not oid or oid in seen or oid == host_id:
            continue
        main = main_part(store, oid)
        if main is None:
            continue
        seen.add(oid)
        if support_ref(main) != SUPPORT_ROOM_FLOOR:
            continue
        # Same collection / room as host when possible.
        if (main.collection or "") and (host.collection or ""):
            if main.collection != host.collection:
                continue
        params = _parse_params(main)
        hx, hy = footprint_half_xy(params, main.get("layoutlab_generator"))
        loc = [float(main.location.x), float(main.location.y), float(main.location.z)]
        centre = corner_to_center(loc, hx, hy, float(main.rotation_z_deg or 0.0))
        for surface in host_surfaces:
            sid = str(surface.get("id") or "")
            if not sid:
                continue
            local_xy = supports.world_xy_to_surface_local(host, surface, centre)
            if not supports.centre_in_surface(surface, local_xy):
                continue
            place_on(
                session,
                oid,
                host_id,
                surface_id=sid,
                location=[loc[0], loc[1]],
                honour_lock=False,
            )
            attached.append(oid)
            break
    return attached


def mark_dangling_support_children(session, host_object_id: str) -> list[str]:
    """After host delete: keep dangling support_ref, mark INVALID_NO_SUPPORT."""
    store = session.mesh_store
    affected = []
    host = str(host_object_id)
    # Collect before delete empties the host.
    children = list(iter_children_on_host(store, host))
    for child_id, _sid in children:
        for part in objects_for_id(store, child_id):
            part["layoutlab_validity"] = VALIDITY_NO_SUPPORT
        affected.append(child_id)
    return affected


def set_support(
    session,
    object_id: str,
    support_ref_value: str,
    *,
    support_local_xy=None,
    honour_lock: bool = True,
) -> dict:
    """Attach object to room_floor or object:<host>#surface (DD-021)."""
    store = session.mesh_store
    main = main_part(store, object_id)
    if main is None:
        raise ValueError(f"object not found: {object_id}")
    if honour_lock:
        _require_unlocked(main, action="set_support")
    ref = str(support_ref_value or SUPPORT_ROOM_FLOOR).strip() or SUPPORT_ROOM_FLOOR
    for part in objects_for_id(store, object_id):
        part["layoutlab_support_ref"] = ref

    if ref == SUPPORT_ROOM_FLOOR:
        supports.set_support_local_xy(main, None)
        for part in objects_for_id(store, object_id):
            part.props.pop("layoutlab_support_local_xy", None)
        return move_object(
            session,
            object_id,
            [main.location.x, main.location.y, main.location.z],
            honour_lock=False,
        )

    parsed = supports.parse_object_support(ref)
    if not parsed:
        raise ValueError(f"unsupported support_ref {ref!r}")
    host_id, surface_id = parsed
    if host_id == str(object_id):
        raise ValueError("cannot support an object on itself")
    host = main_part(store, host_id)
    if host is None:
        raise ValueError(f"support host not found: {host_id}")
    supports.stamp_host_surfaces(host)
    surface = supports.find_surface(host, surface_id)
    if surface is None:
        raise ValueError(f"surface {surface_id!r} not found on host {host_id}")

    if support_local_xy is not None:
        local_xy = [float(support_local_xy[0]), float(support_local_xy[1])]
    else:
        local_xy = supports.world_xy_to_surface_local(
            host, surface, [main.location.x, main.location.y]
        )
    supports.set_support_local_xy(main, local_xy)
    for part in objects_for_id(store, object_id):
        if part is not main and main.get("layoutlab_support_local_xy"):
            part["layoutlab_support_local_xy"] = main["layoutlab_support_local_xy"]
    _apply_pose_from_support(session, object_id, delta_rz=0.0)
    validity = refresh_validity(store, session._rooms, object_id)
    out = semantic_summary(store, object_id)
    out["validity"] = validity
    out["support_local_xy"] = supports.support_local_xy_of(main)
    return out


def place_on(
    session,
    object_id: str,
    host_object_id: str,
    *,
    surface_id: str = supports.SURFACE_TOP,
    location=None,
    honour_lock: bool = True,
) -> dict:
    """Convenience: set_support to host surface; optional world XY for child corner."""
    store = session.mesh_store
    main = main_part(store, object_id)
    if main is None:
        raise ValueError(f"object not found: {object_id}")
    host = main_part(store, host_object_id)
    if host is None:
        raise ValueError(f"host not found: {host_object_id}")
    supports.stamp_host_surfaces(host)
    surface = supports.find_surface(host, surface_id)
    if surface is None:
        raise ValueError(f"surface {surface_id!r} not found on host")
    if location is not None:
        if not isinstance(location, (list, tuple)) or len(location) < 2:
            raise ValueError("place_on location must be [x, y] or [x, y, z]")
        local_xy = supports.world_xy_to_surface_local(host, surface, location)
    else:
        local_xy = supports.surface_centre_local(surface)
        # Convert surface-centre (point on top) to child corner: place corner so
        # footprint centre lands on surface centre.
        params = _parse_params(main)
        hx, hy = footprint_half_xy(params, main.get("layoutlab_generator"))
        # Approx without child rz: store centre as local, then corner = centre - half
        # in surface frame before host rotation — use child rz ≈ 0 relative to host.
        local_xy = [local_xy[0] - hx, local_xy[1] - hy]
    ref = supports.format_object_support(str(host_object_id), str(surface_id))
    return set_support(
        session,
        object_id,
        ref,
        support_local_xy=local_xy,
        honour_lock=honour_lock,
    )

def refresh_validity(store, rooms: dict, object_id: str) -> str:
    state = compute_validity(store, rooms, object_id)
    for obj in objects_for_id(store, object_id):
        obj["layoutlab_validity"] = state
    return state


def refresh_all_validity(store, rooms: dict) -> None:
    seen = set()
    for obj in store.objects:
        if not is_furniture_part(obj):
            continue
        oid = obj.get("layoutlab_object_id")
        if not oid or oid in seen:
            continue
        seen.add(oid)
        refresh_validity(store, rooms, oid)


def semantic_summary(store, object_id: str) -> dict[str, Any]:
    main = main_part(store, object_id)
    if not main:
        raise ValueError(f"object not found: {object_id}")
    loc = main.world_origin()
    return {
        "object_id": object_id,
        "name": main.name,
        "generator": main.get("layoutlab_generator"),
        "location": [round(loc[0], 4), round(loc[1], 4), round(loc[2], 4)],
        "rotation_z_deg": round(float(main.rotation_z_deg), 4),
        "support_ref": support_ref(main),
        "support_local_xy": supports.support_local_xy_of(main),
        "room_id": main.get("layoutlab_room_id"),
        "validity": validity_of(main),
        "locked": is_locked(main),
        "visible": is_visible(main),
        "included_in_analysis": bool(main.props.get("included_in_analysis", True)),
        "protected_from_ai": bool(
            main.props.get("protected_from_ai")
            or main.props.get("layoutlab_protected_from_ai")
        ),
        "part_count": len(objects_for_id(store, object_id)),
    }


def _require_unlocked(main: MeshObject, *, action: str) -> None:
    if is_locked(main):
        raise ValueError(f"object is locked; cannot {action}: {main.get('layoutlab_object_id')}")


def select_object(session, object_id: str | None) -> dict:
    """Ephemeral single-select (WP-03). None clears selection."""
    if object_id in (None, "", "null"):
        session.selected_object_id = None
        return {"selected_object_id": None, "cleared": True}
    oid = str(object_id)
    if main_part(session.mesh_store, oid) is None:
        raise ValueError(f"object not found: {oid}")
    session.selected_object_id = oid
    return {"selected_object_id": oid, "object": semantic_summary(session.mesh_store, oid)}


def _rotate_offset_z(x: float, y: float, degrees: float) -> tuple[float, float]:
    import math

    if not degrees:
        return float(x), float(y)
    rad = math.radians(float(degrees))
    c, s = math.cos(rad), math.sin(rad)
    return x * c - y * s, x * s + y * c


def footprint_half_xy(params: dict | None, generator: str | None = None) -> tuple[float, float]:
    """Half footprint extents in local XY (min-corner → center), before Z rotation."""
    p = params or {}
    gen = str(generator or "")
    if gen == "bed_basic":
        sx = float(p.get("length") or 2.0)
        sy = float(p.get("width") or 1.2)
    elif gen == "lamp_basic":
        base = float(p.get("base") or 0.12)
        sx = base
        sy = base
    else:
        # desk_basic / wardrobe_basic / unknown: width×depth
        sx = float(p.get("width") or 1.0)
        sy = float(p.get("depth") or p.get("base") or 0.6)
    return max(sx, 0.01) * 0.5, max(sy, 0.01) * 0.5


def corner_to_center(location, half_x: float, half_y: float, rotation_z_deg: float) -> list[float]:
    lx, ly, lz = float(location[0]), float(location[1]), float(location[2] if len(location) > 2 else 0.0)
    ox, oy = _rotate_offset_z(half_x, half_y, rotation_z_deg)
    return [lx + ox, ly + oy, lz]


def center_to_corner(center, half_x: float, half_y: float, rotation_z_deg: float) -> list[float]:
    cx, cy, cz = float(center[0]), float(center[1]), float(center[2] if len(center) > 2 else 0.0)
    ox, oy = _rotate_offset_z(half_x, half_y, rotation_z_deg)
    return [cx - ox, cy - oy, cz]


def location_after_size_change(
    location,
    old_half_x: float,
    old_half_y: float,
    new_half_x: float,
    new_half_y: float,
    rotation_z_deg: float,
    *,
    anchor: str = "center",
) -> list[float]:
    """New min-corner location after a footprint size change.

    ``anchor``:
    - ``center`` — keep footprint centre fixed (default for API resize)
    - ``min_x`` / ``max_x`` / ``min_y`` / ``max_y`` — keep that local edge fixed
      (Viewer scale gizmos: opposite edge to the dragged handle)
    """
    a = str(anchor or "center").lower().replace("-", "_")
    if a in ("center", "centre", ""):
        center = corner_to_center(location, old_half_x, old_half_y, rotation_z_deg)
        return center_to_corner(center, new_half_x, new_half_y, rotation_z_deg)

    dsx = 2.0 * (float(new_half_x) - float(old_half_x))
    dsy = 2.0 * (float(new_half_y) - float(old_half_y))
    local_dx = 0.0
    local_dy = 0.0
    if a in ("max_x", "pos_x", "+x"):
        local_dx = -dsx
    elif a in ("min_x", "neg_x", "-x"):
        local_dx = 0.0
    elif a in ("max_y", "pos_y", "+y"):
        local_dy = -dsy
    elif a in ("min_y", "neg_y", "-y"):
        local_dy = 0.0
    else:
        center = corner_to_center(location, old_half_x, old_half_y, rotation_z_deg)
        return center_to_corner(center, new_half_x, new_half_y, rotation_z_deg)

    lx = float(location[0])
    ly = float(location[1])
    lz = float(location[2] if len(location) > 2 else 0.0)
    wx, wy = _rotate_offset_z(local_dx, local_dy, rotation_z_deg)
    return [lx + wx, ly + wy, lz]


def move_object(session, object_id: str, location, *, honour_lock: bool = True) -> dict:
    """Set Main Part world XY location; Z follows support_ref (floor or host surface)."""
    store = session.mesh_store
    main = main_part(store, object_id)
    if main is None:
        raise ValueError(f"object not found: {object_id}")
    if honour_lock:
        _require_unlocked(main, action="move")
    if not isinstance(location, (list, tuple)) or len(location) < 2:
        raise ValueError("move requires location [x, y] or [x, y, z]")

    x, y = float(location[0]), float(location[1])
    ref = support_ref(main)
    parsed = supports.parse_object_support(ref)

    if parsed:
        host_id, surface_id = parsed
        host = main_part(store, host_id)
        if host is not None:
            supports.stamp_host_surfaces(host)
            surface = supports.find_surface(host, surface_id)
            if surface is not None:
                local_xy = supports.world_xy_to_surface_local(host, surface, [x, y])
                supports.set_support_local_xy(main, local_xy)
                for part in objects_for_id(store, object_id):
                    if part is not main and main.get("layoutlab_support_local_xy"):
                        part["layoutlab_support_local_xy"] = main["layoutlab_support_local_xy"]
                _apply_pose_from_support(session, object_id, delta_rz=0.0)
                validity = refresh_validity(store, session._rooms, object_id)
                # Host itself moved? Children follow below when this object is a host.
                follow_support_children(session, object_id, delta_rz=0.0)
                out = semantic_summary(store, object_id)
                out["validity"] = validity
                return out

    # Floor support: keep Z on room floor / current floor height.
    z = float(main.location.z)
    if ref == SUPPORT_ROOM_FLOOR:
        room_id = main.get("layoutlab_room_id")
        model = session.get_by_id(room_id) if room_id else None
        if model is None:
            for m in session.list_rooms():
                if (m.get("collection") or "layoutlab_room") == (main.collection or "layoutlab_room"):
                    model = m
                    break
        if model is not None:
            z = float((model.get("origin") or [0, 0, 0])[2])
        else:
            z = 0.0
    elif len(location) >= 3:
        z = float(location[2])

    main.location.x = x
    main.location.y = y
    main.location.z = z

    params = _parse_params(main)
    params["location"] = [x, y, z]
    _write_params(main, params)
    # Keep params string in sync on siblings that share it.
    for part in objects_for_id(store, object_id):
        if part is not main and part.get("layoutlab_params"):
            _write_params(part, params)

    validity = refresh_validity(store, session._rooms, object_id)
    follow_support_children(session, object_id, delta_rz=0.0)
    out = semantic_summary(store, object_id)
    out["validity"] = validity
    return out


def rotate_object_z(
    session,
    object_id: str,
    degrees: float,
    *,
    absolute: bool = True,
    honour_lock: bool = True,
    pivot: str = "center",
) -> dict:
    """Rotate Main Part about Z. Default pivot is footprint center (keeps center fixed)."""
    store = session.mesh_store
    main = main_part(store, object_id)
    if main is None:
        raise ValueError(f"object not found: {object_id}")
    if honour_lock:
        _require_unlocked(main, action="rotate_z")

    params = _parse_params(main)
    gen = main.get("layoutlab_generator")
    hx, hy = footprint_half_xy(params, gen)
    old_rz = float(main.rotation_z_deg or 0.0)
    loc = [float(main.location.x), float(main.location.y), float(main.location.z)]
    center = corner_to_center(loc, hx, hy, old_rz) if pivot == "center" else None

    deg = float(degrees)
    if absolute:
        main.rotation_z_deg = deg
    else:
        main.rotation_z_deg = old_rz + deg
    # Normalize to (-180, 180]
    while main.rotation_z_deg <= -180.0:
        main.rotation_z_deg += 360.0
    while main.rotation_z_deg > 180.0:
        main.rotation_z_deg -= 360.0

    if pivot == "center" and center is not None:
        new_loc = center_to_corner(center, hx, hy, main.rotation_z_deg)
        main.location.x = new_loc[0]
        main.location.y = new_loc[1]
        main.location.z = new_loc[2]
        params["location"] = new_loc

    params["rotation_z_deg"] = main.rotation_z_deg
    _write_params(main, params)
    for part in objects_for_id(store, object_id):
        if part is not main and part.get("layoutlab_params"):
            _write_params(part, params)

    validity = refresh_validity(store, session._rooms, object_id)
    delta_rz = float(main.rotation_z_deg) - old_rz
    follow_support_children(session, object_id, delta_rz=delta_rz)
    out = semantic_summary(store, object_id)
    out["validity"] = validity
    out["pivot"] = pivot
    return out


def set_object_flags(session, object_id: str, flags: dict, *, honour_lock: bool = False) -> dict:
    """Set locked / visible / included_in_analysis / protected_from_ai on all parts."""
    store = session.mesh_store
    parts = objects_for_id(store, object_id)
    if not parts:
        raise ValueError(f"object not found: {object_id}")
    main = main_part(store, object_id)
    # Allow unlocking a locked object; other edits while locked still blocked elsewhere.
    allowed = {
        "locked",
        "visible",
        "included_in_analysis",
        "protected_from_ai",
        "support_ref",
    }
    updates = {k: v for k, v in (flags or {}).items() if k in allowed}
    if not updates:
        raise ValueError("set_object_flags requires at least one known flag")

    for part in parts:
        if "locked" in updates:
            part["locked"] = bool(updates["locked"])
        if "visible" in updates:
            part["visible"] = bool(updates["visible"])
        if "included_in_analysis" in updates:
            part["included_in_analysis"] = bool(updates["included_in_analysis"])
        if "protected_from_ai" in updates:
            part["protected_from_ai"] = bool(updates["protected_from_ai"])

    if "support_ref" in updates:
        ref = str(updates["support_ref"] or SUPPORT_ROOM_FLOOR)
        return set_support(session, object_id, ref, honour_lock=False)

    return semantic_summary(store, object_id)


def hide_object(session, object_id: str, *, hidden: bool = True) -> dict:
    return set_object_flags(session, object_id, {"visible": not hidden})


def delete_object(session, object_id: str, *, honour_lock: bool = True) -> dict:
    store = session.mesh_store
    main = main_part(store, object_id)
    if main is None:
        raise ValueError(f"object not found: {object_id}")
    if honour_lock:
        _require_unlocked(main, action="delete")
    dangling = mark_dangling_support_children(session, str(object_id))
    n = store.delete_by_object_id(str(object_id))
    if getattr(session, "selected_object_id", None) == str(object_id):
        session.selected_object_id = None
    return {"deleted": n, "object_id": str(object_id), "dangling_support": dangling}


def duplicate_object(
    session,
    object_id: str,
    *,
    offset=(0.2, 0.2, 0.0),
    honour_lock: bool = True,
) -> dict:
    store = session.mesh_store
    parts = objects_for_id(store, object_id)
    if not parts:
        raise ValueError(f"object not found: {object_id}")
    main = main_part(store, object_id)
    if honour_lock and main is not None:
        _require_unlocked(main, action="duplicate")

    new_id = str(uuid.uuid4())
    ox = float(offset[0]) if offset is not None else 0.2
    oy = float(offset[1]) if offset is not None and len(offset) > 1 else 0.2
    oz = float(offset[2]) if offset is not None and len(offset) > 2 else 0.0

    # Deep-copy parts; rewrite ids; re-link parents within the new set.
    old_to_new: dict[int, MeshObject] = {}
    clones: list[MeshObject] = []
    for src in parts:
        clone = copy.deepcopy(src)
        clone.parent = None
        old_to_new[id(src)] = clone
        clones.append(clone)

    for src, clone in zip(parts, clones):
        if src.parent is not None and id(src.parent) in old_to_new:
            clone.parent = old_to_new[id(src.parent)]
        clone["layoutlab_object_id"] = new_id
        # Unique mesh names
        base = clone.name
        if base.endswith(str(object_id)[:8]):
            clone.name = base
        clone.name = f"{base}__dup_{new_id[:8]}"
        params = _parse_params(clone)
        if clone.parent is None:
            clone.location.x = float(clone.location.x) + ox
            clone.location.y = float(clone.location.y) + oy
            clone.location.z = float(clone.location.z) + oz
            params["location"] = [
                clone.location.x,
                clone.location.y,
                clone.location.z,
            ]
            params["name"] = f"{params.get('name') or 'OBJ'}_copy"
        params["object_id"] = new_id
        _write_params(clone, params)
        store.add(clone)

    ensure_semantic_defaults(store, session._rooms, new_id)
    return {
        "object_id": new_id,
        "source_object_id": str(object_id),
        "object": semantic_summary(store, new_id),
    }


def resolve_object_id(store, *, object_id=None, object_name=None) -> str:
    """Resolve logical furniture id from object_id or any part mesh name."""
    if object_id:
        oid = str(object_id)
        if main_part(store, oid) is None:
            raise ValueError(f"object not found: {oid}")
        return oid
    name = object_name
    if not name:
        raise ValueError("object_id or object (mesh name) required")
    for obj in store.objects:
        if obj.name == name:
            oid = obj.get("layoutlab_object_id")
            if not oid:
                raise ValueError(
                    f"Object '{name}' has no layoutlab_object_id "
                    "(legacy — use delete_prefix + run_generator)"
                )
            return str(oid)
    raise ValueError(f"Object not found: {name}")


def _capture_semantic_state(store, object_id: str) -> dict[str, Any]:
    main = main_part(store, object_id)
    if main is None:
        raise ValueError(f"object not found: {object_id}")
    loc = main.world_origin()
    return {
        "location": [float(loc[0]), float(loc[1]), float(loc[2])],
        "rotation_z_deg": float(main.rotation_z_deg or 0.0),
        "support_ref": support_ref(main),
        "support_local_xy": supports.support_local_xy_of(main),
        "room_id": main.get("layoutlab_room_id"),
        "locked": is_locked(main),
        "visible": is_visible(main),
        "included_in_analysis": bool(main.props.get("included_in_analysis", True)),
        "protected_from_ai": bool(
            main.props.get("protected_from_ai") or main.props.get("layoutlab_protected_from_ai")
        ),
        "generator": main.get("layoutlab_generator"),
        "params": _parse_params(main),
        "collection": main.collection or "layoutlab_room",
    }


def _restore_semantic_state(store, object_id: str, state: dict) -> None:
    main = main_part(store, object_id)
    if main is None:
        return
    main.rotation_z_deg = float(state.get("rotation_z_deg") or 0.0)
    for part in objects_for_id(store, object_id):
        part["layoutlab_support_ref"] = state.get("support_ref") or SUPPORT_ROOM_FLOOR
        if state.get("room_id"):
            part["layoutlab_room_id"] = state["room_id"]
        part["locked"] = bool(state.get("locked"))
        part["visible"] = bool(state.get("visible", True))
        part["included_in_analysis"] = bool(state.get("included_in_analysis", True))
        part["protected_from_ai"] = bool(state.get("protected_from_ai"))
    if state.get("support_local_xy") is not None:
        supports.set_support_local_xy(main, state["support_local_xy"])
        for part in objects_for_id(store, object_id):
            if part is not main and main.get("layoutlab_support_local_xy"):
                part["layoutlab_support_local_xy"] = main["layoutlab_support_local_xy"]
    else:
        supports.set_support_local_xy(main, None)
    params = _parse_params(main)
    params["location"] = list(state.get("location") or params.get("location") or [0, 0, 0])
    params["rotation_z_deg"] = main.rotation_z_deg
    _write_params(main, params)
    for part in objects_for_id(store, object_id):
        if part is not main and part.get("layoutlab_params"):
            _write_params(part, params)


def regenerate_object(
    session,
    *,
    object_id: str | None = None,
    object_name: str | None = None,
    params_override: dict | None = None,
    honour_lock: bool = True,
    anchor: str = "center",
) -> dict:
    """Rebuild furniture from generator params (DD-002 / FC-001/WP-04). Same object_id."""
    from ..util import merge_generator_params
    from .headless_api import execute_generator_headless

    store = session.mesh_store
    oid = resolve_object_id(store, object_id=object_id, object_name=object_name)
    main = main_part(store, oid)
    if main is None:
        raise ValueError(f"object not found: {oid}")
    if honour_lock:
        _require_unlocked(main, action="regenerate")

    state = _capture_semantic_state(store, oid)
    generator = state.get("generator")
    if not generator:
        raise ValueError("Object has no layoutlab_generator metadata")

    overrides = dict(params_override or {})
    # Non-generator keys (pose anchors) — strip before merge.
    override_anchor = overrides.pop("anchor", None) or overrides.pop("resize_anchor", None)
    resize_anchor = str(override_anchor or anchor or "center")

    merged = merge_generator_params(state["params"], overrides)
    # Adjust min-corner so the chosen edge (or centre) stays fixed in world.
    if "location" not in overrides:
        old_hx, old_hy = footprint_half_xy(state["params"], generator)
        new_hx, new_hy = footprint_half_xy(merged, generator)
        merged["location"] = location_after_size_change(
            state["location"],
            old_hx,
            old_hy,
            new_hx,
            new_hy,
            state["rotation_z_deg"],
            anchor=resize_anchor,
        )
    if "rotation_z_deg" not in overrides:
        merged["rotation_z_deg"] = state["rotation_z_deg"]
    if not merged.get("collection"):
        merged["collection"] = state["collection"]

    was_selected = getattr(session, "selected_object_id", None) == oid
    store.delete_by_object_id(oid)
    result = execute_generator_headless(generator, merged, object_id=oid, store=store)
    ensure_semantic_defaults(store, session._rooms, oid)
    pose_state = {
        **state,
        "params": merged,
        "location": list(merged.get("location") or state["location"]),
    }
    _restore_semantic_state(store, oid, pose_state)

    new_main = main_part(store, oid)
    if new_main is not None:
        if "location" in overrides:
            loc = overrides["location"]
            new_main.location.x = float(loc[0])
            new_main.location.y = float(loc[1])
            new_main.location.z = float(loc[2]) if len(loc) > 2 else float(new_main.location.z)
        else:
            loc = pose_state["location"]
            new_main.location.x = float(loc[0])
            new_main.location.y = float(loc[1])
            new_main.location.z = float(loc[2])
        if "rotation_z_deg" in overrides:
            new_main.rotation_z_deg = float(overrides["rotation_z_deg"])
        else:
            new_main.rotation_z_deg = float(state["rotation_z_deg"])
        # Re-sync params JSON after pose fix.
        params = _parse_params(new_main)
        params["location"] = [
            new_main.location.x,
            new_main.location.y,
            new_main.location.z,
        ]
        params["rotation_z_deg"] = new_main.rotation_z_deg
        _write_params(new_main, params)

    validity = refresh_validity(store, session._rooms, oid)
    supports.stamp_host_surfaces(main_part(store, oid) or new_main)
    follow_support_children(session, oid, delta_rz=0.0)
    if was_selected:
        session.selected_object_id = oid

    summary = semantic_summary(store, oid)
    summary["validity"] = validity
    out = {
        "regenerated": merged.get("name") or summary.get("name") or "",
        "object_id": oid,
        "generator": generator,
        "params": merged,
        "object": summary,
        "anchor": resize_anchor,
    }
    if isinstance(result, dict):
        for key in ("parts", "main_part", "part_object_count"):
            if key in result:
                out[key] = result[key]
    return out


def set_parameter(
    session,
    *,
    object_id: str | None = None,
    object_name: str | None = None,
    params: dict | None = None,
    parameter: str | None = None,
    value: Any = None,
    honour_lock: bool = True,
    anchor: str = "center",
) -> dict:
    """Change generator parameter(s) and regenerate (semantic resize — no mesh scale)."""
    overrides = dict(params or {})
    if parameter is not None:
        overrides[str(parameter)] = value
    if not overrides:
        raise ValueError("set_parameter requires params{} and/or parameter+value")
    result = regenerate_object(
        session,
        object_id=object_id,
        object_name=object_name,
        params_override=overrides,
        honour_lock=honour_lock,
        anchor=anchor,
    )
    result["set_parameter"] = True
    result["overrides"] = {
        k: v for k, v in overrides.items() if k not in ("anchor", "resize_anchor")
    }
    return result


def apply_furniture_command(session, cmd: dict) -> Any:
    """Dispatch one furniture manipulation command."""
    action = cmd.get("action")
    params = cmd.get("params") if isinstance(cmd.get("params"), dict) else {}
    object_id = cmd.get("object_id") or params.get("object_id")
    object_name = cmd.get("object") or cmd.get("name") or params.get("object") or params.get("name")

    if action == "select_object":
        return select_object(session, object_id or object_name)

    if action in ("move", "move_object"):
        oid = resolve_object_id(
            session.mesh_store, object_id=object_id, object_name=object_name
        )
        location = cmd.get("location") or params.get("location")
        return move_object(session, oid, location)

    if action in ("rotate_z", "rotate_object_z"):
        oid = resolve_object_id(
            session.mesh_store, object_id=object_id, object_name=object_name
        )
        if "degrees" in cmd:
            degrees = cmd.get("degrees")
        elif "degrees" in params:
            degrees = params.get("degrees")
        else:
            degrees = cmd.get("rotation_z_deg", params.get("rotation_z_deg"))
        if degrees is None:
            raise ValueError("rotate_z requires degrees")
        absolute = True
        if "absolute" in cmd:
            absolute = bool(cmd.get("absolute"))
        elif "absolute" in params:
            absolute = bool(params.get("absolute"))
        elif cmd.get("delta") or params.get("delta"):
            absolute = False
        return rotate_object_z(session, oid, float(degrees), absolute=absolute)

    if action == "duplicate":
        oid = resolve_object_id(
            session.mesh_store, object_id=object_id, object_name=object_name
        )
        offset = cmd.get("offset") or params.get("offset") or (0.2, 0.2, 0.0)
        return duplicate_object(session, oid, offset=offset)

    if action == "delete":
        oid = resolve_object_id(
            session.mesh_store, object_id=object_id, object_name=object_name
        )
        return delete_object(session, oid)

    if action == "hide":
        oid = resolve_object_id(
            session.mesh_store, object_id=object_id, object_name=object_name
        )
        return hide_object(session, oid, hidden=True)

    if action == "show":
        oid = resolve_object_id(
            session.mesh_store, object_id=object_id, object_name=object_name
        )
        return hide_object(session, oid, hidden=False)

    if action in ("set_flags", "set_object_flags"):
        oid = resolve_object_id(
            session.mesh_store, object_id=object_id, object_name=object_name
        )
        flags = dict(params)
        for key in (
            "locked",
            "visible",
            "included_in_analysis",
            "protected_from_ai",
            "support_ref",
        ):
            if key in cmd:
                flags[key] = cmd[key]
        return set_object_flags(session, oid, flags)

    if action == "set_support":
        oid = resolve_object_id(
            session.mesh_store, object_id=object_id, object_name=object_name
        )
        ref = cmd.get("support_ref") or params.get("support_ref")
        if ref is None:
            raise ValueError("set_support requires support_ref")
        local_xy = cmd.get("support_local_xy", params.get("support_local_xy"))
        return set_support(session, oid, ref, support_local_xy=local_xy)

    if action == "place_on":
        oid = resolve_object_id(
            session.mesh_store, object_id=object_id, object_name=object_name
        )
        host_id = (
            cmd.get("host_object_id")
            or params.get("host_object_id")
            or cmd.get("host_id")
            or params.get("host_id")
        )
        if not host_id:
            host_name = cmd.get("host") or params.get("host")
            if host_name:
                host_id = resolve_object_id(
                    session.mesh_store, object_id=None, object_name=host_name
                )
        if not host_id:
            raise ValueError("place_on requires host_object_id")
        surface_id = (
            cmd.get("surface_id")
            or params.get("surface_id")
            or supports.SURFACE_TOP
        )
        location = cmd.get("location") or params.get("location")
        return place_on(
            session,
            oid,
            str(host_id),
            surface_id=str(surface_id),
            location=location,
        )

    if action == "set_locked":
        oid = resolve_object_id(
            session.mesh_store, object_id=object_id, object_name=object_name
        )
        locked = cmd.get("locked") if "locked" in cmd else params.get("locked")
        if locked is None:
            raise ValueError("set_locked requires locked: bool")
        return set_object_flags(session, oid, {"locked": bool(locked)})

    if action == "regenerate":
        overrides = dict(params) if params else {}
        for key, value in cmd.items():
            if key in (
                "action",
                "object_id",
                "object",
                "name",
                "params",
                "generator",
                "anchor",
                "resize_anchor",
            ):
                continue
            if key not in overrides:
                overrides[key] = value
        anchor = (
            cmd.get("anchor")
            or cmd.get("resize_anchor")
            or overrides.pop("anchor", None)
            or overrides.pop("resize_anchor", None)
            or "center"
        )
        return regenerate_object(
            session,
            object_id=object_id,
            object_name=object_name,
            params_override=overrides or None,
            anchor=str(anchor),
        )

    if action in ("set_parameter", "resize"):
        overrides = dict(params) if params else {}
        parameter = cmd.get("parameter") or cmd.get("param")
        if parameter is not None and "value" in cmd:
            overrides[str(parameter)] = cmd.get("value")
        for key, val in cmd.items():
            if key in (
                "action",
                "object_id",
                "object",
                "name",
                "params",
                "parameter",
                "param",
                "value",
                "generator",
                "anchor",
                "resize_anchor",
            ):
                continue
            if key not in overrides:
                overrides[key] = val
        anchor = (
            cmd.get("anchor")
            or cmd.get("resize_anchor")
            or overrides.pop("anchor", None)
            or overrides.pop("resize_anchor", None)
            or "center"
        )
        return set_parameter(
            session,
            object_id=object_id,
            object_name=object_name,
            params=overrides or None,
            anchor=str(anchor),
        )

    raise ValueError(f"unhandled furniture action {action!r}")
