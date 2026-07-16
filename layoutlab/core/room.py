"""Pure-Python Room Model (DD-010) — no bpy dependency."""

from __future__ import annotations

import copy
import uuid

FOOTPRINT_KINDS = ("rectangle", "polygon")
OPENING_KINDS = ("door", "window")
FIXED_KINDS = ("radiator",)
RECT_WALL_ORDER = ("south", "east", "north", "west")  # y_min, x_max, y_max, x_min
DEFAULT_WALL_THICKNESS = 0.2
DEFAULT_WALL_HEIGHT = 26.0


def _new_id():
    return str(uuid.uuid4())


def _f(value, default=0.0):
    try:
        return float(value)
    except (TypeError, ValueError):
        return float(default)


def wall_length_for_side(width, depth, side):
    if side in ("south", "north"):
        return float(width)
    if side in ("east", "west"):
        return float(depth)
    raise ValueError(f"unknown wall side {side!r}")


def derive_rectangle_walls(origin, width, depth, height, thickness, existing=None):
    """Return four wall dicts for a rectangle footprint.

    If ``existing`` is a list of walls with ``side`` keys, reuse their wall_ids.
    """
    ox, oy, oz = (_f(origin[0]), _f(origin[1]), _f(origin[2]) if len(origin) > 2 else 0.0)
    width = _f(width)
    depth = _f(depth)
    height = _f(height)
    thickness = _f(thickness, DEFAULT_WALL_THICKNESS)
    by_side = {}
    if existing:
        for wall in existing:
            side = wall.get("side")
            if side:
                by_side[side] = wall

    segments = {
        "south": {"start": [ox, oy, oz], "end": [ox + width, oy, oz]},
        "east": {"start": [ox + width, oy, oz], "end": [ox + width, oy + depth, oz]},
        "north": {"start": [ox, oy + depth, oz], "end": [ox + width, oy + depth, oz]},
        "west": {"start": [ox, oy, oz], "end": [ox, oy + depth, oz]},
    }
    walls = []
    for side in RECT_WALL_ORDER:
        prev = by_side.get(side, {})
        walls.append(
            {
                "wall_id": prev.get("wall_id") or _new_id(),
                "side": side,
                "thickness": thickness,
                "height": height,
                "segment": segments[side],
                "length": wall_length_for_side(width, depth, side),
            }
        )
    return walls


def create_room_model(params):
    """Build a new room model dict from create_room params."""
    name = str(params.get("name") or "ROOM")
    origin = list(params.get("location") or params.get("origin") or [0, 0, 0])
    if len(origin) < 3:
        origin = [
            _f(origin[0]) if origin else 0.0,
            _f(origin[1]) if len(origin) > 1 else 0.0,
            0.0,
        ]
    else:
        origin = [_f(origin[0]), _f(origin[1]), _f(origin[2])]

    footprint_in = params.get("footprint") or {}
    kind = str(footprint_in.get("kind") or params.get("footprint_kind") or "rectangle").strip().lower()
    if kind not in FOOTPRINT_KINDS:
        raise ValueError(f"unsupported footprint.kind {kind!r}")
    if kind != "rectangle":
        raise ValueError("MVP supports footprint.kind 'rectangle' only")

    width = _f(footprint_in.get("width", params.get("width", 10.0)), 10.0)
    depth = _f(footprint_in.get("depth", params.get("depth", 10.0)), 10.0)
    if width <= 0 or depth <= 0:
        raise ValueError("room width and depth must be > 0")

    height = _f(params.get("height", DEFAULT_WALL_HEIGHT), DEFAULT_WALL_HEIGHT)
    if height <= 0:
        raise ValueError("room height must be > 0")

    thickness = _f(params.get("wall_thickness", DEFAULT_WALL_THICKNESS), DEFAULT_WALL_THICKNESS)
    room_id = str(params.get("room_id") or _new_id())

    return {
        "schema_version": "0.1.0",
        "room_id": room_id,
        "name": name,
        "origin": origin,
        "height": height,
        "wall_thickness": thickness,
        "footprint": {"kind": "rectangle", "width": width, "depth": depth},
        "walls": derive_rectangle_walls(origin, width, depth, height, thickness),
        "openings": [],
        "fixed_elements": [],
        "collection": str(params.get("collection") or "layoutlab_room"),
    }


def room_to_dict(model):
    return copy.deepcopy(model)


