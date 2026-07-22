"""Pure-Python Room Model (DD-010) — no bpy dependency."""

from __future__ import annotations

import copy
import uuid

FOOTPRINT_KINDS = ("rectangle", "polygon")
OPENING_KINDS = ("door", "window")
FIXED_KINDS = ("radiator",)
RECT_WALL_ORDER = ("south", "east", "north", "west")  # y_min, x_max, y_max, x_min
DEFAULT_WALL_THICKNESS = 0.02
DEFAULT_WALL_HEIGHT = 2.6

ATTACHMENT_ACTIVE = "ACTIVE"
ATTACHMENT_INACTIVE_OUTSIDE_WALL = "INACTIVE_OUTSIDE_WALL"
CORNER_NAMES = ("sw", "se", "nw", "ne")


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

    width = _f(footprint_in.get("width", params.get("width", 4.0)), 4.0)
    depth = _f(footprint_in.get("depth", params.get("depth", 3.0)), 3.0)
    if width <= 0 or depth <= 0:
        raise ValueError("room width and depth must be > 0")

    height = _f(params.get("height", DEFAULT_WALL_HEIGHT), DEFAULT_WALL_HEIGHT)
    if height <= 0:
        raise ValueError("room height must be > 0")

    thickness = _f(params.get("wall_thickness", DEFAULT_WALL_THICKNESS), DEFAULT_WALL_THICKNESS)
    room_id = str(params.get("room_id") or _new_id())

    rotation_z = _f(params.get("rotation_z_deg", 0.0), 0.0)
    return {
        "schema_version": "0.1.0",
        "room_id": room_id,
        "name": name,
        "origin": origin,
        "rotation_z_deg": rotation_z,
        "height": height,
        "wall_thickness": thickness,
        "footprint": {"kind": "rectangle", "width": width, "depth": depth},
        "walls": derive_rectangle_walls(origin, width, depth, height, thickness),
        "openings": [],
        "fixed_elements": [],
        "collection": str(params.get("collection") or "layoutlab_room"),
        "visible": bool(params.get("visible", True)),
        "locked": bool(params.get("locked", False)),
        "included_in_analysis": bool(params.get("included_in_analysis", True)),
        "protected_from_ai": bool(params.get("protected_from_ai", False)),
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

    footprint = model["footprint"]
    if footprint.get("kind") != "rectangle":
        raise ValueError("MVP update_room supports rectangle only")

    prev = _footprint_snapshot(model)

    if "location" in params or "origin" in params:
        loc = params.get("location") or params.get("origin")
        model["origin"] = [
            _f(loc[0]),
            _f(loc[1]),
            _f(loc[2]) if len(loc) > 2 else model["origin"][2],
        ]

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

    _apply_rectangle_footprint(model, existing=model.get("walls"))
    _reconcile_wall_attachments(model, prev)
    return model


def _footprint_snapshot(model):
    origin = list(model["origin"])
    fp = model["footprint"]
    return {
        "origin": origin,
        "width": _f(fp["width"]),
        "depth": _f(fp["depth"]),
    }


def _apply_rectangle_footprint(model, *, existing=None):
    fp = model["footprint"]
    model["walls"] = derive_rectangle_walls(
        model["origin"],
        fp["width"],
        fp["depth"],
        model["height"],
        model["wall_thickness"],
        existing=existing if existing is not None else model.get("walls"),
    )
    _revalidate_attachments(model)


def _attachment_world_u(model, wall, offset):
    """World coordinate along the wall's primary axis at ``offset``."""
    ox, oy = _f(model["origin"][0]), _f(model["origin"][1])
    side = wall.get("side")
    if side in ("south", "north"):
        return ox + _f(offset)
    if side in ("west", "east"):
        return oy + _f(offset)
    raise ValueError(f"unknown wall side {side!r}")


def _offset_from_world_u(model, wall, world_u):
    ox, oy = _f(model["origin"][0]), _f(model["origin"][1])
    side = wall.get("side")
    if side in ("south", "north"):
        return _f(world_u) - ox
    if side in ("west", "east"):
        return _f(world_u) - oy
    raise ValueError(f"unknown wall side {side!r}")


def _attachment_fits(wall, offset, span):
    return offset >= -1e-6 and offset + span <= wall["length"] + 1e-6


def _snapshot_attachments(model):
    """Capture world-U anchors before a footprint change (DD-019 preserve world)."""
    snaps = []
    for opening in model.get("openings", []):
        wall = find_wall(model, opening["wall_id"])
        snaps.append(
            {
                "kind": "opening",
                "id": opening.get("opening_id"),
                "wall_id": opening["wall_id"],
                "world_u": _attachment_world_u(model, wall, opening.get("offset", 0.0)),
                "span": _f(opening.get("width")),
            }
        )
    for fixed in model.get("fixed_elements", []):
        wall = find_wall(model, fixed["wall_id"])
        snaps.append(
            {
                "kind": "fixed",
                "id": fixed.get("fixed_element_id"),
                "wall_id": fixed["wall_id"],
                "world_u": _attachment_world_u(model, wall, fixed.get("offset", 0.0)),
                "span": _f(fixed.get("width")),
            }
        )
    return snaps


def _reconcile_wall_attachments(model, prev_footprint=None):
    """Recompute offsets from preserved world anchors; inactive when swallowed."""
    # If prev given, use snapshots from that geometry conceptually — callers snapshot
    # before mutating. When prev is a footprint dict we rebuild anchors using current
    # attachments' offsets against *prev* geometry via a temporary view.
    if prev_footprint is not None:
        temp = {
            "origin": list(prev_footprint["origin"]),
            "footprint": {
                "kind": "rectangle",
                "width": prev_footprint["width"],
                "depth": prev_footprint["depth"],
            },
            "walls": derive_rectangle_walls(
                prev_footprint["origin"],
                prev_footprint["width"],
                prev_footprint["depth"],
                model["height"],
                model.get("wall_thickness", DEFAULT_WALL_THICKNESS),
                existing=model.get("walls"),
            ),
            "openings": model.get("openings", []),
            "fixed_elements": model.get("fixed_elements", []),
        }
        snaps = _snapshot_attachments(temp)
    else:
        snaps = _snapshot_attachments(model)

    by_opening = {s["id"]: s for s in snaps if s["kind"] == "opening"}
    by_fixed = {s["id"]: s for s in snaps if s["kind"] == "fixed"}

    for opening in model.get("openings", []):
        snap = by_opening.get(opening.get("opening_id"))
        wall = find_wall(model, opening["wall_id"])
        if snap:
            opening["offset"] = _offset_from_world_u(model, wall, snap["world_u"])
        span = _f(opening.get("width"))
        if _attachment_fits(wall, _f(opening.get("offset")), span):
            opening["state"] = ATTACHMENT_ACTIVE
        else:
            opening["state"] = ATTACHMENT_INACTIVE_OUTSIDE_WALL
        opening.setdefault("state", ATTACHMENT_ACTIVE)

    for fixed in model.get("fixed_elements", []):
        snap = by_fixed.get(fixed.get("fixed_element_id"))
        wall = find_wall(model, fixed["wall_id"])
        if snap:
            fixed["offset"] = _offset_from_world_u(model, wall, snap["world_u"])
        span = _f(fixed.get("width"))
        if _attachment_fits(wall, _f(fixed.get("offset")), span):
            fixed["state"] = ATTACHMENT_ACTIVE
        else:
            fixed["state"] = ATTACHMENT_INACTIVE_OUTSIDE_WALL
        fixed.setdefault("state", ATTACHMENT_ACTIVE)


def move_wall(model, wall_ref, delta, *, outward_positive=True):
    """Move one rectangle wall parallel to itself (FC-001/WP-05).

    ``delta > 0`` expands the room (wall moves outward) when ``outward_positive``.
    Opposite wall stays fixed; adjacent walls lengthen/shorten.
    """
    if model["footprint"].get("kind") != "rectangle":
        raise ValueError("move_wall supports rectangle footprint only")
    wall = find_wall(model, wall_ref)
    side = wall.get("side")
    d = _f(delta)
    if not outward_positive:
        d = -d

    prev = _footprint_snapshot(model)
    ox, oy, oz = (_f(v) for v in model["origin"])
    width = _f(model["footprint"]["width"])
    depth = _f(model["footprint"]["depth"])

    if side == "north":
        depth = depth + d
    elif side == "south":
        oy = oy - d
        depth = depth + d
    elif side == "east":
        width = width + d
    elif side == "west":
        ox = ox - d
        width = width + d
    else:
        raise ValueError(f"unknown wall side {side!r}")

    if width <= 1e-6 or depth <= 1e-6:
        raise ValueError("move_wall would make width/depth <= 0")

    model["origin"] = [ox, oy, oz]
    model["footprint"]["width"] = width
    model["footprint"]["depth"] = depth
    _apply_rectangle_footprint(model, existing=model.get("walls"))
    _reconcile_wall_attachments(model, prev)
    return model


def move_corner(model, corner, dx=0.0, dy=0.0):
    """Move a rectangle corner (sw/se/nw/ne) by dx/dy in world XY (FC-001/WP-05)."""
    corner = str(corner or "").strip().lower()
    if corner not in CORNER_NAMES:
        raise ValueError(f"corner must be one of {CORNER_NAMES}")
    dx = _f(dx)
    dy = _f(dy)
    # Map corner motion to wall outward deltas.
    # sw: west outward = -dx if dx<0... 
    # Moving SW corner by (dx, dy): west wall moves by -dx (outward if dx negative),
    # south wall moves by -dy (outward if dy negative).
    # Better: apply footprint bounds directly.
    if model["footprint"].get("kind") != "rectangle":
        raise ValueError("move_corner supports rectangle footprint only")

    prev = _footprint_snapshot(model)
    ox, oy, oz = (_f(v) for v in model["origin"])
    width = _f(model["footprint"]["width"])
    depth = _f(model["footprint"]["depth"])

    # Corner world positions before:
    # sw=(ox,oy), se=(ox+w,oy), nw=(ox,oy+d), ne=(ox+w,oy+d)
    if corner == "sw":
        ox, oy = ox + dx, oy + dy
        width, depth = width - dx, depth - dy
    elif corner == "se":
        oy = oy + dy
        width, depth = width + dx, depth - dy
    elif corner == "nw":
        ox = ox + dx
        width, depth = width - dx, depth + dy
    elif corner == "ne":
        width, depth = width + dx, depth + dy

    if width <= 1e-6 or depth <= 1e-6:
        raise ValueError("move_corner would make width/depth <= 0")

    model["origin"] = [ox, oy, oz]
    model["footprint"]["width"] = width
    model["footprint"]["depth"] = depth
    _apply_rectangle_footprint(model, existing=model.get("walls"))
    _reconcile_wall_attachments(model, prev)
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


def is_attachment_active(item):
    return str(item.get("state") or ATTACHMENT_ACTIVE) == ATTACHMENT_ACTIVE


def add_opening(model, params):
    params = params or {}
    kind = str(params.get("kind") or params.get("opening_kind") or "door").strip().lower()
    if kind not in OPENING_KINDS:
        raise ValueError(f"unsupported opening kind {kind!r}")
    wall = find_wall(model, params.get("wall_id") or params.get("wall") or params.get("wall_side"))
    width = _f(params.get("width"), 0.9 if kind == "door" else 1.0)
    height = _f(params.get("height"), 2.0 if kind == "door" else 1.4)
    if "offset" in params:
        offset = _f(params.get("offset"), 0.0)
    elif "offset_along_wall" in params:
        offset = _f(params.get("offset_along_wall"), 0.0)
    else:
        offset = 0.0
    sill = _f(params.get("sill_height") or params.get("sill"), 0.0 if kind == "door" else 0.8)
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
        "state": ATTACHMENT_ACTIVE,
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
        ("offset_along_wall", "offset"),
        ("width", "width"),
        ("height", "height"),
        ("sill_height", "sill_height"),
        ("sill", "sill_height"),
    ):
        if src in params:
            opening[dest] = _f(params[src])

    wall = find_wall(model, opening["wall_id"])
    if _attachment_fits(wall, _f(opening["offset"]), _f(opening["width"])):
        opening["state"] = ATTACHMENT_ACTIVE
    else:
        # Explicit user edit that doesn't fit → keep data, mark inactive (no silent delete).
        opening["state"] = ATTACHMENT_INACTIVE_OUTSIDE_WALL
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
    width = _f(params.get("width"), 1.1)
    depth = _f(params.get("depth"), 0.1)
    height = _f(params.get("height"), 0.75)
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
        "state": ATTACHMENT_ACTIVE,
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
    for key in ("offset", "offset_along_wall", "width", "depth", "height"):
        if key in params:
            dest = "offset" if key == "offset_along_wall" else key
            fixed[dest] = _f(params[key])

    wall = find_wall(model, fixed["wall_id"])
    if _attachment_fits(wall, _f(fixed["offset"]), _f(fixed["width"])):
        fixed["state"] = ATTACHMENT_ACTIVE
    else:
        fixed["state"] = ATTACHMENT_INACTIVE_OUTSIDE_WALL
    return fixed


