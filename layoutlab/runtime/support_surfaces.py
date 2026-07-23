"""Named host surfaces + stacking support (DD-021 / FC-001/WP-07)."""

from __future__ import annotations

import json
import math
from typing import Any

from .mesh_store import MeshObject

SUPPORT_ROOM_FLOOR = "room_floor"

VALIDITY_OFF_SUPPORT = "INVALID_OFF_SUPPORT"
VALIDITY_NO_SUPPORT = "INVALID_NO_SUPPORT"

SURFACE_TOP = "surface_top"


def format_object_support(host_object_id: str, surface_id: str = SURFACE_TOP) -> str:
    return f"object:{host_object_id}#{surface_id}"


def parse_object_support(ref: str) -> tuple[str, str] | None:
    text = str(ref or "").strip()
    if not text.startswith("object:"):
        return None
    rest = text[len("object:") :]
    if "#" not in rest:
        return None
    host_id, surface_id = rest.split("#", 1)
    host_id = host_id.strip()
    surface_id = surface_id.strip()
    if not host_id or not surface_id:
        return None
    return host_id, surface_id


def support_local_xy_of(obj: MeshObject) -> list[float] | None:
    raw = obj.get("layoutlab_support_local_xy")
    if isinstance(raw, (list, tuple)) and len(raw) >= 2:
        return [float(raw[0]), float(raw[1])]
    if isinstance(raw, str) and raw.strip():
        try:
            data = json.loads(raw)
            if isinstance(data, (list, tuple)) and len(data) >= 2:
                return [float(data[0]), float(data[1])]
        except json.JSONDecodeError:
            return None
    return None


def set_support_local_xy(obj: MeshObject, xy) -> None:
    if xy is None:
        obj.props.pop("layoutlab_support_local_xy", None)
        return
    obj["layoutlab_support_local_xy"] = json.dumps(
        [round(float(xy[0]), 6), round(float(xy[1]), 6)],
        separators=(",", ":"),
    )


def surfaces_of(main: MeshObject) -> list[dict]:
    raw = main.get("layoutlab_surfaces")
    if isinstance(raw, list):
        return [s for s in raw if isinstance(s, dict)]
    if isinstance(raw, str) and raw.strip():
        try:
            data = json.loads(raw)
            if isinstance(data, list):
                return [s for s in data if isinstance(s, dict)]
        except json.JSONDecodeError:
            return []
    return []


def find_surface(main: MeshObject, surface_id: str) -> dict | None:
    sid = str(surface_id)
    for surf in surfaces_of(main):
        if str(surf.get("id") or "") == sid:
            return surf
    return None


def desk_surface_top_from_params(params: dict) -> dict:
    width = float(params.get("width") or 1.2)
    depth = float(params.get("depth") or 0.6)
    height = float(params.get("height") or 0.75)
    return {
        "id": SURFACE_TOP,
        "kind": "horizontal",
        "local_z": height,
        "local_min_xy": [0.0, 0.0],
        "local_max_xy": [width, depth],
    }


def stamp_host_surfaces(main: MeshObject) -> list[dict]:
    """Recompute layoutlab_surfaces from generator params (survives regenerate)."""
    gen = str(main.get("layoutlab_generator") or "")
    params_raw = main.get("layoutlab_params")
    params: dict = {}
    if isinstance(params_raw, dict):
        params = dict(params_raw)
    elif isinstance(params_raw, str) and params_raw.strip():
        try:
            data = json.loads(params_raw)
            if isinstance(data, dict):
                params = data
        except json.JSONDecodeError:
            params = {}

    surfaces: list[dict] = []
    if gen == "desk_basic":
        surfaces = [desk_surface_top_from_params(params)]

    if surfaces:
        main["layoutlab_surfaces"] = json.dumps(surfaces, ensure_ascii=False, sort_keys=True)
    else:
        main.props.pop("layoutlab_surfaces", None)
    return surfaces


def surface_local_to_world(host: MeshObject, surface: dict, local_xy, *, z: float | None = None):
    lx = float(local_xy[0])
    ly = float(local_xy[1])
    lz = float(surface.get("local_z") if z is None else z)
    return host.local_point_to_world(lx, ly, lz)


def world_xy_to_surface_local(host: MeshObject, surface: dict, world_xy) -> list[float]:
    """Inverse of surface XY map (ignore Z): world → surface local XY."""
    wx = float(world_xy[0]) - float(host.location.x)
    wy = float(world_xy[1]) - float(host.location.y)
    rz = float(host.rotation_z_deg or 0.0)
    if rz:
        rad = math.radians(-rz)
        c, s = math.cos(rad), math.sin(rad)
        lx = wx * c - wy * s
        ly = wx * s + wy * c
    else:
        lx, ly = wx, wy
    return [lx, ly]


def centre_in_surface(surface: dict, local_xy) -> bool:
    mn = surface.get("local_min_xy") or [0.0, 0.0]
    mx = surface.get("local_max_xy") or [0.0, 0.0]
    lx, ly = float(local_xy[0]), float(local_xy[1])
    return (
        float(mn[0]) - 1e-6 <= lx <= float(mx[0]) + 1e-6
        and float(mn[1]) - 1e-6 <= ly <= float(mx[1]) + 1e-6
    )


def surface_centre_local(surface: dict) -> list[float]:
    mn = surface.get("local_min_xy") or [0.0, 0.0]
    mx = surface.get("local_max_xy") or [0.0, 0.0]
    return [0.5 * (float(mn[0]) + float(mx[0])), 0.5 * (float(mn[1]) + float(mx[1]))]
