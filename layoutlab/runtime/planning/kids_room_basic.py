"""Kids-room layout recipe (DD-016) — sleep + play + homework, no bpy.

Differs from bedroom_basic: smaller default bed, desk prioritized over wardrobe,
strategies that keep a free play strip, wardrobe optional (off by default).
"""

from __future__ import annotations

from typing import Any

from .bedroom_basic import (
    MARGIN,
    _default_windows_for_count,
    _f,
    _opening_offset,
    _side,
    _spaced_window_commands,
)
from .placement import mattress_to_bed_axes

RECIPE_NAME = "kids_room_basic"
RECIPE_KIND = "room_use"
RECIPE_GOALS = ("sleep", "play", "homework")
ROOM_NAME = "KIDS_ROOM"
COLLECTION = "layoutlab_room"

# Kids single bed default (human width × length).
BED_MATTRESS_WIDTH = 0.9
BED_MATTRESS_LENGTH = 2.0
DESK_WIDTH = 1.0
DESK_DEPTH = 0.55
DESK_HEIGHT = 0.75
WARDROBE_WIDTH = 0.8
WARDROBE_DEPTH = 0.5
WARDROBE_HEIGHT = 1.8
DOOR_ACCESS_KEEP = 0.9

DEFAULT_STRATEGY = "bed_west__desk_north"

_STRATEGY_SPECS: tuple[dict[str, str], ...] = (
    {"strategy": "bed_west__desk_north", "bed_wall": "west", "desk_wall": "north"},
    {"strategy": "bed_east__desk_north", "bed_wall": "east", "desk_wall": "north"},
    {"strategy": "bed_south__desk_north", "bed_wall": "south", "desk_wall": "north"},
    {"strategy": "bed_north__desk_south", "bed_wall": "north", "desk_wall": "south"},
)


def _overlap(a, b) -> bool:
    if not a or not b:
        return False
    return not (a[2] <= b[0] or b[2] <= a[0] or a[3] <= b[1] or b[3] <= a[1])


def _resolve_strategy(params: dict) -> dict[str, str]:
    bed_wall = str(params.get("bed_wall") or params.get("prefer_bed_wall") or "").strip().lower()
    if bed_wall not in ("south", "north", "east", "west"):
        bed_wall = ""
    desk_wall = str(params.get("desk_wall") or "").strip().lower()
    if desk_wall not in ("south", "north", "east", "west"):
        desk_wall = ""

    strategy = str(params.get("strategy") or "").strip().lower()
    for spec in _STRATEGY_SPECS:
        if strategy and spec["strategy"] == strategy:
            return dict(spec)
        if bed_wall and desk_wall:
            if spec["bed_wall"] == bed_wall and spec["desk_wall"] == desk_wall:
                return dict(spec)
        if bed_wall and not desk_wall and spec["bed_wall"] == bed_wall:
            return dict(spec)

    return dict(_STRATEGY_SPECS[0])


def _bed_placement(
    *,
    bed_wall: str,
    room_w: float,
    room_d: float,
    mattress_w: float,
    mattress_l: float,
) -> tuple[list[float], str, float, float, tuple[float, float, float, float], str]:
    """Return location, head_side, length(X), width(Y), box, note."""
    if bed_wall in ("west", "east"):
        head_side = "x_min" if bed_wall == "west" else "x_max"
        length_x, width_y = mattress_to_bed_axes(head_side, mattress_w, mattress_l)
        length_x = min(length_x, room_w - 2 * MARGIN)
        width_y = min(width_y, room_d - 2 * MARGIN)
        bed_y = MARGIN
        if bed_wall == "west":
            bed_x = MARGIN
            note = (
                f"Bed on west wall (head_side=x_min): "
                f"{mattress_w:.2f}×{mattress_l:.2f}m mattress along +X."
            )
        else:
            bed_x = max(MARGIN, room_w - length_x - MARGIN)
            note = (
                f"Bed on east wall (head_side=x_max): "
                f"{mattress_w:.2f}×{mattress_l:.2f}m mattress along −X."
            )
    else:
        head_side = "y_max" if bed_wall == "north" else "y_min"
        length_x, width_y = mattress_to_bed_axes(head_side, mattress_w, mattress_l)
        length_x = min(length_x, room_w - 2 * MARGIN)
        width_y = min(width_y, room_d - 2 * MARGIN)
        bed_x = MARGIN
        if bed_wall == "north":
            bed_y = max(MARGIN, room_d - width_y - MARGIN)
            note = (
                f"Bed on north wall (head_side=y_max): "
                f"{mattress_w:.2f}×{mattress_l:.2f}m mattress along −Y."
            )
        else:
            bed_y = MARGIN
            note = (
                f"Bed on south wall (head_side=y_min): "
                f"{mattress_w:.2f}×{mattress_l:.2f}m mattress along +Y."
            )

    box = (bed_x, bed_y, bed_x + length_x, bed_y + width_y)
    return [round(bed_x, 3), round(bed_y, 3), 0], head_side, length_x, width_y, box, note