def remove_fixed_element(model, params):
    fixed = _find_fixed(model, params)
    model["fixed_elements"].remove(fixed)
    return fixed


def _wall_slot_box(model, wall, offset, span, z0, height, depth, inward):
    """AABB along a wall plane (zero-thickness fabric).

    Offset/span: south/north from west along +X; west/east from south along +Y.
    ``inward=True`` grows into the room from the wall plane.
    """
    ox, oy, oz = (_f(v) for v in model["origin"])
    width = _f(model["footprint"]["width"])
    room_depth = _f(model["footprint"]["depth"])
    side = wall.get("side")
    d = max(_f(depth), 0.005)

    if side == "south":
        x = ox + offset
        if inward:
            return [x, oy, oz + z0], [span, d, height]
        return [x, oy - d, oz + z0], [span, d, height]
    if side == "north":
        x = ox + offset
        if inward:
            return [x, oy + room_depth - d, oz + z0], [span, d, height]
        return [x, oy + room_depth, oz + z0], [span, d, height]
    if side == "west":
        y = oy + offset
        if inward:
            return [ox, y, oz + z0], [d, span, height]
        return [ox - d, y, oz + z0], [d, span, height]
    if side == "east":
        y = oy + offset
        if inward:
            return [ox + width - d, y, oz + z0], [d, span, height]
        return [ox + width, y, oz + z0], [d, span, height]
    raise ValueError(f"unknown wall side {side!r}")


