"""Semantic furniture manipulation for headless Core (DD-019 / FC-001/WP-03)."""

from __future__ import annotations

import copy
import json
import uuid
from typing import Any

from ..core import room as room_core
from .mesh_store import MeshObject

SUPPORT_ROOM_FLOOR = "room_floor"

VALIDITY_VALID = "VALID"
VALIDITY_OUTSIDE = "INVALID_OUTSIDE_ROOM"
VALIDITY_WALL = "INVALID_INTERSECTS_WALL"

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
    # Outside room footprint (XY).
    if (
        fx0 < rmin[0] - _BOUNDS_EPS
        or fy0 < rmin[1] - _BOUNDS_EPS
        or fx1 > rmax[0] + _BOUNDS_EPS
        or fy1 > rmax[1] + _BOUNDS_EPS
    ):
        return VALIDITY_OUTSIDE

    # Intersects wall display panels (inward plane AABBs).
    for wall in model.get("walls") or []:
        for panel in room_core.wall_display_panels(model, wall):
            corners = panel.get("corners") or []
            if len(corners) < 2:
                continue
            xs = [c[0] for c in corners]
            ys = [c[1] for c in corners]
            wall_bb = (min(xs), min(ys), max(xs), max(ys))
            # Inflate thin wall AABBs slightly so zero-thickness planes still collide.
            wx0, wy0, wx1, wy1 = wall_bb
            if abs(wx1 - wx0) < _WALL_HIT_EPS:
                mid = 0.5 * (wx0 + wx1)
                wx0, wx1 = mid - _WALL_HIT_EPS, mid + _WALL_HIT_EPS
            if abs(wy1 - wy0) < _WALL_HIT_EPS:
                mid = 0.5 * (wy0 + wy1)
                wy0, wy1 = mid - _WALL_HIT_EPS, mid + _WALL_HIT_EPS
            if _aabb_overlap_2d(bbox, (wx0, wy0, wx1, wy1), eps=0.0):
                return VALIDITY_WALL

    return VALIDITY_VALID


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


def move_object(session, object_id: str, location, *, honour_lock: bool = True) -> dict:
    """Set Main Part world XY location; Z follows floor support (MVP)."""
    store = session.mesh_store
    main = main_part(store, object_id)
    if main is None:
        raise ValueError(f"object not found: {object_id}")
    if honour_lock:
        _require_unlocked(main, action="move")
    if not isinstance(location, (list, tuple)) or len(location) < 2:
        raise ValueError("move requires location [x, y] or [x, y, z]")

    x, y = float(location[0]), float(location[1])
    # Floor support: keep Z on room floor / current floor height.
    z = float(main.location.z)
    if support_ref(main) == SUPPORT_ROOM_FLOOR:
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
) -> dict:
    store = session.mesh_store
    main = main_part(store, object_id)
    if main is None:
        raise ValueError(f"object not found: {object_id}")
    if honour_lock:
        _require_unlocked(main, action="rotate_z")
    deg = float(degrees)
    if absolute:
        main.rotation_z_deg = deg
    else:
        main.rotation_z_deg = float(main.rotation_z_deg) + deg
    # Normalize to (-180, 180]
    while main.rotation_z_deg <= -180.0:
        main.rotation_z_deg += 360.0
    while main.rotation_z_deg > 180.0:
        main.rotation_z_deg -= 360.0

    params = _parse_params(main)
    params["rotation_z_deg"] = main.rotation_z_deg
    _write_params(main, params)
    for part in objects_for_id(store, object_id):
        if part is not main and part.get("layoutlab_params"):
            _write_params(part, params)

    validity = refresh_validity(store, session._rooms, object_id)
    out = semantic_summary(store, object_id)
    out["validity"] = validity
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
            part["layoutlab_support_ref"] = ref

    if main and "support_ref" in updates and updates["support_ref"] == SUPPORT_ROOM_FLOOR:
        # Snap Z to floor when (re)attaching to floor.
        move_object(
            session,
            object_id,
            [main.location.x, main.location.y, main.location.z],
            honour_lock=False,
        )

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
    n = store.delete_by_object_id(str(object_id))
    if getattr(session, "selected_object_id", None) == str(object_id):
        session.selected_object_id = None
    return {"deleted": n, "object_id": str(object_id)}


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

    merged = merge_generator_params(state["params"], params_override or {})
    # Keep current world pose unless the override explicitly sets location.
    if not (params_override and "location" in params_override):
        merged["location"] = list(state["location"])
    if not (params_override and "rotation_z_deg" in params_override):
        merged["rotation_z_deg"] = state["rotation_z_deg"]
    if not merged.get("collection"):
        merged["collection"] = state["collection"]

    was_selected = getattr(session, "selected_object_id", None) == oid
    store.delete_by_object_id(oid)
    result = execute_generator_headless(generator, merged, object_id=oid, store=store)
    ensure_semantic_defaults(store, session._rooms, oid)
    _restore_semantic_state(store, oid, {**state, "params": merged})

    new_main = main_part(store, oid)
    if new_main is not None:
        if params_override and "location" in params_override:
            loc = params_override["location"]
            new_main.location.x = float(loc[0])
            new_main.location.y = float(loc[1])
            new_main.location.z = float(loc[2]) if len(loc) > 2 else float(new_main.location.z)
        else:
            loc = state["location"]
            new_main.location.x = float(loc[0])
            new_main.location.y = float(loc[1])
            new_main.location.z = float(loc[2])
        if params_override and "rotation_z_deg" in params_override:
            new_main.rotation_z_deg = float(params_override["rotation_z_deg"])
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
    )
    result["set_parameter"] = True
    result["overrides"] = overrides
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
        flags.pop("object_id", None)
        flags.pop("object", None)
        flags.pop("name", None)
        return set_object_flags(session, oid, flags)

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
            if key in ("action", "object_id", "object", "name", "params", "generator"):
                continue
            if key not in overrides:
                overrides[key] = value
        return regenerate_object(
            session,
            object_id=object_id,
            object_name=object_name,
            params_override=overrides or None,
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
            ):
                continue
            if key not in overrides:
                overrides[key] = val
        return set_parameter(
            session,
            object_id=object_id,
            object_name=object_name,
            params=overrides or None,
        )

    raise ValueError(f"unhandled furniture action {action!r}")