def _desk_placement(
    *,
    desk_wall: str,
    room_w: float,
    room_d: float,
    door_side: str,
    bed_box: tuple | None,
) -> tuple[list[float], float, float, float, str] | None:
    dw = min(DESK_WIDTH, max(0.7, room_w * 0.35))
    dd = min(DESK_DEPTH, 0.55)
    if desk_wall == "north":
        dy = room_d - dd - MARGIN
        # Prefer east half for free play near west bed; avoid east door strip.
        dx = max(MARGIN, room_w - dw - MARGIN)
        if door_side == "east":
            dx = max(MARGIN, min(dx, room_w - DOOR_ACCESS_KEEP - dw))
        if bed_box is not None and _overlap((dx, dy, dx + dw, dy + dd), bed_box):
            dx = max(MARGIN, bed_box[2] + 0.12)
            if dx + dw > room_w - MARGIN:
                return None
        note = "Desk on north wall; chair clearance faces south into play floor."
        return [round(dx, 3), round(dy, 3), 0], dw, dd, 0.45, note
    if desk_wall == "south":
        dy = MARGIN
        dx = max(MARGIN, room_w - dw - MARGIN)
        if door_side == "east":
            dx = max(MARGIN, min(dx, room_w - DOOR_ACCESS_KEEP - dw))
        if bed_box is not None and _overlap((dx, dy, dx + dw, dy + dd), bed_box):
            dx = max(MARGIN, bed_box[2] + 0.12)
            if dx + dw > room_w - MARGIN:
                return None
        note = "Desk on south wall; chair clearance faces north into play floor."
        return [round(dx, 3), round(dy, 3), 0], dw, dd, 0.45, note
    return None


def _wardrobe_placement(
    *,
    room_w: float,
    room_d: float,
    door_side: str,
    bed_box: tuple | None,
    desk_box: tuple | None,
) -> tuple[list[float], float, float, str, str] | None:
    """Compact wardrobe on a free north/south corner — skipped if it won't fit."""
    ww = min(WARDROBE_WIDTH, room_w * 0.28)
    wd = min(WARDROBE_DEPTH, 0.5)
    # Prefer north-west corner (play stays east/south).
    candidates = [
        (MARGIN, room_d - wd - MARGIN, "y_min", "north-west"),
        (max(MARGIN, room_w - ww - MARGIN), room_d - wd - MARGIN, "y_min", "north-east"),
        (MARGIN, MARGIN, "y_max", "south-west"),
    ]
    for wx, wy, front, label in candidates:
        if door_side == "east" and wx + ww > room_w - DOOR_ACCESS_KEEP:
            continue
        box = (wx, wy, wx + ww, wy + wd)
        if bed_box is not None and _overlap(box, bed_box):
            continue
        if desk_box is not None and _overlap(box, desk_box):
            continue
        return [round(wx, 3), round(wy, 3), 0], ww, wd, front, label
    return None