def find_wall(model, wall_ref):
    """Resolve wall by wall_id or side name (south/east/north/west)."""
    if not wall_ref:
        raise ValueError("wall reference required")
    ref = str(wall_ref)
    for wall in model.get("walls", []):
        if wall.get("wall_id") == ref or wall.get("side") == ref:
            return wall
    raise ValueError(f"wall not found: {wall_ref}")


def update_room_model(model, params):
    params = params or {}
    if "name" in params:
        model["name"] = str(params["name"])
    if "collection" in params:
        model["collection"] = str(params["collection"])

    if "location" in params or "origin" in params:
        loc = params.get("location") or params.get("origin")
        model["origin"] = [
            _f(loc[0]),
            _f(loc[1]),
            _f(loc[2]) if len(loc) > 2 else model["origin"][2],
        ]

    footprint = model["footprint"]
    if footprint.get("kind") != "rectangle":
        raise ValueError("MVP update_room supports rectangle only")

    width = footprint["width"]
    depth = footprint["depth"]
    if "width" in params:
        width = _f(params["width"])
    if "depth" in params:
        depth = _f(params["depth"])
    fp_in = params.get("footprint") or {}
    if "width" in fp_in:
        width = _f(fp_in["width"])
    if "depth" in fp_in:
        depth = _f(fp_in["depth"])
    if width <= 0 or depth <= 0:
        raise ValueError("room width and depth must be > 0")
    footprint["width"] = width
    footprint["depth"] = depth

    if "height" in params:
        height = _f(params["height"])
        if height <= 0:
            raise ValueError("room height must be > 0")
        model["height"] = height
    if "wall_thickness" in params:
        model["wall_thickness"] = _f(params["wall_thickness"], DEFAULT_WALL_THICKNESS)

    model["walls"] = derive_rectangle_walls(
        model["origin"],
        footprint["width"],
        footprint["depth"],
        model["height"],
        model["wall_thickness"],
        existing=model.get("walls"),
    )
    _revalidate_attachments(model)
    return model


def _revalidate_attachments(model):
    wall_ids = {w["wall_id"] for w in model.get("walls", [])}
    sides = {w["side"]: w["wall_id"] for w in model.get("walls", []) if w.get("side")}
    for opening in model.get("openings", []):
        if opening.get("wall_id") not in wall_ids and opening.get("wall_side") in sides:
            opening["wall_id"] = sides[opening["wall_side"]]
        if opening.get("wall_id") not in wall_ids:
            raise ValueError(f"opening {opening.get('opening_id')} references missing wall")
    for fixed in model.get("fixed_elements", []):
        if fixed.get("wall_id") not in wall_ids and fixed.get("wall_side") in sides:
            fixed["wall_id"] = sides[fixed["wall_side"]]
        if fixed.get("wall_id") not in wall_ids:
            raise ValueError(f"fixed_element {fixed.get('fixed_element_id')} references missing wall")


def _fit_on_wall(wall, offset, span, label):
    if span <= 0:
        raise ValueError(f"{label} span must be > 0")
    if offset < 0 or offset + span > wall["length"] + 1e-6:
        raise ValueError(
            f"{label} does not fit on wall {wall.get('side')}: "
            f"offset={offset} span={span} length={wall['length']}"
        )


def add_opening(model, params):
    params = params or {}
    kind = str(params.get("kind") or params.get("opening_kind") or "door").strip().lower()
    if kind not in OPENING_KINDS:
        raise ValueError(f"unsupported opening kind {kind!r}")
    wall = find_wall(model, params.get("wall_id") or params.get("wall") or params.get("wall_side"))
    width = _f(params.get("width"), 9.0 if kind == "door" else 10.0)
    height = _f(params.get("height"), 20.0 if kind == "door" else 14.0)
    offset = _f(params.get("offset"), 0.0)
    sill = _f(params.get("sill_height") or params.get("sill"), 0.0 if kind == "door" else 8.0)
    if height <= 0:
        raise ValueError("opening height must be > 0")
    _fit_on_wall(wall, offset, width, "opening")

    opening = {
        "opening_id": str(params.get("opening_id") or _new_id()),
        "name": str(params.get("opening_name") or params.get("name") or f"{kind}_{wall.get('side')}"),
        "kind": kind,
        "wall_id": wall["wall_id"],
        "wall_side": wall.get("side"),
        "offset": offset,
        "width": width,
        "height": height,
        "sill_height": sill,
    }
    model.setdefault("openings", []).append(opening)
    return opening