def opening_world_box(model, opening):
    wall = find_wall(model, opening["wall_id"])
    depth = max(_f(model.get("wall_thickness"), DEFAULT_WALL_THICKNESS) * 1.2, 0.025)
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


def opening_access_world_box(model, opening, depth=0.7):
    """Inward box in front of a door/window for soft access checks (DD-015)."""
    wall = find_wall(model, opening["wall_id"])
    return _wall_slot_box(
        model,
        wall,
        opening["offset"],
        opening["width"],
        opening.get("sill_height", 0.0),
        opening["height"],
        depth=_f(depth, 0.7),
        inward=True,
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


def wall_plane_corners(model, wall):
    """Four world-space corners of an inward-facing wall plane.

    Winding yields a geometric normal pointing into the room (right-hand rule).
    With material backface culling, walls are opaque from inside and see-through
    from outside.
    """
    wall_h = _f(wall.get("height", model["height"]))
    return wall_panel_corners(model, wall, 0.0, wall["length"], 0.0, wall_h)


def openings_for_wall(model, wall):
    wall_id = wall.get("wall_id")
    return [
        o
        for o in model.get("openings", [])
        if o.get("wall_id") == wall_id and is_attachment_active(o)
    ]


def wall_local_opening_rect(opening, wall_height):
    """Return (u0, u1, v0, v1) in wall-local space for an opening hole."""
    u0 = _f(opening.get("offset"))
    u1 = u0 + _f(opening.get("width"))
    v0 = max(0.0, _f(opening.get("sill_height")))
    v1 = min(_f(wall_height), v0 + _f(opening.get("height")))
    if u1 <= u0 or v1 <= v0:
        raise ValueError(f"opening {opening.get('name')!r} has empty wall footprint")
    return (u0, u1, v0, v1)


def _rects_overlap(a, b, eps=1e-9):
    return a[0] < b[1] - eps and a[1] > b[0] + eps and a[2] < b[3] - eps and a[3] > b[2] + eps


def _subtract_one_rect(outer, hole, eps=1e-9):
    """Subtract axis-aligned ``hole`` from ``outer``; return remaining rects."""
    ou0, ou1, ov0, ov1 = outer
    hu0, hu1, hv0, hv1 = hole
    cu0 = max(ou0, hu0)
    cu1 = min(ou1, hu1)
    cv0 = max(ov0, hv0)
    cv1 = min(ov1, hv1)
    if cu1 - cu0 <= eps or cv1 - cv0 <= eps:
        return [outer]
    parts = []
    if cu0 - ou0 > eps:
        parts.append((ou0, cu0, ov0, ov1))
    if ou1 - cu1 > eps:
        parts.append((cu1, ou1, ov0, ov1))
    if cv0 - ov0 > eps:
        parts.append((cu0, cu1, ov0, cv0))
    if ov1 - cv1 > eps:
        parts.append((cu0, cu1, cv1, ov1))
    return parts


def subtract_rects(outer, holes, eps=1e-9):
    """Subtract all ``holes`` from ``outer``; holes must not overlap each other."""
    holes = list(holes)
    for i, a in enumerate(holes):
        for b in holes[i + 1 :]:
            if _rects_overlap(a, b, eps=eps):
                raise ValueError("openings overlap on the same wall")
    remaining = [outer]
    for hole in holes:
        next_remaining = []
        for rect in remaining:
            next_remaining.extend(_subtract_one_rect(rect, hole, eps=eps))
        remaining = next_remaining
    return remaining


def wall_panel_corners(model, wall, u0, u1, v0, v1):
    """Four world corners for a wall sub-panel in local (u along wall, v up)."""
    ox, oy, oz = (_f(v) for v in model["origin"])
    width = _f(model["footprint"]["width"])
    depth = _f(model["footprint"]["depth"])
    side = wall.get("side")
    u0, u1, v0, v1 = _f(u0), _f(u1), _f(v0), _f(v1)
    if side == "south":
        return [
            [ox + u0, oy, oz + v0],
            [ox + u0, oy, oz + v1],
            [ox + u1, oy, oz + v1],
            [ox + u1, oy, oz + v0],
        ]
    if side == "north":
        return [
            [ox + u0, oy + depth, oz + v0],
            [ox + u1, oy + depth, oz + v0],
            [ox + u1, oy + depth, oz + v1],
            [ox + u0, oy + depth, oz + v1],
        ]
    if side == "west":
        return [
            [ox, oy + u0, oz + v0],
            [ox, oy + u1, oz + v0],
            [ox, oy + u1, oz + v1],
            [ox, oy + u0, oz + v1],
        ]
    if side == "east":
        return [
            [ox + width, oy + u0, oz + v0],
            [ox + width, oy + u0, oz + v1],
            [ox + width, oy + u1, oz + v1],
            [ox + width, oy + u1, oz + v0],
        ]
    raise ValueError(f"unknown wall side {side!r}")


def wall_display_panels(model, wall):
    """List of inward-facing wall panel dicts after cutting openings.

    Each item: ``{"corners": [...], "u0", "u1", "v0", "v1"}``.
    """
    wall_h = _f(wall.get("height", model["height"]))
    wall_len = _f(wall.get("length"))
    outer = (0.0, wall_len, 0.0, wall_h)
    holes = []
    for opening in openings_for_wall(model, wall):
        holes.append(wall_local_opening_rect(opening, wall_h))
    panels = []
    for u0, u1, v0, v1 in subtract_rects(outer, holes):
        panels.append(
            {
                "corners": wall_panel_corners(model, wall, u0, u1, v0, v1),
                "u0": u0,
                "u1": u1,
                "v0": v0,
                "v1": v1,
            }
        )
    return panels


def wall_display_box(model, wall):
    """Thin AABB for export/debug around an inward wall plane (zero thickness)."""
    corners = wall_plane_corners(model, wall)
    xs = [c[0] for c in corners]
    ys = [c[1] for c in corners]
    zs = [c[2] for c in corners]
    return (
        [min(xs), min(ys), min(zs)],
        [max(xs) - min(xs) or 0.001, max(ys) - min(ys) or 0.001, max(zs) - min(zs) or 0.001],
    )


def floor_display_box(model):
    ox, oy, oz = (_f(v) for v in model["origin"])
    width = _f(model["footprint"]["width"])
    depth = _f(model["footprint"]["depth"])
    return [ox, oy, oz], [width, depth, 0.005]


def room_world_bounds(model):
    ox, oy, oz = (_f(v) for v in model["origin"])
    width = _f(model["footprint"]["width"])
    depth = _f(model["footprint"]["depth"])
    height = _f(model["height"])
    return {
        "min": [ox, oy, oz],
        "max": [ox + width, oy + depth, oz + height],
    }


def export_room_block(model):
    """Serializable layoutlab.room export block (DD-010 nested under Spatial Project)."""
    origin = list(model["origin"])
    rotation_z = _f(model.get("rotation_z_deg", 0.0), 0.0)
    return {
        "room_id": model["room_id"],
        "name": model["name"],
        "schema_version": model.get("schema_version", "0.1.0"),
        "origin": origin,
        "rotation_z_deg": rotation_z,
        "transform": {
            "location": origin,
            "rotation_z_deg": rotation_z,
        },
        "height": model["height"],
        "wall_thickness": model.get("wall_thickness", DEFAULT_WALL_THICKNESS),
        "footprint": copy.deepcopy(model["footprint"]),
        "walls": copy.deepcopy(model.get("walls", [])),
        "openings": copy.deepcopy(model.get("openings", [])),
        "fixed_elements": copy.deepcopy(model.get("fixed_elements", [])),
        "world_bounds": room_world_bounds(model),
        "collection": model.get("collection", "layoutlab_room"),
        "visible": bool(model.get("visible", True)),
        "locked": bool(model.get("locked", False)),
        "included_in_analysis": bool(model.get("included_in_analysis", True)),
        "protected_from_ai": bool(model.get("protected_from_ai", False)),
    }