def _place_furniture(
    *,
    room_w: float,
    room_d: float,
    collection: str,
    door_side: str,
    include_bed: bool,
    include_desk: bool,
    include_wardrobe: bool,
    mattress_w: float,
    mattress_l: float,
    bed_wall: str,
    desk_wall: str,
) -> tuple[list[dict], list[str]]:
    commands: list[dict] = []
    notes: list[str] = [
        "Kids recipe prioritizes sleep + homework + free play floor; wardrobe optional.",
    ]
    bed_box = None

    if include_bed:
        loc, head, length_x, width_y, bed_box, note = _bed_placement(
            bed_wall=bed_wall,
            room_w=room_w,
            room_d=room_d,
            mattress_w=mattress_w,
            mattress_l=mattress_l,
        )
        notes.append(note)
        commands.append(
            {
                "action": "run_generator",
                "generator": "bed_basic",
                "params": {
                    "name": "BED",
                    "location": loc,
                    "length": round(length_x, 3),
                    "width": round(width_y, 3),
                    "head_side": head,
                    "collection": collection,
                    "clearances": [
                        {
                            "clearance_name": "bed_entry",
                            "side": "right",
                            "depth": 0.45,
                            "requirement": "preferred",
                        }
                    ],
                },
            }
        )

    desk_box = None
    if include_desk:
        desk = _desk_placement(
            desk_wall=desk_wall,
            room_w=room_w,
            room_d=room_d,
            door_side=door_side,
            bed_box=bed_box,
        )
        if desk is None:
            notes.append("Desk omitted — not enough clear floor beside bed.")
        else:
            loc, dw, dd, cdepth, note = desk
            notes.append(note)
            desk_box = (loc[0], loc[1], loc[0] + dw, loc[1] + dd)
            commands.append(
                {
                    "action": "run_generator",
                    "generator": "desk_basic",
                    "params": {
                        "name": "DESK",
                        "location": loc,
                        "width": round(dw, 3),
                        "depth": round(dd, 3),
                        "height": DESK_HEIGHT,
                        "show_clearance": True,
                        "clearance_depth": cdepth,
                        "collection": collection,
                    },
                }
            )

    if include_wardrobe:
        ward = _wardrobe_placement(
            room_w=room_w,
            room_d=room_d,
            door_side=door_side,
            bed_box=bed_box,
            desk_box=desk_box,
        )
        if ward is None:
            notes.append("Wardrobe omitted — no free corner without blocking play/bed/desk.")
        else:
            loc, ww, wd, front, label = ward
            notes.append(f"Compact wardrobe at {label}.")
            commands.append(
                {
                    "action": "run_generator",
                    "generator": "wardrobe_basic",
                    "params": {
                        "name": "WARDROBE",
                        "location": loc,
                        "width": round(ww, 3),
                        "depth": round(wd, 3),
                        "height": WARDROBE_HEIGHT,
                        "front_side": front,
                        "show_clearance": True,
                        "clearance_depth": 0.45,
                        "collection": collection,
                    },
                }
            )

    return commands, notes