def _find_opening(model, params):
    opening_id = (params or {}).get("opening_id")
    name = (params or {}).get("opening_name") or (params or {}).get("name")
    for item in model.get("openings", []):
        if opening_id and item.get("opening_id") == opening_id:
            return item
        if name and item.get("name") == name:
            return item
    raise ValueError(f"opening not found: {opening_id or name}")


def update_opening(model, params):
    params = params or {}
    opening = _find_opening(model, params)

    if "kind" in params:
        kind = str(params["kind"]).strip().lower()
        if kind not in OPENING_KINDS:
            raise ValueError(f"unsupported opening kind {kind!r}")
        opening["kind"] = kind
    if "name" in params and params.get("opening_id"):
        opening["name"] = str(params["name"])
    if any(k in params for k in ("wall_id", "wall", "wall_side")):
        wall = find_wall(model, params.get("wall_id") or params.get("wall") or params.get("wall_side"))
        opening["wall_id"] = wall["wall_id"]
        opening["wall_side"] = wall.get("side")
    for src, dest in (
        ("offset", "offset"),
        ("width", "width"),
        ("height", "height"),
        ("sill_height", "sill_height"),
        ("sill", "sill_height"),
    ):
        if src in params:
            opening[dest] = _f(params[src])

    wall = find_wall(model, opening["wall_id"])
    _fit_on_wall(wall, opening["offset"], opening["width"], "opening")
    return opening


def remove_opening(model, params):
    opening = _find_opening(model, params)
    model["openings"].remove(opening)
    return opening


def add_fixed_element(model, params):
    params = params or {}
    kind = str(params.get("kind") or params.get("fixed_kind") or "radiator").strip().lower()
    if kind not in FIXED_KINDS:
        raise ValueError(f"unsupported fixed element kind {kind!r}")
    wall = find_wall(model, params.get("wall_id") or params.get("wall") or params.get("wall_side"))
    width = _f(params.get("width"), 11.0)
    depth = _f(params.get("depth"), 1.0)
    height = _f(params.get("height"), 7.5)
    offset = _f(params.get("offset"), 0.0)
    if depth <= 0 or height <= 0:
        raise ValueError("fixed element dimensions must be > 0")
    _fit_on_wall(wall, offset, width, "fixed element")

    fixed = {
        "fixed_element_id": str(params.get("fixed_element_id") or _new_id()),
        "name": str(params.get("fixed_name") or params.get("name") or f"{kind}_{wall.get('side')}"),
        "kind": kind,
        "wall_id": wall["wall_id"],
        "wall_side": wall.get("side"),
        "offset": offset,
        "width": width,
        "depth": depth,
        "height": height,
    }
    model.setdefault("fixed_elements", []).append(fixed)
    return fixed


def _find_fixed(model, params):
    fixed_id = (params or {}).get("fixed_element_id")
    name = (params or {}).get("fixed_name") or (params or {}).get("name")
    for item in model.get("fixed_elements", []):
        if fixed_id and item.get("fixed_element_id") == fixed_id:
            return item
        if name and item.get("name") == name:
            return item
    raise ValueError(f"fixed_element not found: {fixed_id or name}")


def update_fixed_element(model, params):
    params = params or {}
    fixed = _find_fixed(model, params)

    if "kind" in params:
        kind = str(params["kind"]).strip().lower()
        if kind not in FIXED_KINDS:
            raise ValueError(f"unsupported fixed element kind {kind!r}")
        fixed["kind"] = kind
    if "name" in params and params.get("fixed_element_id"):
        fixed["name"] = str(params["name"])
    if any(k in params for k in ("wall_id", "wall", "wall_side")):
        wall = find_wall(model, params.get("wall_id") or params.get("wall") or params.get("wall_side"))
        fixed["wall_id"] = wall["wall_id"]
        fixed["wall_side"] = wall.get("side")
    for key in ("offset", "width", "depth", "height"):
        if key in params:
            fixed[key] = _f(params[key])

    wall = find_wall(model, fixed["wall_id"])
    _fit_on_wall(wall, fixed["offset"], fixed["width"], "fixed element")
    return fixed


def remove_fixed_element(model, params):
    fixed = _find_fixed(model, params)
    model["fixed_elements"].remove(fixed)
    return fixed