def plan_kids_room_basic(params: dict | None = None) -> dict[str, Any]:
    """Deterministic kids-room commands for one strategy."""
    params = dict(params or {})
    spec = _resolve_strategy(params)

    room_w = max(2.4, _f(params.get("width"), 4.0))
    room_d = max(2.1, _f(params.get("depth"), 3.0))
    room_h = max(2.2, _f(params.get("height"), 2.5))
    collection = str(params.get("collection") or COLLECTION)
    include_bed = params.get("include_bed", True) is not False
    include_desk = params.get("include_desk", True) is not False
    # Wardrobe off by default — play floor first.
    include_wardrobe = params.get("include_wardrobe") is True

    door = params.get("door")
    if door is False or door is None:
        door = {"wall_side": "east", "width": 0.8}
    elif not isinstance(door, dict):
        door = {"wall_side": "east", "width": 0.8}
    door_side = _side(door.get("wall_side"), "east")
    door_w = max(0.7, _f(door.get("width"), 0.8))

    windows_in = params.get("windows")
    if params.get("window_count") is not None:
        try:
            windows_in = _default_windows_for_count(
                int(params.get("window_count")), avoid_side=door_side
            )
        except (TypeError, ValueError):
            windows_in = _default_windows_for_count(1, avoid_side=door_side)
    elif windows_in is None:
        windows_in = _default_windows_for_count(1, avoid_side=door_side)
    elif isinstance(windows_in, int):
        windows_in = _default_windows_for_count(windows_in, avoid_side=door_side)
    elif not isinstance(windows_in, list):
        windows_in = _default_windows_for_count(1, avoid_side=door_side)

    assumes = [
        f"Kids room {room_w:.1f}×{room_d:.1f} m",
        "Recipe kids_room_basic (sleep + play + homework)",
        f"Strategy {spec['strategy']}",
    ]
    if not include_wardrobe:
        assumes.append("No wardrobe by default (play space); set include_wardrobe=true to add.")

    commands: list[dict] = [
        {"action": "delete_collection_objects", "collection": collection},
        {
            "action": "create_room",
            "params": {
                "name": ROOM_NAME,
                "location": [0, 0, 0],
                "width": round(room_w, 3),
                "depth": round(room_d, 3),
                "height": round(room_h, 3),
                "wall_thickness": 0.02,
                "collection": collection,
            },
        },
        {
            "action": "add_opening",
            "params": {
                "room": ROOM_NAME,
                "opening_name": f"door_{door_side}",
                "kind": "door",
                "wall_side": door_side,
                "offset": _opening_offset(door_side, door_w, room_w, room_d),
                "width": round(door_w, 3),
                "height": round(max(1.9, _f(door.get("height"), 2.0)), 3),
            },
        },
    ]

    win_cmds, _win_south = _spaced_window_commands(windows_in, room_w, room_d, ROOM_NAME)
    commands.extend(win_cmds)

    mattress_w = max(0.8, _f(params.get("bed_width"), BED_MATTRESS_WIDTH))
    mattress_l = max(1.6, _f(params.get("bed_length"), BED_MATTRESS_LENGTH))

    furn_cmds, notes = _place_furniture(
        room_w=room_w,
        room_d=room_d,
        collection=collection,
        door_side=door_side,
        include_bed=include_bed,
        include_desk=include_desk,
        include_wardrobe=include_wardrobe,
        mattress_w=mattress_w,
        mattress_l=mattress_l,
        bed_wall=spec["bed_wall"],
        desk_wall=spec["desk_wall"],
    )
    commands.extend(furn_cmds)

    return {
        "ok": True,
        "recipe": RECIPE_NAME,
        "recipe_kind": RECIPE_KIND,
        "recipe_goals": list(RECIPE_GOALS),
        "strategy": spec["strategy"],
        "commands": commands,
        "assumes": assumes,
        "notes": notes,
        "room": {"width": room_w, "depth": room_d, "height": room_h, "name": ROOM_NAME},
    }


def enumerate_kids_room_candidates(params: dict | None = None) -> list[dict[str, Any]]:
    """Expand kids_room_basic into up to 4 candidate command sets."""
    params = dict(params or {})
    prefer = str(params.get("prefer_bed_wall") or params.get("bed_wall") or "").strip().lower()
    specs = list(_STRATEGY_SPECS)
    if prefer in ("south", "north", "east", "west"):
        preferred = [s for s in specs if s["bed_wall"] == prefer]
        other = [s for s in specs if s["bed_wall"] != prefer]
        specs = preferred + other

    out: list[dict[str, Any]] = []
    for spec in specs[:4]:
        call = dict(params)
        call["strategy"] = spec["strategy"]
        call["bed_wall"] = spec["bed_wall"]
        call["desk_wall"] = spec["desk_wall"]
        planned = plan_kids_room_basic(call)
        out.append(
            {
                "candidate_id": spec["strategy"],
                "strategy": spec["strategy"],
                "commands": planned.get("commands") or [],
                "assumes": planned.get("assumes") or [],
                "notes": planned.get("notes") or [],
            }
        )
    return out