def _wall_slot_box(model, wall, offset, span, z0, height, depth, inward):
    """AABB along a wall.

    Offset/span: south/north from west along +X; west/east from south along +Y.
    """
    ox, oy, oz = (_f(v) for v in model["origin"])
    width = _f(model["footprint"]["width"])
    room_depth = _f(model["footprint"]["depth"])
    thickness = _f(model.get("wall_thickness"), DEFAULT_WALL_THICKNESS)
    side = wall.get("side")
    d = _f(depth)

    if side == "south":
        x = ox + offset
        if inward:
            return [x, oy + thickness, oz + z0], [span, d, height]
        return [x, oy - d * 0.5, oz + z0], [span, d, height]
    if side == "north":
        x = ox + offset
        if inward:
            return [x, oy + room_depth - thickness - d, oz + z0], [span, d, height]
        return [x, oy + room_depth - d * 0.5, oz + z0], [span, d, height]
    if side == "west":
        y = oy + offset
        if inward:
            return [ox + thickness, y, oz + z0], [d, span, height]
        return [ox - d * 0.5, y, oz + z0], [d, span, height]
    if side == "east":
        y = oy + offset
        if inward:
            return [ox + width - thickness - d, y, oz + z0], [d, span, height]
        return [ox + width - d * 0.5, y, oz + z0], [d, span, height]
    raise ValueError(f"unknown wall side {side!r}")


def opening_world_box(model, opening):
    wall = find_wall(model, opening["wall_id"])
    depth = max(_f(model.get("wall_thickness"), DEFAULT_WALL_THICKNESS) * 1.2, 0.25)
    return _wall_slot_box(
        model,
        wall,
        opening["offset"],
        opening["width"],
        opening.get("sill_height", 0.0),
        opening["height"],
        depth=depth,
        inward=False,
    )


def fixed_element_world_box(model, fixed):
    wall = find_wall(model, fixed["wall_id"])
    return _wall_slot_box(
        model,
        wall,
        fixed["offset"],
        fixed["width"],
        0.0,
        fixed["height"],
        depth=fixed["depth"],
        inward=True,
    )


def wall_display_box(model, wall):
    ox, oy, oz = (_f(v) for v in model["origin"])
    width = _f(model["footprint"]["width"])
    depth = _f(model["footprint"]["depth"])
    height = _f(wall.get("height", model["height"]))
    t = _f(wall.get("thickness", model.get("wall_thickness", DEFAULT_WALL_THICKNESS)))
    side = wall.get("side")
    if side == "south":
        return [ox, oy - t, oz], [width, t, height]
    if side == "north":
        return [ox, oy + depth, oz], [width, t, height]
    if side == "west":
        return [ox - t, oy, oz], [t, depth, height]
    if side == "east":
        return [ox + width, oy, oz], [t, depth, height]
    raise ValueError(f"unknown wall side {side!r}")


def floor_display_box(model):
    ox, oy, oz = (_f(v) for v in model["origin"])
    width = _f(model["footprint"]["width"])
    depth = _f(model["footprint"]["depth"])
    return [ox, oy, oz], [width, depth, 0.05]


def room_world_bounds(model):
    ox, oy, oz = (_f(v) for v in model["origin"])
    width = _f(model["footprint"]["width"])
    depth = _f(model["footprint"]["depth"])
    height = _f(model["height"])
    t = _f(model.get("wall_thickness"), DEFAULT_WALL_THICKNESS)
    return {
        "min": [ox - t, oy - t, oz],
        "max": [ox + width + t, oy + depth + t, oz + height],
    }


def export_room_block(model):
    """Serializable layoutlab.room export block."""
    return {
        "room_id": model["room_id"],
        "name": model["name"],
        "schema_version": model.get("schema_version", "0.1.0"),
        "origin": list(model["origin"]),
        "height": model["height"],
        "wall_thickness": model.get("wall_thickness", DEFAULT_WALL_THICKNESS),
        "footprint": copy.deepcopy(model["footprint"]),
        "walls": copy.deepcopy(model.get("walls", [])),
        "openings": copy.deepcopy(model.get("openings", [])),
        "fixed_elements": copy.deepcopy(model.get("fixed_elements", [])),
        "world_bounds": room_world_bounds(model),
        "collection": model.get("collection", "layoutlab_room"),
    }
